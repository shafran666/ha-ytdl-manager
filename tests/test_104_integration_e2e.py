import ast, pathlib, subprocess, sys, urllib.parse, tempfile
import pytest
ROOT=pathlib.Path(__file__).resolve().parents[1]
SERVER=ROOT/'ytdl_manager/server.py'
CONFIG=ROOT/'ytdl_manager/config.yaml'
SOURCE=SERVER.read_text(encoding='utf-8')
TREE=ast.parse(SOURCE)

def get_function(name):
    matches=[n for n in TREE.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name]
    assert len(matches)==1, f'{name}: expected one definition'
    return matches[0]

def test_01_server_compiles():
    compile(SOURCE,str(SERVER),'exec')

def test_02_youtube_policy_positive():
    node=get_function('valid_url')
    ns={'urlsplit':urllib.parse.urlsplit}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(SERVER),'exec'),ns)
    for url in ('https://youtube.com/watch?v=abc123','https://youtu.be/abc123','https://www.youtube.com/shorts/abc123','https://www.youtube.com/live/abc123'):
        assert ns['valid_url'](url),url

def test_03_youtube_policy_negative():
    node=get_function('valid_url')
    ns={'urlsplit':urllib.parse.urlsplit}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(SERVER),'exec'),ns)
    for url in ('https://vimeo.com/123','https://youtube.com.evil.test/watch?v=123','http://youtube.com/watch?v=123','https://youtube.com/playlist?list=123','https://youtube.com@evil.test/watch?v=123','file:///etc/passwd','https://127.0.0.1/watch?v=abc'):
        assert not ns['valid_url'](url),url

def test_04_mkv_for_merged_and_single_stream():
    assert "'--merge-output-format','mkv'" in SOURCE
    assert "'--remux-video','mkv'" in SOURCE

def test_05_no_search_in_stable_ui():
    html=(ROOT/'ytdl_manager/index.html').read_text()
    assert 'search_engine.py' not in html

def test_06_dev_slug_is_isolated():
    text=CONFIG.read_text()
    assert 'slug: "ytdl_manager_dev_104"' in text
    assert 'version: "1.0.4-dev"' in text

def test_07_dev_storage_is_isolated():
    # A separate slug alone is insufficient if both apps use shared /media/downloads.
    text=CONFIG.read_text()
    assert 'download_directory: "/media/ytdl-dev-104"' in text

def test_08_no_non_youtube_provider_code():
    assert not (ROOT/'ytdl_manager/search_engine.py').exists()

def test_09_docker_uses_deno_and_ejs():
    docker=(ROOT/'ytdl_manager/Dockerfile').read_text().lower()
    assert 'deno' in docker and 'yt-dlp' in docker and ('ejs' in docker or 'default' in docker)

def test_10_version_consistency():
    assert "VERSION='1.0.4-dev'" in SOURCE

def test_11_no_unresolved_merge_conflicts():
    for p in (SERVER,CONFIG,ROOT/'ytdl_manager/Dockerfile'):
        text=p.read_text()
        assert not any(x in text for x in ('<<<<<<< HEAD','=======\n>>>>>>>','>>>>>>> '))

def test_12_changelog():
    assert '1.0.4-dev' in (ROOT/'ytdl_manager/CHANGELOG.md').read_text()

def test_13_yt_dlp_subprocess_contract():
    assert '--no-playlist' in SOURCE and '--continue' in SOURCE

def test_14_safe_postprocessing_order():
    assert SOURCE.count("'--remux-video','mkv'")==1

def test_15_stable_slug_not_reused():
    assert 'slug: "ytdl_manager"' not in CONFIG.read_text()
