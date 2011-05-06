# -*- coding: utf-8 -*-

from time import sleep

from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from activities.models.activity import Meeting, Activity

from creme_core.models import *
from creme_core.gui.last_viewed import LastViewedItem
from creme_core.tests.base import CremeTestCase
from creme_core.gui.bulk_update import BulkUpdateRegistry

from persons.models import Contact
from persons.models.organisation import Organisation


class GuiTestCase(CremeTestCase):
    def setUp(self):
        self.bulk_update_registry = BulkUpdateRegistry()

    def test_last_viewed_items(self):
        self.login()

        class FakeRequest(object):
            def __init__(self):
                sessions = Session.objects.all()
                assert 1 == len(sessions)
                self.session = sessions[0].get_decoded()

        def get_items():
            try:
                return FakeRequest().session['last_viewed_items']
            except Exception, e:
                self.fail(str(e))

        self.assertEqual(0, len(LastViewedItem.get_all(FakeRequest())))

        contact01 = Contact.objects.create(user=self.user, first_name='Casca', last_name='Mylove')
        contact02 = Contact.objects.create(user=self.user, first_name='Puck',  last_name='Elfman')
        contact03 = Contact.objects.create(user=self.user, first_name='Judo',  last_name='Doe')

        self.assertEqual(200, self.client.get(contact01.get_absolute_url()).status_code)
        items = get_items()
        self.assertEqual(1, len(items))
        self.assertEqual(contact01.pk, items[0].pk)

        self.assertEqual(200, self.client.get(contact02.get_absolute_url()).status_code)
        self.assertEqual(200, self.client.get(contact03.get_absolute_url()).status_code)
        items = get_items()
        self.assertEqual(3, len(items))
        self.assertEqual([contact03.pk, contact02.pk, contact01.pk], [i.pk for i in items])

        sleep(1)
        contact01.last_name = 'ILoveYou'
        contact01.save()
        self.assertEqual(200, self.client.get(Contact.get_lv_absolute_url()).status_code)
        old_item = get_items()[2]
        self.assertEqual(contact01.pk,       old_item.pk)
        self.assertEqual(unicode(contact01), old_item.name)

        self.assertEqual(200, self.client.get(contact02.get_absolute_url()).status_code)
        self.assertEqual([contact02.pk, contact03.pk, contact01.pk], [i.pk for i in get_items()])

        contact03.delete()
        self.assertEqual(0, CremeEntity.objects.filter(pk=contact03.id).count())
        self.assertEqual(200, self.client.get(Contact.get_lv_absolute_url()).status_code)
        self.assertEqual([contact02.pk, contact01.pk], [i.pk for i in get_items()])

    def test_bulk_update_registry01(self):
        bulk_update_registry = self.bulk_update_registry

        contact_excluded_fields = ['position', 'first_name']
        ce_excluded_fields = ['created']

        bulk_update_registry.register((Contact, contact_excluded_fields))

        self.assertEqual(bulk_update_registry.get_excluded_fields(Contact), set(contact_excluded_fields))

        bulk_update_registry.register((CremeEntity, ce_excluded_fields))

        self.assertEqual(bulk_update_registry.get_excluded_fields(Contact), set(contact_excluded_fields) | set(ce_excluded_fields))


    def test_bulk_update_registry02(self):
        bulk_update_registry = self.bulk_update_registry

        contact_excluded_fields  = ['position', 'first_name']
        orga_excluded_fields     = ['sector', 'name']
        ce_excluded_fields       = ['created']

        bulk_update_registry.register(
                                        (Contact,      contact_excluded_fields),
                                        (CremeEntity,  ce_excluded_fields),
                                        (Organisation, orga_excluded_fields),
                                     )

        self.assertEqual(bulk_update_registry.get_excluded_fields(Contact),      set(contact_excluded_fields)   | set(ce_excluded_fields))
        self.assertEqual(bulk_update_registry.get_excluded_fields(Organisation), set(orga_excluded_fields)      | set(ce_excluded_fields))

    def test_bulk_update_registry03(self):
        bulk_update_registry = self.bulk_update_registry

        contact_excluded_fields  = ['position', 'first_name']
        orga_excluded_fields     = ['sector', 'name']
        ce_excluded_fields       = ['created']
        activity_excluded_fields = ['title']
        meeting_excluded_fields  = ['place']

        bulk_update_registry.register(
                                        (Contact,      contact_excluded_fields),
                                        (CremeEntity,  ce_excluded_fields),
                                        (Organisation, orga_excluded_fields),
                                        (Meeting,      meeting_excluded_fields),
                                        (Activity,     activity_excluded_fields),
                                     )
        
        meeting_excluded_fields_expected = set(activity_excluded_fields)   | set(ce_excluded_fields) | set(meeting_excluded_fields)
        self.assertEqual(bulk_update_registry.get_excluded_fields(Meeting), meeting_excluded_fields_expected)

        
        bulk_update_registry.register((Activity, ['status']))

        activity_excluded_fields_expected = set(activity_excluded_fields)   | set(ce_excluded_fields) | set(['status'])

        self.assertEqual(bulk_update_registry.get_excluded_fields(Activity), activity_excluded_fields_expected)

    def test_bulk_update_registry04(self):
        bulk_update_registry = self.bulk_update_registry
        
        ce_excluded_fields       = ['created']

        bulk_update_registry.register(
                                        (CremeEntity,  ce_excluded_fields),
                                     )

        self.assertEqual(bulk_update_registry.get_excluded_fields(Contact), set(ce_excluded_fields))
