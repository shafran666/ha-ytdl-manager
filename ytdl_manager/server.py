import json, os, re, signal, subprocess, threading, time, uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, unquote
import yt_dlp

VERSION='1.0.3'; ROOT=Path('/data'); ROOT.mkdir(exist_ok=True)
OPTIONS=json.loads((ROOT/'options.json').read_text()) if (ROOT/'options.json').exists() else {}
DEFAULT=Path(OPTIONS.get('download_directory','/media/downloads'))
DB=ROOT/'jobs.json'; PREF=ROOT/'preferences.json'; UI=Path('/app/index.html'); TZ=ZoneInfo(os.environ.get('TZ','UTC'))
LOCK=threading.RLock(); JOBS=[]; ACTIVE={}; METADATA={}; FORMAT_DETAILS={}; SEARCH={}; MAX_JOBS=200
RUNNING={'downloading','processing','cancelling'}
QUEUE_STATES={'queued','scheduled','retry_wait'}
def now(): return datetime.now(timezone.utc).isoformat()
def save():
    temp=DB.with_suffix('.tmp'); temp.write_text(json.dumps(JOBS[-MAX_JOBS:],ensure_ascii=False,indent=2)); temp.replace(DB)
try:
    JOBS=json.loads(DB.read_text()) if DB.exists() else []
    for j in JOBS:
        if j.get('state') in RUNNING:
            j.update(state='retry_wait',message='Interrupted by restart',next_retry=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat())
    for i,j in enumerate(JOBS): j.setdefault('queue_rank',i)
    save()
except Exception as exc: print('History load error:',exc,flush=True); JOBS=[]
def valid_url(url):
    # Supported yt-dlp single-video sites, excluding generic URLs and private hosts.
    from urllib.parse import urlsplit
    import ipaddress
    try:
        if not isinstance(url,str) or len(url)>2048: return False
        p=urlsplit(url)
        if p.scheme!='https' or not p.hostname or p.username or p.password: return False
        host=p.hostname.lower().rstrip('.')
        if host=='localhost' or host.endswith(('.local','.localhost','.internal')): return False
        try: return ipaddress.ip_address(host).is_global
        except ValueError: pass
        if '.' not in host: return False
        from yt_dlp.extractor import gen_extractor_classes
        return any(cls.IE_NAME!='generic' and cls.suitable(url) for cls in gen_extractor_classes())
    except (TypeError,ValueError): return False

def close_brackets(text):
    stack=[]; pairs={'(':')','[':']','{':'}'}
    for ch in text:
        if ch in pairs: stack.append(pairs[ch])
        elif stack and ch==stack[-1]: stack.pop()
    return text+''.join(reversed(stack))

def clean_name(s):
    s=re.sub(r'[<>:"/\\|?*\x00-\x1f]',' ',str(s)); s=re.sub(r'\s+',' ',s).strip(' .')
    if not s or s in ('.','..'): raise ValueError('Invalid Save as name')
    return s[:160].rstrip(' .')
def allowed_dir(path):
    base=Path('/media').resolve(strict=True)
    target=Path(str(path)).resolve(strict=True)
    if not target.is_dir() or (target!=base and base not in target.parents): raise ValueError('Choose an existing folder under /media')
    return target
def chapter_rows(text,duration):
    result=[]
    for line in (text or '').splitlines():
        m=re.search(r'(?<!\d)(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?!\d)\s*[-–—:.)|]*\s*(.{2,120})',line)
        if not m: continue
        h,minutes,seconds,title=m.groups(); sec=int(h or 0)*3600+int(minutes)*60+int(seconds)
        title=title.strip(' -–—:.)|\t')
        if title and (not duration or sec<duration) and (not result or sec>result[-1]['start']): result.append({'start':sec,'title':close_brackets(title)})
    return result if len(result)>=3 else []
def extract(url,comments=False,limit=0):
    opts={'quiet':True,'no_warnings':True,'skip_download':True,'noplaylist':True}
    if comments:
        opts['getcomments']=True
        opts['extractor_args']={'youtube':{'max_comments':[str(limit)]}}
    with yt_dlp.YoutubeDL(opts) as y: return y.extract_info(url,download=False)
def codec_name(c):
    c=c.lower().split('.')[0]
    if c in ('hev1','hvc1','hevc','h265'): return 'H.265'
    if c in ('avc1','avc3','h264'): return 'H.264'
    if c.startswith('vp09') or c=='vp9': return 'VP9'
    if c.startswith('av01') or c=='av1': return 'AV1'
    if c=='vp8': return 'VP8'
    return c.upper()
