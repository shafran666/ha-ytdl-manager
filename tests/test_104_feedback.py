from pathlib import Path
R=Path(__file__).resolve().parents[1]
def test_labels():
 h=(R/'ytdl_manager/index.html').read_text()
 assert "actionButton('cancel','Cancel'" not in h
 assert "actionButton('cancel','Delete'" not in h
 assert "actionButton('cancel','Pause'" in h
 assert "actionButton('cancel','Delete from queue'" in h
 assert "'Schedule time ('+appTimezone+')'" not in h
def test_no_search():
 assert not (R/'ytdl_manager/search_engine.py').exists()
