# yt-dlp-threads

A [yt-dlp](https://github.com/yt-dlp/yt-dlp) extractor plugin for Threads video posts. It handles `threads.com` and `threads.net` URLs in three forms: `/@user/post/CODE`, `/t/CODE` and `/share/CODE`.

Threads returns a "not found" page to logged-out visitors, so you need cookies from a logged-in session.

## Export cookies

1. Log in to <https://www.threads.com> in Chrome or Firefox.
2. Install a cookies.txt exporter that runs locally:
   - Chrome: "Get cookies.txt LOCALLY"
   - Firefox: "cookies.txt"
3. With a threads.com tab open, export cookies **for the current site** in Netscape format and save the file as `cookies.txt`.
4. Check that the file contains a `sessionid` line for `.threads.com`.

Alternative: run `yt-dlp --cookies-from-browser firefox --cookies cookies.txt --skip-download https://www.threads.com/` on the same machine as the browser.

Cookies grant access to your account. Keep the file private, and re-export it when downloads start failing with a login error.

## Use with MeTube

1. Mount the plugin into yt-dlp's system plugin folder:

   ```yaml
   services:
     metube:
       volumes:
         - ./yt-dlp-threads:/etc/yt-dlp/plugins/threads:ro
   ```

   The mount target must contain `yt_dlp_plugins/extractor/threads.py`.
2. Upload `cookies.txt` with MeTube's cookie upload button (it is stored in `STATE_DIR`).
3. Restart MeTube and paste a Threads URL.

Public posts work without cookies. MeTube ignores a `cookies.txt` inside the plugin folder; only the uploaded file is used.

To run yt-dlp by hand inside the container, copy the cookies to a writable path first. yt-dlp writes the cookie file back on exit, and the `:ro` mount makes it fail with `OSError: [Errno 30] Read-only file system`:

```bash
docker exec metube sh -c 'cp /etc/yt-dlp/plugins/threads/cookies.txt /tmp/c.txt &&
  yt-dlp --cookies /tmp/c.txt --simulate https://www.threads.com/share/I5GPDH3O5; rm -f /tmp/c.txt'
```

## Use with the yt-dlp CLI

```bash
mkdir -p ~/.config/yt-dlp/plugins
ln -s "$PWD" ~/.config/yt-dlp/plugins/threads
yt-dlp --cookies cookies.txt https://www.threads.com/share/I5GPDH3O5
```

Run `yt-dlp -v` and look for `Extractor Plugins: ThreadsIE` to confirm the plugin loaded.

## Tests

```bash
uv sync
uv run pytest tests/                                   # offline tests
THREADS_COOKIES=cookies.txt uv run pytest tests/       # adds the live test
```

`THREADS_TEST_URL` overrides the live test URL.

## Limitations

- Video only. Image-only posts report "This Threads post has no video".
- Text posts that embed another post's video download that embedded video, with the outer post's caption and author.
- The extractor reads post data embedded in the page. If Threads stops embedding it for logged-in users, extraction breaks.