def analyze_info(info):
    fm=info.get('formats') or []; videos=set(); audios=set(); codecs=set(); combos={}
    for f in fm:
        v=f.get('vcodec') or 'none'; a=f.get('acodec') or 'none'; h=f.get('height'); abr=f.get('abr') or (f.get('tbr') if v=='none' else None)
        if v!='none' and isinstance(h,int) and h>0:
            videos.add(h); c=codec_name(v); codecs.add(c); combos.setdefault(c,set()).add(h)
        if a!='none' and isinstance(abr,(float,int)) and abr>0: audios.add(round(abr))
    duration=info.get('duration')
    video=[{'start':int(c.get('start_time') or 0),'title':close_brackets(str(c.get('title') or 'Chapter'))} for c in info.get('chapters') or [] if c.get('start_time') is not None]
    description=chapter_rows(info.get('description'),duration)
    # yt-dlp may infer chapters from description. Mark matching sets as description, not video.
    same=bool(video and description and len(video)==len(description) and all(abs(a['start']-b['start'])<=2 for a,b in zip(video,description)))
    sources=[]
    if video and not same: sources.append({'id':'video','label':f'Video ({len(video)})','source':'video','chapters':video})
    if description: sources.append({'id':'description','label':f'Description ({len(description)})','source':'description','chapters':description})
    subs=sorted(set((info.get('subtitles') or {}).keys())|set((info.get('automatic_captions') or {}).keys()))
    ordered=[x for x in ('H.265','H.264','VP9','AV1','VP8') if x in codecs]+sorted(codecs-{'H.265','H.264','VP9','AV1','VP8'})
    return {'thumbnail':info.get('thumbnail') or '', 'title':info.get('title') or 'Untitled','duration':duration,'video':sorted(videos),'audio':sorted(audios),'codecs':ordered,'codec_heights':{k:sorted(v) for k,v in combos.items()},'subtitles':subs,'sources':sources,'id':info.get('id')}
def check_chapters(items,duration):
    if not isinstance(items,list) or len(items)>300: raise ValueError('Invalid chapter list')
    out=[]
    for row in items:
        start=int(row['start']); title=str(row['title']).strip()[:120]
        if start<0 or not title or (duration and start>=duration) or (out and start<=out[-1]['start']): raise ValueError('Chapters must be chronological and within video duration')
        out.append({'start':start,'title':close_brackets(title)})
    return out
def video_format(job):
    info=extract(job['url'])
    job['_format_info']=info
    height=int(job['video']); codec=str(job['codec'])
    formats=info.get('formats') or []
    videos=[f for f in formats if f.get('format_id') and f.get('vcodec') not in (None,'none')
            and f.get('height')==height and codec_name(str(f['vcodec']))==codec]
    if not videos: raise ValueError(f'No video format for {height}p / {codec}')
    def https_first(f):
        protocol=str(f.get('protocol') or '').lower()
        direct=protocol in ('https','http')
        return (0 if direct else 1, 0 if f.get('acodec') in (None,'none') else 1,
                -(f.get('fps') or 0), -(f.get('tbr') or 0))
    videos.sort(key=https_first)
    audio_target=int(job['audio']) if job.get('audio') else None
    audios=[f for f in formats if f.get('format_id') and f.get('acodec') not in (None,'none')
            and f.get('vcodec') in (None,'none')]
    audios.sort(key=lambda f:(0 if str(f.get('protocol') or '').lower() in ('https','http') else 1,
               abs((f.get('abr') or 0)-(audio_target or (f.get('abr') or 0))),
               -(f.get('abr') or 0)))
    # An audio stream may not match the reported rounded bitrate exactly.
    if not audios:
        combined=[f for f in videos if f.get('acodec') not in (None,'none')]
        if combined: return str(combined[0]['format_id'])
        raise ValueError('No audio-only stream available')
    return str(videos[0]['format_id'])+'+'+str(audios[0]['format_id'])

