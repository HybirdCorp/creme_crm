# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from creme_core.models import Relation
from creme_core.tests.base import CremeTestCase

from persons.models import Contact, Organisation

from activities.models import PhoneCall, PhoneCallType, Calendar
from activities.constants import *


class CTITestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'activities')

    def login(self):
        super(CTITestCase, self).login()

        user = self.user
        self.contact = Contact.objects.create(user=user, is_user=user, first_name='Rally', last_name='Vincent')

    def test_add_phonecall01(self):
        self.login()
        user = self.user

        self.failIf(PhoneCall.objects.count())
        self.assert_(PhoneCallType.objects.count())

        contact = Contact.objects.create(user=user, first_name='Bean', last_name='Bandit')
        self.assertEqual(200, self.client.post('/cti/add_phonecall', data={'entity_id': contact.id}).status_code)

        pcalls = PhoneCall.objects.all()
        self.assertEqual(1, len(pcalls))

        pcall = pcalls[0]
        self.assertEqual(user.id, pcall.user_id)
        self.assert_(unicode(contact) in pcall.title)
        self.assert_(pcall.description)
        self.assertEqual(PHONECALLTYPE_OUTGOING, pcall.call_type.id)
        self.assertEqual(STATUS_IN_PROGRESS,     pcall.status.id)
        self.assert_(timedelta(seconds=10) > (datetime.now() - pcall.start))
        self.assertEqual(timedelta(minutes=5), (pcall.end - pcall.start))

        self.assertEqual(1, Relation.objects.filter(subject_entity=self.contact, type=REL_SUB_PART_2_ACTIVITY, object_entity=pcall).count())
        self.assertEqual(1, Relation.objects.filter(subject_entity=contact,      type=REL_SUB_PART_2_ACTIVITY, object_entity=pcall).count())

        calendar = Calendar.get_user_default_calendar(user)
        self.assert_(pcall.calendars.filter(pk=calendar.id).exists())

    def test_add_phonecall02(self): #no contact
        self.login()

        self.assertEqual(404, self.client.post('/cti/add_phonecall', data={'entity_id': '1024'}).status_code)
        self.failIf(PhoneCall.objects.count())

    def test_add_phonecall03(self): #organisation
        self.login()

        orga = Organisation.objects.create(user=self.user, name='Gunsmith Cats')
        self.assertEqual(200, self.client.post('/cti/add_phonecall', data={'entity_id': orga.id}).status_code)

        pcalls = PhoneCall.objects.all()
        self.assertEqual(1, len(pcalls))

        pcall = pcalls[0]
        self.failIf(Relation.objects.filter(subject_entity=orga, type=REL_SUB_PART_2_ACTIVITY, object_entity=pcall).count())
        self.assertEqual(1, Relation.objects.filter(subject_entity=orga, type=REL_SUB_LINKED_2_ACTIVITY, object_entity=pcall).count())

    def test_respond_to_a_call01(self):
        self.login()

        phone='558899'
        contact = Contact.objects.create(user=self.user, first_name='Bean', last_name='Bandit', phone=phone)

        response = self.client.get('/cti/respond_to_a_call', data={'number': phone})
        self.assertEqual(200, response.status_code)

        try:
            callers = response.context['callers']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(1, len(callers))
        self.assertEqual(contact.id, callers[0].id)

    def test_respond_to_a_call02(self):
        self.login()

        phone='558899'
        contact = Contact.objects.create(user=self.user, first_name='Bean', last_name='Bandit', mobile=phone)
        response = self.client.get('/cti/respond_to_a_call', data={'number': phone})
        self.assertEqual(200, response.status_code)
        self.assertEqual([contact.id], [c.id for c in response.context['callers']])

    def test_respond_to_a_call03(self):
        self.login()

        phone='558899'
        orga = Organisation.objects.create(user=self.user, name='Gunsmith Cats', phone=phone)
        response = self.client.get('/cti/respond_to_a_call', data={'number': phone})
        self.assertEqual([orga.id], [o.id for o in response.context['callers']])

    def test_create_contact(self):
        self.login()

        phone = '121366'
        url = '/cti/contact/add/%s' % phone
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            form = response.context['form']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(phone, form.initial.get('phone'))

        response = self.client.post(url, follow=True,
                                    data={
                                            'user':       self.user.id,
                                            'first_name': 'Minnie',
                                            'last_name':  'May',
                                            'phone':      phone,
                                        }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertEqual(1,   Contact.objects.filter(phone=phone).count())

    def test_create_orga(self):
        self.login()

        phone = '987654'
        url = '/cti/organisation/add/%s' % phone
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            form = response.context['form']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(phone, form.initial.get('phone'))

        response = self.client.post(url, follow=True,
                                    data={
                                            'user':  self.user.id,
                                            'name':  'Gunsmith cats',
                                            'phone': phone,
                                        }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertEqual(1,   Organisation.objects.filter(phone=phone).count())

    def test_create_phonecall01(self):
        self.login()
        user = self.user

        contact = Contact.objects.create(user=user, first_name='Bean', last_name='Bandit')
        self.assertEqual(302, self.client.post('/cti/phonecall/add/%s' % contact.id).status_code)

        pcalls = PhoneCall.objects.all()
        self.assertEqual(1, len(pcalls))

        pcall = pcalls[0]
        self.assertEqual(user.id, pcall.user_id)
        self.assert_(unicode(contact) in pcall.title)
        self.assert_(pcall.description)
        self.assertEqual(PHONECALLTYPE_INCOMING, pcall.call_type.id)
        self.assertEqual(STATUS_IN_PROGRESS,     pcall.status.id)
        self.assert_(timedelta(seconds=10) > (datetime.now() - pcall.start))
        self.assertEqual(timedelta(minutes=5), (pcall.end - pcall.start))

        self.assertEqual(1, Relation.objects.filter(subject_entity=self.contact, type=REL_SUB_PART_2_ACTIVITY, object_entity=pcall).count())
        self.assertEqual(1, Relation.objects.filter(subject_entity=contact,      type=REL_SUB_PART_2_ACTIVITY, object_entity=pcall).count())

        calendar = Calendar.get_user_default_calendar(user)
        self.assert_(pcall.calendars.filter(pk=calendar.id).exists())
