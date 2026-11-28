import ast
from pathlib import Path
R=Path(__file__).resolve().parents[1]
S=(R/'ytdl_manager/server.py').read_text()
def test_no_automatic_caption_metadata():
    assert "info.get('automatic_captions')" not in S
    assert "subs=sorted((info.get('subtitles') or {}).keys())" in S
def test_no_auto_download_flag():
    assert "'--write-auto-subs'" not in S
    assert "'--write-subs'" in S
def test_manual_subtitles_selection_contract():
    fn=next(n for n in ast.parse(S).body if isinstance(n,ast.FunctionDef) and n.name=='analyze_info')
    source=ast.get_source_segment(S,fn)
    assert 'automatic_captions' not in source
    assert "info.get('subtitles')" in source
def test_mkv_and_queue_unchanged():
    assert "'--remux-video','mkv'" in S
    assert 'def worker(' in S
