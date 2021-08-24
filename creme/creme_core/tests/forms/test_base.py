# -*- coding: utf-8 -*-

from functools import partial

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.forms.boundfield import BoundField
from django.test.utils import override_settings
from django.utils.translation import gettext as _

from creme.creme_config.forms.fields import (
    CustomEnumChoiceField,
    CustomMultiEnumChoiceField,
)
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.forms import CremeForm, CremeModelForm
from creme.creme_core.forms.widgets import Label
from creme.creme_core.models import (
    CremePropertyType,
    CustomField,
    CustomFieldEnumValue,
    CustomFieldInteger,
    FakeAddress,
    FakeContact,
    FakeOrganisation,
    FakeSector,
    FieldsConfig,
    Relation,
    RelationType,
    SemiFixedRelationType,
    SetCredentials,
)

from ..base import CremeTestCase
from ..fake_forms import FakeContactForm


class CremeFormTestCase(CremeTestCase):
    def test_user(self):
        user = self.create_user()

        class TestCremeForm(CremeForm):
            order = forms.IntegerField(label='Order')

        form = TestCremeForm(user=user)
        self.assertEqual(user, form.fields['order'].user)

    def test_blocks(self):
        user = self.create_user()

        class TestCremeForm(CremeForm):
            order = forms.IntegerField(label='Order')
            description = forms.CharField(label='Description', required=False)

        form = TestCremeForm(user=user)

        blocks = form.get_blocks()
        with self.assertNoException():
            general_group = blocks['general']

        self.assertEqual(_('General information'), general_group.label)

        bound_fields = general_group.bound_fields
        self.assertIsList(bound_fields, length=2)

        # --
        bound_field1 = bound_fields[0]
        self.assertIsInstance(bound_field1, BoundField)
        self.assertEqual('order', bound_field1.name)

        # --
        self.assertEqual('description', bound_fields[1].name)

    def test_hook(self):
        user = self.create_user()

        class TestCremeForm(CremeForm):
            order = forms.IntegerField(label='Order')

        init_cb_args = []
        clean_cb_args = []
        save_cb_args = []

        def init_cb(*args):
            init_cb_args.extend(args)

        def clean_cb(*args):
            clean_cb_args.extend(args)

        def save_cb(*args):
            save_cb_args.extend(args)

        TestCremeForm.add_post_init_callback(init_cb) \
                     .add_post_clean_callback(clean_cb) \
                     .add_post_save_callback(save_cb)

        form = TestCremeForm(user=user, data={'order': 123})
        self.assertListEqual([form], init_cb_args)
        self.assertFalse(clean_cb_args)
        self.assertFalse(save_cb_args)

        form.full_clean()
        self.assertListEqual([form], init_cb_args)
        self.assertListEqual([form], clean_cb_args)
        self.assertFalse(save_cb_args)

        form.save()
        self.assertListEqual([form], init_cb_args)
        self.assertListEqual([form], clean_cb_args)
        self.assertListEqual([form], save_cb_args)


class CremeModelFormTestCase(CremeTestCase):
    def test_basic(self):
        user = self.create_user()

        class FakeSectorForm(CremeModelForm):
            class Meta:
                model = FakeSector
                fields = '__all__'

        form2 = FakeSectorForm(user=user)
        fields = form2.fields

        with self.assertNoException():
            order_f = fields['title']

        self.assertEqual(user, order_f.user)
        self.assertIn('is_custom', fields)
        self.assertNotIn('order',  fields)

        # ---
        blocks = form2.get_blocks()
        with self.assertNoException():
            general_group = blocks['general']

        self.assertEqual(_('General information'), general_group.label)
        self.assertEqual(2, len(general_group.bound_fields))

        # --
        form1 = FakeSectorForm(user=user, data={})
        self.assertFormInstanceErrors(form1, ('title', _('This field is required.')))

        # --
        title = 'IT'
        form2 = FakeSectorForm(user=user, data={'title': title})
        self.assertFalse(form2.errors)

        sector = form2.save()
        self.assertIsInstance(sector, FakeSector)
        self.assertEqual(title, sector.title)
        self.assertFalse(sector.is_custom)
        self.assertIsNotNone(sector.id)

    def test_hook(self):
        user = self.create_user()

        class FakeSectorForm(CremeModelForm):
            class Meta:
                model = FakeSector
                fields = '__all__'

        init_cb_args = []
        clean_cb_args = []
        save_cb_args = []

        def init_cb(*args):
            init_cb_args.extend(args)

        def clean_cb(*args):
            clean_cb_args.extend(args)

        def save_cb(*args):
            save_cb_args.extend(args)

        FakeSectorForm.add_post_init_callback(init_cb) \
                      .add_post_clean_callback(clean_cb) \
                      .add_post_save_callback(save_cb)

        form = FakeSectorForm(user=user, data={'title': 'Sector#1'})
        self.assertListEqual([form], init_cb_args)
        self.assertFalse(clean_cb_args)
        self.assertFalse(save_cb_args)

        form.full_clean()
        self.assertListEqual([form], init_cb_args)
        self.assertListEqual([form], clean_cb_args)
        self.assertFalse(save_cb_args)

        form.save()
        self.assertListEqual([form], init_cb_args)
        self.assertListEqual([form], clean_cb_args)
        self.assertListEqual([form], save_cb_args)

    def test_fields_config(self):
        user = self.create_user()

        FieldsConfig.objects.create(
            content_type=FakeAddress,
            descriptions=[('department', {FieldsConfig.HIDDEN: True})],
        )

        class FakeAddressForm(CremeModelForm):
            class Meta:
                model = FakeAddress
                exclude = ('zipcode', )

        fields = FakeAddressForm(user=user).fields
        self.assertIn('value', fields)
        self.assertIn('city',  fields)
        self.assertNotIn('zipcode',    fields)
        self.assertNotIn('department', fields)


