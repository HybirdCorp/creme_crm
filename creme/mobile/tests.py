# -*- coding: utf-8 -*-

try:
    from datetime import datetime, timedelta
    from functools import partial
    from itertools import count
    from random import randint

    from django.conf import settings
    from django.contrib.auth.models import User
    from django.utils.timezone import now, localtime
    from django.utils.translation import ugettext as _

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.models import Relation
    #from creme.creme_core.utils.dates import make_aware_dt

    from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES
    from creme.persons.models import Contact, Organisation

    from creme.activities.constants import (NARROW, FLOATING_TIME, FLOATING,
            REL_SUB_PART_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT,
            STATUS_PLANNED, STATUS_IN_PROGRESS, STATUS_DONE, STATUS_CANCELLED,
            ACTIVITYTYPE_MEETING, ACTIVITYSUBTYPE_MEETING_NETWORK,
            ACTIVITYTYPE_PHONECALL,
            ACTIVITYSUBTYPE_PHONECALL_OUTGOING, ACTIVITYSUBTYPE_PHONECALL_FAILED)
    from creme.activities.models import Activity, Calendar

    from creme.mobile.models import MobileFavorite
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class MobileTestCase(CremeTestCase):
    PORTAL_URL              = '/mobile/'
    PERSONS_PORTAL_URL      = '/mobile/persons'
    CREATE_CONTACT_URL      = '/mobile/contact/add'
    CREATE_ORGA_URL         = '/mobile/organisation/add'
    SEARCH_PERSON_URL       = '/mobile/person/search'
    ACTIVITIES_PORTAL_URL   = '/mobile/activities'
    PCALL_PANEL_URL         = '/mobile/phone_call/panel'
    WF_FAILED_URL           = '/mobile/phone_call/failed'
    WF_POSTPONED_URL        = '/mobile/phone_call/postponed'
    WF_LASTED5MIN_URL       = '/mobile/phone_call/lasted_5_minutes'
    WF_JUSTDONE_URL         = '/mobile/phone_call/just_done'

    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls.populate('creme_config', 'persons', 'activities', 'mobile')

    def login(self, is_superuser=True, other_is_owner=False):
        super(MobileTestCase, self).login(is_superuser,
                                          allowed_apps=['activities', 'persons'],
                                         ) #'creme_core'

    def _build_start_url(self, activity):
        return '/mobile/activity/%s/start' % activity.id

    def _build_stop_url(self, activity):
        return '/mobile/activity/%s/stop' % activity.id

    def _create_floating(self, title, participant, status_id=None):
        activity = Activity.objects.create(user=self.user, title=title,
                                           type_id=ACTIVITYTYPE_MEETING,
                                           sub_type_id=ACTIVITYSUBTYPE_MEETING_NETWORK,
                                           status_id=status_id,
                                           floating_type=FLOATING,
                                          )

        Relation.objects.create(subject_entity=participant, user=self.user,
                                type_id=REL_SUB_PART_2_ACTIVITY,
                                object_entity=activity,
                               )

        return activity

    def _create_meeting(self, title, start=None, end=None, participant=None, status_id=None, **kwargs):
        if start is None:
            start = now()

        if end is None:
            end = start + timedelta(hours=1)

        activity = Activity.objects.create(user=self.user, title=title,
                                           type_id=ACTIVITYTYPE_MEETING,
                                           sub_type_id=ACTIVITYSUBTYPE_MEETING_NETWORK,
                                           status_id=status_id,
                                           start=start,
                                           end=end,
                                           **kwargs
                                          )

        if participant is not None:
            Relation.objects.create(subject_entity=participant, user=self.user,
                                    type_id=REL_SUB_PART_2_ACTIVITY,
                                    object_entity=activity,
                                   )

        return activity

    def _create_pcall(self, title, start=None, participant=None, status_id=None, **kwargs):
        if start is None:
            start = self.create_datetime(year=2014, month=1, day=6, hour=8) \
                        .replace(month=randint(1, 12))

        activity = Activity.objects.create(user=self.user, title=title,
                                           type_id=ACTIVITYTYPE_PHONECALL,
                                           sub_type_id=ACTIVITYSUBTYPE_PHONECALL_OUTGOING,
                                           status_id=status_id,
                                           start=start,
                                           end=start + timedelta(hours=1),
                                           **kwargs
                                          )

        if participant is not None:
            Relation.objects.create(subject_entity=participant, user=self.user,
                                    type_id=REL_SUB_PART_2_ACTIVITY,
                                    object_entity=activity,
                                   )

        return activity


    def _existing_pcall_ids(self):
        return list(Activity.objects.filter(type=ACTIVITYTYPE_PHONECALL)
                                    .values_list('id', flat=True)
                   )

    def _get_created_pcalls(self, existing_pcall_ids):
        with self.assertNoException():
            return Activity.objects.filter(type=ACTIVITYTYPE_PHONECALL) \
                                   .exclude(id__in=existing_pcall_ids)

    def _get_created_pcall(self, existing_pcall_ids):
        with self.assertNoException():
            return self._get_created_pcalls(existing_pcall_ids).get()

    def test_login(self):
      url = '/mobile/login/'
      response = self.assertGET200(url)
      self.assertTemplateUsed(response, 'mobile/login.html')

      with self.assertNoException():
          response.context['REDIRECT_FIELD_NAME']

      username = 'gally'
      password = 'passwd'
      User.objects.create_superuser(username, 'gally@zalem.org', password)

      response = self.assertPOST200(url, follow=True,
                                    data={'username': username,
                                          'password': password,
                                          'next':     self.PORTAL_URL,
                                         }
                                   )
      self.assertRedirects(response, self.PORTAL_URL)

    def test_logout(self):
        self.login()
        response = self.assertGET200('/mobile/logout/', follow=True)
        self.assertRedirects(response, settings.LOGIN_URL)

    def test_portal(self):
        self.login()
        contact = self.user.linked_contact
        #now_val = now()
        now_val = localtime(now())

        def today(hour=14, minute=0, second=0):
            #return make_aware_dt(datetime.combine(now_val, time(hour=hour, minute=minute)))
            return datetime(year=now_val.year, month=now_val.month, day=now_val.day,
                            hour=hour, minute=minute, second=second,
                            tzinfo=now_val.tzinfo
                           )

        past_midnight = today(0)

        def today_in_the_past(near):
            return now_val - (now_val - past_midnight) / near

        def today_in_the_future(near):
            return now_val + (today(23, 59, 59) - now_val) / near

        create_m = self._create_meeting
        m1 = create_m('Meeting: Manga',      start=today_in_the_past(3),   participant=contact)
        m2 = create_m('Meeting: Anime',      start=today_in_the_past(2),   participant=contact, status_id=STATUS_PLANNED)
        m3 = create_m('Meeting: Manga #2',   start=past_midnight,          participant=contact, floating_type=FLOATING_TIME)
        m4 = create_m('Meeting: Figures',    start=today_in_the_future(3), participant=contact, status_id=STATUS_IN_PROGRESS)
        m5 = create_m('Meeting: Figures #3', start=today_in_the_future(2), participant=contact) #should be after m6
        m6 = create_m('Meeting: Figures #2', start=today_in_the_future(3), participant=contact)

        oneday = timedelta(days=1)
        create_m('Meeting: Tezuka manga', start=today(9),         participant=self.other_user.linked_contact) #I do not participate
        create_m('Meeting: Comics',       start=today(7),         participant=contact, status_id=STATUS_DONE) #done are excluded
        create_m('Meeting: Manhua',       start=today(10),        participant=contact, status_id=STATUS_CANCELLED) #cancelled are excluded
        create_m('Meeting: Manga again',  start=now_val - oneday, participant=contact) #yesterday
        create_m('Meeting: Manga ter.',   start=now_val + oneday, participant=contact) #tomorrow

        response = self.assertGET200(self.PORTAL_URL)
        self.assertTemplateUsed(response, 'mobile/index.html')

        with self.assertNoException():
            context = response.context
            hot_activities   = list(context['hot_activities'])
            today_activities = list(context['today_activities'])

        self.assertEqual([m2, m1, m4], hot_activities)
        self.assertEqual([m3, m6, m5], today_activities)
        self.assertContains(response, m1.title)
        self.assertContains(response, m3.title)

    def test_persons(self):
        self.login()

        create_contact = partial(Contact.objects.create, user=self.user)
        may = create_contact(first_name='May',   last_name='Shiranui')
        joe = create_contact(first_name='Joe',   last_name='Higashi')
        terry = create_contact(first_name='Terry', last_name='Bogard')
        create_contact(first_name='Andy', last_name='Bogard')

        create_orga = partial(Organisation.objects.create, user=self.user)
        kof = create_orga(name='KingOfFighters')
        create_orga(name='Fatal fury')

        create_fav = partial(MobileFavorite.objects.create, user=self.user)
        create_fav(entity=may)
        create_fav(entity=joe)
        create_fav(entity=kof)
        create_fav(entity=terry, user=self.other_user)

        response = self.assertGET200(self.PERSONS_PORTAL_URL)
        self.assertTemplateUsed(response, 'mobile/directory.html')

        with self.assertNoException():
            contacts = set(response.context['favorite_contacts'])
            orgas    = list(response.context['favorite_organisations'])

        self.assertEqual({may, joe}, contacts)
        self.assertContains(response, may.last_name)
        self.assertContains(response, may.first_name)

        self.assertEqual([kof], orgas)
        self.assertContains(response, kof)

    def test_create_contact01(self):
        self.login()

        url = self.CREATE_CONTACT_URL
        self.assertGET200(url)

        kof = Organisation.objects.create(user=self.user, name='KOF')
        first_name = 'May'
        last_name = 'Shiranui'
        response = self.assertPOST200(url, follow=True,
                                      data={'first_name':   first_name,
                                            'last_name':    last_name,
                                            'organisation': kof.name,
                                           }
                                     )
        self.assertNoFormError(response)

        may = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertRelationCount(1, may, REL_SUB_EMPLOYED_BY, kof)
        self.assertFalse(self.user.mobile_favorite.all())

        self.assertRedirects(response, self.PERSONS_PORTAL_URL)

    def test_create_contact02(self):
        self.login()
        first_name = 'May'
        last_name = 'Shiranui'

        url = self.CREATE_CONTACT_URL
        arg = {'last_name': first_name}
        response = self.assertGET200(url, data=arg)
        self.assertEqual(arg, response.context['form'].initial)

        orga_name = 'KOF'
        self.assertFalse(Organisation.objects.filter(name=orga_name))

        phone = '111111'
        mobile = '222222'
        email = 'may.shiranui@kof.org'
        response = self.assertPOST200(url, follow=True,
                                      data={'first_name':   first_name,
                                            'last_name':    last_name,
                                            'organisation': orga_name,
                                            'phone':        phone,
                                            'mobile':       mobile,
                                            'email':        email,
                                            'is_favorite':  True,
                                           }
                                     )
        self.assertNoFormError(response)

        may = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertEqual(phone,  may.phone)
        self.assertEqual(mobile, may.mobile)
        self.assertEqual(email,  may.email)

        kof = self.get_object_or_fail(Organisation, name=orga_name)
        self.assertRelationCount(1, may, REL_SUB_EMPLOYED_BY, kof)

        self.assertEqual([may], list(f.entity.get_real_entity() for f in self.user.mobile_favorite.all()))

    def test_create_orga01(self):
        self.login()

        url = self.CREATE_ORGA_URL
        self.assertGET200(url)

        name = 'KOF'
        phone = '111111'
        #email = 'contact@kof.org'
        response = self.assertPOST200(url, follow=True,
                                      data={'name':  name,
                                            'phone': phone,
                                            #'email': email,
                                           }
                                     )
        self.assertNoFormError(response)

        kof = self.get_object_or_fail(Organisation, name=name)
        self.assertEqual(phone, kof.phone)
        #self.assertEqual(email, kof.email)
        self.assertFalse(self.user.mobile_favorite.all())

        self.assertRedirects(response, self.PERSONS_PORTAL_URL)

    def test_create_orga02(self):
        self.login()
        name = 'Fatal Fury Inc.'

        url = self.CREATE_ORGA_URL
        arg = {'name': name}
        response = self.assertGET200(url, data=arg)
        self.assertEqual(arg, response.context['form'].initial)

        response = self.assertPOST200(url, follow=True,
                                      data={'name':         name,
                                            'is_favorite':  True,
                                           }
                                     )
        self.assertNoFormError(response)

        ff = self.get_object_or_fail(Organisation, name=name)
        self.assertEqual([ff], [f.entity.get_real_entity() for f in self.user.mobile_favorite.all()])

    def test_search_persons01(self):
        self.login()
        url = self.SEARCH_PERSON_URL

        self.assertGET404(url)
        self.assertGET409(url, data={'search': 'Ik'})

        response = self.assertGET200(url, data={'search': 'Ikari'})
        self.assertTemplateUsed(response, 'mobile/search.html')

        with self.assertNoException():
            contacts = response.context['contacts']
            orgas    = response.context['organisations']

        self.assertEqual(0, len(contacts))
        self.assertEqual(0, len(orgas))

    def test_search_persons02(self):
        self.login()

        create_contact = partial(Contact.objects.create, user=self.user)
        create_contact(first_name='Rei',   last_name='Ayanami')
        create_contact(first_name='Asuka', last_name='Langley')
        shinji = create_contact(first_name='Shinji', last_name='Ikari', mobile='559966')
        gendo  = create_contact(first_name='Gendo',  last_name='Ikari')
        ikari  = create_contact(first_name='Ikari',  last_name='Warrior')

        response = self.assertGET200(self.SEARCH_PERSON_URL, data={'search': 'Ikari'})

        with self.assertNoException():
            contacts = set(response.context['contacts'])

        self.assertEqual({shinji, gendo, ikari}, contacts)
        self.assertContains(response, shinji.first_name)
        self.assertContains(response, shinji.mobile)

    def test_search_persons03(self):
        "Search in organisations which employ ('employed by')"
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        kof = create_orga(name='KingOfFighters')
        ff = create_orga(name='Fatal fury')

        create_contact = partial(Contact.objects.create, user=self.user)
        may = create_contact(first_name='May', last_name='Shiranui')
        create_contact(first_name='Asuka', last_name='Langley')

        create_rel = partial(Relation.objects.create, type_id=REL_SUB_EMPLOYED_BY, user=self.user)
        create_rel(subject_entity=may, object_entity=kof)
        create_rel(subject_entity=may, object_entity=ff) #can cause doublon

        url = self.SEARCH_PERSON_URL
        context = self.assertGET200(url, data={'search': kof.name.lower()[1:6]}).context
        self.assertEqual([may], list(context['contacts']))
        self.assertEqual([kof], list(context['organisations']))

        response = self.assertGET200(url, data={'search': may.last_name[:4]})
        self.assertEqual([may], list(response.context['contacts']))

    def test_search_persons04(self):
        "Search in organisations which employ ('managed by')"
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        kof = create_orga(name='KingOfFighters')
        create_orga(name='Fatal fury')

        create_contact = partial(Contact.objects.create, user=self.user)
        may = create_contact(first_name='May', last_name='Shiranui')
        create_contact(first_name='Asuka', last_name='Langley')

        Relation.objects.create(subject_entity=may, object_entity=kof,
                                type_id=REL_SUB_MANAGES, user=self.user,
                               )

        response = self.assertGET200(self.SEARCH_PERSON_URL,
                                     data={'search': kof.name.lower()[1:6]}
                                    )
        self.assertEqual([may], list(response.context['contacts']))

