import ast, pathlib, subprocess, json
from unittest.mock import patch
import pytest
ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=(ROOT/'ytdl_manager/server.py').read_text()
TREE=ast.parse(SRC)
def functions(*names):
    nodes=[n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert len(nodes)==len(names)
    ns={}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<helpers>','exec'),ns)
    return ns
@pytest.mark.parametrize('message,expected',[
 ('read timed out',True),('HTTP Error 429',True),('connection reset',True),
 ('HTTP Error 503',True),('signature challenge failed',True),
 ('Requested format is not available',False),('HTTP Error 403',False),
 ('Video unavailable',False),('No space left on device',False),
 ('invalid URL',False),('',False)])
def test_retry_classification(message,expected):
    assert functions('ytdl104_transient_error')['ytdl104_transient_error'](message)==expected
@pytest.mark.parametrize('container,types,expected',[
 ('matroska,webm',['video','audio'],True),('mov,mp4',['video','audio'],False),
 ('matroska',['video'],False),('matroska',['audio'],False),
 ('matroska',['video','audio','subtitle'],True)])
def test_ffprobe_contract(tmp_path,container,types,expected):
    file=tmp_path/'out.mkv';file.write_bytes(b'fixture')
    result=subprocess.CompletedProcess([],0,json.dumps({'format':{'format_name':container},'streams':[{'codec_type':x} for x in types]}),'')
    with patch('subprocess.run',return_value=result):
        fn=functions('ytdl104_validate_mkv')['ytdl104_validate_mkv']
        if expected:assert fn(file)
        else:
            with pytest.raises(RuntimeError):fn(file)
def test_missing_output_rejected(tmp_path):
    with pytest.raises(RuntimeError):functions('ytdl104_validate_mkv')['ytdl104_validate_mkv'](tmp_path/'missing.mkv')
def test_completion_requires_validation():
    assert '# YTDL_104_FINAL_MKV_GATE' in SRC
    assert "'--remux-video','mkv'" in SRC
