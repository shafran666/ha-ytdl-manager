import ast
from pathlib import Path
R=Path(__file__).resolve().parents[1]
S=(R/'ytdl_manager/server.py').read_text();H=(R/'ytdl_manager/index.html').read_text()
def test_server_parses():ast.parse(S)
def test_safe_folder_and_creation():
 assert 'strict=False' in S and '# YTDL104_CREATE_SAFE_DIRECTORY' in S
 assert ('folder.mkdir(parents=True, exist_ok=True)' in S or 'folder.mkdir(parents=True,exist_ok=True)' in S or 'Path(folder).mkdir(parents=True, exist_ok=True)' in S or 'Path(folder).mkdir(parents=True,exist_ok=True)' in S)
def test_duplicate_status():
 assert '# YTDL104_DUPLICATE_STATUS_VERIFIED' in S
 assert "state='already_exists'" in S
 assert 'Already exists' in S
def test_saved_subtitle_tracks():
 assert '# YTDL104_FINAL_SUBTITLE_STATUS_VERIFIED' in S
 assert "job['saved_subtitles']=actual_subtitles" in S
 assert 'saved_subtitles' in H
def test_ui():
 assert "actionButton('cancel','Pause'" in H
 assert "actionButton('cancel','Delete from queue'" in H
 assert "'Schedule time ('+appTimezone+')'" not in H
