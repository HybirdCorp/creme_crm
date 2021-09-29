# -*- coding: utf-8 -*-

from datetime import timedelta

from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.activities import constants as a_constants
from creme.activities import get_activity_model
from creme.activities.models import ActivitySubType, ActivityType, Calendar
from creme.activities.tests.base import skipIfCustomActivity
from creme.creme_core.gui.field_printers import field_printers_registry
from creme.creme_core.models import FieldsConfig
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.cti.bricks import CallersBrick
from creme.persons import get_contact_model, get_organisation_model
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

Contact = get_contact_model()
Organisation = get_organisation_model()
Activity = get_activity_model()


class CTITestCase(CremeTestCase, BrickTestCaseMixin):
    RESPOND_URL = reverse('cti__respond_to_a_call')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.ADD_PCALL_URL = reverse('cti__create_phonecall_as_caller')

    @staticmethod
    def _build_add_pcall_url(contact):
        return reverse('cti__create_phonecall', args=(contact.id,))

    def login(self, *args, **kwargs):
        user = super().login(*args, **kwargs)

        other_user = self.other_user
        self.contact = user.linked_contact
        self.contact_other_user = other_user.linked_contact

        return user

    def test_config(self):
        "Should not ne available when creating UserRoles."
        self.login()

        response = self.assertGET200(reverse('creme_config__create_role'))

        with self.assertNoException():
            app_labels = response.context['form'].fields['allowed_apps'].choices

        self.assertInChoices(
            value='creme_core', label=_('Core'), choices=app_labels,
        )
        self.assertInChoices(
            value='persons', label=_('Accounts and Contacts'), choices=app_labels,
        )
        self.assertNotInChoices(value='cti', choices=app_labels)  # <==

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
        self.assertIn('<a class="cti-phonecall" onclick="creme.cti.phoneCall', html)

    @skipIfCustomContact
    def test_add_phonecall01(self):
        user = self.login()

        atype = self.get_object_or_fail(ActivityType, pk=a_constants.ACTIVITYTYPE_PHONECALL)
        self.assertTrue(ActivitySubType.objects.filter(type=atype).exists())
        self.assertFalse(Activity.objects.filter(type=atype).exists())

        contact = Contact.objects.create(user=user, first_name='Bean', last_name='Bandit')
        self.assertPOST200(self.ADD_PCALL_URL, data={'entity_id': contact.id})

        pcalls = Activity.objects.filter(type=atype)
        self.assertEqual(1, len(pcalls))

        pcall = pcalls[0]
        self.assertEqual(user, pcall.user)
        self.assertIn(str(contact), pcall.title)
        self.assertTrue(pcall.description)
        self.assertEqual(a_constants.ACTIVITYSUBTYPE_PHONECALL_OUTGOING, pcall.sub_type.id)
        self.assertEqual(a_constants.STATUS_IN_PROGRESS, pcall.status.id)
        self.assertDatetimesAlmostEqual(now(), pcall.start)
        self.assertEqual(timedelta(minutes=5), (pcall.end - pcall.start))

        self.assertRelationCount(1, self.contact, a_constants.REL_SUB_PART_2_ACTIVITY, pcall)
        self.assertRelationCount(1, contact,      a_constants.REL_SUB_PART_2_ACTIVITY, pcall)

        calendar = Calendar.objects.get_default_calendar(user)
        self.assertTrue(pcall.calendars.filter(pk=calendar.id).exists())

    @skipIfCustomActivity
    def test_add_phonecall02(self):
        "No contact."
        self.login()

        self.assertPOST404(self.ADD_PCALL_URL, data={'entity_id': str(self.UNUSED_PK)})
        self.assertFalse(Activity.objects.filter(type=a_constants.ACTIVITYTYPE_PHONECALL))

    @skipIfCustomOrganisation
    def test_add_phonecall03(self):
        "Organisation."
        user = self.login()

        orga = Organisation.objects.create(user=user, name='Gunsmith Cats')
        self.assertPOST200(self.ADD_PCALL_URL, data={'entity_id': orga.id})

        pcalls = Activity.objects.filter(type=a_constants.ACTIVITYTYPE_PHONECALL)
        self.assertEqual(1, len(pcalls))

        pcall = pcalls[0]
        self.assertRelationCount(0, orga, a_constants.REL_SUB_PART_2_ACTIVITY,   pcall)
        self.assertRelationCount(1, orga, a_constants.REL_SUB_LINKED_2_ACTIVITY, pcall)

    @skipIfCustomContact
    def test_respond_to_a_call01(self):
        "Contact."
        user = self.login()

        phone = '558899'
        contact = Contact.objects.create(
            user=user, first_name='Bean', last_name='Bandit', phone=phone,
        )

        response = self.assertGET200(self.RESPOND_URL, data={'number': phone})
        self.assertTemplateUsed(response, 'cti/respond_to_a_call.html')

        get = response.context.get
        self.assertEqual(phone, get('number'))
        self.assertEqual(
            reverse('cti__reload_callers_brick', args=(phone,)),
            get('bricks_reload_url')
        )

        brick_id = CallersBrick.id_
        brick_node = self.get_brick_node(self.get_html_tree(response.content), brick_id)
        self.assertInstanceLink(brick_node, contact)
        self.assertNoInstanceLink(brick_node, user.linked_contact)

        # Reload
        response = self.assertGET200(reverse('cti__reload_callers_brick', args=(phone,)))
        content = response.json()
        self.assertIsList(content, length=1)

        sub_content = content[0]
        self.assertIsList(sub_content, length=2)
        self.assertEqual(brick_id, sub_content[0])

        l_brick_node = self.get_brick_node(self.get_html_tree(sub_content[1]), brick_id)
        self.assertInstanceLink(l_brick_node, contact)
        self.assertNoInstanceLink(l_brick_node, user.linked_contact)

    @skipIfCustomContact
    def test_respond_to_a_call02(self):
        "Contact's other field (mobile)."
        user = self.login()

        phone = '558899'
        contact = Contact.objects.create(
            user=user, first_name='Bean', last_name='Bandit', mobile=phone,
        )
        response = self.assertGET200(self.RESPOND_URL, data={'number': phone})
        self.assertContains(response, str(contact))
        self.assertNotContains(response, str(user.linked_contact))

    @skipIfCustomOrganisation
    def test_respond_to_a_call03(self):
        "Organisation."
        user = self.login()

        phone = '558899'
        orga1 = Organisation.objects.all()[0]
        orga2 = Organisation.objects.create(user=user, name='Gunsmith Cats', phone=phone)
        response = self.client.get(self.RESPOND_URL, data={'number': phone})
        self.assertContains(response, str(orga2))
        self.assertNotContains(response, str(orga1))

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_respond_to_a_call04(self):
        """FieldsConfig: all fields are hidden."""
        self.login()

        fc_create = FieldsConfig.objects.create
        fc_create(
            content_type=Contact,
            descriptions=[
                ('phone',  {FieldsConfig.HIDDEN: True}),
                ('mobile', {FieldsConfig.HIDDEN: True}),
            ],
        )
        fc_create(
            content_type=Organisation,
            descriptions=[('phone', {FieldsConfig.HIDDEN: True})],
        )

        self.assertGET409(self.RESPOND_URL, data={'number': '558899'})

    @skipIfCustomContact
    def test_respond_to_a_call05(self):
        """FieldsConfig: some fields are hidden."""
        user = self.login()

        FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('phone', {FieldsConfig.HIDDEN: True})],
        )

        phone = '558899'
        contact = Contact.objects.create(
            user=user, first_name='Bean', last_name='Bandit', phone=phone,
        )
        response = self.assertGET200(self.RESPOND_URL, data={'number': phone})
        self.assertNotContains(response, str(contact))

    @skipIfCustomContact
    def test_create_contact(self):
        user = self.login()

        phone = '121366'
        url = reverse('cti__create_contact', args=(phone,))
        response = self.assertGET200(url)
        self.assertTemplateUsed('persons/add_contact_form.html')

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(phone, form.initial.get('phone'))

        first_name = 'Minnie'
        last_name = 'May'
        self.assertNoFormError(self.client.post(
            url, follow=True,
            data={
                'user':       user.id,
                'first_name': first_name,
                'last_name':  last_name,
                'phone':      phone,
            },
        ))
        contact = self.get_object_or_fail(Contact, phone=phone)
        self.assertEqual(last_name,  contact.last_name)
        self.assertEqual(first_name, contact.first_name)

    @skipIfCustomOrganisation
    def test_create_orga(self):
        user = self.login()

        phone = '987654'
        url = reverse('cti__create_organisation', args=(phone,))
        response = self.assertGET200(url)

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(Organisation, form._meta.model)
        self.assertEqual(phone, form.initial.get('phone'))

        name = 'Gunsmith cats'
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user':  user.id,
                'name':  name,
                'phone': phone,
            },
        ))
        orga = self.get_object_or_fail(Organisation, phone=phone)
        self.assertEqual(name, orga.name)

    @skipIfCustomContact
    @skipIfCustomActivity
    def test_create_phonecall01(self):
        user = self.login()

        contact = Contact.objects.create(user=user, first_name='Bean', last_name='Bandit')
        self.assertPOST(302, self._build_add_pcall_url(contact))

        pcalls = Activity.objects.filter(type=a_constants.ACTIVITYTYPE_PHONECALL)
        self.assertEqual(1, len(pcalls))

        pcall = pcalls[0]
        self.assertEqual(user, pcall.user)
        self.assertIn(str(contact), pcall.title)
        self.assertTrue(pcall.description)
        self.assertEqual(a_constants.ACTIVITYSUBTYPE_PHONECALL_INCOMING, pcall.sub_type.id)
        self.assertEqual(a_constants.STATUS_IN_PROGRESS,                 pcall.status.id)
        self.assertDatetimesAlmostEqual(now(), pcall.start)
        self.assertEqual(timedelta(minutes=5), (pcall.end - pcall.start))

        self.assertRelationCount(1, self.contact, a_constants.REL_SUB_PART_2_ACTIVITY, pcall)
        self.assertRelationCount(1, contact,      a_constants.REL_SUB_PART_2_ACTIVITY, pcall)

        calendar = Calendar.objects.get_default_calendar(user)
        self.assertTrue(pcall.calendars.filter(pk=calendar.id).exists())

    @skipIfCustomActivity
    def test_create_phonecall02(self):
        user = self.login()

        self.assertPOST(302, self._build_add_pcall_url(self.contact))

        activities = Activity.objects.all()
        self.assertEqual(1, len(activities))

        phone_call = activities[0]
        self.assertRelationCount(1, self.contact, a_constants.REL_SUB_PART_2_ACTIVITY, phone_call)

        calendar = Calendar.objects.get_default_calendar(user)
        self.assertTrue(phone_call.calendars.filter(pk=calendar.id).exists())

    @skipIfCustomActivity
    def test_create_phonecall03(self):
        user = self.login()

        self.assertPOST(302, self._build_add_pcall_url(self.contact_other_user))

        self.assertEqual(1, Activity.objects.count())

        phone_call = Activity.objects.all()[0]
        self.assertRelationCount(
            1, self.contact, a_constants.REL_SUB_PART_2_ACTIVITY, phone_call,
        )
        self.assertRelationCount(
            1, self.contact_other_user, a_constants.REL_SUB_PART_2_ACTIVITY, phone_call,
        )

        get_cal = Calendar.objects.get_default_calendar
        filter_calendars = phone_call.calendars.filter
        self.assertTrue(filter_calendars(pk=get_cal(user).id).exists())
        self.assertTrue(filter_calendars(pk=get_cal(self.other_user).id).exists())