#TODO: smart word splitting ; special chars like " ??

    def test_start_activity01(self):
        "Start & end are past"
        self.login()

        meeting = self._create_meeting('Meeting#1', participant=self.user.linked_contact,
                                       start=now() - timedelta(hours=2),
                                      )

        url = self._build_start_url(meeting)
        self.assertGET404(url)
        response = self.assertPOST200(url, follow=True)

        meeting = self.refresh(meeting)
        self.assertDatetimesAlmostEqual(now(), meeting.start)
        self.assertEqual(meeting.type.as_timedelta(), meeting.end - meeting.start)
        self.assertEqual(STATUS_IN_PROGRESS, meeting.status_id)

        self.assertRedirects(response, '/mobile/#activity_%s' % meeting.id)

    def test_start_activity02(self):
        "Start & end are in the future"
        self.login()

        meeting = self._create_meeting('Meeting#1', participant=self.user.linked_contact, 
                                       start=now() + timedelta(minutes=30),
                                      )
        #old_end = meeting.end
        old_end = self.refresh(meeting).end #NB: MySQL does not record milliseconds...

        self.assertPOST200(self._build_start_url(meeting), follow=True)

        meeting = self.refresh(meeting)
        self.assertDatetimesAlmostEqual(now(), meeting.start)
        self.assertGreater(meeting.end, meeting.start)
        self.assertEqual(old_end, meeting.end)

    def test_start_activity03(self):
        "Floating time activity"
        self.login()

        now_val = now()

        def today(hour=14, minute=0):
            #return make_aware_dt(datetime.combine(now_val, time(hour=hour, minute=minute)))
            return datetime(year=now_val.year, month=now_val.month, day=now_val.day,
                            hour=hour, minute=minute,
                            tzinfo=now_val.tzinfo
                           )

        end = today(23, 59)
        meeting = self._create_meeting('Meeting#1', participant=self.user.linked_contact,
                                       start=today(0, 0),
                                       end=end,
                                       floating_type=FLOATING_TIME,
                                      )

        self.assertPOST200(self._build_start_url(meeting), follow=True)

        meeting = self.refresh(meeting)
        #self.assertLess((now() - meeting.start).seconds, 10)
        self.assertDatetimesAlmostEqual(now(), meeting.start)
        self.assertEqual(end, meeting.end)
        self.assertEqual(NARROW, meeting.floating_type)

    def test_start_activity04(self):
        "Floating activity"
        self.login()

        f_act = self._create_floating('Floating#1', participant=self.user.linked_contact)

        self.assertPOST200(self._build_start_url(f_act), follow=True)

        f_act = self.refresh(f_act)
        self.assertDatetimesAlmostEqual(now(), f_act.start)
        self.assertEqual(f_act.type.as_timedelta(), f_act.end - f_act.start)
        self.assertEqual(NARROW, f_act.floating_type)

    def test_stop_activity01(self):
        self.login()

        meeting = self._create_meeting('Meeting#1', participant=self.user.linked_contact,
                                       start=now() - timedelta(minutes=30)
                                      )

        url = self._build_stop_url(meeting)
        self.assertGET404(url)
        response = self.assertPOST200(url, follow=True)

        meeting = self.refresh(meeting)
        self.assertEqual(STATUS_DONE, meeting.status_id)
        self.assertDatetimesAlmostEqual(now(), meeting.end)

        self.assertRedirects(response, self.PORTAL_URL)

    def test_stop_activity02(self):
        "Start is in the future => error"
        self.login()

        meeting = self._create_meeting('Meeting#1', participant=self.user.linked_contact,
                                       start=now() + timedelta(minutes=30),
                                      )
        self.assertPOST409(self._build_stop_url(meeting))

    def test_activities_portal01(self):
        self.login()
        contact = self.user.linked_contact
        other_contact = self.other_user.linked_contact

        now_val = now()
        yesterday = now_val - timedelta(days=1)

        #Phone calls ----------------------------------------------------------
        i = count(1)
        create_pc = lambda **kwargs: self._create_pcall(title='Pcall#%i' % i.next(), **kwargs)

        pc1 = create_pc(start=yesterday,             status_id=STATUS_PLANNED,   participant=contact)
        pc2 = create_pc(start=now_val - timedelta(hours=25),                     participant=contact) # older than pc1 -> before
        create_pc(start=yesterday,                   status_id=STATUS_DONE,      participant=contact) # done -> excluded
        create_pc(start=yesterday,                   status_id=STATUS_CANCELLED, participant=contact) # cancelled -> excluded
        create_pc(start=yesterday,                   status_id=STATUS_PLANNED,   participant=other_contact) # I do not participate
        tom1 = create_pc(start=now_val + timedelta(days=1), status_id=STATUS_PLANNED, participant=contact) # tomorrow

        expected_pcalls = [pc2, pc1]

        for minute in xrange(8):
            expected_pcalls.append(create_pc(start=now_val - timedelta(hours=23, minutes=60 - minute), participant=contact))

        create_pc(start=now_val - timedelta(hours=23, minutes=minute), participant=contact) # already 10 PhoneCalls

        #Floating activities --------------------------------------------------
        create_floating = self._create_floating

        f1 = create_floating('Floating B', contact)
        f2 = create_floating('Floating A', contact)
        f3 = create_floating('Floating C', contact)
        create_floating('Floating #4', other_contact) # I do not participate
        create_floating('Floating #5', contact, status_id=STATUS_DONE)
        create_floating('Floating #6', contact, status_id=STATUS_CANCELLED)

        #Tomorrow activities --------------------------------------------------
        create_m = partial(self._create_meeting, participant=contact,
                           start=now_val + timedelta(hours=23),
                          )
        tom2 = create_m('Meeting #1')
        create_m('Meeting #2', participant=other_contact)
        create_m('Meeting #3', start=now_val + timedelta(days=2))

        #Assertions -----------------------------------------------------------
        response = self.assertGET200(self.ACTIVITIES_PORTAL_URL)
        self.assertTemplateUsed(response, 'mobile/activities.html')

        with self.assertNoException():
            context = response.context
            pcalls       = list(context['phone_calls'])
            factivities  = list(context['floating_activities'])
            tomorrow_act = list(context['tomorrow_activities'])
            fact_count   = context['floating_activities_count']

        self.assertEqual(expected_pcalls, pcalls)
        self.assertContains(response, pc1.title)

        self.assertEqual([f2, f1, f3], factivities)
        self.assertContains(response, f2.title)
        self.assertEqual(3, fact_count)

        self.assertEqual([tom2, tom1], tomorrow_act)
        self.assertContains(response, tom2.title)

    def test_activities_portal02(self):
        "Floating count when truncated"
        self.login()

        create_floating = partial(self._create_floating, participant=self.user.linked_contact)
        for i in xrange(1, 32):
            create_floating('Floating %i' % i)

        response = self.assertGET200(self.ACTIVITIES_PORTAL_URL)
        self.assertTemplateUsed(response, 'mobile/activities.html')

        with self.assertNoException():
            context = response.context
            factivities = context['floating_activities']
            fact_count  = context['floating_activities_count']

        self.assertEqual(30, len(factivities))
        self.assertEqual(31, fact_count)

    def test_phone_call_panel01(self):
        "Create with the number of a contact"
        self.login()

        url = self.PCALL_PANEL_URL
        self.assertGET404(url)

        gally = Contact.objects.create(user=self.user, first_name='Gally', last_name='Alita')
        phone = '4546465'
        response = self.assertGET200(url,
                                     data={'call_start': '2014-04-17T16:18:05.0Z',
                                           'person_id':  gally.id,
                                           'number':     phone,
                                          }
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
        self.assertEqual(self.create_datetime(utc=True, year=2014, month=4, day=17,
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

    def test_phone_call_panel02(self):
        "Create with the number of an organisation"
        self.login()

        zalem = Organisation.objects.create(user=self.user, name='Zalem')
        mobile = '896255'
        response = self.assertGET200(self.PCALL_PANEL_URL,
                                     data={'call_start': '2014-04-18T16:18:05.0Z',
                                           'person_id':  zalem.id,
                                           'number':     mobile,
                                          }
                                    )

        with self.assertNoException():
            context = response.context
            orga    = context['called_orga']
            orgas   = context['participant_organisations']

        self.assertEqual(self.create_datetime(utc=True, year=2014, month=4, day=18,
                                              hour=16, minute=18, second=5,
                                             ),
                         context['call_start']
                        )
        self.assertNotIn('called_contact', context)
        self.assertEqual(zalem, orga)
        self.assertNotIn('phone_call', context)
        self.assertEqual(mobile, context['number'])
        self.assertNotIn('participant_contacts', context)
        self.assertEqual([zalem], orgas)

    def test_phone_call_panel03(self):
        "Update an existing phone call"
        self.login()
        user = self.user
        contact = user.linked_contact

        pcall = self._create_pcall('Phone call#1', participant=contact)

        gally = Contact.objects.create(user=user, first_name='Gally', last_name='Alita')

        create_orga = partial(Organisation.objects.create, user=user)
        zalem = create_orga(name='Zalem')
        kuzu  = create_orga(name='Kuzutetsu')

        create_rel = partial(Relation.objects.create, user=user, object_entity=pcall)
        create_rel(subject_entity=gally, type_id=REL_SUB_PART_2_ACTIVITY)
        #TODO: 1.5 subject -> participate
        create_rel(subject_entity=kuzu, type_id=REL_SUB_ACTIVITY_SUBJECT)

        response = self.assertGET200(self.PCALL_PANEL_URL,
                                     data={'call_start': '2014-04-18T16:18:05.0Z',
                                           'pcall_id':   pcall.id,
                                           'person_id':  zalem.id,
                                           'number':     '896255',
                                          }
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
        self.assertEqual({gally, contact}, set(contacts))
        self.assertEqual([kuzu], orgas)

    def test_phone_call_wf_done(self):
        self.login()
        contact = self.user.linked_contact

        pcall = self._create_pcall('Phone call#1', participant=contact)

        url_fmt = '/mobile/phone_call/%s/done'
        url = url_fmt % pcall.id
        self.assertGET404(url)

        response = self.assertPOST200(url, follow=True)
        self.assertEqual(STATUS_DONE, self.refresh(pcall).status_id)

        self.assertRedirects(response, self.PORTAL_URL) #TODO: test with other REFERRER

        #------
        meeting = self._create_meeting('Meeting#1', participant=contact)
        self.assertPOST404(url_fmt % meeting.id)

    def test_phone_call_wf_failed01(self):
        self.login()

        pcall = self._create_pcall('Phone call#1', status_id=STATUS_PLANNED,
                                   participant=self.user.linked_contact,
                                  )

        url = self.WF_FAILED_URL
        self.assertGET404(url)
        self.assertPOST200(url, data={'pcall_id':   str(pcall.id),
                                      'call_start': '2014-04-22T16:34:28.0Z',
                                     }
                          )

        pcall = self.refresh(pcall)
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_FAILED, pcall.sub_type_id)
        self.assertEqual(STATUS_DONE,                      pcall.status_id)

        start = self.create_datetime(utc=True, year=2014, month=4, day=22,
                                     hour=16, minute=34, second=28
                                    )
        self.assertEqual(start, pcall.start)
        self.assertEqual(start, pcall.end)

    def test_phone_call_wf_failed02(self):
        "Not a Phone call => error"
        self.login()

        meeting = self._create_meeting('Meeting#1', participant=self.user.linked_contact)
        self.assertPOST404(self.WF_FAILED_URL, data={'pcall_id': meeting.id})

    def test_phone_call_wf_failed03(self):
        "Phone call is created (with contact)"
        self.login()
        other_contact = self.other_user.linked_contact

        pcall_ids = self._existing_pcall_ids()

        self.assertPOST200(self.WF_FAILED_URL,
                           data={'call_start': '2014-04-18T16:17:28.0Z',
                                 'person_id':  str(other_contact.id),
                                }
                          )

        pcall = self._get_created_pcall(pcall_ids)
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_FAILED, pcall.sub_type_id)
        self.assertEqual(STATUS_DONE,                      pcall.status_id)
        self.assertEqual({self.user.linked_contact, other_contact},
                         {r.object_entity.get_real_entity()
                                for r in pcall.get_participant_relations()
                         }
                        )

        start = self.create_datetime(utc=True, year=2014, month=4, day=18,
                                     hour=16, minute=17, second=28
                                    )
        self.assertEqual(start, pcall.start)
        self.assertEqual(start, pcall.end)

        self.assertEqual(_('%(status)s call to %(person)s from Creme Mobile') % {
                                'status': _('Failed'),
                                'person': other_contact,
                            },
                         pcall.title
                        )

        get_cal = Calendar.get_user_default_calendar
        self.assertEqual({get_cal(self.user), get_cal(self.other_user)},
                         set(pcall.calendars.all())
                        )

    def test_phone_call_wf_failed04(self):
        "Second participant == first participant"
        self.login()
        self.assertPOST409(self.WF_FAILED_URL,
                           data={'call_start': '2014-04-18T16:17:28.0Z',
                                 'person_id':  str(self.user.linked_contact.id),
                                }
                          )

    def test_phone_call_wf_failed05(self):
        "Phone call is created (with organisation)"
        self.login()
        pcall_ids = self._existing_pcall_ids()

        kuzu = Organisation.objects.create(user=self.user, name='Kuzutetsu')
        self.assertPOST200(self.WF_FAILED_URL,
                           data={'call_start': '2014-04-18T16:17:28.0Z',
                                 'person_id':  kuzu.id,
                                }
                          )

        pcall = self._get_created_pcall(pcall_ids)
        self.assertEqual([self.user.linked_contact],
                         [r.object_entity.get_real_entity()
                                for r in pcall.get_participant_relations()
                         ]
                        )
        self.assertEqual([kuzu],
                         [r.object_entity.get_real_entity()
                                for r in pcall.get_subject_relations()
                         ]
                        )

    def test_phone_call_wf_postponed01(self):
        self.login()

        contact = self.user.linked_contact
        pcall = self._create_pcall('Phone call#1', status_id=STATUS_PLANNED,
                                   participant=contact,
                                   description='blablabla',
                                   floating_type=FLOATING_TIME,
                                  )
        #old_start = pcall.start
        #old_end = pcall.end

        url = self.WF_POSTPONED_URL
        self.assertGET404(url)

        pcall_ids = self._existing_pcall_ids()
        self.assertPOST200(url, data={'pcall_id':   pcall.id,
                                      'call_start': '2014-04-22T16:17:28.0Z',
                                     })

        pcall = self.refresh(pcall)
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_FAILED, pcall.sub_type_id)
        self.assertEqual(STATUS_DONE,                      pcall.status_id)
        self.assertEqual(NARROW,                           pcall.floating_type)
        #self.assertEqual(old_start,                        pcall.start)
        #self.assertEqual(old_end,                          pcall.end)

        start = self.create_datetime(utc=True, year=2014, month=4, day=22,
                                     hour=16, minute=17, second=28
                                    )
        self.assertEqual(start, pcall.start)
        self.assertEqual(start, pcall.end)

        pcall2 = self._get_created_pcall(pcall_ids)
        self.assertEqual(pcall.description, pcall2.description)
        self.assertRelationCount(1, contact, REL_SUB_PART_2_ACTIVITY, pcall)

        self.assertEqual(STATUS_PLANNED, pcall2.status_id)
        self.assertEqual(FLOATING_TIME,  pcall2.floating_type)

        today = now().day

        start = localtime(pcall2.start)
        self.assertEqual(0, start.hour)
        self.assertEqual(0, start.minute)
        self.assertEqual(1, start.day - today)

        end = localtime(pcall2.end)
        self.assertEqual(23, end.hour)
        self.assertEqual(59, end.minute)
        self.assertEqual(1,  end.day - today)

    def test_phone_call_wf_postponed02(self):
        "Phone calls are created (with contact)"
        self.login()
        pcall_ids = self._existing_pcall_ids()
        other_part = Contact.objects.create(user=self.user, first_name='Gally',
                                            last_name='Alita',
                                           ) #not linked to a user -> (no linked Calendar)
        participants = {self.user.linked_contact, other_part}

        self.assertPOST200(self.WF_POSTPONED_URL,
                           data={'call_start': '2014-04-22T11:54:28.0Z',
                                 'person_id':  other_part.id,
                                }
                          )

        pcalls = sorted(self._get_created_pcalls(pcall_ids), key=lambda c: c.id)
        self.assertEqual(2, len(pcalls))

        failed_pcall = pcalls[0]
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_FAILED, failed_pcall.sub_type_id)
        self.assertEqual(STATUS_DONE,                      failed_pcall.status_id)
        self.assertEqual(NARROW,                           failed_pcall.floating_type)
        self.assertEqual(participants,
                         {r.object_entity.get_real_entity()
                            for r in failed_pcall.get_participant_relations()
                         }
                        )
        self.assertEqual(_('%(status)s call to %(person)s from Creme Mobile') % {
                                'status': _('Failed'),
                                'person':  other_part,
                            },
                         failed_pcall.title
                        )

        start = self.create_datetime(utc=True, year=2014, month=4, day=22,
                                     hour=11, minute=54, second=28
                                    )
        self.assertEqual(start, failed_pcall.start)
        self.assertEqual(start, failed_pcall.end)

        pp_pcall = pcalls[1]
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_OUTGOING, pp_pcall.sub_type_id)
        self.assertEqual(FLOATING_TIME,                      pp_pcall.floating_type)
        self.assertIsNone(pp_pcall.status_id)
        self.assertEqual(participants,
                         {r.object_entity.get_real_entity()
                            for r in pp_pcall.get_participant_relations()
                         }
                        )

        today = now().day

        start = localtime(pp_pcall.start)
        self.assertEqual(0, start.hour)
        self.assertEqual(0, start.minute)
        self.assertEqual(1, start.day - today)

        end = localtime(pp_pcall.end)
        self.assertEqual(23, end.hour)
        self.assertEqual(59, end.minute)
        self.assertEqual(1,  end.day - today)

        self.assertEqual(_('Call to %s from Creme Mobile') % other_part,
                         pp_pcall.title
                        )

    def test_phone_call_wf_lasted5min01(self):
        self.login()

        pcall = self._create_pcall('Phone call#1', status_id=STATUS_PLANNED,
                                   participant=self.user.linked_contact,
                                  )

        url = self.WF_LASTED5MIN_URL
        self.assertGET404(url)
        self.assertPOST200(url, data={'pcall_id':   pcall.id,
                                      'call_start': '2014-03-10T11:30:28.0Z',
                                     }
                          )

        pcall = self.refresh(pcall)
        self.assertEqual(STATUS_DONE, pcall.status_id)

        create_dt = partial(self.create_datetime, utc=True, year=2014, month=3, day=10, hour=11)
        self.assertEqual(create_dt(minute=30, second=28), pcall.start)
        self.assertEqual(create_dt(minute=35, second=28), pcall.end)

    def test_phone_call_wf_lasted5min02(self):
        "Bad date format"
        self.login()

        pcall = self._create_pcall('Phone call#1', status_id=STATUS_PLANNED,
                                   participant=self.user.linked_contact,
                                  )
        self.assertPOST404(self.WF_LASTED5MIN_URL,
                           data={'pcall_id':    pcall.id,
                                 'call_start': '10-03-2014 10:30:28',
                                }
                          )

    def test_phone_call_wf_lasted5min03(self):
        "Phone call is created (with contact)"
        self.login()
        other_contact = self.other_user.linked_contact
        pcall_ids = self._existing_pcall_ids()

        self.assertPOST200(self.WF_LASTED5MIN_URL,
                           data={'call_start': '2014-04-18T16:17:28.0Z',
                                 'person_id':  other_contact.id,
                                }
                          )

        pcall = self._get_created_pcall(pcall_ids)
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_OUTGOING, pcall.sub_type_id)
        self.assertEqual(STATUS_DONE, pcall.status_id)
        self.assertEqual({self.user.linked_contact, other_contact},
                         {r.object_entity.get_real_entity()
                            for r in pcall.get_participant_relations()
                         }
                        )

        create_dt = partial(self.create_datetime, utc=True, year=2014, month=4, day=18, hour=16)
        self.assertEqual(create_dt(minute=17, second=28), pcall.start)
        self.assertEqual(create_dt(minute=22, second=28), pcall.end)

        self.assertEqual(_('%(status)s call to %(person)s from Creme Mobile') % {
                                'status': _('Successful'),
                                'person':  other_contact,
                            },
                         pcall.title
                        )

    def test_phone_call_wf_lasted5min04(self):
        "Second participant == first participant"
        self.login()
        self.assertPOST409(self.WF_LASTED5MIN_URL,
                           data={'call_start': '2014-04-18T16:17:28.0Z',
                                 'person_id':  self.user.linked_contact.id,
                                }
                          )

    def test_phone_call_wf_lasted5min05(self):
        "call_start + 5 minutes > now()"
        self.login()

        pcall = self._create_pcall('Phone call#1', status_id=STATUS_PLANNED,
                                   participant=self.user.linked_contact,
                                  )

        start = now() - timedelta(minutes=2)
        self.assertPOST200(self.WF_LASTED5MIN_URL,
                           data={'pcall_id':   pcall.id,
                                 'call_start': start.strftime("%Y-%m-%dT%H:%M:%S.%fZ"), #TODO: in utils ??
                                }
                          )

        pcall = self.refresh(pcall)
        self.assertEqual(STATUS_DONE, pcall.status_id)
        #self.assertEqual(start, pcall.start)
        self.assertDatetimesAlmostEqual(start, pcall.start) #NB: MySQL does not record milliseconds...
        self.assertDatetimesAlmostEqual(now(), pcall.end)

    def test_phone_call_wf_just_done01(self):
        self.login()
        contact = self.user.linked_contact

        pcall = self._create_pcall('Phone call#1', status_id=STATUS_PLANNED,
                                   participant=contact,
                                  )

        url = self.WF_JUSTDONE_URL
        self.assertGET404(url)

        start = now() - timedelta(minutes=5)
        self.assertPOST200(url, data={'pcall_id':   pcall.id,
                                      'call_start': start.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                                     }
                          )

        pcall = self.refresh(pcall)
        self.assertEqual(STATUS_DONE, pcall.status_id)

        self.assertDatetimesAlmostEqual(start, pcall.start)
        self.assertDatetimesAlmostEqual(now(), pcall.end)

        #------
        meeting = self._create_meeting('Meeting#1', participant=contact)
        self.assertPOST404(url, data={'pcall_id':   meeting.id,
                                      'call_start': start.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                                     }
                          )

    def test_phone_call_wf_just_done02(self):
        self.login()
        other_contact = self.other_user.linked_contact
        pcall_ids = self._existing_pcall_ids()

        start = now() - timedelta(minutes=5)
        self.assertPOST200(self.WF_JUSTDONE_URL,
                           data={'call_start': start.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                                 'person_id':  other_contact.id,
                                }
                          )

        pcall = self._get_created_pcall(pcall_ids)
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_OUTGOING, pcall.sub_type_id)
        self.assertEqual(STATUS_DONE, pcall.status_id)
        self.assertEqual({self.user.linked_contact, other_contact},
                         {r.object_entity.get_real_entity()
                                for r in pcall.get_participant_relations()
                         }
                        )
        self.assertDatetimesAlmostEqual(start, pcall.start)
        self.assertDatetimesAlmostEqual(now(), pcall.end)

        self.assertEqual(_('%(status)s call to %(person)s from Creme Mobile') % {
                                'status': _('Successful'),
                                'person': other_contact,
                            },
                         pcall.title
                        )
