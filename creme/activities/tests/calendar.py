# -*- coding: utf-8 -*-

try:
    from datetime import timedelta #datetime
    from functools import partial

    from django.utils.encoding import force_unicode
    from django.utils.timezone import make_naive, get_current_timezone
    from django.utils.translation import ugettext as _
    from django.utils.simplejson import loads as jsonloads

    from creme.creme_core.models import Relation

    #from creme.persons.models import Contact

    from .base import _ActivitiesTestCase
    from ..models import Calendar, Activity
    from ..constants import *
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('CalendarTestCase',)


class CalendarTestCase(_ActivitiesTestCase):
    ADD_URL = '/activities/calendar/add'
    CONF_ADD_URL = '/creme_config/activities/calendar/add/'
    CALENDAR_URL = '/activities/calendar/user'
    DEL_CALENDAR_URL = '/activities/calendar/delete'
    UPDATE_URL = '/activities/calendar/activity/update'

    def assertUserHasDefaultCalendar(self, user):
        return self.get_object_or_fail(Calendar, is_default=True, user=user)

    def _build_ts(self, dt):
        return float(dt.strftime('%s')) * 1000 #simulates JS that sends milliseconds

    def _get_cal_activities(self, users, calendars, start=None, end=None, status=200):
        data = {}
        if start: data['start'] = start
        if end:   data['end'] = end

        return self.assertGET(status,
                              '/activities/calendar/users_activities/%s/%s' % (
                                        ','.join(u.username for u in users),
                                        ','.join(str(c.id) for c in calendars),
                                   ),
                              data=data,
                             )

    def test_user_default_calendar01(self):
        self.login()
        user = self.user

        with self.assertNumQueries(2):
            def_cal = Calendar.get_user_default_calendar(user)

        self.assertEqual(_(u"Default %(user)s's calendar") % {'user': user},
                         def_cal.name,
                        )

        def_cal2 = self.assertUserHasDefaultCalendar(user)
        self.assertEqual(def_cal, def_cal2)

    def test_user_default_calendar02(self):
        "Default already exists"
        self.login()
        user = self.user

        cal1 = Calendar.objects.create(is_default=True, user=user)

        with self.assertNumQueries(1):
            def_cal = Calendar.get_user_default_calendar(user)

        self.assertEqual(cal1, def_cal)

    def test_user_default_calendar03(self):
        "Several default exist"
        self.login()
        user = self.user
        cal1 = Calendar.objects.create(is_default=True, user=user, name='Cal#1')
        cal2 = Calendar.objects.create(user=user, name='Cal#2')
        Calendar.objects.filter(id=cal2.id).update(is_default=True)
 
        #be sure that we well managed the automatic save() behaviour
        self.assertEqual(2, Calendar.objects.filter(is_default=True, user=user).count())

        self.assertEqual(cal1, Calendar.get_user_default_calendar(user))
        self.assertFalse(self.refresh(cal2).is_default)

    def test_user_default_calendar04(self):
        "No default Calendar in existing ones."
        self.login()
        user = self.user
        cal = Calendar.objects.create(user=user, name='Cal #1')
        Calendar.objects.filter(id=cal.id).update(is_default=False)

        #be sure that we well managed the automatic save() behaviour
        self.assertFalse(Calendar.objects.filter(is_default=True, user=user))

        #with self.assertNumQueries(2): TODO: see comment in the code
        with self.assertNumQueries(3):
            def_cal = Calendar.get_user_default_calendar(user)

        self.assertEqual(cal, def_cal)
        self.assertTrue(def_cal.is_default)

    def test_get_user_calendars01(self):
        self.login()

        with self.assertNumQueries(2):
            cals = Calendar.get_user_calendars(self.user)

        self.assertEqual(1, len(cals))

        cal = cals[0]
        self.assertIsInstance(cal, Calendar)
        self.assertTrue(cal.is_default)

    def test_get_user_calendars02(self):
        self.login()
        user = self.user
        Calendar.get_user_default_calendar(user)
        Calendar.objects.create(user=user, name='Cal#2')

        with self.assertNumQueries(1):
            cals = Calendar.get_user_calendars(self.user)

        self.assertEqual(2, len(cals))

    def test_user_calendar01(self):
        self.login()
        user = self.user

        response = self.assertGET200(self.CALENDAR_URL)
        self.assertTemplateUsed(response, 'activities/calendar.html')

        with self.assertNoException():
            ctxt = response.context
            cal_ids = ctxt['current_calendars']
            floating_acts = ctxt['floating_activities']
            my_cals = ctxt['my_calendars']
            users = ctxt['current_users']

        def_cal = self.assertUserHasDefaultCalendar(user)
        self.assertEqual([str(def_cal.id)], cal_ids)

        self.assertFalse(floating_acts)
        self.assertEqual([def_cal], list(my_cals))
        self.assertEqual([user], list(users))

    def test_user_calendar02(self):
        self.login()
        user = self.user
        other_user = self.other_user

        create_cal = partial(Calendar.objects.create, is_default=True)
        cal1 = create_cal(user=user,       name='Cal #1')
        cal2 = create_cal(user=other_user, name='Cal #2')

        create_act = partial(Activity.objects.create, user=user,
                             type_id=ACTIVITYTYPE_TASK, floating_type=FLOATING
                            )
        act1 = create_act(title='Act#1')
        act2 = create_act(title='Act#2', type_id=ACTIVITYTYPE_MEETING, 
                          sub_type_id=ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                         )
        create_act(title='Act#3', is_deleted=True)
        create_act(title='Act#4', user=other_user)
        create_act(title='Act#5', floating_type=NARROW)

        response = self.assertPOST200(self.CALENDAR_URL,
                                      data={'user_selected':     [user.username, other_user.username],
                                            'calendar_selected': [cal1.id, cal2.id],
                                           }
                                    )

        with self.assertNoException():
            ctxt = response.context
            users = ctxt['current_users']
            cal_ids = ctxt['current_calendars']
            floating_acts = ctxt['floating_activities']

        self.assertEqual(set([user, other_user]), set(users))
        self.assertEqual(set([str(cal1.id), str(cal2.id)]), set(cal_ids))
        self.assertEqual(set([act1, act2]), set(floating_acts))

    #def test_my_calendar(self):
        #self.login()

        #response = self.assertGET200('/activities/calendar/my')
        #self.assertTemplateUsed(response, 'activities/calendar.html')

        #with self.assertNoException():
            #users = response.context['current_users']

        #self.assertEqual([self.user], list(users))

    def test_add_user_calendar01(self):
        self.login()
        user = self.user

        self.assertFalse(Calendar.objects.filter(is_default=True, user=user))

        url = self.ADD_URL
        self.assertGET200(url)

        name = 'My pretty calendar'
        self.assertNoFormError(self.client.post(url, data={'name': name}))

        cals = Calendar.objects.filter(user=user)
        self.assertEqual(1, len(cals))

        cal = cals[0]
        self.assertEqual(name, cal.name)
        self.assertIs(cal.is_default, True)
        self.assertIs(cal.is_public, False)
        self.assertIs(cal.is_custom, True)

    def test_add_user_calendar02(self):
        "Only one default calendar"
        self.login()
        user = self.user

        cal1 = Calendar.get_user_default_calendar(user)

        name = 'My pretty calendar'
        self.assertNoFormError(self.client.post(self.ADD_URL,
                                                data={'name': name,
                                                      'is_default': True,
                                                      'is_public': True,
                                                     }
                                               )
                              )

        cal2 = self.get_object_or_fail(Calendar, name=name)
        self.assertTrue(cal2.is_default)
        self.assertTrue(cal2.is_public)
        self.assertFalse(self.refresh(cal1).is_default)

    def test_edit_user_calendar01(self):
        self.login()

        cal = Calendar.get_user_default_calendar(self.user)
        name = 'My calendar'

        url = '/activities/calendar/%s/edit' % cal.id
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(url, data={'name': name}))
        self.assertEqual(name, self.refresh(cal).name)

    def test_delete_calendar01(self):
        "Not custom -> error"
        self.login()

        Calendar.get_user_default_calendar(self.user)
        cal = Calendar.objects.create(user=self.user, name='Cal #1', is_custom=False)

        url = self.DEL_CALENDAR_URL
        self.assertGET404(url)

        self.assertPOST404(url, data={'id': 1024})

        response = self.assertPOST403(url, data={'id': cal.id})
        self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual(_('You are not allowed to delete this calendar.'),
                         force_unicode(response.content)
                        )

        self.get_object_or_fail(Calendar, pk=cal.pk)

    def test_delete_calendar02(self):
        self.login()
        user = self.user

        Calendar.get_user_default_calendar(user)
        cal = Calendar.objects.create(user=user, name='Cal #1', is_custom=True)

        url = self.DEL_CALENDAR_URL
        self.assertGET404(url)
        self.assertPOST200(url, data={'id': cal.id})
        self.assertFalse(Calendar.objects.filter(pk=cal.pk))

    def test_delete_calendar03(self):
        "No super user"
        self.login(is_superuser=False)

        user = self.user

        Calendar.get_user_default_calendar(user)
        cal = Calendar.objects.create(user=user, name='Cal #1', is_custom=True)

        self.assertPOST200(self.DEL_CALENDAR_URL, data={'id': cal.id})
        self.assertFalse(Calendar.objects.filter(pk=cal.pk))

    def test_delete_calendar04(self): 
        "Other user's calendar"
        self.login(is_superuser=False)

        #user = self.user
        other_user = self.other_user

        Calendar.get_user_default_calendar(other_user)
        cal = Calendar.objects.create(user=other_user, name='Cal #1', is_custom=True)

        self.assertPOST403(self.DEL_CALENDAR_URL, data={'id': cal.id})

    def test_get_users_activities01(self):
        "One user, no Activity"
        self.login()
        user = self.user

        response = self._get_cal_activities([user], [Calendar.get_user_default_calendar(user)])
        self.assertEqual('text/javascript', response['Content-Type'])

        with self.assertNoException():
            data = jsonloads(response.content)

        self.assertEqual([], data)

    def test_get_users_activities02(self):
        "One user, several activities"
        self.login()
        user = self.user

        cal = Calendar.get_user_default_calendar(user)

        #start = datetime(year=2013, month=3, day=1)
        #end   = datetime(year=2013, month=3, day=31, hour=23, minute=59)
        create_dt = self.create_datetime
        start = create_dt(year=2013, month=3, day=1)
        end   = create_dt(year=2013, month=3, day=31, hour=23, minute=59)

        create = partial(Activity.objects.create, user=user, type_id=ACTIVITYTYPE_TASK)
        act1 = create(title='Act#1', start=start + timedelta(days=1), end=start + timedelta(days=2))
        act2 = create(title='Act#2', start=start + timedelta(days=1), end=start + timedelta(days=2)) #not in calendar
        act3 = create(title='Act#3', start=start + timedelta(days=1), end=end   + timedelta(days=1), #start OK
                      is_all_day=True, type_id=ACTIVITYTYPE_MEETING, 
                      sub_type_id=ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                     )
        act4 = create(title='Act#4', start=start - timedelta(days=1), end=start + timedelta(days=3)) #end OK
        act5 = create(title='Act#5', start=start + timedelta(days=5), end=start + timedelta(days=5, hours=3),
                      is_deleted=True,
                     )

        for act in (act1, act3, act4, act5):
            act.calendars = [cal]

        response = self._get_cal_activities([user], [cal],
                                            start=start.strftime('%s'),
                                            end=end.strftime('%s'),
                                           )

        with self.assertNoException():
            data = jsonloads(response.content)

        self.assertEqual(3, len(data))

        def formated_dt(dt):
            return make_naive(dt, get_current_timezone()).isoformat()

        url_fmt = '/activities/activity/%s/popup'
        self.assertEqual({'id':           act1.id,
                          'title':        'Act#1 - Kirika',
                          'allDay':       False,
                          #'start':        act1.start.isoformat(),
                          #'end':          act1.end.isoformat(),
                          'start':        formated_dt(act1.start),
                          'end':          formated_dt(act1.end),
                          'url':          url_fmt % act1.id,
                          'entity_color': '#987654',
                          'editable':     True,
                         },
                         data[0]
                        )
        self.assertEqual({'id':           act3.id,
                          'title':        'Act#3 - Kirika',
                          'allDay':       True,
                          #'start':        act3.start.isoformat(),
                          #'end':          act3.end.isoformat(),
                          'start':        formated_dt(act3.start),
                          'end':          formated_dt(act3.end),
                          'url':          url_fmt % act3.id,
                          'entity_color': '#456FFF',
                          'editable':     True,
                         },
                         data[1]
                        )
        self.assertEqual(act4.id, data[2]['id'])

    def test_get_users_activities03(self):
        "2 Users, 2 Calendars, Indisponibilities"
        self.login()
        user = self.user
        other_user = self.other_user

        contact1 = self.contact
        contact2 = self.other_contact

        cal1 = Calendar.get_user_default_calendar(user)
        cal2 = Calendar.get_user_default_calendar(other_user)
        cal3 = Calendar.objects.create(user=other_user, name='Cal #3',
                                       is_custom=True, is_default=False,
                                       is_public=True,
                                      )
        self.assertFalse(cal2.is_public)

        #start = datetime(year=2013, month=4, day=1)
        start = self.create_datetime(year=2013, month=4, day=1)

        create = partial(Activity.objects.create, user=user, type_id=ACTIVITYTYPE_TASK)
        act1 = create(title='Act#1', start=start + timedelta(days=1),  end=start + timedelta(days=2))
        act2 = create(title='Act#2', start=start + timedelta(days=1),  end=start + timedelta(days=2)) #not in [cal1, cal3]
        act3 = create(title='Act#3', start=start + timedelta(days=32), end=start + timedelta(days=33)) #start KO
        act4 = create(title='Act#4', start=start + timedelta(days=29), end=start + timedelta(days=30))

        act1.calendars = [cal1]
        act2.calendars = [cal2]
        act3.calendars = [cal3]
        act4.calendars = [cal3]

        create_ind = partial(Activity.objects.create, user=user, type_id=ACTIVITYTYPE_INDISPO)
        act6 = create_ind(title='Ind#1', start=start + timedelta(days=5), end=start + timedelta(days=6))
        act7 = create_ind(title='Ind#2', start=start + timedelta(days=7), end=start + timedelta(days=8)) #not linked
        act8 = create_ind(title='Ind#3', start=start + timedelta(days=9), end=start + timedelta(days=10))

        create_rel = partial(Relation.objects.create, user=user, type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(subject_entity=contact2, object_entity=act6)
        create_rel(subject_entity=contact1, object_entity=act8)

        response = self._get_cal_activities([user, other_user],
                                            [cal1, cal2], #cal2 should not be used, it does not belong to user (so, no 'act2')
                                            start=start.strftime('%s'),
                                           )

        with self.assertNoException():
            data = jsonloads(response.content)

        expected = [act1, act4, act6, act8]
        expected_ids = set(act.id for act in expected)
        retrieved_ids = set(d['id'] for d in data)
        self.assertEqual(expected_ids, retrieved_ids,
                         '%s != %s (id map: %s)' % (expected_ids, retrieved_ids,
                                                    ['%s -> %s' % (act.id, act.title) for act in expected]
                                                   )
                        )

    def test_update_activity_date01(self):
        self.login()

        #start = datetime(year=2013, month=4, day=1, hour=9)
        start = self.create_datetime(year=2013, month=4, day=1, hour=9)
        end   = start + timedelta(hours=2)
        act = Activity.objects.create(user=self.user, type_id=ACTIVITYTYPE_TASK,
                                      title='Act#1', start=start, end=end,
                                     )

        url = self.UPDATE_URL
        self.assertGET404(url)

        offset = timedelta(days=1, hours=2)
        new_start = start + offset
        new_end   = end  + offset
        self.assertPOST(400, url, data={'id': act.id})
        self.assertPOST200(url, data={'id':     act.id,
                                      'start': self._build_ts(new_start),
                                      'end':   self._build_ts(new_end),
                                     }
                          )

        act = self.refresh(act)
        self.assertEqual(new_start, act.start)
        self.assertEqual(new_end,   act.end)

    def test_update_activity_date02(self):
        "Collision"
        self.login()
        user = self.user
        contact = self.contact

        create_act = partial(Activity.objects.create, user=user,
                             type_id=ACTIVITYTYPE_TASK, busy=True,
                            )
        create_dt = self.create_datetime
        act1 = create_act(title='Act#1',
                          #start=datetime(year=2013, month=4, day=1, hour=9),
                          #end=datetime(year=2013,   month=4, day=1, hour=10),
                          start=create_dt(year=2013, month=4, day=1, hour=9),
                          end=create_dt(year=2013,   month=4, day=1, hour=10),
                         )
        act2 = create_act(title='Act#2',
                          #start=datetime(year=2013, month=4, day=2, hour=9),
                          #end=datetime(year=2013,   month=4, day=2, hour=10),
                          start=create_dt(year=2013, month=4, day=2, hour=9),
                          end=create_dt(year=2013,   month=4, day=2, hour=10),
                         )

        create_rel = partial(Relation.objects.create, user=user, type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(subject_entity=contact, object_entity=act1)
        create_rel(subject_entity=contact, object_entity=act2)

        self.assertPOST(409, self.UPDATE_URL,
                        data={'id':    act1.id,
                              'start': self._build_ts(act2.start),
                              'end':   self._build_ts(act2.end),
                             }
                       )

    #def test_update_activity_date03(self): TODO: allDay

    def test_config01(self):
        self.login()

        self.assertGET200('/creme_config/activities/portal/')
        self.assertGET200('/creme_config/activities/calendar/portal/')

        url = self.CONF_ADD_URL
        self.assertGET200(url)

        user = self.user
        name = 'My Cal'
        self.assertNoFormError(self.client.post(url, data={'name': name,
                                                           'user': user.id,
                                                          }
                                               )
                              )

        cal = self.get_object_or_fail(Calendar, name=name, user=user)
        self.assertTrue(cal.is_default)
        self.assertTrue(cal.is_custom)
        self.assertFalse(cal.is_public)

    def test_config02(self): 
        "Only one default"
        self.login()
        user = self.user
        cal1 = Calendar.get_user_default_calendar(user)

        name = 'My default Cal'
        self.assertNoFormError(self.client.post(self.CONF_ADD_URL,
                                                data={'name': name,
                                                      'user': user.id,
                                                      'is_default': True,
                                                      'is_public': True,
                                                     }
                                               )
                              )

        cal2 = self.get_object_or_fail(Calendar, name=name, user=user)
        self.assertTrue(cal2.is_default)
        self.assertTrue(cal2.is_custom)
        self.assertTrue(cal2.is_public)

        self.assertFalse(self.refresh(cal1).is_default)

        #Delete
        self.assertPOST200('/creme_config/activities/calendar/delete',
                           data={'id': cal2.id},
                          )
        self.assertFalse(Calendar.objects.filter(pk=cal2.pk).exists())
        self.assertTrue(self.refresh(cal1).is_default)

    def test_config03(self): 
        "Edition"
        self.login()
        user = self.user
        cal1 = Calendar.get_user_default_calendar(user)

        name = 'cal#1'
        cal2 = Calendar.objects.create(user=user, name=name)

        url = '/creme_config/activities/calendar/edit/%s' % cal2.id
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('user', fields)

        name = name.title()
        self.assertNoFormError(self.client.post(url,
                                                data={'name': name,
                                                      'is_default': True,
                                                      'is_public': True,
                                                     }
                                               )
                              )

        cal2 = self.refresh(cal2)
        self.assertEqual(name, cal2.name)
        self.assertTrue(cal2.is_default)
        self.assertTrue(cal2.is_public)

        self.assertFalse(self.refresh(cal1).is_default)
