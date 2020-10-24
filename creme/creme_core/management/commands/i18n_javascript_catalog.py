# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2018-2020 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################

import os

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, no_translations
from django.http import HttpRequest
from django.utils import translation
from django.views.i18n import JavaScriptCatalog


class Command(BaseCommand):
    help = 'Build a static javascript translation catalog'

    def handle_language(self, language_code):
        with translation.override(language=language_code):
            self.stdout.write(f"Building javascript catalog for language {language_code}...")

            language_bidi = language_code.split('-')[0] in settings.LANGUAGES_BIDI

            # Hybird FIX - Django1.10 version
            # request = HttpRequest()
            # request.GET['language'] = language

            # Add some JavaScript data
            content = f'var LANGUAGE_CODE = "{language_code}";\n'
            content += 'var LANGUAGE_BIDI = ' + \
                (language_bidi and 'true' or 'false') + ';\n'

            # content += javascript_catalog(request,
            #     packages=settings.INSTALLED_APPS).content

            # Hybird FIX - Django1.8 version
            # content += javascript_catalog(
            #                 request,
            #                 packages=[app_config.name for app_config in apps.app_configs.values()],
            #             ).content
            # Hybird FIX - Django1.10 version
            # content += JavaScriptCatalog(packages=[app_config.name for app_config in apps.app_configs.values()]) \
            #                             .get(HttpRequest()).content
            content += JavaScriptCatalog(packages=[app_config.name for app_config in apps.app_configs.values()]) \
                                        .get(HttpRequest()).content.decode()

            # The hgettext() function just calls gettext() internally, but it won't get indexed by makemessages.
            content += '\nwindow.hgettext = function(text) { return gettext(text); };\n'
            # Add a similar hngettext() function
            content += 'window.hngettext = function(singular, plural, count) { return ngettext(singular, plural, count); };\n'

            with open(os.path.join(settings.CREME_ROOT, "static", f"{language_code}.js"), "w") as fd:
                fd.write(content)

    @no_translations
    def handle(self, **kwargs):
        for language_code, language_name in settings.LANGUAGES:
            self.handle_language(language_code)
