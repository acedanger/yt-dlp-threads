"""Tests for the Threads yt-dlp plugin.

The live test needs a Netscape cookies file from a logged-in threads.com session:
    THREADS_COOKIES=/path/to/cookies.txt uv run pytest tests/
It is skipped when THREADS_COOKIES is unset. THREADS_TEST_URL overrides the test URL.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / 'tests' / 'fixtures' / 'post.html'
LIVE_URL = os.environ.get('THREADS_TEST_URL', 'https://www.threads.com/share/I5GPDH3O5')

sys.path.insert(0, str(ROOT))


def run_ytdlp(*args):
    env = {**os.environ, 'PYTHONPATH': str(ROOT)}
    return subprocess.run(
        [sys.executable, '-m', 'yt_dlp', *args], env=env, capture_output=True, text=True, timeout=180)


def test_plugin_is_discovered_by_ytdlp():
    # --list-extractors omits plugins; the verbose header lists them.
    out = run_ytdlp('-v')
    assert 'Extractor Plugins: ThreadsIE' in out.stderr, out.stderr


@pytest.mark.parametrize('url', [
    'https://www.threads.com/share/I5GPDH3O5',
    'https://www.threads.net/@pubity/post/Cxd59tZLMrd',
    'https://threads.com/t/CuXnwmrMIZL',
])
def test_url_matching(url):
    from yt_dlp_plugins.extractor.threads import ThreadsIE
    assert ThreadsIE.suitable(url)


def test_non_threads_url_not_matched():
    from yt_dlp_plugins.extractor.threads import ThreadsIE
    assert not ThreadsIE.suitable('https://www.instagram.com/p/Cxd59tZLMrd/')


def test_parses_post_from_page_json():
    from yt_dlp import YoutubeDL
    from yt_dlp_plugins.extractor.threads import ThreadsIE

    ie = ThreadsIE(YoutubeDL({'quiet': True}))
    post = ie._pick_post(FIXTURE.read_text(), 'Cxd59tZLMrd')
    assert post['code'] == 'Cxd59tZLMrd'

    entry = ie._media_entry(post, {'id': 'Cxd59tZLMrd'})
    urls = {f['url'] for f in entry['formats']}
    assert urls == {
        'https://scontent.cdninstagram.com/v/fixture_720.mp4',
        'https://scontent.cdninstagram.com/v/fixture_480.mp4',
    }
    assert entry['http_headers']['Referer'] == 'https://www.threads.com/'


def test_live_share_url():
    cookies = os.environ.get('THREADS_COOKIES')
    if not cookies or not Path(cookies).is_file():
        pytest.skip('THREADS_COOKIES not set to a cookies.txt file')
    out = run_ytdlp('--cookies', cookies, '--no-cache-dir', '-J', LIVE_URL)
    assert out.returncode == 0, out.stderr
    info = json.loads(out.stdout)
    entries = info.get('entries') or [info]
    assert all(e.get('formats') for e in entries)
