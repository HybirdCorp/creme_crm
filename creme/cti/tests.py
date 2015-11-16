# -*- coding: utf-8 -*-

try:
    from datetime import timedelta # datetime
    #from functools import partial

    from django.core.urlresolvers import reverse
    from django.utils.timezone import now

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.gui.field_printers import field_printers_registry
    from creme.creme_core.models import FieldsConfig

    from creme.persons import get_contact_model, get_organisation_model
    # from creme.persons.models import Contact, Organisation
    from creme.persons.tests.base import skipIfCustomContact, skipIfCustomOrganisation

    from creme.activities import get_activity_model
    from creme.activities.models import Calendar, ActivityType, ActivitySubType  # Activity
    from creme.activities.constants import *
    from creme.activities.tests.base import skipIfCustomActivity
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


Contact = get_contact_model()
Organisation = get_organisation_model()
Activity = get_activity_model()


class CTITestCase(CremeTestCase):
#    ADD_PCALL_URL = '/cti/add_phonecall'
    RESPOND_URL = '/cti/respond_to_a_call'

    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls.populate('creme_core', 'activities')
        #cls.autodiscover()

        cls.ADD_PCALL_URL = reverse('cti__create_phonecall_as_caller')

    def _buid_add_pcall_url(self, contact):
#        return '/cti/phonecall/add/%s' % contact.id
        return reverse('cti__create_phonecall', args=(contact.id,))

    def login(self):
        user = super(CTITestCase, self).login()

        other_user = self.other_user
        #create_contact = partial(Contact.objects.create, user=user)
        #self.contact = create_contact(is_user=user, first_name='Rally', last_name='Vincent')
        #self.contact_other_user = create_contact(is_user=other_user, first_name='Bean', last_name='Bandit')
        self.contact = user.linked_contact
        self.contact_other_user = other_user.linked_contact

        return user

    def test_config(self):
        "Should not ne available when creating UserRoles"
        self.login()

        response = self.assertGET200('/creme_config/role/add/')

        with self.assertNoException():
            fields = response.context['form'].fields
            apps_choices  = set(c[0] for c in fields['allowed_apps'].choices)
            admin_choices = set(c[0] for c in fields['admin_4_apps'].choices)

        self.assertIn('creme_core', apps_choices)
        self.assertIn('persons',    apps_choices)
        self.assertNotIn('cti',    apps_choices) #<==

        self.assertIn('creme_core', admin_choices)
        self.assertIn('persons',    admin_choices)
        self.assertNotIn('cti',    admin_choices) #<==

    def test_print_phone(self):
        user = self.login()

        get_html_val = field_printers_registry.get_html_field_value
        get_csv_val  = field_printers_registry.get_csv_field_value

        contact = self.contact
        self.assertEqual('', get_html_val(contact, 'phone', user))
        self.assertEqual('', get_csv_val(contact,  'phone', user))

        contact.phone = '112233'
        self.assertEqual(contact.phone, get_csv_val(contact, 'phone', user))

        html = get_html_val(contact, 'phone', user)
        self.assertIn(contact.phone, html)
        self.assertIn('<a onclick="creme.cti.phoneCall', html)

    @skipIfCustomContact
    def test_add_phonecall01(self):
        user = self.login()

        atype = self.get_object_or_fail(ActivityType, pk=ACTIVITYTYPE_PHONECALL)
        self.assertTrue(ActivitySubType.objects.filter(type=atype).exists())
        self.assertFalse(Activity.objects.filter(type=atype).exists())

        contact = Contact.objects.create(user=user, first_name='Bean', last_name='Bandit')
        self.assertPOST200(self.ADD_PCALL_URL, data={'entity_id': contact.id})

        pcalls = Activity.objects.filter(type=atype)
        self.assertEqual(1, len(pcalls))

        pcall = pcalls[0]
        self.assertEqual(user, pcall.user)
        self.assertIn(unicode(contact), pcall.title)
        self.assertTrue(pcall.description)
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_OUTGOING, pcall.sub_type.id)
        self.assertEqual(STATUS_IN_PROGRESS, pcall.status.id)
        self.assertDatetimesAlmostEqual(now(), pcall.start)
        self.assertEqual(timedelta(minutes=5), (pcall.end - pcall.start))

        self.assertRelationCount(1, self.contact, REL_SUB_PART_2_ACTIVITY, pcall)
        self.assertRelationCount(1, contact,      REL_SUB_PART_2_ACTIVITY, pcall)

        calendar = Calendar.get_user_default_calendar(user)
        self.assertTrue(pcall.calendars.filter(pk=calendar.id).exists())

    @skipIfCustomActivity
    def test_add_phonecall02(self):
        "No contact"
        self.login()

        self.assertPOST404(self.ADD_PCALL_URL, data={'entity_id': '1024'})
        self.assertFalse(Activity.objects.filter(type=ACTIVITYTYPE_PHONECALL).exists())

    @skipIfCustomOrganisation
    def test_add_phonecall03(self):
        "Organisation"
        user = self.login()

        orga = Organisation.objects.create(user=user, name='Gunsmith Cats')
        self.assertPOST200(self.ADD_PCALL_URL, data={'entity_id': orga.id})

        pcalls = Activity.objects.filter(type=ACTIVITYTYPE_PHONECALL)
        self.assertEqual(1, len(pcalls))

        pcall = pcalls[0]
        self.assertRelationCount(0, orga, REL_SUB_PART_2_ACTIVITY,   pcall)
        self.assertRelationCount(1, orga, REL_SUB_LINKED_2_ACTIVITY, pcall)

    @skipIfCustomContact
    def test_respond_to_a_call01(self):
        user = self.login()

        phone = '558899'
        contact = Contact.objects.create(user=user, first_name='Bean', last_name='Bandit', phone=phone)

        response = self.assertGET200(self.RESPOND_URL, data={'number': phone})
        self.assertTemplateUsed(response, 'cti/respond_to_a_call.html')

        with self.assertNoException():
            callers = response.context['callers']

        self.assertEqual(1, len(callers))
        self.assertEqual(contact.id, callers[0].id)

    @skipIfCustomContact
    def test_respond_to_a_call02(self):
        user = self.login()

        phone = '558899'
        contact = Contact.objects.create(user=user, first_name='Bean', last_name='Bandit', mobile=phone)
        response = self.assertGET200(self.RESPOND_URL, data={'number': phone})
        self.assertEqual([contact.id], [c.id for c in response.context['callers']])

    @skipIfCustomOrganisation
    def test_respond_to_a_call03(self):
        user = self.login()

        phone = '558899'
        orga = Organisation.objects.create(user=user, name='Gunsmith Cats', phone=phone)
        response = self.client.get(self.RESPOND_URL, data={'number': phone})
        self.assertEqual([orga.id], [o.id for o in response.context['callers']])

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_respond_to_a_call04(self):
        """FieldsConfig"""
        self.login()

        fc_create= FieldsConfig.create
        fc_create(Contact,
                  descriptions=[('phone',  {FieldsConfig.HIDDEN: True}),
                                ('mobile', {FieldsConfig.HIDDEN: True}),
                               ]
                 )
        fc_create(Organisation,
                  descriptions=[('phone', {FieldsConfig.HIDDEN: True})]
                 )

        self.assertGET409(self.RESPOND_URL, data={'number': '558899'})

    @skipIfCustomContact
    def test_respond_to_a_call05(self):
        """All fields are hidden"""
        user = self.login()

        FieldsConfig.create(Contact,
                            descriptions=[('phone', {FieldsConfig.HIDDEN: True})]
                           )

        phone='558899'
        Contact.objects.create(user=user, first_name='Bean', last_name='Bandit')
        response = self.assertGET200(self.RESPOND_URL, data={'number': phone})


    @skipIfCustomContact
    def test_create_contact(self):
        user = self.login()

        phone = '121366'
