# -*- coding: utf-8 -*-

try:
    from functools import partial

    from ..base import CremeTestCase, skipIfNotInstalled
    from creme.creme_core.gui.bulk_update import _BulkUpdateRegistry

    from creme.persons.models import Contact, Organisation

    from creme.activities.models import Activity
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('BulkUpdateRegistryTestCase',)


class BulkUpdateRegistryTestCase(CremeTestCase):
    def setUp(self):
        self.bulk_update_registry = _BulkUpdateRegistry()

    def test_bulk_update_registry01(self):
        is_bulk_updatable = partial(self.bulk_update_registry.is_bulk_updatable, model=Organisation)

        organisation_excluded_fields = ['siren']

        self.bulk_update_registry.register((Organisation, organisation_excluded_fields))

        # TODO uncomment when bulk registry will manage empty_or_unique fields
#        self.assertTrue(is_bulk_updatable(field_name='siren', exclude_unique=False)) # Inner editable
        self.assertTrue(is_bulk_updatable(field_name='name'))
        self.assertTrue(is_bulk_updatable(field_name='phone'))

        self.assertFalse(is_bulk_updatable(field_name='created')) # Editable = False
        self.assertFalse(is_bulk_updatable(field_name='billing_address')) # Editable = False
        self.assertFalse(is_bulk_updatable(field_name='siren')) # excluded field

    def test_bulk_update_registry02(self):
        is_bulk_updatable = partial(self.bulk_update_registry.is_bulk_updatable, model=Contact)

        self.assertTrue(is_bulk_updatable(field_name='first_name'))
        self.assertTrue(is_bulk_updatable(field_name='last_name'))

        # Automatically inherited from CremeEntity excluded fields (editable = false)
        self.assertFalse(is_bulk_updatable(field_name='modified'))
        self.assertFalse(is_bulk_updatable(field_name='shipping_address'))
        self.assertFalse(is_bulk_updatable(field_name='is_deleted'))

    def test_bulk_update_registry03(self):
        bulk_update_registry = self.bulk_update_registry

        is_bulk_updatable = partial(self.bulk_update_registry.is_bulk_updatable, model=Activity)

        activity_excluded_fields = ['type', 'start_date', 'end_date', 'busy', 'is_all_day']

        bulk_update_registry.register((Activity, activity_excluded_fields))

        self.assertTrue(is_bulk_updatable(field_name='title'))
        self.assertTrue(is_bulk_updatable(field_name='description'))

        self.assertFalse(is_bulk_updatable(field_name='type'))
        self.assertFalse(is_bulk_updatable(field_name='end_date'))
        self.assertFalse(is_bulk_updatable(field_name='busy'))

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
        is_bulk_updatable = partial(self.bulk_update_registry.is_bulk_updatable, model=Ticket)

        # 'title' is an unique field which means that its not bulk updtable if the registry manage the unique
        # and it is if not
        self.assertTrue(is_bulk_updatable(field_name='title', exclude_unique=False))
        self.assertFalse(is_bulk_updatable(field_name='title'))

