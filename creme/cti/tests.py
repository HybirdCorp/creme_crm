# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from creme_core.models import Relation
from creme_core.tests.base import CremeTestCase

from persons.models import Contact, Organisation

from activities.models import PhoneCall, PhoneCallType, Calendar, CalendarActivityLink
from activities.constants import (PHONECALLTYPE_OUTGOING, STATUS_IN_PROGRESS,
                                  REL_SUB_PART_2_ACTIVITY, REL_SUB_LINKED_2_ACTIVITY)


class CTITestCase(CremeTestCase):
    def setUp(self):
        self.populate('activities')

    def test_add_phonecall01(self):
        self.login()
        user = self.user

        self.failIf(PhoneCall.objects.count())
        self.assert_(PhoneCallType.objects.count())

        create_contact = Contact.objects.create
        user_contact = create_contact(user=user, is_user=user, first_name='Rally', last_name='Vincent')
        contact      = create_contact(user=user, first_name='Bean', last_name='Bandit')
        self.assertEqual(200, self.client.post('/cti/add_phonecall', data={'entity_id': contact.id}).status_code)

        pcalls = PhoneCall.objects.all()
        self.assertEqual(1, len(pcalls))

        pcall = pcalls[0]
        self.assertEqual(self.user.id, pcall.user_id)
        self.assert_(unicode(contact) in pcall.title)
        self.assert_(pcall.description)
        self.assertEqual(PHONECALLTYPE_OUTGOING, pcall.call_type.id)
        self.assertEqual(STATUS_IN_PROGRESS,     pcall.status.id)
        self.assert_(timedelta(seconds=10) > (datetime.now() - pcall.start))
        self.assertEqual(timedelta(minutes=5), (pcall.end - pcall.start))

        self.assertEqual(1, Relation.objects.filter(subject_entity=user_contact, type=REL_SUB_PART_2_ACTIVITY, object_entity=pcall).count())
        self.assertEqual(1, Relation.objects.filter(subject_entity=contact,      type=REL_SUB_PART_2_ACTIVITY, object_entity=pcall).count())

        calendar = Calendar.get_user_default_calendar(user)
        self.assert_(CalendarActivityLink.objects.filter(calendar=calendar, activity=pcall).exists())

    def test_add_phonecall02(self): #no contact
        self.login()
        user = self.user
        user_contact = Contact.objects.create(user=user, is_user=user, first_name='Rally', last_name='Vincent')

        self.assertEqual(404, self.client.post('/cti/add_phonecall', data={'entity_id': '1024'}).status_code)
        self.failIf(PhoneCall.objects.count())

    def test_add_phonecall03(self): #organisation
        self.login()
        user = self.user
        user_contact = Contact.objects.create(user=user, is_user=user, first_name='Rally', last_name='Vincent') #TODO: in setUp ??

        orga = Organisation.objects.create(user=self.user, name='Gunsmith Cats')
        self.assertEqual(200, self.client.post('/cti/add_phonecall', data={'entity_id': orga.id}).status_code)

        pcalls = PhoneCall.objects.all()
        self.assertEqual(1, len(pcalls))

        pcall = pcalls[0]
        self.failIf(Relation.objects.filter(subject_entity=orga, type=REL_SUB_PART_2_ACTIVITY, object_entity=pcall).count())
        self.assertEqual(1, Relation.objects.filter(subject_entity=orga, type=REL_SUB_LINKED_2_ACTIVITY, object_entity=pcall).count())
