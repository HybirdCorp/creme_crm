# -*- coding: utf-8 -*-

from functools import partial
from itertools import chain

from django.contrib.contenttypes.models import ContentType
from django.db.models.query_utils import Q
from django.forms.models import ModelMultipleChoiceField
from django.urls import reverse

from creme.creme_config.forms.fields import CreatorModelChoiceField
from creme.creme_core.core import entity_cell
from creme.creme_core.forms.bulk import BulkDefaultEditForm
from creme.creme_core.forms.fields import (
    CreatorEntityField,
    MultiCreatorEntityField,
)
from creme.creme_core.gui.bulk_update import (
    FieldNotAllowed,
    _BulkUpdateRegistry,
)
from creme.creme_core.models import CustomField, Language
from creme.creme_core.utils.unicode_collation import collator

from ..base import CremeTestCase
from ..fake_models import (
    FakeActivity,
    FakeAddress,
    FakeCivility,
    FakeContact,
    FakeEmailCampaign,
    FakeImage,
    FakeImageCategory,
    FakeLegalForm,
    FakeOrganisation,
    FakeProduct,
    FakeSector,
)


# TODO: test register(..., expandables=[..])
class BulkUpdateRegistryTestCase(CremeTestCase):
    def setUp(self):
        super().setUp()
        self.bulk_update_registry = _BulkUpdateRegistry()
        self.maxDiff = None

    @staticmethod
    def sort_fields(fields):
        sort_key = collator.sort_key
        return sorted(fields, key=lambda f: sort_key(f.verbose_name))

    def test_bulk_update_registry01(self):
        registry = self.bulk_update_registry
        is_updatable = partial(registry.is_updatable, model=FakeOrganisation)

        registry.register(FakeOrganisation, exclude=['emails'])

        # TODO uncomment when bulk registry will manage empty_or_unique fields
        self.assertTrue(is_updatable(field_name='name'))
        self.assertTrue(is_updatable(field_name='phone'))

        self.assertFalse(is_updatable(field_name='id'))
        self.assertFalse(is_updatable(field_name='cremeentity_ptr'))
        self.assertFalse(is_updatable(field_name='created'))  # Editable = False
        self.assertFalse(is_updatable(field_name='address'))  # Editable = False
        self.assertFalse(is_updatable(field_name='emails'))  # Excluded field

    def test_bulk_update_registry02(self):
        is_updatable = partial(self.bulk_update_registry.is_updatable, model=FakeContact)

        self.assertTrue(is_updatable(field_name='first_name'))
        self.assertTrue(is_updatable(field_name='last_name'))

        # Automatically inherited from CremeEntity excluded fields (editable = false)
        self.assertFalse(is_updatable(field_name='modified'))
        self.assertFalse(is_updatable(field_name='address'))
        self.assertFalse(is_updatable(field_name='is_deleted'))

    def test_bulk_update_registry03(self):
        "Unique field."
        registry = self.bulk_update_registry
        registry.register(FakeActivity)

        # 'title' is an unique field which means that its not bulk updatable if
        # the registry manage the unique and it is if not.
        is_bulk_updatable = partial(registry.is_updatable, model=FakeActivity)
        self.assertTrue(is_bulk_updatable(field_name='title', exclude_unique=False))
        self.assertFalse(is_bulk_updatable(field_name='title'))

    def test_is_updatable_many2many(self):
        registry = self.bulk_update_registry

        registry.register(FakeImage)
        self.assertTrue(
            registry.is_updatable(model=FakeImage, field_name='categories')
        )

        status = registry.status(FakeImage)
        self.assertFalse(status.is_expandable(status.get_field('categories')))

    def test_is_updatable_foreignkey(self):
        registry = self.bulk_update_registry
        is_updatable = registry.is_updatable

        registry.register(FakeContact)
        self.assertFalse(is_updatable(model=FakeContact, field_name='billing_address'))
        self.assertFalse(is_updatable(model=FakeContact, field_name='shipping_address'))

    def test_is_updatable_enumerable(self):
        registry = self.bulk_update_registry

        registry.register(FakeContact)
        self.assertTrue(
            registry.is_updatable(model=FakeContact, field_name='civility')
        )

        status = registry.status(FakeContact)
        self.assertFalse(status.is_expandable(status.get_field('civility')))

    def test_is_updatable_not_editable(self):
        registry = self.bulk_update_registry
        is_updatable = registry.is_updatable

        registry.register(FakeContact)
        self.assertFalse(is_updatable(model=FakeContact, field_name='billing_address'))
        self.assertFalse(is_updatable(model=FakeContact, field_name='shipping_address'))

    def test_is_expandable(self):
        registry = self.bulk_update_registry
        is_expandable = registry.is_expandable

        registry.register(FakeContact)
        self.assertTrue(is_expandable(model=FakeContact, field_name='address'))

        # Enumerable not expandable
        self.assertFalse(is_expandable(model=FakeContact, field_name='civility'))

        # Related model is not a CremeModel
        self.assertFalse(is_expandable(model=FakeContact, field_name='is_user'))

    def test_is_expandable_excluded(self):
        registry = self.bulk_update_registry

        registry.register(FakeContact, exclude=['address'])
        self.assertFalse(
            registry.is_expandable(model=FakeContact, field_name='address')
        )

    def test_is_updatable_ignore(self):
        registry = self.bulk_update_registry
        is_updatable = partial(registry.is_updatable, model=FakeOrganisation)

        registry.ignore(FakeOrganisation)
        self.assertFalse(is_updatable(field_name='name'))
        self.assertFalse(is_updatable(field_name='phone'))

    def test_regular_fields(self):
        fields = {
            field.name: field
            for field in chain(
                FakeContact._meta.fields,
                FakeContact._meta.many_to_many,
            )
            if field.editable and not field.unique
        }
        self.assertIn('first_name', fields)
        self.assertIn('last_name',  fields)
        self.assertIn('sector',     fields)
        self.assertIn('languages',  fields)  # M2M

        self.assertNotIn('id',              fields)  # Unique
        self.assertNotIn('cremeentity_ptr', fields)  # Unique
        self.assertNotIn('is_user',         fields)  # Not editable

        registry = self.bulk_update_registry

        self.assertListEqual(
            self.sort_fields(fields.values()),
            registry.regular_fields(FakeContact),
        )

        registry.register(FakeContact, exclude=['sector'])
        del fields['sector']
        self.assertListEqual(
            self.sort_fields(fields.values()),
            registry.regular_fields(FakeContact),
        )

        # ---
        get_field = FakeActivity._meta.get_field
        self.assertListEqual(
            self.sort_fields([
                get_field(fname) for fname in
                [
                    # 'cremeentity_ptr',
                    # 'id',
                    'user',
                    'description',

                    # 'title',  Unique
                    'place',
                    'minutes',
                    'start',
                    'end',
                    'type',
                ]
            ]),
            registry.regular_fields(FakeActivity),
        )

    def test_regular_fields_ignore(self):
        registry = self.bulk_update_registry

        registry.ignore(FakeContact)
        self.assertListEqual([], registry.regular_fields(FakeContact))

    def test_regular_fields_include_unique(self):
        # meta = FakeContact._meta
        get_field = FakeActivity._meta.get_field
        self.assertListEqual(
            self.sort_fields([
                # field
                # for field in chain(meta.fields, meta.many_to_many)
                # if field.editable
                get_field(fname) for fname in
                [
                    # 'cremeentity_ptr',
                    # 'id',
                    'user',
                    'description',

                    'title',
                    'place',
                    'minutes',
                    'start',
                    'end',
                    'type',
                ]
            ]),
            # self.bulk_update_registry.regular_fields(FakeContact, exclude_unique=False),
            self.bulk_update_registry.regular_fields(FakeActivity, exclude_unique=False),
        )

    def test_get_regular_field_not_editable(self):
        registry = self.bulk_update_registry
        registry.register(FakeContact)
        status = registry.status(FakeContact)
        get_field = FakeContact._meta.get_field

        self.assertFalse(status.is_updatable(get_field('address')))

        with self.assertRaises(FieldNotAllowed):
            status.get_field('address')

        with self.assertRaises(FieldNotAllowed):
            registry.get_field(FakeContact, 'address')

        # ---
        self.assertFalse(status.is_updatable(get_field('id')))

        with self.assertRaises(FieldNotAllowed):
            status.get_field('id')

        with self.assertRaises(FieldNotAllowed):
            registry.get_field(FakeContact, 'id')

        # ---
        self.assertFalse(status.is_updatable(get_field('cremeentity_ptr')))

        with self.assertRaises(FieldNotAllowed):
            status.get_field('cremeentity_ptr')

        with self.assertRaises(FieldNotAllowed):
            registry.get_field(FakeContact, 'cremeentity_ptr')

    def test_get_regular_subfield_expandable(self):
        registry = self.bulk_update_registry
        registry.register(FakeContact)

        with self.assertRaises(FieldNotAllowed):
            registry.get_field(FakeContact, 'address')

        self.assertIsNotNone(
            registry.status(FakeContact).get_expandable_field('address'),
        )
        self.assertIsNotNone(
            registry.get_field(FakeContact, 'address__zipcode'),
        )

    def test_regular_fields_expanded(self):
        registry = self.bulk_update_registry
        registry.register(FakeContact)

        c_meta = FakeContact._meta
        expected_names = [
            field.name
            for field in chain(c_meta.fields, c_meta.many_to_many)
            if field.editable and not field.unique
        ]
        expanded_names = ['address']

        fields = registry.regular_fields(FakeContact, expand=True)

        self.assertListEqual(
            sorted(expected_names + expanded_names),
            sorted(field[0].name for field in fields),
        )
        self.assertListEqual(
            sorted(expanded_names),
            sorted(field.name for field, sub in fields if sub is not None)
        )

        fields_dict = {field[0].name: field for field in fields}

        a_meta = FakeAddress._meta
        sub_expected_names = [
            field.name
            for field in chain(a_meta.fields, a_meta.many_to_many)
            if field.editable and not field.unique
        ]

        address_fields = fields_dict['address'][1]
        self.assertListEqual(
            sorted(sub_expected_names),
            sorted(field.name for field in address_fields),
        )

    def test_regular_subfield(self):
        registry = self.bulk_update_registry
        registry.register(FakeContact)

        zipcode_field = FakeAddress._meta.get_field('zipcode')
        self.assertEqual(
            zipcode_field,
            registry.get_field(FakeContact, 'address__zipcode'),
        )
        self.assertEqual(
            zipcode_field,
            registry.get_field(FakeAddress, 'zipcode'),
        )

    def test_default_field(self):
        registry = self.bulk_update_registry
        registry.register(FakeContact)

        meta = FakeContact._meta
        expected = self.sort_fields([
            field
            for field in chain(meta.fields, meta.many_to_many)
            if field.editable and not field.unique
        ])[0]
        self.assertEqual(
            expected.name,
            registry.get_default_field(FakeContact).name,
        )

    def test_custom_fields(self):
        registry = self.bulk_update_registry
        registry.register(FakeContact)

        contact_ct = ContentType.objects.get_for_model(FakeContact)

        create_cf = CustomField.objects.create
        create_cf(name='A', content_type=contact_ct, field_type=CustomField.STR)

        meta = FakeContact._meta
        regular_names = [
            field.name
            for field in chain(meta.fields, meta.many_to_many)
            if field.editable and not field.unique
        ]
        custom_names = ['A']

        regular_fields = registry.regular_fields(FakeContact)
        custom_fields  = registry.custom_fields(FakeContact)

        self.assertListEqual(
            sorted(regular_names),
            sorted([field.name for field in regular_fields])
        )
        self.assertListEqual(
            sorted(custom_names),
            [field.name for field in custom_fields],
        )

        create_cf(name='C', content_type=contact_ct, field_type=CustomField.BOOL)
        create_cf(name='0', content_type=contact_ct, field_type=CustomField.INT)
        create_cf(
            name='DELETED', content_type=contact_ct, field_type=CustomField.INT,
            is_deleted=True,
        )

        custom_names = ['0', 'A', 'C']

        regular_fields = registry.regular_fields(FakeContact)
        custom_fields  = registry.custom_fields(FakeContact)

        self.assertListEqual(
            sorted(regular_names),
            sorted([field.name for field in regular_fields]),
        )
        self.assertListEqual(
            sorted(custom_names),
            [field.name for field in custom_fields],
        )

    def test_custom_fields_ignore(self):
        registry = self.bulk_update_registry

        registry.ignore(FakeOrganisation)
        self.assertListEqual(registry.custom_fields(FakeOrganisation), [])

    def test_innerforms(self):
        registry = self.bulk_update_registry
        is_updatable = partial(registry.is_updatable, model=FakeContact)

        class _ContactInnerBirthday(BulkDefaultEditForm):
            pass

        registry.register(
            FakeContact,
            exclude=['position'],
            innerforms={'birthday': _ContactInnerBirthday},
        )

        self.assertFalse(is_updatable(field_name='position'))
        self.assertIsNone(registry.status(FakeContact).get_form('position'))

        self.assertTrue(is_updatable(field_name='birthday'))
        self.assertEqual(
            _ContactInnerBirthday,
            registry.status(FakeContact).get_form('birthday'),
        )