def ffmetadata(job):
    p=ROOT/('chapters-'+job['id']+'.ffmeta'); lines=[';FFMETADATA1']; rows=job['chapters']
    for i,c in enumerate(rows):
        end=rows[i+1]['start'] if i+1<len(rows) else int(job.get('duration') or c['start']+1)
        if end<=c['start']: continue
        title=c['title'].replace('\\','\\\\').replace('=','\\=').replace(';','\\;').replace('#','\\#').replace('\n',' ')
        lines+=['[CHAPTER]','TIMEBASE=1/1000',f'START={c["start"]*1000}',f'END={end*1000}',f'title={title}']
    p.write_text('\n'.join(lines)+'\n'); return p
def friendly_download_error(text):
    msg=str(text or '')
    low=msg.lower()
    if 'no space left on device' in low or 'insufficient disk space' in low:
        return 'Insufficient disk space'
    if 'http error 429' in low: return 'Rate limit reached (HTTP 429)'
    if 'http error 403' in low: return 'Access denied by video source (HTTP 403)'
    if 'requested format is not available' in low or 'no video format' in low:
        return 'Selected video format unavailable'
    if 'network is unreachable' in low or 'connection timed out' in low:
        return 'Network connection interrupted'
    if 'ffmpeg' in low and ('error' in low or 'failed' in low):
        return 'Video processing failed'
    return msg[:240] or 'Download failed; see app logs'

def monitor_partial_files(job,stop):
    from pathlib import Path
    import shutil,time
    folder=Path(job['directory'])/job['save_as']
    stem=job['save_as']+'.'
    ids=[x for x in str(job.get('format_ids') or '').split('+') if x]
    highwater={fid:0 for fid in ids}
    previous=0
    last=time.monotonic()
    smoothed=None
    while not stop.wait(3):
        try:
            if not folder.is_dir(): continue
            free=shutil.disk_usage(folder).free
            files=list(folder.iterdir())
            active=[]
            for fid in ids:
                prefix=stem+'f'+fid+'.'
                sizes=[]
                for path in files:
                    if not path.is_file() or not path.name.startswith(prefix): continue
                    name=path.name
                    if '.part-Frag' in name or name.endswith('.ytdl'): continue
                    if name.endswith('.part') or ('.part' not in name and not name.endswith('.tmp')):
                        sizes.append(path.stat().st_size)
                        if name.endswith('.part'): active.append(fid)
                if sizes: highwater[fid]=max(highwater[fid],max(sizes))
            downloaded=sum(highwater.values())
            timestamp=time.monotonic()
            interval=max(.01,timestamp-last)
            instantaneous=max(0,downloaded-previous)/interval
            last=timestamp
            previous=downloaded
            if instantaneous>1024:
                smoothed=instantaneous if smoothed is None else smoothed*.65+instantaneous*.35
            with LOCK:
                if job.get('state') not in ('downloading','processing'): return
                if free<100*1000000:
                    job['message']='Insufficient disk space'
                    job['disk_space_warning']=True
                    job['updated']=now()
                    save()
                    proc=ACTIVE.get(job['id'])
                    if proc is not None:
                        try: proc.terminate()
                        except OSError: pass
                    return
                if downloaded:
                    job['downloaded_mb']=round(max(float(job.get('downloaded_mb') or 0),downloaded/1000000),1)
                    total=job.get('total_mb')
                    if isinstance(total,(int,float)) and total>0:
                        percent=min(99.9,job['downloaded_mb']/total*100)
                        job['progress']=round(max(float(job.get('progress') or 0),percent),1)
                        if smoothed and smoothed>1024:
                            remaining=max(0,total*1000000-downloaded)
                            job['eta']=str(int(remaining/smoothed))+' s'
                    if smoothed and smoothed>1024:
                        job['speed']=f'{smoothed/1000000:.2f} MB/s'
                    if active:
                        job['message']='Downloading video' if active[0]==ids[0] else 'Downloading audio'
                    job['updated']=now()
                    save()
        except (OSError,ValueError,TypeError) as exc:
            print('Progress monitor:',exc,flush=True)

def estimate_job_size(job,info):
    ids=str(job.get('format_ids') or '').split('+')
    formats={str(f.get('format_id')):f for f in (info.get('formats') or [])}
    duration=info.get('duration') or job.get('duration')
    values=[]
    for fid in ids:
        f=formats.get(fid)
        if not f: return None
        size=f.get('filesize') or f.get('filesize_approx')
        if not size:
            bitrate=f.get('tbr') or f.get('vbr') or f.get('abr')
            if not bitrate or not duration: return None
            size=float(bitrate)*1000*float(duration)/8
        values.append(float(size))
    return round(sum(values)/1000000,1) if values else None

