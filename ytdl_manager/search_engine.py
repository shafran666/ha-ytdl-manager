"""Search helper for YTDL Manager. No authentication or direct downloads."""
import time
from urllib.parse import urlparse

QUALITIES=(0,720,1080,1440,2160)
PROVIDERS={'YouTube':'ytsearch'}

class RateLimited(Exception): pass

def merge_round_robin(groups):
    result=[]; keys=list(groups)
    for i in range(max((len(groups[k]) for k in keys),default=0)):
        for k in keys:
            if i<len(groups[k]): result.append(dict(groups[k][i],provider=k))
    return result

def allowed_quality(height,minimum):
    return height is not None and isinstance(height,(int,float)) and height>=minimum

def duration_ok(duration,minimum):
    return minimum<=0 or (isinstance(duration,(int,float)) and duration>=minimum*60)

def normalize_query(query):
    if not isinstance(query,str) or not query.strip() or len(query)>200:raise ValueError('Search text must contain 1-200 characters')
    return query.strip()

def validate_options(data):
    query=normalize_query(data.get('query'))
    providers=data.get('websites',['YouTube'])
    if not isinstance(providers,list) or not providers or any(p not in PROVIDERS for p in providers):raise ValueError('Unsupported search website')
    providers=list(dict.fromkeys(providers))
    minimum=int(data.get('min_quality',0))
    if minimum not in QUALITIES:raise ValueError('Invalid minimum quality')
    minutes=float(data.get('min_duration',0))
    if not 0<=minutes<=10000:raise ValueError('Invalid minimum duration')
    count=int(data.get('count',20)); offset=int(data.get('offset',0))
    if count!=20 or offset<0 or offset>200:raise ValueError('Invalid result window')
    return query,providers,minimum,minutes,count,offset

def extract_search(query,provider,count,offset):
    import yt_dlp
    prefix=PROVIDERS[provider]
    opts={'quiet':True,'no_warnings':True,'extract_flat':'in_playlist','skip_download':True,'noplaylist':False,'socket_timeout':12,'retries':0}
    with yt_dlp.YoutubeDL(opts) as y:
        info=y.extract_info(f'{prefix}{count+offset}:{query}',download=False)
    entries=(info or {}).get('entries') or []
    result=[]
    for e in entries[offset:offset+count]:
        if not isinstance(e,dict):continue
        url=e.get('webpage_url') or e.get('url') or ''
        if not str(url).startswith(('https://','http://')):continue
        result.append({'title':e.get('title') or 'Untitled','url':url,'duration':e.get('duration'),'thumbnail':e.get('thumbnail'),'id':e.get('id'),'quality':None})
    return result

def verify_quality(url):
    import yt_dlp
    if not isinstance(url,str) or not url.startswith('https://'):raise ValueError('Invalid video URL')
    host=(urlparse(url).hostname or '').lower()
    if host not in ('youtube.com','www.youtube.com','m.youtube.com','youtu.be'):raise ValueError('Unsupported quality-check domain')
    with yt_dlp.YoutubeDL({'quiet':True,'no_warnings':True,'skip_download':True,'noplaylist':True,'socket_timeout':12,'retries':0}) as y:
        info=y.extract_info(url,download=False)
    formats=(info or {}).get('formats') or []
    heights=[f.get('height') for f in formats if f.get('vcodec') not in ('none',None) and isinstance(f.get('height'),int)]
    return {'height':max(heights) if heights else None,'codecs':sorted({str(f.get('vcodec')).split('.')[0] for f in formats if f.get('vcodec') not in ('none',None)})}
