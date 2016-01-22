# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from collections import defaultdict, Counter
from os import listdir
from os.path import join, exists

from django.apps import apps
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Find duplicates in .po files of your project. ' \
           'Diverging duplicates are different translations for the same key.'

    def add_arguments(self, parser):
        add_argument = parser.add_argument
        add_argument('-l', '--language',
                     action='store', dest='language', default='en',
                     help='Search duplicates for LANGUAGE files. [default: %(default)s]',
                    )
        add_argument('-d', '--not_diverging',
                     action='store_true', dest='not_diverging', default=False,
                     help='Display the not diverging duplicates in translations too '
                          '(useful to see translation message that are duplicated between apps). '
                          '[default: %(default)s]'
                    )
        add_argument('-n', '--no_context',
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

        verbosity = int(options.get('verbosity'))

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
                self.stdout.write('No locale file for "%s" (%s)' % (app_config.label, language))

        if verbosity >= 1:
            self.stdout.write('Number of entries: %s' % entry_count)

        problems_count = 0

        for msgid, entries in entries_per_id.iteritems():
            if len(entries) > 1:
                entries_per_msg = defaultdict(list)

                for entry in entries:
                    if entry.msgid_plural:
                        entries_per_msg[entry.msgstr_plural[0]].append(entry)
                    else:
                        entries_per_msg[entry.msgstr].append(entry)

                if len(entries_per_msg) == 1:
                    if not_diverging:
                        msg_entries = entries_per_msg.itervalues().next()
                        self.stdout.write('\n[duplicates] {%s} in %s' % (
                                                msgid,
                                                [entry.file_path for entry in msg_entries],
                                            )
                                         )

                        problems_count += 1
                else:
                    # cxt_conflict = bool(reduce(lambda s1, s2: s1 & s2,
                    #                            ({entry.msgctxt for entry in msg_entries}
                    #                                 for msg_entries in entries_per_msg.itervalues()
                    #                            )
                    #                           )
                    #                    )
                    ctn = Counter()

                    for msg_entries in entries_per_msg.itervalues():
                        for ctxt in {entry.msgctxt for entry in msg_entries}:
                            ctn[ctxt] += 1

                    cxt_conflict = (ctn.most_common()[0][1] > 1)

                    if not cxt_conflict and no_context:
                        cxt_conflict = any(entry.msgctxt is None
                                               for msg_entries in entries_per_msg.itervalues()
                                                   for entry in msg_entries
                                          )

                    if cxt_conflict:
                        self.stdout.write('\n[diverging]\n {%s} in :' % msgid)

                        for msgstr, msg_entries in entries_per_msg.iteritems():
                            self.stdout.write('    {%s} in: %s' % (
                                                    msgstr,
                                                    ', '.join('(file=%s, cxt=%s)' % (
                                                                    entry.file_path,
                                                                    entry.msgctxt,
                                                                ) for entry in msg_entries
                                                             )
                                                )
                                             )

                        problems_count += 1

        if verbosity >= 1:
            self.stdout.write('\nNumber of problems: %s' % problems_count)