def is_subtitle_error(message):
    text=str(message).lower()
    return ('subtitle' in text or 'caption' in text) and any(x in text for x in (
        'unable to download', 'error downloading', 'failed to download'))

def without_subtitles(command):
    # Only remove flags added for subtitle downloading/embedding.
    result=[]; i=0
    while i<len(command):
        if command[i] in ('--write-subs','--write-auto-subs','--embed-subs'):
            i+=1; continue
        if command[i]=='--sub-langs':
            i+=2; continue
        result.append(command[i]); i+=1
    return result

def worker(job):
    try:
        folder=allowed_dir(job['directory'])
        import shutil
        if shutil.disk_usage(folder).free < 150*1000000:
            raise RuntimeError('Insufficient disk space')

        with LOCK:
            if job['state']=='cancelled': return
            job.update(state='downloading',message='Starting download',updated=now()); save()
        out=str(folder/job['save_as']/(job['save_as']+'.%(ext)s'))
        selected_format=video_format(job)
        with LOCK: job['format_ids']=selected_format; job['message']='Downloading video'; job['total_mb']=estimate_job_size(job,job.pop('_format_info',{})); job['downloaded_mb']=0.0; save()
        cmd=['python3','-m','yt_dlp','--newline','--continue','--no-playlist','--js-runtimes','deno','--no-write-thumbnail','--merge-output-format','mkv','-f',selected_format,'-o',out,'--print','after_move:filepath:%(filepath)s','--progress-template','download:YTDL_PROGRESS:%(progress.downloaded_bytes)s:%(progress.total_bytes)s:%(progress.total_bytes_estimate)s:%(progress.speed)s:%(progress.eta)s']
        if job['subtitle']!='None': cmd+=['--write-subs','--write-auto-subs','--sub-langs',job['subtitle'],'--embed-subs']
        # Prevent original chapters from being embedded if user explicitly ignored them.
        if job['chapters']: cmd+=['--embed-chapters']
        cmd.append(job['url'])
        stop_monitor=threading.Event()
        threading.Thread(target=monitor_partial_files,args=(job,stop_monitor),daemon=True).start()
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,start_new_session=True)
        with LOCK: ACTIVE[job['id']]=proc
        final=None; err=''; subtitles_seen=False
        for line in proc.stdout:
            line=line.strip()
            if not line: continue
            print(line[:400],flush=True)
            if line.startswith('filepath:'): final=line[9:]
            if False and line.startswith('YTDL_PROGRESS:'):
                fields=line[len('YTDL_PROGRESS:'):].split(':')
                if len(fields)>=5:
                    def number(x):
                        try: return float(x) if x not in ('None','NA','') else None
                        except (ValueError,TypeError): return None
                    downloaded,total,estimate,speed,eta=map(number,fields[:5])
                    with LOCK:
                        if downloaded is not None:
                            job['downloaded_mb']=max(job.get('downloaded_mb') or 0,round(downloaded/1000000,1))
                        expected=total or estimate
                        if expected and expected>0:
                            job['total_mb']=round(expected/1000000,1)
                            if downloaded is not None: job['progress']=round(min(100,downloaded/expected*100),1)
                        if speed is not None: job['speed']=f'{speed/1000000:.2f} MB/s'
                        if eta is not None: job['eta']=str(int(eta))+' s'
                        job['updated']=now()
                        save()
                continue

            if '[EmbedSubtitle]' in line: subtitles_seen=True
            if '[Merger]' in line or '[VideoRemuxer]' in line:
                with LOCK: job['message']='Merging video and audio'; save()
            if '[EmbedSubtitle]' in line or '[EmbedChapters]' in line:
                with LOCK: job['message']='Embedding subtitles or chapters'; save()
            m=re.search(r'\[download\]\s+(\d+(?:\.\d+)?)%',line)
            with LOCK:
                if m: job['stream_progress']=float(m.group(1))
                if ' ETA ' in line: job['eta']=line.rsplit(' ETA ',1)[-1].split()[0]
                if ' at ' in line: job['speed']=line.rsplit(' at ',1)[-1].split(' ETA')[0][:45]
                if line.startswith('ERROR:'): err=line[:250]
        rc=proc.wait()
        with LOCK: cancelled=job['state']=='cancelling'
        if cancelled: raise RuntimeError('Cancelled by user')
        if rc and not cancelled and job.get('subtitle')!='None' and is_subtitle_error(err):
            # One fallback attempt without subtitles. Preserve video/audio .part files.
            with LOCK:
                job['subtitle_failed']=True
                job['subtitle_error']=err[:240]
                job['message']='Subtitles unavailable; continuing without subtitles'
                save()
            retry_cmd=without_subtitles(cmd)
            retry_proc=subprocess.Popen(retry_cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                        text=True,bufsize=1,start_new_session=True)
            with LOCK: ACTIVE[job['id']]=retry_proc
            retry_error=''
            for retry_line in retry_proc.stdout:
                retry_line=retry_line.strip()
                if retry_line.startswith('filepath:'): final=retry_line[9:]
                if retry_line.startswith('ERROR:'): retry_error=retry_line[:250]
                if retry_line: print(retry_line[:400],flush=True)
            rc=retry_proc.wait()
            with LOCK: cancelled=job.get('state')=='cancelling'
            if cancelled: raise RuntimeError('Cancelled by user')
            if rc: err=retry_error or 'Video/audio retry failed after subtitle error'
        if rc: raise RuntimeError(err or f'yt-dlp exited with {rc}')
        chapter_embedded=False
        if job['chapters'] and final and Path(final).is_file():
            with LOCK: job['message']='Embedding chapters'; save()
            original=Path(final); meta=ffmetadata(job); tmp=original.with_name(original.stem+'.chaptertemp'+original.suffix)
            run=subprocess.run(['ffmpeg','-nostdin','-y','-i',str(original),'-i',str(meta),'-map','0','-map_metadata','0','-map_chapters','1','-c','copy',str(tmp)],capture_output=True,text=True)
            if run.returncode==0 and tmp.is_file(): os.replace(tmp,original); chapter_embedded=True
            else: tmp.unlink(missing_ok=True)
            meta.unlink(missing_ok=True)
        with LOCK:
            if final and Path(final).is_file():
                final_bytes=Path(final).stat().st_size
                final_mb=round(final_bytes/1000000,1)
                job['final_size_bytes']=final_bytes
                job['downloaded_mb']=final_mb
                job['total_mb']=final_mb
                job['message']='Completed'
            job.update(state='completed',progress=100,message='Completed' if not job['chapters'] or chapter_embedded else 'Completed; chapters could not be embedded',finished=now(),updated=now(),subtitles_embedded=(subtitles_seen and not job.get('subtitle_failed')),chapters_embedded=chapter_embedded,next_retry=None); save()
    except Exception as exc:
        with LOCK:
            cancelled=job.get('state')=='cancelling' or str(exc)=='Cancelled by user'
            retry_count=job.get('retries',0)
            if cancelled: job.update(state='cancelled',message='Cancelled',next_retry=None)
            elif retry_count<3: job.update(state='retry_wait',message=str(exc)[:200],next_retry=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat(),retries=retry_count+1)
            else: job.update(state='interrupted',message=str(exc)[:200],next_retry=None)
            job.update(updated=now(),finished=now()); save()
    finally:
        if 'stop_monitor' in locals(): stop_monitor.set()
        with LOCK: ACTIVE.pop(job['id'],None)
