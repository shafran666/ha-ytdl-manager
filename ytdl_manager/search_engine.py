"""Safe, bounded search support for YTDL Manager DEV.

Only providers with a verified search extractor are enabled. Full media URL
support in the downloader is independent of title search provider support.
"""
from collections import deque
from urllib.parse import urlparse
import time

QUALITIES=(0,720,1080,1440,2160)
PROVIDERS={'YouTube':'ytsearch'}
SORTS=('relevance','newest','oldest','most_viewed','longest','shortest','highest_quality')
MAX_CHECKS=20
COOLDOWN_SECONDS=3600
class RateLimited(Exception): pass
class SearchState:
    def __init__(self):
        self.cooldowns={}
        self.quality_cache={}
    def allowed(self,provider,now=None):
        now=time.monotonic() if now is None else now
        return now>=self.cooldowns.get(provider,0)
    def block(self,provider,now=None):
        now=time.monotonic() if now is None else now
        self.cooldowns[provider]=now+COOLDOWN_SECONDS

def normalize_query(query):
    if not isinstance(query,str) or not 1<=len(query.strip())<=200:raise ValueError('Search query must be 1-200 characters')
    return query.strip()
def validate_options(data):
    if not isinstance(data,dict):raise ValueError('Invalid search request')
    query=normalize_query(data.get('query'))
    websites=data.get('websites',['YouTube'])
    if not isinstance(websites,list) or not websites or any(w not in PROVIDERS for w in websites):raise ValueError('Unsupported search website')
    websites=list(dict.fromkeys(websites))
    minimum=int(data.get('min_quality',0))
    if minimum not in QUALITIES:raise ValueError('Invalid minimum quality')
    duration=float(data.get('min_duration',0))
    if not 0<=duration<=10000:raise ValueError('Invalid minimum duration')
    count=int(data.get('count',20));offset=int(data.get('offset',0))
    if count!=20 or not 0<=offset<=200:raise ValueError('Invalid result window')
    sort=data.get('sort','relevance')
    if sort not in SORTS:raise ValueError('Invalid sorting')
    return query,websites,minimum,duration,count,offset,sort

def duration_ok(value,minimum):
    return minimum==0 or (isinstance(value,(int,float)) and value>=minimum*60)
def allowed_quality(value,minimum):
    return isinstance(value,(int,float)) and value>=minimum
def merge_round_robin(groups):
    keys=list(groups);out=[]
    for index in range(max((len(groups[k]) for k in keys),default=0)):
        for key in keys:
            if index<len(groups[key]):out.append(dict(groups[key][index],provider=key))
    return out
def sort_results(rows,mode):
    if mode=='relevance':return list(rows)
    field={'newest':'timestamp','oldest':'timestamp','most_viewed':'view_count','longest':'duration','shortest':'duration','highest_quality':'quality'}[mode]
    reverse=mode not in ('oldest','shortest')
    return sorted(rows,key=lambda r:(r.get(field) is not None,r.get(field) or 0),reverse=reverse)
def classify_error(exc):
    msg=str(exc).lower()
    if '429' in msg or 'too many requests' in msg or 'not a bot' in msg:return 'RATE_LIMIT'
    if '403' in msg:return 'ACCESS_DENIED'
    if 'timed out' in msg or 'timeout' in msg:return 'TIMEOUT'
    return 'OTHER'
def extract_search(query,provider,count,offset):
    import yt_dlp
    if provider not in PROVIDERS:raise ValueError('Unsupported provider')
    with yt_dlp.YoutubeDL({'quiet':True,'no_warnings':True,'extract_flat':'in_playlist','skip_download':True,'socket_timeout':12,'retries':0}) as y:
        info=y.extract_info(f'{PROVIDERS[provider]}{count+offset}:{query}',download=False)
    out=[]
    for e in ((info or {}).get('entries') or [])[offset:offset+count]:
        if not isinstance(e,dict):continue
        url=e.get('webpage_url') or e.get('url') or ''
        if not isinstance(url,str) or not url.startswith('https://'):continue
        out.append({'title':e.get('title') or 'Untitled','url':url,'duration':e.get('duration'),'thumbnail':e.get('thumbnail'),'timestamp':e.get('timestamp'),'view_count':e.get('view_count'),'quality':None})
    return out
def verify_quality(url):
    import yt_dlp
    if not isinstance(url,str) or not url.startswith('https://'):raise ValueError('Invalid URL')
    if (urlparse(url).hostname or '').lower() not in ('youtube.com','www.youtube.com','m.youtube.com','youtu.be'):raise ValueError('Unsupported quality domain')
    with yt_dlp.YoutubeDL({'quiet':True,'no_warnings':True,'skip_download':True,'noplaylist':True,'socket_timeout':12,'retries':0}) as y:
        info=y.extract_info(url,download=False)
    formats=(info or {}).get('formats') or []
    heights=[f.get('height') for f in formats if f.get('vcodec') not in (None,'none') and isinstance(f.get('height'),int)]
    return {'height':max(heights) if heights else None,'codecs':sorted({str(f.get('vcodec')).split('.')[0] for f in formats if f.get('vcodec') not in (None,'none')})}

def auto_verify(rows,minimum,verify,limit=10,state=None,provider='YouTube'):
    state=state or SearchState()
    accepted=[];checked=0;errors=[];skipped=0
    for row in rows:
        if checked>=MAX_CHECKS or (minimum==0 and checked>=limit) or (minimum>0 and len(accepted)>=limit):break
        if not state.allowed(provider):errors.append('RATE_LIMIT');break
        url=row.get('url')
        if not isinstance(url,str) or not url.startswith('https://'):
            skipped+=1;continue
        if url in state.quality_cache:
            result=state.quality_cache[url]
        else:
            checked+=1
            try:
                result=verify(url)
                state.quality_cache[url]=result
            except Exception as exc:
                kind=classify_error(exc);errors.append(kind)
                if kind=='RATE_LIMIT':state.block(provider);break
                continue
        height=result.get('height')
        updated=dict(row,quality=height,codecs=result.get('codecs',[]))
        if minimum==0 or allowed_quality(height,minimum):accepted.append(updated)
    return {'accepted':accepted,'checked':checked,'errors':errors,'skipped':skipped,'remaining':max(0,len(rows)-checked-skipped)}
