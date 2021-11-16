# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2017-2021 Hybird
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

# import importlib
from collections import defaultdict
# from os import listdir
# from os.path import dirname, exists, join
from pathlib import Path

import django
from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand


class _POFileInfo:
    __slots__ = ('app_label', 'file_path', 'pofile')

    def __init__(self, app_label, file_path, pofile):
        self.app_label = app_label
        self.file_path = file_path
        self.pofile = pofile

    def __str__(self):
        return f'{self.app_label} ({self.file_path})'


class _EntryInfo:
    __slots__ = ('app_label', 'file_path', 'linenum')

    def __init__(self, app_label, file_path, linenum):
        self.app_label = app_label
        self.file_path = file_path
        self.linenum = linenum

    def __str__(self):
        return f'{self.app_label} ({self.file_path} l.{self.linenum})'


class Command(BaseCommand):
    help = (
        "Find msgstr which are empty in all .po files of your project. "
        "It's useful to keep a msgid translated only once in your project."
        "without forgetting to translate any message."
    )

    def add_arguments(self, parser):
        add_arg = parser.add_argument
        add_arg(
            '-l', '--language',
            action='store', dest='language', default='en',
            help='Search empty message in LANGUAGE files. [default: %(default)s]',
        )
        add_arg(
            '--js',
            action='store_true', dest='javascript', default=False,
            help='Work with po file for javascript (ie: djangojs.po instead of djangojs.po) '
                 '[default: %(default)s]',
        )

    # def _iter_locale_base_paths(self):
    #     django_package = importlib.import_module('django.conf')
    #
    #     yield 'django', dirname(django_package.__file__)
    #
    #     CREME_ROOT = settings.CREME_ROOT
    #     yield 'creme', CREME_ROOT
    #     yield 'creme', join(CREME_ROOT, 'locale_overload')
    #
    #     for app_config in apps.get_app_configs():
    #         yield app_config.label, app_config.path
    @staticmethod
    def _iter_locale_base_paths():
        yield 'django', Path(django.__file__).resolve().parent / 'conf' / 'locale'

        for local_path in settings.LOCALE_PATHS:
            yield 'local', Path(local_path)

        for app_config in apps.get_app_configs():
            yield app_config.label, Path(app_config.path, 'locale')

    def _iter_pofiles(self, language, polib, file_name):
        # for label, base_path in self._iter_locale_base_paths():
        #     dir_path = join(base_path, 'locale', language, 'LC_MESSAGES')
        #
        #     if exists(dir_path):
        #         for fname in listdir(dir_path):
        #             if fname == file_name:
        #                 path = join(dir_path, fname)
        #
        #                 yield _POFileInfo(label, path, polib.pofile(path))
        for label, base_path in self._iter_locale_base_paths():
            po_path = base_path / language / 'LC_MESSAGES' / file_name

            if po_path.exists():
                yield _POFileInfo(label, po_path, polib.pofile(po_path))

    def handle(self, *args, **options):
        try:
            import polib
        except ImportError as e:
            self.stderr.write(str(e))
            self.stderr.write(
                'The required "polib" library seems not installed; aborting.'
            )
            return

        get_opt = options.get
        verbosity = get_opt('verbosity')

        if verbosity >= 2:
            self.stdout.write('OK "polib" library is installed.')

        language = get_opt('language')
        file_name = 'djangojs.po'if get_opt('javascript') else 'django.po'

        untranslated_entries = defaultdict(list)

        for app_pofinfo in self._iter_pofiles(language, polib, file_name):
            for entry in app_pofinfo.pofile.untranslated_entries():
                untranslated_entries[(entry.msgctxt, entry.msgid)].append(
                    _EntryInfo(
                        app_label=app_pofinfo.app_label,
                        file_path=app_pofinfo.file_path,
                        linenum=entry.linenum,
                    )
                )

        for app_pofinfo in self._iter_pofiles(language, polib, file_name):
            for entry in app_pofinfo.pofile.translated_entries():
                untranslated_entries.pop((entry.msgctxt, entry.msgid), None)

        if not untranslated_entries:
            if verbosity >= 2:
                self.stdout.write('No empty message.')
        else:
            for (msgctxt, msgid), entries_info in untranslated_entries.items():
                self.stdout.write(
                    '{ctxt}\nmsgid "{msgid}"\n{entries}\n--------\n'.format(
                        ctxt=f'\nmsgctxt "{msgctxt}"' if msgctxt is not None else '',
                        msgid=msgid,
                        entries='\n'.join(f' - {entry_info}' for entry_info in entries_info),
                    )
                )

            if verbosity >= 1:
                self.stdout.write(f'\nNumber of problems: {len(untranslated_entries)}')
