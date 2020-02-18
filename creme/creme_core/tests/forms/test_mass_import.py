# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.core.exceptions import ValidationError
    from django.forms import CharField
    from django.forms.widgets import TextInput
    from django.utils.translation import gettext as _

    # from .base import FieldTestCase
    from ..base import CremeTestCase

    from creme.creme_core.models import (
        CustomField, CustomFieldEnumValue,
        FakeContact, FakeSector,
    )
    from creme.creme_core.forms.mass_import import (
        Extractor, CustomFieldExtractor,
        ExtractorWidget, CustomFieldExtractorWidget,
        ExtractorField, CustomfieldExtractorField,
    )
except Exception as e:
    print(f'Error in <{__name__}>: {e}')

# TODO: complete
#    - complete existing test cases
#    - test other extractors
#    - test other fields
#         - EntityExtractorField
#         - RelationExtractorField
#    - test widgets ?


class ExtractorTestCase(CremeTestCase):
    def test_extract01(self):
        default_value = '??'
        extractor = Extractor(
            column_index=1,
            default_value=default_value,
            value_castor=str,
        )
        line1 = ['Claus', 'Valca']
        self.assertEqual((line1[0], None), extractor.extract_value(line1))

        line2 = ['Lavie', 'Head']
        self.assertEqual((line2[0], None), extractor.extract_value(line2))

        line3 = ['', 'Hamilton']
        self.assertEqual((default_value, None), extractor.extract_value(line3))

    def test_extract02(self):
        "Other index, casting."
        default_value = 42
        extractor = Extractor(
            column_index=3,
            default_value=default_value,
            value_castor=int,
        )
        line1 = ['Claus', 'Valca', '17']
        self.assertEqual((17, None), extractor.extract_value(line1))

        line2 = ['Lavie', 'Head', '']
        self.assertEqual((default_value, None), extractor.extract_value(line2))

        line3 = ['Lavie', 'Head', 'notanint']
        self.assertEqual(
            (default_value, "invalid literal for int() with base 10: 'notanint'"),
            extractor.extract_value(line3)
        )

    def test_extract03(self):
        "Sub-field search."
        extractor = Extractor(
            column_index=3,
            default_value=None,
            value_castor=int,
        )
        extractor.set_subfield_search(
            subfield_search='title',
            subfield_model=FakeSector,
            multiple=False,
            create_if_unfound=False,
        )

        sector1, sector2 = FakeSector.objects.all()[:2]

        line1 = ['Claus', 'Valca', sector1.title]
        self.assertEqual((sector1, None), extractor.extract_value(line1))

        line2 = ['Lavie', 'Head', sector2.title]
        self.assertEqual((sector2, None), extractor.extract_value(line2))

        line3 = ['Alvis', 'Hamilton', '']
        self.assertEqual((None, None), extractor.extract_value(line3))

        line4 = ['Alex', 'Row', 'Unknown sector']
        value4, err_msg4 = extractor.extract_value(line4)
        self.assertIsNone(value4)
        self.assertEqual(
            _('Error while extracting value: tried to retrieve '
              '«{value}» (column {column}) on {model}. '
              'Raw error: [{raw_error}]').format(
                raw_error='FakeSector matching query does not exist.',
                column=3,
                value=line4[2],
                model=FakeSector._meta.verbose_name,
            ),
            err_msg4
        )

    def test_extract04(self):
        "Sub-field search + create_if_unfound=True."
        extractor = Extractor(
            column_index=3,
            default_value=None,
            value_castor=int,
        )
        extractor.set_subfield_search(
            subfield_search='title',
            subfield_model=FakeSector,
            multiple=False,
            create_if_unfound=True,
        )

        title = 'Planes'
        self.assertFalse(FakeSector.objects.filter(title=title))

        line1 = ['Claus', 'Valca', title]
        value, err_msg = extractor.extract_value(line1)
        self.assertIsNone(err_msg)

        sector = self.get_object_or_fail(FakeSector, title=title)
        self.assertEqual(sector, value)

    # TODO: creation error
    # TODO: multiple=True
    # TODO: value_castor + ValidationError