@override_settings(FORMS_RELATION_FIELDS=True)
class CremeEntityFormTestCase(CremeTestCase):
    def test_basic(self):
        user = self.create_user()

        form1 = FakeContactForm(user=user)
        fields = form1.fields
        self.assertIn('first_name', fields)
        self.assertIn('last_name', fields)
        self.assertNotIn('is_user', fields)

        # ---
        blocks = form1.get_blocks()
        with self.assertNoException():
            general_group = blocks['general']

        self.assertEqual(_('General information'), general_group.label)
        self.assertGreater(len(general_group.bound_fields), 10)

        # ---
        first_name = 'Kanbaru'
        last_name = 'Suruga'
        form2 = FakeContactForm(
            user=user,
            data={
                'user':       user.id,
                'first_name': first_name,
                'last_name':  last_name,
            },
        )
        self.assertFalse(form2.errors)

        contact = form2.save()
        self.assertIsInstance(contact, FakeContact)
        self.assertEqual(user,       contact.user)
        self.assertEqual(first_name, contact.first_name)
        self.assertEqual(last_name,  contact.last_name)
        self.assertIsNotNone(contact.id)

    def test_customfields01(self):
        user = self.create_user()

        create_cf = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeContact),
        )
        cfield1 = create_cf(name='Size',   field_type=CustomField.INT)
        cfield2 = create_cf(name='Cursed', field_type=CustomField.BOOL)
        cfield3 = create_cf(name='Animal', field_type=CustomField.ENUM)
        cfield4 = create_cf(name='Sports', field_type=CustomField.MULTI_ENUM)
        deleted = create_cf(name='Deleted', field_type=CustomField.INT, is_deleted=True)

        create_evalue = CustomFieldEnumValue.objects.create
        eval1_01 = create_evalue(value='Crab',        custom_field=cfield3)
        eval1_02 = create_evalue(value='Monkey',      custom_field=cfield3)
        eval2_01 = create_evalue(value='Basket Ball', custom_field=cfield4)
        eval2_02 = create_evalue(value='Kendo',       custom_field=cfield4)

        fields = FakeContactForm(user=user).fields

        with self.assertNoException():
            cf_f1 = fields[f'custom_field-{cfield1.id}']
            cf_f2 = fields[f'custom_field-{cfield2.id}']
            cf_f3 = fields[f'custom_field-{cfield3.id}']
            cf_f4 = fields[f'custom_field-{cfield4.id}']

        self.assertIsInstance(cf_f1, forms.IntegerField)
        self.assertEqual(cfield1.name, cf_f1.label)
        self.assertFalse(cf_f1.required)

        self.assertIsInstance(cf_f2, forms.NullBooleanField)
        self.assertEqual(cfield2.name, cf_f2.label)
        self.assertFalse(cf_f2.required)

        self.assertIsInstance(cf_f3, CustomEnumChoiceField)
        self.assertEqual(user,    cf_f3.user)
        self.assertEqual(cfield3, cf_f3.custom_field)
        self.assertListEqual(
            [
                ('', '-------'),
                (eval1_01.id, eval1_01.value),
                (eval1_02.id, eval1_02.value),
            ],
            cf_f3.choices,
        )

        self.assertIsInstance(cf_f4, CustomMultiEnumChoiceField)
        self.assertEqual(user,    cf_f4.user)
        self.assertEqual(cfield4, cf_f4.custom_field)
        self.assertListEqual(
            [
                (eval2_01.id, eval2_01.value),
                (eval2_02.id, eval2_02.value),
            ],
            cf_f4.choices,
        )

        self.assertNotIn(f'custom_field-{deleted.id}', fields)

        # ---
        first_name = 'Karen'
        last_name = 'Araragi'
        form2 = FakeContactForm(
            user=user,
            data={
                'user':       user.id,
                'first_name': first_name,
                'last_name':  last_name,

                f'custom_field-{cfield1.id}': '150',
                f'custom_field-{cfield2.id}': '',
                f'custom_field-{cfield3.id}': '',
            },
        )
        self.assertFalse(form2.errors)

        contact = form2.save()
        self.assertIsInstance(contact, FakeContact)
        self.assertEqual(first_name, contact.first_name)
        self.assertEqual(last_name,  contact.last_name)

        cf_value = self.get_object_or_fail(
            CustomFieldInteger, custom_field=cfield1, entity=contact,
        )
        self.assertEqual(150, cf_value.value)

    def test_customfields02(self):
        "Required."
        user = self.create_user()

        cfield = CustomField.objects.create(
            name='Size',
            content_type=FakeContact,
            field_type=CustomField.INT,
            is_required=True,
        )

        fields = FakeContactForm(user=user).fields

        with self.assertNoException():
            cfield_f = fields[f'custom_field-{cfield.id}']

        self.assertIsInstance(cfield_f, forms.IntegerField)
        self.assertTrue(cfield_f.required)

    def test_customfields03(self):
        "Required + Boolean."
        user = self.create_user()

        cfield = CustomField.objects.create(
            name='Cursed?',
            content_type=FakeContact,
            field_type=CustomField.BOOL,
            is_required=True,
        )

        fields = FakeContactForm(user=user).fields

        with self.assertNoException():
            cfield_f = fields[f'custom_field-{cfield.id}']

        self.assertIsInstance(cfield_f, forms.BooleanField)
        self.assertNotIsInstance(cfield_f, forms.NullBooleanField)
        self.assertFalse(cfield_f.required)

    def test_properties01(self):
        user = self.create_user()

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype01 = create_ptype(
            str_pk='test-prop_spirit', text='Haunted by a spirit',
        )
        ptype02 = create_ptype(
            str_pk='test-prop_bakemono', text='Cursed by a bakemono',
        )
        ptype03 = create_ptype(
            str_pk='test-prop_see', text='See the yokai',
            subject_ctypes=[FakeContact],
        )
        ptype04 = create_ptype(
            str_pk='test-prop_license', text='Has a license',
            subject_ctypes=[FakeOrganisation],
        )

        form1 = FakeContactForm(user=user)

        with self.assertNoException():
            ptypes_choices = form1.fields['property_types'].choices

        # Choices are sorted with 'text'
        choices = [(choice[0].value, choice[1]) for choice in ptypes_choices]
        i1 = self.assertIndex((ptype02.id, ptype02.text), choices)
        i2 = self.assertIndex((ptype01.id, ptype01.text), choices)
        i3 = self.assertIndex((ptype03.id, ptype03.text), choices)
        self.assertLess(i1, i2)
        self.assertLess(i2, i3)

        self.assertNotIn((ptype04.id, ptype04.text), choices)

        # ---
        blocks = form1.get_blocks()

        with self.assertNoException():
            prop_group = blocks['properties']

        self.assertEqual(_('Properties'), prop_group.label)

        bound_fields = prop_group.bound_fields
        self.assertEqual(len(bound_fields), 1)
        self.assertEqual('property_types', bound_fields[0].name)

        # ---
        form2 = FakeContactForm(
            user=user,
            data={
                'user':       user.id,
                'first_name': 'Kanbaru',
                'last_name':  'Suruga',

                'property_types': [ptype01.id, ptype03.id],
            },
        )
        self.assertFalse(form2.errors)

        contact = form2.save()
        self.assertSetEqual(
            {ptype01, ptype03}, {p.type for p in contact.properties.all()}
        )

    def test_properties02(self):
        "Forced CremePropertyTypes (IDs)."
        user = self.create_user()

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype01 = create_ptype(
            str_pk='test-prop_spirit',   text='Haunted by a spirit',
        )
        ptype02 = create_ptype(
            str_pk='test-prop_bakemono', text='Cursed by a bakemono',
        )
        ptype03 = create_ptype(
            str_pk='test-prop_see', text='See the yokai', subject_ctypes=[FakeContact],
        )

        form = FakeContactForm(user=user, forced_ptypes=[ptype02.id])

        with self.assertNoException():
            ptypes_choices = form.fields['property_types'].choices

        choices = [
            (choice_obj.value, choice_obj.readonly)
            for choice_obj, _label in ptypes_choices
        ]
        self.assertIndex((ptype01.id, False), choices)
        self.assertIndex((ptype02.id, True),  choices)
        self.assertIndex((ptype03.id, False), choices)

    def test_properties03(self):
        "Forced CremePropertyTypes (instances)."
        user = self.create_user()

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype01 = create_ptype(
            str_pk='test-prop_spirit',   text='Haunted by a spirit',
        )
        ptype02 = create_ptype(
            str_pk='test-prop_bakemono', text='Cursed by a bakemono',
        )
        ptype03 = create_ptype(
            str_pk='test-prop_see', text='See the yokai', subject_ctypes=[FakeContact],
        )

        form = FakeContactForm(user=user, forced_ptypes=[ptype02])

        with self.assertNoException():
            ptypes_choices = form.fields['property_types'].choices

        choices = [
            (choice_obj.value, choice_obj.readonly)
            for choice_obj, _label in ptypes_choices
        ]
        self.assertIndex((ptype01.id, False), choices)
        self.assertIndex((ptype02.id, True),  choices)
        self.assertIndex((ptype03.id, False), choices)

    @override_settings(FORMS_RELATION_FIELDS=False)
    def test_properties04(self):
        "Forced CremePropertyTypes + no <properties> field."
        user = self.create_user()

        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_spirit', text='Haunted by a spirit',
        )

        form = FakeContactForm(
            user=user, forced_ptypes=[ptype.id],
            data={
                'user': user.id,
                'first_name': 'Kanbaru',
                'last_name': 'Suruga',
            },
        )
        self.assertFalse(form.errors)

        contact = form.save()
        self.assertListEqual(
            [ptype], [p.type for p in contact.properties.all()]
        )

    def test_relations01(self):
        user = self.create_user()

        contact = FakeContact.objects.create(
            user=user, first_name='Hitagi', last_name='Senjyogahara',
        )
        orga = FakeOrganisation.objects.create(user=user, name='Oshino corp.')

        create_rtype = RelationType.objects.smart_update_or_create
        rtype1 = create_rtype(
            ('test-subject_loves', 'loves'),
            ('test-object_loves',  'is loved'),
        )[0]
        rtype2 = create_rtype(
            ('test-subject_heals', 'has healed', [FakeOrganisation]),
            ('test-object_heals',  'healed by',  [FakeContact]),
        )[1]

        form1 = FakeContactForm(user=user)
        fields = form1.fields
        self.assertIn('relation_types', fields)
        self.assertNotIn('semifixed_rtypes', fields)
        self.assertNotIn('rtypes_info',      fields)

        # ---
        blocks = form1.get_blocks()

        with self.assertNoException():
            relation_group = blocks['relationships']

        self.assertEqual(_('Relationships'), relation_group.label)

        self.assertListEqual(
            ['relation_types'],
            [bf.name for bf in relation_group.bound_fields],
        )

        # ---
        form2 = FakeContactForm(
            user=user,
            data={
                'user':       user.id,
                'first_name': 'Kanbaru',
                'last_name':  'Suruga',

                'relation_types': self.formfield_value_multi_relation_entity(
                    (rtype1.id, contact),
                    (rtype2.id, orga),
                    (rtype2.id, orga),  # Duplicates
                ),
            },
        )
        self.assertFalse(form2.errors)

        subject = form2.save()
        self.assertEqual(2, subject.relations.count())
        self.assertRelationCount(1, subject, rtype1, contact)
        self.assertRelationCount(1, subject, rtype2, orga)

    def test_relations02(self):
        "Semi-fixed."
        user = self.create_user()

        contact = FakeContact.objects.create(
            user=user, first_name='Hitagi', last_name='Senjyogahara',
        )
        orga = FakeOrganisation.objects.create(user=user, name='Oshino corp.')

        create_rtype = RelationType.objects.smart_update_or_create
        rtype1 = create_rtype(
            ('test-subject_loves', 'loves'),
            ('test-object_loves',  'is loved'),
        )[0]
        rtype2 = create_rtype(
            ('test-subject_heals', 'has healed', [FakeOrganisation]),
            ('test-object_heals',  'healed by',  [FakeContact]),
        )[1]

        create_strt = SemiFixedRelationType.objects.create
        sfrt1 = create_strt(
            predicate='Healed by Oshino', relation_type=rtype2, object_entity=orga,
        )
        sfrt2 = create_strt(
            predicate='Loves Hitagi', relation_type=rtype1, object_entity=contact,
        )

        form1 = FakeContactForm(user=user)
        fields = form1.fields
        self.assertIn('relation_types', fields)
        self.assertNotIn('rtypes_info', fields)

        with self.assertNoException():
            sf_choices = fields['semifixed_rtypes'].choices

        self.assertInChoices(value=sfrt1.id, label=sfrt1.predicate, choices=sf_choices)
        self.assertInChoices(value=sfrt2.id, label=sfrt2.predicate, choices=sf_choices)

        # ---
        blocks = form1.get_blocks()

        with self.assertNoException():
            relation_group = blocks['relationships']

        self.assertEqual(_('Relationships'), relation_group.label)
        self.assertListEqual(
            ['relation_types', 'semifixed_rtypes'],
            [bf.name for bf in relation_group.bound_fields],
        )

        # ---
        form2 = FakeContactForm(
            user=user,
            data={
                'user':       user.id,
                'first_name': 'Kanbaru',
                'last_name':  'Suruga',

                'semifixed_rtypes': [sfrt1.id, sfrt2.id],
            },
        )
        self.assertFalse(form2.errors)

        subject = form2.save()
        self.assertEqual(2, subject.relations.count())
        self.assertRelationCount(1, subject, rtype1, contact)
        self.assertRelationCount(1, subject, rtype2, orga)

    def test_relations03(self):
        "Fixed & semi-fixed."
        user = self.create_user()

        contact = FakeContact.objects.create(
            user=user, first_name='Hitagi', last_name='Senjyogahara',
        )
        orga = FakeOrganisation.objects.create(user=user, name='Oshino corp.')

        create_rtype = RelationType.objects.smart_update_or_create
        rtype1 = create_rtype(
            ('test-subject_loves', 'loves'),
            ('test-object_loves',  'is loved'),
        )[0]
        rtype2 = create_rtype(
            ('test-subject_heals', 'has healed', [FakeOrganisation]),
            ('test-object_heals',  'healed by',  [FakeContact]),
        )[1]

        create_strt = SemiFixedRelationType.objects.create
        sfrt1 = create_strt(
            predicate='Healed by Oshino', relation_type=rtype2, object_entity=orga,
        )
        sfrt2 = create_strt(
            predicate='Loves Hitagi', relation_type=rtype1, object_entity=contact,
        )

        form = FakeContactForm(
            user=user,
            data={
                'user':       user.id,
                'first_name': 'Kanbaru',
                'last_name':  'Suruga',

                'relation_types': self.formfield_value_multi_relation_entity(
                    (rtype1.id, contact),  # Duplicated with fixed
                ),
                'semifixed_rtypes': [sfrt1.id, sfrt2.id],
            },
        )
        self.assertFalse(form.errors)

        subject = form.save()
        self.assertEqual(2, subject.relations.count())
        self.assertRelationCount(1, subject, rtype1, contact)
        self.assertRelationCount(1, subject, rtype2, orga)

    def test_relations04(self):
        "Forced Relations."
        user = self.create_user()

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Hitagi', last_name='Senjyogahara')
        contact2 = create_contact(first_name='Koyomi', last_name='Araragi')

        orga = FakeOrganisation.objects.create(user=user, name='Oshino corp.')

        create_rtype = RelationType.objects.smart_update_or_create
        rtype1 = create_rtype(
            ('test-subject_loves', 'loves'),
            ('test-object_loves',  'is loved'),
        )[0]
        rtype2 = create_rtype(
            ('test-subject_heals', 'has healed', [FakeOrganisation]),
            ('test-object_heals',  'healed by',  [FakeContact]),
        )[1]

        fields1 = FakeContactForm(
            user=user,
            forced_relations=[Relation(type=rtype2, object_entity=orga)],
        ).fields

        with self.assertNoException():
            info_field = fields1['rtypes_info']

        self.assertIn('relation_types', fields1)
        self.assertHTMLEqual(
            _('This relationship will be added: {predicate} «{entity}»').format(
                predicate=rtype2.predicate,
                entity=orga,
            ),
            info_field.initial
        )

        # ---
        forced_relations = [
            Relation(type=rtype2, object_entity=orga),
            Relation(type=rtype1, object_entity=contact1),
        ]
        fields2 = FakeContactForm(user=user, forced_relations=forced_relations).fields

        self.assertIn('relation_types', fields2)
        self.assertHTMLEqual(
            _('These relationships will be added: {}').format(
                f'<ul><li>{rtype2.predicate} «{orga}»</li>'
                f'<li>{rtype1.predicate} «{contact1}»</li></ul>'
            ),
            fields2['rtypes_info'].initial,
        )

        # ---
        form = FakeContactForm(
            user=user,
            forced_relations=forced_relations,
            data={
                'user':       user.id,
                'first_name': 'Kanbaru',
                'last_name':  'Suruga',

                'relation_types': self.formfield_value_multi_relation_entity(
                    (rtype1.id, contact2),
                ),
            },
        )
        self.assertFalse(form.errors)

        subject = form.save()
        self.assertRelationCount(1, subject, rtype1, contact1)
        self.assertRelationCount(1, subject, rtype1, contact2)
        self.assertRelationCount(1, subject, rtype2, orga)

    @override_settings(FORMS_RELATION_FIELDS=False)
    def test_relations05(self):
        "Forced Relations (no <relations> block)."
        user = self.create_user()

        orga = FakeOrganisation.objects.create(user=user, name='Oshino corp.')
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_heals', 'has healed'),
            ('test-object_heals',  'healed by'),
        )[1]

        form = FakeContactForm(
            user=user,
            forced_relations=[Relation(type=rtype, object_entity=orga)],
        )
        self.assertNotIn('rtypes_info', form.fields)

    @override_settings(FORMS_RELATION_FIELDS=False)
    def test_no_relations_fields01(self):
        "FORMS_RELATION_FIELDS == False."
        user = self.create_user()

        fields = FakeContactForm(user=user).fields
        self.assertNotIn('property_types',   fields)
        self.assertNotIn('relation_types',   fields)
        self.assertNotIn('semifixed_rtypes', fields)
        self.assertNotIn('rtypes_info',      fields)

    def test_no_relations_fields02(self):
        "Edition => no relations/properties field."
        user = self.create_user()

        contact = FakeContact.objects.create(
            user=user, first_name='Kanbaru', last_name='Suruga',
        )

        fields = FakeContactForm(user=user, instance=contact).fields
        self.assertNotIn('property_types',   fields)
        self.assertNotIn('relation_types',   fields)
        self.assertNotIn('semifixed_rtypes', fields)
        self.assertNotIn('rtypes_info',      fields)

    def test_relations_credentials01(self):
        user = self.login(is_superuser=False, creatable_models=[FakeContact])
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

        create_contact = FakeContact.objects.create
        contact1 = create_contact(user=user, first_name='Kanbaru', last_name='Suruga')
        self.assertTrue(user.has_perm_to_link(contact1))

        contact2 = create_contact(
            user=self.other_user, first_name='Hitagi', last_name='Senjyogahara',
        )
        self.assertFalse(user.has_perm_to_link(contact2))

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_loves', 'loves'),
            ('test-object_loves',  'is loved'),
        )[0]

        create_strt = SemiFixedRelationType.objects.create
        sfrt1 = create_strt(
            predicate='Loves Kanbaru', relation_type=rtype, object_entity=contact1,
        )
        sfrt2 = create_strt(
            predicate='Loves Hitagi', relation_type=rtype, object_entity=contact2,
        )

        form = FakeContactForm(user=user)
        fields = form.fields

        with self.assertNoException():
            sf_choices = fields['semifixed_rtypes'].choices

        self.assertInChoices(value=sfrt1.id, label=sfrt1.predicate, choices=sf_choices)
        self.assertNotInChoices(value=sfrt2.id, choices=sf_choices)

    def test_relations_credentials02(self):
        "Label if cannot link the future entity."
        user = self.login(is_superuser=False, creatable_models=[FakeContact])

        create_creds = partial(SetCredentials.objects.create, role=self.role)
        create_creds(
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_OWN,
        )
        create_creds(
            value=EntityCredentials.LINK,
            set_type=SetCredentials.ESET_ALL,
            ctype=FakeContact, forbidden=True,
        )

        orga = FakeOrganisation.objects.create(user=user, name='Oshino corp.')

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_heals', 'heals'),
            ('test-object_heals',  'is healed by'),
        )[1]

        sfrt = SemiFixedRelationType.objects.create(
            predicate='Healed by Oshino', relation_type=rtype, object_entity=orga,
        )

        fields = FakeContactForm(user=user).fields

        with self.assertNoException():
            info_field = fields['rtypes_info']

        self.assertNotIn('relation_types', fields)
        self.assertNotIn('semifixed_rtypes', fields)
        self.assertIsInstance(info_field.widget, Label)
        self.assertEqual(
            _('You are not allowed to link this kind of entity.'),
            info_field.initial,
        )

        # ---
        form2 = FakeContactForm(
            user=user,
            data={
                'user':       user.id,
                'first_name': 'Kanbaru',
                'last_name':  'Suruga',

                'relation_types': self.formfield_value_multi_relation_entity(
                    (rtype.id, orga),  # Should not be used
                ),
                'semifixed_rtypes': [sfrt.id],  # Idem
            },
        )
        self.assertFalse(form2.errors)

        subject = form2.save()
        self.assertFalse(subject.relations.count())

    def test_relations_credentials03(self):
        "Link credentials on the created entity."
        user = self.login(is_superuser=False, creatable_models=[FakeContact])

        create_creds = partial(SetCredentials.objects.create, role=self.role)
        create_creds(
            value=EntityCredentials.VIEW | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_OWN,
        )
        create_creds(value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)

        orga = FakeOrganisation.objects.create(user=user, name='Oshino corp.')

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_heals', 'heals'),
            ('test-object_heals',  'is healed by'),
        )[1]

        data = {
            'first_name': 'Kanbaru',
            'last_name': 'Suruga',
            'relation_types': self.formfield_value_multi_relation_entity(
                (rtype.id, orga),
            ),
        }

        # KO ---
        form1 = FakeContactForm(user=user, data={**data, 'user': self.other_user.id})
        self.assertFormInstanceErrors(
            form1,
            (
                'relation_types',
                _('You are not allowed to link the created entity (wrong owner?).'),
            ),
        )

        # OK ---
        form2 = FakeContactForm(user=user, data={**data, 'user': user.id})
        self.assertFalse(form2.errors)

        subject = form2.save()
        self.assertRelationCount(1, subject, rtype, orga)

    def test_relations_credentials04(self):
        "Link credentials on the created entity (semi-fixed version)."
        user = self.login(is_superuser=False, creatable_models=[FakeContact])

        create_creds = partial(SetCredentials.objects.create, role=self.role)
        create_creds(
            value=EntityCredentials.VIEW | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_OWN,
        )
        create_creds(value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)

        orga = FakeOrganisation.objects.create(user=user, name='Oshino corp.')

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_heals', 'heals'),
            ('test-object_heals',  'is healed by'),
        )[1]
        sfrt = SemiFixedRelationType.objects.create(
            predicate='Healed by Oshino', relation_type=rtype, object_entity=orga,
        )

        data = {
            'first_name': 'Kanbaru',
            'last_name': 'Suruga',
            'semifixed_rtypes': [sfrt.id],
        }

        # KO ---
        form1 = FakeContactForm(user=user, data={**data, 'user': self.other_user.id})
        self.assertFormInstanceErrors(
            form1,
            (
                'semifixed_rtypes',
                _('You are not allowed to link the created entity (wrong owner?).'),
            ),
        )

        # OK ---
        form2 = FakeContactForm(user=user, data={**data, 'user': user.id})
        self.assertFalse(form2.errors)

        subject = form2.save()
        self.assertRelationCount(1, subject, rtype, orga)

    def test_relations_credentials05(self):
        "No link credentials on the created entity but no relation wanted."
        user = self.login(is_superuser=False, creatable_models=[FakeContact])

        create_creds = partial(SetCredentials.objects.create, role=self.role)
        create_creds(
            value=EntityCredentials.VIEW | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_OWN,
        )
        create_creds(value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)

        form = FakeContactForm(
            user=user,
            data={
                'user':       self.other_user.id,
                'first_name': 'Kanbaru',
                'last_name':  'Suruga',
            },
        )
        self.assertFalse(form.errors)

    def test_relations_credentials06(self):
        "Link credentials on the created entity + forced relationships."
        user = self.login(is_superuser=False, creatable_models=[FakeContact])

        create_creds = partial(SetCredentials.objects.create, role=self.role)
        create_creds(
            value=EntityCredentials.VIEW | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_OWN,
        )
        create_creds(value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)

        orga = FakeOrganisation.objects.create(user=user, name='Oshino corp.')

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_heals', 'heals'),
            ('test-object_heals',  'is healed by'),
        )[1]

        data = {
            'first_name': 'Kanbaru',
            'last_name': 'Suruga',
        }
        forced_relations = [Relation(type=rtype, object_entity=orga)]

        # KO ---
        form1 = FakeContactForm(
            user=user,
            data={**data, 'user': self.other_user.id},
            forced_relations=forced_relations,
        )
        self.assertFormInstanceErrors(
            form1,
            (
                'user',
                _('You are not allowed to link with the «{models}» of this user.').format(
                    models='Test Contacts',
                ),
            ),
        )

        # OK ---
        form2 = FakeContactForm(
            user=user,
            data={**data, 'user': user.id},
            forced_relations=forced_relations,
        )
        self.assertFalse(form2.errors)

        subject = form2.save()
        self.assertRelationCount(1, subject, rtype, orga)

    def test_relations_error01(self):
        "ContentType constraint error."
        user = self.login()

        orga = FakeOrganisation.objects.create(user=user, name='Oshino corp.')
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_registered', 'has registered',      [FakeOrganisation]),
            ('test-object_registered',  'has been registered', [FakeOrganisation]),
        )[0]

        SemiFixedRelationType.objects.create(
            predicate='has registered Oshino',
            relation_type=rtype,
            object_entity=orga,
        )  # Not available

        # ---
        form1 = FakeContactForm(user=user)
        self.assertNotIn('semifixed_rtypes', form1.fields)

        # ---
        form2 = FakeContactForm(
            user=user,
            data={
                'user':       user.id,
                'first_name': 'Kanbaru',
                'last_name':  'Suruga',

                'relation_types': self.formfield_value_multi_relation_entity(
                    (rtype.id, orga),
                ),
            },
        )
        self.assertFormInstanceErrors(
            form2,
            (
                'relation_types',
                _(
                    'This type of relationship causes a constraint error '
                    '(id="%(rtype_id)s").'
                ) % {'rtype_id': rtype.id},
            ),
        )

    @override_settings(FORMS_RELATION_FIELDS=True)
    def test_relations_error02(self):
        "Property constraint errors."
        user = self.login()

        orga = FakeOrganisation.objects.create(user=user, name='Bebop')

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-prop_captain', text='Is a captain')
        ptype2 = create_ptype(str_pk='test-prop_strong',  text='Is strong')

        create_rtype = RelationType.objects.smart_update_or_create
        rtype1 = create_rtype(
            ('test-subject_registered', 'registered',     [FakeContact], [ptype1]),
            ('test-object_registered',  'has registered', [FakeOrganisation]),
        )[0]
        rtype2 = create_rtype(
            ('test-subject_leads', 'leads',   [FakeContact], [ptype1, ptype2]),
            ('test-object_leads',  'is lead', [FakeOrganisation]),
        )[0]

        sfrt = SemiFixedRelationType.objects.create(
            predicate='Registered the Bebop',
            relation_type=rtype1,
            object_entity=orga,
        )

        # ---
        form1 = FakeContactForm(user=user)

        with self.assertNoException():
            sf_choices = form1.fields['semifixed_rtypes'].choices

        self.assertInChoices(value=sfrt.id, label=sfrt.predicate, choices=sf_choices)

        # ---
        data = {
            'user': user.id,
            'first_name': 'Spike',
            'last_name': 'Spiegel',
        }

        form2 = FakeContactForm(
            user=user,
            data={
                **data,
                'relation_types': self.formfield_value_multi_relation_entity((rtype1.id, orga)),
            },
        )
        self.assertFormInstanceErrors(
            form2,
            (
                'relation_types',
                _(
                    'The property «%(property)s» is mandatory '
                    'in order to use the relationship «%(predicate)s»'
                ) % {
                    'property': ptype1.text,
                    'predicate': rtype1.predicate,
                },
            ),
        )

        # --
        form3 = FakeContactForm(
            user=user,
            data={**data, 'semifixed_rtypes': [sfrt.id]},
        )
        self.assertFormInstanceErrors(
            form3,
            (
                'semifixed_rtypes',
                _(
                    'The property «%(property)s» is mandatory '
                    'in order to use the relationship «%(predicate)s»'
                ) % {
                    'property': ptype1.text,
                    'predicate': rtype1.predicate,
                }
            ),
        )

        # --
        form4 = FakeContactForm(
            user=user,
            data={
                **data,
                'relation_types': self.formfield_value_multi_relation_entity(
                    (rtype2.id, orga),
                ),
            },
        )
        self.assertFormInstanceErrors(
            form4,
            (
                'relation_types',
                _(
                    'These properties are mandatory in order to use '
                    'the relationship «%(predicate)s»: %(properties)s'
                ) % {
                    'properties': f'{ptype1.text}, {ptype2.text}',
                    'predicate': rtype2.predicate,
                },
            ),
        )

        # --
        form4 = FakeContactForm(
            user=user,
            data={
                **data,
                'property_types': [ptype1.id],
                'relation_types': self.formfield_value_multi_relation_entity(
                    (rtype2.id, orga),
                ),
            },
        )
        self.assertFormInstanceErrors(
            form4,
            (
                'relation_types',
                _(
                    'These properties are mandatory in order to use '
                    'the relationship «%(predicate)s»: %(properties)s'
                ) % {
                    'properties': f'{ptype1.text}, {ptype2.text}',
                    'predicate': rtype2.predicate,
                },
            ),
        )

    @override_settings(FORMS_RELATION_FIELDS=True)
    def test_relations_n_properties(self):
        "The properties needed by the relation types are added."
        user = self.create_user()

        orga = FakeOrganisation.objects.create(user=user, name='Bebop')

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-prop_captain', text='Is a captain')
        ptype2 = create_ptype(str_pk='test-prop_strong',  text='Is strong')

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_leads', 'leads',   [FakeContact], [ptype1, ptype2]),
            ('test-object_leads',  'is lead', [FakeOrganisation]),
        )[0]

        form = FakeContactForm(
            user=user,
            data={
                'user':       user.id,
                'first_name': 'Spike',
                'last_name':  'Spiegel',
                'property_types': [ptype1.id, ptype2.id],
                'relation_types': self.formfield_value_multi_relation_entity(
                    (rtype.id, orga),
                ),
            },
        )
        self.assertFalse(form.errors)

        subject = form.save()
        self.assertRelationCount(1, subject, rtype, orga)

    # TODO: test edition
