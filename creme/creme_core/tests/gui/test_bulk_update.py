# -*- coding: utf-8 -*-

try:
    from datetime import datetime
    from functools import partial
    from itertools import chain

    from django.contrib.contenttypes.models import ContentType
    from django.db.models.query_utils import Q
    from django.forms.models import ModelMultipleChoiceField
    from django.utils.translation import ugettext as _

    from ..base import CremeTestCase # skipIfNotInstalled
    from ..fake_models import (FakeContact as Contact,
            FakeOrganisation as Organisation, FakeAddress as Address,
            FakeCivility as Civility,
            FakeImageCategory as ImageCategory,
            FakeImage as Image, FakeActivity,
            FakeEmailCampaign as EmailCampaign)

    from creme.creme_config.forms.fields import CreatorModelChoiceField

    from creme.creme_core.forms.fields import CreatorEntityField, MultiCreatorEntityField
    from creme.creme_core.forms.bulk import BulkDefaultEditForm
    from creme.creme_core.gui.bulk_update import _BulkUpdateRegistry, FieldNotAllowed
    from creme.creme_core.models.custom_field import CustomField
    from creme.creme_core.utils.unicode_collation import collator
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


# TODO: test register(..., expandables=[..])
class BulkUpdateRegistryTestCase(CremeTestCase):
    def setUp(self):
        self.bulk_update_registry = _BulkUpdateRegistry()
        self.maxDiff = None

    def tearDown(self):
        self.remove_field_attr(Contact, 'image', 'limit_choices_to')
        self.remove_field_attr(Contact, 'civility', 'limit_choices_to')
        self.remove_field_attr(Image, 'categories', 'limit_choices_to')
        self.remove_field_attr(EmailCampaign, 'mailing_lists', 'limit_choices_to')

    def remove_field_attr(self, model, fieldname, attr):
        field = model._meta.get_field(fieldname)

        if hasattr(field, attr):
            delattr(field, attr)

    def sortFields(self, fields):
        sort_key = collator.sort_key
        return sorted(fields, key=lambda f: sort_key(f.verbose_name))

    def test_bulk_update_registry01(self):
        is_bulk_updatable = partial(self.bulk_update_registry.is_updatable, model=Organisation)

        self.bulk_update_registry.register(Organisation, exclude=['emails'])

        # TODO uncomment when bulk registry will manage empty_or_unique fields
        self.assertTrue(is_bulk_updatable(field_name='name'))
        self.assertTrue(is_bulk_updatable(field_name='phone'))

        self.assertFalse(is_bulk_updatable(field_name='created'))  # Editable = False
        self.assertFalse(is_bulk_updatable(field_name='address'))  # Editable = False
        self.assertFalse(is_bulk_updatable(field_name='emails'))  # Excluded field

    def test_bulk_update_registry02(self):
        is_bulk_updatable = partial(self.bulk_update_registry.is_updatable, model=Contact)

        self.assertTrue(is_bulk_updatable(field_name='first_name'))
        self.assertTrue(is_bulk_updatable(field_name='last_name'))

        # Automatically inherited from CremeEntity excluded fields (editable = false)
        self.assertFalse(is_bulk_updatable(field_name='modified'))
        self.assertFalse(is_bulk_updatable(field_name='address'))
        self.assertFalse(is_bulk_updatable(field_name='is_deleted'))

    def test_is_updatable_many2many(self):
        bulk_update_registry = self.bulk_update_registry

        is_bulk_updatable = partial(bulk_update_registry.is_updatable, model=Image)

        bulk_update_registry.register(Image)
        self.assertTrue(is_bulk_updatable(model=Image, field_name='categories'))

        status = bulk_update_registry.status(Image)
        self.assertFalse(status.is_expandable(status.get_field('categories')))

    def test_is_updatable_foreignkey(self):
        bulk_update_registry = self.bulk_update_registry
        is_bulk_updatable = bulk_update_registry.is_updatable

        bulk_update_registry.register(Contact)
        self.assertFalse(is_bulk_updatable(model=Contact, field_name='billing_address'))
        self.assertFalse(is_bulk_updatable(model=Contact, field_name='shipping_address'))

    def test_is_updatable_enumerable(self):
        bulk_update_registry = self.bulk_update_registry
        is_bulk_updatable = bulk_update_registry.is_updatable

        bulk_update_registry.register(Contact)
        self.assertTrue(is_bulk_updatable(model=Contact, field_name='civility'))

        status = bulk_update_registry.status(Contact)
        self.assertFalse(status.is_expandable(status.get_field('civility')))

    def test_is_updatable_not_editable(self):
        bulk_update_registry = self.bulk_update_registry
        is_bulk_updatable = bulk_update_registry.is_updatable

        bulk_update_registry.register(Contact)
        self.assertFalse(is_bulk_updatable(model=Contact, field_name='billing_address'))
        self.assertFalse(is_bulk_updatable(model=Contact, field_name='shipping_address'))

    def test_is_expandable(self):
        bulk_update_registry = self.bulk_update_registry
        is_bulk_expandable = bulk_update_registry.is_expandable

        bulk_update_registry.register(Contact)
        self.assertTrue(is_bulk_expandable(model=Contact, field_name='address'))

        # Enumerable not expandable
        self.assertFalse(is_bulk_expandable(model=Contact, field_name='civility'))

        # Related model is not a CremeModel
        self.assertFalse(is_bulk_expandable(model=Contact, field_name='is_user'))

    def test_is_expandable_excluded(self):
        bulk_update_registry = self.bulk_update_registry

        bulk_update_registry.register(Contact, exclude=['address'])
        self.assertFalse(bulk_update_registry.is_expandable(model=Contact, field_name='address'))

    def test_is_updatable_ignore(self):
        bulk_update_registry = self.bulk_update_registry
        is_bulk_updatable = partial(bulk_update_registry.is_updatable, model=Organisation)

        bulk_update_registry.ignore(Organisation)

        self.assertFalse(is_bulk_updatable(field_name='name'))
        self.assertFalse(is_bulk_updatable(field_name='phone'))

    def test_regular_fields(self):
        bulk_update_registry = self.bulk_update_registry

        expected = [field for field in chain(Contact._meta.fields, Contact._meta.many_to_many)
                        if field.editable and not field.unique
                   ]
        self.assertListEqual(self.sortFields(expected),
                             bulk_update_registry.regular_fields(Contact))

    def test_regular_fields_ignore(self):
        bulk_update_registry = self.bulk_update_registry

        bulk_update_registry.ignore(Contact)
        self.assertListEqual(bulk_update_registry.regular_fields(Contact), [])

    def test_regular_fields_include_unique(self):
        bulk_update_registry = self.bulk_update_registry

        expected = [field for field in chain(Contact._meta.fields, Contact._meta.many_to_many)
                        if field.editable
                   ]
        self.assertListEqual(self.sortFields(expected),
                             bulk_update_registry.regular_fields(Contact, exclude_unique=False))

    def test_get_regular_field_not_editable(self):
        bulk_update_registry = self.bulk_update_registry
        bulk_update_registry.register(Contact)

        with self.assertRaises(FieldNotAllowed):
            bulk_update_registry.status(Contact).get_field('address')

        with self.assertRaises(FieldNotAllowed):
            bulk_update_registry.get_field(Contact, 'address')

    def test_get_regular_subfield_expandable(self):
        bulk_update_registry = self.bulk_update_registry
        bulk_update_registry.register(Contact)

        with self.assertRaises(FieldNotAllowed):
            bulk_update_registry.get_field(Contact, 'address')

        self.assertIsNotNone(bulk_update_registry.status(Contact)
                                                 .get_expandable_field('address')
                            )
        self.assertIsNotNone(bulk_update_registry.get_field(Contact, 'address__zipcode'))

    def test_regular_fields_expanded(self):
        bulk_update_registry = self.bulk_update_registry
        bulk_update_registry.register(Contact)

        expected_names = [field.name for field in chain(Contact._meta.fields, Contact._meta.many_to_many)
                              if field.editable and not field.unique
                         ]
        expanded_names = ['address']

        fields = bulk_update_registry.regular_fields(Contact, expand=True)

        self.assertListEqual(sorted(expected_names + expanded_names), sorted([field[0].name for field in fields]))
        self.assertListEqual(sorted(expanded_names), sorted([field.name for field, sub in fields if sub is not None]))

        fields_dict = {field[0].name: field for field in fields}

        sub_expected_names = [field.name for field in chain(Address._meta.fields, Address._meta.many_to_many)
                                  if field.editable and not field.unique
                             ]

        address_fields = fields_dict['address'][1]
        self.assertListEqual(sorted(sub_expected_names),
                             sorted([field.name for field in address_fields])
                            )

    def test_regular_subfield(self):
        bulk_update_registry = self.bulk_update_registry
        bulk_update_registry.register(Contact)

        zipcode_field = Address._meta.get_field('zipcode')
        self.assertEqual(zipcode_field, bulk_update_registry.get_field(Contact, 'address__zipcode'))
        self.assertEqual(zipcode_field, bulk_update_registry.get_field(Address, 'zipcode'))

    def test_default_field(self):
        bulk_update_registry = self.bulk_update_registry
        bulk_update_registry.register(Contact)

        expected = self.sortFields([field for field in chain(Contact._meta.fields, Contact._meta.many_to_many)
                                        if field.editable and not field.unique
                                   ]
                                  )[0]

        self.assertEqual(expected.name, bulk_update_registry.get_default_field(Contact).name)

    def test_custom_fields(self):
        bulk_update_registry = self.bulk_update_registry
        bulk_update_registry.register(Contact)

        contact_ct = ContentType.objects.get_for_model(Contact)

        CustomField.objects.create(name='A', content_type=contact_ct, field_type=CustomField.STR)

        regular_names = [field.name for field in chain(Contact._meta.fields, Contact._meta.many_to_many)
                             if field.editable and not field.unique
                        ]
        custom_names  = ['A']

        regular_fields = bulk_update_registry.regular_fields(Contact)
        custom_fields  = bulk_update_registry.custom_fields(Contact)

        self.assertListEqual(sorted(regular_names), sorted([field.name for field in regular_fields]))
        self.assertListEqual(sorted(custom_names), [field.name for field in custom_fields])

        CustomField.objects.create(name='C', content_type=contact_ct, field_type=CustomField.BOOL)
        CustomField.objects.create(name='0', content_type=contact_ct, field_type=CustomField.INT)

        custom_names  = ['0', 'A', 'C']

        regular_fields = bulk_update_registry.regular_fields(Contact)
        custom_fields  = bulk_update_registry.custom_fields(Contact)

        self.assertListEqual(sorted(regular_names), sorted([field.name for field in regular_fields]))
        self.assertListEqual(sorted(custom_names), [field.name for field in custom_fields])

    def test_custom_fields_ignore(self):
        bulk_update_registry = self.bulk_update_registry

        bulk_update_registry.ignore(Organisation)
        self.assertListEqual(bulk_update_registry.custom_fields(Organisation), [])

    def test_innerforms(self):
        bulk_update_registry = self.bulk_update_registry
        is_bulk_updatable = partial(bulk_update_registry.is_updatable, model=Contact)

        class _ContactInnerBirthday(BulkDefaultEditForm):
            pass

        bulk_update_registry.register(Contact, exclude=['position'],
                                      innerforms={'birthday': _ContactInnerBirthday},
                                     )

        self.assertFalse(is_bulk_updatable(field_name='position'))
        self.assertIsNone(bulk_update_registry.status(Contact).get_form('position'))

        self.assertTrue(is_bulk_updatable(field_name='birthday'))
        self.assertEqual(_ContactInnerBirthday,
                          bulk_update_registry.status(Contact).get_form('birthday')
                         )