class CustomFieldExtractorTestCase(CremeTestCase):
    def test_extract01(self):
        cfield = CustomField.objects.create(
            name='Hobby',
            field_type=CustomField.STR,
            content_type=FakeContact,
        )

        default_value = '??'
        extractor = CustomFieldExtractor(
            column_index=3,
            default_value=default_value,
            value_castor=str,
            custom_field=cfield,
            create_if_unfound=False,
        )

        line1 = ['Claus', 'Valca', 'Vanship']
        self.assertEqual((line1[2], None), extractor.extract_value(line1))

        line2 = ['Lavie', 'Head', 'Motors']
        self.assertEqual((line2[2], None), extractor.extract_value(line2))

        line3 = ['Alvis', 'Hamilton', '']
        self.assertEqual((default_value, None), extractor.extract_value(line3))

    def test_extract02(self):
        "Validation."
        cfield = CustomField.objects.create(
            name='Size',
            field_type=CustomField.INT,
            content_type=FakeContact,
        )

        default_value = 12
        extractor = CustomFieldExtractor(
            column_index=3,
            default_value=default_value,
            value_castor=cfield.get_formfield(None).clean,
            custom_field=cfield,
            create_if_unfound=False,
        )

        line1 = ['Claus', 'Valca', '173']
        self.assertEqual((173, None), extractor.extract_value(line1))

        line2 = ['Lavie', 'Head', '164']
        self.assertEqual((164, None), extractor.extract_value(line2))

        line3 = ['Alvis', 'Hamilton', 'noatanint']
        self.assertEqual(
            (default_value, _('Enter a whole number.')),
            extractor.extract_value(line3)
        )

    def test_extract_enum01(self):
        "create_if_unfound == True"
        cfield = CustomField.objects.create(
            name='Hobby',
            field_type=CustomField.ENUM,
            content_type=FakeContact,
        )

        create_evalue = CustomFieldEnumValue.objects.create
        eval1 = create_evalue(custom_field=cfield, value='Piloting')
        eval2 = create_evalue(custom_field=cfield, value='Mechanic')

        default_value = eval2.id
        extractor = CustomFieldExtractor(
            column_index=3,
            default_value=default_value,
            value_castor=cfield.get_formfield(None).clean,
            custom_field=cfield,
            create_if_unfound=True,
        )

        line1 = ['Claus', 'Valca', eval1.value]
        self.assertEqual((eval1.id, None), extractor.extract_value(line1))

        line2 = ['Lavie', 'Head', eval2.value]
        self.assertEqual((eval2.id, None), extractor.extract_value(line2))

        line3 = ['Alvis', 'Hamilton', 'Cooking']
        eval3_id, err_msg = extractor.extract_value(line3)
        self.assertIsNone(err_msg)

        eval3 = self.get_object_or_fail(CustomFieldEnumValue, id=eval3_id)
        self.assertEqual(cfield, eval3.custom_field)
        self.assertEqual(line3[2], eval3.value)

    def test_extract_enum02(self):
        "create_if_unfound == False + empty default value."
        cfield = CustomField.objects.create(
            name='Hobby',
            field_type=CustomField.ENUM,
            content_type=FakeContact,
        )

        create_evalue = CustomFieldEnumValue.objects.create
        eval1 = create_evalue(custom_field=cfield, value='Piloting')
        # eval2 = create_evalue(custom_field=cfield, value='Mechanic')

        default_value = ''
        extractor = CustomFieldExtractor(
            column_index=3,
            default_value=default_value,
            value_castor=cfield.get_formfield(None).clean,
            custom_field=cfield,
            create_if_unfound=False,
        )

        line1 = ['Claus', 'Valca', eval1.value]
        self.assertEqual((eval1.id, None), extractor.extract_value(line1))

        line2 = ['Alvis', 'Hamilton', 'Cooking']
        self.assertEqual(
            (default_value,
             _('Error while extracting value: the choice «{value}» '
               'was not found in existing choices (column {column}). '
               'Hint: fix your imported file, or configure the import to '
               'create new choices.').format(
                    column=3,
                    value=line2[2],
             )
            ),
            extractor.extract_value(line2)
        )

    def test_extract_enum03(self):
        "create_if_unfound == False + default value."
        cfield = CustomField.objects.create(
            name='Hobby',
            field_type=CustomField.ENUM,
            content_type=FakeContact,
        )

        create_evalue = CustomFieldEnumValue.objects.create
        create_evalue(custom_field=cfield, value='Piloting')
        eval2 = create_evalue(custom_field=cfield, value='Mechanic')

        default_value = str(eval2.id)
        extractor = CustomFieldExtractor(
            column_index=3,
            default_value=default_value,
            value_castor=cfield.get_formfield(None).clean,
            custom_field=cfield,
            create_if_unfound=False,
        )

        line = ['Alvis', 'Hamilton', 'Cooking']
        self.assertEqual(
            (default_value,
             _('Error while extracting value: the choice «{value}» '
               'was not found in existing choices (column {column}). '
               'Hint: fix your imported file, or configure the import to '
               'create new choices.').format(
                    column=3,
                    value=line[2],
             )
            ),
            extractor.extract_value(line)
        )

    def test_extract_enum04(self):
        "Search + duplicates."
        cfield = CustomField.objects.create(
            name='Hobby',
            field_type=CustomField.ENUM,
            content_type=FakeContact,
        )

        create_evalue = partial(CustomFieldEnumValue.objects.create,
                                custom_field=cfield, value='Piloting',
                               )
        eval1 = create_evalue()
        create_evalue()

        extractor = CustomFieldExtractor(
            column_index=3,
            default_value='',
            value_castor=cfield.get_formfield(None).clean,
            custom_field=cfield,
            create_if_unfound=True,
        )

        line = ['Claus', 'Valca', eval1.value]
        eval_id, err_msg = extractor.extract_value(line)
        self.assertIsNone(err_msg)
        # self.assertEqual((eval1.id, None), extractor.extract_value(line1))


    def test_extract_menum01(self):
        cfield = CustomField.objects.create(
            name='Hobby',
            field_type=CustomField.MULTI_ENUM,
            content_type=FakeContact,
        )

        create_evalue = CustomFieldEnumValue.objects.create
        eval1 = create_evalue(custom_field=cfield, value='Piloting')
        eval2 = create_evalue(custom_field=cfield, value='Mechanic')

        default_value = eval2.id
        extractor = CustomFieldExtractor(
            column_index=3,
            default_value=default_value,
            value_castor=cfield.get_formfield(None).clean,
            custom_field=cfield,
            create_if_unfound=True,
        )

        line1 = ['Claus', 'Valca', eval1.value]
        self.assertEqual(([eval1.id], None), extractor.extract_value(line1))

        line2 = ['Lavie', 'Head', eval2.value]
        self.assertEqual(([eval2.id], None), extractor.extract_value(line2))

        line3 = ['Alvis', 'Hamilton', 'Cooking']
        eval3_ids, err_msg = extractor.extract_value(line3)
        self.assertIsNone(err_msg)
        self.assertEqual(1, len(eval3_ids))

        eval3 = self.get_object_or_fail(CustomFieldEnumValue, id=eval3_ids[0])
        self.assertEqual(cfield, eval3.custom_field)
        self.assertEqual(line3[2], eval3.value)


