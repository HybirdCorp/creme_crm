from functools import partial

from creme.creme_core.core.snapshot import Snapshot
from creme.creme_core.models import (
    CustomField,
    CustomFieldEnumValue,
    CustomFieldValue,
    FakeContact,
    FakeCountry,
    FakeOrganisation,
    FakeSector,
    Language,
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

    def test_compare__different_model(self):
        user = self.get_root_user()
        contact = self.refresh(FakeContact.objects.create(
            user=user, first_name='John', last_name='Doe',
        ))
        snapshot = Snapshot.get_for_instance(contact)

        with self.assertRaises(TypeError):
            next(snapshot.compare(FakeOrganisation(user=user, name='Acme')))

    def test_compare__invalid_value(self):
        contact = FakeContact.objects.create(
            user=self.get_root_user(), first_name='John', last_name='Doe',
        )
        self.assertIsNone(Snapshot.get_for_instance(contact))

        contact = self.refresh(contact)
        snapshot = Snapshot.get_for_instance(contact)
        contact.birthday = 'Not date'

        with self.assertLogs(level='CRITICAL'):
            diffs = [*snapshot.compare(contact)]
        self.assertFalse(diffs)

        # ---
        contact = self.refresh(contact)
        sector_id = FakeSector.objects.first().id
        snapshot = Snapshot.get_for_instance(contact)
        contact.sector_id = str(sector_id)

        with self.assertNumQueries(0):
            diff = self.get_alone_element([*snapshot.compare(contact)])

        self.assertEqual(None,           diff.old_value)
        self.assertEqual(str(sector_id), diff.new_value)  # TODO: cast anyway?

    def test_m2m(self):
        user = self.get_root_user()
        contact1 = FakeContact.objects.create(
            user=user, first_name='John', last_name='Doe',
        )

        l1, l2, l3 = Language.objects.all()[:3]
        c1 = FakeCountry.objects.create(name='Wonderland')

        contact1.languages.set([l1])
        contact1.preferred_countries.set([c1])
        self.assertListEqual([l1], contact1.get_m2m_values('languages'))
        self.assertListEqual([c1], contact1.get_m2m_values('preferred_countries'))

        contact1 = self.refresh(contact1)
        contact1.languages.remove(l1)
        contact1.languages.add(l2)

        contact2 = Snapshot.get_for_instance(contact1).get_initial_instance()
        self.assertListEqual([l2], contact1.get_m2m_values('languages'))
        self.assertListEqual([l1], contact2.get_m2m_values('languages'))

        self.assertListEqual([c1], contact1.get_m2m_values('preferred_countries'))
        self.assertListEqual([c1], contact2.get_m2m_values('preferred_countries'))

        # Cache not initialized ---
        contact3 = Snapshot.get_for_instance(self.refresh(contact1)).get_initial_instance()
        self.assertListEqual([l2], contact3.get_m2m_values('languages'))

    def test_custom_field__int(self):
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
        # TODO?
        # diff1 = snapshot.compare_custom_field(instance=contact, custom_field=cfield)
        # self.assertIsNone(diff1)

        # Compare ---
        new_value = 180
        CustomFieldValue.save_values_for_entities(cfield, [contact], new_value)
        self.assertEqual(new_value, contact.get_custom_value(cfield).value)

        # TODO?
        # diff2 = snapshot.compare_custom_field(instance=contact, custom_field=cfield)
        # self.assertIsInstance(diff2, Snapshot.Difference)
        # self.assertEqual('value',   diff2.field_name)
        # self.assertEqual(old_value, diff2.old_value)
        # self.assertEqual(new_value, diff2.new_value)

        # Get initial instance ---
        contact2 = snapshot.get_initial_instance()
        self.assertIsInstance(contact2, FakeContact)
        self.assertIsNot(contact, contact2)
        self.assertEqual(old_value, contact2.get_custom_value(cfield).value)

    def test_custom_field__enum(self):
        cfield = CustomField.objects.create(
            name='Job', field_type=CustomField.ENUM, content_type=FakeContact,
        )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield)
        j1 = create_evalue(value='Fireman')
        j2 = create_evalue(value='Baker')

        contact = FakeContact.objects.create(
            user=self.get_root_user(), first_name='John', last_name='Doe',
        )
        CustomFieldValue.save_values_for_entities(cfield, [contact], j1.id)

        contact = self.refresh(contact)
        snapshot = Snapshot.get_for_instance(contact)

        CustomFieldValue.save_values_for_entities(cfield, [contact], j2.id)
        self.assertEqual(j2, contact.get_custom_value(cfield).value)

        contact2 = snapshot.get_initial_instance()
        self.assertEqual(j1, contact2.get_custom_value(cfield).value)

    def test_custom_field__multienum(self):
        cfield = CustomField.objects.create(
            name='Hobbies', field_type=CustomField.MULTI_ENUM, content_type=FakeContact,
        )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield)
        h1 = create_evalue(value='Painting')
        h2 = create_evalue(value='Dancing')

        contact = FakeContact.objects.create(
            user=self.get_root_user(), first_name='John', last_name='Doe',
        )
        CustomFieldValue.save_values_for_entities(cfield, [contact], [h1.id])

        contact = self.refresh(contact)
        snapshot = Snapshot.get_for_instance(contact)

        CustomFieldValue.save_values_for_entities(cfield, [contact], [h2.id])
        self.assertListEqual([h2], [*contact.get_custom_value(cfield).get_enumvalues()])

        contact2 = snapshot.get_initial_instance()
        self.assertListEqual([h1], [*contact2.get_custom_value(cfield).get_enumvalues()])
