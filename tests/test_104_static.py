import ast
from pathlib import Path
src=Path('ytdl_manager/server.py').read_text()
tree=ast.parse(src)
def test_single_valid_url_function():
    assert sum(isinstance(n,ast.FunctionDef) and n.name=='valid_url' for n in tree.body)==1
def test_remux_to_mkv():
    assert "'--remux-video','mkv'" in src
    assert "'--merge-output-format','mkv'" in src
def test_version():
    assert "VERSION='1.0.4-dev'" in src
