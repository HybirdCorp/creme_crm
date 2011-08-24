# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.core.management.base import BaseCommand

from creme_core.utils.unicode_csv import UnicodeReader


class CSVImportCommand(BaseCommand):
    """Base class for commands that import CSV files.
    Useful for CSV files that can not be easily managed by the generic visual
    CSV import system.
    """
    help = "import data from a CSV file (base class)"
    args = 'CSV filename'

    def _read(self, filename, callback, delimiter=','):
        with open(filename, 'rb') as csvfile:
            it = iter(UnicodeReader(csvfile, delimiter=delimiter))

            try:
                header = next(it)
            except:
                print 'Void file ??!!'
                raise

            for i, line in enumerate(it, start=1):
                callback(i, line, dict((col, val) for col, val in zip(header, line) if col))

    def _manage_line(self, idx, line, line_dict):
        """Overload this method."""
        raise NotImplementedError

    def handle(self, csv_filename, *app_labels, **options):
        self._read(csv_filename, callback=self._manage_line, delimiter=";")


#EXAMPLE

## Content of 'my_file.csv' ----------------------------------------------------

#"Organisation";"Manager";"Address 1";"Address 2";"PO";"City";"Zip";"Department";"Phone";"Email"
#"NERV";"Gendô IKARI";"12, Avenue of the bearded";"Block 2";"12345";"NeoTôkyô";"XXX-XXX";"Kantô";"666666";"gendo.ikari@nerv.org"
#etc....


## Content of 'my_app/management/commands/my_import.py' ------------------------
##  [so command is: > python manage.py my_import path/to/my_file.csv]

#from django.contrib.auth.models import User
#
#from creme_core.models import Relation, RelationType
#from creme_core.management.base import CSVImportCommand
#
#from persons.models import Contact, Organisation, Address
#from persons.constants import REL_SUB_MANAGES
#
#
#class Command(CSVImportCommand):
#    help = "import organisations and their manager"
#
#    def _create_contact(self, raw, organisation):
#        names = raw.split(None, 1)
#
#        if len(names) == 1:
#            first_name = ''
#            last_name = names[0]
#        else:
#            first_name = names[0]
#            last_name = names[1]
#
#        return Contact.objects.get_or_create(last_name=last_name,
#                                                         first_name=first_name,
#                                                         user=self.user,
#                                                        )[0]
#
#    def handle_manager(self, raw, organisation):
#        if raw:
#            Relation.objects.get_or_create(subject_entity=self._create_contact(raw, organisation),
#                                           type=self.rtype_manages,
#                                           object_entity=organisation,
#                                           user=self.user
#                                          )
#
#    def _manage_line(self, idx, line, line_dict):
#        l_get = line_dict.get
#
#        try:
#            organisation, is_created = Organisation.objects.get_or_create(name=l_get(u'Organisation'), user=self.user)
#
#            phone = l_get(u'Phone')
#            if phone and not organisation.phone:
#                organisation.phone = phone
#
#            email = l_get(u'Email')
#            if email and not organisation.email:
#                organisation.email = email
#
#            if not organisation.billing_address:
#                organisation.billing_address = Address.objects.create(
#                        owner=organisation,
#                        address='%s %s' % (l_get('Address 1'), l_get('Address 2')),
#                        po_box=l_get(u'PO'),
#                        city=l_get(u'City'),
#                        zipcode=l_get(u'Zip'),
#                        department=l_get(u'Department'),
#                    )
#
#            organisation.save()
#            self.handle_manager(l_get(u'Manager'), organisation)
#        except Exception, e:
#            print "An error occurred at line :", line
#            print e
#
#    def handle(self, csv_filename, *app_labels, **options):
#        print 'Importing organisation...'
#
#        try:
#            self.user = User.objects.get(pk=1)
#            self.rtype_manages = RelationType.objects.get(pk=REL_SUB_MANAGES)
#        except Exception, e:
#            print 'Error (%s): have you run the populates ???' % e
#            print 'Importing organisation [KO]'
#        else:
#            self._read(csv_filename, self._manage_line, delimiter=";")
#
#            print 'Importing organisation [OK]'
#            print '    Organisations in database:', Organisation.objects.count()
#            print '    Contacts in database':, Contact.objects.count()
