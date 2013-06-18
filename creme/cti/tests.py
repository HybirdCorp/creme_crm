# -*- coding: utf-8 -*-

try:
    from datetime import timedelta # datetime
    from functools import partial

    from django.utils.timezone import now

    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons.models import Contact, Organisation

    from creme.activities.models import Activity, Calendar, ActivitySubType
    from creme.activities.constants import *
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class CTITestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'activities')

    def login(self):
        super(CTITestCase, self).login()

        user = self.user
        other_user = self.other_user
        create_contact = partial(Contact.objects.create, user=user)
        self.contact = create_contact(is_user=user, first_name='Rally', last_name='Vincent')
        self.contact_other_user = create_contact(is_user=other_user, first_name='Bean', last_name='Bandit')

    def test_add_phonecall01(self):
        self.login()
        user = self.user

        self.assertFalse(Activity.objects.filter(type=ACTIVITYTYPE_PHONECALL).exists())
        self.assertTrue(ActivitySubType.objects.filter(type=ACTIVITYTYPE_PHONECALL).exists())

        contact = Contact.objects.create(user=user, first_name='Bean', last_name='Bandit')
        self.assertPOST200('/cti/add_phonecall', data={'entity_id': contact.id})

        pcalls = Activity.objects.filter(type=ACTIVITYTYPE_PHONECALL)
        self.assertEqual(1, len(pcalls))

        pcall = pcalls[0]
        self.assertEqual(user, pcall.user)
        self.assertIn(unicode(contact), pcall.title)
        self.assert_(pcall.description)
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_OUTGOING, pcall.sub_type.id)
        self.assertEqual(STATUS_IN_PROGRESS, pcall.status.id)
        self.assertLess((now() - pcall.start).seconds, 10)
        self.assertEqual(timedelta(minutes=5), (pcall.end - pcall.start))

        self.assertRelationCount(1, self.contact, REL_SUB_PART_2_ACTIVITY, pcall)
        self.assertRelationCount(1, contact,      REL_SUB_PART_2_ACTIVITY, pcall)

        calendar = Calendar.get_user_default_calendar(user)
        self.assertTrue(pcall.calendars.filter(pk=calendar.id).exists())

    def test_add_phonecall02(self):
        "No contact"
        self.login()

        self.assertPOST404('/cti/add_phonecall', data={'entity_id': '1024'})
        self.assertFalse(Activity.objects.filter(type=ACTIVITYTYPE_PHONECALL).exists())

    def test_add_phonecall03(self):
        "Organisation"
        self.login()

        orga = Organisation.objects.create(user=self.user, name='Gunsmith Cats')
        self.assertPOST200('/cti/add_phonecall', data={'entity_id': orga.id})

        pcalls = Activity.objects.filter(type=ACTIVITYTYPE_PHONECALL)
        self.assertEqual(1, len(pcalls))

        pcall = pcalls[0]
        self.assertRelationCount(0, orga, REL_SUB_PART_2_ACTIVITY,   pcall)
        self.assertRelationCount(1, orga, REL_SUB_LINKED_2_ACTIVITY, pcall)

    def test_respond_to_a_call01(self):
        self.login()

        phone='558899'
        contact = Contact.objects.create(user=self.user, first_name='Bean', last_name='Bandit', phone=phone)

        response = self.client.get('/cti/respond_to_a_call', data={'number': phone})
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            callers = response.context['callers']

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

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(phone, form.initial.get('phone'))

        response = self.client.post(url, follow=True,
                                    data={'user':       self.user.id,
                                          'first_name': 'Minnie',
                                          'last_name':  'May',
                                          'phone':      phone,
                                        }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(1, Contact.objects.filter(phone=phone).count())

    def test_create_orga(self):
        self.login()

        phone = '987654'
        url = '/cti/organisation/add/%s' % phone
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(phone, form.initial.get('phone'))

        response = self.client.post(url, follow=True,
                                    data={'user':  self.user.id,
                                          'name':  'Gunsmith cats',
                                          'phone': phone,
                                        }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(1, Organisation.objects.filter(phone=phone).count())

    def test_create_phonecall01(self):
        self.login()
        user = self.user

        contact = Contact.objects.create(user=user, first_name='Bean', last_name='Bandit')
        self.assertEqual(302, self.client.post('/cti/phonecall/add/%s' % contact.id).status_code)

        pcalls = Activity.objects.filter(type=ACTIVITYTYPE_PHONECALL)
        self.assertEqual(1, len(pcalls))

        pcall = pcalls[0]
        self.assertEqual(user, pcall.user)
        self.assertIn(unicode(contact), pcall.title)
        self.assertTrue(pcall.description)
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_INCOMING, pcall.sub_type.id)
        self.assertEqual(STATUS_IN_PROGRESS,     pcall.status.id)
        self.assertLess((now() - pcall.start).seconds, 10)
        self.assertEqual(timedelta(minutes=5), (pcall.end - pcall.start))

        self.assertRelationCount(1, self.contact, REL_SUB_PART_2_ACTIVITY, pcall)
        self.assertRelationCount(1, contact,      REL_SUB_PART_2_ACTIVITY, pcall)

        calendar = Calendar.get_user_default_calendar(user)
        self.assertTrue(pcall.calendars.filter(pk=calendar.id).exists())

    def test_create_phonecall02(self):
        self.login()
        user = self.user

        self.assertEqual(302, self.client.post('/cti/phonecall/add/%s' % self.contact.id).status_code)

        self.assertEqual(1, Activity.objects.count())

        phone_call = Activity.objects.all()[0]
        self.assertRelationCount(1, self.contact, REL_SUB_PART_2_ACTIVITY, phone_call)

        calendar = Calendar.get_user_default_calendar(user)
        self.assertTrue(phone_call.calendars.filter(pk=calendar.id).exists())

    def test_create_phonecall03(self):
        self.login()
        user = self.user
        other_user = self.other_user

        self.assertEqual(302, self.client.post('/cti/phonecall/add/%s' % self.contact_other_user.id).status_code)

        self.assertEqual(1, Activity.objects.count())

        phone_call = Activity.objects.all()[0]
        self.assertRelationCount(1, self.contact, REL_SUB_PART_2_ACTIVITY, phone_call)
        self.assertRelationCount(1, self.contact_other_user, REL_SUB_PART_2_ACTIVITY, phone_call)

        calendar_user = Calendar.get_user_default_calendar(user)
        calendar_other_user = Calendar.get_user_default_calendar(other_user)
        self.assertTrue(phone_call.calendars.filter(pk=calendar_user.id).exists())
        self.assertTrue(phone_call.calendars.filter(pk=calendar_other_user.id).exists())
