# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django import forms
    from django.contrib.contenttypes.models import ContentType
    from django.forms.boundfield import BoundField
    from django.test.utils import override_settings
    from django.utils.translation import gettext as _

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.forms import CremeForm, CremeModelForm
    from creme.creme_core.forms.widgets import Label
    from creme.creme_core.models import (RelationType, Relation, SemiFixedRelationType,
            CremePropertyType, FieldsConfig, SetCredentials,
            CustomField, CustomFieldInteger,
            FakeContact, FakeOrganisation, FakeAddress, FakeSector)

    from ..base import CremeTestCase
    from ..fake_forms import FakeContactForm
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


# TODO: test CremeModelWithUserForm
# TODO: test hooks

class CremeFormTestCase(CremeTestCase):
    def test_01(self):
        user = self.login()

        class TestCremeForm(CremeForm):
            order = forms.IntegerField(label='Order')
            description = forms.CharField(label='Description', required=False)

        form = TestCremeForm(user=user)
        self.assertEqual(user, form.fields['order'].user)

        blocks = form.get_blocks()
        with self.assertNoException():
            general_group = blocks['general']

        self.assertIsInstance(general_group, tuple)
        self.assertEqual(2, len(general_group))
        self.assertEqual(_('General information'), general_group[0])

        items = general_group[1]
        self.assertIsInstance(items, list)
        self.assertEqual(2, len(items))

        # --
        item1 = items[0]
        self.assertIsInstance(item1, tuple)
        self.assertEqual(2, len(item1))
        self.assertIs(item1[1], True)

        bound_field1 = item1[0]
        self.assertIsInstance(bound_field1, BoundField)
        self.assertEqual('order', bound_field1.name)

        # --
        item2 = items[1]
        self.assertEqual('description', item2[0].name)
        self.assertIs(item2[1], False)


