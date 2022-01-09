# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2009-2022 Hybird
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

from collections import defaultdict
from datetime import datetime
from os import listdir, makedirs
from os.path import exists, isdir, join

import pytz
from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.encoding import smart_str

# APP_NAME = 'locale_overload'


# TODO: factorise with i18n_duplicates ?
class Command(BaseCommand):
    help = (
        'Find some terms in .po files of your project and create/update a '
        'translation file with the messages containing one of these terms.\n'
        'The purpose is to overload some terms for a specific instance of your project.'
    )
    args = 'term1 term2 ... termN'

    def add_arguments(self, parser):
        add_arg = parser.add_argument
        add_arg(
            '-d', '--directory',
            action='store', dest='directory', default='locale_overload',
            help='Local directory of your project used to store the .po file(s). '
                 '[default: %(default)s]',
        )
        add_arg(
            '-l', '--language',
            action='store', dest='language', default='en',
            help='Search terms in LANGUAGE files. [default: %(default)s]',
        )
        add_arg(
            '-u', '--comment_useless',
            action='store_true', dest='comment_useless', default=False,
            help='Search messages which are useless in the overloading file '
                 '(ie: these messages are not found in overloaded files) '
                 'and mark them as obsolete (ie: start with "#~" in the po file).'
                 '[default: %(default)s]',
        )
        add_arg(
            '--js',
            action='store_true', dest='javascript', default=False,
            help='Work with po file for javascript (ie: djangojs.po instead of django.po) '
                 '[default: %(default)s]',
        )
        add_arg(
            'args', metavar='terms', nargs='*',
            help='The terms to find in existing messages.',
        )

    def handle(self, *terms, **options):
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

        settings_opt = get_opt('settings')
        self.settings_arg = f'--settings={settings_opt}' if settings_opt else ''

        if verbosity >= 2:
            self.stdout.write('OK "polib" library is installed.')

        self.directory = get_opt('directory')
        language = get_opt('language')
        file_name = 'djangojs.po'if get_opt('javascript') else 'django.po'

        if get_opt('comment_useless'):
            self._comment_useless(language, verbosity, polib, file_name, *terms)
        else:
            self._overload_terms(language, verbosity, polib, file_name, *terms)

    def _get_catalog_paths(self, language, file_name):
        catalog_dirpath = join(
            # settings.CREME_ROOT, APP_NAME, 'locale', language, 'LC_MESSAGES',
            settings.BASE_DIR, self.directory, language, 'LC_MESSAGES',
        )
        catalog_path = join(catalog_dirpath, file_name)

        return catalog_dirpath, catalog_path

    def _iter_pofiles(self, language, polib, file_name):
        for app_config in apps.get_app_configs():
            basepath = join(app_config.path, 'locale', language, 'LC_MESSAGES')

            if exists(basepath):
                for fname in listdir(basepath):
                    if fname == file_name:
                        path = join(basepath, fname)

                        yield polib.pofile(path)

    def _comment_useless(self, language, verbosity, polib, file_name, *args):
        if args:
            self.stderr.write('Error: in <useless> mode, given terms are not used')

        catalog_dirpath, catalog_path = self._get_catalog_paths(language, file_name)

        if not exists(catalog_path):
            raise CommandError(
                f'no existing overloading {file_name} found in "{catalog_dirpath}".'
            )

        catalog = polib.pofile(catalog_path)
        overloading_entries = {
            entry.msgid: entry
            for entry in catalog.translated_entries()
        }

        for app_pofile in self._iter_pofiles(language, polib, file_name):
            for entry in app_pofile.translated_entries():
                overloading_entries.pop(entry.msgid, None)

        if not overloading_entries:
            if verbosity >= 1:
                self.stdout.write('No useless entry')
        else:
            if verbosity >= 1:
                self.stdout.write(
                    f'{len(overloading_entries)} useless entries found and commented:'
                )

            for msgid, entry in overloading_entries.items():
                self.stdout.write(msgid)
                entry.obsolete = True

            catalog.save(catalog_path)

    def _overload_terms(self, language, verbosity, polib, file_name, *args):
        if not args:
            raise CommandError('please give at least one term')

        catalog_entries = {}
        catalog_dirpath, catalog_path = self._get_catalog_paths(language, file_name)
        # all_plural_forms = set()
        all_plural_forms = defaultdict(list)

        if exists(catalog_path):
            catalog = polib.pofile(catalog_path)

            for entry in catalog.translated_entries():
                entry.obsolete = True
                catalog_entries[entry.msgid] = entry
        else:
            if verbosity >= 1:
                self.stdout.write(f'Create catalog at {catalog_path}')

            if not exists(catalog_dirpath):
                if verbosity >= 2:
                    self.stdout.write(f'Create the folder "{catalog_dirpath}"')

                makedirs(catalog_dirpath)
            elif not isdir(catalog_dirpath):
                self.stderr.write(f'"{catalog_dirpath}" exists and is not a directory.')
                return

            catalog = polib.POFile()
            catalog.metadata = {
                'Project-Id-Version':        'PACKAGE VERSION',
                'Report-Msgid-Bugs-To':      '',
                'PO-Revision-Date':          'YEAR-MO-DA HO:MI+ZONE',
                'Last-Translator':           'FULL NAME <EMAIL@ADDRESS>',
                'Language-Team':             'LANGUAGE <LL@li.org>',
                'Language':                  language,
                'MIME-Version':              '1.0',
                'Content-Type':              'text/plain; charset=UTF-8',
                'Content-Transfer-Encoding': '8bit',
            }

        catalog.metadata['POT-Creation-Date'] = pytz.timezone(
            settings.TIME_ZONE
        ).localize(datetime.now()).strftime('%Y-%m-%d %H:%M%z')

        terms = [smart_str(arg) for arg in args]
        entry_count = 0

        for app_pofile in self._iter_pofiles(language, polib, file_name):
            plural_forms = app_pofile.metadata.get('Plural-Forms')
            # if plural_forms:
            #     all_plural_forms.add(plural_forms)
            if not plural_forms:
                raise CommandError(
                    f'The file "{app_pofile.fpath}" has no "Plural-Forms" in its metadata. '
                    f'It could prevent the overloading to work correctly. '
                    f'Fix it before you try gain to run this command.'
                )

            all_plural_forms[plural_forms].append(app_pofile.fpath)

            for entry in app_pofile.translated_entries():
                entry_count += 1
                msgid = entry.msgid
                existing_entry = catalog_entries.get(msgid)

                # TODO: manage context (key=msgid + context ?)
                if existing_entry is not None:
                    if existing_entry.obsolete:  # Entry has not been updated yet
                        existing_entry.obsolete = False
                        existing_entry.occurrences = entry.occurrences
                    else:
                        existing_entry.occurrences += entry.occurrences
                else:
                    for term in terms:
                        if term in msgid:  # TODO: what about case sensitivity ?
                            entry.flags.append('fuzzy')
                            catalog.append(entry)
                            catalog_entries[entry.msgid] = entry
                            break

        # if not catalog.fpath and all_plural_forms:  # Creation of the file
        #     if len(all_plural_forms) > 1:
        #         self.stderr.write(
        #             'Different information about plural forms were found '
        #             '(first one used):{}'.format(
        #                 ''.join(f'\n - {i}' for i in all_plural_forms)
        #             )
        #         )
        #
        #     catalog.metadata['Plural-Forms'] = next(iter(all_plural_forms))
        if len(all_plural_forms) > 1:
            raise CommandError(
                'The .po files contain different "Plural-Forms" in their metadata. '
                'It could prevent the overloading to work correctly. '
                'Fix it before you try gain to run this command.\n'
                'Details:\n'
                '{}'.format(
                    ''.join(
                        ' - "{}": {}\n'.format(plural_forms, ', '.join(paths))
                        for plural_forms, paths in all_plural_forms.items()
                    )
                )
            )

        catalog.metadata['Plural-Forms'] = next(iter(all_plural_forms.keys()))

        catalog.save(catalog_path)

        if verbosity >= 1:
            self.stdout.write(
                f"Number of examined entries: {entry_count}.\n"
                f"To use the overloading .po file(s), edit your settings to add a line like:\n"
                f" > LOCALE_PATHS.insert(0, BASE_DIR / '{self.directory}')\n"
                f"Once you have edited '{catalog_path}' (set the <msgstr>, "
                f"remove the <#fuzzy>...), create the .mo file with the command:\n"
                f" > creme compilemessages {self.settings_arg}"
            )
