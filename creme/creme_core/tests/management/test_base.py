from os import path as os_path

from django.core.management import CommandError, call_command

from creme import persons
from creme.creme_core.management.csv_import_example import (
    Command as ImportCommand,
)
from creme.persons.constants import REL_SUB_MANAGES
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from .. import base


class CSVImportCommandTestCase(base.CremeTestCase):
    def test_no_file_argument(self):
        with self.assertRaises(CommandError) as cm:
            call_command(ImportCommand())

        self.assertEqual(
            'Error: the following arguments are required: csv_file',
            str(cm.exception),
        )

    def test_no_file(self):
        with self.assertRaises(FileNotFoundError) as cm:
            call_command(ImportCommand(), 'invalid.csv')

        self.assertIn(
            "No such file or directory: 'invalid.csv'",
            str(cm.exception),
        )

    @skipIfCustomAddress
    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_ok(self):
        path = os_path.join(os_path.dirname(__file__), 'data', 'example01.csv')
        self.assertTrue(os_path.exists(path))

        with self.assertNoException():
            call_command(ImportCommand(), path)

        orga = self.get_object_or_fail(
            persons.get_organisation_model(), name='NERV',
        )
        self.assertEqual('666666', orga.phone)
        self.assertEqual('gendo.ikari@nerv.org', orga.email)

        address = orga.billing_address
        self.assertIsNotNone(address)
        self.assertEqual(orga, address.owner)
        self.assertEqual('12, Avenue of the bearded, Block 2', address.address)
        self.assertEqual('NeoTôkyô', address.city)

        contact = self.get_object_or_fail(
            persons.get_contact_model(), first_name='Gendô', last_name='IKARI',
        )
        self.assertHaveRelation(subject=contact, type=REL_SUB_MANAGES, object=orga)
