# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

import csv

from django.core.management.base import BaseCommand


class CSVImportCommand(BaseCommand):
    """Base class for commands which import CSV files.
    Useful for CSV files that can not be easily managed by the generic visual
    CSV import system.
    """
    help = "Import data from a CSV file (base class)."
    # args = 'CSV filename'

    def add_arguments(self, parser):
        parser.add_argument(
            'args', metavar='csv_file', nargs='+',
            help='Path of the file to import',
        )

    def _read(self, filename, callback, delimiter=','):
        with open(filename, 'r') as csvfile:
            it = csv.reader(csvfile, delimiter=delimiter)

            try:
                header = next(it)
            except Exception:
                self.stderr.write('Void file ??!!')
                raise

            for i, line in enumerate(it, start=1):
                callback(i, line, {col: val for col, val in zip(header, line) if col})

    def _manage_line(self, idx, line, line_dict):
        """Overload this method."""
        raise NotImplementedError

    def handle(self, *csv_filenames, **options):
        for csv_filename in csv_filenames:
            self._read(csv_filename, callback=self._manage_line, delimiter=';')


# EXAMPLE

# Content of 'my_file.csv' ----------------------------------------------------

# "Organisation";"Manager";"Address 1";"Address 2";"PO";"City";"Zip";"Department";"Phone";"Email"
# "NERV";"Gendô IKARI";"12, Avenue of the bearded";"Block 2";"12345";"NeoTôkyô";"XXX-XXX";"Kantô";"666666";"gendo.ikari@nerv.org"  # NOQA
# etc....

# Content of 'my_app/management/commands/my_import.py' ------------------------
# [so command is: > python creme/manage.py my_import path/to/my_file.csv]

# from django.contrib.auth import get_user_model
#
# from creme.creme_core.models import Relation, RelationType
# from creme.creme_core.management.base import CSVImportCommand
#
# from creme.persons import get_contact_model, get_organisation_model, get_address_model
# from creme.persons.constants import REL_SUB_MANAGES
#
# Contact = get_contact_model()
# Organisation = get_organisation_model()
# Address = get_address_model()
#
# class Command(CSVImportCommand):
#     help = "import organisations and their manager"
#
#     def _create_contact(self, raw):
#         names = raw.split(None, 1)
#
#         if len(names) == 1:
#             first_name = ''
#             last_name = names[0]
#         else:
#             first_name = names[0]
#             last_name = names[1]
#
#         return Contact.objects.get_or_create(last_name=last_name,
#                                              first_name=first_name,
#                                              user=self.user,
#                                             )[0]
#
#     def handle_manager(self, raw, organisation):
#         if raw:
#             Relation.objects.get_or_create(subject_entity=self._create_contact(raw),
#                                            type=self.rtype_manages,
#                                            object_entity=organisation,
#                                            defaults={'user': self.user},
#                                           )
#
#     def _manage_line(self, idx, line, line_dict):
#         l_get = line_dict.get
#
#         try:
#             organisation, is_created = Organisation.objects.get_or_create(
#                 name=l_get('Organisation'), user=self.user,
#             )
#
#             phone = l_get('Phone')
#             if phone and not organisation.phone:
#                 organisation.phone = phone
#
#             email = l_get('Email')
#             if email and not organisation.email:
#                 organisation.email = email
#
#             if not organisation.billing_address:
#                 organisation.billing_address = Address.objects.create(
#                         owner=organisation,
#                         address='{} {}'.format(l_get('Address 1'), l_get('Address 2')),
#                         po_box=l_get('PO'),
#                         city=l_get('City'),
#                         zipcode=l_get('Zip'),
#                         department=l_get('Department'),
#                     )
#
#             organisation.full_clean()
#             organisation.save()
#             self.handle_manager(l_get('Manager'), organisation)
#         except Exception as e:
#             self.stderr.write('An error occurred at line: {}'.format(line))
#             self.stderr.write(e)
#
#     def handle(self, *csv_filenames, **options):
#         self.stdout.write('Importing organisation...')
#
#         try:
#             self.user = get_user_model().objects.get(pk=1)
#             self.rtype_manages = RelationType.objects.get(pk=REL_SUB_MANAGES)
#         except Exception as e:
#             self.stderr.write('Error ({}): have you run the populates ???'.format(e))
#             self.stderr.write('Importing organisation [KO]')
#         else:
#             super().handle(*csv_filenames, **options)
#
#             self.stdout.write('Importing organisation [OK]')
#             self.stdout.write(
#                 '    Organisations in database: {}'.format(Organisation.objects.count())
#             )
#             self.stdout.write(
#                 '    Contacts in database: {}'.format(Contact.objects.count())
#             )
