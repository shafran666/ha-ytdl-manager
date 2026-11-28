import ast,re
from pathlib import Path
R=Path(__file__).resolve().parents[1]
S=(R/'ytdl_manager/server.py').read_text();H=(R/'ytdl_manager/index.html').read_text()
def test_python():ast.parse(S)
def test_folder():
    assert 'resolve(strict=False)' in S
    assert re.search(r'(?:Path\(folder\)|folder)\.mkdir\(parents=True\s*,\s*exist_ok=True\)',S)
def test_duplicate():
    assert "state='already_exists'" in S
    assert 'Already exists' in S
def test_subtitle_tracks():
    assert "job['saved_subtitles']=actual_subtitles" in S
    assert 'saved_subtitles' in H
def test_ui():
    assert "actionButton('cancel','Pause'" in H
    assert "actionButton('cancel','Delete from queue'" in H
    assert "'Schedule time ('+appTimezone+')'" not in H
def test_no_search():assert not (R/'ytdl_manager/search_engine.py').exists()
