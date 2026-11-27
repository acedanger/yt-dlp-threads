"""yt-dlp extractor plugin for Threads (threads.com / threads.net) posts."""

import json
import re

from yt_dlp.extractor.instagram import InstagramBaseIE
from yt_dlp.utils import ExtractorError, format_field, int_or_none, str_or_none, traverse_obj


class ThreadsIE(InstagramBaseIE):
    IE_NAME = 'threads'
    IE_DESC = 'Threads posts (threads.com / threads.net)'
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?threads\.(?:com|net)/
        (?:
            @(?P<user>[\w.]+)/post/(?P<code>[\w-]+)
            |t/(?P<tcode>[\w-]+)
            |share/(?P<share>[\w-]+)
        )'''
    _BASE_URL = 'https://www.threads.com/'
    _COOKIE_DOMAINS = ('threads.com', '.threads.com', 'www.threads.com', 'threads.net', '.threads.net')
    _TESTS = [{
        'url': 'https://www.threads.com/share/I5GPDH3O5',
        'only_matching': True,
    }, {
        'url': 'https://www.threads.net/@pubity/post/Cxd59tZLMrd',
        'only_matching': True,
    }, {
        'url': 'https://www.threads.net/t/CuXnwmrMIZL',
        'only_matching': True,
    }]

    @staticmethod
    def _iter_sjs_blobs(webpage):
        for m in re.finditer(
                r'<script[^>]+type="application/json"[^>]*data-sjs[^>]*>(.+?)</script>', webpage, re.DOTALL):
            try:
                yield json.loads(m.group(1))
            except json.JSONDecodeError:
                continue

    @classmethod
    def _find_posts(cls, obj):
        """Yield every dict that looks like a Threads post (has a code and media fields)."""
        stack = [obj]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                if isinstance(cur.get('code'), str) and (
                        'video_versions' in cur or 'carousel_media' in cur or 'image_versions2' in cur):
                    yield cur
                stack.extend(cur.values())
            elif isinstance(cur, list):
                stack.extend(cur)

    def _pick_post(self, webpage, code):
        posts = [p for blob in self._iter_sjs_blobs(webpage) for p in self._find_posts(blob)]
        if code:
            for post in posts:
                if post.get('code') == code:
                    return post
        return posts[0] if posts else None

    @staticmethod
    def _media_source(post):
        """Return the dict holding the post's video: the post itself, or media it embeds from another post."""
        def has_video(media):
            return bool(media.get('video_versions') or traverse_obj(media, ('carousel_media', ..., 'video_versions')))

        if has_video(post):
            return post
        # Text posts (media_type 19) that embed another post's reel keep the video here
        linked = traverse_obj(post, ('text_post_app_info', 'linked_inline_media', {dict}))
        if linked and has_video(linked):
            return linked
        return post

    def _media_entry(self, media, info):
        entry = {**info, **self._extract_product_media(media)}
        entry['http_headers'] = {'Referer': self._BASE_URL}
        return entry

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        code = mobj.group('code') or mobj.group('tcode')
        display_id = code or mobj.group('share')

        webpage, urlh = self._download_webpage_handle(url, display_id)
        final = self._match_valid_url(urlh.url)
        if final and (final.group('code') or final.group('tcode')):
            code = final.group('code') or final.group('tcode')

        post = self._pick_post(webpage, code)
        if not post:
            if not self._is_logged_in:
                self.raise_login_required(
                    'Threads did not return this post; it may need login cookies', method='cookies')
            raise ExtractorError('Unable to find post data in page', expected=True)

        code = post.get('code') or code
        info = {
            'id': code,
            'display_id': display_id,
            'webpage_url': format_field(
                traverse_obj(post, ('user', 'username', {str})), None,
                f'https://www.threads.com/@%s/post/{code}', default=url),
            'title': format_field(post, [('user', 'username', {str})], 'Post by %s', default=None),
            **traverse_obj(post, {
                'description': ('caption', 'text', {str}),
                'channel': ('user', 'username', {str}),
                'uploader': ('user', 'full_name', {str}),
                'uploader_id': ('user', 'pk', {str_or_none}),
                'timestamp': ('taken_at', {int_or_none}),
                'like_count': ('like_count', {int_or_none}),
            }),
        }

        media = self._media_source(post)
        carousel = [m for m in traverse_obj(media, ('carousel_media', ..., {dict})) if m.get('video_versions')]
        if carousel:
            entries = []
            for idx, media in enumerate(carousel, start=1):
                entry = self._media_entry(media, info)
                entry['id'] = f'{code}_{idx}'
                entries.append(entry)
            if len(entries) == 1:
                return {**entries[0], 'id': code}
            return self.playlist_result(entries, code, info.get('title'), info.get('description'))

        if not media.get('video_versions'):
            raise ExtractorError('This Threads post has no video', expected=True)

        entry = self._media_entry(media, info)
        entry['id'] = code
        return entry
