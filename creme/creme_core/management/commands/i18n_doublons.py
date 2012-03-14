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
    help = 'Find doublons in .po files of your project.'
    option_list = BaseCommand.option_list + (
                     make_option('-l', '--language', action='store', dest='language',
                                 default='en', help='Search doublons for LANGUAGE files. '
                                                    '[default: %default]'
                                ),
                     make_option('-d', '--only_diverging', action='store_true',
                                 dest='only_diverging', default=True,
                                 help='Display only diverging translations '
                                      '(different translations for the same key). [default: %default]'
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

        print 'OK "polib" library is installed.'

        language = options.get('language')
        only_diverging = options.get('only_diverging')
        entry_count = 0
        entries = defaultdict(list)

        for app_name in settings.INSTALLED_CREME_APPS:
            basepath = '%s/locale/%s/LC_MESSAGES/' % (app_name, language)

            if exists(basepath):
                for fname in listdir(basepath):
                    if fname.endswith('.po'):
                        path = join(basepath, fname)

                        for entry in pofile(path).translated_entries():
                            entry_count += 1
                            entries[entry.msgid].append((entry.msgstr, path))

        print 'Number of entries:', entry_count

        for msgid, trans_info in entries.iteritems():
            if len(trans_info) > 1:
                analysis = defaultdict(list)

                for msgstr, path in trans_info:
                    analysis[msgstr].append(path)

                if len(analysis) == 1:
                    if not only_diverging:
                        paths = analysis.itervalues().next()
                        print '[doublon] {%s} in %s' % (msgid, paths)
                else:
                    print '[diverging] {%s}' % msgid
                    for msgstr, paths in analysis.iteritems():
                        print '    {%s} in %s' % (msgstr, paths)
