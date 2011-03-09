# -*- coding: utf-8 -*-

from time import sleep

from django.contrib.auth.models import User
from django.contrib.sessions.models import Session

from creme_core.models import *
from creme_core.gui.last_viewed import LastViewedItem
from creme_core.tests.base import CremeTestCase

from persons.models import Contact


class GuiTestCase(CremeTestCase):
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
