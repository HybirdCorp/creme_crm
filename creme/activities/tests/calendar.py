# -*- coding: utf-8 -*-

try:
    from datetime import timedelta #datetime
    from functools import partial

    from django.utils.encoding import force_unicode
    from django.utils.html import escape
    from django.utils.simplejson import loads as jsonloads, dumps as jsondumps
    from django.utils.timezone import make_naive, get_current_timezone
    from django.utils.translation import ugettext as _

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import Relation, SetCredentials

    #from creme.persons.models import Contact

    from .base import _ActivitiesTestCase
    from ..models import Calendar, Activity
    from ..constants import *
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


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

    def build_link_url(self, activity_id):
        return '/activities/calendar/link/%s' % activity_id

    def _get_cal_activities(self, calendars, start=None, end=None, status=200):
        data = {}
        if start: data['start'] = start
        if end:   data['end'] = end

        return self.assertGET(status,
                              '/activities/calendar/users_activities/%s' % (
                                        ','.join(str(c.id) for c in calendars),
                                   ),
                              data=data,
                             )

    def test_user_default_calendar01(self):
        self.login()
        user = self.user

        with self.assertNumQueries(3):
            def_cal = Calendar.get_user_default_calendar(user)

        #self.assertEqual(_(u"Default %(user)s's calendar") % {'user': user},
        self.assertEqual(_(u"%s's calendar") % user,
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

        with self.assertNumQueries(3):
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

        response = self.assertGET200(self.CALENDAR_URL)
        self.assertTemplateUsed(response, 'activities/calendar.html')

        with self.assertNoException():
            ctxt = response.context
            cal_ids = ctxt['current_calendars']
            floating_acts = ctxt['floating_activities']
            my_cals = ctxt['my_calendars']
            user = ctxt['user_username']
            ctxt['events_url']
            ctxt['others_calendars']
            ctxt['n_others_calendars']
            ctxt['creme_calendars_by_user']
            # ctxt['default_color']
            ctxt['creation_perm']

        def_cal = self.assertUserHasDefaultCalendar(self.user)
        self.assertEqual([str(def_cal.id)], cal_ids)

        self.assertFalse(floating_acts)
        self.assertEqual([def_cal], list(my_cals))
        self.assertEqual(self.user.username, user)

    def test_user_calendar02(self):
        self.login()
        user = self.user
        other_user = self.other_user

        cal1 = Calendar.objects.create(user=self.user, is_default=True, name='Cal #1')
        cal2 = Calendar.objects.create(user=other_user, is_default=True, name='Cal #2', is_public=True)
        cal3 = Calendar.objects.create(user=other_user, name='Cal #3', is_public=False)

        create_act = partial(Activity.objects.create, user=self.user,
                             type_id=ACTIVITYTYPE_TASK, floating_type=FLOATING
                            )
        act1 = create_act(title='Act#1')
        act2 = create_act(title='Act#2', type_id=ACTIVITYTYPE_MEETING,
                          sub_type_id=ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                         )
        act3 = create_act(title='Act#3', is_deleted=True)
        act4 = create_act(title='Act#4', user=other_user)
        act5 = create_act(title='Act#5', floating_type=NARROW)

        #create_rel = partial(Relation.objects.create, user=self.user, type_id=REL_SUB_PART_2_ACTIVITY)
        #create_rel(subject_entity=self.contact, object_entity=act1)
        #act1.calendars.add(cal1)
        #create_rel(subject_entity=self.contact, object_entity=act2)
        #act2.calendars.add(cal1)
        #create_rel(subject_entity=self.contact, object_entity=act3)
        #act3.calendars.add(cal1)
        #create_rel(subject_entity=self.contact, object_entity=act4)
        #act4.calendars.add(cal1)
        #create_rel(subject_entity=self.contact, object_entity=act5)
        #act5.calendars.add(cal1)
        create_rel = partial(Relation.objects.create, user=user,
                             subject_entity=user.linked_contact,
                             type_id=REL_SUB_PART_2_ACTIVITY,
                            )
        create_rel(object_entity=act1)
        act1.calendars.add(cal1)
        create_rel(object_entity=act2)
        act2.calendars.add(cal1)
        create_rel(object_entity=act3)
        act3.calendars.add(cal1)
        create_rel(object_entity=act4)
        act4.calendars.add(cal1)
        create_rel(object_entity=act5)
        act5.calendars.add(cal1)

        response = self.assertPOST200(self.CALENDAR_URL,
                                      data={'selected_calendars': [cal1.id, cal2.id, cal3.id]}
                                    )


        with self.assertNoException():
            ctxt = response.context
            cal_ids = ctxt['current_calendars']
            floating_acts = ctxt['floating_activities']
            my_cals = ctxt['my_calendars']
            user = ctxt['user_username']
            event_url = ctxt['events_url']
            others_calendars = ctxt['others_calendars']
            n_others_calendars = ctxt['n_others_calendars']
            creme_calendars_by_user = ctxt['creme_calendars_by_user']
            creation_perm = ctxt['creation_perm']

        self.assertEqual(self.user.username, user)
        self.assertEqual({str(cal1.id), str(cal2.id)}, set(cal_ids))
        self.assertEqual({act1, act2, act4}, set(floating_acts))
        self.assertEqual({cal1}, set(my_cals))
        self.assertEqual('/activities/calendar/users_activities/', event_url)
        self.assertEqual({other_user: [cal2]}, others_calendars)
        self.assertEqual(1, n_others_calendars)
        filter_key = "%s %s %s" % (other_user.username,
                                   other_user.first_name,
                                   other_user.last_name)
        self.assertEqual(jsondumps({filter_key: [{'name': cal2.name,
                                                  'id': cal2.id}]}), creme_calendars_by_user)
        self.assertEqual(True, creation_perm)



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
        self.assertDoesNotExist(cal)

    def test_delete_calendar03(self):
        "No super user"
        self.login(is_superuser=False)

        user = self.user

        Calendar.get_user_default_calendar(user)
        cal = Calendar.objects.create(user=user, name='Cal #1', is_custom=True)

        self.assertPOST200(self.DEL_CALENDAR_URL, data={'id': cal.id})
        self.assertDoesNotExist(cal)

    def test_delete_calendar04(self): 
        "Other user's calendar"
        self.login(is_superuser=False)

        #user = self.user
        other_user = self.other_user

        Calendar.get_user_default_calendar(other_user)
        cal = Calendar.objects.create(user=other_user, name='Cal #1', is_custom=True)

        self.assertPOST403(self.DEL_CALENDAR_URL, data={'id': cal.id})

    def test_delete_calendar05(self):
        "reassign activities calendars"
        self.login()
        user = self.user

        default_calendar = Calendar.get_user_default_calendar(user)

        cal = Calendar.objects.create(user=user, name='Cal #1', is_custom=True)
        act = Activity.objects.create(user=user, title='Act#1', type_id=ACTIVITYTYPE_TASK)
        act.calendars.add(cal)
        self.assertEqual([cal], list(act.calendars.all()))

        url = self.DEL_CALENDAR_URL
        self.assertPOST200(url, data={'id': cal.id})
        self.assertDoesNotExist(cal)

        act = self.refresh(act)
        self.assertEqual([default_calendar], list(act.calendars.all()))

    def test_change_activity_calendar01(self):
        "Reassign activity calendar"
        self.login()
        user = self.user
        default_calendar = Calendar.get_user_default_calendar(user)

        cal = Calendar.objects.create(user=user, name='Cal #1', is_custom=True)
        act = Activity.objects.create(user=user, title='Act#1', type_id=ACTIVITYTYPE_TASK)
        act.calendars.add(default_calendar)
        self.assertEqual([default_calendar], list(act.calendars.all()))

        activity_url = act.get_absolute_url()
        response = self.assertGET200(activity_url)
        self.assertContains(response, escape(default_calendar.name))

        url = self.build_link_url(act.id)
        self.assertGET200(url)
        response = self.assertPOST200(url, data={'calendar': cal.id})

        self.assertNoFormError(response)

        act = self.refresh(act)
        self.assertEqual([cal], list(act.calendars.all()))
        response = self.assertGET200(activity_url)
        self.assertContains(response, cal.name)

    def test_change_activity_calendar02(self):
        "Multiple calendars => error (waiting the rigth solution)"
        self.login()
        user = self.user
        default_calendar = Calendar.get_user_default_calendar(user)

        create_cal = partial(Calendar.objects.create, user=user, is_custom=True)
        cal1 = create_cal(name='Cal #1')
        cal2 = create_cal(name='Cal #2')

        act = Activity.objects.create(user=user, title='Act#1', type_id=ACTIVITYTYPE_TASK)
        act.calendars = (default_calendar, cal1)

        url = self.build_link_url(act.id)
        self.assertGET409(url)
        self.assertPOST409(url, data={'calendar': cal2.id})

    def test_change_activity_calendar03(self):
        "Credentials: user can always change its calendars"
        self.login(is_superuser=False)
        user = self.user
        default_calendar = Calendar.get_user_default_calendar(user)

        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                        EntityCredentials.DELETE | EntityCredentials.LINK   | EntityCredentials.UNLINK,
                  set_type=SetCredentials.ESET_OWN,
                 )
        create_sc( value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)

        cal = Calendar.objects.create(user=user, name='Cal #1', is_custom=True)

        act = Activity.objects.create(user=self.other_user, title='Act#1', type_id=ACTIVITYTYPE_TASK)
        self.assertFalse(user.has_perm_to_change(act))
        self.assertFalse(user.has_perm_to_link(act))

        act.calendars.add(default_calendar)


        url = self.build_link_url(act.id)
        self.assertGET200(url)
        self.assertNoFormError(self.assertPOST200(url, data={'calendar': cal.id}))
        self.assertEqual([cal], list(act.calendars.all()))

    def test_get_users_activities01(self):
        "One user, no Activity"
        self.login()

        response = self._get_cal_activities([Calendar.get_user_default_calendar(self.user)])
        self.assertEqual('text/javascript', response['Content-Type'])

        with self.assertNoException():
            data = jsonloads(response.content)

        self.assertEqual([], data)

    def test_get_users_activities02(self):
        "One user, several activities"
        self.login()
        user = self.user

        cal = Calendar.get_user_default_calendar(user)
        Calendar.objects.create(user=user, name='Other Cal #1', is_custom=True)

        #start = datetime(year=2013, month=3, day=1)
        #end   = datetime(year=2013, month=3, day=31, hour=23, minute=59)
        create_dt = self.create_datetime
        start = create_dt(year=2013, month=3, day=1)
        end   = create_dt(year=2013, month=3, day=31, hour=23, minute=59)

        create = partial(Activity.objects.create, user=user, type_id=ACTIVITYTYPE_TASK)
        act0 = create(title='Act#0', start=start, end=start)
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

        for act in (act0, act1, act3, act4, act5):
            act.calendars = [cal]

        create_rel = partial(Relation.objects.create, user=user, type_id=REL_SUB_PART_2_ACTIVITY)
        #create_rel(subject_entity=self.contact, object_entity=act3)
        #create_rel(subject_entity=self.other_contact, object_entity=act3)
        create_rel(subject_entity=user.linked_contact,            object_entity=act3)
        create_rel(subject_entity=self.other_user.linked_contact, object_entity=act3)

        response = self._get_cal_activities([cal,],
                                            start=start.strftime('%s'),
                                            end=end.strftime('%s'),
                                           )

        with self.assertNoException():
            data = jsonloads(response.content)

        self.assertEqual(4, len(data))

        def formated_dt(dt):
            return make_naive(dt, get_current_timezone()).isoformat()

        url_fmt = '/activities/activity/%s/popup'
        self.assertEqual({'id':             act1.id,
                          'title':          'Act#1 - Kirika',
                          'allDay':         False,
                          'calendar':       cal.id,
                          'calendar_color': '#%s' % cal.color,
                          # 'start':          act1.start.isoformat(),
                          #'end':             act1.end.isoformat(),
                          'start':          formated_dt(act1.start),
                          'end':            formated_dt(act1.end),
                          'url':            url_fmt % act1.id,
                          # 'entity_color':   '#987654',
                          'editable':       True,
                          'title':          'Act#1',
                          #'type':           u'T\xe2che',
                          'type':           _(u'Task'),
                         },
                         data[0]
                        )
        self.assertEqual({'id':             act3.id,
                          'title':          'Act#3 - Kirika',
                          'allDay':         True,
                          'calendar':       cal.id,
                          'calendar_color': '#%s' % cal.color,
                          # 'start':          act3.start.isoformat(),
                          #'end':             act3.end.isoformat(),
                          'start':          formated_dt(act3.start),
                          'end':            formated_dt(act3.end),
                          'url':            url_fmt % act3.id,
                          # 'entity_color': '#456FFF',
                          'editable':       True,
                          'title':         'Act#3',
                          'type':          _('Meeting'),
                         },
                         data[1]
                        )
        self.assertEqual({'id':             act0.id,
                          'title':          'Act#0 - Kirika',
                          'allDay':         False,
                          'calendar':       cal.id,
                          'calendar_color': '#%s' % cal.color,
                          # 'start':          act3.start.isoformat(),
                          #'end':             act3.end.isoformat(),
                          'start':          formated_dt(act0.start),
                          'end':            formated_dt(act0.end + timedelta(seconds=1)),
                          'url':            url_fmt % act0.id,
                          # 'entity_color':   '#456FFF',
                          'editable':       True,
                          'title':          'Act#0',
                          'type':           _(u'Task'),
                         },
                         data[2]
                        )
        self.assertEqual(act4.id, data[3]['id'])

    def test_get_users_activities03(self):
        "2 Users, 2 Calendars, Indisponibilities"
        self.login()
        user = self.user
        other_user = self.other_user

        #contact1 = self.contact
        #contact2 = self.other_contact

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
        #create_rel(subject_entity=contact2, object_entity=act6)
        #create_rel(subject_entity=contact1, object_entity=act8)
        create_rel(subject_entity=other_user.linked_contact, object_entity=act6)
        create_rel(subject_entity=user.linked_contact,       object_entity=act8)

        response = self._get_cal_activities([cal1, cal2], #cal2 should not be used, it does not belong to user (so, no 'act2')
                                            start=start.strftime('%s'),
                                           )

        with self.assertNoException():
            data = jsonloads(response.content)

        expected = [act1]
        expected_ids  = {act.id for act in expected}
        retrieved_ids = {d['id'] for d in data}
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
                                      title='Act#1', start=start, end=end, floating_type=FLOATING,
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
        self.assertEqual(NARROW,   act.floating_type)

    def test_update_activity_date02(self):
        "Collision"
        self.login()
        user = self.user
        #contact = self.contact
        contact = user.linked_contact

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

    def test_update_activity_date03(self):
        "allDay"
        self.login()

        start = self.create_datetime(year=2013, month=4, day=1, hour=9)
        end   = start + timedelta(hours=2)
        act = Activity.objects.create(user=self.user, type_id=ACTIVITYTYPE_TASK,
                                      title='Act#1', start=start, end=end,
                                     )

        url = self.UPDATE_URL
        self.assertGET404(url)

        self.assertPOST(400, url, data={'id': act.id})
        self.assertPOST200(url, data={'id':     act.id,
                                      'start': self._build_ts(start),
                                      'end': self._build_ts(end),
                                      'allDay': '1',
                                     }
                          )

        act = self.refresh(act)
        self.assertEqual(self.create_datetime(year=2013, month=4, day=1, hour=0), act.start)
        self.assertEqual(self.create_datetime(year=2013, month=4, day=1, hour=23, minute=59),   act.end)

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
        self.assertDoesNotExist(cal2)
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
