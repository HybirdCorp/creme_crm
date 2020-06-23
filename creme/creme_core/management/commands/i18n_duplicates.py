# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2009-2020 Hybird
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

from collections import Counter, defaultdict
from os import listdir
from os.path import exists, join

from django.apps import apps
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Find duplicates in .po files of your project. ' \
           'Diverging duplicates are different translations for the same key.'

    def add_arguments(self, parser):
        add_argument = parser.add_argument
        add_argument(
            '-l', '--language',
            action='store', dest='language', default='en',
            help='Search duplicates for LANGUAGE files. [default: %(default)s]',
        )
        add_argument(
            '-d', '--not_diverging',
            action='store_true', dest='not_diverging', default=False,
            help='Display the not diverging duplicates in translations too '
                 '(useful to see translation message that are duplicated between apps). '
                 '[default: %(default)s]'
        )
        add_argument(
            '-n', '--no_context',
            action='store_true', dest='no_context', default=False,
            help='Display the diverging duplicates without problem (context are distinct), '
                 'but with some translations without context. [default: %(default)s]'
        )

    def handle(self, **options):
        try:
            from polib import pofile
        except ImportError as e:
            self.stderr.write(str(e))
            self.stderr.write('The required "polib" library seems not installed ; aborting.')
            return

        verbosity = options.get('verbosity')

        if verbosity >= 2:
            self.stdout.write('OK "polib" library is installed.')

        get_opt = options.get
        language = get_opt('language')
        not_diverging = get_opt('not_diverging')
        no_context = get_opt('no_context')

        entry_count = 0
        entries_per_id = defaultdict(list)

        for app_config in apps.get_app_configs():
            basepath = join(app_config.path, 'locale', language, 'LC_MESSAGES')

            if exists(basepath):
                for fname in listdir(basepath):
                    if fname.endswith('.po'):
                        path = join(basepath, fname)

                        for entry in pofile(path).translated_entries():
                            entry_count += 1
                            entry.file_path = path
                            entries_per_id[entry.msgid].append(entry)
            elif verbosity >= 1:
                self.stdout.write(f'No locale file for "{app_config.label}" ({language})')

        if verbosity >= 1:
            self.stdout.write(f'Number of entries: {entry_count}')

        problems_count = 0

        for msgid, entries in entries_per_id.items():
            if len(entries) > 1:
                entries_per_msg = defaultdict(list)

                for entry in entries:
                    if entry.msgid_plural:
                        entries_per_msg[entry.msgstr_plural[0]].append(entry)
                    else:
                        entries_per_msg[entry.msgstr].append(entry)

                if len(entries_per_msg) == 1:
                    if not_diverging:
                        msg_entries = next(entries_per_msg.values())
                        self.stdout.write(
                            '\n[duplicates] ({}) in {}'.format(
                                msgid,
                                [entry.file_path for entry in msg_entries],
                            )
                        )

                        problems_count += 1
                else:
                    ctn = Counter()

                    for msg_entries in entries_per_msg.values():
                        for ctxt in {entry.msgctxt for entry in msg_entries}:
                            ctn[ctxt] += 1

                    cxt_conflict = (ctn.most_common()[0][1] > 1)

                    if not cxt_conflict and no_context:
                        cxt_conflict = any(
                            entry.msgctxt is None
                            for msg_entries in entries_per_msg.values()
                            for entry in msg_entries
                        )

                    if cxt_conflict:
                        self.stdout.write(f'\n[diverging]\n ({msgid}) in :')

                        for msgstr, msg_entries in entries_per_msg.items():
                            self.stdout.write(
                                '    ({}) in: {}'.format(
                                    msgstr,
                                    ', '.join(
                                        f'(file={entry.file_path}, cxt={entry.msgctxt})'
                                        for entry in msg_entries
                                    )
                                )
                            )

                        problems_count += 1

        if verbosity >= 1:
            self.stdout.write(f'\nNumber of problems: {problems_count}')
