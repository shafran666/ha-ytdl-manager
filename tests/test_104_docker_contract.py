from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_docker_does_not_copy_search():
    docker=(ROOT/'ytdl_manager/Dockerfile').read_text()
    assert 'search_engine.py' not in docker
    for line in docker.splitlines():
        if line.strip().startswith('COPY '):
            source=line.split()[1]
            assert (ROOT/'ytdl_manager'/source).exists(),source
def test_no_search_module():
    assert not (ROOT/'ytdl_manager/search_engine.py').exists()