# class ExtractorFieldTestCase(FieldTestCase):
class ExtractorFieldTestCase(CremeTestCase):
    def test_attributes(self):
        user = self.login()

        first_name_field = FakeContact._meta.get_field('first_name')
        choices = [
            (0, 'Not in the file'),
            (1, 'Column 1'),
        ]

        field = ExtractorField(
            choices=choices,
            modelfield=first_name_field,
            modelform_field=CharField(),
        )
        self.assertTrue(field.required)
        self.assertIsNone(field.user)

        widget = field.widget
        self.assertIsInstance(field.widget, ExtractorWidget)
        self.assertEqual(choices, widget.choices)
        self.assertIsInstance(widget.default_value_widget, TextInput)

        field.user = user
        self.assertEqual(user, field.user)

    # TODO: @user + test with FK/creme_config

    def test_errors(self):
        field = ExtractorField(
            choices=[
                (0, 'Not in the file'),
                (1, 'Column 1'),
            ],
            modelfield=FakeContact._meta.get_field('first_name'),
            modelform_field=CharField(),
        )

        # TODO: improve assertFieldValidationError()
        #       (it needs a default cosntructor for the error messages)
        # self.assertFieldValidationError(ExtractorField, 'invalid', field.clean,
        #                                 'notadict'
        #                                )
        invalid = (_('Enter a valid value.'), 'invalid', None)
        with self.assertRaises(ValidationError) as cm:
            __ = field.clean('notadict')
        self.assertEqual(invalid, cm.exception.args)

        with self.assertRaises(ValidationError) as cm:
            __ = field.clean({'selected_column': 'notanint'})
        self.assertEqual(invalid, cm.exception.args)

        with self.assertRaises(ValidationError) as cm:
            __ = field.clean({'selected_column': '25'})
        self.assertEqual(invalid, cm.exception.args)

        with self.assertRaises(ValidationError) as cm:
            __ = field.clean({'selected_column': '1'})  # No default value
        self.assertEqual('invalid', cm.exception.args[1])

        with self.assertRaises(ValidationError) as cm:
            __ = field.clean({'selected_column': '1',
                              'default_value': 'John',
                             }
                            )
        self.assertEqual(invalid, cm.exception.args)

    # TODO: test with required + no column
    # TODO: test with not required

    def test_clean(self):
        field = ExtractorField(
            choices=[
                (0, 'Not in the file'),
                (1, 'Column 1'),
            ],
            modelfield=FakeContact._meta.get_field('first_name'),
            modelform_field=CharField(),
        )

        col = 1
        def_val = 'John'
        extractor = field.clean({'selected_column': str(col),
                                 'default_value': def_val,
                                 'subfield_create': '',
                                }
                              )
        self.assertIsInstance(extractor, Extractor)
        self.assertEqual(col, extractor._column_index)
        self.assertEqual(def_val, extractor._default_value)

        first_name = 'Claus'
        value, err_msg = extractor.extract_value([first_name, 'Valca'])
        self.assertIsNone(err_msg)
        self.assertEqual(first_name, value)


