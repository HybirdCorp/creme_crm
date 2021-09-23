from creme.creme_core.models import (
    CustomField,
    FakeCivility,
    FakeContact,
    FakePosition,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.crudity.core import (
    CRUDityExtractor,
    CRUDityExtractorRegistry,
    CustomFieldExtractor,
    RegularFieldExtractor,
)


class CRUDityExtractorTestCase(CremeTestCase):
    def test_regularfield_extractor(self):
        contact = FakeContact()
        model = type(contact)
        field_name1 = 'last_name'
        field_name2 = 'first_name'

        last_name = 'Spiegel'
        first_name = 'Spike'
        data = {
            field_name1: last_name,
            field_name2: first_name,
        }

        # TODO: generate a form-field instead?
        # TODO: use another word than "extract" (it injects too)?
        extractor1 = RegularFieldExtractor(
            # model=model, field_name=field_name1,
            model=model, value=field_name1,
        )
        self.assertEqual('regular_field',  extractor1.type_id)
        self.assertEqual(model,            extractor1.model)
        self.assertEqual(field_name1,      extractor1.field_name)

        extractor1.extract(instance=contact, data=data)
        self.assertEqual(last_name, contact.last_name)
        self.assertFalse(contact.first_name)

        RegularFieldExtractor(
            # model=type(contact), field_name=field_name2,
            model=type(contact), value=field_name2,
        ).extract(instance=contact, data=data)
        self.assertEqual(first_name, contact.first_name)

        # No data
        with self.assertNoException():
            extractor1.extract(
                instance=contact,
                data={
                    # field_name1: last_name,
                    field_name2: first_name,
                },
            )

    def test_customfield_extractor(self):
        user = self.create_user()
        contact = FakeContact.objects.create(user=user, last_name='Spiegel')
        model = type(contact)
        cfield = CustomField.objects.create(
            content_type=contact.entity_type,
            field_type=CustomField.STR,
            name='Nickname',
        )

        # extractor = CustomFieldExtractor(model=model, custom_field_id=cfield.id)
        extractor = CustomFieldExtractor(model=model, value=cfield.id)
        self.assertEqual('custom_field', extractor.type_id)
        self.assertEqual(model,          extractor.model)
        self.assertEqual(cfield,         extractor.custom_field)

        nick_name = 'The little dragon'
        extractor.extract(
            instance=contact,
            data={
                f'custom_field-{cfield.id}': nick_name,
                'first_name': 'Spike',  # TODO: 'regular_field-first_name' ???
            },
        )
        self.assertEqual(
            nick_name,
            cfield.value_class.objects.get(custom_field=cfield.id, entity=contact.id).value,
        )

        # No data
        with self.assertNoException():
            extractor.extract(
                instance=contact,
                data={
                    # f'custom_field-{cfield.id}': nick_name,
                    'first_name': 'Spike',
                },
            )

    def test_eq(self):
        self.assertEqual(
            RegularFieldExtractor(model=FakeCivility, value='title'),
            RegularFieldExtractor(model=FakeCivility, value='title'),
        )
        self.assertNotEqual(
            RegularFieldExtractor(model=FakeCivility, value='title'),
            RegularFieldExtractor(model=FakePosition, value='title'),
        )
        self.assertNotEqual(
            RegularFieldExtractor(model=FakeCivility, value='title'),
            RegularFieldExtractor(model=FakeCivility, value='shortcut'),
        )

    def test_to_dict(self):
        self.assertDictEqual(
            {'key': 'regular_field-title'},  # TODO: 'extractor_type': 'basic',
            RegularFieldExtractor(model=FakeCivility, value='title').to_dict(),
        )

        cfield = CustomField.objects.create(
            content_type=FakeContact,
            field_type=CustomField.STR,
            name='Nickname',
        )
        self.assertDictEqual(
            {'key': f'custom_field-{cfield.id}'},
            CustomFieldExtractor(model=FakeContact, value=cfield.id).to_dict(),
        )

    def test_registry(self):
        registry = CRUDityExtractorRegistry()
        model = FakeContact
        self.assertFalse([*registry.build_extractors(model=model, dicts=[])])

        field_name = 'last_name'
        cfield = CustomField.objects.create(
            content_type=model,
            field_type=CustomField.STR,
            name='Nickname',
        )

        data = [
            {
                # 'cell_key': f'regular_field-{field_name}',
                'key': f'regular_field-{field_name}',
                'extractor_type': 'basic',
            }, {
                # 'cell_key': f'custom_field-{cfield.id}',
                'key': f'custom_field-{cfield.id}',
                'extractor_type': 'basic',
            },
        ]

        with self.assertRaises(CRUDityExtractor.InvalidExtractor) as cm1:
            _ = [*registry.build_extractors(model=model, dicts=data)]

        self.assertEqual(
            'the type ID "regular_field" is invalid',
            str(cm1.exception),
        )

        # ---
        registry.register(RegularFieldExtractor)
        registry.register(CustomFieldExtractor)

        extractors = [*registry.build_extractors(model=model, dicts=data)]
        self.assertEqual(2, len(extractors))

        extractor1 = extractors[0]
        self.assertIsInstance(extractor1, RegularFieldExtractor)
        self.assertEqual(model,      extractor1.model)
        self.assertEqual(field_name, extractor1.field_name)

        extractor2 = extractors[1]
        self.assertIsInstance(extractor2, CustomFieldExtractor)
        self.assertEqual(model,  extractor2.model)
        self.assertEqual(cfield, extractor2.custom_field)

    def test_registry_error01(self):
        registry = CRUDityExtractorRegistry()

        with self.assertRaises(CRUDityExtractor.InvalidExtractor) as cm:
            _ = [*registry.build_extractors(
                model=FakeContact,
                # dicts=[{'cell_key': 'invalid', 'extractor_type': 'basic'}],
                dicts=[{'key': 'invalid', 'extractor_type': 'basic'}],
            )]

        self.assertEqual(
            # 'the cell key "invalid" is malformed',
            'the key "invalid" is malformed',
            str(cm.exception),
        )

    def test_registry_error02(self):
        registry = CRUDityExtractorRegistry()

        with self.assertRaises(CRUDityExtractor.InvalidExtractor) as cm:
            _ = [*registry.build_extractors(
                model=FakeContact,
                # dicts=[{'extractor_type': 'basic'}],  # No <'cell_key': '...'>
                dicts=[{'extractor_type': 'basic'}],  # No <'key': '...'>
            )]

        # self.assertEqual('the cell key is missing', str(cm.exception))
        self.assertEqual('the key is missing', str(cm.exception))
