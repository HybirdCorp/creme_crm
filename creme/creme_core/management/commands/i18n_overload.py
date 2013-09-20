# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from __future__ import print_function

from datetime import datetime
from optparse import make_option, OptionParser
from os import listdir, makedirs, sep
from os.path import join, exists, isdir

import pytz

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.encoding import smart_unicode


APP_NAME = 'locale_overload' #TODO: can configure it with command options ??


#TODO: factorise with i18n_doublons ?
class Command(BaseCommand):
    help = 'Find some terms in .po files of your project and create/update a ' \
           'translation file with the messages containing one of these terms.\n' \
           'The purpose is to overload some terms for a specific instance of your project.'
    args = 'term1 term2 ... termN'
    option_list = BaseCommand.option_list + (
                     make_option('-l', '--language', action='store', dest='language',
                                 default='en', help='Search terms in LANGUAGE files. '
                                                    '[default: %default]'
                                ),
                    )

    def create_parser(self, prog_name, subcommand):
        return OptionParser(prog=prog_name,
                            usage=self.usage(subcommand),
                            version=self.get_version(),
                            option_list=self.option_list,
                            conflict_handler='resolve',
                           )

    def handle(self, *args, **options):
        if not args:
            print('Error: give at least one term')
            return

        try:
            from polib import pofile, POFile
        except ImportError as e:
            print(e)
            print('The required "polib" library seems not installed ; aborting.')
            return

        verbosity = int(options.get('verbosity'))

        if verbosity >= 2:
            print('OK "polib" library is installed.')

        language = options.get('language')
        catalog_entries = {}

        catalog_dirpath = join(settings.CREME_ROOT, APP_NAME, 'locale', language, 'LC_MESSAGES')
        catalog_path = join(catalog_dirpath, 'django.po')

        if exists(catalog_path):
            catalog = pofile(catalog_path)

            for entry in catalog.translated_entries():
                entry.obsolete = True
                catalog_entries[entry.msgid] = entry
        else:
            if verbosity >= 1:
                print('Create catalog at ', catalog_path)

            if not exists(catalog_dirpath):
                makedirs(catalog_dirpath)
            elif not isdir(catalog_dirpath):
                print('Error: "%s" exists and is not a directory.' % catalog_dirpath)
                return

            catalog = POFile()
            catalog.metadata = {
                    'Project-Id-Version':        'PACKAGE VERSION',
                    'Report-Msgid-Bugs-To':      '',
                    'PO-Revision-Date':          'YEAR-MO-DA HO:MI+ZONE',
                    'Last-Translator':           'FULL NAME <EMAIL@ADDRESS>',
                    'Language-Team':             'LANGUAGE <LL@li.org>',
                    'MIME-Version':              '1.0',
                    'Content-Type':              'text/plain; charset=UTF-8',
                    'Content-Transfer-Encoding': '8bit',
                    'Plural-Forms':              'nplurals=2; plural=n>1;',
                }

        catalog.metadata['POT-Creation-Date'] = pytz.timezone(settings.TIME_ZONE) \
                                                    .localize(datetime.now()) \
                                                    .strftime('%Y-%m-%d %H:%M%z')

        #terms = map(smart_unicode, args)
        terms = [smart_unicode(arg) for arg in args]
        entry_count = 0

        for app_name in settings.INSTALLED_CREME_APPS:
            #basepath = '%s/locale/%s/LC_MESSAGES/' % (app_name, language)
            basepath = join(app_name.replace('.', sep), #creme.creme_core => creme/creme_core
                            'locale', language, 'LC_MESSAGES',
                           )

            if exists(basepath):
                for fname in listdir(basepath):
                    if fname.endswith('.po'):
                        path = join(basepath, fname)

                        for entry in pofile(path).translated_entries():
                            entry_count += 1
                            msgid = entry.msgid

                            existing_entry = catalog_entries.get(msgid)

                            #TODO: manage context (key=msgid + context ?)
                            if existing_entry is not None:
                                if existing_entry.obsolete: #entry has not been updated yet
                                    existing_entry.obsolete = False
                                    existing_entry.occurrences = entry.occurrences
                                else:
                                    existing_entry.occurrences += entry.occurrences
                            else:
                                for term in terms:
                                    if term in msgid: #TODO: what about case sensitivity ?
                                        entry.flags.append('fuzzy')
                                        catalog.append(entry)
                                        catalog_entries[entry.msgid] = entry
                                        break

        catalog.save(catalog_path)

        if verbosity >= 1:
            print('Number of examinated entries:', entry_count)
