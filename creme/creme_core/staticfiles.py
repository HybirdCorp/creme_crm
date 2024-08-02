import json
import os
import posixpath
import re

from csscompressor import compress as compress_css
from django.apps import apps
from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import (
    ManifestStaticFilesStorage,
    staticfiles_storage,
)
from django.http import HttpRequest
from django.utils import translation
from django.views.i18n import JavaScriptCatalog
from rjsmin import jsmin

from creme.creme_core.global_info import get_global_info, set_global_info


class BundleItem:
    def __init__(self, relpath, abspath):
        self.relpath = relpath
        self.abspath = abspath

    def preprocess(self, content):
        return content

    def read(self):
        with open(self.abspath, 'r', encoding="utf-8") as f:
            return f.read()

    def get_content(self):
        content = self.read()
        return self.preprocess(content)


class Bundle:
    item_type = BundleItem

    def __init__(self, filename):
        self.filename = filename
        self.files = []

    def add(self, relpath, abspath):
        self.files.append((relpath, abspath))

    def make_comment(self, comment):
        return f"/* {comment} */\n\n"

    def postprocess(self, content):
        return content

    def get_content(self):
        content = ""
        for relpath, abspath in self.files:
            content += self.make_comment(relpath)
            item = self.item_type(relpath, abspath)
            content += item.get_content()
            content += "\n\n\n"
        return self.postprocess(content)

    def save(self, destination):
        with open(os.path.join(destination, self.filename), 'w', encoding="utf-8") as f:
            f.write(self.get_content())


# url_re = re.compile(r'url\s*\(["\']?([\w\.][^:]*?)["\']?\)', re.UNICODE)
url_re = re.compile(r'url\s*\(["\']?([\w\./][^:]*?)["\']?\)', re.UNICODE)


class StyleSheetFile(BundleItem):

    def fixurls(self, match):
        """
        Replace the css url function calls parameters.
        If the url starts with a /, it is considered relative to the static url.
        Else, it is considered relative to css file containing it.
        """
        url = match.group(1)

        hashid = ''
        if '#' in url:
            url, hashid = url.split('#', 1)
            hashid = '#' + hashid

        url_query = None
        if '?' in url:
            url, url_query = url.split('?', 1)

        # Always relative to the file we are adding
        base_path = posixpath.dirname(self.relpath)
        url = posixpath.join(base_path, url)

        abspath = finders.find(url)  # ensure the file exists
        if abspath is None:
            raise ValueError(url)

        if url_query is None:
            url_query = ''
        elif '?' in url:
            url_query = '&' + url_query
        else:
            url_query = '?' + url_query

        return f'url({url}{url_query}{hashid})'

    def preprocess(self, content):
        return url_re.sub(self.fixurls, content)


class StyleSheetBundle(Bundle):
    item_type = StyleSheetFile

    def postprocess(self, content):
        return compress_css(content)


class JavaScriptFile(BundleItem):
    pass


class JavaScriptBundle(Bundle):
    item_type = JavaScriptFile

    def postprocess(self, content):
        return jsmin(content)


class I18NCatalog:
    def __init__(self, language_code):
        self.language_code = language_code
        self.filename = f"{language_code}.js"

    def get_content(self):
        language_bidi = self.language_code.split('-')[0] in settings.LANGUAGES_BIDI

        # Add some JavaScript data
        content = f'var LANGUAGE_CODE = "{self.language_code}";\n'
        content += 'var LANGUAGE_BIDI = ' + \
            (language_bidi and 'true' or 'false') + ';\n'

        translation.activate(self.language_code)
        content += JavaScriptCatalog(
            packages=[app_config.name for app_config in apps.app_configs.values()],
        ).get(HttpRequest()).content.decode()

        # The hgettext() function just calls gettext() internally,
        # but it won't get indexed by makemessages.
        content += '\nwindow.hgettext = function(text) { return gettext(text); };\n'
        # Add a similar hngettext() function
        content += (
            'window.hngettext = function(singular, plural, count) {'
            ' return ngettext(singular, plural, count); '
            '};\n'
        )

        return content

    def save(self, destination):
        with open(os.path.join(destination, self.filename), 'w', encoding="utf-8") as f:
            f.write(self.get_content())


def load_manifest():
    manifest = get_global_info("staticfiles_manifest")

    if manifest is None:
        manifest_name = ManifestStaticFilesStorage.manifest_name
        manifest_path = os.path.join(settings.STATIC_ROOT, manifest_name)
        with open(manifest_path, "r") as fp:
            manifest = json.load(fp)
        set_global_info(staticfiles_manifest=manifest)

    return manifest


def get_staticfile_url(path, verify=False):
    if verify:
        manifest = load_manifest()["paths"]
        if path not in manifest:
            raise KeyError(f"Resource not found {path}")
    return staticfiles_storage.url(path)
