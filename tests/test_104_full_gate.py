import ast
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
SERVER=ROOT/'ytdl_manager/server.py'
SRC=SERVER.read_text()
TREE=ast.parse(SRC)
def url_check():
    fn=[n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name=='valid_url']
    assert len(fn)==1
    scope={'urlsplit':urlsplit}
    exec(compile(ast.Module(body=fn,type_ignores=[]),'<isolated-valid-url>','exec'),scope)
    return scope['valid_url']
def test_youtube_positive():
    fn=url_check()
    for url in ['https://youtube.com/watch?v=abc123','https://www.youtube.com/watch?v=abc123','https://youtu.be/abc123','https://youtube.com/shorts/abc123','https://youtube.com/live/abc123']:
        assert fn(url),url
def test_youtube_negative():
    fn=url_check()
    for url in ['https://vimeo.com/123','https://youtube.com.evil.test/watch?v=abc','http://youtube.com/watch?v=abc','https://youtube.com/playlist?list=abc','https://youtube.com@evil.test/watch?v=abc','file:///etc/passwd','https://127.0.0.1/watch?v=abc','https://youtube.com/watch']:
        assert not fn(url),url
def test_remux_requested():
    assert SRC.count("'--merge-output-format','mkv'")==1
    assert SRC.count("'--remux-video','mkv'")==1
def test_no_search_engine():
    assert not (ROOT/'ytdl_manager/search_engine.py').exists()
def test_no_conflicts():
    for p in [SERVER,ROOT/'ytdl_manager/Dockerfile',ROOT/'ytdl_manager/config.yaml']:
        t=p.read_text()
        assert '<<<<<<< HEAD' not in t and '>>>>>>> ' not in t
def test_changelog():
    assert '1.0.4-dev' in (ROOT/'ytdl_manager/CHANGELOG.md').read_text()
def test_docker_dependencies():
    t=(ROOT/'ytdl_manager/Dockerfile').read_text().lower()
    assert 'deno' in t and 'yt-dlp' in t and ('ejs' in t or 'default' in t)
def test_resume_and_no_playlist():
    assert '--continue' in SRC and '--no-playlist' in SRC
