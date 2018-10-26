# -*- coding: utf-8 -*-

try:
    from datetime import timedelta, date
    from functools import partial
    from json import dumps as jsondumps # loads as jsonloads

    from django.core.exceptions import ValidationError
    from django.urls import reverse
    from django.utils.encoding import force_text
    from django.utils.html import escape
    from django.utils.timezone import make_naive, get_current_timezone
    from django.utils.translation import ugettext as _

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import Relation, SetCredentials

    from .base import _ActivitiesTestCase, skipIfCustomActivity
    from .. import get_activity_model
    from ..models import Calendar
    from ..constants import *
    from ..utils import get_last_day_of_a_month
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


Activity = get_activity_model()


class CalendarTestCase(_ActivitiesTestCase):
    ADD_URL = reverse('activities__create_calendar')
    CONF_ADD_URL = reverse('creme_config__create_instance', args=('activities', 'calendar'))
    CALENDAR_URL = reverse('activities__calendar')
    DEL_CALENDAR_URL = reverse('activities__delete_calendar')
    UPDATE_URL = reverse('activities__set_activity_dates')

    def assertUserHasDefaultCalendar(self, user):
        return self.get_object_or_fail(Calendar, is_default=True, user=user)

    def _build_ts(self, dt):
        return float(dt.strftime('%s')) * 1000  # Simulates JS that sends milliseconds

    def build_link_url(self, activity_id):
        return reverse('activities__link_calendar', args=(activity_id,))

    def _get_cal_activities(self, calendars, start=None, end=None, status=200):
        # data = {}
        data = {'calendar_id': [str(c.id) for c in calendars]}
        if start: data['start'] = start
        if end:   data['end'] = end

        return self.assertGET(status,
                              reverse('activities__calendars_activities',
                                      # args=(','.join(str(c.id) for c in calendars),)
                                     ),
                              data=data,
                             )

    def test_user_default_calendar01(self):
        user = self.login()

        with self.assertNumQueries(3):
            def_cal = Calendar.get_user_default_calendar(user)

        self.assertEqual(_(u"{user}'s calendar").format(user=user),
                         def_cal.name,
                        )

        def_cal2 = self.assertUserHasDefaultCalendar(user)
        self.assertEqual(def_cal, def_cal2)

    def test_user_default_calendar02(self):
        "Default already exists"
        user = self.login()

        cal1 = Calendar.objects.create(is_default=True, user=user)

        with self.assertNumQueries(1):
            def_cal = Calendar.get_user_default_calendar(user)

        self.assertEqual(cal1, def_cal)

    def test_user_default_calendar03(self):
        "There are several default calendars"
        user = self.login()
        cal1 = Calendar.objects.create(is_default=True, user=user, name='Cal#1')
        cal2 = Calendar.objects.create(user=user, name='Cal#2')
        Calendar.objects.filter(id=cal2.id).update(is_default=True)

        # Be sure that we well managed the automatic save() behaviour
        self.assertEqual(2, Calendar.objects.filter(is_default=True, user=user).count())

        self.assertEqual(cal1, Calendar.get_user_default_calendar(user))
        self.assertFalse(self.refresh(cal2).is_default)

    def test_user_default_calendar04(self):
        "No default Calendar in existing ones."
        user = self.login()
        cal = Calendar.objects.create(user=user, name='Cal #1')
        Calendar.objects.filter(id=cal.id).update(is_default=False)

        # Be sure that we well managed the automatic save() behaviour
        self.assertFalse(Calendar.objects.filter(is_default=True, user=user))

        with self.assertNumQueries(2):
            def_cal = Calendar.get_user_default_calendar(user)

        self.assertEqual(cal, def_cal)
        self.assertTrue(def_cal.is_default)

    def test_get_user_calendars01(self):
        user = self.login()

        with self.assertNumQueries(3):
            cals = Calendar.get_user_calendars(user)

        self.assertEqual(1, len(cals))

        cal = cals[0]
        self.assertIsInstance(cal, Calendar)
        self.assertTrue(cal.is_default)

    def test_get_user_calendars02(self):
        user = self.login()
        Calendar.get_user_default_calendar(user)
        Calendar.objects.create(user=user, name='Cal#2')

        with self.assertNumQueries(1):
            cals = Calendar.get_user_calendars(self.user)

        self.assertEqual(2, len(cals))

    def test_user_calendar01(self):
        user = self.login()

        response = self.assertGET200(self.CALENDAR_URL)
        self.assertTemplateUsed(response, 'activities/calendar.html')

        with self.assertNoException():
            ctxt = response.context
            cal_ids = ctxt['current_calendars']
            floating_acts = ctxt['floating_activities']
            my_cals = ctxt['my_calendars']
            user_name = ctxt['user_username']
            ctxt['events_url']
            ctxt['others_calendars']
            ctxt['n_others_calendars']
            ctxt['creme_calendars_by_user']
            ctxt['creation_perm']

        def_cal = self.assertUserHasDefaultCalendar(user)
        self.assertEqual([str(def_cal.id)], cal_ids)

        self.assertFalse(floating_acts)
        self.assertEqual([def_cal], list(my_cals))
        self.assertEqual(user.username, user_name)

    @skipIfCustomActivity
    def test_user_calendar02(self):
        user = self.login()
        other_user = self.other_user

        create_cal = Calendar.objects.create
        cal1 = create_cal(user=user,       is_default=True, name='Cal #1')
        cal2 = create_cal(user=other_user, is_default=True, name='Cal #2', is_public=True)
        cal3 = create_cal(user=other_user, name='Cal #3', is_public=False)

        create_act = partial(Activity.objects.create, user=user,
                             type_id=ACTIVITYTYPE_TASK, floating_type=FLOATING,
                            )
        act1 = create_act(title='Act#1')
        act2 = create_act(title='Act#2', type_id=ACTIVITYTYPE_MEETING,
                          sub_type_id=ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                         )
        act3 = create_act(title='Act#3', is_deleted=True)
        act4 = create_act(title='Act#4', user=other_user)
        act5 = create_act(title='Act#5', floating_type=NARROW)

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
            user_name = ctxt['user_username']
            event_url = ctxt['events_url']
            others_calendars = ctxt['others_calendars']
            n_others_calendars = ctxt['n_others_calendars']
            creme_calendars_by_user = ctxt['creme_calendars_by_user']
            creation_perm = ctxt['creation_perm']

        self.assertEqual(user.username, user_name)
        self.assertEqual({str(cal1.id), str(cal2.id)}, set(cal_ids))
        self.assertEqual({act1, act2, act4}, set(floating_acts))
        self.assertEqual({cal1}, set(my_cals))
        # self.assertEqual(reverse('activities__calendars_activities', args=('',)), event_url)
        self.assertEqual(reverse('activities__calendars_activities'), event_url)
        self.assertEqual({other_user: [cal2]}, others_calendars)
        self.assertEqual(1, n_others_calendars)
        filter_key = '{} {} {}'.format(other_user.username,
                                       other_user.first_name,
                                       other_user.last_name,
                                      )
        self.assertEqual(jsondumps({filter_key: [{'name': cal2.name, 'id': cal2.id}]}),
                         creme_calendars_by_user
                        )
        self.assertIs(creation_perm, True)

    @skipIfCustomActivity
    def test_user_calendar03(self):
        "Floating activity without calendar (bugfix)"
        user = self.login()

        def create_act(i):
            act = Activity.objects.create(user=user, title='Floating Act#{}'.format(i),
                                          type_id=ACTIVITYTYPE_TASK,
                                          floating_type=FLOATING,
                                         )
            Relation.objects.create(user=user,
                                    subject_entity=user.linked_contact,
                                    type_id=REL_SUB_PART_2_ACTIVITY,
                                    object_entity=act,
                                   )
            return act

        create_act(1)
        act2 = create_act(2)
        act2.calendars.add(Calendar.get_user_default_calendar(user))

        response = self.assertGET200(self.CALENDAR_URL)

        with self.assertNoException():
            floating_acts = response.context['floating_activities']

        self.assertEqual([act2], list(floating_acts))

    def test_add_user_calendar01(self):
        user = self.login()
        self.assertFalse(Calendar.objects.filter(is_default=True, user=user))

        url = self.ADD_URL
        context = self.assertGET200(url).context
        self.assertEqual(_('Create a calendar'), context.get('title'))
        self.assertEqual(_('Save the calendar'), context.get('submit_label'))

        name = 'My pretty calendar'
        color = '009900'
        self.assertNoFormError(self.client.post(url,
                                                data={'name':  name,
                                                      'color': color,
                                                     }
                                               )
                              )

        cals = Calendar.objects.filter(user=user)
        self.assertEqual(1, len(cals))

        cal = cals[0]
        self.assertEqual(name, cal.name)
        self.assertEqual(color, cal.color)
        self.assertIs(cal.is_default, True)
        self.assertIs(cal.is_public, False)
        self.assertIs(cal.is_custom, True)

    def test_add_user_calendar02(self):
        "Only one default calendar"
        user = self.login(is_superuser=False)
        cal1 = Calendar.get_user_default_calendar(user)

        name = 'My pretty calendar'
        self.assertNoFormError(self.client.post(self.ADD_URL,
                                                data={'name': name,
                                                      'is_default': True,
                                                      'is_public': True,
                                                      'color': 'FF0000',
                                                     }
                                               )
                              )

        cal2 = self.get_object_or_fail(Calendar, name=name)
        self.assertTrue(cal2.is_default)
        self.assertTrue(cal2.is_public)
        self.assertFalse(self.refresh(cal1).is_default)

    def test_add_user_calendar03(self):
        "Not allowed"
        self.login(is_superuser=False, allowed_apps=['persons'])
        self.assertGET403(self.ADD_URL)

    def test_edit_user_calendar01(self):
        user = self.login()
        cal = Calendar.get_user_default_calendar(user)
        url = reverse('activities__edit_calendar', args=(cal.id,))
        response = self.assertGET200(url)
        # self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit_popup.html')
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(_('Edit «{}»').format(cal), response.context.get('title'))

        # ---
        name = 'My calendar'
        color = '0000FF'
        self.assertNoFormError(self.client.post(url,
                                                data={'name':  name,
                                                      'color': color,
                                                     },
                                               )
                              )

        cal = self.refresh(cal)
        self.assertEqual(name,  cal.name)
        self.assertEqual(color, cal.color)

    def test_edit_user_calendar02(self):
        "Edit calendar of another user"
        self.login()
        cal = Calendar.get_user_default_calendar(self.other_user)
        self.assertGET403(reverse('activities__edit_calendar', args=(cal.id,)))

    def test_edit_user_calendar03(self):
        "Not super-user"
        user = self.login(is_superuser=False, allowed_apps=['persons', 'activities'])
        cal = Calendar.get_user_default_calendar(user)
        self.assertGET200(reverse('activities__edit_calendar', args=(cal.id,)))

    def test_edit_user_calendar04(self):
        "App credentials needed"
        user = self.login(is_superuser=False, allowed_apps=['persons'])  # 'activities'
        cal = Calendar.get_user_default_calendar(user)
        self.assertGET403(reverse('activities__edit_calendar', args=(cal.id,)))

    def test_delete_calendar01(self):
        "Not custom -> error"
        user = self.login()

        Calendar.get_user_default_calendar(user)
        cal = Calendar.objects.create(user=user, name='Cal #1', is_custom=False)

        url = self.DEL_CALENDAR_URL
        self.assertGET404(url)

        self.assertPOST404(url, data={'id': 1024})

        response = self.assertPOST403(url, data={'id': cal.id})
        self.assertEqual('application/json', response['Content-Type'])
        self.assertEqual(_('You are not allowed to delete this calendar.'),
                         force_text(response.content)
                        )

        self.get_object_or_fail(Calendar, pk=cal.pk)

    def test_delete_calendar02(self):
        user = self.login()

        Calendar.get_user_default_calendar(user)
        cal = Calendar.objects.create(user=user, name='Cal #1', is_custom=True)

        url = self.DEL_CALENDAR_URL
        self.assertGET404(url)
        self.assertPOST200(url, data={'id': cal.id})
        self.assertDoesNotExist(cal)

    def test_delete_calendar03(self):
        "No super user"
        user = self.login(is_superuser=False)

        Calendar.get_user_default_calendar(user)
        cal = Calendar.objects.create(user=user, name='Cal #1', is_custom=True)

        self.assertPOST200(self.DEL_CALENDAR_URL, data={'id': cal.id})
        self.assertDoesNotExist(cal)

    def test_delete_calendar04(self): 
        "Other user's calendar"
        self.login(is_superuser=False)
        other_user = self.other_user

        Calendar.get_user_default_calendar(other_user)
        cal = Calendar.objects.create(user=other_user, name='Cal #1', is_custom=True)

        self.assertPOST403(self.DEL_CALENDAR_URL, data={'id': cal.id})

    @skipIfCustomActivity
    def test_delete_calendar05(self):
        "reassign activities calendars"
        user = self.login()
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

    @skipIfCustomActivity
    def test_change_activity_calendar01(self):
        "Reassign activity calendar"
        user = self.login()
        default_calendar = Calendar.get_user_default_calendar(user)

        cal = Calendar.objects.create(user=user, name='Cal #1', is_custom=True)
        act = Activity.objects.create(user=user, title='Act#1', type_id=ACTIVITYTYPE_TASK)
        act.calendars.add(default_calendar)
        self.assertEqual([default_calendar], list(act.calendars.all()))

        activity_url = act.get_absolute_url()
        response = self.assertGET200(activity_url)
        self.assertContains(response, escape(default_calendar.name))

        url = self.build_link_url(act.id)
        response = self.assertGET200(url)
        # self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit_popup.html')
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')
        # self.assertEqual(_('Change calendar of «%s»') % act,
        self.assertEqual(_('Change calendar of «{}»').format(act),
                         response.context.get('title')
                        )

        response = self.assertPOST200(url, data={'calendar': cal.id})
        self.assertNoFormError(response)

        act = self.refresh(act)
        self.assertEqual([cal], list(act.calendars.all()))
        response = self.assertGET200(activity_url)
        self.assertContains(response, cal.name)

    @skipIfCustomActivity
    def test_change_activity_calendar02(self):
        "Multiple calendars => error (waiting the rigth solution)"
        user = self.login()
        default_calendar = Calendar.get_user_default_calendar(user)

        create_cal = partial(Calendar.objects.create, user=user, is_custom=True)
        cal1 = create_cal(name='Cal #1')
        cal2 = create_cal(name='Cal #2')

        act = Activity.objects.create(user=user, title='Act#1', type_id=ACTIVITYTYPE_TASK)
        # act.calendars = (default_calendar, cal1)
        act.calendars.set([default_calendar, cal1])

        url = self.build_link_url(act.id)
        self.assertGET409(url)
        self.assertPOST409(url, data={'calendar': cal2.id})

    @skipIfCustomActivity
    def test_change_activity_calendar03(self):
        "Credentials: user can always change its calendars"
        user = self.login(is_superuser=False)
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

    def test_change_activity_calendar04(self):
        "App credentials needed"
        user = self.login(is_superuser=False, allowed_apps=['creme_core'])
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_ALL,
        )

        act = Activity.objects.create(user=self.other_user,
                                      title='Act#1', type_id=ACTIVITYTYPE_TASK,
                                     )
        act.calendars.add(Calendar.get_user_default_calendar(user))
        self.assertGET403(self.build_link_url(act.id))

    def test_get_users_activities01(self):
        "One user, no Activity"
        user = self.login()

        response = self._get_cal_activities([Calendar.get_user_default_calendar(user)])
        self.assertEqual('application/json', response['Content-Type'])
        self.assertEqual([], response.json())

    @skipIfCustomActivity
    def test_get_users_activities02(self):
        "One user, several activities"
        user = self.login()
        cal = Calendar.get_user_default_calendar(user)
        Calendar.objects.create(user=user, name='Other Cal #1', is_custom=True)

        create_dt = self.create_datetime
        start = create_dt(year=2013, month=3, day=1)
        end   = create_dt(year=2013, month=3, day=31, hour=23, minute=59)

        create = partial(Activity.objects.create, user=user, type_id=ACTIVITYTYPE_TASK)
        act0 = create(title='Act#0', start=start, end=start)
        act1 = create(title='Act#1', start=start + timedelta(days=1), end=start + timedelta(days=2))
        act2 = create(title='Act#2', start=start + timedelta(days=1), end=start + timedelta(days=2))  # Not in calendar
        act3 = create(title='Act#3', start=start + timedelta(days=2), end=end   + timedelta(days=1),  # Start OK
                      is_all_day=True, type_id=ACTIVITYTYPE_MEETING, 
                      sub_type_id=ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                     )
        act4 = create(title='Act#4', start=start - timedelta(days=1), end=start + timedelta(days=3))  # End OK
        act5 = create(title='Act#5', start=start + timedelta(days=5), end=start + timedelta(days=5, hours=3),
                      is_deleted=True,
                     )

        for act in (act0, act1, act3, act4, act5):
            # act.calendars = [cal]
            act.calendars.set([cal])

        create_rel = partial(Relation.objects.create, user=user, type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(subject_entity=user.linked_contact,            object_entity=act3)
        create_rel(subject_entity=self.other_user.linked_contact, object_entity=act3)

        response = self._get_cal_activities([cal],
                                            start=start.strftime('%s'),
                                            end=end.strftime('%s'),
                                           )

        # with self.assertNoException():
        #     data = jsonloads(response.content)
        data = response.json()

        self.assertEqual(4, len(data))

        def formatted_dt(dt):
            return make_naive(dt, get_current_timezone()).isoformat()

        def build_popup_url(act):
            return reverse('activities__view_activity_popup', args=(act.id,))

        self.assertEqual({'id':             act3.id,
                          'title':         'Act#3',
                          'start':          formatted_dt(act3.start),
                          'end':            formatted_dt(act3.end),
                          'allDay':         True,
                          'calendar':       cal.id,
                          'calendar_color': '#{}'.format(cal.color),
                          'url':            build_popup_url(act3),
                          'editable':       True,
                          'type':           _('Meeting'),
                         },
                         data[0]
                        )
        self.assertEqual({'id':             act1.id,
                          'title':          'Act#1',
                          'start':          formatted_dt(act1.start),
                          'end':            formatted_dt(act1.end),
                          'allDay':         False,
                          'calendar':       cal.id,
                          'calendar_color': '#{}'.format(cal.color),
                          'url':            build_popup_url(act1),
                          'editable':       True,
                          'type':           _(u'Task'),
                         },
                         data[1]
                        )
        self.assertEqual({'id':             act0.id,
                          'title':          'Act#0',
                          'start':          formatted_dt(act0.start),
                          'end':            formatted_dt(act0.end + timedelta(seconds=1)),
                          'allDay':         False,
                          'calendar':       cal.id,
                          'calendar_color': '#{}'.format(cal.color),
                          'url':            build_popup_url(act0),
                          'editable':       True,
                          'type':           _(u'Task'),
                         },
                         data[2]
                        )
        self.assertEqual(act4.id, data[3]['id'])

    @skipIfCustomActivity
    def test_get_users_activities03(self):
        "2 Users, 2 Calendars, Unavailability"
        user = self.login()
        other_user = self.other_user

        cal1 = Calendar.get_user_default_calendar(user)
        cal2 = Calendar.get_user_default_calendar(other_user)
        cal3 = Calendar.objects.create(user=other_user, name='Cal #3',
                                       is_custom=True, is_default=False,
                                       is_public=True,
                                      )
        self.assertFalse(cal2.is_public)

        start = self.create_datetime(year=2013, month=4, day=1)

        create = partial(Activity.objects.create, user=user, type_id=ACTIVITYTYPE_TASK)
        act1 = create(title='Act#1', start=start + timedelta(days=1),  end=start + timedelta(days=2))
        act2 = create(title='Act#2', start=start + timedelta(days=1),  end=start + timedelta(days=2))  # Not in [cal1, cal3]
        act3 = create(title='Act#3', start=start + timedelta(days=32), end=start + timedelta(days=33))  # Start KO
        act4 = create(title='Act#4', start=start + timedelta(days=29), end=start + timedelta(days=30))

        # act1.calendars = [cal1]
        # act2.calendars = [cal2]
        # act3.calendars = [cal3]
        # act4.calendars = [cal3]
        act1.calendars.set([cal1])
        act2.calendars.set([cal2])
        act3.calendars.set([cal3])
        act4.calendars.set([cal3])

        create_ind = partial(Activity.objects.create, user=user, type_id=ACTIVITYTYPE_INDISPO)
        act6 = create_ind(title='Ind#1', start=start + timedelta(days=5), end=start + timedelta(days=6))
        act7 = create_ind(title='Ind#2', start=start + timedelta(days=7), end=start + timedelta(days=8))  # Not linked
        act8 = create_ind(title='Ind#3', start=start + timedelta(days=9), end=start + timedelta(days=10))

        create_rel = partial(Relation.objects.create, user=user, type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(subject_entity=other_user.linked_contact, object_entity=act6)
        create_rel(subject_entity=user.linked_contact,       object_entity=act8)

        # cal2 should not be used, it does not belong to user (so, no 'act2')
        response = self._get_cal_activities([cal1, cal2],
                                            start=start.strftime('%s'),
                                           )

        # with self.assertNoException():
        #     data = jsonloads(response.content)
        data = response.json()

        expected = [act1]
        expected_ids  = {act.id for act in expected}
        retrieved_ids = {d['id'] for d in data}
        self.assertEqual(expected_ids, retrieved_ids,
                         '{} != {} (id map: {})'.format(expected_ids, retrieved_ids,
                                                        ['{} -> {}'.format(act.id, act.title) for act in expected]
                                                       )
                        )

    # @skipIfCustomActivity
    # def test_get_users_activities_legacy(self):
    #     "One user, several activities (deprecated version without GET parameter)"
    #     user = self.login()
    #     cal = Calendar.get_user_default_calendar(user)
    #     Calendar.objects.create(user=user, name='Other Cal #1', is_custom=True)
    #
    #     create_dt = self.create_datetime
    #     start = create_dt(year=2013, month=3, day=1)
    #     end   = create_dt(year=2013, month=3, day=31, hour=23, minute=59)
    #
    #     create = partial(Activity.objects.create, user=user, type_id=ACTIVITYTYPE_TASK)
    #     act0 = create(title='Act#0', start=start, end=start)
    #     act1 = create(title='Act#1', start=start + timedelta(days=1), end=start + timedelta(days=2))
    #     act2 = create(title='Act#2', start=start + timedelta(days=1), end=start + timedelta(days=2))  # Not in calendar
    #     act3 = create(title='Act#3', start=start + timedelta(days=2), end=end   + timedelta(days=1),  # Start OK
    #                   is_all_day=True, type_id=ACTIVITYTYPE_MEETING,
    #                   sub_type_id=ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
    #                  )
    #     act4 = create(title='Act#4', start=start - timedelta(days=1), end=start + timedelta(days=3))  # End OK
    #     act5 = create(title='Act#5', start=start + timedelta(days=5), end=start + timedelta(days=5, hours=3),
    #                   is_deleted=True,
    #                  )
    #
    #     for act in (act0, act1, act3, act4, act5):
    #         # act.calendars = [cal]
    #         act.calendars.set([cal])
    #
    #     create_rel = partial(Relation.objects.create, user=user, type_id=REL_SUB_PART_2_ACTIVITY)
    #     create_rel(subject_entity=user.linked_contact,            object_entity=act3)
    #     create_rel(subject_entity=self.other_user.linked_contact, object_entity=act3)
    #
    #     response = self.assertGET200(reverse('activities__calendars_activities', args=(cal.id,)),
    #                                  data={
    #                                      'start': start.strftime('%s'),
    #                                      'end':   end.strftime('%s'),
    #                                  },
    #                                 )
    #
    #     # with self.assertNoException():
    #     #     data = jsonloads(response.content)
    #     data = response.json()
    #     self.assertEqual(4, len(data))
    #
    #     def formatted_dt(dt):
    #         return make_naive(dt, get_current_timezone()).isoformat()
    #
    #     def build_popup_url(act):
    #         return reverse('activities__view_activity_popup', args=(act.id,))
    #
    #     self.assertEqual({'id':             act3.id,
    #                       'title':         'Act#3',
    #                       'start':          formatted_dt(act3.start),
    #                       'end':            formatted_dt(act3.end),
    #                       'allDay':         True,
    #                       'calendar':       cal.id,
    #                       'calendar_color': '#%s' % cal.color,
    #                       'url':            build_popup_url(act3),
    #                       'editable':       True,
    #                       'type':           _('Meeting'),
    #                      },
    #                      data[0]
    #                     )
    #     self.assertEqual({'id':             act1.id,
    #                       'title':          'Act#1',
    #                       'start':          formatted_dt(act1.start),
    #                       'end':            formatted_dt(act1.end),
    #                       'allDay':         False,
    #                       'calendar':       cal.id,
    #                       'calendar_color': '#%s' % cal.color,
    #                       'url':            build_popup_url(act1),
    #                       'editable':       True,
    #                       'type':           _(u'Task'),
    #                      },
    #                      data[1]
    #                     )
    #     self.assertEqual({'id':             act0.id,
    #                       'title':          'Act#0',
    #                       'start':          formatted_dt(act0.start),
    #                       'end':            formatted_dt(act0.end + timedelta(seconds=1)),
    #                       'allDay':         False,
    #                       'calendar':       cal.id,
    #                       'calendar_color': '#%s' % cal.color,
    #                       'url':            build_popup_url(act0),
    #                       'editable':       True,
    #                       'type':           _(u'Task'),
    #                      },
    #                      data[2]
    #                     )
    #     self.assertEqual(act4.id, data[3]['id'])

    @skipIfCustomActivity
    def test_update_activity_date01(self):
        user = self.login()

        start = self.create_datetime(year=2013, month=4, day=1, hour=9)
        end   = start + timedelta(hours=2)
        act = Activity.objects.create(user=user, type_id=ACTIVITYTYPE_TASK,
                                      title='Act#1', start=start, end=end, floating_type=FLOATING,
                                     )

        url = self.UPDATE_URL
        self.assertGET404(url)

        offset = timedelta(days=1, hours=2)
        new_start = start + offset
        new_end   = end  + offset
        self.assertPOST(400, url, data={'id': act.id})
        self.assertPOST200(url, data={'id':    act.id,
                                      'start': self._build_ts(new_start),
                                      'end':   self._build_ts(new_end),
                                     }
                          )

        act = self.refresh(act)
        self.assertEqual(new_start, act.start)
        self.assertEqual(new_end,   act.end)
        self.assertEqual(NARROW,    act.floating_type)

    @skipIfCustomActivity
    def test_update_activity_date02(self):
        "Collision"
        user = self.login()
        contact = user.linked_contact

        create_act = partial(Activity.objects.create, user=user,
                             type_id=ACTIVITYTYPE_TASK, busy=True,
                            )
        create_dt = self.create_datetime
        act1 = create_act(title='Act#1',
                          start=create_dt(year=2013, month=4, day=1, hour=9),
                          end=create_dt(year=2013,   month=4, day=1, hour=10),
                         )
        act2 = create_act(title='Act#2',
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

    @skipIfCustomActivity
    def test_update_activity_date03(self):
        "allDay"
        user = self.login()

        start = self.create_datetime(year=2013, month=4, day=1, hour=9)
        end   = start + timedelta(hours=2)
        act = Activity.objects.create(user=user, type_id=ACTIVITYTYPE_TASK,
                                      title='Act#1', start=start, end=end,
                                     )

        url = self.UPDATE_URL
        self.assertGET404(url)

        self.assertPOST(400, url, data={'id': act.id})
        self.assertPOST200(url, data={'id':     act.id,
                                      'start':  self._build_ts(start),
                                      'end':    self._build_ts(end),
                                      'allDay': '1',
                                     }
                          )

        act = self.refresh(act)
        create_dt = partial(self.create_datetime, year=2013, month=4, day=1)
        self.assertEqual(create_dt(hour=0),             act.start)
        self.assertEqual(create_dt(hour=23, minute=59), act.end)

    def test_config01(self):
        user = self.login()

        self.assertGET200(reverse('creme_config__app_portal', args=('activities',)))
        self.assertGET200(reverse('creme_config__model_portal', args=('activities', 'calendar')))

        url = self.CONF_ADD_URL
        self.assertGET200(url)

        name = 'My Cal'
        color = '998877'
        self.assertNoFormError(self.client.post(url, data={'name': name,
                                                           'user': user.id,
                                                           'color': color,
                                                          }
                                               )
                              )

        cal = self.get_object_or_fail(Calendar, name=name, user=user)
        self.assertEqual(color, cal.color)
        self.assertTrue(cal.is_default)
        self.assertTrue(cal.is_custom)
        self.assertFalse(cal.is_public)

    def test_config02(self): 
        "Only one default"
        user = self.login()
        cal1 = Calendar.get_user_default_calendar(user)

        name = 'My default Cal'
        self.assertNoFormError(self.client.post(self.CONF_ADD_URL,
                                                data={'name': name,
                                                      'user': user.id,
                                                      'is_default': True,
                                                      'is_public': True,
                                                      'color': '0000FF',
                                                     }
                                               )
                              )

        cal2 = self.get_object_or_fail(Calendar, name=name, user=user)
        self.assertTrue(cal2.is_default)
        self.assertTrue(cal2.is_custom)
        self.assertTrue(cal2.is_public)

        self.assertFalse(self.refresh(cal1).is_default)

        cal3 = Calendar.objects.create(user=user, name='My third calendar')

        # Delete
        self.assertPOST200(reverse('creme_config__delete_instance', args=('activities', 'calendar')),
                           data={'id': cal2.id},
                          )
        self.assertDoesNotExist(cal2)
        self.assertTrue(self.refresh(cal1).is_default)
        self.assertFalse(self.refresh(cal3).is_default)

    def test_config03(self): 
        "Edition"
        user = self.login()
        cal1 = Calendar.get_user_default_calendar(user)

        name = 'cal#1'
        cal2 = Calendar.objects.create(user=user, name=name)

        url = reverse('creme_config__edit_instance', args=('activities', 'calendar', cal2.id))
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('user', fields)

        name = name.title()
        color = '0000FF'
        self.assertNoFormError(self.client.post(url,
                                                data={'name': name,
                                                      'is_default': True,
                                                      'is_public': True,
                                                      'color': color,
                                                     }
                                               )
                              )

        cal2 = self.refresh(cal2)
        self.assertEqual(name,  cal2.name)
        self.assertEqual(color, cal2.color)
        self.assertTrue(cal2.is_default)
        self.assertTrue(cal2.is_public)

        self.assertFalse(self.refresh(cal1).is_default)

    def test_colorfield(self):
        user = self.login()
        cal = Calendar.get_user_default_calendar(user)

        cal.color = 'FF0000'
        with self.assertNoException():
            cal.full_clean()

        cal.color = 'ZZ0000'
        self.assertRaises(ValidationError, cal.full_clean)

    def test_delete_user(self):
        """The User who receives the Calendars from the deleted User should keep
        his default Calendar.
        """
        user = self.login()
        other_user = self.other_user

        cal11 = Calendar.get_user_default_calendar(user)
        cal12 = Calendar.objects.create(user=user, name='Cal#12')
        cal21 = Calendar.get_user_default_calendar(other_user)
        cal22 = Calendar.objects.create(user=other_user, name='Cal#22')
        self.assertTrue(self.refresh(cal11).is_default)
        self.assertFalse(self.refresh(cal12).is_default)
        self.assertTrue(self.refresh(cal21).is_default)
        self.assertFalse(self.refresh(cal22).is_default)

        url = reverse('creme_config__delete_user', args=(other_user.id,))
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(url, {'to_user': user.id}))
        self.assertDoesNotExist(other_user)

        self.assertEqual({cal11.id, cal12.id, cal21.id, cal22.id},
                         set(Calendar.objects.filter(user=user).values_list('id', flat=True))
                        )
        self.assertTrue(self.refresh(cal11).is_default)
        self.assertFalse(self.refresh(cal12).is_default)
        self.assertFalse(self.refresh(cal21).is_default)
        self.assertFalse(self.refresh(cal22).is_default)

    def test_get_last_day_of_a_month(self):
        self.assertEqual(date(year=2016, month=1, day=31),
                         get_last_day_of_a_month(date(year=2016, month=1, day=1))
                        )
        self.assertEqual(date(year=2016, month=1, day=31),
                         get_last_day_of_a_month(date(year=2016, month=1, day=18))
                        )

        # Other 31 days
        self.assertEqual(date(year=2016, month=3, day=31),
                         get_last_day_of_a_month(date(year=2016, month=3, day=17))
                        )

        # 30 days
        self.assertEqual(date(year=2016, month=4, day=30),
                         get_last_day_of_a_month(date(year=2016, month=4, day=17))
                        )
        self.assertEqual(date(year=2016, month=4, day=30),
                         get_last_day_of_a_month(date(year=2016, month=4, day=30))
                        )

        # February
        self.assertEqual(date(year=2016, month=2, day=29),
                         get_last_day_of_a_month(date(year=2016, month=2, day=17))
                        )
        self.assertEqual(date(year=2015, month=2, day=28),
                         get_last_day_of_a_month(date(year=2015, month=2, day=17))
                        )
