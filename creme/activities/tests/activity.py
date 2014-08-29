# -*- coding: utf-8 -*-

try:
    from datetime import datetime, date, time # timedelta
    from functools import partial

    from django.forms.util import ValidationError
    from django.utils.encoding import force_unicode
    from django.utils.formats import date_format
    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType
    #from django.utils.simplejson.encoder import JSONEncoder
    from django.utils.timezone import now, get_current_timezone, make_naive

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import RelationType, Relation, SetCredentials, EntityFilter
    from creme.creme_core.constants import REL_SUB_HAS
    from creme.creme_core.utils import create_or_update

    from creme.creme_config.models import SettingKey, SettingValue

    from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES
    from creme.persons.models import Contact, Organisation

    from creme.assistants.models import Alert

    from .base import _ActivitiesTestCase
    from ..models import *
    from ..constants import *
    from ..utils import check_activity_collisions
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('ActivityTestCase',)


class ActivityTestCase(_ActivitiesTestCase):
    ADD_URL         = '/activities/activity/add'
    ADD_POPUP_URL   = '/activities/activity/add_popup'
    ADD_INDISPO_URL = '/activities/activity/add_indispo'
    DEL_ACTTYPE_URL = '/creme_config/activities/activity_type/delete'
    GET_TYPES    = '/activities/type/%s/json'

    def _buid_add_participants_url(self, activity):
        return '/activities/activity/%s/participant/add' % activity.id

    def _build_add_related_uri(self, related, act_type_id=None):
        return '/activities/activity/add_related/%(entity)s%(type_arg)s' % {
                    'entity':   related.id,
                    'type_arg': '' if not act_type_id else '?activity_type=%s' % act_type_id,
                }

    def _buid_add_subjects_url(self, activity):
        return '/activities/activity/%s/subject/add' % activity.id

    def _buid_edit_url(self, activity):
        return '/activities/activity/edit/%s' % activity.id

    def _build_nolink_setcreds(self):
        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(value=EntityCredentials.LINK, set_type=SetCredentials.ESET_OWN)
        create_sc(value=EntityCredentials.VIEW | EntityCredentials.CHANGE |
                  EntityCredentials.DELETE     | EntityCredentials.UNLINK, #not LINK
                  set_type=SetCredentials.ESET_ALL,
                 )

    def _create_meeting(self, title='Meeting01', subtype_id=ACTIVITYSUBTYPE_MEETING_NETWORK, hour=14):
        create_dt = self.create_datetime
        return Activity.objects.create(user=self.user, title=title,
                                       type_id=ACTIVITYTYPE_MEETING, sub_type_id=subtype_id,
                                       start=create_dt(year=2013, month=4, day=1, hour=hour,     minute=0),
                                       end=create_dt(year=2013,   month=4, day=1, hour=hour + 1, minute=0),
                                      )

    def _create_phonecall(self, title='Call01', subtype_id=ACTIVITYSUBTYPE_PHONECALL_OUTGOING, hour=14):
        create_dt = self.create_datetime
        return Activity.objects.create(user=self.user, title=title,
                                       type_id=ACTIVITYTYPE_PHONECALL, sub_type_id=subtype_id,
                                       start=create_dt(year=2013, month=4, day=1, hour=hour, minute=0),
                                       end=create_dt(year=2013,   month=4, day=1, hour=hour, minute=15),
                                      )

    def _create_task(self, title='Task01', day=1):
        create_dt = self.create_datetime
        return Activity.objects.create(user=self.user, title=title,
                                       type_id=ACTIVITYTYPE_TASK,
                                       start=create_dt(year=2013, month=4, day=day, hour=8,  minute=0),
                                       end=create_dt(year=2013,   month=4, day=day, hour=18, minute=0),
                                      )

    #def _acttype_field_value(self, atype_id, subtype_id=None):
        #return JSONEncoder().encode({'type': atype_id, 'sub_type': subtype_id})

    #def _relation_field_value(self, entity):
        #return '[{"ctype":"%s", "entity":"%s"}]' % (entity.entity_type_id, entity.id)
    def _relation_field_value(self, *entities):
        return '[%s]' % ','.join('{"ctype":"%s", "entity":"%s"}' % (entity.entity_type_id, entity.id)
                                    for entity in entities
                                )

    def test_populate(self):
        rtypes_pks = [REL_SUB_LINKED_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT, REL_SUB_PART_2_ACTIVITY]
        self.assertEqual(len(rtypes_pks), RelationType.objects.filter(pk__in=rtypes_pks).count())

        acttypes_pks = [ACTIVITYTYPE_TASK, ACTIVITYTYPE_MEETING, ACTIVITYTYPE_PHONECALL,
                        ACTIVITYTYPE_GATHERING, ACTIVITYTYPE_SHOW, ACTIVITYTYPE_DEMO,
                        ACTIVITYTYPE_INDISPO,
                       ]
        self.assertEqual(len(acttypes_pks),
                         ActivityType.objects.filter(pk__in=acttypes_pks).count()
                        )

        subtype_ids = [ACTIVITYSUBTYPE_PHONECALL_INCOMING, ACTIVITYSUBTYPE_PHONECALL_OUTGOING,
                     ACTIVITYSUBTYPE_PHONECALL_CONFERENCE, ACTIVITYSUBTYPE_MEETING_NETWORK,
                     ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                    ]
        self.assertEqual(len(subtype_ids),
                         ActivitySubType.objects.filter(pk__in=subtype_ids).count()
                        )

        #Filters
        self.login() #user
        acts = [self._create_meeting('Meeting01', subtype_id=ACTIVITYSUBTYPE_MEETING_NETWORK, hour=14),
                self._create_meeting('Meeting02', subtype_id=ACTIVITYSUBTYPE_MEETING_REVIVAL, hour=15),
                self._create_phonecall('Call01', subtype_id=ACTIVITYSUBTYPE_PHONECALL_OUTGOING, hour=14),
                self._create_phonecall('Call02', subtype_id=ACTIVITYSUBTYPE_PHONECALL_OUTGOING, hour=15),
                self._create_task('Task01', day=1),
                self._create_task('Task02', day=2),
               ]

        def check_content(efilter, *expected_titles):
            titles = set(efilter.filter(Activity.objects.all()).values_list('title', flat=True))

            for activity in acts:
                title = activity.title
                if title in expected_titles:
                    self.assertIn(title, titles)
                else:
                    self.assertNotIn(title, titles)

        efilter = self.get_object_or_fail(EntityFilter, pk=EFILTER_MEETINGS)
        self.assertFalse(efilter.is_custom)
        check_content(efilter, 'Meeting01', 'Meeting02')

        efilter = self.get_object_or_fail(EntityFilter, pk=EFILTER_PHONECALLS)
        check_content(efilter, 'Call01', 'Call02')

        efilter = self.get_object_or_fail(EntityFilter, pk=EFILTER_TASKS)
        check_content(efilter, 'Task01', 'Task02')

        sk = self.get_object_or_fail(SettingKey, pk=DISPLAY_REVIEW_ACTIVITIES_BLOCKS)
        sv = self.get_object_or_fail(SettingValue, key=sk)
        self.assertIsNone(sv.user)
        self.assertIs(sv.value, True)

        sk = self.get_object_or_fail(SettingKey, pk=SETTING_AUTO_ORGA_SUBJECTS)
        sv = self.get_object_or_fail(SettingValue, key=sk)
        self.assertIsNone(sv.user)
        self.assertIs(sv.value, True)

    def test_portal(self):
        self.login()
        self.assertGET200('/activities/')

    def test_createview01(self):
        self.login()

        #me = self.contact
        user = self.user

        create_contact = partial(Contact.objects.create, user=user)
        ranma = create_contact(first_name='Ranma', last_name='Saotome')
        genma = create_contact(first_name='Genma', last_name='Saotome')

        dojo = Organisation.objects.create(user=user, name='Dojo')

        url = self.ADD_URL
        self.assertGET200(url)

        title  = 'My task'
        status = Status.objects.all()[0]
        my_calendar = Calendar.get_user_default_calendar(user)
        response = self.client.post(url, follow=True,
                                    data={'user':               user.pk,
                                          'title':              title,
                                          'type_selector':      self._acttype_field_value(ACTIVITYTYPE_TASK),
                                          'status':             status.pk,
                                          'start':              '2010-1-10',
                                          'start_time':         '17:30:00',
                                          'end':                '2010-1-10',
                                          'end_time':           '18:45:00',
                                          'my_participation':   True,
                                          'my_calendar':        my_calendar.pk,
                                          'other_participants': '[%d]' % genma.id,
                                          'subjects':           self._relation_field_value(ranma),
                                          'linked_entities':    self._relation_field_value(dojo),
                                         }
                                   )
        self.assertNoFormError(response)

        act = self.get_object_or_fail(Activity, type=ACTIVITYTYPE_TASK, title=title)
        self.assertIsNone(act.sub_type)
        self.assertEqual(status, act.status)
        self.assertEqual(NARROW, act.floating_type)
        self.assertEqual(self.create_datetime(year=2010, month=1, day=10, hour=17, minute=30),
                         act.start,
                        )
        self.assertEqual(self.create_datetime(year=2010, month=1, day=10, hour=18, minute=45),
                         act.end,
                        )

        self.assertEqual(4 * 2, Relation.objects.count()) # * 2: relations have their symmetric ones

        #self.assertRelationCount(1, me,    REL_SUB_PART_2_ACTIVITY,   act)
        self.assertRelationCount(1, user.linked_contact, REL_SUB_PART_2_ACTIVITY,   act)
        self.assertRelationCount(1, genma,               REL_SUB_PART_2_ACTIVITY,   act)
        self.assertRelationCount(1, ranma,               REL_SUB_ACTIVITY_SUBJECT,  act)
        self.assertRelationCount(1, dojo,                REL_SUB_LINKED_2_ACTIVITY, act)

    def test_createview02(self):
        "Credentials errors"
        #self.login(is_superuser=False, other_is_owner=True)
        self.login(is_superuser=False)
        self._build_nolink_setcreds()
        self.role.creatable_ctypes = [ContentType.objects.get_for_model(Activity)]

        user = self.user
        other_user = self.other_user

        #kirika   = self.other_contact

        #mireille = self.contact
        mireille = user.linked_contact
        mireille.user = other_user
        mireille.save()

        self.assertFalse(user.has_perm_to_link(mireille))

        create_contact = partial(Contact.objects.create, user=other_user)
        genma = create_contact(first_name='Genma', last_name='Saotome')
        akane = create_contact(first_name='Akane', last_name='Tendo')

        dojo = Organisation.objects.create(user=other_user, name='Dojo')

        my_calendar = Calendar.get_user_default_calendar(user)
        response = self.assertPOST200(self.ADD_URL, follow=True,
                                      data={'user':                user.pk,
                                            'title':               'Fight !!',
                                            'type_selector':       self._acttype_field_value(ACTIVITYTYPE_MEETING,
                                                                                             ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                                                                                            ),
                                            'start':               '2011-2-22',
                                            'my_participation':    True,
                                            'my_calendar':         my_calendar.pk,
                                            'participating_users': other_user.pk,
                                            'other_participants':  '[%d]' % genma.id,
                                            'subjects':            self._relation_field_value(akane),
                                            'linked_entities':     self._relation_field_value(dojo),
                                           }
                                     )
        self.assertFormError(response, 'form', 'my_participation',
                             #_(u'You are not allowed to link this entity: %s') % kirika
                             _(u'You are not allowed to link this entity: %s') % mireille
                            )

        msg = _(u'Some entities are not linkable: %s')
        #self.assertFormError(response, 'form', 'participating_users', msg % mireille)
        #self.assertFormError(response, 'form', 'participating_users', msg % kirika)
        self.assertFormError(response, 'form', 'participating_users', msg % other_user.linked_contact)
        self.assertFormError(response, 'form', 'other_participants',  msg % genma)
        self.assertFormError(response, 'form', 'subjects',            msg % akane)
        self.assertFormError(response, 'form', 'linked_entities',     msg % dojo)

    def test_createview03(self):
        "No end given ; auto subjects"
        self.login()
        #me   = self.contact
        user = self.user
        me   = user.linked_contact

        create_contact = partial(Contact.objects.create, user=user)
        ranma = create_contact(first_name='Ranma', last_name='Saotome')
        genma = create_contact(first_name='Genma', last_name='Saotome')
        akane = create_contact(first_name='Akane', last_name='Tendo')

        create_orga = partial(Organisation.objects.create, user=user)
        dojo_t = create_orga(name='Tendo Dojo')
        dojo_s = create_orga(name='Saotome Dojo')
        school = create_orga(name='Furinkan High')
        rest   = create_orga(name='Okonomiyaki tenshi')

        mngd = Organisation.get_all_managed_by_creme()[0]

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=me,    type_id=REL_SUB_EMPLOYED_BY, object_entity=mngd)
        create_rel(subject_entity=ranma, type_id=REL_SUB_EMPLOYED_BY, object_entity=dojo_s)
        create_rel(subject_entity=akane, type_id=REL_SUB_EMPLOYED_BY, object_entity=school)
        create_rel(subject_entity=akane, type_id=REL_SUB_EMPLOYED_BY, object_entity=dojo_t)
        create_rel(subject_entity=genma, type_id=REL_SUB_MANAGES,     object_entity=school) # 2 employes for the same organisations
        create_rel(subject_entity=genma, type_id=REL_SUB_EMPLOYED_BY, object_entity=rest)

        title  = 'My training'
        status = Status.objects.all()[0]
        my_calendar = Calendar.get_user_default_calendar(user)
        type_id = 'activities-activity_custom_1'
        ActivityType.objects.create(pk=type_id, name='Karate session',
                                    default_day_duration=1, default_hour_duration="00:15:00",
                                    is_custom=True,
                                   )
        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'user':               user.pk,
                                          'title':              title,
                                          'status':             status.pk,
                                          'start':              '2013-3-26',
                                          'start_time':         '12:10:00',
                                          'my_participation':   True,
                                          'my_calendar':        my_calendar.pk,
                                          'other_participants': '[%d, %s]' % (genma.id, akane.id),
                                          'subjects':           self._relation_field_value(ranma, rest),
                                          'linked_entities':    self._relation_field_value(dojo_s),
                                          'type_selector':      self._acttype_field_value(type_id),
                                         }
                                   )
        self.assertNoFormError(response)

        act = self.get_object_or_fail(Activity, type=type_id, title=title)
        self.assertEqual(status, act.status)
        
        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2013, month=3, day=26, hour=12, minute=10), act.start)
        self.assertEqual(create_dt(year=2013, month=3, day=27, hour=12, minute=25), act.end)

        self.assertRelationCount(1, me,     REL_SUB_PART_2_ACTIVITY,   act)
        self.assertRelationCount(1, genma,  REL_SUB_PART_2_ACTIVITY,   act)
        self.assertRelationCount(1, akane,  REL_SUB_PART_2_ACTIVITY,   act)
        self.assertRelationCount(1, ranma,  REL_SUB_ACTIVITY_SUBJECT,  act)
        self.assertRelationCount(1, dojo_s, REL_SUB_LINKED_2_ACTIVITY, act)
        self.assertRelationCount(0, dojo_s, REL_SUB_ACTIVITY_SUBJECT,  act)
        self.assertRelationCount(1, dojo_t, REL_SUB_ACTIVITY_SUBJECT,  act) #auto subject #1
        self.assertRelationCount(1, school, REL_SUB_ACTIVITY_SUBJECT,  act) #auto subject #2
        self.assertRelationCount(0, mngd,   REL_SUB_ACTIVITY_SUBJECT,  act) #no auto subject with managed organisations
        self.assertRelationCount(1, rest,   REL_SUB_ACTIVITY_SUBJECT,  act) #auto subject #3 -> no doublon 

        self.assertEqual(8, Relation.objects.filter(subject_entity=act.id).count())

    def _create_activity_by_view(self, title='My task',
                                 atype_id=ACTIVITYTYPE_TASK, subtype_id=None,
                                 **kwargs
                                ):
        self.login()

        user = self.user
        data = {'user':             user.pk,
                'title':            title,
                'type_selector':    self._acttype_field_value(atype_id, subtype_id),
                'my_participation': True,
                'my_calendar':      Calendar.get_user_default_calendar(user).pk,
               }
        data.update(kwargs)

        self.assertNoFormError(self.client.post(self.ADD_URL, follow=True, data=data))

        return self.get_object_or_fail(Activity, title=title)

    def test_createview04(self):
        "No end but end time"
        act = self._create_activity_by_view(start='2013-3-29',
                                            start_time='14:30:00',
                                            end_time='15:45:00',
                                           )
        create_dt = partial(self.create_datetime, year=2013, month=3, day=29)
        self.assertEqual(create_dt(hour=14, minute=30), act.start)
        self.assertEqual(create_dt(hour=15, minute=45), act.end)

    def test_createview05(self):
        "FLOATING type"
        act = self._create_activity_by_view()
        self.assertIsNone(act.start)
        self.assertIsNone(act.end)
        self.assertEqual(FLOATING, act.floating_type)

    def test_createview06(self):
        "FLOATING_TIME type"
        act = self._create_activity_by_view(start='2013-3-30', end='2013-3-30')
        create_dt = partial(self.create_datetime, year=2013, month=3, day=30)
        self.assertEqual(create_dt(hour=0,  minute=0),  act.start)
        self.assertEqual(create_dt(hour=23, minute=59), act.end)
        self.assertEqual(FLOATING_TIME, act.floating_type)

    def test_createview07(self):
        "default_day_duration=1 + FLOATING_TIME"
        atype = self.get_object_or_fail(ActivityType, id=ACTIVITYTYPE_SHOW)
        self.assertEqual(1,          atype.default_day_duration)
        self.assertEqual('00:00:00', atype.default_hour_duration)

        act = self._create_activity_by_view('TGS', atype.id, start='2013-7-3')

        create_dt = partial(self.create_datetime, year=2013, month=7, day=3)
        self.assertEqual(create_dt(hour=0,  minute=0),  act.start)
        self.assertEqual(create_dt(hour=23, minute=59), act.end)

    def test_createview08(self):
        "default_day_duration=1 + is_all_day"
        act = self._create_activity_by_view('TGS', ACTIVITYTYPE_SHOW,
                                            start='2013-7-3', is_all_day=True,
                                           )

        create_dt = partial(self.create_datetime, year=2013, month=7, day=3)
        self.assertEqual(create_dt(hour=0,  minute=0),  act.start)
        self.assertEqual(create_dt(hour=23, minute=59), act.end)

    def test_createview09(self):
        "default_duration = 1.5 day + FLOATING_TIME"
        atype = ActivityType.objects.create(pk='activities-activity_custom_1',
                                            name='Big Show',
                                            default_day_duration=1,
                                            default_hour_duration='12:00:00',
                                            is_custom=True,
                                           )

        act = self._create_activity_by_view('TGS', atype.id, start='2013-7-3')

        create_dt = partial(self.create_datetime, year=2013, month=7)
        self.assertEqual(create_dt(day=3, hour=0,  minute=0),  act.start)
        self.assertEqual(create_dt(day=4, hour=23, minute=59), act.end)

    def test_createview10(self):
        "default_duration = 0 + FLOATING_TIME"
        atype = ActivityType.objects.create(pk='activities-activity_custom_1',
                                            name='Big Show',
                                            default_day_duration=0,
                                            default_hour_duration='00:00:00',
                                            is_custom=True,
                                           )

        act = self._create_activity_by_view('TGS', atype.id, start='2013-7-3')

        create_dt = partial(self.create_datetime, year=2013, month=7, day=3)
        self.assertEqual(create_dt(hour=0,  minute=0),  act.start)
        self.assertEqual(create_dt(hour=23, minute=59), act.end)

    def test_createview11(self):
        "Auto subjects disabled"
        self.login()
        #me   = self.contact
        user = self.user
        me   = user.linked_contact

        sv = self.get_object_or_fail(SettingValue, key=SETTING_AUTO_ORGA_SUBJECTS)
        sv.value = False #we disable the auto subjects feature
        sv.save()

        dojo = Organisation.objects.create(user=user, name='Tendo Dojo')
        Relation.objects.create(subject_entity=me, type_id=REL_SUB_EMPLOYED_BY,
                                object_entity=dojo, user=user,
                               )

        title  = 'My task'
        my_calendar = Calendar.get_user_default_calendar(user)
        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'user':             user.pk,
                                          'title':            title,
                                          'status':           Status.objects.all()[0].pk,
                                          'my_participation': True,
                                          'my_calendar':      my_calendar.pk,
                                          'type_selector':    self._acttype_field_value(ACTIVITYTYPE_TASK),
                                         }
                                   )
        self.assertNoFormError(response)

        act = self.get_object_or_fail(Activity, title=title)
        self.assertRelationCount(1, me,   REL_SUB_PART_2_ACTIVITY,  act)
        self.assertRelationCount(0, dojo, REL_SUB_ACTIVITY_SUBJECT, act)

        #better in a teardown method...
        sv.value = True
        sv.save()

    def test_createview_errors01(self):
        self.login()

        user = self.user
        data = {'user':             user.pk,
                'title':            'My task',
                'type_selector':    self._acttype_field_value(ACTIVITYTYPE_TASK),
                'end':              '2013-3-29',
                'my_participation': True,
                'my_calendar':      Calendar.get_user_default_calendar(user).pk,
               }
        url = self.ADD_URL

        response = self.assertPOST200(url, follow=True, data=data)
        self.assertFormError(response, 'form', None,
                             _(u"You can't set the end of your activity without setting its start")
                            )

        response = self.assertPOST200(url, follow=True, data=dict(data, start='2013-3-30'))
        self.assertFormError(response, 'form', None, _(u'End time is before start time'))

        response = self.assertPOST200(url, follow=True, data=dict(data, start='2013-3-29', busy=True))
        self.assertFormError(response, 'form', None,
                             _(u"A floating on the day activity can't busy its participants")
                            )

    def test_createview_errors02(self):
        "RelationType constraint error"
        self.login()

        user = self.user
        bad_subject = self._create_meeting()
        response = self.assertPOST200(self.ADD_URL, follow=True,
                                      data={'user':             user.pk,
                                            'title':            'My task',
                                            'type_selector':    self._acttype_field_value(ACTIVITYTYPE_TASK),
                                            'my_participation': True,
                                            'my_calendar':      Calendar.get_user_default_calendar(user).pk,
                                            'subjects':         self._relation_field_value(bad_subject),
                                        }
                                     )
        self.assertFormError(response, 'form', 'subjects',
                             _(u"This content type is not allowed.")
                            )

    def test_createview_errors03(self):
        "other_participants contains contact of user"
        self.login()

        user = self.user

        #create_contact = partial(Contact.objects.create, user=user)
        #ranma = create_contact(first_name='Ranma', last_name='Saotome')
        ranma = Contact.objects.create(user=user, first_name='Ranma', last_name='Saotome')

        response = self.assertPOST200(self.ADD_URL, follow=True,
                                      data={'user':             user.pk,
                                            'title':            'My task',
                                            'type_selector':    self._acttype_field_value(ACTIVITYTYPE_TASK),
                                            'my_participation': True,
                                            'my_calendar':      Calendar.get_user_default_calendar(user).pk,
                                            'subjects':         self._relation_field_value(ranma),
                                            #'other_participants': '[%d]' % self.other_contact.id,
                                            'other_participants': '[%d]' % self.other_user.linked_contact.id,
                                        }
                                     )
        self.assertFormError(response, 'form', 'other_participants',
                             _(u"This entity doesn't exist.")
                            )

    def test_createview_alert01(self):
        self.login()

        user = self.user
        title  = 'Meeting01'
        my_calendar = Calendar.get_user_default_calendar(user)
        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'user':             user.pk,
                                          'title':            title,
                                          'type_selector':    self._acttype_field_value(ACTIVITYTYPE_MEETING, 
                                                                                        ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                                                                                       ),
                                          'start':            '2010-1-10',
                                          'my_participation': True,
                                          'my_calendar':      my_calendar.pk,

                                          'alert_day':        '2010-2-10',
                                          'alert_start_time': '10:05',

                                          'alert_trigger_number': 2,
                                          'alert_trigger_unit':   'days',
                                         }
                                   )
        self.assertNoFormError(response)

        act = self.get_object_or_fail(Activity, title=title)
        create_dt = self.create_datetime
        #self.assertEqual(date(year=2010, month=1, day=10), act.start.date())
        self.assertEqual(create_dt(year=2010, month=1, day=10), act.start)
        self.assertEqual(ACTIVITYTYPE_MEETING, act.type.id)
        self.assertEqual(ACTIVITYSUBTYPE_MEETING_QUALIFICATION, act.sub_type.id)

        alerts = Alert.objects.filter(entity_id=act.id).order_by('id')
        self.assertEqual(2, len(alerts))

        alert1 = alerts[0]
        self.assertEqual(_('Alert of activity'), alert1.title)
        self.assertEqual(_(u'Alert related to %s') % act, alert1.description)
        self.assertEqual(create_dt(2010, 2, 10, 10, 05), alert1.trigger_date)

        self.assertEqual(create_dt(2010, 1, 8, 0, 0), alerts[1].trigger_date)

    def test_createview_alert02(self):
        "Unit is missing"
        self.login()

        user = self.user
        title  = 'Meeting01'
        my_calendar = Calendar.get_user_default_calendar(user)
        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'user':             user.pk,
                                          'title':            title,
                                          'type_selector':    self._acttype_field_value(ACTIVITYTYPE_MEETING,
                                                                                        ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                                                                                       ),
                                          'start':            '2013-3-28',
                                          'start_time':       '17:30:00',
                                          'my_participation': True,
                                          'my_calendar':      my_calendar.pk,

                                          'alert_trigger_number': 2,
                                          #'alert_trigger_unit':  'days' #missing,
                                         }
                                   )
        self.assertNoFormError(response)

        act = self.get_object_or_fail(Activity, title=title)
        alert = self.get_object_or_fail(Alert, entity_id=act.id)
        self.assertEqual(self.create_datetime(2013, 3, 28, 17, 28), alert.trigger_date)

    def test_create_view_meeting01(self):
        self.login()

        atype = self.get_object_or_fail(ActivityType, pk=ACTIVITYTYPE_MEETING)
        self.assertEqual(0,          atype.default_day_duration)
        self.assertEqual('00:15:00', atype.default_hour_duration) #TODO: timedelta instead ??

        subtype = self.get_object_or_fail(ActivitySubType, pk=ACTIVITYSUBTYPE_MEETING_NETWORK)

        #me   = self.contact
        user = self.user

        create_contact = partial(Contact.objects.create, user=user)
        ranma = create_contact(first_name='Ranma', last_name='Saotome')
        genma = create_contact(first_name='Genma', last_name='Saotome')

        dojo = Organisation.objects.create(user=user, name='Dojo')

        url = '/activities/activity/add/meeting'
        self.assertGET200(url)

        #TODO: help text of end (duration)

        title  = 'My meeting'
        status = Status.objects.all()[0]
        my_calendar = Calendar.get_user_default_calendar(user)
        response = self.client.post(url, follow=True,
                                    data={'user':               user.pk,
                                          'title':              title,
                                          'type_selector':      self._acttype_field_value(atype.id, subtype.id),
                                          'status':             status.pk,
                                          'start':              '2013-4-12',
                                          'start_time':         '10:00:00',
                                          'my_participation':   True,
                                          'my_calendar':        my_calendar.pk,
                                          'other_participants': '[%d]' % genma.id,
                                          'subjects':           self._relation_field_value(ranma),
                                          'linked_entities':    self._relation_field_value(dojo),
                                         }
                                   )
        self.assertNoFormError(response)

        meeting = self.get_object_or_fail(Activity, type=atype, title=title)

        self.assertEqual(status, meeting.status)
        self.assertEqual(NARROW, meeting.floating_type)
        self.assertEqual(self.create_datetime(year=2013, month=4, day=12, hour=10, minute=00),
                         meeting.start,
                        )
        self.assertEqual(self.create_datetime(year=2013, month=4, day=12, hour=10, minute=15),
                         meeting.end,
                        )

        #self.assertRelationCount(1, me,    REL_SUB_PART_2_ACTIVITY,   meeting)
        self.assertRelationCount(1, user.linked_contact, REL_SUB_PART_2_ACTIVITY,   meeting)
        self.assertRelationCount(1, genma,               REL_SUB_PART_2_ACTIVITY,   meeting)
        self.assertRelationCount(1, ranma,               REL_SUB_ACTIVITY_SUBJECT,  meeting)
        self.assertRelationCount(1, dojo,                REL_SUB_LINKED_2_ACTIVITY, meeting)

    def test_create_view_phonecall01(self):
        self.login()

        user = self.user
        type_id = ACTIVITYTYPE_PHONECALL
        subtype = self.get_object_or_fail(ActivitySubType, pk=ACTIVITYSUBTYPE_PHONECALL_OUTGOING)

        url = '/activities/activity/add/phonecall'
        self.assertGET200(url)

        title  = 'My call'
        my_calendar = Calendar.get_user_default_calendar(user)
        response = self.client.post(url, follow=True,
                                    data={'user':             user.pk,
                                          'title':            title,
                                          'type_selector':    self._acttype_field_value(type_id, subtype.id),
                                          'start':            '2013-4-12',
                                          'start_time':       '10:00:00',
                                          'my_participation': True,
                                          'my_calendar':      my_calendar.pk,
                                         }
                                   )
        self.assertNoFormError(response)
        self.get_object_or_fail(Activity, type=type_id, title=title)

    def test_create_view_invalidtype(self):
        self.login()
        self.assertGET404('/activities/activity/add/invalid')

    def test_create_view_unallowedtype(self):
        self.login()

        response = self.assertPOST200('/activities/activity/add/phonecall', follow=True,
                                      data={'user':          self.user.pk,
                                            'title':         'My meeting',
                                            'type_selector': self._acttype_field_value(ACTIVITYTYPE_MEETING,
                                                                                       ACTIVITYSUBTYPE_MEETING_NETWORK,
                                                                                      ),
                                            'start':         '2013-4-12',
                                            'start_time':    '10:00:00',
                                           }
                                     )
        self.assertFormError(response, 'form', 'type_selector',
                             _(u'This type causes constraint error.')
                            )

    def test_create_view_task01(self):
        self.login()

        user = self.user
        type_id = ACTIVITYTYPE_TASK

        url = '/activities/activity/add/task'
        self.assertGET200(url)

        title  = 'My call'
        my_calendar = Calendar.get_user_default_calendar(user)
        response = self.client.post(url, follow=True,
                                    data={'user':             user.pk,
                                          'title':            title,
                                          'type_selector':    self._acttype_field_value(type_id),
                                          'start':            '2013-4-12',
                                          'start_time':       '10:00:00',
                                          'my_participation': True,
                                          'my_calendar':      my_calendar.pk,
                                         }
                                   )
        self.assertNoFormError(response)
        self.get_object_or_fail(Activity, type=type_id, title=title)

    def test_createview_related01(self):
        self.login()

        user = self.user
        other_user = self.other_user

        contact01 = Contact.objects.create(user=user, first_name='Ranma', last_name='Saotome')
        #contact02 = self.other_contact
        contact02 = other_user.linked_contact

        uri = self._build_add_related_uri(contact01)
        response = self.assertGET200(uri)

        with self.assertNoException():
            other_participants = response.context['form'].fields['other_participants']

        self.assertEqual([contact01], other_participants.initial)

        title  = 'My meeting'
        response = self.client.post(uri, follow=True,
                                    data={'user':                user.pk,
                                          'title':               title,
                                          'type_selector':       self._acttype_field_value(ACTIVITYTYPE_MEETING,
                                                                                           ACTIVITYSUBTYPE_MEETING_REVIVAL,
                                                                                          ),
                                          'start':               '2010-1-10',
                                          'start_time':          '17:30:00',
                                          'participating_users': other_user.pk,
                                         }
                                    )
        self.assertNoFormError(response)
        self.assertRedirects(response, contact01.get_absolute_url())

        meeting = self.get_object_or_fail(Activity, title=title)
        self.assertEqual(self.create_datetime(year=2010, month=1, day=10, hour=17, minute=30),
                         meeting.start
                        )
        self.assertEqual(ACTIVITYTYPE_MEETING,            meeting.type.pk)
        self.assertEqual(ACTIVITYSUBTYPE_MEETING_REVIVAL, meeting.sub_type_id)

        self.assertEqual(2, Relation.objects.count())

        relations = Relation.objects.filter(type=REL_SUB_PART_2_ACTIVITY)
        self.assertEqual(1, len(relations))

        relation = relations[0]
        self.assertEqual(contact02.id, relation.subject_entity_id)
        self.assertEqual(meeting.id,   relation.object_entity_id)

    def test_createview_related02(self):
        self.login()

        #response = self.assertGET200(self._build_add_related_uri(self.other_contact,
        response = self.assertGET200(self._build_add_related_uri(self.other_user.linked_contact,
                                                                 ACTIVITYTYPE_MEETING,
                                                                )
                                    )

        with self.assertNoException():
            users = response.context['form'].fields['participating_users']

        self.assertEqual([self.other_user.id], [e.id for e in users.initial])

    def test_createview_related03(self):
        self.login()

        dojo = Organisation.objects.create(user=self.user, name='Tendo no dojo')
        response = self.assertGET200(self._build_add_related_uri(dojo, ACTIVITYTYPE_MEETING))

        with self.assertNoException():
            subjects = response.context['form'].fields['subjects']

        self.assertEqual([dojo.id], [e.id for e in subjects.initial])

    def test_createview_related04(self):
        self.login()

        linked = Activity.objects.create(user=self.user, title='Meet01',
                                         type_id=ACTIVITYTYPE_MEETING,
                                        )
        response = self.assertGET200(self._build_add_related_uri(linked, ACTIVITYTYPE_PHONECALL))

        with self.assertNoException():
            linked_entities = response.context['form'].fields['linked_entities']

        self.assertEqual([linked.id], [e.id for e in linked_entities.initial])

    def test_createview_related_meeting01(self):
        "Meeting forced"
        self.login()

        user = self.user
        ryoga = Contact.objects.create(user=user, first_name='Ryoga', last_name='Hibiki')

        uri = self._build_add_related_uri(ryoga, ACTIVITYTYPE_MEETING)
        title  = 'My meeting'
        my_calendar = Calendar.get_user_default_calendar(user)
        response = self.client.post(uri, follow=True,
                                    data={'user':             user.pk,
                                          'title':            title,
                                          'type_selector':    self._acttype_field_value(ACTIVITYTYPE_MEETING,
                                                                                        ACTIVITYSUBTYPE_MEETING_REVIVAL,
                                                                                       ),
                                          'start':            '2013-5-21',
                                          'start_time':       '9:30:00',
                                          'my_participation': True,
                                          'my_calendar':      my_calendar.pk,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertRedirects(response, ryoga.get_absolute_url())

        meeting = self.get_object_or_fail(Activity, title=title)
        self.assertEqual(self.create_datetime(year=2013, month=5, day=21, hour=9, minute=30),
                         meeting.start
                        )
        self.assertEqual(ACTIVITYTYPE_MEETING,            meeting.type.pk)
        self.assertEqual(ACTIVITYSUBTYPE_MEETING_REVIVAL, meeting.sub_type_id)

        response = self.assertPOST200(uri, follow=True,
                                      data={'user':             user.pk,
                                            'title':            'Other meeting',
                                            'type_selector':    self._acttype_field_value(ACTIVITYTYPE_TASK),
                                            'start':            '2013-5-21',
                                            'start_time':       '9:30:00',
                                            'my_participation': True,
                                            'my_calendar':      my_calendar.pk,
                                           }
                                     )
        self.assertFormError(response, 'form', 'type_selector',
                             _(u'This type causes constraint error.'),
                            )

    def test_createview_related_other01(self):
        self.login()

        ryoga = Contact.objects.create(user=self.user, first_name='Ryoga', last_name='Hibiki')
        build_url = partial(self._build_add_related_uri, ryoga)
        self.assertGET200(build_url(ACTIVITYTYPE_PHONECALL))
        self.assertGET200(build_url(ACTIVITYTYPE_TASK))
        self.assertGET404(build_url('foobar'))

    def test_popup_view01(self):
        self.login()

        create_dt = partial(self.create_datetime, year=2010, month=10, day=1)
        activity = Activity.objects.create(user=self.user, title='Meet01',
                                           type_id=ACTIVITYTYPE_MEETING,
                                           start=create_dt(hour=14, minute=0),
                                           end=create_dt(hour=15, minute=0),
                                          )
        response = self.assertGET200('/activities/activity/%s/popup' % activity.id)
        self.assertContains(response, activity.type)

    def test_editview01(self):
        self.login()
        user = self.user

        title = 'meet01'
        create_dt = partial(self.create_datetime, year=2013, month=10, day=1)
        start = create_dt(hour=22, minute=0)
        end = create_dt(hour=23, minute=0)
        type_id = ACTIVITYTYPE_MEETING
        sub_type_id = ACTIVITYSUBTYPE_MEETING_MEETING
        activity = Activity.objects.create(user=self.user, title=title,
                                           type_id=type_id, sub_type_id=sub_type_id,
                                           start=start, end=end,
                                          )
        #rel = Relation.objects.create(subject_entity=self.contact, user=self.user,
        rel = Relation.objects.create(subject_entity=user.linked_contact, user=user,
                                      type_id=REL_SUB_PART_2_ACTIVITY,
                                      object_entity=activity,
                                     )

        url = self._buid_edit_url(activity)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            start_time_f = fields['start_time']
            end_time_f = fields['end_time']

        self.assertEqual(22, start_time_f.initial.hour)
        self.assertEqual(23, end_time_f.initial.hour)

        title += '_edited'
        self.assertNoFormError(self.client.post(
                url, follow=True,
                data={'user':          self.user.pk,
                      'title':         title,
                      'start':         '2011-2-22',
                      'type_selector': self._acttype_field_value(type_id, sub_type_id),
                     }
            ))

        activity = self.refresh(activity)
        self.assertEqual(title, activity.title)
        #self.assertEqual(date(year=2011, month=2, day=22), activity.start.date())
        self.assertEqual(create_dt(year=2011, month=2, day=22), activity.start)
        self.assertEqual(type_id,     activity.type.id)
        self.assertEqual(sub_type_id, activity.sub_type.id)

        relations = Relation.objects.filter(type=REL_SUB_PART_2_ACTIVITY)
        self.assertEqual(1, len(relations))
        self.assertEqual(rel, relations[0])

    def test_editview02(self):
        "Change sub type"
        self.login()

        title = 'act01'

#        ACTIVITYTYPE_ACTIVITY = 'activities-activity_custom_1'
#        act_type = create_or_update(ActivityType, ACTIVITYTYPE_ACTIVITY, name='Karate session',
#                                    default_day_duration=0, default_hour_duration="00:15:00", is_custom=True
#                                   )
#
#        ACTIVITYTYPE_ACTIVITY2 = 'activities-activity_custom_2'
#        create_or_update(ActivityType, ACTIVITYTYPE_ACTIVITY2, name='Karate session',
#                         default_day_duration=0, default_hour_duration="00:15:00", is_custom=True
#                        )

        create_dt = self.create_datetime
        activity = Activity.objects.create(user=self.user, title=title,
                                           start=create_dt(year=2010, month=10, day=1, hour=14, minute=0),
                                           end=create_dt(year=2010, month=10, day=1, hour=15, minute=0),
                                           type_id=ACTIVITYTYPE_PHONECALL,
                                           sub_type_id=ACTIVITYSUBTYPE_PHONECALL_INCOMING
                                          )

        url = self._buid_edit_url(activity)
        title += '_edited'
        data = {'user':  self.user.pk,
                'title': title,
                'start': '2011-2-22',
               }
        fvalue = self._acttype_field_value
        response = self.assertPOST200(url, follow=True,
                                      data=dict(data, type_selector=fvalue(ACTIVITYTYPE_MEETING,
                                                                           ACTIVITYSUBTYPE_MEETING_NETWORK,
                                                                          )
                                               )
                                     )
        self.assertFormError(response, 'form', 'type_selector', 
                             _('This type causes constraint error.'),
                            )

        self.assertNoFormError(self.client.post(
                self._buid_edit_url(activity), follow=True,
                 data=dict(data, type_selector=fvalue(ACTIVITYTYPE_PHONECALL,
                                                      ACTIVITYSUBTYPE_PHONECALL_OUTGOING,
                                                      )
                          )
            ))

        activity = self.refresh(activity)
        self.assertEqual(title, activity.title)
        self.assertEqual(create_dt(year=2011, month=2, day=22), activity.start)
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_OUTGOING, activity.sub_type_id)

    def test_editview03(self):
        "Collision"
        self.login()
        user = self.user
        #contact = self.contact
        contact = user.linked_contact

        def create_task(**kwargs):
            task = Activity.objects.create(user=user, type_id=ACTIVITYTYPE_TASK, **kwargs)
            Relation.objects.create(subject_entity=contact, user=user,
                                    type_id=REL_SUB_PART_2_ACTIVITY,
                                    object_entity=task,
                                   )

            return task

        create_dt = self.create_datetime
        task01 = create_task(title='Task#1',
                             start=create_dt(year=2013, month=4, day=17, hour=11, minute=0),
                             end=create_dt(year=2013,   month=4, day=17, hour=12, minute=0),
                            )
        task02 = create_task(title='Task#2', busy=True,
                             start=create_dt(year=2013, month=4, day=17, hour=14, minute=0),
                             end=create_dt(year=2013,   month=4, day=17, hour=15, minute=0),
                            )

        response = self.assertPOST200(
                self._buid_edit_url(task01), follow=True,
                data={'user':          user.pk,
                      'title':         task01.title,
                      'busy':          True,
                      'start':         '2013-4-17',
                      'start_time':    '14:30:00',
                      'end':           '2013-4-17',
                      'end_time':      '16:00:00',
                      'type_selector': self._acttype_field_value(task01.type_id,
                                                                 task01.sub_type_id,
                                                                ),
                     }
            )
        self.assertFormError(response, 'form', None,
                             _(u"%(participant)s already participates to the activity «%(activity)s» between %(start)s and %(end)s.") % {
                                    'participant': contact,
                                    'activity':    task02,
                                    'start':       '14:30:00',
                                    'end':         '15:00:00',
                                }
                            )

    def test_editview04(self):
        "Edit FLOATING_TIME activity"
        task = self._create_activity_by_view(start='2013-7-25')
        self.assertEqual(FLOATING_TIME, task.floating_type)

        response = self.assertGET200(self._buid_edit_url(task))

        with self.assertNoException():
            fields = response.context['form'].fields
            start_time_f = fields['start_time']
            end_time_f = fields['end_time']

        self.assertIsNone(start_time_f.initial)
        self.assertIsNone(end_time_f.initial)

    #def test_editview05(self):
        #"Edit FLOATING activity"
        #task = self._create_task_by_view()
        #self.assertIsNone(task.start)
        #self.assertIsNone(task.end)
        #self.assertEqual(FLOATING, task.floating_type)

        #atype = task.type
        #self.assertEqual(0,          atype.default_day_duration)
        #self.assertEqual('00:15:00', atype.default_hour_duration)

        #response = self.client.post(self._buid_edit_url(task), follow=True,
                                    #data={'user':  self.user.pk,
                                          #'title': task.title,
                                          #'start':      '2013-4-17',
                                          #'start_time': '14:30:00',
                                          ##'end':        '2013-4-17',
                                         #}
                                   #)
        #self.assertNoFormError(response)

    def _check_activity_collisions(self, activity_start, activity_end, participants,
                                   busy=True, exclude_activity_id=None,
                                  ):
        collisions = check_activity_collisions(activity_start, activity_end,
                                               participants, busy=busy,
                                               exclude_activity_id=exclude_activity_id,
                                              )
        if collisions:
            raise ValidationError(collisions)

    def test_collision01(self):
        self.login()

        create_activity = partial(Activity.objects.create, user=self.user)
        create_dt = self.create_datetime

        with self.assertNoException():
            act01 = create_activity(title='call01', type_id=ACTIVITYTYPE_PHONECALL,
                                    sub_type_id=ACTIVITYSUBTYPE_PHONECALL_INCOMING,
                                    start=create_dt(year=2010, month=10, day=1, hour=12, minute=0),
                                    end=create_dt(year=2010, month=10, day=1, hour=13, minute=0),
                                   )
            act02 = create_activity(title='meet01', type_id=ACTIVITYTYPE_MEETING,
                                    start=create_dt(year=2010, month=10, day=1, hour=14, minute=0),
                                    end=create_dt(year=2010, month=10, day=1, hour=15, minute=0),
                                   )
            act03 = create_activity(title='meet02',  type_id=ACTIVITYTYPE_MEETING, busy=True,
                                    start=create_dt(year=2010, month=10, day=1, hour=18, minute=0),
                                    end=create_dt(year=2010, month=10, day=1, hour=19, minute=0),
                                   )

            create_contact = partial(Contact.objects.create, user=self.user)
            c1 = create_contact(first_name='first_name1', last_name='last_name1')
            c2 = create_contact(first_name='first_name2', last_name='last_name2')

            create_rel = partial(Relation.objects.create, subject_entity=c1, 
                                 type_id=REL_SUB_PART_2_ACTIVITY, user=self.user,
                                )
            create_rel(object_entity=act01)
            create_rel(object_entity=act02)
            create_rel(object_entity=act03)

        check_coll = partial(self._check_activity_collisions, participants=[c1, c2])

        try:
            #no collision
            #next day
            check_coll(activity_start=create_dt(year=2010, month=10, day=2, hour=12, minute=0),
                       activity_end=create_dt(year=2010,   month=10, day=2, hour=13, minute=0),
                      )

            #one minute before
            check_coll(activity_start=create_dt(year=2010, month=10, day=1, hour=11, minute=0),
                       activity_end=create_dt(year=2010,   month=10, day=1, hour=11, minute=59),
                      )

            #one minute after
            check_coll(activity_start=create_dt(year=2010, month=10, day=1, hour=13, minute=1),
                       activity_end=create_dt(year=2010,   month=10, day=1, hour=13, minute=10),
                      )
            #not busy
            check_coll(activity_start=create_dt(year=2010, month=10, day=1, hour=14, minute=0),
                       activity_end=create_dt(year=2010,   month=10, day=1, hour=15, minute=0),
                       busy=False
                      )
        except ValidationError as e:
            self.fail(str(e))

        #collision with act01
        #before
        self.assertRaises(ValidationError, self._check_activity_collisions,
                          activity_start=create_dt(year=2010, month=10, day=1, hour=11, minute=30),
                          activity_end=create_dt(year=2010, month=10, day=1, hour=12, minute=30),
                          participants=[c1, c2]
                         )

        #after
        self.assertRaises(ValidationError, self._check_activity_collisions,
                          activity_start=create_dt(year=2010, month=10, day=1, hour=12, minute=30),
                          activity_end=create_dt(year=2010, month=10, day=1, hour=13, minute=30),
                          participants=[c1, c2]
                         )

        #shorter
        self.assertRaises(ValidationError, self._check_activity_collisions,
                          activity_start=create_dt(year=2010, month=10, day=1, hour=12, minute=10),
                          activity_end=create_dt(year=2010, month=10, day=1, hour=12, minute=30),
                          participants=[c1, c2]
                         )

        #longer
        self.assertRaises(ValidationError, self._check_activity_collisions,
                          activity_start=create_dt(year=2010, month=10, day=1, hour=11, minute=0),
                          activity_end=create_dt(year=2010, month=10, day=1, hour=13, minute=30),
                          participants=[c1, c2]
                         )
        #busy1
        self.assertRaises(ValidationError, self._check_activity_collisions,
                          activity_start=create_dt(year=2010, month=10, day=1, hour=17, minute=30),
                          activity_end=create_dt(year=2010, month=10, day=1, hour=18, minute=30),
                          participants=[c1, c2]
                         )
        #busy2
        self.assertRaises(ValidationError, self._check_activity_collisions,
                          activity_start=create_dt(year=2010, month=10, day=1, hour=18, minute=0),
                          activity_end=create_dt(year=2010, month=10, day=1, hour=18, minute=30),
                          busy=False, participants=[c1, c2]
                         )

    def test_listviews(self):
        self.login()
        self.assertFalse(Activity.objects.all())

        create_act = partial(Activity.objects.create, user=self.user)
        create_dt = self.create_datetime
        acts = [create_act(title='call01', type_id=ACTIVITYTYPE_PHONECALL,
                           sub_type_id=ACTIVITYSUBTYPE_PHONECALL_INCOMING,
                           start=create_dt(year=2010, month=10, day=1, hour=12, minute=0),
                           end=create_dt(year=2010, month=10, day=1, hour=13, minute=0)
                         ),
                create_act(title='meet01', type_id=ACTIVITYTYPE_MEETING,
                           sub_type_id=ACTIVITYSUBTYPE_MEETING_REVIVAL,
                           start=create_dt(year=2010, month=10, day=1, hour=14, minute=0),
                           end=create_dt(year=2010, month=10, day=1, hour=15, minute=0)
                          ),
               ]

        response = self.assertGET200('/activities/activities')

        with self.assertNoException():
            activities_page = response.context['entities']

        self.assertEqual(1, activities_page.number)
        self.assertEqual(2, activities_page.paginator.count)
        self.assertEqual(set(acts), set(activities_page.object_list))

        #Phone calls
        response = self.assertGET200('/activities/phone_calls')

        with self.assertNoException():
            pcalls_page = response.context['entities']

        self.assertEqual([acts[0]], list(pcalls_page.object_list))

        #Meetings
        response = self.assertGET200('/activities/meetings')

        with self.assertNoException():
            meetings_page = response.context['entities']

        self.assertEqual([acts[1]], list(meetings_page.object_list))

    def test_unlink01(self):
        self.login()

        activity = self._create_meeting()
        contact = Contact.objects.create(user=self.user, first_name='Musashi', last_name='Miyamoto')

        create_rel = partial(Relation.objects.create, subject_entity=contact,
                             object_entity=activity, user=self.user,
                            )
        r1 = create_rel(type_id=REL_SUB_PART_2_ACTIVITY)
        r2 = create_rel(type_id=REL_SUB_ACTIVITY_SUBJECT)
        r3 = create_rel(type_id=REL_SUB_LINKED_2_ACTIVITY)
        r4 = create_rel(type_id=REL_SUB_HAS)
        self.assertEqual(3, contact.relations.filter(pk__in=[r1.id, r2.id, r3.id]).count())

        url = '/activities/linked_activity/unlink'
        self.assertPOST200(url, data={'id': activity.id, 'object_id': contact.id})
        self.assertEqual(0, contact.relations.filter(pk__in=[r1.id, r2.id, r3.id]).count())
        self.assertEqual(1, contact.relations.filter(pk=r4.id).count())

        #errors
        self.assertPOST404(url, data={'id': activity.id})
        self.assertPOST404(url, data={'object_id': contact.id})
        self.assertPOST404(url)
        self.assertPOST404(url, data={'id': 1024,        'object_id': contact.id})
        self.assertPOST404(url, data={'id': activity.id, 'object_id': 1024})

    def test_unlink02(self):
        "Can not unlink the activity"
        self.login(is_superuser=False)
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        activity = self._create_meeting()
        contact = Contact.objects.create(user=self.user, first_name='Musashi', last_name='Miyamoto')
        relation = Relation.objects.create(subject_entity=contact, type_id=REL_SUB_PART_2_ACTIVITY,
                                           object_entity=activity, user=self.user
                                          )

        self.assertPOST403('/activities/linked_activity/unlink',
                           data={'id': activity.id, 'object_id': contact.id},
                          )
        self.assertEqual(1, contact.relations.filter(pk=relation.id).count())

    def test_unlink03(self):
        "Can not unlink the contact"
        self.login(is_superuser=False)

        create_creds = partial(SetCredentials.objects.create, role=self.role)
        create_creds(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                           EntityCredentials.DELETE | EntityCredentials.LINK   |
                           EntityCredentials.UNLINK,
                     set_type=SetCredentials.ESET_OWN
                    )
        create_creds(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                           EntityCredentials.DELETE | EntityCredentials.LINK,
                     set_type=SetCredentials.ESET_ALL
                    )

        activity = self._create_meeting()
        contact = Contact.objects.create(user=self.other_user, first_name='Musashi', last_name='Miyamoto')
        relation = Relation.objects.create(subject_entity=contact, type_id=REL_SUB_PART_2_ACTIVITY,
                                           object_entity=activity, user=self.user
                                          )

        self.assertPOST403('/activities/linked_activity/unlink',
                           data={'id': activity.id, 'object_id': contact.id}
                          )
        self.get_object_or_fail(Relation, pk=relation.id)

    def test_participants01(self):
        self.login()

        activity = self._create_meeting()

        create_contact = partial(Contact.objects.create, user=self.user)
        ids = (create_contact(first_name='Musashi', last_name='Miyamoto').id,
               create_contact(first_name='Kojiro',  last_name='Sasaki').id,
              )

        uri = self._buid_add_participants_url(activity)
        self.assertGET200(uri)
        self.assertNoFormError(self.client.post(uri, data={'participants': '[%d,%d]' % ids}))

        relations = Relation.objects.filter(subject_entity=activity.id, type=REL_OBJ_PART_2_ACTIVITY)
        self.assertEqual(2, len(relations))
        self.assertEqual(set(ids), {r.object_entity_id for r in relations})

    def test_participants02(self):
        "Credentials error with the activity"
        self.login(is_superuser=False)
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        activity = self._create_meeting()
        self.assertTrue(self.user.has_perm_to_change(activity))
        self.assertFalse(self.user.has_perm_to_link(activity))
        self.assertGET403(self._buid_add_participants_url(activity))

    def test_participants03(self):
        "Credentials error with selected subjects"
        self.login(is_superuser=False)
        self._build_nolink_setcreds()

        activity = self._create_meeting()
        self.assertTrue(self.user.has_perm_to_link(activity))

        contact = Contact.objects.create(user=self.other_user, first_name='Musashi', last_name='Miyamoto')
        self.assertTrue(self.user.has_perm_to_change(contact))
        self.assertFalse(self.user.has_perm_to_link(contact))

        uri = self._buid_add_participants_url(activity)
        self.assertGET200(uri)

        response = self.assertPOST200(uri, data={'participants': '[%d]' % contact.id})
        self.assertFormError(response, 'form', 'participants',
                             _(u'Some entities are not linkable: %s') % contact
                            )
        self.assertFalse(Relation.objects.filter(subject_entity=activity.id,
                                                 type=REL_OBJ_PART_2_ACTIVITY,
                                                )
                        )

    def test_participants04(self):
        "Remove participants (relationships deleted)"
        self.login()
        user = self.user
        #logged   = self.contact
        logged   = user.linked_contact
        #other    = self.other_contact
        other    = self.other_user.linked_contact
        contact3 = Contact.objects.create(user=user, first_name='Roy', last_name='Mustang')
        dt_now = now()
        phone_call = Activity.objects.create(title='a random activity',
                                             start=dt_now, end=dt_now,
                                             user=user, type_id=ACTIVITYTYPE_PHONECALL
                                            )

        add_url = self._buid_add_participants_url(phone_call)
        self.assertGET200(add_url)

        response = self.assertPOST200(add_url, follow=True,
                                      data={'my_participation':    True,
                                            'my_calendar':         Calendar.get_user_default_calendar(logged.is_user).pk,
                                            'participating_users': other.is_user_id,
                                            'participants':        '[%d]' % contact3.pk,
                                           }
                                     )

        self.assertRelationCount(1, phone_call, REL_OBJ_PART_2_ACTIVITY, logged)   # logged user, push in his calendar
        self.assertRelationCount(1, phone_call, REL_OBJ_PART_2_ACTIVITY, other)    # other contact user, push in his calendar too
        self.assertRelationCount(1, phone_call, REL_OBJ_PART_2_ACTIVITY, contact3) # classic contact, has no calendar
        self.assertEqual(2, phone_call.calendars.count())

        sym_rel = Relation.objects.get(subject_entity=logged, type=REL_SUB_PART_2_ACTIVITY, object_entity=phone_call)

        del_url = '/activities/activity/participant/delete'
        self.assertGET404(del_url)
        self.assertPOST404(del_url, data={'id': sym_rel.pk})
        self.get_object_or_fail(Relation, pk=sym_rel.pk)

        qs = Relation.objects.filter(type=REL_OBJ_PART_2_ACTIVITY, subject_entity=phone_call)

        for participant_rel in qs.all():
            self.assertGET404(del_url)
            response = self.client.post(del_url, data={'id': participant_rel.pk})
            self.assertRedirects(response, phone_call.get_absolute_url())

        self.assertFalse(qs.all())
        self.assertFalse(phone_call.calendars.all())

    def test_participants05(self):
        "'My participation' field is removed when it is useless."
        activity = self._create_activity_by_view()

        create_contact = partial(Contact.objects.create, user=self.user)
        ids = (create_contact(first_name='Musashi', last_name='Miyamoto').id,
               create_contact(first_name='Kojiro',  last_name='Sasaki').id,
              )

        uri = self._buid_add_participants_url(activity)
        response = self.assertGET200(uri)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('my_participation', fields)
        self.assertNotIn('my_calendar',      fields)

        self.assertNoFormError(self.client.post(uri, data={'participants': '[%d,%d]' % ids}))

        relations = Relation.objects.filter(subject_entity=activity.id, type=REL_OBJ_PART_2_ACTIVITY)
        self.assertEqual(3, len(relations))
        self.assertEqual(set(ids + (self.user.related_contact.all()[0].id,)),
                         {r.object_entity_id for r in relations}
                        )

    def test_participants06(self):
        "Fix a bug when checking for collision for a floating activities"
        activity = self._create_activity_by_view()
        self.assertIsNone(activity.start)
        self.assertIsNone(activity.end)
        self.assertEqual(FLOATING, activity.floating_type)

        create_contact = partial(Contact.objects.create, user=self.user)
        ids = (create_contact(first_name='Musashi', last_name='Miyamoto').id,
               create_contact(first_name='Kojiro',  last_name='Sasaki').id,
              )

        uri = self._buid_add_participants_url(activity)
        self.assertGET200(uri)
        self.assertNoFormError(self.client.post(uri, data={'participants': '[%d,%d]' % ids}))

        relations = Relation.objects.filter(subject_entity=activity.id, type=REL_OBJ_PART_2_ACTIVITY)
        self.assertEqual(3, len(relations))
        self.assertEqual(set(ids + (self.user.related_contact.all()[0].id,)),
                         {r.object_entity_id for r in relations}
                        )

    def test_add_subjects01(self):
        self.login()

        activity = self._create_meeting()
        orga = Organisation.objects.create(user=self.user, name='Ghibli')

        uri = self._buid_add_subjects_url(activity)
        self.assertGET200(uri)
        self.assertNoFormError(self.client.post(uri, data={'subjects': self._relation_field_value(orga)}))

        relations = Relation.objects.filter(subject_entity=activity.id, type=REL_OBJ_ACTIVITY_SUBJECT)
        self.assertEqual(1, len(relations))
        self.assertEqual(orga.id, relations[0].object_entity_id)

    def test_add_subjects02(self):
        "Credentials error with the activity"
        self.login(is_superuser=False)
        SetCredentials.objects.create(role=self.user.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        activity = self._create_meeting()
        self.assertTrue(self.user.has_perm_to_change(activity))
        self.assertFalse(self.user.has_perm_to_link(activity))
        self.assertGET403(self._buid_add_subjects_url(activity))

    def test_add_subjects03(self): 
        "Credentials error with selected subjects"
        self.login(is_superuser=False)
        self._build_nolink_setcreds()

        user = self.user
        activity = self._create_meeting()
        self.assertTrue(user.has_perm_to_link(activity))

        orga = Organisation.objects.create(user=self.other_user, name='Ghibli')
        self.assertTrue(user.has_perm_to_change(orga))
        self.assertFalse(user.has_perm_to_link(orga))

        uri = self._buid_add_subjects_url(activity)
        self.assertGET200(uri)

        response = self.assertPOST200(uri, data={'subjects': self._relation_field_value(orga)})
        self.assertFormError(response, 'form', 'subjects',
                             _(u'Some entities are not linkable: %s') % orga
                            )
        self.assertFalse(Relation.objects.filter(subject_entity=activity.id,
                                                 type=REL_OBJ_ACTIVITY_SUBJECT,
                                                )
                        )

    def test_add_subjects04(self): 
        "Bad ContentType (relationType constraint error)"
        self.login()

        create_meeting = self._create_meeting
        activity    = create_meeting(title='My meeting')
        bad_subject = create_meeting(title="I'm bad heeheeeee")

        response = self.assertPOST200(self._buid_add_subjects_url(activity),
                                      data={'subjects': self._relation_field_value(bad_subject)}
                                     )
        self.assertFormError(response, 'form', 'subjects',
                             _(u"This content type is not allowed.")
                            )

    def test_indisponibility_createview01(self):
        "Can not create an indispo with generic view"
        self.login()

        url = self.ADD_URL
        self.assertGET200(url)

        user = self.user
        status = Status.objects.all()[0]
        my_calendar = Calendar.get_user_default_calendar(user)
        response = self.assertPOST200(url, follow=True,
                                      data={'user':               user.pk,
                                            'title':              'Away',
                                            'type_selector':      self._acttype_field_value(ACTIVITYTYPE_INDISPO),
                                            'status':             status.pk,
                                            'start':              '2013-3-27',
                                            'end':                '2010-3-27',
                                            'start_time':         '09:00:00',
                                            'end_time':           '11:00:00',
                                            'my_participation':   True,
                                            'my_calendar':        my_calendar.pk,
                                           }
                                    )
        self.assertFormError(response, 'form', 'type_selector',
                             _('This type causes constraint error.'),
                            )

    def test_indisponibility_createview02(self):
        self.login()
        #contact1 = self.contact
        #contact2 = self.other_contact
        user = self.user
        other_user = self.other_user

        title = 'Away'
        #my_calendar = Calendar.get_user_default_calendar(user)
        response = self.client.post(self.ADD_INDISPO_URL, follow=True,
                                    data={'user':               user.pk,
                                          'title':              title,
                                          'start':              '2010-1-10',
                                          'end':                '2010-1-12',
                                          'start_time':         '09:08:07',
                                          'end_time':           '06:05:04',
                                          'participating_users': [user.id, other_user.id],
                                         }
                                   )
        self.assertNoFormError(response)

        act = self.get_object_or_fail(Activity, type=ACTIVITYTYPE_INDISPO, title=title)
        self.assertIsNone(act.sub_type)
        self.assertIsNone(act.status)
        self.assertFalse(act.is_all_day)
        self.assertFalse(act.busy)

        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2010, month=1, day=10, hour=9, minute=8, second=7), act.start)
        self.assertEqual(create_dt(year=2010, month=1, day=12, hour=6, minute=5, second=4), act.end)

        #self.assertRelationCount(1, contact1, REL_SUB_PART_2_ACTIVITY, act)
        #self.assertRelationCount(1, contact2, REL_SUB_PART_2_ACTIVITY, act)
        self.assertRelationCount(1, user.linked_contact,       REL_SUB_PART_2_ACTIVITY, act)
        self.assertRelationCount(1, other_user.linked_contact, REL_SUB_PART_2_ACTIVITY, act)

    def test_indisponibility_createview03(self):
        "Is all day"
        self.login()

        user = self.user
        title  = 'AFK'
        subtype = ActivitySubType.objects.create(id='hollydays', name='Hollydays',
                                                 type_id=ACTIVITYTYPE_INDISPO,
                                                )
        response = self.client.post(self.ADD_INDISPO_URL, follow=True,
                                    data={'user':                user.pk,
                                          'title':               title,
                                          'type_selector':       subtype.id,
                                          'start':               '2010-1-10',
                                          'end':                 '2010-1-12',
                                          'is_all_day':          True,
                                          'participating_users': [user.id],
                                         }
                                   )
        self.assertNoFormError(response)

        act = self.get_object_or_fail(Activity, type=ACTIVITYTYPE_INDISPO, title=title)
        self.assertEqual(subtype, act.sub_type)
        self.assertTrue(act.is_all_day)
        self.assertEqual(self.create_datetime(year=2010, month=1, day=10, hour=0,  minute=0),  act.start)
        self.assertEqual(self.create_datetime(year=2010, month=1, day=12, hour=23, minute=59), act.end)

    def test_indisponibility_createview04(self):
        "Start & end are required"
        self.login()

        user = self.user
        response = self.assertPOST200(self.ADD_INDISPO_URL, follow=True,
                                      data={'user':                user.pk,
                                            'title':               'AFK',
                                            'participating_users': [user.id],
                                           }
                                     )
        msg = _('This field is required.')
        self.assertFormError(response, 'form', 'start', msg)
        self.assertFormError(response, 'form', 'end',   msg)

    def test_detete_activity_type01(self):
        self.login()

        atype = create_or_update(ActivityType, 'activities-activity_custom_1',
                                 name='Karate session',
                                 default_day_duration=0, default_hour_duration="00:15:00",
                                 is_custom=True,
                                )

        self.assertPOST200(self.DEL_ACTTYPE_URL, data={'id': atype.pk})
        self.assertFalse(ActivityType.objects.filter(pk=atype.pk).exists())

    def test_detete_activity_type02(self):
        self.login()

        atype = create_or_update(ActivityType, 'activities-activity_custom_1',
                                 name='Karate session',
                                 default_day_duration=0, default_hour_duration="00:15:00",
                                 is_custom=True,
                                )
        activity = Activity.objects.create(user=self.user, type=atype)

        self.assertPOST404(self.DEL_ACTTYPE_URL, data={'id': atype.pk})
        self.get_object_or_fail(ActivityType, pk=atype.pk)

        activity = self.get_object_or_fail(Activity, pk=activity.pk)
        self.assertEqual(atype, activity.type)

    def test_createview_popup1(self):
        "With existing activity type and start date given"
        self.login()
        user = self.user
        my_calendar = Calendar.get_user_default_calendar(user)

        url = self.ADD_POPUP_URL
        #today = datetime.today().replace(second=0, microsecond=0)
        today = make_naive(now().replace(second=0, microsecond=0), get_current_timezone()) #beurkk
 
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            start_f = fields['start']
            end_f = fields['end']

        self.assertTemplateUsed(response, 'activities/frags/activity_form_content.html')
        self.assertContains(response, 'name="title"') #it seems TemplateDoesNotExists is not raised in unit tests

        initial_start = start_f.initial
        self.assertIsInstance(initial_start, datetime)

        self.assertGreaterEqual(initial_start, today)
        self.assertLessEqual(initial_start, datetime.today())
        #self.assertLessEqual(initial_start, now())

        initial_end = end_f.initial
        self.assertIsNone(initial_end)
        #self.assertIsInstance(initial_end, datetime)
        #self.assertEqual(initial_end - initial_start, timedelta(hours=1))

        title = "meeting activity popup 1"
        response = self.client.post(url, data={'user':          user.pk,
                                               'title':         title,
                                               'type_selector': self._acttype_field_value(ACTIVITYTYPE_MEETING,
                                                                                          ACTIVITYSUBTYPE_MEETING_NETWORK,
                                                                                         ),
                                               'start':         '2010-1-10',
                                               'end':           '2010-1-10',
                                               'start_time':    '09:30:00',
                                               'end_time':      '15:00:00',
                                              }
                                   )
        self.assertFormError(response, 'form', None, _(u'No participant'))

        response = self.client.post(url, data={'user':          user.pk,
                                               'title':         title,
                                               'type_selector': self._acttype_field_value(ACTIVITYTYPE_MEETING,
                                                                                          ACTIVITYSUBTYPE_MEETING_NETWORK,
                                                                                         ),
                                               'my_participation': True,
                                               'start':         '2010-1-10',
                                               'end':           '2010-1-10',
                                               'start_time':    '09:30:00',
                                               'end_time':      '15:00:00',
                                              }
                                   )

        self.assertFormError(response, 'form', 'my_calendar',
                               _(u"If you participate, you have to choose one of your calendars.")
                              )

        response = self.client.post(url, data={'user':          user.pk,
                                               'title':         title,
                                               'type_selector': self._acttype_field_value(ACTIVITYTYPE_MEETING,
                                                                                          ACTIVITYSUBTYPE_MEETING_NETWORK,
                                                                                         ),
                                               'my_participation': True,
                                               'my_calendar':      my_calendar.pk,
                                               'start':            '2010-1-10',
                                               'end':              '2010-1-10',
                                               'start_time':       '09:30:00',
                                               'end_time':         '15:00:00',
                                              }
                                   )

        self.assertNoFormError(response)
        self.assertEqual(1, Activity.objects.count())

        activity = self.get_object_or_fail(Activity, title=title)
        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2010, month=1, day=10, hour=9, minute=30, second=0), activity.start)
        self.assertEqual(create_dt(year=2010, month=1, day=10, hour=15, minute=0, second=0), activity.end)
        self.assertEqual(ACTIVITYTYPE_MEETING, activity.type_id)
        self.assertEqual(ACTIVITYSUBTYPE_MEETING_NETWORK, activity.sub_type_id)

    def test_createview_popup2(self):
        "With existing activity type and start date given"
        self.login()
        user = self.user
        my_calendar = Calendar.get_user_default_calendar(user)
        title = "meeting activity popup 2"
        response = self.client.post(self.ADD_POPUP_URL,
                                    data={'user':           self.user.pk,
                                          'title':          title,
                                          'type_selector':  self._acttype_field_value(ACTIVITYTYPE_PHONECALL, 
                                                                                      ACTIVITYSUBTYPE_PHONECALL_CONFERENCE,
                                                                                     ),
                                          'my_participation': True,
                                          'my_calendar': my_calendar.pk,
                                          'start':          '2010-3-15',
                                          'end':            '2010-3-15',
                                          'start_time':     '19:30:00',
                                          'end_time':       '20:00:00',
                                         }
                                   )

        self.assertNoFormError(response)
        self.assertEqual(1, Activity.objects.count())

        activity = self.get_object_or_fail(Activity, title=title)
        create_dt = partial(self.create_datetime, year=2010, month=3, day=15)
        self.assertEqual(create_dt(hour=19, minute=30, second=0), activity.start)
        self.assertEqual(create_dt(hour=20, minute=0,  second=0), activity.end)
        self.assertEqual(ACTIVITYTYPE_PHONECALL, activity.type_id)
        self.assertEqual(ACTIVITYSUBTYPE_PHONECALL_CONFERENCE, activity.sub_type_id)

    def test_createview_popup3(self):
        "With custom activity type and without start date given"
        self.login()
        user = self.user
        my_calendar = Calendar.get_user_default_calendar(user)

        ACTIVITYTYPE_ACTIVITY = 'activities-activity_custom_1'
        create_or_update(ActivityType, ACTIVITYTYPE_ACTIVITY, name='Karate session',
                         default_day_duration=0, default_hour_duration="00:15:00", is_custom=True
                        )

        create_dt = self.create_datetime

        def post(title, today):
            response = self.client.post(self.ADD_POPUP_URL,
                                        data={'user':             user.pk,
                                              'title':            title,
                                              'type_selector':    self._acttype_field_value(ACTIVITYTYPE_ACTIVITY),
                                              'start':            date_format(today),
                                              'my_participation': True,
                                              'my_calendar':      my_calendar.pk,
                                             }
                                    )

            self.assertNoFormError(response)

            activity = self.get_object_or_fail(Activity, title=title)
            self.assertEqual(ACTIVITYTYPE_ACTIVITY, activity.type_id)
            self.assertIsNone(activity.sub_type)

            create_today_dt = partial(create_dt, year=today.year, month=today.month, day=today.day)
            self.assertEqual(create_today_dt(hour=0,  minute=0,  second=0), activity.start)
            self.assertEqual(create_today_dt(hour=23, minute=59, second=0), activity.end)

        post("meeting activity popup 3a", create_dt(year=2013, month=10, day=28, hour=11)) #No DST change for Europe/Paris
        post("meeting activity popup 3b", create_dt(year=2013, month=10, day=27, hour=11)) #Timezone DST change for Europe/Paris

    def test_createview_popup4(self):
        "Beware when it's 23 o clock (bugfix)"
        self.login()

        response = self.assertGET200(self.ADD_POPUP_URL,
                                     data={'year':   2012,
                                           'month':  3,
                                           'day':    26,
                                           'hour':   23,
                                           'minute': 16,
                                          }
                                    )

        with self.assertNoException():
            fields = response.context['form'].fields
            start_f = fields['start']
            end_f = fields['end']
            start_time_f = fields['start_time']
            end_time_f = fields['end_time']

        self.assertEqual(date(year=2012, month=3, day=26), start_f.initial.date())
        #self.assertEqual(date(year=2012, month=3, day=27), end_f.initial.date())
        self.assertIsNone(end_f.initial)
        self.assertEqual(time(hour=23, minute=16), start_time_f.initial)
        #self.assertEqual(time(hour=0, minute=16),  end_time_f.initial)
        self.assertIsNone(end_time_f.initial)

    def test_dl_ical(self):
        self.login()

        create_act = partial(Activity.objects.create, user=self.user,
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

        response = self.assertGET200('/activities/activities/%s,%s/ical' % (
                                            act1.id, act2.id
                                        )
                                    )
        self.assertEqual('text/calendar', response['Content-Type'])
        self.assertEqual('attachment; filename=Calendar.ics',
                         response['Content-Disposition']
                        )

        content = force_unicode(response.content)
        self.assertTrue(content.startswith('BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//CremeCRM//CremeCRM//EN\n'
                                           'BEGIN:VEVENT\n'
                                           'UID:http://cremecrm.com\n'
                                          )
                       )
        self.assertIn(u'SUMMARY:Act#2\n'
                      u'DTSTART:20130402T090000Z\n'
                      u'DTEND:20130402T100000Z\n'
                      u'LOCATION:\n'
                      u'CATEGORIES:%s\n'
                      u'STATUS:\n'
                      u'END:VEVENT\n' %  act2.type.name,
                      content
                     )
        self.assertIn(u'SUMMARY:Act#1\n', content)
        self.assertTrue(content.endswith('END:VCALENDAR'))