class CremeModelFormTestCase(CremeTestCase):
    def test_basic(self):
        user = self.login()

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

        self.assertIsInstance(general_group, tuple)
        self.assertEqual(2, len(general_group))
        self.assertEqual(_('General information'), general_group[0])
        self.assertEqual(2, len(general_group[1]))

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

    def test_fields_config(self):
        user = self.login()

        FieldsConfig.create(
            FakeAddress,
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
        user = self.login()

        form = FakeContactForm(user=user)
        fields = form.fields
        self.assertIn('first_name', fields)
        self.assertIn('last_name', fields)
        self.assertNotIn('is_user', fields)

        # ---
        blocks = form.get_blocks()
        with self.assertNoException():
            general_group = blocks['general']

        self.assertIsInstance(general_group, tuple)
        self.assertEqual(2, len(general_group))
        self.assertEqual(_('General information'), general_group[0])
        self.assertGreater(len(general_group[1]), 10)

        # ---
        first_name = 'Kanbaru'
        last_name = 'Suruga'
        form = FakeContactForm(
            user=user,
            data={
                'user':       user.id,
                'first_name': first_name,
                'last_name':  last_name,
             },
        )
        self.assertFalse(form.errors)

        contact = form.save()
        self.assertIsInstance(contact, FakeContact)
        self.assertEqual(user,       contact.user)
        self.assertEqual(first_name, contact.first_name)
        self.assertEqual(last_name,  contact.last_name)
        self.assertIsNotNone(contact.id)

    def test_customfields(self):
        user = self.login()

        create_cf = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeContact),
        )
        cfield1 = create_cf(name='Size',   field_type=CustomField.INT)
        __      = create_cf(name='Cursed', field_type=CustomField.BOOL)

        fields = FakeContactForm(user=user).fields

        with self.assertNoException():
            cf_f1 = fields['custom_field_0']
            cf_f2 = fields['custom_field_1']

        self.assertIsInstance(cf_f1, forms.IntegerField)
        self.assertIsInstance(cf_f2, forms.NullBooleanField)

        # ---
        first_name = 'Karen'
        last_name = 'Araragi'
        form = FakeContactForm(
            user=user,
            data={
                'user':       user.id,
                'first_name': first_name,
                'last_name':  last_name,

                'custom_field_0': '150',
                'custom_field_1': '',
             },
        )
        self.assertFalse(form.errors)

        contact = form.save()
        self.assertIsInstance(contact, FakeContact)
        self.assertEqual(first_name, contact.first_name)
        self.assertEqual(last_name,  contact.last_name)

        cf_value = self.get_object_or_fail(CustomFieldInteger,
                                           custom_field=cfield1,
                                           entity=contact,
                                          )
        self.assertEqual(150, cf_value.value)

    def test_properties01(self):
        user = self.login()

        create_ptype = CremePropertyType.create
        ptype01 = create_ptype(str_pk='test-prop_spirit',   text='Haunted by a spirit')
        ptype02 = create_ptype(str_pk='test-prop_bakemono', text='Cursed by a bakemono')
        ptype03 = create_ptype(str_pk='test-prop_see',      text='See the yokai',
                               subject_ctypes=[FakeContact],
                              )
        ptype04 = create_ptype(str_pk='test-prop_license', text='Has a license',
                               subject_ctypes=[FakeOrganisation],
                              )

        form = FakeContactForm(user=user)

        with self.assertNoException():
            ptypes_choices = form.fields['property_types'].choices

        # Choices are sorted with 'text'
        choices = list((choice[0].value, choice[1]) for choice in ptypes_choices)
        i1 = self.assertIndex((ptype02.id, ptype02.text), choices)
        i2 = self.assertIndex((ptype01.id, ptype01.text), choices)
        i3 = self.assertIndex((ptype03.id, ptype03.text), choices)
        self.assertLess(i1, i2)
        self.assertLess(i2, i3)

        self.assertNotIn((ptype04.id, ptype04.text), choices)

        # ---
        blocks = form.get_blocks()

        with self.assertNoException():
            prop_group = blocks['properties']

        self.assertEqual(_('Properties'), prop_group[0])

        items = prop_group[1]
        self.assertEqual(len(items), 1)
        self.assertEqual('property_types', items[0][0].name)

        # ---
        form = FakeContactForm(
            user=user,
            data={
                'user':       user.id,
                'first_name': 'Kanbaru',
                'last_name':  'Suruga',

                'property_types': [ptype01.id, ptype03.id],
            },
        )
        self.assertFalse(form.errors)

        contact = form.save()
        self.assertSetEqual({ptype01, ptype03},
                            {p.type for p in contact.properties.all()}
                           )

    def test_properties02(self):
        "Forced CremePropertyTypes (IDs)."
        user = self.login()

        create_ptype = CremePropertyType.create
        ptype01 = create_ptype(str_pk='test-prop_spirit',   text='Haunted by a spirit')
        ptype02 = create_ptype(str_pk='test-prop_bakemono', text='Cursed by a bakemono')
        ptype03 = create_ptype(str_pk='test-prop_see',      text='See the yokai',
                               subject_ctypes=[FakeContact],
                              )

        form = FakeContactForm(user=user, forced_ptypes=[ptype02.id])

        with self.assertNoException():
            ptypes_choices = form.fields['property_types'].choices

        choices = [(choice_obj.value, choice_obj.readonly)
                        for choice_obj, _label in ptypes_choices
                  ]
        self.assertIndex((ptype01.id, False), choices)
        self.assertIndex((ptype02.id, True),  choices)
        self.assertIndex((ptype03.id, False), choices)

    def test_properties03(self):
        "Forced CremePropertyTypes (instances)."
        user = self.login()

        create_ptype = CremePropertyType.create
        ptype01 = create_ptype(str_pk='test-prop_spirit',   text='Haunted by a spirit')
        ptype02 = create_ptype(str_pk='test-prop_bakemono', text='Cursed by a bakemono')
        ptype03 = create_ptype(str_pk='test-prop_see',      text='See the yokai',
                               subject_ctypes=[FakeContact],
                              )

        form = FakeContactForm(user=user, forced_ptypes=[ptype02])

        with self.assertNoException():
            ptypes_choices = form.fields['property_types'].choices

        choices = [(choice_obj.value, choice_obj.readonly)
                        for choice_obj, _label in ptypes_choices
                  ]
        self.assertIndex((ptype01.id, False), choices)
        self.assertIndex((ptype02.id, True),  choices)
        self.assertIndex((ptype03.id, False), choices)

    @override_settings(FORMS_RELATION_FIELDS=False)
    def test_properties04(self):
        "Forced CremePropertyTypes + no <properties> field."
        user = self.login()

        ptype = CremePropertyType.create(str_pk='test-prop_spirit',   text='Haunted by a spirit')

        form = FakeContactForm(user=user, forced_ptypes=[ptype.id],
                               data={
                                   'user': user.id,
                                   'first_name': 'Kanbaru',
                                   'last_name': 'Suruga',
                               },
                              )
        self.assertFalse(form.errors)

        contact = form.save()
        self.assertListEqual([ptype],
                             [p.type for p in contact.properties.all()]
                            )

    def test_relations01(self):
        user = self.login()

        contact = FakeContact.objects.create(user=user,
                                             first_name='Hitagi',
                                             last_name='Senjyogahara',
                                            )
        orga = FakeOrganisation.objects.create(user=user, name='Oshino corp.')

        create_rtype = RelationType.create
        rtype1 = create_rtype(('test-subject_loves', 'loves'),
                              ('test-object_loves',  'is loved'),
                             )[0]
        rtype2 = create_rtype(('test-subject_heals', 'has healed', [FakeOrganisation]),
                              ('test-object_heals',  'healed by',  [FakeContact]),
                             )[1]

        form = FakeContactForm(user=user)
        fields = form.fields
        self.assertIn('relation_types', fields)
        self.assertNotIn('semifixed_rtypes', fields)
        self.assertNotIn('rtypes_info',      fields)

        # ---
        blocks = form.get_blocks()

        with self.assertNoException():
            relation_group = blocks['relationships']

        self.assertEqual(_('Relationships'), relation_group[0])

        items = relation_group[1]
        self.assertEqual(len(items), 1)
        self.assertEqual('relation_types', items[0][0].name)

        # ---
        form = FakeContactForm(
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
        self.assertFalse(form.errors)

        subject = form.save()
        self.assertEqual(2, subject.relations.count())
        self.assertRelationCount(1, subject, rtype1, contact)
        self.assertRelationCount(1, subject, rtype2, orga)

    def test_relations02(self):
        "Semi-fixed."
        user = self.login()

        contact = FakeContact.objects.create(user=user,
                                             first_name='Hitagi',
                                             last_name='Senjyogahara',
                                            )
        orga = FakeOrganisation.objects.create(user=user, name='Oshino corp.')

        create_rtype = RelationType.create
        rtype1 = create_rtype(('test-subject_loves', 'loves'),
                              ('test-object_loves',  'is loved'),
                             )[0]
        rtype2 = create_rtype(('test-subject_heals', 'has healed', [FakeOrganisation]),
                              ('test-object_heals',  'healed by',  [FakeContact]),
                             )[1]

        create_strt = SemiFixedRelationType.objects.create
        sfrt1 = create_strt(predicate='Healed by Oshino',
                            relation_type=rtype2,
                            object_entity=orga,
                           )
        sfrt2 = create_strt(predicate='Loves Hitagi',
                            relation_type=rtype1,
                            object_entity=contact,
                           )

        form = FakeContactForm(user=user)
        fields = form.fields
        self.assertIn('relation_types', fields)
        self.assertNotIn('rtypes_info', fields)

        with self.assertNoException():
            sf_choices = fields['semifixed_rtypes'].choices

        self.assertIn((sfrt1.id, sfrt1.predicate), sf_choices)
        self.assertIn((sfrt2.id, sfrt2.predicate), sf_choices)

        # ---
        blocks = form.get_blocks()

        with self.assertNoException():
            relation_group = blocks['relationships']

        self.assertEqual(2, len(relation_group))
        self.assertEqual(_('Relationships'), relation_group[0])

        items = relation_group[1]
        self.assertEqual(len(items), 2)
        self.assertEqual('relation_types',   items[0][0].name)
        self.assertEqual('semifixed_rtypes', items[1][0].name)

        # ---
        form = FakeContactForm(
            user=user,
            data={
                'user':       user.id,
                'first_name': 'Kanbaru',
                'last_name':  'Suruga',

                'semifixed_rtypes': [sfrt1.id, sfrt2.id],
             },
        )
        self.assertFalse(form.errors)

        subject = form.save()
        self.assertEqual(2, subject.relations.count())
        self.assertRelationCount(1, subject, rtype1, contact)
        self.assertRelationCount(1, subject, rtype2, orga)

    def test_relations03(self):
        "Fixed & semi-fixed."
        user = self.login()

        contact = FakeContact.objects.create(user=user,
                                             first_name='Hitagi',
                                             last_name='Senjyogahara',
                                            )
        orga = FakeOrganisation.objects.create(user=user, name='Oshino corp.')

        create_rtype = RelationType.create
        rtype1 = create_rtype(('test-subject_loves', 'loves'),
                              ('test-object_loves',  'is loved'),
                             )[0]
        rtype2 = create_rtype(('test-subject_heals', 'has healed', [FakeOrganisation]),
                              ('test-object_heals',  'healed by',  [FakeContact]),
                             )[1]

        create_strt = SemiFixedRelationType.objects.create
        sfrt1 = create_strt(predicate='Healed by Oshino',
                            relation_type=rtype2,
                            object_entity=orga,
                           )
        sfrt2 = create_strt(predicate='Loves Hitagi',
                            relation_type=rtype1,
                            object_entity=contact,
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
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Hitagi', last_name='Senjyogahara')
        contact2 = create_contact(first_name='Koyomi', last_name='Araragi')

        orga = FakeOrganisation.objects.create(user=user, name='Oshino corp.')

        create_rtype = RelationType.create
        rtype1 = create_rtype(('test-subject_loves', 'loves'),
                              ('test-object_loves',  'is loved'),
                             )[0]
        rtype2 = create_rtype(('test-subject_heals', 'has healed', [FakeOrganisation]),
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
        forced_relations = [Relation(type=rtype2, object_entity=orga),
                            Relation(type=rtype1, object_entity=contact1),
                           ]
        fields2 = FakeContactForm(user=user, forced_relations=forced_relations).fields

        self.assertIn('relation_types', fields2)
        self.assertHTMLEqual(
            _('These relationships will be added: {}').format(
                '<ul><li>{} «{}»</li><li>{} «{}»</li></ul>'.format(
                    rtype2.predicate, orga,
                    rtype1.predicate, contact1,
                )
            ),
            fields2['rtypes_info'].initial
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
        user = self.login()

        orga = FakeOrganisation.objects.create(user=user, name='Oshino corp.')
        rtype = RelationType.create(('test-subject_heals', 'has healed'),
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
        user = self.login()

        fields = FakeContactForm(user=user).fields
        self.assertNotIn('property_types',   fields)
        self.assertNotIn('relation_types',   fields)
        self.assertNotIn('semifixed_rtypes', fields)
        self.assertNotIn('rtypes_info',      fields)

    def test_no_relations_fields02(self):
        "Edition => no relations/properties field."
        user = self.login()

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
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        create_contact = FakeContact.objects.create
        contact1 = create_contact(user=user, first_name='Kanbaru', last_name='Suruga')
        self.assertTrue(user.has_perm_to_link(contact1))

        contact2 = create_contact(user=self.other_user,
                                  first_name='Hitagi', last_name='Senjyogahara',
                                 )
        self.assertFalse(user.has_perm_to_link(contact2))

        rtype = RelationType.create(('test-subject_loves', 'loves'),
                                    ('test-object_loves',  'is loved'),
                                   )[0]

        create_strt = SemiFixedRelationType.objects.create
        sfrt1 = create_strt(predicate='Loves Kanbaru',
                            relation_type=rtype,
                            object_entity=contact1,
                           )
        sfrt2 = create_strt(predicate='Loves Hitagi',
                            relation_type=rtype,
                            object_entity=contact2,
                           )

        form = FakeContactForm(user=user)
        fields = form.fields

        with self.assertNoException():
            sf_choices = fields['semifixed_rtypes'].choices

        self.assertIn((sfrt1.id, sfrt1.predicate), sf_choices)
        self.assertNotIn((sfrt2.id, sfrt2.predicate), sf_choices)

    def test_relations_credentials02(self):
        "Label if cannot link the future entity."
        user = self.login(is_superuser=False, creatable_models=[FakeContact])

        create_creds = partial(SetCredentials.objects.create, role=self.role)
        create_creds(value=EntityCredentials.VIEW   |
                           EntityCredentials.CHANGE |
                           EntityCredentials.LINK,
                     set_type=SetCredentials.ESET_OWN,
                    )
        create_creds(value=EntityCredentials.LINK,
                     set_type=SetCredentials.ESET_ALL,
                     ctype=FakeContact, forbidden=True,
                    )

        orga = FakeOrganisation.objects.create(user=user, name='Oshino corp.')

        rtype = RelationType.create(('test-subject_heals', 'heals'),
                                    ('test-object_heals',  'is healed by'),
                                   )[1]

        sfrt = SemiFixedRelationType.objects.create(predicate='Healed by Oshino',
                                                    relation_type=rtype,
                                                    object_entity=orga,
                                                   )

        fields = FakeContactForm(user=user).fields

        with self.assertNoException():
            info_field = fields['rtypes_info']

        self.assertNotIn('relation_types', fields)
        self.assertNotIn('semifixed_rtypes', fields)
        self.assertIsInstance(info_field.widget, Label)
        self.assertEqual(
            _('You are not allowed to link this kind of entity.'),
            info_field.initial
        )

        # ---
        form = FakeContactForm(
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
        self.assertFalse(form.errors)

        subject = form.save()
        self.assertFalse(subject.relations.count())

    def test_relations_credentials03(self):
        "Link credentials on the created entity."
        user = self.login(is_superuser=False, creatable_models=[FakeContact])

        create_creds = partial(SetCredentials.objects.create, role=self.role)
        create_creds(value=EntityCredentials.VIEW | EntityCredentials.LINK,
                     set_type=SetCredentials.ESET_OWN,
                    )
        create_creds(value=EntityCredentials.VIEW,
                     set_type=SetCredentials.ESET_ALL,
                    )

        orga = FakeOrganisation.objects.create(user=user, name='Oshino corp.')

        rtype = RelationType.create(('test-subject_heals', 'heals'),
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
            ('relation_types', _('You are not allowed to link the created entity (wrong owner?).')),
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
        create_creds(value=EntityCredentials.VIEW| EntityCredentials.LINK,
                     set_type=SetCredentials.ESET_OWN,
                    )
        create_creds(value=EntityCredentials.VIEW,
                     set_type=SetCredentials.ESET_ALL,
                    )

        orga = FakeOrganisation.objects.create(user=user, name='Oshino corp.')

        rtype = RelationType.create(('test-subject_heals', 'heals'),
                                    ('test-object_heals',  'is healed by'),
                                   )[1]
        sfrt = SemiFixedRelationType.objects.create(predicate='Healed by Oshino',
                                                    relation_type=rtype,
                                                    object_entity=orga,
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
            ('semifixed_rtypes', _('You are not allowed to link the created entity (wrong owner?).')),
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
        create_creds(value=EntityCredentials.VIEW| EntityCredentials.LINK,
                     set_type=SetCredentials.ESET_OWN,
                    )
        create_creds(value=EntityCredentials.VIEW,
                     set_type=SetCredentials.ESET_ALL,
                    )

        form = FakeContactForm(
            user=user,
            data={
                'user':       self.other_user.id,
                'first_name': 'Kanbaru',
                'last_name':  'Suruga',
             },
        )
        self.assertFalse(form.errors)

    def test_relations_error01(self):
        "ContentType constraint error."
        user = self.login()

        orga = FakeOrganisation.objects.create(user=user, name='Oshino corp.')
        rtype = RelationType.create(
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
            ('relation_types', _('This type of relationship causes a constraint error.')),
        )

    @override_settings(FORMS_RELATION_FIELDS=True)
    def test_relations_error02(self):
        "Property constraint errors."
        user = self.login()

        orga = FakeOrganisation.objects.create(user=user, name='Bebop')

        create_ptype = CremePropertyType.create
        ptype1 = create_ptype(str_pk='test-prop_captain', text='Is a captain')
        ptype2 = create_ptype(str_pk='test-prop_strong',  text='Is strong')

        create_rtype = RelationType.create
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

        self.assertIn((sfrt.id, sfrt.predicate), sf_choices)

        # ---
        data = {'user': user.id,
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
            ('relation_types',
             _('The property «%(property)s» is mandatory '
               'in order to use the relationship «%(predicate)s»'
              ) % {'property': ptype1.text,
                   'predicate': rtype1.predicate,
            }),
        )

        # --
        form3 = FakeContactForm(
            user=user,
            data={**data, 'semifixed_rtypes': [sfrt.id]},
        )
        self.assertFormInstanceErrors(
            form3,
            ('semifixed_rtypes',
             _('The property «%(property)s» is mandatory '
               'in order to use the relationship «%(predicate)s»'
              ) % {'property': ptype1.text,
                   'predicate': rtype1.predicate,
            }),
        )

        # --
        form4 = FakeContactForm(
            user=user,
            data={
                **data,
                'relation_types': self.formfield_value_multi_relation_entity((rtype2.id, orga)),
            },
        )
        self.assertFormInstanceErrors(
            form4,
            ('relation_types',
             _('These properties are mandatory in order to use '
               'the relationship «%(predicate)s»: %(properties)s'
              ) % {'properties': '{}, {}'.format(ptype1.text, ptype2.text),
                   'predicate': rtype2.predicate,
            }),
        )

        # --
        form4 = FakeContactForm(
            user=user,
            data={
                **data,
                'property_types': [ptype1.id],
                'relation_types': self.formfield_value_multi_relation_entity((rtype2.id, orga)),
            },
        )
        self.assertFormInstanceErrors(
            form4,
            ('relation_types',
             _('These properties are mandatory in order to use '
               'the relationship «%(predicate)s»: %(properties)s'
              ) % {'properties': '{}, {}'.format(ptype1.text, ptype2.text),
                   'predicate': rtype2.predicate,
            }),
        )

    @override_settings(FORMS_RELATION_FIELDS=True)
    def test_relations_n_properties(self):
        "The properties needed by the relation types are added."
        user = self.login()

        orga = FakeOrganisation.objects.create(user=user, name='Bebop')

        create_ptype = CremePropertyType.create
        ptype1 = create_ptype(str_pk='test-prop_captain', text='Is a captain')
        ptype2 = create_ptype(str_pk='test-prop_strong',  text='Is strong')

        rtype = RelationType.create(
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
