from creme.creme_core.core.snapshot import Snapshot
from creme.creme_core.models import (
    CustomField,
    CustomFieldValue,
    FakeContact,
    FakeOrganisation,
    FakeSector,
)

from ..base import CremeTestCase


class SnapshotTestCase(CremeTestCase):
    def test_regular_field(self):
        user = self.get_root_user()
        first_name = 'John'
        last_name = 'Doe'
        contact1 = FakeContact.objects.create(
            user=user, first_name=first_name, last_name=last_name,
        )
        self.assertIsNone(Snapshot.get_for_instance(contact1))

        # Compare (no change) ---
        contact1 = self.refresh(contact1)
        snapshot = Snapshot.get_for_instance(contact1)
        self.assertIsInstance(snapshot, Snapshot)
        self.assertEqual(FakeContact, snapshot.model)
        self.assertListEqual([], [*snapshot.compare(contact1)])

        # Compare (one change) ---
        contact1.description = description = 'New value'
        contact1.not_a_field = 'A value'

        diff = self.get_alone_element([*snapshot.compare(contact1)])
        self.assertIsInstance(diff, Snapshot.Difference)
        self.assertEqual(FakeContact._meta.get_field('description'), diff.field)
        self.assertEqual('description',                              diff.field_name)
        self.assertEqual('',                                         diff.old_value)
        self.assertEqual(description,                                diff.new_value)

        # Get initial instance ---
        contact2 = snapshot.get_initial_instance()
        self.assertIsInstance(contact2, FakeContact)
        self.assertIsNot(contact1, contact2)
        self.assertEqual(user,       contact2.user)
        self.assertEqual(first_name, contact2.first_name)
        self.assertEqual(last_name,  contact2.last_name)

    def test_regular_fields(self):
        user = self.get_root_user()
        old_description = 'Unknown'
        sector1, sector2 = FakeSector.objects.all()[:2]
        contact = self.refresh(FakeContact.objects.create(
            user=user, first_name='John', last_name='Doe',
            description=old_description,
            sector=sector1,
        ))

        # ---
        contact.description = description = 'Very mysterious'
        contact.sector = sector2

        all_diff = [*Snapshot.get_for_instance(contact).compare(contact)]
        self.assertEqual(2, len(all_diff), all_diff)

        diff1 = all_diff[0]
        self.assertEqual('description',   diff1.field_name)
        self.assertEqual(old_description, diff1.old_value)
        self.assertEqual(description,     diff1.new_value)

        diff2 = all_diff[1]
        self.assertEqual('sector_id', diff2.field_name)
        self.assertEqual(sector1.id,  diff2.old_value)
        self.assertEqual(sector2.id,  diff2.new_value)

    def test_compare_error(self):
        user = self.get_root_user()
        contact = self.refresh(FakeContact.objects.create(
            user=user, first_name='John', last_name='Doe',
        ))
        snapshot = Snapshot.get_for_instance(contact)

        with self.assertRaises(TypeError):
            next(snapshot.compare(FakeOrganisation(user=user, name='Acme')))

    def test_custom_field(self):
        user = self.get_root_user()

        cfield = CustomField.objects.create(
            name='Size (cm)', field_type=CustomField.INT, content_type=FakeContact,
        )

        contact = FakeContact.objects.create(
            user=user, first_name='John', last_name='Doe',
        )
        old_value = 175
        CustomFieldValue.save_values_for_entities(cfield, [contact], old_value)

        # Compare (no change) ---
        contact = self.refresh(contact)
        snapshot = Snapshot.get_for_instance(contact)
        diff1 = snapshot.compare_custom_field(instance=contact, custom_field=cfield)
        self.assertIsNone(diff1)

        # Compare ---
        new_value = 180
        CustomFieldValue.save_values_for_entities(cfield, [contact], new_value)
        self.assertEqual(new_value, contact.get_custom_value(cfield).value)

        diff2 = snapshot.compare_custom_field(instance=contact, custom_field=cfield)
        self.assertIsInstance(diff2, Snapshot.Difference)
        self.assertEqual('value',   diff2.field_name)
        self.assertEqual(old_value, diff2.old_value)
        self.assertEqual(new_value, diff2.new_value)

        # Get initial instance ---
        contact2 = snapshot.get_initial_instance()
        self.assertIsInstance(contact2, FakeContact)
        self.assertIsNot(contact, contact2)
        self.assertEqual(old_value, contact2.get_custom_value(cfield).value)