# NB: these 2 tests make some other test cases crash.
#  eg: Problem with entity deletion: (1146, "Table '....creme_core_subcontact' doesn't exist")
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
        user = self.create_user()

        registry = self.bulk_update_registry
        registry.register(FakeContact)

        class _ZipcodeInnerEdit(BulkDefaultEditForm):
            pass

        contact = FakeContact.objects.create(last_name='contact', user=user)

        form = registry.get_form(
            FakeContact, 'address__zipcode', BulkDefaultEditForm,
        )(user=user, entities=[contact])

        self.assertIsInstance(form, BulkDefaultEditForm)

        registry.register(
            FakeAddress, innerforms={'zipcode': _ZipcodeInnerEdit},
        )

        form = registry.get_form(
            FakeContact, 'address__zipcode', BulkDefaultEditForm,
        )(user=user, entities=[contact])
        self.assertIsInstance(form, _ZipcodeInnerEdit)

    def test_expandable_innerforms(self):
        user = self.create_user()

        contact = FakeContact.objects.create(last_name='contact', user=user)

        registry = self.bulk_update_registry
        registry.register(FakeContact)

        with self.assertRaises(FieldNotAllowed):
            registry.get_form(FakeContact, 'address', BulkDefaultEditForm)

        form = registry.get_form(
            FakeContact, 'address__zipcode', BulkDefaultEditForm,
        )(user=user, entities=[contact])
        self.assertIsInstance(form, BulkDefaultEditForm)

    def test_fk_innerform01(self):
        user = self.create_user()

        civility_field = FakeContact._meta.get_field('civility')
        self.assertFalse(civility_field.remote_field.limit_choices_to)

        contact = FakeContact.objects.create(first_name='A', last_name='B', user=user)

        form = BulkDefaultEditForm(FakeContact, civility_field, user, [contact])
        field_value_f = form.fields['field_value']
        self.assertIsInstance(field_value_f, CreatorModelChoiceField)
        self.assertQuerysetSQLEqual(FakeCivility.objects.all(), field_value_f.queryset)

    def test_fk_innerform02(self):
        "limit_choices_to: dict."
        user = self.create_user()

        lform_field = FakeOrganisation._meta.get_field('legal_form')
        self.assertEqual(
            {'title__endswith': '[OK]'},
            lform_field.remote_field.limit_choices_to
        )

        orga = FakeOrganisation.objects.create(user=user, name='A')

        form = BulkDefaultEditForm(FakeContact, lform_field, user, [orga])
        self.assertQuerysetSQLEqual(
            FakeLegalForm.objects.filter(title__endswith='[OK]'),
            form.fields['field_value'].queryset
        )

    def test_fk_innerform03(self):
        "limit_choices_to: callable yielding Q"
        user = self.create_user()

        sector_field = FakeContact._meta.get_field('sector')
        # NB: limit_choices_to=lambda: ~Q(title='[INVALID]')
        self.assertTrue(callable(sector_field.remote_field.limit_choices_to))

        contact = FakeContact.objects.create(first_name='A', last_name='B', user=user)

        form = BulkDefaultEditForm(FakeContact, sector_field, user, [contact])
        self.assertQuerysetSQLEqual(
            FakeSector.objects.exclude(title='[INVALID]'),
            form.fields['field_value'].queryset
        )

    def test_fk_entity_innerform01(self):
        user = self.create_user()

        image_field = FakeContact._meta.get_field('image')
        self.assertFalse(image_field.remote_field.limit_choices_to)

        contact = FakeContact.objects.create(first_name='A', last_name='B', user=user)

        form = BulkDefaultEditForm(FakeContact, image_field, user, [contact])
        self.assertIsInstance(form.fields['field_value'], CreatorEntityField)
        self.assertFalse(form.fields['field_value'].q_filter)

    def test_fk_entity_innerform02(self):
        "limit_choices_to."
        user = self.create_user()

        image_field = FakeOrganisation._meta.get_field('image')
        # NB: limit_choices_to=lambda: {'user__is_staff': False}
        self.assertTrue(callable(image_field.remote_field.limit_choices_to))

        orga = FakeOrganisation.objects.create(user=user, name='A')
        form = BulkDefaultEditForm(FakeOrganisation, image_field, user, [orga])

        field_value_f = form.fields['field_value']
        self.assertTrue(callable(field_value_f.q_filter))
        self.assertQEqual(Q(user__is_staff=False), field_value_f.q_filter_query)

        # TODO: test Q as limit_choices_to
        # with self.assertRaises(ValueError) as err:
        #     BulkDefaultEditForm(Contact, image_field, user, [contact])
        #
        # self.assertEqual(
        #     str(err.exception),
        #     'Q filter is not (yet) supported for bulk edition of a field
        #     related to a CremeEntity.'
        # )

    def test_manytomany_innerform01(self):
        user = self.create_user()

        categories_field = FakeImage._meta.get_field('categories')
        self.assertFalse(categories_field.remote_field.limit_choices_to)

        image = FakeImage.objects.create(name='A', user=user)
        form = BulkDefaultEditForm(FakeImage, categories_field, user, [image])

        field_value_f = form.fields['field_value']
        self.assertIsInstance(field_value_f, ModelMultipleChoiceField)
        self.assertQuerysetSQLEqual(
            FakeImageCategory.objects.all(),
            field_value_f.queryset,
        )

    def test_manytomany_innerform02(self):
        "limit_choices_to"
        user = self.create_user()

        languages_field = FakeContact._meta.get_field('languages')
        # NB: limit_choices_to=~Q(name__contains='[deprecated]')
        self.assertIsInstance(languages_field.remote_field.limit_choices_to, Q)

        contact = FakeContact.objects.create(user=user, first_name='A', last_name='B')

        form = BulkDefaultEditForm(FakeImage, languages_field, user, [contact])
        self.assertQuerysetSQLEqual(
            Language.objects.exclude(name__contains='[deprecated]'),
            form.fields['field_value'].queryset,
        )

    def test_manytomany_entity_innerform01(self):
        user = self.create_user()

        mailing_lists_field = FakeEmailCampaign._meta.get_field('mailing_lists')
        self.assertFalse(mailing_lists_field.remote_field.limit_choices_to)

        campaign = FakeEmailCampaign.objects.create(name='A', user=user)
        form = BulkDefaultEditForm(FakeEmailCampaign, mailing_lists_field, user, [campaign])

        field_value_f = form.fields['field_value']
        self.assertIsInstance(field_value_f, MultiCreatorEntityField)
        self.assertFalse(field_value_f.q_filter)

    def test_manytomany_entity_innerform02(self):
        "limit_choices_to."
        user = self.create_user()

        images_field = FakeProduct._meta.get_field('images')
        self.assertDictEqual(
            {'user__is_active': True},
            images_field.remote_field.limit_choices_to,
        )

        product = FakeProduct.objects.create(user=user, name='P1')

        form = BulkDefaultEditForm(FakeEmailCampaign, images_field, user, [product])
        self.assertEqual({'user__is_active': True}, form.fields['field_value'].q_filter)

        # TODO: test Q as limit_choices_to
        # with self.assertRaises(ValueError) as err:
        #     BulkDefaultEditForm(EmailCampaign, mailing_lists_field, user, [campaign])
        #
        # self.assertEqual(
        #     str(err.exception),
        #     'Q filter is not (yet) supported for bulk edition of a field '
        #     'related to a CremeEntity.'
        # )

    def test_inner_uri01(self):
        "Regular field."
        user = self.create_user()
        model = FakeContact
        instance = model.objects.create(
            user=user, first_name='Guybrush', last_name='Threepwood',
        )
        ct_id = instance.entity_type_id
        pk = instance.id

        fname1 = 'first_name'
        cell1 = entity_cell.EntityCellRegularField.build(model=model, name=fname1)
        self.assertEqual(
            reverse('creme_core__inner_edition', args=(ct_id, pk, fname1)),
            self.bulk_update_registry.inner_uri(cell=cell1, instance=instance, user=user),
        )

        fname2 = 'last_name'
        cell2 = entity_cell.EntityCellRegularField.build(model=model, name=fname2)
        self.assertEqual(
            reverse('creme_core__inner_edition', args=(ct_id, pk, fname2)),
            self.bulk_update_registry.inner_uri(cell=cell2, instance=instance, user=user),
        )

    def test_inner_uri02(self):
        "Not inner-editable field."
        user = self.create_user()
        model = FakeContact
        fname = 'first_name'

        registry = self.bulk_update_registry
        registry.register(model, exclude=[fname])

        instance = model.objects.create(
            user=user, first_name='Guybrush', last_name='Threepwood',
        )
        cell = entity_cell.EntityCellRegularField.build(model=model, name=fname)
        self.assertIsNone(registry.inner_uri(cell=cell, instance=instance, user=user))

    def test_inner_uri03(self):
        "Custom field."
        user = self.create_user()
        model = FakeContact

        ct = ContentType.objects.get_for_model(model)
        cfield = CustomField.objects.create(
            name='A', content_type=ct, field_type=CustomField.STR,
        )

        instance = model.objects.create(
            user=user, first_name='Guybrush', last_name='Threepwood',
        )
        cell = entity_cell.EntityCellCustomField.build(model=model, customfield_id=cfield.id)
        self.assertEqual(
            reverse(
                'creme_core__inner_edition',
                args=(ct.id, instance.id, f'customfield-{cfield.id}'),
            ),
            self.bulk_update_registry.inner_uri(cell=cell, instance=instance, user=user),
        )
