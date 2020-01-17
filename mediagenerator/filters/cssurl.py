from base64 import b64encode
from mimetypes import guess_type
import os
import posixpath
import re

from django.conf import settings

from mediagenerator.generators.bundles.base import Filter, FileFilter
from mediagenerator.utils import media_url, prepare_patterns, find_file
from ..api import global_errors

url_re = re.compile(r'url\s*\(["\']?([\w\.][^:]*?)["\']?\)', re.UNICODE)

# Whether to rewrite CSS URLs, at all
REWRITE_CSS_URLS = getattr(settings, 'REWRITE_CSS_URLS', True)
# Whether to rewrite CSS URLs relative to the respective source file
# or whether to use "absolute" URL rewriting (i.e., relative URLs are
# considered absolute with regards to STATICFILES_URL)
REWRITE_CSS_URLS_RELATIVE_TO_SOURCE = getattr(settings,
    'REWRITE_CSS_URLS_RELATIVE_TO_SOURCE', True)

GENERATE_DATA_URIS = getattr(settings, 'GENERATE_DATA_URIS', False)
MAX_DATA_URI_FILE_SIZE = getattr(settings, 'MAX_DATA_URI_FILE_SIZE', 12 * 1024)
IGNORE_PATTERN = prepare_patterns(getattr(settings,
   'IGNORE_DATA_URI_PATTERNS', (r'.*\.htc',)), 'IGNORE_DATA_URI_PATTERNS')


class URLRewriter:
    def __init__(self, base_path='./'):
        self.base_path = base_path or './'

    def rewrite_urls(self, content):
        return url_re.sub(self.fixurls, content) if REWRITE_CSS_URLS else content

    def fixurls(self, match):
        url = original_url = match.group(1)

        hashid = ''
        if '#' in url:
            url, hashid = url.split('#', 1)
            hashid = '#' + hashid

        url_query = None
        if '?' in url:
            url, url_query = url.split('?', 1)

        if ':' not in url and not url.startswith('/'):
            rebased_url = posixpath.join(self.base_path, url)
            rebased_url = posixpath.normpath(rebased_url)
            try:
                if GENERATE_DATA_URIS:
                    path = find_file(rebased_url)
                    if os.path.getsize(path) <= MAX_DATA_URI_FILE_SIZE and \
                            not IGNORE_PATTERN.match(rebased_url):
                        data = b64encode(open(path, 'rb').read())
                        mime = guess_type(path)[0] or 'application/octet-stream'
                        return f'url(data:{mime};base64,{data})'

                url = media_url(rebased_url)
            except KeyError:
                global_errors['filters.cssurl'][original_url] = 'URL not found: ' + original_url
            else:
                global_errors['filters.cssurl'].pop(original_url, None)

        if url_query is None:
            url_query = ''
        elif '?' in url:
            url_query = '&' + url_query
        else:
            url_query = '?' + url_query

        return f'url({url}{url_query}{hashid})'


class CSSURL(Filter):
    """Rewrites URLs relative to media folder ("absolute" rewriting)."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        assert self.filetype == 'css', (
            f'CSSURL only supports CSS output. '
            f'The parent filter expects "{self.filetype}".')

    def get_output(self, variation):
        rewriter = URLRewriter()
        for input in self.get_input(variation):
            yield rewriter.rewrite_urls(input)

    def get_dev_output(self, name, variation):
        content = super().get_dev_output(name, variation)

        return URLRewriter().rewrite_urls(content)


class CSSURLFileFilter(FileFilter):
    """Rewrites URLs relative to input file's location."""
    def get_dev_output(self, name, variation):
        content = super().get_dev_output(name, variation)
        if not REWRITE_CSS_URLS_RELATIVE_TO_SOURCE:
            return content

        return URLRewriter(posixpath.dirname(name)).rewrite_urls(content)
