# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2021 Hybird
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
#
################################################################################

import importlib
from collections import defaultdict
from glob import glob
from os import listdir
from os.path import dirname, exists, join

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Find .po files which have divergent plural-forms meta-data in your project. "
        "It's a good thing that each language get only one value for <plural-forms> "
        "(only one merged dictionary per language, easy to override a 'msgid'...)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'args', metavar='languages', nargs='*',
            help='Limit to these languages. If not given, all available languages are used.',
        )

    @staticmethod
    def _iter_locale_base_paths():
        django_package = importlib.import_module('django.conf')

        yield dirname(django_package.__file__)

        CREME_ROOT = settings.CREME_ROOT
        yield CREME_ROOT
        yield join(CREME_ROOT, 'locale_overload')

        for app_config in apps.get_app_configs():
            yield app_config.path

    def _iter_po_paths(self, accept_language):
        for base_path in self._iter_locale_base_paths():
            locale_dir_path = join(base_path, 'locale')

            if exists(locale_dir_path):
                for language in listdir(locale_dir_path):
                    if accept_language(language):
                        for path in glob(
                            join(base_path, 'locale', language, 'LC_MESSAGES', '*.po')
                        ):
                            yield language, path

    def handle(self, *languages, **options):
        try:
            from polib import pofile
        except ImportError as e:
            self.stderr.write(str(e))
            self.stderr.write(
                'The required "polib" library seems not installed; aborting.'
            )
            return

        get_opt = options.get
        verbosity = get_opt('verbosity')
        write = self.stdout.write

        if verbosity >= 2:
            write('OK "polib" library is installed.')

        plural_forms = defaultdict(lambda: defaultdict(list))

        # NB: we could avoid to use 'polib' just to read some meta-data in file header...
        for language, path in self._iter_po_paths(
            {*languages}.__contains__ if languages else lambda l: True
        ):
            plural_forms[language][pofile(path).metadata.get('Plural-Forms')].append(path)

        error_count = 0

        for language, pforms in plural_forms.items():
            if len(pforms) > 1:
                error_count += 1
                write(f'- {language}:\n')

                for rule, paths in pforms.items():
                    write(
                        '  - "{rule}" found in following files:\n{files}'.format(
                            rule=rule,
                            files='\n'.join(f'    - {path}' for path in paths),
                        )
                    )

        if not error_count and verbosity >= 2:
            write('No error found.')
