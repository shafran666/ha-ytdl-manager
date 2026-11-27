import ast
from urllib.parse import urlsplit
from pathlib import Path
src=Path('ytdl_manager/server.py').read_text()
node=next(n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='valid_url')
ns={'urlsplit':urlsplit}
exec(compile(ast.Module(body=[node],type_ignores=[]),'<test>','exec'),ns)
def test_accept_youtube():
    for u in ['https://www.youtube.com/watch?v=abc123','https://youtu.be/abc123','https://www.youtube.com/live/abc123','https://www.youtube.com/shorts/abc123']:
        assert ns['valid_url'](u),u
def test_reject_non_youtube():
    for u in ['https://vimeo.com/123','https://youtube.com.evil.test/watch?v=123','http://youtube.com/watch?v=123','https://youtube.com/playlist?list=123','https://127.0.0.1/watch?v=abc','https://youtube.com@evil.test/watch?v=abc']:
        assert not ns['valid_url'](u),u