def queue_job(data,scheduled=False):
    url=str(data.get('url','')).strip()
    if not valid_url(url): raise ValueError('Invalid YouTube URL')
    with LOCK:
        info=METADATA.get(url)
        if not info: raise ValueError('Analyze URL first')
        video=int(data.get('video')); audio=int(data.get('audio')) if data.get('audio') is not None else None
        codec=str(data.get('codec')); sub=str(data.get('subtitle','None'))
        if video not in info['video']: raise ValueError('Video quality unavailable')
        if audio is not None and audio not in info['audio']: raise ValueError('Audio quality unavailable')
        if codec not in info['codecs']: raise ValueError('Codec unavailable')
        if video not in info['codec_heights'].get(codec,[]): raise ValueError('Selected codec is unavailable at selected resolution')
        if sub!='None' and sub not in info['subtitles']: raise ValueError('Subtitle unavailable')
        chapters=check_chapters(data.get('chapters') or [],info['duration'])
        directory=str(allowed_dir(data.get('directory') or DEFAULT))
        name=clean_name(data.get('save_as') or info['title'])
        schedule=None
        if scheduled:
            m=re.fullmatch(r'(\d{2}):(\d{2})',str(data.get('time','')))
            if not m or int(m[1])>23 or int(m[2])>59: raise ValueError('Invalid schedule time')
            local=datetime.now(TZ); target=local.replace(hour=int(m[1]),minute=int(m[2]),second=0,microsecond=0)
            if target<=local: target+=timedelta(days=1)
            schedule=target.astimezone(timezone.utc).isoformat()
        job={'id':str(uuid.uuid4()),'url':url,'title':info['title'],'thumbnail':info.get('thumbnail') or '', 'save_as':name,'directory':directory,'duration':info['duration'],'video':video,'audio':audio,'codec':codec,'subtitle':sub,'chapters':chapters,'chapter_source':str(data.get('chapter_source','')) if chapters else '', 'state':'scheduled' if scheduled else 'queued','scheduled_for':schedule,'progress':0,'speed':'','eta':'','message':'Scheduled' if scheduled else 'Queued','started':now(),'updated':now(),'finished':None,'retries':0,'next_retry':None,'subtitles_embedded':False,'subtitle_failed':False,'subtitle_error':'','chapters_embedded':False}
        job['queue_rank']=max((int(x.get('queue_rank',i)) for i,x in enumerate(JOBS)),default=-1)+1
        JOBS.append(job); save()
        PREF.write_text(json.dumps({'directory':directory}))
        return job
