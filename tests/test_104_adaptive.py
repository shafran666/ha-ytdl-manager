import ast, pathlib
import pytest
from unittest.mock import patch
SRC=(pathlib.Path(__file__).resolve().parents[1]/'ytdl_manager/server.py').read_text()
TREE=ast.parse(SRC)
def functions(*names):
    nodes=[n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert len(nodes)==len(names)
    scope={}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<helpers>','exec'),scope)
    return scope
@pytest.mark.parametrize('downloaded,total,speed,pct,mb,eta',[
 (0,1000,100,0.0,0.0,10),
 (500,1000,100,50.0,0.0,5),
 (1000,1000,100,100.0,0.0,0),
 (1500,1000,100,100.0,0.0,0),
 (5242880,10485760,1048576,50.0,5.0,5),
 (0,None,None,None,0.0,None),
 (-100,-1,-5,None,0.0,None),
 ('bad','bad','bad',None,0.0,None),
 (float('inf'),float('inf'),float('inf'),None,0.0,None),
 (100,100,0,100.0,0.0,None)])
def test_progress_boundaries(downloaded,total,speed,pct,mb,eta):
    r=functions('ytdl104_progress_snapshot')['ytdl104_progress_snapshot'](downloaded,total,speed)
    assert (r['percent'],r['downloaded_mb'],r['eta_seconds'])==(pct,mb,eta)
def test_disk_low_space(tmp_path):
    fn=functions('ytdl104_has_disk_reserve')['ytdl104_has_disk_reserve']
    with patch('shutil.disk_usage') as usage:
        usage.return_value=type('DU',(),{'free':100})()
        assert not fn(tmp_path,required_bytes=101)
        assert fn(tmp_path,required_bytes=100)
def test_disk_unknown_directory(tmp_path):
    fn=functions('ytdl104_has_disk_reserve')['ytdl104_has_disk_reserve']
    with patch('shutil.disk_usage') as usage:
        usage.return_value=type('DU',(),{'free':1000})()
        assert fn(tmp_path/'not-yet-created',100)
