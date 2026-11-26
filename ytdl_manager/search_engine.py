"""YouTube-only search helper for YTDL Manager DEV. Video URL downloads remain multi-site."""
from urllib.parse import urlparse
import time

PROVIDERS={'YouTube':'ytsearch'}
QUALITIES=(0,720,1080,1440,2160)
SORTS=('relevance','newest','oldest','most_viewed','longest','shortest','highest_quality')
MAX_CHECKS=20
COOLDOWN_SECONDS=3600
class SearchState:
    def __init__(self):self.cooldowns={};self.quality_cache={}
    def allowed(self,provider='YouTube',now=None):
        now=time.monotonic() if now is None else now
        return now>=self.cooldowns.get('YouTube',0)
    def block(self,provider='YouTube',now=None):
        now=time.monotonic() if now is None else now
        self.cooldowns['YouTube']=now+COOLDOWN_SECONDS

def available_providers(extractor_classes=None):
    if extractor_classes is None:
        try:
            from yt_dlp.extractor import gen_extractor_classes
            extractor_classes=list(gen_extractor_classes())
        except ImportError:extractor_classes=[]
    return {'YouTube':'ytsearch'} if any(c.__name__=='YoutubeSearchIE' for c in extractor_classes) else {}

def normalize_query(query):
    if not isinstance(query,str) or not 1<=len(query.strip())<=200:raise ValueError('Search text must be 1-200 characters')
    return query.strip()
def validate_options(data):
    if not isinstance(data,dict):raise ValueError('Invalid request')
    query=normalize_query(data.get('query'))
    websites=data.get('websites',['YouTube'])
    if websites!=['YouTube']:raise ValueError('Only YouTube search is supported')
    minimum=int(data.get('min_quality',0))
    if minimum not in QUALITIES:raise ValueError('Invalid quality')
    duration=float(data.get('min_duration',0))
    if not 0<=duration<=10000:raise ValueError('Invalid duration')
    count=int(data.get('count',20));offset=int(data.get('offset',0))
    if count!=20 or not 0<=offset<=200:raise ValueError('Invalid pagination')
    sort=data.get('sort','relevance')
    if sort not in SORTS:raise ValueError('Invalid sorting')
    return query,['YouTube'],minimum,duration,count,offset,sort

def allowed_result_url(url,provider='YouTube'):
    if provider!='YouTube' or not isinstance(url,str) or not url.startswith('https://'):return False
    try:
        u=urlparse(url)
        return u.hostname in ('youtube.com','www.youtube.com','m.youtube.com','youtu.be') and not u.username and not u.password and u.port in (None,443)
    except ValueError:return False

def duration_ok(value,minimum):return minimum==0 or isinstance(value,(int,float)) and value>=minimum*60
def allowed_quality(value,minimum):return isinstance(value,(int,float)) and value>=minimum

def merge_round_robin(groups):
    return [dict(x,provider='YouTube') for x in groups.get('YouTube',[])]
def sort_results(rows,mode):
    if mode=='relevance':return list(rows)
    field={'newest':'timestamp','oldest':'timestamp','most_viewed':'view_count','longest':'duration','shortest':'duration','highest_quality':'quality'}[mode]
    return sorted(rows,key=lambda r:(r.get(field) is not None,r.get(field) or 0),reverse=mode not in ('oldest','shortest'))
def classify_error(exc):
    msg=str(exc).lower()
    if '429' in msg or 'too many requests' in msg or 'not a bot' in msg:return 'RATE_LIMIT'
    if '403' in msg:return 'ACCESS_DENIED'
    if 'timed out' in msg or 'timeout' in msg:return 'TIMEOUT'
    return 'OTHER'

def extract_search(query,provider,count,offset):
    if provider!='YouTube':raise ValueError('Only YouTube search is supported')
    import yt_dlp
    with yt_dlp.YoutubeDL({'quiet':True,'no_warnings':True,'extract_flat':'in_playlist','skip_download':True,'socket_timeout':12,'retries':0}) as y:
        info=y.extract_info(f'ytsearch{count+offset}:{query}',download=False)
    rows=[]
    for e in ((info or {}).get('entries') or [])[offset:offset+count]:
        if not isinstance(e,dict):continue
        url=e.get('webpage_url') or e.get('url') or ''
        if not allowed_result_url(url):continue
        rows.append({'title':e.get('title') or 'Untitled','url':url,'duration':e.get('duration'),'thumbnail':e.get('thumbnail'),'timestamp':e.get('timestamp'),'view_count':e.get('view_count'),'quality':None})
    return rows

def verify_quality(url,provider=None):
    if not allowed_result_url(url):raise ValueError('Unsupported quality URL')
    import yt_dlp
    with yt_dlp.YoutubeDL({'quiet':True,'no_warnings':True,'skip_download':True,'noplaylist':True,'socket_timeout':12,'retries':0}) as y:
        info=y.extract_info(url,download=False)
    fs=(info or {}).get('formats') or []
    heights=[f.get('height') for f in fs if f.get('vcodec') not in (None,'none') and isinstance(f.get('height'),int)]
    return {'height':max(heights) if heights else None,'codecs':sorted({str(f.get('vcodec')).split('.')[0] for f in fs if f.get('vcodec') not in (None,'none')})}

def auto_verify(rows,minimum,verify,limit=10,state=None,provider='YouTube'):
    if provider!='YouTube':raise ValueError('Only YouTube search is supported')
    state=state or SearchState();accepted=[];checked=0;errors=[]
    for row in rows:
        if checked>=MAX_CHECKS or (minimum==0 and checked>=limit) or (minimum>0 and len(accepted)>=limit):break
        if not state.allowed():errors.append('RATE_LIMIT');break
        url=row.get('url')
        if not allowed_result_url(url):continue
        if url in state.quality_cache:result=state.quality_cache[url]
        else:
            checked+=1
            try:result=verify(url);state.quality_cache[url]=result
            except Exception as exc:
                kind=classify_error(exc);errors.append(kind)
                if kind=='RATE_LIMIT':state.block();break
                continue
        height=result.get('height')
        if minimum==0 or allowed_quality(height,minimum):accepted.append(dict(row,quality=height,codecs=result.get('codecs',[])))
    return {'accepted':accepted,'checked':checked,'errors':errors,'remaining':max(0,len(rows)-checked)}
