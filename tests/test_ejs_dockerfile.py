from pathlib import Path
import re
DOCKERFILE=(Path(__file__).resolve().parents[1]/"ytdl_manager/Dockerfile").read_text()
def test_yt_dlp_ejs_dependency():
    assert '"yt-dlp[default]"' in DOCKERFILE
def test_deno_installed():
    assert re.search(r"apk add[^\n]*\bdeno\b",DOCKERFILE)
def test_old_pin_removed():
    assert "yt-dlp-ejs==0.8.0" not in DOCKERFILE