class CustomfieldExtractorFieldTestCase(CremeTestCase):
    def test_attributes(self):
        user = self.login()

        cfield = CustomField.objects.create(
            name='Hobby',
            field_type=CustomField.STR,
            content_type=FakeContact,
        )

        choices = [
            (0, 'Not in the file'),
            (1, 'Column 1'),
        ]

        field = CustomfieldExtractorField(
            choices=choices,
            custom_field=cfield,
            user=user,
        )
        self.assertEqual(user, field.user)
        self.assertFalse(field.required)

        widget = field.widget
        self.assertIsInstance(field.widget, CustomFieldExtractorWidget)
        self.assertEqual(choices, widget.choices)
        self.assertIsInstance(widget.default_value_widget, TextInput)

    def test_errors(self):
        user = self.login()

        cfield = CustomField.objects.create(
            name='Hobby',
            field_type=CustomField.STR,
            content_type=FakeContact,
        )

        field = CustomfieldExtractorField(
            choices=[
                (0, 'Not in the file'),
                (1, 'Column 1'),
            ],
            custom_field=cfield,
            user=user,
        )

        invalid = (_('Enter a valid value.'), 'invalid', None)
        with self.assertRaises(ValidationError) as cm:
            __ = field.clean('notadict')
        self.assertEqual(invalid, cm.exception.args)

        with self.assertRaises(ValidationError) as cm:
            __ = field.clean({'selected_column': 'notanint'})
        self.assertEqual(invalid, cm.exception.args)

        with self.assertRaises(ValidationError) as cm:
            __ = field.clean({'selected_column': '25'})
        self.assertEqual(invalid, cm.exception.args)

        with self.assertRaises(ValidationError) as cm:
            __ = field.clean({'selected_column': '1'})  # No default value
        self.assertEqual('invalid', cm.exception.args[1])

    def test_clean(self):
        user = self.login()

        cfield = CustomField.objects.create(
            name='Hobby',
            field_type=CustomField.STR,
            content_type=FakeContact,
        )

        field = CustomfieldExtractorField(
            choices=[
                (0, 'Not in the file'),
                (1, 'Column 1'),
                (2, 'Column 2'),
                (3, 'Column 3'),
            ],
            custom_field=cfield,
            user=user,
        )

        col = 3
        def_val = '??'
        extractor = field.clean({'selected_column': str(col),
                                 'default_value': def_val,
                                 # 'can_create': '',
                                }
                               )
        self.assertIsInstance(extractor, CustomFieldExtractor)
        self.assertEqual(col, extractor._column_index)
        self.assertEqual(def_val, extractor._default_value)

        line = ['Claus', 'Valca', 'Piloting']
        value, err_msg = extractor.extract_value(line)
        self.assertIsNone(err_msg)
        self.assertEqual(line[2], value)

    # TODO: can_create