def scheduler():
    while True:
        try:
            with LOCK:
                busy=bool(ACTIVE) or any(j['state'] in ('processing','downloading','cancelling') for j in JOBS)
                if not busy:
                    utc=datetime.now(timezone.utc)
                    ready=[]
                    for j in JOBS:
                        if j['state']=='queued': ready.append(j)
                        elif j['state']=='scheduled' and j.get('scheduled_for') and datetime.fromisoformat(j['scheduled_for'])<=utc: ready.append(j)
                        elif j['state']=='retry_wait' and j.get('next_retry') and datetime.fromisoformat(j['next_retry'])<=utc: ready.append(j)
                    if ready:
                        ready.sort(key=lambda j:(int(j.get('queue_rank',JOBS.index(j))),j['started']))
                        job=ready[0]; job['state']='processing'; save(); threading.Thread(target=worker,args=(job,),daemon=True).start()
        except Exception as exc: print('Scheduler:',exc,flush=True)
        time.sleep(2)
threading.Thread(target=scheduler,daemon=True).start()
class Handler(BaseHTTPRequestHandler):
    def allowed(self): return self.client_address[0] in ('127.0.0.1','::1','172.30.32.2')
    def log_message(self,*args): pass
    def reply(self,code,obj):
        body=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def body(self):
        size=int(self.headers.get('Content-Length','0'))
        if size<1 or size>100000: raise ValueError('Invalid request size')
        obj=json.loads(self.rfile.read(size))
        if not isinstance(obj,dict): raise ValueError('Expected JSON object')
        return obj
    def do_GET(self):
        if not self.allowed(): self.reply(403,{'error':'Ingress access only'}); return
        path=self.path.split('?',1)[0]
        if path in ('/','/index.html'):
            b=UI.read_bytes(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
        elif path=='/health': self.reply(200,{'status':'ok','version':VERSION,'storage_available':DEFAULT.is_dir()})
        elif path=='/jobs':
            with LOCK: rows=sorted(JOBS,key=lambda j:(0 if j['state'] in ('downloading','processing','cancelling') else 1 if j['state'] in QUEUE_STATES else 2, int(j.get('queue_rank',JOBS.index(j))) if j['state'] in QUEUE_STATES else -datetime.fromisoformat(j['started']).timestamp()))[:20]
            self.reply(200,rows)
        elif path=='/timezone': self.reply(200,{'timezone':str(TZ)})
        elif path=='/preferences':
            try: prefs=json.loads(PREF.read_text())
            except Exception: prefs={'directory':str(DEFAULT)}
            self.reply(200,prefs)
        else: self.reply(404,{'error':'Not found'})
    def do_POST(self):
        if not self.allowed(): self.reply(403,{'error':'Ingress access only'}); return
        try:
            data=self.body(); path=self.path.split('?',1)[0]
            if path=='/analyze':
                url=str(data.get('url','')).strip()
                if not valid_url(url): raise ValueError('Invalid URL')
                raw=extract(url)
                if raw.get('_type') in ('playlist','multi_video') or raw.get('entries') is not None:
                    raise ValueError('Playlists and multi-video collections are not supported')
                formats=raw.get('formats') or []
                if not any(f.get('vcodec') not in (None,'none') for f in formats): raise ValueError('No video stream available')
                if not any(f.get('acodec') not in (None,'none') for f in formats): raise ValueError('No audio stream available')
                info=analyze_info(raw); METADATA[url]=info; FORMAT_DETAILS[url]=raw.get('formats') or []; SEARCH[url]={'seen':set(),'limit':0,'candidates':[],'limit_reached':False}
                self.reply(200,info)
            elif path=='/estimate':
                url=str(data.get('url','')).strip()
                if url not in METADATA: raise ValueError('Analyze URL first')
                video=int(data.get('video',0)); codec=str(data.get('codec','')); audio=int(data.get('audio',0))
                formats=FORMAT_DETAILS.get(url,[])
                vids=[f for f in formats if f.get('vcodec') not in ('none',None) and f.get('height')==video and codec_name(f['vcodec'])==codec]
                auds=[f for f in formats if f.get('acodec') not in ('none',None) and f.get('vcodec')=='none' and isinstance(f.get('abr'),(float,int))]
                def size(f):
                    for field in ('filesize','filesize_approx'):
                        n=f.get(field)
                        if isinstance(n,(float,int)) and n>0: return (float(n),field=='filesize')
                    bitrate=f.get('tbr') or f.get('vbr') or f.get('abr')
                    duration=METADATA[url].get('duration')
                    if isinstance(bitrate,(int,float)) and bitrate>0 and isinstance(duration,(int,float)) and duration>0:
                        return (float(bitrate)*1000*duration/8,False)
                    return (None,False)
                # Prefer video-only and audio-only streams, matching normal yt-dlp merging.
                vids.sort(key=lambda f:(f.get('acodec')=='none',f.get('tbr') or 0),reverse=True)
                auds.sort(key=lambda f:abs((f.get('abr') or 0)-audio))
                if not vids: raise ValueError('Selected video stream unavailable')
                v=vids[0]; a=auds[0] if auds else None
                vs,vexact=size(v); ass,aexact=size(a) if a else (0,True)
                if vs is None or ass is None:
                    self.reply(200,{'size_mb':None,'estimated':True}); return
                total=vs+ass
                self.reply(200,{'size_mb':round(total/1000000,1),'estimated':not(vexact and aexact)})
            elif path=='/comments':
                url=data.get('url')
                if url not in METADATA: raise ValueError('Analyze first')
                cache=SEARCH.setdefault(url,{'seen':set(),'limit':0,'candidates':[],'limit_reached':False})
                if cache['limit_reached']: self.reply(200,{'candidates':cache['candidates'],'limit_reached':True,'checked':cache['limit']}); return
                limit=min(cache['limit']+100,10000)
                info=extract(url,True,limit)
                for c in info.get('comments') or []:
                    cid=str(c.get('id') or '')
                    if not cid or cid in cache['seen']: continue
                    cache['seen'].add(cid)
                    chapters=chapter_rows(c.get('text'),METADATA[url]['duration'])
                    if chapters: cache['candidates'].append({'id':'comment-'+cid,'label':f'Comment {len(cache["candidates"])+1} ({len(chapters)})','source':'comments','chapters':chapters,'author':c.get('author') or 'unknown','date':c.get('timestamp')})
                cache['limit']=limit; cache['limit_reached']=limit>=10000 or len(info.get('comments') or [])<limit
                self.reply(200,{'candidates':cache['candidates'],'limit_reached':cache['limit_reached'],'checked':cache['limit']})
            elif path=='/folders':
                folder=allowed_dir(data.get('path','/media'))
                children=[]
                try:
                    for x in folder.iterdir():
                        if x.is_dir() and not x.is_symlink(): children.append(x.name)
                except OSError as exc: raise ValueError(str(exc))
                parent=folder.parent if str(folder)!='/media' else folder
                self.reply(200,{'path':str(folder),'parent':str(parent),'folders':sorted(children,key=str.casefold)[:300]})
            elif path=='/download': self.reply(202,queue_job(data))
            elif path=='/schedule': self.reply(202,queue_job(data,True))
            elif path=='/cancel':
                with LOCK:
                    job=next((j for j in JOBS if j['id']==data.get('id')),None)
                    if not job or job['state'] not in RUNNING|{'scheduled','retry_wait'}: raise ValueError('Job not cancellable')
                    proc=ACTIVE.get(job['id']); job['state']='cancelling' if proc else 'cancelled'; job['next_retry']=None; save()
                if proc and proc.poll() is None: os.killpg(proc.pid,signal.SIGTERM)
                self.reply(200,{'ok':True})
            elif path=='/reorder':
                jid=str(data.get('id','')); direction=str(data.get('direction',''))
                if direction not in ('up','down'): raise ValueError('Invalid direction')
                with LOCK:
                    ordered=sorted((j for i,j in enumerate(JOBS) if j.get('state') in QUEUE_STATES),key=lambda j:(int(j.get('queue_rank',JOBS.index(j))),j['started']))
                    pos=next((i for i,j in enumerate(ordered) if j.get('id')==jid),None)
                    if pos is None: raise ValueError('Job is not waiting')
                    target=pos+(-1 if direction=='up' else 1)
                    if target<0 or target>=len(ordered): raise ValueError('Already at queue boundary')
                    ordered[pos],ordered[target]=ordered[target],ordered[pos]
                    for i,j in enumerate(ordered): j['queue_rank']=i
                    save()
                self.reply(200,{'ok':True})
            elif path=='/delete':
                jid=str(data.get('id',''))
                with LOCK:
                    job=next((j for j in JOBS if j.get('id')==jid),None)
                    if job is None: raise ValueError('Job not found')
                    if job.get('state') in ('downloading','processing','cancelling') or jid in ACTIVE:
                        raise ValueError('Cancel the active download and wait before deleting its history')
                    JOBS.remove(job)
                    save()
                self.reply(200,{'ok':True})
            elif path=='/resume':
                with LOCK:
                    job=next((j for j in JOBS if j['id']==data.get('id')),None)
                    if not job or job['state'] not in ('interrupted','cancelled','retry_wait'): raise ValueError('Cannot resume')
                    job.update(state='queued',next_retry=None,retries=0,message='Queued to resume',finished=None); save()
                self.reply(202,{'ok':True})
            else: self.reply(404,{'error':'Not found'})
        except RuntimeError as exc: self.reply(409,{'error':str(exc)})
        except Exception as exc: self.reply(400,{'error':str(exc)[:300]})
print('YTDL Manager',VERSION,'ready; storage:',DEFAULT.is_dir(),flush=True)
# YTDL_SEARCH_110_DEV
import json as _search_json
import search_engine as _search_engine
from urllib.parse import urlsplit as _search_urlsplit
_original_search_post=Handler.do_POST
_search_state=_search_engine.SearchState()
def _search_do_POST(self):
    path=_search_urlsplit(self.path).path
    if path not in ('/search','/search/quality'):return _original_search_post(self)
    try:
        length=int(self.headers.get('Content-Length','0'))
        if not 0<length<=8192:raise ValueError('Invalid request size')
        data=_search_json.loads(self.rfile.read(length))
        if path=='/search':
            query,providers,minimum,minutes,count,offset,sort=_search_engine.validate_options(data)
            groups={};warnings=[]
            for provider in providers:
                if not _search_state.allowed(provider):warnings.append(provider+': rate limited');groups[provider]=[];continue
                try:groups[provider]=[x for x in _search_engine.extract_search(query,provider,count,offset) if _search_engine.duration_ok(x.get('duration'),minutes)]
                except Exception as exc:
                    kind=_search_engine.classify_error(exc);warnings.append(provider+': '+kind);groups[provider]=[]
                    if kind=='RATE_LIMIT':_search_state.block(provider)
            items=_search_engine.sort_results(_search_engine.merge_round_robin(groups),sort)
            payload={'results':items,'next_offset':offset+count,'providers':list(_search_engine.PROVIDERS),'warnings':warnings,'min_quality':minimum}
        else:
            if not _search_state.allowed('YouTube'):raise ValueError('Quality checks paused after rate limit')
            try:payload=_search_engine.verify_quality(data.get('url'))
            except Exception as exc:
                if _search_engine.classify_error(exc)=='RATE_LIMIT':_search_state.block('YouTube')
                raise
        raw=_search_json.dumps(payload,ensure_ascii=False).encode()
        self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    except Exception as exc:
        raw=_search_json.dumps({'error':str(exc)[:300]}).encode()
        self.send_response(400);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
Handler.do_POST=_search_do_POST

ThreadingHTTPServer(('0.0.0.0',8765),Handler).serve_forever()
