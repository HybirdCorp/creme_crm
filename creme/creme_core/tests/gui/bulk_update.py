# -*- coding: utf-8 -*-

try:
    from itertools import chain
    from functools import partial

    from django.db.models.fields import FieldDoesNotExist
    from django.contrib.contenttypes.models import ContentType

    from ..base import CremeTestCase, skipIfNotInstalled

    from creme.creme_core.models.custom_field import CustomField
    from creme.creme_core.gui.bulk_update import _BulkUpdateRegistry, FieldNotAllowed
    from creme.creme_core.forms.bulk import BulkDefaultEditForm
    from creme.creme_core.utils.unicode_collation import collator

    from creme.persons.models import Contact, Organisation, Address

    from creme.media_managers.models import Image

    from creme.activities.models import Activity
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('BulkUpdateRegistryTestCase',)


class BulkUpdateRegistryTestCase(CremeTestCase):
    def setUp(self):
        self.bulk_update_registry = _BulkUpdateRegistry()
        self.maxDiff = None

    def sortFields(self, fields):
        sort_key = collator.sort_key
        return sorted(fields, key=lambda f: sort_key(f.verbose_name))

    def test_bulk_update_registry01(self):
        is_bulk_updatable = partial(self.bulk_update_registry.is_updatable, model=Organisation)

        organisation_excluded_fields = ['siren']

        self.bulk_update_registry.register(Organisation, exclude=organisation_excluded_fields)

        # TODO uncomment when bulk registry will manage empty_or_unique fields
