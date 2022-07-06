# EXAMPLE OF COMMAND INHERITING <creme.creme_core.management.base.CSVImportCommand>

from django.contrib.auth import get_user_model

from creme import persons
from creme.creme_core.management.base import CSVImportCommand
from creme.creme_core.models import Relation, RelationType
from creme.persons.constants import REL_SUB_MANAGES

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()
Address = persons.get_address_model()


# Content of 'my_file.csv' -----------------------------------------------------
#
# "Organisation";"Manager";"Address 1";"Address 2";"PO";"City";"Zip";"Department";"Phone";"Email"
# "NERV";"Gendô IKARI";"12, Avenue of the bearded";"Block 2";"12345";"NeoTôkyô";"XXX-XXX";"Kantô";"666666";"gendo.ikari@nerv.org"  # NOQA
# etc....
# ------------------------------------------------------------------------------

# Put your .py file in the directory 'my_app/management/commands/'
# Run command with:
#  > creme name_of_my_py_file path/to/my_file.csv
class Command(CSVImportCommand):
    help = "Import organisations and their manager."

    def _create_contact(self, raw):
        names = raw.split(None, 1)

        if len(names) == 1:
            first_name = ''
            last_name = names[0]
        else:
            first_name = names[0]
            last_name = names[1]

        return Contact.objects.get_or_create(
            last_name=last_name, first_name=first_name,
            defaults={'user': self.user},
        )[0]

    def handle_manager(self, raw, organisation):
        if raw:
            Relation.objects.safe_get_or_create(
                subject_entity=self._create_contact(raw),
                type=self.rtype_manages,
                object_entity=organisation,
                user=self.user,
            )

    def _manage_line(self, idx, line, line_dict):
        l_get = line_dict.get

        try:
            # NB: duplicates are not managed in this example; if several
            #     Organisations use this name an exception
            #     'Organisation.MultipleObjectsReturned' will be raised.
            organisation, is_created = Organisation.objects.get_or_create(
                name=l_get('Organisation'),
                defaults={'user': self.user},
            )

            phone = l_get('Phone')
            if phone and not organisation.phone:
                organisation.phone = phone

            email = l_get('Email')
            if email and not organisation.email:
                organisation.email = email

            if not organisation.billing_address:
                organisation.billing_address = Address.objects.create(
                    owner=organisation,
                    address='{}, {}'.format(l_get('Address 1'), l_get('Address 2')),
                    po_box=l_get('PO'),
                    city=l_get('City'),
                    zipcode=l_get('Zip'),
                    department=l_get('Department'),
                )

            organisation.full_clean()
            organisation.save()
            self.handle_manager(l_get('Manager'), organisation)
        except Exception as e:
            self.stderr.write(f'An error occurred at line: {line}')
            self.stderr.write(e)

    def handle(self, *csv_filenames, **options):
        self.stdout.write('Importing organisation...')

        try:
            self.user = get_user_model().objects.get_admin()
            self.rtype_manages = RelationType.objects.get(pk=REL_SUB_MANAGES)
        except Exception as e:
            self.stderr.write(f'Error ({e}): have you run the populates ???')
            self.stderr.write('Importing organisation [KO]')
        else:
            super().handle(*csv_filenames, **options)

            self.stdout.write('Importing organisation [OK]')
            self.stdout.write(
                f'    Organisations in database: {Organisation.objects.count()}'
            )
            self.stdout.write(
                f'    Contacts in database: {Contact.objects.count()}'
            )
