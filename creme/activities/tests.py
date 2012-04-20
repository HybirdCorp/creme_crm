# -*- coding: utf-8 -*-

try:
    from datetime import datetime, date

    from django.forms.util import ValidationError
    from django.core.serializers.json import simplejson
    from django.utils.translation import ugettext as _
    from django.utils.formats import date_format
    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import RelationType, Relation, SetCredentials
    from creme_core.constants import REL_SUB_HAS
    from creme_core.tests.base import CremeTestCase
    from creme_core.utils import create_or_update

    from persons.models import Contact, Organisation

    from assistants.models import Alert

    from activities.models import *
    from activities.constants import *
    from activities.forms.activity import _check_activity_collisions
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class ActivitiesTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'activities') #'persons'

    def login(self, is_superuser=True):
        super(ActivitiesTestCase, self).login(is_superuser, allowed_apps=['activities', 'persons']) #'creme_core'

    def _aux_build_setcreds(self):
        role = self.role
        SetCredentials.objects.create(role=role,
                                      value=SetCredentials.CRED_LINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )
        SetCredentials.objects.create(role=role,
                                      value=SetCredentials.CRED_VIEW   | \
                                            SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | \
                                            SetCredentials.CRED_UNLINK, #not CRED_LINK
                                      set_type=SetCredentials.ESET_ALL
                                     )

    def test_populate(self):
        rtypes_pks = [REL_SUB_LINKED_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT, REL_SUB_PART_2_ACTIVITY]
        rtypes = RelationType.objects.filter(pk__in=rtypes_pks)
        self.assertEqual(len(rtypes_pks), len(rtypes))

        acttypes_pks = [ACTIVITYTYPE_TASK, ACTIVITYTYPE_MEETING, ACTIVITYTYPE_PHONECALL,
                        ACTIVITYTYPE_GATHERING, ACTIVITYTYPE_SHOW, ACTIVITYTYPE_DEMO,
                        ACTIVITYTYPE_INDISPO,
                       ]
        acttypes = ActivityType.objects.filter(pk__in=acttypes_pks)
        self.assertEqual(len(acttypes_pks), len(acttypes))

    def test_portal(self):
        self.login()
        self.assertEqual(200, self.client.get('/activities/').status_code)

    def _build_rel_field(self, entity):
        return '[{"ctype":"%s", "entity":"%s"}]' % (entity.entity_type_id, entity.id)

    def test_activity_createview01(self):
        self.login()

        user = self.user

        create_contact = Contact.objects.create
        me    = create_contact(user=user, first_name='Ryoga', last_name='Hibiki', is_user=user)
        ranma = create_contact(user=user, first_name='Ranma', last_name='Saotome')
        genma = create_contact(user=user, first_name='Genma', last_name='Saotome')

        dojo = Organisation.objects.create(user=user, name='Dojo')

        url = '/activities/activity/add/task'
        self.assertEqual(200, self.client.get(url).status_code)

        title  = 'my_task'
        status = Status.objects.all()[0]
        my_calendar = Calendar.get_user_default_calendar(self.user)
        response = self.client.post(url, follow=True,
                                    data={'user':               user.pk,
                                          'title':              title,
                                          'status':             status.pk,
                                          'start':              '2010-1-10',
                                          'my_participation':   True,
                                          'my_calendar':        my_calendar.pk,
                                          'other_participants': genma.id,
                                          'subjects':           self._build_rel_field(ranma),
                                          'linked_entities':    self._build_rel_field(dojo),
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            act  = Activity.objects.get(type=ACTIVITYTYPE_TASK, title=title)
            task = Task.objects.get(title=title)

        self.assertEqual(act.id, task.id)
        self.assertEqual(status, task.status)
        self.assertEqual(date(year=2010, month=1, day=10), task.start.date())

        self.assertEqual(4 * 2, Relation.objects.count()) # * 2: relations have their symmetric ones

        self.assertRelationCount(1, me,    REL_SUB_PART_2_ACTIVITY,   task)
        self.assertRelationCount(1, genma, REL_SUB_PART_2_ACTIVITY,   task)
        self.assertRelationCount(1, ranma, REL_SUB_ACTIVITY_SUBJECT,  task)
        self.assertRelationCount(1, dojo,  REL_SUB_LINKED_2_ACTIVITY, task)

    def test_activity_createview02(self): #creds errors
        self.login(is_superuser=False)
        self._aux_build_setcreds()
        self.role.creatable_ctypes = [ContentType.objects.get_for_model(Activity)]

        user = self.user
        other_user = self.other_user

        my_calendar = Calendar.get_user_default_calendar(user)

        create_contact = Contact.objects.create
        ryoga = create_contact(user=other_user, first_name='Ryoga', last_name='Hibiki',  is_user=user)
        ranma = create_contact(user=other_user, first_name='Ranma', last_name='Saotome', is_user=other_user)
        genma = create_contact(user=other_user, first_name='Genma', last_name='Saotome')
        akane = create_contact(user=other_user, first_name='Akane', last_name='Tendo')

        dojo = Organisation.objects.create(user=other_user, name='Dojo')

        response = self.client.post('/activities/activity/add/meeting', follow=True,
                                    data={'user':                user.pk,
                                          'title':               'Fight !!',
                                          'start':               '2011-2-22',
                                          'my_participation':    True,
                                          'my_calendar':         my_calendar.pk,
                                          'participating_users': other_user.pk,
                                          'other_participants':  genma.id,
                                          'subjects':            self._build_rel_field(akane),
                                          'linked_entities':     self._build_rel_field(dojo),
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'my_participation',    [_(u'You are not allowed to link this entity: %s') % ryoga])

        msg = _(u'Some entities are not linkable: %s')
        self.assertFormError(response, 'form', 'participating_users', [msg % ranma])
        self.assertFormError(response, 'form', 'other_participants',  [msg % genma])
        self.assertFormError(response, 'form', 'subjects',            [msg % akane])
        self.assertFormError(response, 'form', 'linked_entities',     [msg % dojo])

    def test_activity_createview03(self):
        self.login()

        user = self.user

        create_contact = Contact.objects.create
        me    = create_contact(user=user, first_name='Ryoga', last_name='Hibiki', is_user=user)
        ranma = create_contact(user=user, first_name='Ranma', last_name='Saotome')
        genma = create_contact(user=user, first_name='Genma', last_name='Saotome')

        dojo = Organisation.objects.create(user=user, name='Dojo')

        url = '/activities/activity/add/activity'
        self.assertEqual(200, self.client.get(url).status_code)

        title  = 'my_task'
        status = Status.objects.all()[0]
        my_calendar = Calendar.get_user_default_calendar(self.user)
        ACTIVITYTYPE_ACTIVITY = 'activities-activity_custom_1'
        create_or_update(ActivityType, ACTIVITYTYPE_ACTIVITY, name='Karate session', color="FFFFFF",
                         default_day_duration=0, default_hour_duration="00:15:00", is_custom=True
                        )

        response = self.client.post(url, follow=True,
                                    data={'user':               user.pk,
                                          'title':              title,
                                          'status':             status.pk,
                                          'start':              '2010-1-10',
                                          'my_participation':   True,
                                          'my_calendar':        my_calendar.pk,
                                          'other_participants': genma.id,
                                          'subjects':           self._build_rel_field(ranma),
                                          'linked_entities':    self._build_rel_field(dojo),
                                          'type':               ACTIVITYTYPE_ACTIVITY,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        act = self.get_object_or_fail(Activity, type=ACTIVITYTYPE_ACTIVITY, title=title)
        self.assertEqual(status, act.status)
        self.assertEqual(date(year=2010, month=1, day=10), act.start.date())

        self.assertEqual(4 * 2, Relation.objects.count()) # * 2: relations have their symmetric ones

        self.assertRelationCount(1, me,    REL_SUB_PART_2_ACTIVITY,   act)
        self.assertRelationCount(1, genma, REL_SUB_PART_2_ACTIVITY,   act)
        self.assertRelationCount(1, ranma, REL_SUB_ACTIVITY_SUBJECT,  act)
        self.assertRelationCount(1, dojo,  REL_SUB_LINKED_2_ACTIVITY, act)

    def test_activity_createview04(self):#Alert generation
        self.login()

        user = self.user
        url = '/activities/activity/add/meeting'
        self.assertEqual(200, self.client.get(url).status_code)

        title  = 'meeting01'
        status = Status.objects.all()[0]
        my_calendar = Calendar.get_user_default_calendar(self.user)
        response = self.client.post(url, follow=True,
                                    data={'user':                     user.pk,
                                          'title':                    title,
                                          'status':                   status.pk,
                                          'start':                    '2010-1-10',
                                          'my_participation':         True,
                                          'my_calendar':              my_calendar.pk,
                                          'generate_datetime_alert':  True,
                                          'alert_start_time':         '10:05',
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            act  = Activity.objects.get(type=ACTIVITYTYPE_MEETING, title=title)
            meeting = Meeting.objects.get(title=title)

        self.assertEqual(act.id, meeting.id)
        self.assertEqual(status, meeting.status)
        self.assertEqual(date(year=2010, month=1, day=10), meeting.start.date())

        alert = self.get_object_or_fail(Alert, entity_id=meeting.id)
        self.assertEqual(datetime(2010, 1, 10, 10, 05), alert.trigger_date)

    def test_activity_createview_related01(self):
        self.login()

        user = self.user
        other_user = self.other_user

        create_contact = Contact.objects.create
        contact01 = create_contact(user=user, first_name='Ryoga', last_name='Hibiki')
        contact02 = create_contact(user=user, first_name='Akane', last_name='Tendo', is_user=other_user)

        args = '&'.join(['ct_entity_for_relation=%s' % contact01.entity_type_id,
                         'id_entity_for_relation=%s' % contact01.id,
                         'entity_relation_type=%s' % REL_SUB_PART_2_ACTIVITY
                        ])
        uri = '/activities/activity/add_related/meeting?' + args

        response = self.client.get(uri)
        self.assertEqual(response.status_code, 200)

        with self.assertNoException():
            other_participants = response.context['form'].fields['other_participants']

        self.assertEqual([contact01.id], other_participants.initial)

        title  = 'my_meeting'
        response = self.client.post(uri, follow=True,
                                    data={'user':                user.pk,
                                          'title':               title,
                                          'start':               '2010-1-10',
                                          'start_time':          '17:30:00',
                                          'end_time':            '18:30:00',
                                          'participating_users': other_user.pk,
                                         }
                                    )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.redirect_chain)
        self.assertEqual(u"http://testserver%s" % contact01.get_absolute_url(), response.redirect_chain[-1][0])#Redirect to related entity detailview

        meeting = self.get_object_or_fail(Meeting, title=title)
        self.assertEqual(datetime(year=2010, month=1, day=10, hour=17, minute=30), meeting.start)

        self.assertEqual(2, Relation.objects.count())

        relations = Relation.objects.filter(type=REL_SUB_PART_2_ACTIVITY)
        self.assertEqual(1, len(relations))

        relation = relations[0]
        self.assertEqual(contact02.id, relation.subject_entity_id)
        self.assertEqual(meeting.id,   relation.object_entity_id)

    def test_activity_createview_related02(self):
        self.login()

        user = self.user
        ryoga = Contact.objects.create(user=user, first_name='Ryoga', last_name='Hibiki', is_user=self.other_user)
        response = self.client.get('/activities/activity/add_related/phonecall',
                                  data={'ct_entity_for_relation': ryoga.entity_type_id,
                                        'id_entity_for_relation': ryoga.id,
                                        'entity_relation_type':   REL_SUB_PART_2_ACTIVITY,
                                       }
                                  )
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            users = response.context['form'].fields['participating_users']

        self.assertEqual([self.other_user.id], [e.id for e in users.initial])

    def test_activity_createview_related03(self):
        self.login()

        user = self.user
        ryoga = Contact.objects.create(user=user, first_name='Ryoga', last_name='Hibiki')
        response = self.client.get('/activities/activity/add_related/phonecall',
                                  data={'ct_entity_for_relation': ryoga.entity_type_id,
                                        'id_entity_for_relation': ryoga.id,
                                        'entity_relation_type':   REL_SUB_ACTIVITY_SUBJECT,
                                       }
                                  )
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            subjects = response.context['form'].fields['subjects']

        self.assertEqual([ryoga.id], [e.id for e in subjects.initial])

    def test_activity_createview_related04(self):
        self.login()

        user = self.user
        ryoga = Contact.objects.create(user=user, first_name='Ryoga', last_name='Hibiki')
        response = self.client.get('/activities/activity/add_related/phonecall?',
                                   data={'ct_entity_for_relation': ryoga.entity_type_id,
                                         'id_entity_for_relation': ryoga.id,
                                         'entity_relation_type':   REL_SUB_LINKED_2_ACTIVITY,
                                        }
                                  )
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            linked_entities = response.context['form'].fields['linked_entities']

        self.assertEqual([ryoga.id], [e.id for e in linked_entities.initial])

    def test_activity_createview_404(self):
        self.login()

        self.assertEqual(200, self.client.get('/activities/activity/add/meeting').status_code)
        self.assertEqual(200, self.client.get('/activities/activity/add/phonecall').status_code)
        self.assertEqual(404, self.client.get('/activities/activity/add/foobar').status_code)

        c = Contact.objects.create(user=self.user, first_name='first_name', last_name='last_name')
        args = {'ct_entity_for_relation': c.entity_type_id,
                'id_entity_for_relation': c.id,
                'entity_relation_type':   REL_SUB_LINKED_2_ACTIVITY,
               }

        self.assertEqual(200, self.client.get('/activities/activity/add_related/meeting',   data=args).status_code)
        self.assertEqual(200, self.client.get('/activities/activity/add_related/phonecall', data=args).status_code)
        self.assertEqual(404, self.client.get('/activities/activity/add_related/foobar',    data=args).status_code)

    def test_activity_editview01(self):
        self.login()

        title = 'meet01'
        activity = Meeting.objects.create(user=self.user, title=title,
                                          start=datetime(year=2010, month=10, day=1, hour=14, minute=0),
                                          end=datetime(year=2010, month=10, day=1, hour=15, minute=0)
                                         )
        url = '/activities/activity/edit/%s' % activity.id

        self.assertEqual(200, self.client.get(url).status_code)

        title += '_edited'
        response = self.client.post(url, follow=True, data={'user':  self.user.pk,
                                                            'title': title,
                                                            'start': '2011-2-22',
                                                           }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        activity = self.refresh(activity)
        self.assertEqual(title, activity.title)
        self.assertEqual(date(year=2011, month=2, day=22), activity.start.date())

    def test_activity_editview02(self):
        self.login()

        title = 'act01'

        ACTIVITYTYPE_ACTIVITY = 'activities-activity_custom_1'
        act_type = create_or_update(ActivityType, ACTIVITYTYPE_ACTIVITY, name='Karate session', color="FFFFFF",
                                    default_day_duration=0, default_hour_duration="00:15:00", is_custom=True
                                   )

        ACTIVITYTYPE_ACTIVITY2 = 'activities-activity_custom_2'
        create_or_update(ActivityType, ACTIVITYTYPE_ACTIVITY2, name='Karate session', color="FFFFFF",
                         default_day_duration=0, default_hour_duration="00:15:00", is_custom=True
                        )

        activity = Activity.objects.create(user=self.user, title=title,
                                          start=datetime(year=2010, month=10, day=1, hour=14, minute=0),
                                          end=datetime(year=2010, month=10, day=1, hour=15, minute=0),
                                          type=act_type
                                         )
        url = '/activities/activity/edit/%s' % activity.id

        self.assertEqual(200, self.client.get(url).status_code)

        title += '_edited'
        response = self.client.post(url, follow=True,
                                    data={'user':  self.user.pk,
                                          'title': title,
                                          'start': '2011-2-22',
                                          'type' : ACTIVITYTYPE_ACTIVITY2,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        activity = self.refresh(activity)
        self.assertEqual(title, activity.title)
        self.assertEqual(date(year=2011, month=2, day=22), activity.start.date())
        self.assertEqual(ACTIVITYTYPE_ACTIVITY2, activity.type.id)

    def test_collision01(self):
        self.login()

        with self.assertNoException():
            act01 = PhoneCall.objects.create(user=self.user, title='call01',
                                             call_type=PhoneCallType.objects.all()[0],
                                             start=datetime(year=2010, month=10, day=1, hour=12, minute=0),
                                             end=datetime(year=2010, month=10, day=1, hour=13, minute=0)
                                            )
            act02 = Meeting.objects.create(user=self.user, title='meet01',
                                           start=datetime(year=2010, month=10, day=1, hour=14, minute=0),
                                           end=datetime(year=2010, month=10, day=1, hour=15, minute=0)
                                          )
            act03 = Meeting.objects.create(user=self.user, title='meet02', busy=True,
                                           start=datetime(year=2010, month=10, day=1, hour=18, minute=0),
                                           end=datetime(year=2010, month=10, day=1, hour=19, minute=0)
                                          )

            c1 = Contact.objects.create(user=self.user, first_name='first_name1', last_name='last_name1')
            c2 = Contact.objects.create(user=self.user, first_name='first_name2', last_name='last_name2')

            create_rel = Relation.objects.create
            create_rel(subject_entity=c1, type_id=REL_SUB_PART_2_ACTIVITY, object_entity=act01, user=self.user)
            create_rel(subject_entity=c1, type_id=REL_SUB_PART_2_ACTIVITY, object_entity=act02, user=self.user)
            create_rel(subject_entity=c1, type_id=REL_SUB_PART_2_ACTIVITY, object_entity=act03, user=self.user)

        try:
            #no collision
            #next day
            _check_activity_collisions(activity_start=datetime(year=2010, month=10, day=2, hour=12, minute=0),
                                       activity_end=datetime(year=2010, month=10, day=2, hour=13, minute=0),
                                       participants=[c1, c2]
                                      )

            #one minute before
            _check_activity_collisions(activity_start=datetime(year=2010, month=10, day=1, hour=11, minute=0),
                                       activity_end=datetime(year=2010, month=10, day=1, hour=11, minute=59),
                                       participants=[c1, c2]
                                      )

            #one minute after
            _check_activity_collisions(activity_start=datetime(year=2010, month=10, day=1, hour=13, minute=1),
                                       activity_end=datetime(year=2010, month=10, day=1, hour=13, minute=10),
                                       participants=[c1, c2]
                                      )
            #not busy
            _check_activity_collisions(activity_start=datetime(year=2010, month=10, day=1, hour=14, minute=0),
                                       activity_end=datetime(year=2010, month=10, day=1, hour=15, minute=0),
                                       participants=[c1, c2], busy=False
                                      )
        except ValidationError as e:
            self.fail(str(e))

        #collision with act01
        #before
        self.assertRaises(ValidationError, _check_activity_collisions,
                          activity_start=datetime(year=2010, month=10, day=1, hour=11, minute=30),
                          activity_end=datetime(year=2010, month=10, day=1, hour=12, minute=30),
                          participants=[c1, c2]
                         )

        #after
        self.assertRaises(ValidationError, _check_activity_collisions,
                          activity_start=datetime(year=2010, month=10, day=1, hour=12, minute=30),
                          activity_end=datetime(year=2010, month=10, day=1, hour=13, minute=30),
                          participants=[c1, c2]
                         )

        #shorter
        self.assertRaises(ValidationError, _check_activity_collisions,
                          activity_start=datetime(year=2010, month=10, day=1, hour=12, minute=10),
                          activity_end=datetime(year=2010, month=10, day=1, hour=12, minute=30),
                          participants=[c1, c2]
                         )

        #longer
        self.assertRaises(ValidationError, _check_activity_collisions,
                          activity_start=datetime(year=2010, month=10, day=1, hour=11, minute=0),
                          activity_end=datetime(year=2010, month=10, day=1, hour=13, minute=30),
                          participants=[c1, c2]
                         )
        #busy1
        self.assertRaises(ValidationError, _check_activity_collisions,
                          activity_start=datetime(year=2010, month=10, day=1, hour=17, minute=30),
                          activity_end=datetime(year=2010, month=10, day=1, hour=18, minute=30),
                          participants=[c1, c2]
                         )
        #busy2
        self.assertRaises(ValidationError, _check_activity_collisions,
                          activity_start=datetime(year=2010, month=10, day=1, hour=18, minute=0),
                          activity_end=datetime(year=2010, month=10, day=1, hour=18, minute=30),
                          busy=False, participants=[c1, c2]
                         )

    def _create_meeting(self):
        return Meeting.objects.create(user=self.user, title='meet01',
                                      start=datetime(year=2011, month=2, day=1, hour=14, minute=0),
                                      end=datetime(year=2011,   month=2, day=1, hour=15, minute=0)
                                     )

    def test_listview(self):
        self.login()

        PhoneCall.objects.create(user=self.user, title='call01',
                                 call_type=PhoneCallType.objects.all()[0],
                                 start=datetime(year=2010, month=10, day=1, hour=12, minute=0),
                                 end=datetime(year=2010, month=10, day=1, hour=13, minute=0)
                                )
        Meeting.objects.create(user=self.user, title='meet01',
                               start=datetime(year=2010, month=10, day=1, hour=14, minute=0),
                               end=datetime(year=2010, month=10, day=1, hour=15, minute=0)
                              )

        self.assertEqual(200, self.client.get('/activities/activities').status_code)

    def test_unlink01(self):
        self.login()

        activity = self._create_meeting()
        contact = Contact.objects.create(user=self.user, first_name='Musashi', last_name='Miyamoto')

        create_rel = Relation.objects.create
        r1 = create_rel(subject_entity=contact, type_id=REL_SUB_PART_2_ACTIVITY,   object_entity=activity, user=self.user)
        r2 = create_rel(subject_entity=contact, type_id=REL_SUB_ACTIVITY_SUBJECT,  object_entity=activity, user=self.user)
        r3 = create_rel(subject_entity=contact, type_id=REL_SUB_LINKED_2_ACTIVITY, object_entity=activity, user=self.user)
        r4 = create_rel(subject_entity=contact, type_id=REL_SUB_HAS,               object_entity=activity, user=self.user)
        self.assertEqual(3, contact.relations.filter(pk__in=[r1.id, r2.id, r3.id]).count())

        def unlink_status(data):
            return self.client.post('/activities/linked_activity/unlink', data=data).status_code

        self.assertEqual(200, unlink_status({'id': activity.id, 'object_id': contact.id}))
        self.assertEqual(0,   contact.relations.filter(pk__in=[r1.id, r2.id, r3.id]).count())
        self.assertEqual(1,   contact.relations.filter(pk=r4.id).count())

        #errors
        self.assertEqual(404, unlink_status({'id':        activity.id}))
        self.assertEqual(404, unlink_status({'object_id': contact.id}))
        self.assertEqual(404, unlink_status({}))
        self.assertEqual(404, unlink_status({'id': 1024,        'object_id': contact.id}))
        self.assertEqual(404, unlink_status({'id': activity.id, 'object_id': 1024}))

    def test_unlink02(self): #can not unlink the activity
        self.login(is_superuser=False)
        SetCredentials.objects.create(role=self.user.role,
                                      value=SetCredentials.CRED_VIEW   | \
                                            SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | \
                                            SetCredentials.CRED_LINK,
                                      set_type=SetCredentials.ESET_OWN)

        activity = self._create_meeting()
        contact = Contact.objects.create(user=self.user, first_name='Musashi', last_name='Miyamoto')
        relation = Relation.objects.create(subject_entity=contact, type_id=REL_SUB_PART_2_ACTIVITY,
                                           object_entity=activity, user=self.user
                                          )

        self.assertEqual(403, self.client.post('/activities/linked_activity/unlink', data={'id': activity.id, 'object_id': contact.id}).status_code)
        self.assertEqual(1,   contact.relations.filter(pk=relation.id).count())

    def test_unlink03(self): #can not unlink the contact
        self.login(is_superuser=False)

        create_creds = SetCredentials.objects.create
        create_creds(role=self.role,
                     value=SetCredentials.CRED_VIEW   | SetCredentials.CRED_CHANGE | \
                           SetCredentials.CRED_DELETE | SetCredentials.CRED_LINK   | \
                           SetCredentials.CRED_UNLINK,
                     set_type=SetCredentials.ESET_OWN
                    )
        create_creds(role=self.role,
                     value=SetCredentials.CRED_VIEW   | SetCredentials.CRED_CHANGE | \
                           SetCredentials.CRED_DELETE | SetCredentials.CRED_LINK,
                     set_type=SetCredentials.ESET_ALL
                    )

        activity = self._create_meeting()
        contact = Contact.objects.create(user=self.other_user, first_name='Musashi', last_name='Miyamoto')
        relation = Relation.objects.create(subject_entity=contact, type_id=REL_SUB_PART_2_ACTIVITY,
                                           object_entity=activity, user=self.user
                                          )

        self.assertEqual(403, self.client.post('/activities/linked_activity/unlink',
                                               data={'id': activity.id, 'object_id': contact.id}
                                              ) \
                                         .status_code
                        )
        self.assertEqual(1,   contact.relations.filter(pk=relation.id).count())

    def test_add_participants01(self):
        self.login()

        activity = self._create_meeting()

        create_contact = Contact.objects.create
        contact01 = create_contact(user=self.user, first_name='Musashi', last_name='Miyamoto')
        contact02 = create_contact(user=self.user, first_name='Kojiro',  last_name='Sasaki')
        ids = (contact01.id, contact02.id)

        uri = '/activities/activity/%s/participant/add' % activity.id
        self.assertEqual(200, self.client.get(uri).status_code)

        response = self.client.post(uri, data={'participants': '%s,%s' % ids})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        relations = Relation.objects.filter(subject_entity=activity.id, type=REL_OBJ_PART_2_ACTIVITY)
        self.assertEqual(2, len(relations))
        self.assertEqual(set(ids), set(r.object_entity_id for r in relations))

    def test_add_participants02(self): #credentials error with the activity
        self.login(is_superuser=False)
        SetCredentials.objects.create(role=self.user.role,
                                      value=SetCredentials.CRED_VIEW   | \
                                            SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | \
                                            SetCredentials.CRED_UNLINK,
                                      set_type=SetCredentials.ESET_OWN)

        activity = self._create_meeting()
        self.assertTrue(activity.can_change(self.user))
        self.assertFalse(activity.can_link(self.user))
        self.assertEqual(403, self.client.get('/activities/activity/%s/participant/add' % activity.id).status_code)

    def test_add_participants03(self): #credentials error with selected subjects
        self.login(is_superuser=False)
        self._aux_build_setcreds()

        activity = self._create_meeting()
        self.assertTrue(activity.can_link(self.user))

        contact = Contact.objects.create(user=self.other_user, first_name='Musashi', last_name='Miyamoto')
        self.assertTrue(contact.can_change(self.user))
        self.assertFalse(contact.can_link(self.user))

        uri = '/activities/activity/%s/participant/add' % activity.id
        self.assertEqual(200, self.client.get(uri).status_code)

        response = self.client.post(uri, data={'participants': contact.id})
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'participants', [_(u'Some entities are not linkable: %s') % contact])
        self.assertEqual(0, Relation.objects.filter(subject_entity=activity.id, type=REL_OBJ_PART_2_ACTIVITY).count())

    def test_add_subjects01(self):
        self.login()

        activity = self._create_meeting()
        orga = Organisation.objects.create(user=self.user, name='Ghibli')

        uri = '/activities/activity/%s/subject/add' % activity.id
        self.assertEqual(200, self.client.get(uri).status_code)

        response = self.client.post(uri, data={'subjects': self._build_rel_field(orga)})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        relations = Relation.objects.filter(subject_entity=activity.id, type=REL_OBJ_ACTIVITY_SUBJECT)
        self.assertEqual(1, len(relations))
        self.assertEqual(orga.id, relations[0].object_entity_id)

    def test_add_subjects02(self): #credentials error with the activity
        self.login(is_superuser=False)
        SetCredentials.objects.create(role=self.user.role,
                                      value=SetCredentials.CRED_VIEW   | \
                                            SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | \
                                            SetCredentials.CRED_UNLINK,
                                      set_type=SetCredentials.ESET_OWN)

        activity = self._create_meeting()
        self.assertTrue(activity.can_change(self.user))
        self.assertFalse(activity.can_link(self.user))
        self.assertEqual(403, self.client.get('/activities/activity/%s/subject/add' % activity.id).status_code)

    def test_add_subjects03(self): #credentials error with selected subjects
        self.login(is_superuser=False)
        self._aux_build_setcreds()

        activity = self._create_meeting()
        self.assertTrue(activity.can_link(self.user))

        orga = Organisation.objects.create(user=self.other_user, name='Ghibli')
        self.assertTrue(orga.can_change(self.user))
        self.failIf(orga.can_link(self.user))

        uri = '/activities/activity/%s/subject/add' % activity.id
        self.assertEqual(200, self.client.get(uri).status_code)

        response = self.client.post(uri, data={'subjects': self._build_rel_field(orga)})
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'subjects', [_(u'Some entities are not linkable: %s') % orga])
        self.assertFalse(Relation.objects.filter(subject_entity=activity.id, type=REL_OBJ_ACTIVITY_SUBJECT))

    def test_get_entity_relation_choices(self):
        self.login()

        url = '/activities/get_relationtype_choices'
        self.assertPOST404(url)
        self.assertPOST404(url, data={'ct_id': 'blubkluk'})

        get_ct = ContentType.objects.get_for_model
        response = self.client.post(url, data={'ct_id': get_ct(Contact).id})
        self.assertEqual(200, response.status_code)

        content = simplejson.loads(response.content)
        self.assertTrue(isinstance(content, list))
        self.assertEqual([{"pk": REL_SUB_PART_2_ACTIVITY,   "predicate": _(u"participates to the activity")},
                          {"pk": REL_SUB_ACTIVITY_SUBJECT,  "predicate": _(u"is subject of the activity")},
                          {"pk": REL_SUB_LINKED_2_ACTIVITY, "predicate": _(u"related to the activity")}
                         ],
                         content
                        )

        response = self.client.post(url, data={'ct_id': get_ct(Organisation).id})
        self.assertEqual(200, response.status_code)
        self.assertEqual([{"pk": REL_SUB_ACTIVITY_SUBJECT,  "predicate": _(u"is subject of the activity")},
                          {"pk": REL_SUB_LINKED_2_ACTIVITY, "predicate": _(u"related to the activity")},
                         ],
                         simplejson.loads(response.content)
                        )

    def assertUserHasDefaultCalendar(self, user):
        with self.assertNoException():
            return Calendar.objects.get(is_default=True, user=user)

    def test_user_default_calendar(self):
        self.login()
        user = self.user
        def_cal = Calendar.get_user_default_calendar(self.user)
        def_cal2 = self.assertUserHasDefaultCalendar(user)
        self.assertEqual(def_cal, def_cal2)

    def test_add_user_calendar01(self):
        self.login()
        user = self.user
        url = '/activities/calendar/add'
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={'name': 'whatever',
                                               #'user': user.id
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(1, Calendar.objects.filter(user=user).count())

        self.assertUserHasDefaultCalendar(user)

    #TODO: If we change the user, may the first user will have a default calendar?
    def test_edit_user_calendar01(self):
        self.login()
        user = self.user

        cal = Calendar.get_user_default_calendar(self.user)
        cal_name = "My calendar"

        url = '/activities/calendar/%s/edit' % cal.id
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        response = self.client.post(url, data={'name': cal_name,
                                               #'user': user.id
                                              }
                                   )
        self.assertNoFormError(response)

        cal2 = self.get_object_or_fail(Calendar, pk=cal.id)
        self.assertEqual(1, Calendar.objects.filter(user=user).count())
        self.assertEqual(cal_name, cal2.name)

        self.assertUserHasDefaultCalendar(user)
#TODO: complete test case

    def test_indisponibility_createview01(self):
        self.login()

        user = self.user
        me = Contact.objects.create(user=user, is_user=user, first_name='Ryoga', last_name='Hibiki')

        url = '/activities/indisponibility/add'
        self.assertEqual(200, self.client.get(url).status_code)

        title  = 'away'
        status = Status.objects.all()[0]
        my_calendar = Calendar.get_user_default_calendar(self.user)

        response = self.client.post(url, follow=True,
                                    data={'user':               user.pk,
                                          'title':              title,
                                          'status':             status.pk,
                                          'start':              '2010-1-10',
                                          'end':                '2010-1-12',
                                          'start_time':         '09:08:07',
                                          'end_time':           '06:05:04',
                                          'my_participation':   True,
                                          'my_calendar':        my_calendar.pk,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        act = self.get_object_or_fail(Activity, type=ACTIVITYTYPE_INDISPO, title=title)
        self.assertEqual(datetime(year=2010, month=1, day=10, hour=9, minute=8, second=7), act.start)
        self.assertEqual(datetime(year=2010, month=1, day=12, hour=6, minute=5, second=4), act.end)

    def test_indisponibility_createview02(self):
        self.login()

        user = self.user
        me = Contact.objects.create(user=user, is_user=user, first_name='Ryoga', last_name='Hibiki')

        title  = 'away'
        status = Status.objects.all()[0]
        my_calendar = Calendar.get_user_default_calendar(self.user)

        response = self.client.post('/activities/indisponibility/add', follow=True,
                                    data={'user':               user.pk,
                                          'title':              title,
                                          'status':             status.pk,
                                          'start':              '2010-1-10',
                                          'end':                '2010-1-12',
                                          'start_time':         '09:08:07',
                                          'end_time':           '06:05:04',
                                          'is_all_day':         True,
                                          'my_participation':   True,
                                          'my_calendar':        my_calendar.pk,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        act = self.get_object_or_fail(Activity, type=ACTIVITYTYPE_INDISPO, title=title)
        self.assertTrue(act.is_all_day)
        self.assertEqual(date(year=2010, month=1, day=10), act.start.date())
        self.assertEqual(date(year=2010, month=1, day=12), act.end.date())

    def test_detete_activity_type01(self):
        self.login()

        ACTIVITYTYPE_ACTIVITY = 'activities-activity_custom_1'
        atype = create_or_update(ActivityType, ACTIVITYTYPE_ACTIVITY, name='Karate session', color="FFFFFF",
                                 default_day_duration=0, default_hour_duration="00:15:00", is_custom=True
                                )

        response = self.client.post('/creme_config/activities/activity_type/delete', data={'id': atype.pk})
        self.assertEqual(200, response.status_code)
        self.assertFalse(ActivityType.objects.filter(pk=atype.pk).exists())

    def test_detete_activity_type02(self):
        self.login()

        ACTIVITYTYPE_ACTIVITY = 'activities-activity_custom_1'
        atype = create_or_update(ActivityType, ACTIVITYTYPE_ACTIVITY, name='Karate session', color="FFFFFF",
                                 default_day_duration=0, default_hour_duration="00:15:00", is_custom=True
                                )

        activity = Activity.objects.create(user=self.user, type=atype)

        response = self.client.post('/creme_config/activities/activity_type/delete', data={'id': atype.pk})
        self.assertEqual(404, response.status_code)
        self.assertTrue(ActivityType.objects.filter(pk=atype.pk).exists())

        activity = self.get_object_or_fail(Activity, pk=activity.pk)
        self.assertEqual(atype, activity.type)

    def test_activity_createview_popup1(self): # with existing activity type and start date given
        self.login()

        url = '/activities/activity/add_popup'
        self.assertEqual(200, self.client.get(url).status_code)

        title = "meeting activity popup 1"
        response = self.client.post(url, data={'user':       self.user.pk,
                                               'title':      title,
                                               'type':       ACTIVITYTYPE_MEETING,
                                               'start':      '2010-1-10',
                                               'end':        '2010-1-10',
                                               'start_time': '09:30:00',
                                               'end_time':   '15:00:00',
                                              }
                                   )

        self.assertNoFormError(response)
        self.assertEqual(1, Meeting.objects.count())

        activity = self.get_object_or_fail(Meeting, title=title)
        self.assertEqual(datetime(year=2010, month=1, day=10, hour=9, minute=30, second=0), activity.start)
        self.assertEqual(datetime(year=2010, month=1, day=10, hour=15, minute=0, second=0), activity.end)
        self.assertEqual(ACTIVITYTYPE_MEETING, activity.type_id)

    def test_activity_createview_popup2(self): # with existing activity type and start date given
        self.login()

        title = "meeting activity popup 2"
        response = self.client.post('/activities/activity/add_popup',
                                    data={'user':       self.user.pk,
                                          'title':      title,
                                          'type':       ACTIVITYTYPE_PHONECALL,
                                          'start':      '2010-3-15',
                                          'end':        '2010-3-15',
                                          'start_time': '19:30:00',
                                          'end_time':   '20:00:00',
                                         }
                                   )

        self.assertNoFormError(response)
        self.assertEqual(1, PhoneCall.objects.count())

        activity = self.get_object_or_fail(PhoneCall, title=title)
        self.assertEqual(datetime(year=2010, month=3, day=15, hour=19, minute=30, second=0), activity.start)
        self.assertEqual(datetime(year=2010, month=3, day=15, hour=20, minute=0, second=0), activity.end)
        self.assertEqual(ACTIVITYTYPE_PHONECALL, activity.type_id)

    def test_activity_createview_popup3(self): # with custom activity type and without start date given
        self.login()

        ACTIVITYTYPE_ACTIVITY = 'activities-activity_custom_1'
        create_or_update(ActivityType, ACTIVITYTYPE_ACTIVITY, name='Karate session', color="FFFFFF",
                         default_day_duration=0, default_hour_duration="00:15:00", is_custom=True
                        )

        today = datetime.today()
        title = "meeting activity popup 3"
        response = self.client.post('/activities/activity/add_popup',
                                    data={'user':  self.user.pk,
                                          'title': title,
                                          'type':  ACTIVITYTYPE_ACTIVITY,
                                          'start': date_format(today),
                                         }
                                   )

        self.assertNoFormError(response)
        self.assertEqual(1, Activity.objects.count())

        activity = self.get_object_or_fail(Activity, title=title)
        mydate = datetime(year=today.year, month=today.month, day=today.day, hour=0, minute=0, second=0)
        self.assertEqual(mydate, activity.start)
        self.assertEqual(mydate, activity.end)
        self.assertEqual(ACTIVITYTYPE_ACTIVITY, activity.type_id)

    def _set_activity_context(self):
        self.login()
        # Case 1 : logged contact user
        logged_user = Contact.objects.create(last_name='robert', first_name='foo', user=self.user, is_user=self.user)
        # Case 2 : contact user
        other_contact_user = Contact.objects.create(last_name='jean', first_name='bon', user=self.user, is_user=self.other_user)
        # Case 3 : classic contact
        classic_contact = Contact.objects.create(last_name='michel', first_name='durant', user=self.user)
        # Activity
        phone_call = PhoneCall.objects.create(title='a random activity',
                                              start=datetime.today(), end=datetime.today(),
                                              user=self.user, type_id=ACTIVITYTYPE_PHONECALL
                                             )
        return (logged_user, other_contact_user, classic_contact, phone_call)

    def test_create_participants(self):
        logged_user, other_contact_user, classic_contact, phone_call = self._set_activity_context()

        url = '/activities/activity/%s/participant/add' % phone_call.id

        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, follow=True, data={'my_participation': True,
                                                            'my_calendar': Calendar.get_user_default_calendar(logged_user.is_user).pk,
                                                            'participating_users': other_contact_user.is_user_id,
                                                            'participants': classic_contact.pk,
                                                           }
                                   )
        self.assertEqual(200, response.status_code)

        self.assertRelationCount(1, phone_call, REL_OBJ_PART_2_ACTIVITY, logged_user) # logged user, push in his calendar
        self.assertRelationCount(1, phone_call, REL_OBJ_PART_2_ACTIVITY, other_contact_user) # other contact user, push in his calendar too
        self.assertRelationCount(1, phone_call, REL_OBJ_PART_2_ACTIVITY, classic_contact) # classic contact, has no calendar
        self.assertEqual(2, phone_call.calendars.count())

    def test_delete_participant(self):
        logged_user, other_contact_user, classic_contact, phone_call = self._set_activity_context()

        qs = Relation.objects.filter(type=REL_OBJ_PART_2_ACTIVITY, object_entity=phone_call)

        for participant_rel in qs:
            response = self.client.post('/activities/activity/participant/delete', data={'id': participant_rel.pk})
            self.assertRedirects(response, activity.get_absolute_url())

        self.assertEqual(0, qs.count())
        self.assertEqual(0, phone_call.calendars.count())
