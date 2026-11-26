from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]/'ytdl_manager'
def test_details_panel():
    assert re.search(r'<details\b[^>]*id=["\']ytdl-search-panel["\']',(ROOT/'index.html').read_text())
def test_script_references():
    html=(ROOT/'index.html').read_text()
    for name in ('app-1.js','app-2.js'):
        assert f'src="{name}"' in html
        assert (ROOT/name).is_file()
def test_observer_is_idempotent():
    js=(ROOT/'app-2.js').read_text()
    assert js.count('/* YTDL_SELECT_COLLAPSE_V2 */')==1
def test_only_selected_video_closes():
    js=(ROOT/'app-2.js').read_text()
    assert 'input.value!==previous' in js
    assert 'panel.open=false' in js
    assert 'button.disabled' in js
def test_search_results_not_reset_by_observer():
    js=(ROOT/'app-2.js').read_text().split('/* YTDL_SELECT_COLLAPSE_V2 */')[1]
    assert 'replaceChildren' not in js
    assert 'fetch(' not in js