#        self.assertTrue(is_bulk_updatable(field_name='siren', exclude_unique=False)) # Inner editable
        self.assertTrue(is_bulk_updatable(field_name='name'))
        self.assertTrue(is_bulk_updatable(field_name='phone'))

        self.assertFalse(is_bulk_updatable(field_name='created')) # Editable = False
        self.assertFalse(is_bulk_updatable(field_name='billing_address')) # Editable = False
        self.assertFalse(is_bulk_updatable(field_name='siren')) # excluded field

    def test_bulk_update_registry02(self):
        is_bulk_updatable = partial(self.bulk_update_registry.is_updatable, model=Contact)

        self.assertTrue(is_bulk_updatable(field_name='first_name'))
        self.assertTrue(is_bulk_updatable(field_name='last_name'))

        # Automatically inherited from CremeEntity excluded fields (editable = false)
        self.assertFalse(is_bulk_updatable(field_name='modified'))
        self.assertFalse(is_bulk_updatable(field_name='shipping_address'))
        self.assertFalse(is_bulk_updatable(field_name='is_deleted'))

    def test_bulk_update_registry03(self):
        bulk_update_registry = self.bulk_update_registry

        is_bulk_updatable = partial(bulk_update_registry.is_updatable, model=Activity)

        activity_excluded_fields = ['type', 'start_date', 'end_date', 'busy', 'is_all_day']

        bulk_update_registry.register(Activity, exclude=activity_excluded_fields)

        self.assertTrue(is_bulk_updatable(field_name='title'))
        self.assertTrue(is_bulk_updatable(field_name='description'))

        self.assertFalse(is_bulk_updatable(field_name='type'))
        self.assertFalse(is_bulk_updatable(field_name='end_date'))
        self.assertFalse(is_bulk_updatable(field_name='busy'))

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
        self.assertTrue(is_bulk_expandable(model=Contact, field_name='billing_address'))
        self.assertTrue(is_bulk_expandable(model=Contact, field_name='shipping_address'))

        # enumerable not expandable
        self.assertFalse(is_bulk_expandable(model=Contact, field_name='civility'))

        # related model is not a CremeModel
        self.assertFalse(is_bulk_expandable(model=Contact, field_name='is_user'))

    def test_is_expandable_excluded(self):
        bulk_update_registry = self.bulk_update_registry

        bulk_update_registry.register(Contact, exclude=['billing_address'])
        self.assertFalse(bulk_update_registry.is_expandable(model=Contact, field_name='billing_address'))
        self.assertTrue(bulk_update_registry.is_expandable(model=Contact, field_name='shipping_address'))


    def test_is_updatable_ignore(self):
        bulk_update_registry = self.bulk_update_registry
        is_bulk_updatable = partial(bulk_update_registry.is_updatable, model=Activity)

        bulk_update_registry.ignore(Activity)

        self.assertFalse(is_bulk_updatable(field_name='title'))
        self.assertFalse(is_bulk_updatable(field_name='description'))

        self.assertFalse(is_bulk_updatable(field_name='type'))
        self.assertFalse(is_bulk_updatable(field_name='end_date'))
        self.assertFalse(is_bulk_updatable(field_name='busy'))

    def test_regular_fields(self):
        bulk_update_registry = self.bulk_update_registry

        expected = [field for field in chain(Contact._meta.fields, Contact._meta.many_to_many)
                        if field.editable and not field.unique
                   ]
        self.assertListEqual(self.sortFields(expected),
                             bulk_update_registry.regular_fields(Contact))

    def test_regular_fields_ignore(self):
        bulk_update_registry = self.bulk_update_registry

        bulk_update_registry.ignore(Activity)
        self.assertListEqual(bulk_update_registry.regular_fields(Activity), [])

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
            bulk_update_registry.status(Contact).get_field('billing_address')

        with self.assertRaises(FieldNotAllowed):
            bulk_update_registry.get_field(Contact, 'billing_address')

    def test_get_regular_subfield_expandable(self):
        bulk_update_registry = self.bulk_update_registry
        bulk_update_registry.register(Contact)

        with self.assertRaises(FieldNotAllowed):
            bulk_update_registry.get_field(Contact, 'billing_address')

        self.assertIsNotNone(bulk_update_registry.status(Contact).get_expandable_field('billing_address'))
        self.assertIsNotNone(bulk_update_registry.get_field(Contact, 'billing_address__zipcode'))

    def test_regular_fields_expanded(self):
        bulk_update_registry = self.bulk_update_registry
        bulk_update_registry.register(Contact)

        expected_names = [field.name for field in chain(Contact._meta.fields, Contact._meta.many_to_many)
                              if field.editable and not field.unique
                         ]
        expanded_names = ['billing_address', 'shipping_address']

        fields = bulk_update_registry.regular_fields(Contact, expand=True)

        self.assertListEqual(sorted(expected_names + expanded_names), sorted([field[0].name for field in fields]))
        self.assertListEqual(sorted(expanded_names), sorted([field.name for field, sub in fields if sub is not None]))

        fields_dict = {field[0].name: field for field in fields}

        sub_expected_names = [field.name for field in chain(Address._meta.fields, Address._meta.many_to_many)
                                  if field.editable and not field.unique
                             ]

        billing_fields = fields_dict['billing_address'][1]
        self.assertListEqual(sorted(sub_expected_names), sorted([field.name for field in billing_fields]))

    def test_regular_subfield(self):
        bulk_update_registry = self.bulk_update_registry
        bulk_update_registry.register(Contact)

        zipcode_field = Address._meta.get_field_by_name('zipcode')[0]
        self.assertEqual(zipcode_field, bulk_update_registry.get_field(Contact, 'billing_address__zipcode'))
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

        bulk_update_registry.ignore(Activity)
        self.assertListEqual(bulk_update_registry.custom_fields(Activity), [])

    def test_innerforms(self):
        bulk_update_registry = self.bulk_update_registry
        is_bulk_updatable = partial(bulk_update_registry.is_updatable, model=Activity)

        class _ActivityInnerStart(BulkDefaultEditForm):
            pass

        bulk_update_registry.register(Activity, exclude=['type'], innerforms={'start': _ActivityInnerStart})

        self.assertFalse(is_bulk_updatable(field_name='type'))
        self.assertIsNone(bulk_update_registry.status(Activity).get_form('type'))

        self.assertTrue(is_bulk_updatable(field_name='start'))
        self.assertEquals(_ActivityInnerStart, bulk_update_registry.status(Activity).get_form('start'))

    def test_innerforms_inherit(self):
        bulk_update_registry = self.bulk_update_registry
        is_bulk_updatable = bulk_update_registry.is_updatable

        class SubActivity(Activity):
            pass

        class _ActivityInnerEdit(BulkDefaultEditForm):
            pass

        class _SubActivityInnerEdit(BulkDefaultEditForm):
            pass

        bulk_update_registry.register(Activity, exclude=['type'],
                                      innerforms={'start': _ActivityInnerEdit, 'minutes': _ActivityInnerEdit}
                                     )
        bulk_update_registry.register(SubActivity, exclude=['type'],
                                      innerforms={'end': _SubActivityInnerEdit, 'minutes': _SubActivityInnerEdit}
                                     )

        self.assertFalse(is_bulk_updatable(model=Activity, field_name='type'))
        self.assertFalse(is_bulk_updatable(model=SubActivity, field_name='type'))
        self.assertIsNone(bulk_update_registry.status(Activity).get_form('type'))
        self.assertIsNone(bulk_update_registry.status(SubActivity).get_form('type'))

        # subclass inherits inner forms from base class
        self.assertTrue(is_bulk_updatable(model=Activity, field_name='start'))
        self.assertTrue(is_bulk_updatable(model=SubActivity, field_name='start'))
        self.assertEquals(_ActivityInnerEdit, bulk_update_registry.status(Activity).get_form('start'))
        self.assertEquals(_ActivityInnerEdit, bulk_update_registry.status(SubActivity).get_form('start'))

        # base class ignore changes of inner form made for subclass
        self.assertTrue(is_bulk_updatable(model=Activity, field_name='end'))
        self.assertTrue(is_bulk_updatable(model=SubActivity, field_name='end'))
        self.assertIsNone(bulk_update_registry.status(Activity).get_form('end'))
        self.assertEquals(_SubActivityInnerEdit, bulk_update_registry.status(SubActivity).get_form('end'))

        # subclass force bulk form for field
        self.assertTrue(is_bulk_updatable(model=Activity, field_name='minutes'))
        self.assertTrue(is_bulk_updatable(model=SubActivity, field_name='minutes'))
        self.assertEquals(_ActivityInnerEdit, bulk_update_registry.status(Activity).get_form('minutes'))
        self.assertEquals(_SubActivityInnerEdit, bulk_update_registry.status(SubActivity).get_form('minutes'))

    def test_subfield_innerforms(self):
        self.login()

        bulk_update_registry = self.bulk_update_registry
        bulk_update_registry.register(Contact)

        class _ZipcodeInnerEdit(BulkDefaultEditForm):
            pass

        contact = Contact.objects.create(last_name='contact', user=self.user)
        contact.billing_address = Address.objects.create(owner=contact)

        form = bulk_update_registry.get_form(Contact, 'billing_address__zipcode', BulkDefaultEditForm)(user=self.user, entities=[contact])

        self.assertIsInstance(form, BulkDefaultEditForm)

        bulk_update_registry.register(Address, innerforms={'zipcode': _ZipcodeInnerEdit})

        form = bulk_update_registry.get_form(Contact, 'billing_address__zipcode', BulkDefaultEditForm)(user=self.user, entities=[contact])
        self.assertIsInstance(form, _ZipcodeInnerEdit)

    def test_expandable_innerforms(self):
        self.login()

        contact = Contact.objects.create(last_name='contact', user=self.user)
        contact.billing_address = Address.objects.create(owner=contact)

        bulk_update_registry = self.bulk_update_registry
        bulk_update_registry.register(Contact)

        with self.assertRaises(FieldNotAllowed):
            bulk_update_registry.get_form(Contact, 'billing_address', BulkDefaultEditForm)

        form = bulk_update_registry.get_form(Contact, 'billing_address__zipcode', BulkDefaultEditForm)(user=self.user, entities=[contact])
        self.assertIsInstance(form, BulkDefaultEditForm)

    #def test_bulk_update_registry04_1(self): # Inheritance test case Parent / Child
        #bulk_update_registry = self.bulk_update_registry

        #is_bulk_updatable_for_activity = partial(bulk_update_registry.is_bulk_updatable, model=Activity)
        #is_bulk_updatable_for_meeting = partial(bulk_update_registry.is_bulk_updatable, model=Meeting)

        #activity_excluded_fields = ['type', 'start', 'end', 'busy', 'is_all_day']

        #bulk_update_registry.register((Activity, activity_excluded_fields))

        #self.assertFalse(is_bulk_updatable_for_activity(field_name='type'))
        #self.assertFalse(is_bulk_updatable_for_activity(field_name='end'))
        #self.assertFalse(is_bulk_updatable_for_activity(field_name='busy'))

        #bulk_update_registry.register((Meeting, []))

        ## inherited automatically from CremeEntity
        #self.assertFalse(is_bulk_updatable_for_meeting(field_name='created'))

        ## inherited from Activity excluded fields
        #self.assertFalse(is_bulk_updatable_for_meeting(field_name='type'))
        #self.assertFalse(is_bulk_updatable_for_meeting(field_name='end'))
        #self.assertFalse(is_bulk_updatable_for_meeting(field_name='busy'))

    #def test_bulk_update_registry04_2(self): # Inheritance test case Parent / Child without registering model first
        #bulk_update_registry = self.bulk_update_registry

        #is_bulk_updatable_for_activity = partial(bulk_update_registry.is_bulk_updatable, model=Activity)
        #is_bulk_updatable_for_meeting = partial(bulk_update_registry.is_bulk_updatable, model=Meeting)

        #activity_excluded_fields = ['type', 'start', 'end', 'busy', 'is_all_day']

        #bulk_update_registry.register((Activity, activity_excluded_fields))

        #self.assertFalse(is_bulk_updatable_for_activity(field_name='type'))
        #self.assertFalse(is_bulk_updatable_for_activity(field_name='end'))
        #self.assertFalse(is_bulk_updatable_for_activity(field_name='busy'))

        ## inherited automatically from CremeEntity
        #self.assertFalse(is_bulk_updatable_for_meeting(field_name='created'))

        ## inherited from Activity excluded fields
        #self.assertFalse(is_bulk_updatable_for_meeting(field_name='type'))
        #self.assertFalse(is_bulk_updatable_for_meeting(field_name='end'))
        #self.assertFalse(is_bulk_updatable_for_meeting(field_name='busy'))

    #def test_bulk_update_registry05(self): # Inheritance test case Child / Parent
        #bulk_update_registry = self.bulk_update_registry

        #is_bulk_updatable_for_meeting = partial(bulk_update_registry.is_bulk_updatable, model=Meeting)

        #bulk_update_registry.register((Meeting, []))

        #self.assertTrue(is_bulk_updatable_for_meeting(field_name='type'))
        #self.assertTrue(is_bulk_updatable_for_meeting(field_name='end'))
        #self.assertTrue(is_bulk_updatable_for_meeting(field_name='busy'))

        #activity_excluded_fields = ['type', 'start', 'end', 'busy', 'is_all_day']
        #bulk_update_registry.register((Activity, activity_excluded_fields))

        #self.assertFalse(is_bulk_updatable_for_meeting(field_name='type'))
        #self.assertFalse(is_bulk_updatable_for_meeting(field_name='end'))
        #self.assertFalse(is_bulk_updatable_for_meeting(field_name='busy'))

    @skipIfNotInstalled('creme.tickets')
    def test_bulk_update_registry06(self):
        "Unique field"
        from creme.tickets.models import Ticket
        is_bulk_updatable = partial(self.bulk_update_registry.is_updatable, model=Ticket)

        self.bulk_update_registry.register(Ticket)

        # 'title' is an unique field which means that its not bulk updtable if the registry manage the unique
        # and it is if not
        self.assertTrue(is_bulk_updatable(field_name='title', exclude_unique=False))
        self.assertFalse(is_bulk_updatable(field_name='title'))