# NB: these 2 tests make some other test cases crash.
#  eg: Problem with entity deletion: (1146, "Table 'test_creme_1_6.creme_core_subcontact' doesn't exist")
# We comment them because entity inheritance is not recommended anyway
# TODO: uncomment them with a true SubContact model ??
#    def test_innerforms_inherit01(self):
#        "Inheritance : registering parent first"
#        bulk_update_registry = self.bulk_update_registry
#        is_bulk_updatable = bulk_update_registry.is_updatable
#        status = bulk_update_registry.status
#
#        class SubContact(Contact):
#            pass
#
#        class _ContactInnerEditForm(BulkDefaultEditForm):
#            pass
#
#        class _SubContactInnerEdit(BulkDefaultEditForm):
#            pass
#
#        bulk_update_registry.register(Contact, exclude=['position'],
#                                      innerforms={'first_name': _ContactInnerEditForm,
#                                                  'last_name':  _ContactInnerEditForm,
#                                                 }
#                                     )
#        bulk_update_registry.register(SubContact, exclude=['position'],
#                                      innerforms={'birthday':  _SubContactInnerEdit,
#                                                  'last_name': _SubContactInnerEdit,
#                                                 }
#                                     )
#
#        self.assertFalse(is_bulk_updatable(model=Contact,    field_name='position'))
#        self.assertFalse(is_bulk_updatable(model=SubContact, field_name='position'))
#        self.assertIsNone(status(Contact).get_form('position'))
#        self.assertIsNone(status(SubContact).get_form('position'))
#
#        # subclass inherits inner forms from base class
#        self.assertTrue(is_bulk_updatable(model=Contact,    field_name='first_name'))
#        self.assertTrue(is_bulk_updatable(model=SubContact, field_name='first_name'))
#        self.assertEqual(_ContactInnerEditForm, status(Contact).get_form('first_name'))
#        self.assertEqual(_ContactInnerEditForm, status(SubContact).get_form('first_name'))
#
#        # base class ignore changes of inner form made for subclass
#        self.assertTrue(is_bulk_updatable(model=Contact, field_name='birthday'))
#        self.assertTrue(is_bulk_updatable(model=SubContact, field_name='birthday'))
#        self.assertIsNone(status(Contact).get_form('birthday'))
#        self.assertEqual(_SubContactInnerEdit, status(SubContact).get_form('birthday'))
#
#        # subclass force bulk form for field
#        self.assertTrue(is_bulk_updatable(model=Contact, field_name='last_name'))
#        self.assertTrue(is_bulk_updatable(model=SubContact, field_name='last_name'))
#        self.assertEqual(_ContactInnerEditForm, status(Contact).get_form('last_name'))
#        self.assertEqual(_SubContactInnerEdit, status(SubContact).get_form('last_name'))
#
#    def test_innerforms_inherit02(self):
#        "Inheritance : registering child first"
#        bulk_update_registry = self.bulk_update_registry
#        is_bulk_updatable = bulk_update_registry.is_updatable
#
#       class SubContact(Contact):
#            pass
#
#        class _ContactInnerEditForm(BulkDefaultEditForm):
#            pass
#
#        class _SubContactInnerEdit(BulkDefaultEditForm):
#            pass
#
#        bulk_update_registry.register(SubContact,
#                                      innerforms={'first_name': _SubContactInnerEdit,
#                                                  'last_name':  _SubContactInnerEdit,
#                                                 }
#                                     )
#        bulk_update_registry.register(Contact, exclude=['position'],
#                                      innerforms={'birthday':  _ContactInnerEditForm,
#                                                  'last_name': _ContactInnerEditForm,
#                                                 }
#                                     )
#
#        self.assertFalse(is_bulk_updatable(model=Contact,    field_name='position'))
#        self.assertFalse(is_bulk_updatable(model=SubContact, field_name='position'))
#
#        status = bulk_update_registry.status
#        self.assertTrue(is_bulk_updatable(model=SubContact, field_name='birthday'))
#        self.assertEqual(_ContactInnerEditForm, status(Contact).get_form('birthday'))
#        self.assertEqual(_ContactInnerEditForm, status(SubContact).get_form('birthday'))
#
#        self.assertIsNone(bulk_update_registry.status(Contact).get_form('first_name'))
#        self.assertEqual(_SubContactInnerEdit, status(SubContact).get_form('first_name'))
#
#        self.assertEqual(_ContactInnerEditForm, status(Contact).get_form('last_name'))
#        self.assertEqual(_SubContactInnerEdit,  status(SubContact).get_form('last_name'))

    def test_subfield_innerforms(self):
        user = self.login()

        bulk_update_registry = self.bulk_update_registry
        bulk_update_registry.register(Contact)

        class _ZipcodeInnerEdit(BulkDefaultEditForm):
            pass

        contact = Contact.objects.create(last_name='contact', user=user)

        form = bulk_update_registry.get_form(Contact, 'address__zipcode', BulkDefaultEditForm) \
                                             (user=user, entities=[contact])

        self.assertIsInstance(form, BulkDefaultEditForm)

        bulk_update_registry.register(Address, innerforms={'zipcode': _ZipcodeInnerEdit})

        form = bulk_update_registry.get_form(Contact, 'address__zipcode', BulkDefaultEditForm) \
                                            (user=user, entities=[contact])
        self.assertIsInstance(form, _ZipcodeInnerEdit)

    def test_expandable_innerforms(self):
        user = self.login()

        contact = Contact.objects.create(last_name='contact', user=user)

        bulk_update_registry = self.bulk_update_registry
        bulk_update_registry.register(Contact)

        with self.assertRaises(FieldNotAllowed):
            bulk_update_registry.get_form(Contact, 'address', BulkDefaultEditForm)

        form = bulk_update_registry.get_form(Contact, 'address__zipcode', BulkDefaultEditForm)\
                                            (user=user, entities=[contact])
        self.assertIsInstance(form, BulkDefaultEditForm)

    def test_fk_innerform(self):
        user = self.login()

        bulk_update_registry = self.bulk_update_registry
        bulk_update_registry.register(Contact)

        civility_field = Contact._meta.get_field('civility')
        self.assertFalse(hasattr(civility_field, 'limit_choices_to'))

        contact = Contact.objects.create(first_name='A', last_name='B', user=user)

        form = BulkDefaultEditForm(civility_field, user, [contact])
        self.assertIsInstance(form.fields['field_value'], CreatorModelChoiceField)
        self.assertQuerysetSQLEqual(Civility.objects.all(), form.fields['field_value'].queryset)

        civility_field.limit_choices_to = {'title': _('Mister')}

        form = BulkDefaultEditForm(civility_field, user, [contact])
        self.assertIsInstance(form.fields['field_value'], CreatorModelChoiceField)
        self.assertQuerysetSQLEqual(Civility.objects.filter(title=_('Mister')),
                                    form.fields['field_value'].queryset
                                   )

        civility_field.limit_choices_to = ~Q(**{'title': _('Mister')})

        form = BulkDefaultEditForm(civility_field, user, [contact])
        self.assertIsInstance(form.fields['field_value'], CreatorModelChoiceField)
        self.assertQuerysetSQLEqual(Civility.objects.exclude(title=_('Mister')),
                                    form.fields['field_value'].queryset
                                   )

        civility_field.limit_choices_to = lambda: {'title': _('Miss')}

        form = BulkDefaultEditForm(civility_field, user, [contact])
        self.assertIsInstance(form.fields['field_value'], CreatorModelChoiceField)
        self.assertQuerysetSQLEqual(Civility.objects.filter(title=_('Miss')),
                                    form.fields['field_value'].queryset
                                   )

    def test_fk_entity_innerform(self):
        user = self.login()

        bulk_update_registry = self.bulk_update_registry
        bulk_update_registry.register(Contact)

        image_field = Contact._meta.get_field('image')
        self.assertFalse(hasattr(image_field, 'limit_choices_to'))

        contact = Contact.objects.create(first_name='A', last_name='B', user=user)

        form = BulkDefaultEditForm(image_field, user, [contact])
        self.assertIsInstance(form.fields['field_value'], CreatorEntityField)
        self.assertIsNone(form.fields['field_value'].q_filter)

        image_field.limit_choices_to = {'name': 'A'}

        form = BulkDefaultEditForm(image_field, user, [contact])
        self.assertIsInstance(form.fields['field_value'], CreatorEntityField)
        self.assertDictEqual({'name': 'A'}, form.fields['field_value'].q_filter)

        image_field.limit_choices_to = ~Q(**{'name': 'B'})

        with self.assertRaises(ValueError) as err:
            BulkDefaultEditForm(image_field, user, [contact])

        self.assertEqual(str(err.exception),
                         'Q filter is not (yet) supported for bulk edition of a field related to a CremeEntity.'
                        )

        today = datetime.today()
        image_field.limit_choices_to = lambda: {'created__lte': today}

        form = BulkDefaultEditForm(image_field, user, [contact])
        self.assertIsInstance(form.fields['field_value'], CreatorEntityField)
        self.assertDictEqual({'created__lte': today}, form.fields['field_value'].q_filter)

    def test_manytomany_innerform(self):
        user = self.login()

        bulk_update_registry = self.bulk_update_registry
        bulk_update_registry.register(Image)

        categories_field = Image._meta.get_field('categories')
        self.assertFalse(hasattr(categories_field, 'limit_choices_to'))

        image = Image.objects.create(name='A', user=user)

        form = BulkDefaultEditForm(categories_field, user, [image])
        self.assertIsInstance(form.fields['field_value'], ModelMultipleChoiceField)
        self.assertQuerysetSQLEqual(ImageCategory.objects.all(),
                                    form.fields['field_value'].queryset
                                   )

        categories_field.limit_choices_to = {'name': 'A'}

        form = BulkDefaultEditForm(categories_field, user, [image])
        self.assertIsInstance(form.fields['field_value'], ModelMultipleChoiceField)
        self.assertQuerysetSQLEqual(ImageCategory.objects.filter(name='A'),
                                    form.fields['field_value'].queryset
                                   )

        categories_field.limit_choices_to = ~Q(**{'name': 'A'})

        form = BulkDefaultEditForm(categories_field, user, [image])
        self.assertIsInstance(form.fields['field_value'], ModelMultipleChoiceField)
        self.assertQuerysetSQLEqual(ImageCategory.objects.exclude(name='A'),
                                    form.fields['field_value'].queryset
                                   )

        categories_field.limit_choices_to = lambda: {'name': 'B'}

        form = BulkDefaultEditForm(categories_field, user, [image])
        self.assertIsInstance(form.fields['field_value'], ModelMultipleChoiceField)
        self.assertQuerysetSQLEqual(ImageCategory.objects.filter(name='B'),
                                    form.fields['field_value'].queryset
                                   )

    def test_manytomany_entity_innerform(self):
        user = self.login()

        bulk_update_registry = self.bulk_update_registry
        bulk_update_registry.register(EmailCampaign)

        mailing_lists_field = EmailCampaign._meta.get_field('mailing_lists')
        self.assertFalse(hasattr(mailing_lists_field, 'limit_choices_to'))

        campaign = EmailCampaign.objects.create(name='A', user=user)

        form = BulkDefaultEditForm(mailing_lists_field, user, [campaign])
        self.assertIsInstance(form.fields['field_value'], MultiCreatorEntityField)
        self.assertIsNone(form.fields['field_value'].q_filter)

        mailing_lists_field.limit_choices_to = {'name': 'A'}

        form = BulkDefaultEditForm(mailing_lists_field, user, [campaign])
        self.assertIsInstance(form.fields['field_value'], MultiCreatorEntityField)
        self.assertDictEqual({'name': 'A'}, form.fields['field_value'].q_filter)

        mailing_lists_field.limit_choices_to = ~Q(**{'name': 'A'})

        with self.assertRaises(ValueError) as err:
            BulkDefaultEditForm(mailing_lists_field, user, [campaign])

        self.assertEqual(str(err.exception), 'Q filter is not (yet) supported for bulk edition of a field related to a CremeEntity.')

        today = datetime.today()
        mailing_lists_field.limit_choices_to = lambda: {'created__lte': today}

        form = BulkDefaultEditForm(mailing_lists_field, user, [campaign])
        self.assertIsInstance(form.fields['field_value'], MultiCreatorEntityField)
        self.assertDictEqual({'created__lte': today}, form.fields['field_value'].q_filter)

    def test_bulk_update_registry06(self):
        "Unique field"
        registry = self.bulk_update_registry
        registry.register(FakeActivity)

        # 'title' is an unique field which means that its not bulk updatable if
        # the registry manage the unique and it is if not.
        is_bulk_updatable = partial(registry.is_updatable, model=FakeActivity)
        self.assertTrue(is_bulk_updatable(field_name='title', exclude_unique=False))
        self.assertFalse(is_bulk_updatable(field_name='title'))