#        url = '/cti/contact/add/%s' % phone
        url = reverse('cti__create_contact', args=(phone,))
        response = self.assertGET200(url)

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(phone, form.initial.get('phone'))

        self.assertNoFormError(self.client.post(url, follow=True,
                                                data={'user':       user.id,
                                                      'first_name': 'Minnie',
                                                      'last_name':  'May',
                                                      'phone':      phone,
                                                     }
                                               )
                              )
        self.get_object_or_fail(Contact, phone=phone)

    @skipIfCustomOrganisation
    def test_create_orga(self):
        user = self.login()

        phone = '987654'
#        url = '/cti/organisation/add/%s' % phone
        url = reverse('cti__create_organisation', args=(phone,))
        response = self.assertGET200(url)

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(phone, form.initial.get('phone'))

        self.assertNoFormError(self.client.post(url, follow=True,
                                                data={'user':  user.id,
                                                      'name':  'Gunsmith cats',
                                                      'phone': phone,
                                                     }
                                               )
                              )
        self.get_object_or_fail(Organisation, phone=phone)

    @skipIfCustomContact
    @skipIfCustomActivity
    def test_create_phonecall01(self):
        user = self.login()

        contact = Contact.objects.create(user=user, first_name='Bean', last_name='Bandit')
        self.assertPOST(302, self._buid_add_pcall_url(contact))

        pcalls = Activity.objects.filter(type=ACTIVITYTYPE_PHONECALL)
        self.assertEqual(1, len(pcalls))

        pcall = pcalls[0]
        self.assertEqual(user, pcall.user)
        self.assertIn(unicode(contact), pcall.title)
        self.assertTrue(pcall.description)
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_INCOMING, pcall.sub_type.id)
        self.assertEqual(STATUS_IN_PROGRESS,                 pcall.status.id)
        self.assertDatetimesAlmostEqual(now(), pcall.start)
        self.assertEqual(timedelta(minutes=5), (pcall.end - pcall.start))

        self.assertRelationCount(1, self.contact, REL_SUB_PART_2_ACTIVITY, pcall)
        self.assertRelationCount(1, contact,      REL_SUB_PART_2_ACTIVITY, pcall)

        calendar = Calendar.get_user_default_calendar(user)
        self.assertTrue(pcall.calendars.filter(pk=calendar.id).exists())

    @skipIfCustomActivity
    def test_create_phonecall02(self):
        user = self.login()

        self.assertPOST(302, self._buid_add_pcall_url(self.contact))

        activities = Activity.objects.all()
        self.assertEqual(1, len(activities))

        phone_call = activities[0]
        self.assertRelationCount(1, self.contact, REL_SUB_PART_2_ACTIVITY, phone_call)

        calendar = Calendar.get_user_default_calendar(user)
        self.assertTrue(phone_call.calendars.filter(pk=calendar.id).exists())

    @skipIfCustomActivity
    def test_create_phonecall03(self):
        user = self.login()

        self.assertPOST(302, self._buid_add_pcall_url(self.contact_other_user))

        self.assertEqual(1, Activity.objects.count())

        phone_call = Activity.objects.all()[0]
        self.assertRelationCount(1, self.contact,            REL_SUB_PART_2_ACTIVITY, phone_call)
        self.assertRelationCount(1, self.contact_other_user, REL_SUB_PART_2_ACTIVITY, phone_call)

        get_cal = Calendar.get_user_default_calendar
        filter_calendars = phone_call.calendars.filter
        self.assertTrue(filter_calendars(pk=get_cal(user).id).exists())
        self.assertTrue(filter_calendars(pk=get_cal(self.other_user).id).exists())
