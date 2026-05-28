from functools import partial
from json import dumps as json_dump

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.forms import CharField
from django.forms.widgets import TextInput
from django.utils.translation import gettext as _

from creme.creme_core.forms import CremeModelForm
# RelationExtractorField, RelationExtractorSelector
from creme.creme_core.forms.mass_import import (
    CustomFieldExtractor,
    CustomfieldExtractorField,
    CustomFieldExtractorWidget,
    EntityExtractionCommand,
    EntityExtractor,
    EntityExtractorField,
    EntityExtractorWidget,
    MultiRelationsExtractor,
    MultiRelationsExtractorField,
    MultiRelationsExtractorSelector,
    RegularFieldExtractor,
    RegularFieldExtractorField,
    RegularFieldExtractorWidget,
    RelationExtractor,
)
from creme.creme_core.models import (
    CustomField,
    CustomFieldEnumValue,
    FakeContact,
    FakeDocument,
    FakeOrganisation,
    FakeSector,
    RelationType,
)

from ..base import CremeTestCase

# TODO: complete
#    - complete existing test cases
#    - test other extractors:
#       - MultiRelationsExtractor
#    - test widgets


class ExtractorTestCase(CremeTestCase):
    # TODO: factorise
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.build_user()

    def test_extract(self):
        user = self.user
        default_value = '??'
        extractor = RegularFieldExtractor(
            column_index=1,
            default_value=default_value,
            value_castor=str,
        )
        line1 = ['Claus', 'Valca']
        self.assertEqual((line1[0], None), extractor.extract_value(line1, user))

        line2 = ['Lavie', 'Head']
        self.assertEqual((line2[0], None), extractor.extract_value(line2, user))

        line3 = ['', 'Hamilton']
        self.assertEqual((default_value, None), extractor.extract_value(line3, user))

    def test_extract__cast(self):
        "Other index, casting."
        user = self.user
        default_value = 42
        extractor = RegularFieldExtractor(
            column_index=3,
            default_value=default_value,
            value_castor=int,
        )
        line1 = ['Claus', 'Valca', '17']
        self.assertEqual((17, None), extractor.extract_value(line1, user))

        line2 = ['Lavie', 'Head', '']
        self.assertEqual((default_value, None), extractor.extract_value(line=line2, user=user))

        line3 = ['Lavie', 'Head', 'notanint']
        self.assertEqual(
            (default_value, "invalid literal for int() with base 10: 'notanint'"),
            extractor.extract_value(line3, user),
        )

    def test_extract__sub_field(self):
        "Sub-field search."
        user = self.user
        extractor = RegularFieldExtractor(
            column_index=3,
            default_value=None,
            value_castor=int,
        )
        extractor.set_subfield_search(
            subfield_search='title',
            subfield_model=FakeSector,
            multiple=False,
            # create_if_unfound=False,
            creation_form_class=None,
        )

        sector1, sector2 = FakeSector.objects.all()[:2]

        line1 = ['Claus', 'Valca', sector1.title]
        self.assertEqual((sector1, None), extractor.extract_value(line1, user))

        line2 = ['Lavie', 'Head', sector2.title]
        self.assertEqual((sector2, None), extractor.extract_value(line2, user))

        line3 = ['Alvis', 'Hamilton', '']
        self.assertEqual((None, None), extractor.extract_value(line3, user))

        line4 = ['Alex', 'Row', 'Unknown sector']
        value4, err_msg4 = extractor.extract_value(line4, user)
        self.assertIsNone(value4)
        self.assertEqual(
            _(
                'Error while extracting value: tried to retrieve '
                '«{value}» (column {column}) on {model}. '
                'Raw error: [{raw_error}]'
            ).format(
                raw_error='FakeSector matching query does not exist.',
                column=3,
                value=line4[2],
                model=FakeSector._meta.verbose_name,
            ),
            err_msg4,
        )

    def test_extract__sub_field__creation_form(self):
        "Sub-field search + creation form class."
        class FakeSectorForm(CremeModelForm):
            class Meta:
                model = FakeSector
                fields = '__all__'

        extractor = RegularFieldExtractor(
            column_index=3,
            default_value=None,
            value_castor=int,
        )
        extractor.set_subfield_search(
            subfield_search='title',
            subfield_model=FakeSector,
            multiple=False,
            # create_if_unfound=True,
            creation_form_class=FakeSectorForm,
        )

        title = 'Planes'
        self.assertFalse(FakeSector.objects.filter(title=title))

        line1 = ['Claus', 'Valca', title]
        value, err_msg = extractor.extract_value(line1, self.user)
        self.assertIsNone(err_msg)

        sector = self.get_object_or_fail(FakeSector, title=title)
        self.assertEqual(sector, value)

    def test_extract__sub_field__creation_form__error(self):
        title = 'Planes [deleted]'
        self.assertFalse(FakeSector.objects.filter(title=title))

        class FakeSectorForm(CremeModelForm):
            err_msg = 'Invalid creator name'

            class Meta:
                model = FakeSector
                fields = '__all__'

            def clean(this):
                cdata = super().clean()
                if '[deleted]' in cdata.get('title', ''):
                    raise ValidationError(this.err_msg)

                return cdata

        column_index = 3
        extractor = RegularFieldExtractor(
            column_index=column_index,
            default_value=None,
            value_castor=int,
        )
        extractor.set_subfield_search(
            subfield_search='title',
            subfield_model=FakeSector,
            multiple=False,
            # create_if_unfound=True,
            creation_form_class=FakeSectorForm,
        )

        line1 = ['Claus', 'Valca', title]
        value, err_msg = extractor.extract_value(line1, self.user)
        self.assertIsNone(value)
        self.assertEqual(
            _(
                'Error while extracting value: tried to retrieve '
                'and then build «{value}» (column {column}) on {model}. '
                'Raw error: [{raw_error}]'
            ).format(
                raw_error='FakeSector matching query does not exist.',
                column=column_index,
                value=title,
                model=FakeSector._meta.verbose_name,
            ),
            err_msg,
        )

        self.assertFalse(FakeSector.objects.filter(title=title))

    # TODO: multiple=True
    # TODO: value_castor + ValidationError


