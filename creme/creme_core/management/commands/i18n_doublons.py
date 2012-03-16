# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from collections import defaultdict
from optparse import make_option, OptionParser
from os import listdir
from os.path import join, exists

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Find doublons in .po files of your project. Diverging doublons are different translations for the same key.'
    option_list = BaseCommand.option_list + (
                     make_option('-l', '--language', action='store', dest='language',
                                 default='en', help='Search doublons for LANGUAGE files. '
                                                    '[default: %default]'
                                ),
                     make_option('-d', '--not_diverging', action='store_true',
                                 dest='not_diverging', default=False,
                                 help='Display the not diverging doublons in translations too. '
                                      '[default: %default]'
                                ),
                     make_option('-n', '--no_context', action='store_true',
                                 dest='no_context', default=False,
                                 help='Display the diverging doublons without problem (context are distinct), '
                                      'but with some translations without context. [default: %default]'
                                ),
                    )

    def create_parser(self, prog_name, subcommand):
        return OptionParser(prog=prog_name,
                            usage=self.usage(subcommand),
                            version=self.get_version(),
                            option_list=self.option_list,
                            conflict_handler="resolve"
                           )

    def handle(self, *args, **options):
        try:
            from polib import pofile
        except ImportError as e:
            print e
            print 'The required "polib" library seems not installed ; aborting.'
            return

        verbosity = int(options.get('verbosity'))

        if verbosity >= 2:
            print 'OK "polib" library is installed.'

        language = options.get('language')
        not_diverging = options.get('not_diverging')
        no_context = options.get('no_context')

        entry_count = 0
        entries_per_id = defaultdict(list)

        for app_name in settings.INSTALLED_CREME_APPS:
            basepath = '%s/locale/%s/LC_MESSAGES/' % (app_name, language)

            if exists(basepath):
                for fname in listdir(basepath):
                    if fname.endswith('.po'):
                        path = join(basepath, fname)

                        for entry in pofile(path).translated_entries():
                            entry_count += 1
                            entry.file_path = path
                            entries_per_id[entry.msgid].append(entry)

        if verbosity >= 1:
            print 'Number of entries:', entry_count

        problems_count = 0

        for msgid, entries in entries_per_id.iteritems():
            if len(entries) > 1:
                entries_per_msg = defaultdict(list)

                for entry in entries:
                    entries_per_msg[entry.msgstr].append(entry)

                if len(entries_per_msg) == 1:
                    if not_diverging:
                        msg_entries = entries_per_msg.itervalues().next()
                        print '[doublon] {%s} in %s' % (msgid, [entry.file_path for entry in msg_entries])

                        problems_count += 1
                else:
                    cxt_conflict = bool(reduce(lambda s1, s2: s1 & s2,
                                               (set(entry.msgctxt for entry in msg_entries)
                                                    for msg_entries in entries_per_msg.itervalues()
                                               )
                                              )
                                       )

                    if not cxt_conflict and no_context:
                        cxt_conflict = any(entry.msgctxt is None
                                              for msg_entries in entries_per_msg.itervalues()
                                                  for entry in msg_entries
                                          )

                    if cxt_conflict:
                        print '[diverging]\n {%s} in :' % msgid

                        for msgstr, msg_entries in entries_per_msg.iteritems():
                            print '    {%s} in %s' % (msgstr, [(entry.file_path, entry.msgctxt) for entry in msg_entries])

                        problems_count += 1

        if verbosity >= 1:
            print '\nNumber of problems:', problems_count
