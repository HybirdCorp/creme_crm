# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from functools import partial
from itertools import count

from dateutil.relativedelta import relativedelta
from django.urls import reverse
from django.utils.timezone import localtime, now
from django.utils.translation import gettext as _

from creme.activities.constants import (
    ACTIVITYSUBTYPE_PHONECALL_FAILED,
    ACTIVITYSUBTYPE_PHONECALL_OUTGOING,
    ACTIVITYTYPE_PHONECALL,
    FLOATING_TIME,
    NARROW,
    REL_SUB_ACTIVITY_SUBJECT,
    REL_SUB_PART_2_ACTIVITY,
    STATUS_CANCELLED,
    STATUS_DONE,
    STATUS_IN_PROGRESS,
    STATUS_PLANNED,
)
from creme.activities.models import Calendar
from creme.activities.tests.base import skipIfCustomActivity
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import Relation, SetCredentials
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from .base import Activity, Contact, MobileBaseTestCase, Organisation


class MobileActivitiesTestCase(MobileBaseTestCase):
    ACTIVITIES_PORTAL_URL = reverse('mobile__activities')
    PCALL_PANEL_URL       = reverse('mobile__pcall_panel')

    WF_FAILED_URL     = reverse('mobile__pcall_wf_failed')
    WF_POSTPONED_URL  = reverse('mobile__pcall_wf_postponed')
    WF_LASTED5MIN_URL = reverse('mobile__pcall_wf_lasted_5_minutes')
    WF_JUSTDONE_URL   = reverse('mobile__pcall_wf_just_done')

    @staticmethod
    def _build_start_url(activity):
        return reverse('mobile__start_activity', args=(activity.id,))

    @staticmethod
    def _build_stop_url(activity):
        return reverse('mobile__stop_activity', args=(activity.id,))

    @staticmethod
    def _existing_pcall_ids():
        return [
            *Activity.objects
                     .filter(type=ACTIVITYTYPE_PHONECALL)
                     .values_list('id', flat=True),
        ]

    def _get_created_pcalls(self, existing_pcall_ids):
        with self.assertNoException():
            return Activity.objects.filter(
                type=ACTIVITYTYPE_PHONECALL,
            ).exclude(id__in=existing_pcall_ids)

    def _get_created_pcall(self, existing_pcall_ids):
        with self.assertNoException():
            return self._get_created_pcalls(existing_pcall_ids).get()

    @skipIfCustomActivity
    def test_start_activity01(self):
        "Start & end are past."
        self.login()

        meeting = self._create_meeting(
            'Meeting#1',
            participant=self.user.linked_contact,
            start=now() - timedelta(hours=2),
        )

        url = self._build_start_url(meeting)
        # self.assertGET404(url)
        self.assertGET405(url)

        response = self.assertPOST200(url, follow=True)
        meeting = self.refresh(meeting)
        self.assertDatetimesAlmostEqual(now(), meeting.start)
        self.assertEqual(meeting.type.as_timedelta(), meeting.end - meeting.start)
        self.assertEqual(STATUS_IN_PROGRESS, meeting.status_id)

        self.assertRedirects(
            response, reverse('mobile__portal') + f'#activity_{meeting.id}',
        )

    @skipIfCustomActivity
    def test_start_activity02(self):
        "Start & end are in the future."
        self.login()

        meeting = self._create_meeting(
            'Meeting#1',
            participant=self.user.linked_contact,
            start=now() + timedelta(minutes=30),
        )
        old_end = self.refresh(meeting).end  # NB: MySQL does not record milliseconds...

        self.assertPOST200(self._build_start_url(meeting), follow=True)

        meeting = self.refresh(meeting)
        self.assertDatetimesAlmostEqual(now(), meeting.start)
        self.assertGreater(meeting.end, meeting.start)
        self.assertEqual(old_end, meeting.end)

    @skipIfCustomActivity
    def test_start_activity03(self):
        "Floating time activity."
        user = self.login()
        now_val = now()

        def today(hour=14, minute=0):
            return datetime(
                year=now_val.year, month=now_val.month, day=now_val.day,
                hour=hour, minute=minute,
                tzinfo=now_val.tzinfo,
            )

        end = today(23, 59)
        meeting = self._create_meeting(
            'Meeting#1',
            participant=user.linked_contact,
            start=today(0, 0),
            end=end,
            floating_type=FLOATING_TIME,
        )

        self.assertPOST200(self._build_start_url(meeting), follow=True)

        meeting = self.refresh(meeting)
        self.assertDatetimesAlmostEqual(now(), meeting.start)
        self.assertEqual(end, meeting.end)
        self.assertEqual(NARROW, meeting.floating_type)

    @skipIfCustomActivity
    def test_start_activity04(self):
        "Floating activity."
        user = self.login()

        f_act = self._create_floating('Floating#1', participant=user.linked_contact)

        self.assertPOST200(self._build_start_url(f_act), follow=True)

        f_act = self.refresh(f_act)
        self.assertDatetimesAlmostEqual(now(), f_act.start)
        self.assertEqual(f_act.type.as_timedelta(), f_act.end - f_act.start)
        self.assertEqual(NARROW, f_act.floating_type)

    @skipIfCustomActivity
    def test_start_activity05(self):
        "Not allowed."
        self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            set_type=SetCredentials.ESET_ALL,
            value=(
                EntityCredentials.VIEW
                # | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
        )

        meeting = self._create_meeting(
            'Meeting#1',
            participant=self.user.linked_contact,
            start=now() + timedelta(minutes=30),
        )
        self.assertPOST403(self._build_start_url(meeting), follow=True)

    @skipIfCustomActivity
    def test_start_activity06(self):
        "Not super-user."
        self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            set_type=SetCredentials.ESET_ALL,
            value=EntityCredentials.CHANGE,
        )

        meeting = self._create_meeting(
            'Meeting#1',
            participant=self.user.linked_contact,
            start=now() + timedelta(minutes=30),
        )
        self.assertPOST200(self._build_start_url(meeting), follow=True)

    @skipIfCustomActivity
    def test_stop_activity01(self):
        user = self.login()

        meeting = self._create_meeting(
            'Meeting#1',
            participant=user.linked_contact,
            start=now() - timedelta(minutes=30),
        )

        url = self._build_stop_url(meeting)
        self.assertGET405(url)

        response = self.assertPOST200(url, follow=True)
        meeting = self.refresh(meeting)
        self.assertEqual(STATUS_DONE, meeting.status_id)
        self.assertDatetimesAlmostEqual(now(), meeting.end)

        self.assertRedirects(response, self.PORTAL_URL)

    @skipIfCustomActivity
    def test_stop_activity02(self):
        "Start is in the future => error"
        user = self.login()

        meeting = self._create_meeting(
            'Meeting#1',
            participant=user.linked_contact,
            start=now() + timedelta(minutes=30),
        )
        self.assertPOST409(self._build_stop_url(meeting))

    @skipIfCustomActivity
    def test_stop_activity03(self):
        "Not allowed."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            set_type=SetCredentials.ESET_ALL,
            value=(
                EntityCredentials.VIEW
                # | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
        )

        meeting = self._create_meeting(
            'Meeting#1',
            participant=user.linked_contact,
            start=now() - timedelta(minutes=30),
        )
        self.assertPOST403(self._build_stop_url(meeting))

    @skipIfCustomActivity
    def test_stop_activity04(self):
        "Not super-user."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            set_type=SetCredentials.ESET_ALL,
            value=EntityCredentials.CHANGE,
        )

        meeting = self._create_meeting(
            'Meeting#1',
            participant=user.linked_contact,
            start=now() - timedelta(minutes=30),
        )
        self.assertPOST200(self._build_stop_url(meeting), follow=True)

    @skipIfCustomActivity
    def test_activities_portal01(self):
        user = self.login()
        contact = user.linked_contact
        other_contact = self.other_user.linked_contact

        now_val = now()
        yesterday = now_val - timedelta(days=1)

        # Phone calls ----------------------------------------------------------
        i = count(1)

        def create_pc(participant=contact, **kwargs):
            return self._create_pcall(
                title=f'Pcall#{next(i)}', participant=participant, **kwargs
            )

        pc1 = create_pc(start=yesterday, status_id=STATUS_PLANNED)
        pc2 = create_pc(start=now_val - timedelta(hours=25))  # Older than pc1 -> before
        create_pc(start=yesterday, status_id=STATUS_DONE)  # Done -> excluded
        create_pc(start=yesterday, status_id=STATUS_CANCELLED)  # Cancelled -> excluded
        create_pc(
            start=yesterday, status_id=STATUS_PLANNED,
            participant=other_contact,
        )  # I do not participate
        tom1 = create_pc(
            start=now_val + timedelta(days=1, hours=0 if now_val.hour >= 1 else 1),
            status_id=STATUS_PLANNED,
        )  # Tomorrow

        expected_pcalls = [
            pc2, pc1,
            *(
                create_pc(
                    start=now_val - timedelta(hours=23, minutes=60 - minute),
                    participant=contact,
                ) for minute in range(1, 9)
            ),
        ]

        create_pc(start=now_val - timedelta(hours=23, minutes=7))  # Already 10 PhoneCalls

        # Floating activities --------------------------------------------------
        create_floating = self._create_floating

        f1 = create_floating('Floating B', contact)
        f2 = create_floating('Floating A', contact)
        f3 = create_floating('Floating C', contact)
        create_floating('Floating #4', other_contact)  # I do not participate
        create_floating('Floating #5', contact, status_id=STATUS_DONE)
        create_floating('Floating #6', contact, status_id=STATUS_CANCELLED)

        # Tomorrow activities --------------------------------------------------
        create_m = partial(
            self._create_meeting, participant=contact,
            start=now_val + timedelta(hours=23 if now_val.hour >= 1 else 24),
        )
        tom2 = create_m('Meeting #1')
        create_m('Meeting #2', participant=other_contact)
        create_m('Meeting #3', start=now_val + timedelta(days=2))

        # Assertions -----------------------------------------------------------
        response = self.assertGET200(self.ACTIVITIES_PORTAL_URL)
        self.assertTemplateUsed(response, 'mobile/activities.html')

        with self.assertNoException():
            context = response.context
            pcalls       = [*context['phone_calls']]
            factivities  = [*context['floating_activities']]
            tomorrow_act = [*context['tomorrow_activities']]
            fact_count   = context['floating_activities_count']

        self.assertEqual(expected_pcalls, pcalls)
        self.assertContains(response, pc1.title)

        self.assertEqual([f2, f1, f3], factivities)
        self.assertContains(response, f2.title)
        self.assertEqual(3, fact_count)

        self.assertEqual([tom2, tom1], tomorrow_act)
        self.assertContains(response, tom2.title)

    @skipIfCustomActivity
    def test_activities_portal02(self):
        "Floating count when truncated."
        user = self.login()
        contact1 = user.linked_contact
        contact2 = self.other_user.linked_contact

        create_floating = partial(self._create_floating, participant=contact1)
        for i in range(1, 32):
            activity = create_floating('Floating %i' % i)
            # TODO: improve self._create_floating for several participants
            # several participants, because the template does not display 'me'
            # (user.linked_contact)
            Relation.objects.create(
                subject_entity=contact2, user=user,
                type_id=REL_SUB_PART_2_ACTIVITY,
                object_entity=activity,
            )

        response = self.assertGET200(self.ACTIVITIES_PORTAL_URL)
        self.assertTemplateUsed(response, 'mobile/activities.html')

        with self.assertNoException():
            context = response.context
            factivities = context['floating_activities']
            fact_count  = context['floating_activities_count']

        self.assertEqual(30, len(factivities))
        self.assertEqual(31, fact_count)

    @skipIfCustomContact
    def test_phone_call_panel01(self):
        "Create with the number of a contact."
        user = self.login()

        url = self.PCALL_PANEL_URL
        self.assertGET404(url)

        gally = Contact.objects.create(user=user, first_name='Gally', last_name='Alita')
        phone = '4546465'
        response = self.assertGET200(
            url,
            data={
                'call_start': '2014-04-17T16:18:05.0Z',
                'person_id':  gally.id,
                'number':     phone,
            },
        )
        self.assertTemplateUsed(response, 'mobile/workflow_panel.html')

        with self.assertNoException():
            context = response.context
            type_id    = context['type_id']
            call_start = context['call_start']
            contact    = context['called_contact']
            number     = context['number']
            contacts   = context['participant_contacts']
            user_contact_id = context['user_contact_id']

        self.assertEqual(ACTIVITYTYPE_PHONECALL, type_id)
        self.assertEqual(
            self.create_datetime(
                utc=True,
                year=2014, month=4, day=17,
                hour=16, minute=18, second=5,
            ),
            call_start
        )
        self.assertEqual(gally, contact)
        self.assertNotIn('called_orga', context)
        self.assertNotIn('phone_call', context)
        self.assertEqual(phone, number)
        self.assertEqual([gally], contacts)
        self.assertNotIn('participant_organisations', context)
        self.assertEqual(self.user.linked_contact.id, user_contact_id)

    @skipIfCustomOrganisation
    def test_phone_call_panel02(self):
        "Create with the number of an organisation."
        user = self.login()

        zalem = Organisation.objects.create(user=user, name='Zalem')
        mobile = '896255'
        response = self.assertGET200(
            self.PCALL_PANEL_URL,
            data={
                'call_start': '2014-04-18T16:18:05.0Z',
                'person_id':  zalem.id,
                'number':     mobile,
            },
        )

        with self.assertNoException():
            context = response.context
            orga    = context['called_orga']
            orgas   = context['participant_organisations']

        self.assertEqual(
            self.create_datetime(
                utc=True,
                year=2014, month=4, day=18,
                hour=16, minute=18, second=5,
            ),
            context['call_start']
        )
        self.assertNotIn('called_contact', context)
        self.assertEqual(zalem, orga)
        self.assertNotIn('phone_call', context)
        self.assertEqual(mobile, context['number'])
        self.assertNotIn('participant_contacts', context)
        self.assertListEqual([zalem], orgas)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    @skipIfCustomActivity
    def test_phone_call_panel03(self):
        "Update an existing phone call."
        user = self.login()
        contact = user.linked_contact

        pcall = self._create_pcall('Phone call#1', participant=contact)

        gally = Contact.objects.create(user=user, first_name='Gally', last_name='Alita')

        create_orga = partial(Organisation.objects.create, user=user)
        zalem = create_orga(name='Zalem')
        kuzu  = create_orga(name='Kuzutetsu')

        create_rel = partial(Relation.objects.create, user=user, object_entity=pcall)
        create_rel(subject_entity=gally, type_id=REL_SUB_PART_2_ACTIVITY)
        # TODO: subject -> participate ?
        create_rel(subject_entity=kuzu, type_id=REL_SUB_ACTIVITY_SUBJECT)

        response = self.assertGET200(
            self.PCALL_PANEL_URL,
            data={
                'call_start': '2014-04-18T16:18:05.0Z',
                'pcall_id':   pcall.id,
                'person_id':  zalem.id,
                'number':     '896255',
            },
        )

        with self.assertNoException():
            context    = response.context
            phone_call = context['phone_call']
            orga       = context['called_orga']
            contacts   = context['participant_contacts']
            orgas      = context['participant_organisations']

        self.assertEqual(pcall, phone_call)
        self.assertNotIn('called_contact', context)
        self.assertEqual(zalem, orga)
        self.assertSetEqual({gally, contact}, {*contacts})
        self.assertListEqual([kuzu], orgas)

    @skipIfCustomOrganisation
    @skipIfCustomActivity
    def test_phone_call_panel04(self):
        "Not allowed."
        user = self.login(is_superuser=False)

        pcall = self._create_pcall('Phone call#1', participant=user.linked_contact)
        zalem = Organisation.objects.create(user=user, name='Zalem')
        self.assertGET403(
            self.PCALL_PANEL_URL,
            data={
                'call_start': '2014-04-18T16:18:05.0Z',
                'pcall_id':   pcall.id,
                'person_id':  zalem.id,
                'number':     '896255',
            },
        )

    @skipIfCustomOrganisation
    @skipIfCustomActivity
    def test_phone_call_panel05(self):
        "Not super-user."
        user = self.login(is_superuser=False)

        create_sc = partial(
            SetCredentials.objects.create,
            role=self.role,
            set_type=SetCredentials.ESET_ALL,
            value=EntityCredentials.VIEW,
        )
        create_sc(ctype=Activity)
        create_sc(ctype=Organisation)

        pcall = self._create_pcall('Phone call#1', participant=user.linked_contact)
        zalem = Organisation.objects.create(user=user, name='Zalem')
        self.assertGET200(
            self.PCALL_PANEL_URL,
            data={
                'call_start': '2014-04-18T16:18:05.0Z',
                'pcall_id':   pcall.id,
                'person_id':  zalem.id,
                'number':     '896255',
            },
        )

    @skipIfCustomActivity
    def test_phone_call_wf_done01(self):
        user = self.login()
        contact = user.linked_contact

        pcall = self._create_pcall('Phone call#1', participant=contact)

        url = reverse('mobile__pcall_wf_done', args=(pcall.id,))
        # self.assertGET404(url)
        self.assertGET405(url)

        response = self.assertPOST200(url, follow=True)
        self.assertEqual(STATUS_DONE, self.refresh(pcall).status_id)

        self.assertRedirects(response, self.PORTAL_URL)  # TODO: test with other REFERRER

        # ------
        meeting = self._create_meeting('Meeting#1', participant=contact)
        self.assertPOST404(reverse('mobile__pcall_wf_done', args=(meeting.id,)))

    @skipIfCustomActivity
    def test_phone_call_wf_done02(self):
        "Not allowed."
        user = self.login(is_superuser=False)
        pcall = self._create_pcall('Phone call#1', participant=user.linked_contact)
        self.assertPOST403(
            reverse('mobile__pcall_wf_done', args=(pcall.id,)),
            follow=True,
        )

    @skipIfCustomActivity
    def test_phone_call_wf_done03(self):
        "Not usper-user."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            set_type=SetCredentials.ESET_ALL,
            value=EntityCredentials.CHANGE,
            ctype=Activity,
        )

        pcall = self._create_pcall('Phone call#1', participant=user.linked_contact)
        self.assertPOST200(
            reverse('mobile__pcall_wf_done', args=(pcall.id,)),
            follow=True,
        )

    @skipIfCustomActivity
    def test_phone_call_wf_failed01(self):
        "Existing Phone call (with no minutes)."
        user = self.login()

        pcall = self._create_pcall(
            'Phone call#1',
            status_id=STATUS_PLANNED, participant=user.linked_contact,
        )

        url = self.WF_FAILED_URL
        # self.assertGET404(url)
        self.assertGET405(url)

        minutes = 'argg'
        self.assertPOST200(
            url,
            data={
                'pcall_id':   str(pcall.id),
                'call_start': '2014-04-22T16:34:28.0Z',
                'minutes':    minutes,
            },
        )

        pcall = self.refresh(pcall)
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_FAILED, pcall.sub_type_id)
        self.assertEqual(STATUS_DONE,                      pcall.status_id)
        self.assertEqual(minutes,                          pcall.minutes)

        start = self.create_datetime(
            utc=True, year=2014, month=4, day=22, hour=16, minute=34, second=28,
        )
        self.assertEqual(start, pcall.start)
        self.assertEqual(start, pcall.end)

    @skipIfCustomActivity
    def test_phone_call_wf_failed02(self):
        "Not a Phone call => error."
        user = self.login()

        meeting = self._create_meeting('Meeting#1', participant=user.linked_contact)
        self.assertPOST404(self.WF_FAILED_URL, data={'pcall_id': meeting.id})

    @skipIfCustomActivity
    def test_phone_call_wf_failed03(self):
        "Phone call is created (with contact)."
        user = self.login()
        other_contact = self.other_user.linked_contact

        pcall_ids = self._existing_pcall_ids()

        minutes = 'dammit'
        self.assertPOST200(
            self.WF_FAILED_URL,
            data={
                'call_start': '2014-04-18T16:17:28.0Z',
                'person_id':  str(other_contact.id),
                'minutes':    minutes,
            },
        )

        pcall = self._get_created_pcall(pcall_ids)
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_FAILED, pcall.sub_type_id)
        self.assertEqual(STATUS_DONE,                      pcall.status_id)
        self.assertEqual(minutes,                          pcall.minutes)
        self.assertSetEqual(
            {user.linked_contact, other_contact},
            {
                r.object_entity.get_real_entity()
                for r in pcall.get_participant_relations()
            },
        )

        start = self.create_datetime(
            utc=True, year=2014, month=4, day=18, hour=16, minute=17, second=28,
        )
        self.assertEqual(start, pcall.start)
        self.assertEqual(start, pcall.end)

        self.assertEqual(
            _('{status} call to {person} from Creme Mobile').format(
                status=_('Failed'),
                person=other_contact,
            ),
            pcall.title,
        )

        get_cal = Calendar.objects.get_default_calendar
        self.assertSetEqual(
            {get_cal(user), get_cal(self.other_user)}, {*pcall.calendars.all()}
        )

    def test_phone_call_wf_failed04(self):
        "Second participant == first participant."
        user = self.login()
        self.assertPOST409(
            self.WF_FAILED_URL,
            data={
                'call_start': '2014-04-18T16:17:28.0Z',
                'person_id':  str(user.linked_contact.id),
            },
        )

    @skipIfCustomOrganisation
    def test_phone_call_wf_failed05(self):
        "Phone call is created (with organisation)."
        user = self.login()
        pcall_ids = self._existing_pcall_ids()

        kuzu = Organisation.objects.create(user=user, name='Kuzutetsu')
        self.assertPOST200(
            self.WF_FAILED_URL,
            data={
                'call_start': '2014-04-18T16:17:28.0Z',
                'person_id':  kuzu.id,
            },
        )

        pcall = self._get_created_pcall(pcall_ids)
        self.assertListEqual(
            [user.linked_contact],
            [
                r.object_entity.get_real_entity()
                for r in pcall.get_participant_relations()
            ],
        )
        self.assertListEqual(
            [kuzu],
            [
                r.object_entity.get_real_entity()
                for r in pcall.get_subject_relations()
            ],
        )

    @skipIfCustomActivity
    def test_phone_call_wf_postponed01(self):
        self.login()

        contact = self.user.linked_contact
        pcall = self._create_pcall(
            'Phone call#1',
            status_id=STATUS_PLANNED,
            participant=contact,
            description='blablabla',
            floating_type=FLOATING_TIME,
        )

        url = self.WF_POSTPONED_URL
        self.assertGET405(url)

        pcall_ids = self._existing_pcall_ids()
        self.assertPOST200(
            url,
            data={
                'pcall_id':   pcall.id,
                'call_start': '2014-04-22T16:17:28.0Z',
            },
        )

        pcall = self.refresh(pcall)
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_FAILED, pcall.sub_type_id)
        self.assertEqual(STATUS_DONE,                      pcall.status_id)
        self.assertEqual(NARROW,                           pcall.floating_type)

        start = self.create_datetime(
            utc=True, year=2014, month=4, day=22, hour=16, minute=17, second=28,
        )
        self.assertEqual(start, pcall.start)
        self.assertEqual(start, pcall.end)

        pcall2 = self._get_created_pcall(pcall_ids)
        self.assertEqual(pcall.description, pcall2.description)
        self.assertRelationCount(1, contact, REL_SUB_PART_2_ACTIVITY, pcall)

        self.assertEqual(STATUS_PLANNED, pcall2.status_id)
        self.assertEqual(FLOATING_TIME,  pcall2.floating_type)

        tomorrow = (now() + relativedelta(days=1)).day

        start = localtime(pcall2.start)
        self.assertEqual(0, start.hour)
        self.assertEqual(0, start.minute)
        self.assertEqual(tomorrow, start.day)

        end = localtime(pcall2.end)
        self.assertEqual(23, end.hour)
        self.assertEqual(59, end.minute)
        self.assertEqual(tomorrow, end.day)

    @skipIfCustomContact
    def test_phone_call_wf_postponed02(self):
        "Phone calls are created (with contact)."
        user = self.login()
        pcall_ids = self._existing_pcall_ids()
        other_part = Contact.objects.create(
            user=user, first_name='Gally', last_name='Alita',
        )  # Not linked to a user -> (no linked Calendar)
        participants = {self.user.linked_contact, other_part}

        self.assertPOST200(
            self.WF_POSTPONED_URL,
            data={
                'call_start': '2014-04-22T11:54:28.0Z',
                'person_id':  other_part.id,
            },
        )

        pcalls = sorted(self._get_created_pcalls(pcall_ids), key=lambda c: c.id)
        self.assertEqual(2, len(pcalls))

        failed_pcall = pcalls[0]
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_FAILED, failed_pcall.sub_type_id)
        self.assertEqual(STATUS_DONE,                      failed_pcall.status_id)
        self.assertEqual(NARROW,                           failed_pcall.floating_type)
        self.assertSetEqual(
            participants,
            {
                r.object_entity.get_real_entity()
                for r in failed_pcall.get_participant_relations()
            },
        )
        self.assertEqual(
            _('{status} call to {person} from Creme Mobile').format(
                status=_('Failed'),
                person=other_part,
            ),
            failed_pcall.title,
        )

        start = self.create_datetime(
            utc=True, year=2014, month=4, day=22, hour=11, minute=54, second=28,
        )
        self.assertEqual(start, failed_pcall.start)
        self.assertEqual(start, failed_pcall.end)

        pp_pcall = pcalls[1]
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_OUTGOING, pp_pcall.sub_type_id)
        self.assertEqual(FLOATING_TIME,                      pp_pcall.floating_type)
        self.assertIsNone(pp_pcall.status_id)
        self.assertSetEqual(
            participants,
            {
                r.object_entity.get_real_entity()
                for r in pp_pcall.get_participant_relations()
            },
        )

        tomorrow = (now() + relativedelta(days=1)).day

        start = localtime(pp_pcall.start)
        self.assertEqual(0, start.hour)
        self.assertEqual(0, start.minute)
        self.assertEqual(tomorrow, start.day)

        end = localtime(pp_pcall.end)
        self.assertEqual(23, end.hour)
        self.assertEqual(59, end.minute)
        self.assertEqual(tomorrow, end.day)

        self.assertEqual(
            _('Call to {} from Creme Mobile').format(other_part),
            pp_pcall.title,
        )

    @skipIfCustomActivity
    def test_phone_call_wf_lasted5min01(self):
        user = self.login()

        pcall = self._create_pcall(
            'Phone call#1',
            status_id=STATUS_PLANNED, participant=user.linked_contact,
        )

        url = self.WF_LASTED5MIN_URL
        self.assertGET405(url)
        self.assertPOST200(
            url,
            data={
                'pcall_id':   pcall.id,
                'call_start': '2014-03-10T11:30:28.0Z',
            },
        )

        pcall = self.refresh(pcall)
        self.assertEqual(STATUS_DONE, pcall.status_id)

        create_dt = partial(
            self.create_datetime, utc=True, year=2014, month=3, day=10, hour=11,
        )
        self.assertEqual(create_dt(minute=30, second=28), pcall.start)
        self.assertEqual(create_dt(minute=35, second=28), pcall.end)
        self.assertEqual('', pcall.minutes)

    @skipIfCustomActivity
    def test_phone_call_wf_lasted5min02(self):
        "Bad date format."
        user = self.login()

        pcall = self._create_pcall(
            'Phone call#1',
            status_id=STATUS_PLANNED, participant=user.linked_contact,
        )
        self.assertPOST404(
            self.WF_LASTED5MIN_URL,
            data={
                'pcall_id':    pcall.id,
                'call_start': '10-03-2014 10:30:28',
            },
        )

    @skipIfCustomActivity
    def test_phone_call_wf_lasted5min03(self):
        "Phone call is created (with contact)."
        self.login()
        other_contact = self.other_user.linked_contact
        pcall_ids = self._existing_pcall_ids()

        minutes = 'Gotteferdom'
        self.assertPOST200(
            self.WF_LASTED5MIN_URL,
            data={
                'call_start': '2014-04-18T16:17:28.0Z',
                'person_id':  other_contact.id,
                'minutes':    minutes,
            },
        )

        pcall = self._get_created_pcall(pcall_ids)
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_OUTGOING, pcall.sub_type_id)
        self.assertEqual(STATUS_DONE, pcall.status_id)
        self.assertEqual(minutes, pcall.minutes)
        self.assertSetEqual(
            {self.user.linked_contact, other_contact},
            {
                r.object_entity.get_real_entity()
                for r in pcall.get_participant_relations()
            },
        )

        create_dt = partial(
            self.create_datetime, utc=True, year=2014, month=4, day=18, hour=16,
        )
        self.assertEqual(create_dt(minute=17, second=28), pcall.start)
        self.assertEqual(create_dt(minute=22, second=28), pcall.end)

        self.assertEqual(
            _('{status} call to {person} from Creme Mobile').format(
                status=_('Successful'),
                person=other_contact,
            ),
            pcall.title,
        )

    def test_phone_call_wf_lasted5min04(self):
        "Second participant == first participant."
        user = self.login()
        self.assertPOST409(
            self.WF_LASTED5MIN_URL,
            data={
                'call_start': '2014-04-18T16:17:28.0Z',
                'person_id':  user.linked_contact.id,
            },
        )

    @skipIfCustomActivity
    def test_phone_call_wf_lasted5min05(self):
        "call_start + 5 minutes > now()"
        user = self.login()

        pcall = self._create_pcall(
            'Phone call#1', status_id=STATUS_PLANNED, participant=user.linked_contact,
        )

        start = now() - timedelta(minutes=2)
        self.assertPOST200(
            self.WF_LASTED5MIN_URL,
            data={
                'pcall_id':   pcall.id,
                'call_start': start.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),  # TODO: in utils ??
            },
        )

        pcall = self.refresh(pcall)
        self.assertEqual(STATUS_DONE, pcall.status_id)
        # NB: MySQL does not record milliseconds...
        self.assertDatetimesAlmostEqual(start, pcall.start)
        self.assertDatetimesAlmostEqual(now(), pcall.end)

    @skipIfCustomActivity
    def test_phone_call_wf_just_done01(self):
        user = self.login()
        contact = user.linked_contact

        pcall = self._create_pcall(
            'Phone call#1', status_id=STATUS_PLANNED, participant=contact,
        )

        url = self.WF_JUSTDONE_URL
        self.assertGET405(url)

        start = now() - timedelta(minutes=5)
        minutes = 'yata'
        self.assertPOST200(
            url,
            data={
                'pcall_id':   pcall.id,
                'call_start': start.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'minutes':    minutes,
            },
        )

        pcall = self.refresh(pcall)
        self.assertEqual(STATUS_DONE, pcall.status_id)
        self.assertEqual(minutes,     pcall.minutes)

        self.assertDatetimesAlmostEqual(start, pcall.start)
        self.assertDatetimesAlmostEqual(now(), pcall.end)

        # ------
        meeting = self._create_meeting('Meeting#1', participant=contact)
        self.assertPOST404(
            url,
            data={
                'pcall_id':   meeting.id,
                'call_start': start.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            },
        )

    @skipIfCustomActivity
    def test_phone_call_wf_just_done02(self):
        user = self.login()
        other_contact = self.other_user.linked_contact
        pcall_ids = self._existing_pcall_ids()

        start = now() - timedelta(minutes=5)
        self.assertPOST200(
            self.WF_JUSTDONE_URL,
            data={
                'call_start': start.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'person_id':  other_contact.id,
            },
        )

        pcall = self._get_created_pcall(pcall_ids)
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_OUTGOING, pcall.sub_type_id)
        self.assertEqual(STATUS_DONE, pcall.status_id)
        self.assertSetEqual(
            {user.linked_contact, other_contact},
            {
                r.object_entity.get_real_entity()
                for r in pcall.get_participant_relations()
            },
        )
        self.assertDatetimesAlmostEqual(start, pcall.start)
        self.assertDatetimesAlmostEqual(now(), pcall.end)

        self.assertEqual(
            _('{status} call to {person} from Creme Mobile').format(
                status=_('Successful'),
                person=other_contact,
            ),
            pcall.title
        )

    @skipIfCustomActivity
    def test_phone_call_wf_just_done03(self):
        "Concatenate old & new minutes."
        user = self.login()
        contact = user.linked_contact

        pcall = self._create_pcall(
            'Phone call#1',
            status_id=STATUS_PLANNED, participant=contact, minutes='Will be OK...',
        )

        start = now() - timedelta(minutes=5)
        self.assertPOST200(
            self.WF_JUSTDONE_URL,
            data={
                'pcall_id':   pcall.id,
                'call_start': start.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'minutes':    'noooooo !',
            },
        )

        pcall = self.refresh(pcall)
        self.assertEqual(STATUS_DONE, pcall.status_id)
        self.assertEqual(
            'Will be OK...\nnoooooo !', pcall.minutes,
        )
