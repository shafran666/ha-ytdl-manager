import ast,json,subprocess
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'ytdl_manager/server.py').read_text()
TREE=ast.parse(SRC)
def helpers():
 names={'ytdl104_sidecar_snapshot','ytdl104_cleanup_embedded_sidecars'}
 nodes=[n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name in names]
 assign=next(n for n in TREE.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='YTDL104_SUB_EXTS' for t in n.targets))
 ns={'Path':Path}
 exec(compile(ast.Module(body=[assign,*nodes],type_ignores=[]),'<test>','exec'),ns)
 return ns
def test_remove_new_only_when_embedded(tmp_path):
 h=helpers();m=tmp_path/'Concert.mkv';m.write_bytes(b'fixture')
 old=tmp_path/'Concert.en.vtt';old.write_text('old')
 before=h['ytdl104_sidecar_snapshot'](tmp_path,'Concert')
 new=tmp_path/'Concert.eng.vtt';new.write_text('new')
 mock=subprocess.CompletedProcess([],0,json.dumps({'streams':[{'index':2,'codec_name':'webvtt','tags':{'language':'eng'}}]}),'')
 with patch('subprocess.run',return_value=mock):
  assert h['ytdl104_cleanup_embedded_sidecars'](m,before)==['Concert.eng.vtt']
 assert old.exists() and not new.exists()
def test_keep_new_if_no_embedded_subtitles(tmp_path):
 h=helpers();m=tmp_path/'Concert.mkv';m.write_bytes(b'fixture')
 f=tmp_path/'Concert.en.vtt';f.write_text('keep')
 mock=subprocess.CompletedProcess([],0,json.dumps({'streams':[]}),'')
 with patch('subprocess.run',return_value=mock):
  assert h['ytdl104_cleanup_embedded_sidecars'](m,set())==[]
 assert f.exists()
def test_no_auto_caption_download():
 assert "'--write-auto-subs'" not in SRC
 assert "info.get('automatic_captions')" not in SRC