class EntityExtractorTestCase(CremeTestCase):
    def test_extract__one_command__no_creation(self):
        user = self.get_root_user()

        no_orga_name = 'megacorp'
        self.assertFalse(FakeOrganisation.objects.filter(name=no_orga_name))

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Acme')
        orga2 = create_orga(name='Exile')

        cmd = EntityExtractionCommand(
            model=FakeOrganisation,
            field_name='name',
            column_index='2',
            create=False,
        )
        cmd.build_column_index()

        extractor = EntityExtractor(extraction_cmds=[cmd])
        self.assertEqual([cmd], [*extractor.commands])

        self.assertTupleEqual(
            (None, ''),
            extractor.extract_value(['Claus', ''], user),
        )

        self.assertTupleEqual(
            (orga1, None),
            extractor.extract_value(['Claus', orga1.name], user),
        )

        self.assertTupleEqual(
            (orga2, None),
            extractor.extract_value(['Lavie', orga2.name], user),
        )

        self.assertTupleEqual(
            (
                None,
                _(
                    'Error while extracting value [{raw_error}]: '
                    'tried to retrieve «{value}» on {model}'
                ).format(
                    raw_error='FakeOrganisation matching query does not exist.',
                    value=no_orga_name,
                    model=FakeOrganisation._meta.verbose_name,
                ),
            ),
            extractor.extract_value(['Valca', no_orga_name], user),
        )

    def test_extract__one_command__creation(self):
        user = self.get_root_user()

        no_orga_name1 = 'MegaCorp'
        no_orga_name2 = 'Exile'
        self.assertFalse(
            FakeOrganisation.objects.filter(name__in=[no_orga_name1, no_orga_name2])
        )

        cmd = EntityExtractionCommand(
            model=FakeOrganisation,
            field_name='name',
            column_index='3',
            create=True,
        )
        cmd.build_column_index()

        extractor = EntityExtractor(extraction_cmds=[cmd])

        extracted1 = extractor.extract_value(['Claus', 'Lavie', no_orga_name1], user)
        orga1 = self.get_object_or_fail(FakeOrganisation, user=user, name=no_orga_name1)
        self.assertTupleEqual((orga1, None), extracted1)

        extracted2 = extractor.extract_value(['Claus', 'Lavie', no_orga_name2], user)
        orga2 = self.get_object_or_fail(FakeOrganisation, user=user, name=no_orga_name2)
        self.assertTupleEqual((orga2, None), extracted2)

    def test_extract__one_command__creation__error(self):
        cmd = EntityExtractionCommand(
            model=FakeOrganisation,
            # field_name='name',
            field_name='description',
            column_index='2',
            create=True,
        )
        cmd.build_column_index()

        extractor = EntityExtractor(extraction_cmds=[cmd])
        line = ['Claus', 'the description is here']
        self.assertTupleEqual(
            (
                None,
                _(
                    'Error while extracting value [{raw_error}]: '
                    'tried to retrieve and then build «{value}» on {model}'
                ).format(
                    raw_error="{{'name': ['{valerr}']}}".format(
                        valerr=_('This field cannot be blank.'),
                    ),
                    value=line[1],
                    model=FakeOrganisation._meta.verbose_name,
                ),
            ),
            extractor.extract_value(line, self.get_root_user()),
        )

    def test_extract__two_commands(self):
        user = self.get_root_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Acme')
        orga2 = create_orga(name='Exile', email='contact@exile.jp')

        cmd1 = EntityExtractionCommand(
            model=FakeOrganisation,
            field_name='name',
            column_index='1',
            create=False,
        )
        cmd1.build_column_index()

        cmd2 = EntityExtractionCommand(
            model=FakeOrganisation,
            field_name='email',
            column_index='2',
            create=False,
        )
        cmd2.build_column_index()

        extractor = EntityExtractor(extraction_cmds=[cmd1, cmd2])
        self.assertEqual([cmd1, cmd2], [*extractor.commands])

        self.assertTupleEqual(
            (orga1, None),
            extractor.extract_value([orga1.name, ''], user),
        )
        self.assertTupleEqual(
            (orga2, None),
            extractor.extract_value(['not found', orga2.email], user),
        )

    def test_extract__no_index(self):
        user = self.get_root_user()

        cmd = EntityExtractionCommand(
            model=FakeOrganisation,
            field_name='name',
            column_index='0',  # <==
            create=False,
        )
        cmd.build_column_index()

        extractor = EntityExtractor(extraction_cmds=[cmd])
        self.assertTupleEqual(
            (None, ''),
            extractor.extract_value(['Claus', ''], user),
        )


class RelationExtractorTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rtype = RelationType.objects.builder(
            id='test-subject_love', predicate='loves',
        ).symmetric(
            id='test-object_love', predicate='is loved to',
        ).get_or_create()[0]

    def test_extract__found(self):
        user = self.get_root_user()
        rtype = self.rtype
        orga = FakeOrganisation.objects.create(
            user=user, name='Acme', email='contact@acme.org',
        )

        column_index = 2
        field_name = 'email'
        extractor = RelationExtractor(
            column_index=column_index,
            rtype=rtype,
            subfield_search=field_name,
            related_model=FakeOrganisation,
            create_if_unfound=False,
        )
        self.assertEqual(column_index, extractor.column_index)
        self.assertEqual(rtype, extractor.rtype)
        self.assertEqual(field_name, extractor.subfield_search)
        # self.assertFalse(extractor.create_if_unfound())
        self.assertFalse(extractor.create_if_unfound)

        self.assertTupleEqual(
            ((rtype, orga), None),
            extractor.extract_value(['Claus', orga.email], user),
        )

    def test_extract__create(self):
        user = self.get_root_user()
        rtype = self.rtype

        orga_name = 'Acme'
        self.assertFalse(FakeOrganisation.objects.filter(name=orga_name))

        column_index = 1
        field_name = 'name'
        extractor = RelationExtractor(
            column_index=column_index,
            rtype=rtype,
            subfield_search=field_name,
            related_model=FakeOrganisation,
            create_if_unfound=True,
        )
        self.assertEqual(field_name, extractor.subfield_search)
        # self.assertTrue(extractor.create_if_unfound())
        self.assertTrue(extractor.create_if_unfound)

        extracted = extractor.extract_value([orga_name], user)
        orga = self.get_object_or_fail(FakeOrganisation, name=orga_name)
        self.assertTupleEqual(((rtype, orga), None), extracted)

    def test_extract__create__property(self):
        user = self.get_root_user()
        rtype = self.rtype

        orga_name = 'Acme'
        self.assertFalse(FakeOrganisation.objects.filter(name=orga_name))

        extractor = RelationExtractor(
            column_index=1,
            rtype=rtype,
            subfield_search='name',
            related_model=FakeOrganisation,
            # create_if_unfound=True,
        )
        self.assertFalse(extractor.create_if_unfound)

        extractor.create_if_unfound = True
        extracted = extractor.extract_value([orga_name], user)
        orga = self.get_object_or_fail(FakeOrganisation, name=orga_name)
        self.assertTupleEqual(((rtype, orga), None), extracted)

    def test_extract__no_creation(self):
        user = self.get_root_user()
        rtype = self.rtype

        orga_name = 'Acme'
        self.assertFalse(FakeOrganisation.objects.filter(name=orga_name))

        column_index = 1
        field_name = 'name'
        extractor = RelationExtractor(
            column_index=column_index,
            rtype=rtype,
            subfield_search=field_name,
            related_model=FakeOrganisation,
            create_if_unfound=False,  # <==
        )

        extracted = extractor.extract_value([orga_name], user)
        self.assertTupleEqual(
            (
                (rtype, None),
                _(
                    'Error while extracting value to build a Relation: '
                    'tried to retrieve {field}=«{value}» '
                    '(column {column}) on {model}'
                ).format(
                    field=field_name,
                    column=column_index,
                    value=orga_name,
                    model=FakeOrganisation._meta.verbose_name,
                )
            ),
            extracted,
        )
        self.assertFalse(FakeOrganisation.objects.filter(name=orga_name))

    def test_extract__search__error(self):
        user = self.get_root_user()
        rtype = self.rtype

        column_index = 1
        field_name = 'invalid_field'
        extractor = RelationExtractor(
            column_index=column_index,
            rtype=rtype,
            subfield_search=field_name,
            related_model=FakeOrganisation,
            create_if_unfound=True,
        )

        line = ['whatever']
        extracted = extractor.extract_value(line, user)
        self.maxDiff = None
        self.assertTupleEqual(
            (
                (rtype, None),
                _(
                    'Error while extracting value to build a Relation: '
                    'tried to retrieve {field}=«{value}» (column {column}) on {model}. '
                    'Raw error: [{raw_error}]'
                ).format(
                    raw_error="Cannot resolve keyword 'invalid_field' into field…",
                    column=column_index,
                    field=field_name,
                    value=line[0],
                    model=FakeOrganisation._meta.verbose_name,
                )
            ),
            extracted,
        )

    def test_extract__search__permissions(self):
        user = self.create_user(
            role=self.create_role(
                allowed_apps=['creme_core'],
                # creatable_models=[FakeDocument],  # No FakeOrganisation
            ),
        )
        self.add_credentials(role=user.role, own='*')
        rtype = self.rtype

        orga_name = 'Acme'
        self.assertFalse(FakeOrganisation.objects.filter(name=orga_name))
        FakeOrganisation.objects.create(
            user=self.get_root_user(), name=orga_name,
        )  # Not viewable

        column_index = 1
        field_name = 'name'
        extractor = RelationExtractor(
            column_index=column_index,
            rtype=rtype,
            subfield_search=field_name,
            related_model=FakeOrganisation,
            create_if_unfound=False,
        )

        extracted = extractor.extract_value([orga_name], user)
        self.assertTupleEqual(
            (
                (rtype, None),
                _(
                    'Error while extracting value to build a Relation: '
                    'tried to retrieve {field}=«{value}» '
                    '(column {column}) on {model}'
                ).format(
                    field=field_name,
                    column=column_index,
                    value=orga_name,
                    model=FakeOrganisation._meta.verbose_name,
                )
            ),
            extracted,
        )
        self.assertEqual(1, FakeOrganisation.objects.filter(name=orga_name).count())

    def test_extract__creation_error(self):
        user = self.get_root_user()
        rtype = self.rtype

        orga_email = 'contact@acme.com'
        self.assertFalse(FakeOrganisation.objects.filter(email=orga_email))

        column_index = 1
        field_name = 'email'
        extractor = RelationExtractor(
            column_index=column_index,
            rtype=rtype,
            subfield_search=field_name,
            related_model=FakeOrganisation,
            create_if_unfound=True,
        )

        extracted = extractor.extract_value([orga_email], user)
        self.assertTupleEqual(
            (
                (rtype, None),
                _(
                    'Error while extracting value: '
                    'tried to build {model} with data={data} '
                    '(column {column}) ➔ errors={errors}'
                ).format(
                    model=FakeOrganisation._meta.verbose_name,
                    column=column_index,
                    data={'email': orga_email, 'user': user.id},
                    errors="{'name': [ValidationError(['%s'])]}" % _('This field is required.'),
                )
            ),
            extracted,
        )


class CustomFieldExtractorTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.build_user()

    def test_extract(self):
        user = self.user
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
        self.assertEqual(
            (line1[2], None), extractor.extract_value(line1, user),
        )

        line2 = ['Lavie', 'Head', 'Motors']
        self.assertEqual(
            (line2[2], None), extractor.extract_value(line=line2, user=user),
        )

        line3 = ['Alvis', 'Hamilton', '']
        self.assertEqual(
            (default_value, None), extractor.extract_value(line3, user),
        )

    def test_extract__validation(self):
        user = self.user
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
        self.assertEqual((173, None), extractor.extract_value(line1, user))

        line2 = ['Lavie', 'Head', '164']
        self.assertEqual((164, None), extractor.extract_value(line2, user))

        line3 = ['Alvis', 'Hamilton', 'noatanint']
        self.assertEqual(
            (default_value, _('Enter a whole number.')),
            extractor.extract_value(line3, user)
        )

    def test_extract__enum__creation(self):
        "create_if_unfound == True."
        user = self.user
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
        self.assertEqual(
            (eval1.id, None), extractor.extract_value(line1, user),
        )

        line2 = ['Lavie', 'Head', eval2.value]
        self.assertEqual(
            (eval2.id, None), extractor.extract_value(line2, user),
        )

        line3 = ['Alvis', 'Hamilton', 'Cooking']
        eval3_id, err_msg = extractor.extract_value(line3, user)
        self.assertIsNone(err_msg)

        eval3 = self.get_object_or_fail(CustomFieldEnumValue, id=eval3_id)
        self.assertEqual(cfield, eval3.custom_field)
        self.assertEqual(line3[2], eval3.value)

    def test_extract__enum__no_creation(self):
        "create_if_unfound == False + empty default value."
        user = self.user
        cfield = CustomField.objects.create(
            name='Hobby',
            field_type=CustomField.ENUM,
            content_type=FakeContact,
        )

        evalue = CustomFieldEnumValue.objects.create(
            custom_field=cfield, value='Piloting',
        )

        default_value = ''
        extractor = CustomFieldExtractor(
            column_index=3,
            default_value=default_value,
            value_castor=cfield.get_formfield(None).clean,
            custom_field=cfield,
            create_if_unfound=False,
        )

        line1 = ['Claus', 'Valca', evalue.value]
        self.assertEqual(
            (evalue.id, None), extractor.extract_value(line1, user),
        )

        line2 = ['Alvis', 'Hamilton', 'Cooking']
        self.assertEqual(
            (
                default_value,
                _(
                    'Error while extracting value: the choice «{value}» '
                    'was not found in existing choices (column {column}). '
                    'Hint: fix your imported file, or configure the import to '
                    'create new choices.'
                ).format(column=3, value=line2[2]),
            ),
            extractor.extract_value(line2, user)
        )

    def test_extract__enum__no_creation__default(self):
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
            (
                default_value,
                _(
                    'Error while extracting value: the choice «{value}» '
                    'was not found in existing choices (column {column}). '
                    'Hint: fix your imported file, or configure the import to '
                    'create new choices.'
                ).format(column=3, value=line[2]),
            ),
            extractor.extract_value(line, self.user),
        )

    def test_extract__enum__dupliactes(self):
        "Search + duplicates."
        cfield = CustomField.objects.create(
            name='Hobby',
            field_type=CustomField.ENUM,
            content_type=FakeContact,
        )

        create_evalue = partial(
            CustomFieldEnumValue.objects.create,
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
        eval_id, err_msg = extractor.extract_value(line, user=self.user)
        self.assertIsNone(err_msg)

    def test_extract__multi_enum(self):
        user = self.user
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
        self.assertEqual(
            ([eval1.id], None), extractor.extract_value(line1, user),
        )

        line2 = ['Lavie', 'Head', eval2.value]
        self.assertEqual(
            ([eval2.id], None), extractor.extract_value(line2, user),
        )

        line3 = ['Alvis', 'Hamilton', 'Cooking']
        eval3_ids, err_msg = extractor.extract_value(line3, user)
        self.assertIsNone(err_msg)
        self.assertEqual(1, len(eval3_ids))

        eval3 = self.get_object_or_fail(CustomFieldEnumValue, id=eval3_ids[0])
        self.assertEqual(cfield, eval3.custom_field)
        self.assertEqual(line3[2], eval3.value)


class ExtractorFieldTestCase(CremeTestCase):
    def test_attributes(self):
        user = self.get_root_user()

        first_name_field = FakeContact._meta.get_field('first_name')
        choices = [
            (0, 'Not in the file'),
            (1, 'Column 1'),
        ]

        field = RegularFieldExtractorField(
            choices=choices,
            modelfield=first_name_field,
            modelform_field=CharField(),
        )
        self.assertTrue(field.required)
        self.assertIsNone(field.user)

        widget = field.widget
        self.assertIsInstance(field.widget, RegularFieldExtractorWidget)
        self.assertEqual(choices, widget.choices)
        self.assertIsInstance(widget.default_value_widget, TextInput)

        field.user = user
        self.assertEqual(user, field.user)

    # TODO: @user + test with FK/creme_config

    def test_errors(self):
        field = RegularFieldExtractorField(
            choices=[
                (0, 'Not in the file'),
                (1, 'Column 1'),
            ],
            modelfield=FakeContact._meta.get_field('first_name'),
            modelform_field=CharField(),
        )
        msg = _('Enter a valid value.')
        code = 'invalid'
        self.assertFormfieldError(
            field=field, value='notadict', messages=msg, codes=code,
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value={'selected_column': 'notanint'},
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value={'selected_column': '25'},
        )
        self.assertFormfieldError(
            field=field,
            value={'selected_column': '1'},  # No default value
            messages='Widget seems buggy, no default value',
            codes=code,
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value={
                'selected_column': '1',
                'default_value': 'John',
            },
        )

    # TODO: test with required + no column
    # TODO: test with not required

    def test_clean(self):
        field = RegularFieldExtractorField(
            choices=[
                (0, 'Not in the file'),
                (1, 'Column 1'),
            ],
            modelfield=FakeContact._meta.get_field('first_name'),
            modelform_field=CharField(),
        )

        col = 1
        def_val = 'John'
        extractor = field.clean({
            'selected_column': str(col),
            'default_value': def_val,
            'subfield_create': '',
        })
        self.assertIsInstance(extractor, RegularFieldExtractor)
        self.assertEqual(col, extractor._column_index)
        self.assertEqual(def_val, extractor._default_value)

        first_name = 'Claus'
        value, err_msg = extractor.extract_value(
            line=[first_name, 'Valca'], user=self.build_user(),
        )
        self.assertIsNone(err_msg)
        self.assertEqual(first_name, value)


class EntityExtractorFieldTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.weak_user = cls.create_user(
            role=cls.create_role(
                allowed_apps=['creme_core'],
                creatable_models=[FakeDocument],  # No FakeOrganisation
            ),
        )

    def test_attributes(self):
        choices = [(0, 'Not in the file'), (1, 'Column 1')]
        models_info = [
            (FakeOrganisation, 'name'),
            (FakeContact, 'email'),
        ]
        field = EntityExtractorField(choices=choices, models_info=models_info)
        self.assertTrue(field.required)
        self.assertIsNone(field.user)
        self.assertEqual(models_info, field.models_info)
        self.assertEqual({0, 1}, field.allowed_indexes)

        widget = field.widget
        self.assertIsInstance(field.widget, EntityExtractorWidget)
        self.assertEqual(choices, widget.choices)
        self.assertEqual(models_info, widget.models_info)

    def test_clean__one_active_command__no_creation(self):
        user = self.weak_user
        field = EntityExtractorField(
            choices=[(0, 'Not in the file'), (1, 'Column 1')],
            models_info=[(FakeOrganisation, 'name')],
            user=user,
        )
        self.assertEqual(user, field.user)

        cmd = EntityExtractionCommand(
            model=FakeOrganisation,
            field_name='name',
            column_index='1',
            create=False,
        )
        extractor = field.clean([cmd])
        self.assertIsInstance(extractor, EntityExtractor)
        self.assertListEqual([cmd], [*extractor.commands])

    def test_clean__empty__not_required(self):
        user = self.get_root_user()
        field = EntityExtractorField(
            choices=[(0, 'Not in the file'), (1, 'Column 1')],
            models_info=[(FakeOrganisation, 'name')],
            user=user,
            required=False,
        )
        self.assertFalse(field.required)

        extractor = field.clean([])
        self.assertIsInstance(extractor, EntityExtractor)
        self.assertFalse([*extractor.commands])

    def test_clean__empty__required(self):
        user = self.get_root_user()
        field = EntityExtractorField(
            choices=[(0, 'Not in the file'), (1, 'Column 1')],
            models_info=[(FakeOrganisation, 'name')],
            user=user,
        )
        self.assertTrue(field.required)
        self.assertFormfieldError(
            field=field,
            messages=_('This field is required.'),
            codes='required',
            value=[],
        )

    def test_clean__invalid_column_type(self):
        self.assertFormfieldError(
            field=EntityExtractorField(
                choices=[(0, 'Not in the file'), (1, 'Column 1')],
                models_info=[(FakeOrganisation, 'name')],
                user=self.get_root_user(),
            ),
            value=[EntityExtractionCommand(
                model=FakeOrganisation,
                field_name='name',
                column_index='no_int',  # <==
                create=False,
            )],
            messages=_('Enter a valid value.'),
            codes='invalid',
        )

    def test_clean__forbidden_column(self):
        self.assertFormfieldError(
            field=EntityExtractorField(
                choices=[(0, 'Not in the file'), (1, 'Column 1')],
                models_info=[(FakeOrganisation, 'name')],
                user=self.get_root_user(),
            ),
            value=[EntityExtractionCommand(
                model=FakeOrganisation,
                field_name='name',
                column_index='2',
                create=False,
            )],
            messages=_('Enter a valid value.'),
            codes='invalid',
        )

    def test_clean__forbidden_creation(self):
        self.assertFormfieldError(
            field=EntityExtractorField(
                choices=[(0, 'Not in the file'), (1, 'Column 1')],
                models_info=[(FakeOrganisation, 'name')],
                user=self.weak_user,
            ),
            value=[EntityExtractionCommand(
                model=FakeOrganisation,
                field_name='name',
                column_index='1',
                create=True,
            )],
            messages=_(
                'You are not allowed to create: %(model)s'
            ) % {'model': 'Test Organisation'},
            codes='nocreationperm',
        )

    def test_clean__not_active_command(self):
        user = self.get_root_user()
        field = EntityExtractorField(
            choices=[(0, 'Not in the file'), (1, 'Column 1')],
            models_info=[(FakeOrganisation, 'name')],
            user=user,
            required=False,
        )
        self.assertFalse(field.required)

        cmd = EntityExtractionCommand(
            model=FakeOrganisation,
            field_name='name',
            column_index='0',  # <==
            create=False,
        )

        extractor = field.clean([cmd])
        self.assertIsInstance(extractor, EntityExtractor)
        self.assertListEqual([cmd], [*extractor.commands])

        # ---
        field.required = True
        self.assertFormfieldError(
            field=field,
            value=[cmd],
            messages=_('This field is required.'),
            codes='required',
        )


# class RelationExtractorFieldTestCase(CremeTestCase):
#     @classmethod
#     def setUpClass(cls):
#         super().setUpClass()
#
#         cls.rtype1 = RelationType.objects.builder(
#             id='test-subject_employed_by', predicate='is an employee of',
#             models=[FakeContact],
#         ).symmetric(
#             id='test-object_employed_by', predicate='employs',
#             models=[FakeOrganisation],
#         ).get_or_create()[0]
#         cls.rtype2 = RelationType.objects.builder(
#             id='test-subject_customer', predicate='is a customer of',
#             models=[FakeContact, FakeOrganisation],
#         ).symmetric(
#             id='test-object_customer', predicate='is a supplier of',
#             models=[FakeContact, FakeOrganisation],
#         ).get_or_create()[0]
#
#     @staticmethod
#     def _build_entry(*, rtype, model, column, subfield):
#         return {
#             'rtype':       rtype.id,
#             'ctype':       str(ContentType.objects.get_for_model(model).id),
#             'column':      str(column),
#             'searchfield': subfield,
#         }
#
#     @staticmethod
#     def _build_data(can_create, *entries):
#         return {
#             'can_create': can_create,
#             'selectorlist': json_dump([*entries]),
#         }
#
#     def test_attributes(self):
#         columns1 = [(1, 'Column #1'), (2, 'Column #2')]
#         field = RelationExtractorField(columns=columns1)
#         self.assertTrue(field.required)
#         self.assertIsNone(field.user)
#         self.assertListEqual(columns1, field.columns)
#         self.assertFalse([*field.allowed_rtypes])
#
#         widget = field.widget
#         self.assertIsInstance(field.widget, RelationExtractorSelector)
#         self.assertListEqual(columns1, widget.columns)
#         self.assertFalse([*widget.relation_types])
#
#         columns2 = [*columns1, (3, 'Column #3')]
#         field.columns = columns2
#         self.assertListEqual(columns2, field.columns)
#         self.assertListEqual(columns2, widget.columns)
#
#     def test_clean__one_rtype(self):
#         field = RelationExtractorField(
#             columns=[(1, 'Column #1'), (2, 'Column #2')],
#             allowed_rtypes=[self.rtype1.id, self.rtype2.id],
#         )
#
#         fname = 'name'
#         extractor = field.clean(
#             self._build_data(
#                 False,  # can_create
#                 self._build_entry(
#                     rtype=self.rtype1,
#                     model=FakeOrganisation,
#                     column=1,
#                     subfield=fname,
#                 ),
#             ),
#         )
#         self.assertIsInstance(extractor, MultiRelationsExtractor)
#
#         extractors = [*extractor]
#         self.assertEqual(1, len(extractors))
#
#         extractor = extractors[0]
#         self.assertIsInstance(extractor, RelationExtractor)
#         self.assertEqual(1,                extractor.column_index)
#         self.assertEqual(self.rtype1,      extractor.rtype)
#         self.assertEqual(FakeOrganisation, extractor.related_model)
#         self.assertEqual(fname,            extractor.subfield_search)
#         self.assertFalse(extractor.create_if_unfound())
#
#     def test_clean__two_rtypes(self):
#         field = RelationExtractorField(
#             columns=[(1, 'Column #1'), (2, 'Column #2'), (3, 'Column #3')],
#             allowed_rtypes=[self.rtype1.id, self.rtype2.id],
#         )
#
#         fname1 = 'name'
#         fname2 = 'email'
#         extractor1 = field.clean(
#             self._build_data(
#                 True,  # can_create
#                 self._build_entry(
#                     rtype=self.rtype1,
#                     model=FakeOrganisation,
#                     column=1,
#                     subfield=fname1,
#                 ),
#                 self._build_entry(
#                     rtype=self.rtype2,
#                     model=FakeContact,
#                     column=3,
#                     subfield=fname2,
#                 ),
#             ),
#         )
#
#         extractors = [*extractor1]
#         self.assertEqual(2, len(extractors))
#
#         extractor1 = extractors[0]
#         self.assertEqual(1,                extractor1.column_index)
#         self.assertEqual(self.rtype1,      extractor1.rtype)
#         self.assertEqual(FakeOrganisation, extractor1.related_model)
#         self.assertEqual(fname1,           extractor1.subfield_search)
#         self.assertTrue(extractor1.create_if_unfound())
#
#         extractor2 = extractors[1]
#         self.assertEqual(3,           extractor2.column_index)
#         self.assertEqual(self.rtype2, extractor2.rtype)
#         self.assertEqual(FakeContact, extractor2.related_model)
#         self.assertEqual(fname2,      extractor2.subfield_search)
#         self.assertTrue(extractor2.create_if_unfound())
#
#     def test_clean__empty(self):
#         field = RelationExtractorField(
#             columns=[(1, 'Column #1'), (2, 'Column #2')],
#             allowed_rtypes=[self.rtype1.id, self.rtype2.id],
#             required=False,
#         )
#         self.assertFalse(field.required)
#
#         data = self._build_data(False)
#         extractor = field.clean(data)
#         self.assertIsInstance(extractor, MultiRelationsExtractor)
#         self.assertFalse([*extractor])
#
#         # ---
#         field.required = True
#         self.assertFormfieldError(
#             field=field,
#             messages=_('This field is required.'),
#             codes='required',
#             value=data,
#         )
#
#     def test_clean__invalid_data_type(self):
#         self.assertFormfieldError(
#             field=RelationExtractorField(
#                 columns=[(1, 'Column #1'), (2, 'Column #2')],
#                 allowed_rtypes=[self.rtype1.id],
#                 required=False,
#             ),
#             value={
#                 'can_create': False,
#                 'selectorlist': json_dump({'foo': 'bar'}),  # <==
#             },
#             messages=_('Invalid format'),
#             codes='invalidformat',
#         )
#
#     def test_clean__forbidden_column(self):
#         self.assertFormfieldError(
#             field=RelationExtractorField(
#                 columns=[(1, 'Column #1'), (2, 'Column #2')],
#                 allowed_rtypes=[self.rtype1.id],
#                 required=False,
#             ),
#             value=self._build_data(
#                 False,  # can_create
#                 self._build_entry(
#                     rtype=self.rtype1,
#                     model=FakeOrganisation,
#                     column=3,  # <==
#                     subfield='name',
#                 ),
#             ),
#             messages=_('This column is not a valid choice.'),
#             codes='invalidcolunm',
#         )
#
#     def test_clean__invalid_search_field(self):
#         self.assertFormfieldError(
#             field=RelationExtractorField(
#                 columns=[(1, 'Column #1'), (2, 'Column #2')],
#                 allowed_rtypes=[self.rtype1.id],
#                 required=False,
#             ),
#             value=self._build_data(
#                 False,  # can_create
#                 self._build_entry(
#                     rtype=self.rtype1,
#                     model=FakeOrganisation,
#                     column=1,
#                     subfield='invalid_field',   # <==
#                 ),
#             ),
#             messages=_("This field doesn't exist in this ContentType."),
#             codes='fielddoesnotexist',
#         )
#
#     def test_clean__incompatible_ctype(self):
#         self.assertFormfieldError(
#             field=RelationExtractorField(
#                 columns=[(1, 'Column #1'), (2, 'Column #2')],
#                 allowed_rtypes=[self.rtype1.id],
#                 required=False,
#             ),
#             value=self._build_data(
#                 False,  # can_create
#                 self._build_entry(
#                     rtype=self.rtype1,
#                     model=FakeDocument,  # <==
#                     column=1,
#                     subfield='title',
#                 ),
#             ),
#             messages=_(
#                 'The type «%(model)s» is not allowed by the relationship «%(predicate)s».'
#             ) % {
#                 'model': FakeDocument._meta.verbose_name,
#                 'predicate': self.rtype1.symmetric_type.predicate,
#             },
#             codes='forbiddenctype',
#         )
#
#     def test_clean__forbidden_rtype(self):
#         self.assertFormfieldError(
#             field=RelationExtractorField(
#                 columns=[(1, 'Column #1'), (2, 'Column #2')],
#                 allowed_rtypes=[self.rtype1.id],
#                 required=False,
#             ),
#             value=self._build_data(
#                 False,  # can_create
#                 self._build_entry(
#                     rtype=self.rtype2,
#                     model=FakeDocument,  # <==
#                     column=1,
#                     subfield='title',
#                 ),
#             ),
#             messages=_(
#                 'This type of relationship causes a constraint error '
#                 '(id="%(rtype_id)s").'
#             ) % {'rtype_id': self.rtype2.id},
#             codes='rtypenotallowed',
#         )
class MultiRelationsExtractorFieldTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.rtype1 = RelationType.objects.builder(
            id='test-subject_employed_by', predicate='is an employee of',
            models=[FakeContact],
        ).symmetric(
            id='test-object_employed_by', predicate='employs',
            models=[FakeOrganisation],
        ).get_or_create()[0]
        cls.rtype2 = RelationType.objects.builder(
            id='test-subject_customer', predicate='is a customer of',
            models=[FakeContact, FakeOrganisation],
        ).symmetric(
            id='test-object_customer', predicate='is a supplier of',
            models=[FakeContact, FakeOrganisation],
        ).get_or_create()[0]

    @staticmethod
    def _build_entry(*, rtype, model, column, subfield):
        return {
            'rtype':       rtype.id,
            'ctype':       str(ContentType.objects.get_for_model(model).id),
            'column':      str(column),
            'searchfield': subfield,
        }

    @staticmethod
    def _build_data(can_create, *entries):
        return [
            'on' if can_create else '',
            json_dump([*entries]),
        ]

    def test_attributes(self):
        columns1 = [(1, 'Column #1'), (2, 'Column #2')]
        field = MultiRelationsExtractorField(columns=columns1)
        self.assertTrue(field.required)
        self.assertIsNone(field.user)
        self.assertListEqual(columns1, [*field.columns])
        self.assertFalse([*field.allowed_rtypes])

        widget = field.widget
        self.assertIsInstance(field.widget, MultiRelationsExtractorSelector)
        self.assertListEqual(columns1, widget.columns)
        self.assertFalse([*widget.relation_types])

        columns2 = [*columns1, (3, 'Column #3')]
        field.columns = columns2
        self.assertListEqual(columns2, [*field.columns])
        self.assertListEqual(columns2, widget.columns)

        rtypes = [self.rtype1, self.rtype2]
        field.allowed_rtypes = [rtype.id for rtype in rtypes]
        self.assertCountEqual(rtypes, field.allowed_rtypes)

        choices = widget.relation_types
        self.assertEqual(2, len(choices))
        self.assertInChoices(value=self.rtype1.id, label=str(self.rtype1), choices=choices)
        self.assertInChoices(value=self.rtype2.id, label=str(self.rtype2), choices=choices)

    def test_clean__one_rtype(self):
        field = MultiRelationsExtractorField(
            columns=[(1, 'Column #1'), (2, 'Column #2')],
            allowed_rtypes=[self.rtype1.id, self.rtype2.id],
        )
        self.assertCountEqual([self.rtype1, self.rtype2], field.allowed_rtypes)

        fname = 'name'
        extractor = field.clean(
            self._build_data(
                False,  # can_create
                self._build_entry(
                    rtype=self.rtype1,
                    model=FakeOrganisation,
                    column=1,
                    subfield=fname,
                ),
            ),
        )
        self.assertIsInstance(extractor, MultiRelationsExtractor)

        extractors = [*extractor]
        self.assertEqual(1, len(extractors))

        extractor = extractors[0]
        self.assertIsInstance(extractor, RelationExtractor)
        self.assertEqual(1,                extractor.column_index)
        self.assertEqual(self.rtype1,      extractor.rtype)
        self.assertEqual(FakeOrganisation, extractor.related_model)
        self.assertEqual(fname,            extractor.subfield_search)
        self.assertFalse(extractor.create_if_unfound)

    def test_clean__two_rtypes(self):
        field = MultiRelationsExtractorField(
            columns=[(1, 'Column #1'), (2, 'Column #2'), (3, 'Column #3')],
            allowed_rtypes=[self.rtype1.id, self.rtype2.id],
        )

        fname1 = 'name'
        fname2 = 'email'
        extractor1 = field.clean(
            self._build_data(
                True,  # can_create
                self._build_entry(
                    rtype=self.rtype1,
                    model=FakeOrganisation,
                    column=1,
                    subfield=fname1,
                ),
                self._build_entry(
                    rtype=self.rtype2,
                    model=FakeContact,
                    column=3,
                    subfield=fname2,
                ),
            ),
        )

        extractors = [*extractor1]
        self.assertEqual(2, len(extractors))

        extractor1 = extractors[0]
        self.assertEqual(1,                extractor1.column_index)
        self.assertEqual(self.rtype1,      extractor1.rtype)
        self.assertEqual(FakeOrganisation, extractor1.related_model)
        self.assertEqual(fname1,           extractor1.subfield_search)
        self.assertTrue(extractor1.create_if_unfound)

        extractor2 = extractors[1]
        self.assertEqual(3,           extractor2.column_index)
        self.assertEqual(self.rtype2, extractor2.rtype)
        self.assertEqual(FakeContact, extractor2.related_model)
        self.assertEqual(fname2,      extractor2.subfield_search)
        self.assertTrue(extractor2.create_if_unfound)

    def test_clean__empty__not_required(self):
        field = MultiRelationsExtractorField(
            columns=[(1, 'Column #1'), (2, 'Column #2')],
            allowed_rtypes=[self.rtype1.id, self.rtype2.id],
            required=False,
        )
        self.assertFalse(field.required)

        extractor = field.clean(self._build_data(False))
        self.assertIsInstance(extractor, MultiRelationsExtractor)
        self.assertFalse([*extractor])

    def test_clean__empty__required(self):
        field = MultiRelationsExtractorField(
            columns=[(1, 'Column #1'), (2, 'Column #2')],
            allowed_rtypes=[self.rtype1.id, self.rtype2.id],
            # required=True,
        )
        self.assertTrue(field.required)
        self.assertFormfieldError(
            field=field,
            messages=_('This field is required.'),
            codes='required',
            value=self._build_data(False),
        )

    def test_clean__invalid_data_type(self):
        self.assertFormfieldError(
            field=MultiRelationsExtractorField(
                columns=[(1, 'Column #1'), (2, 'Column #2')],
                allowed_rtypes=[self.rtype1.id],
                required=False,
            ),
            value=[
                '',
                json_dump({'foo': 'bar'}),  # <==
            ],
            messages=_('Invalid format'),
            codes='invalidformat',
        )

    def test_clean__forbidden_column(self):
        self.assertFormfieldError(
            field=MultiRelationsExtractorField(
                columns=[(1, 'Column #1'), (2, 'Column #2')],
                allowed_rtypes=[self.rtype1.id],
                required=False,
            ),
            value=self._build_data(
                False,  # can_create
                self._build_entry(
                    rtype=self.rtype1,
                    model=FakeOrganisation,
                    column=3,  # <==
                    subfield='name',
                ),
            ),
            messages=_('This column is not a valid choice.'),
            codes='invalidcolunm',
        )

    def test_clean__invalid_search_field(self):
        self.assertFormfieldError(
            field=MultiRelationsExtractorField(
                columns=[(1, 'Column #1'), (2, 'Column #2')],
                allowed_rtypes=[self.rtype1.id],
                required=False,
            ),
            value=self._build_data(
                False,  # can_create
                self._build_entry(
                    rtype=self.rtype1,
                    model=FakeOrganisation,
                    column=1,
                    subfield='invalid_field',   # <==
                ),
            ),
            messages=_("This field doesn't exist in this ContentType."),
            codes='fielddoesnotexist',
        )

    def test_clean__incompatible_ctype(self):
        self.assertFormfieldError(
            field=MultiRelationsExtractorField(
                columns=[(1, 'Column #1'), (2, 'Column #2')],
                allowed_rtypes=[self.rtype1.id],
                required=False,
            ),
            value=self._build_data(
                False,  # can_create
                self._build_entry(
                    rtype=self.rtype1,
                    model=FakeDocument,  # <==
                    column=1,
                    subfield='title',
                ),
            ),
            messages=_(
                'The type «%(model)s» is not allowed by the relationship «%(predicate)s».'
            ) % {
                'model': FakeDocument._meta.verbose_name,
                'predicate': self.rtype1.symmetric_type.predicate,
            },
            codes='forbiddenctype',
        )

    def test_clean__forbidden_rtype(self):
        self.assertFormfieldError(
            field=MultiRelationsExtractorField(
                columns=[(1, 'Column #1'), (2, 'Column #2')],
                allowed_rtypes=[self.rtype1.id],
                required=False,
            ),
            value=self._build_data(
                False,  # can_create
                self._build_entry(
                    rtype=self.rtype2,
                    model=FakeDocument,  # <==
                    column=1,
                    subfield='title',
                ),
            ),
            messages=_(
                'This type of relationship causes a constraint error '
                '(id="%(rtype_id)s").'
            ) % {'rtype_id': self.rtype2.id},
            codes='rtypenotallowed',
        )


class CustomfieldExtractorFieldTestCase(CremeTestCase):
    def test_attributes(self):
        user = self.get_root_user()

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
        user = self.get_root_user()

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

        message = _('Enter a valid value.')
        code = 'invalid'
        self.assertFormfieldError(
            field=field, value='notadict', messages=message, codes=code,
        )
        self.assertFormfieldError(
            field=field, value={'selected_column': 'notanint'}, messages=message, codes=code,
        )
        self.assertFormfieldError(
            field=field, value={'selected_column': '25'}, messages=message, codes=code,
        )
        self.assertFormfieldError(
            field=field,
            value={'selected_column': '1'},  # No default value
            messages='Widget seems buggy, no default value',
            codes=code,
        )

    def test_clean(self):
        user = self.get_root_user()

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
        extractor = field.clean({
            'selected_column': str(col),
            'default_value': def_val,
            # 'can_create': '',
        })
        self.assertIsInstance(extractor, CustomFieldExtractor)
        self.assertEqual(col, extractor._column_index)
        self.assertEqual(def_val, extractor._default_value)

        line = ['Claus', 'Valca', 'Piloting']
        value, err_msg = extractor.extract_value(line, user)
        self.assertIsNone(err_msg)
        self.assertEqual(line[2], value)

    # TODO: can_create
