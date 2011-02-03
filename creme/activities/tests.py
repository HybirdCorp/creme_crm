# -*- coding: utf-8 -*-

from datetime import datetime

from django.test import TestCase
from django.forms.util import ValidationError
from django.contrib.auth.models import User

from creme_core.models import RelationType, Relation
from creme_core.management.commands.creme_populate import Command as PopulateCommand

from persons.models import Contact

from activities.models import *
from activities.constants import *
from activities.forms.activity import _check_activity_collisions


class ActivitiesTestCase(TestCase):
    def login(self):
        if not self.user:
            user = User.objects.create(username='Kay')
            user.set_password(self.password)
            user.is_superuser = True
            user.save()
            self.user = user

        logged = self.client.login(username=self.user.username, password=self.password)
        self.assert_(logged, 'Not logged in')

    def setUp(self):
        PopulateCommand().handle(application=['creme_core', 'activities']) #'persons'
        self.password = 'test'
        self.user = None

    def test_populate(self):
        rtypes_pks = [REL_SUB_LINKED_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT, REL_SUB_PART_2_ACTIVITY]
        rtypes = RelationType.objects.filter(pk__in=rtypes_pks)
        self.assertEqual(len(rtypes_pks), len(rtypes))

        acttypes_pks = [ACTIVITYTYPE_TASK, ACTIVITYTYPE_MEETING, ACTIVITYTYPE_PHONECALL,
                        ACTIVITYTYPE_GATHERING, ACTIVITYTYPE_SHOW, ACTIVITYTYPE_DEMO, ACTIVITYTYPE_INDISPO]
        acttypes = ActivityType.objects.filter(pk__in=acttypes_pks)
        self.assertEqual(len(acttypes_pks), len(acttypes))

    def assertNoFormError(self, response): #TODO: move in a CremeTestCase ??? (copied from creme_config)
        try:
            errors = response.context['form'].errors
        except Exception, e:
            pass
        else:
            self.fail(errors)

    def test_activity_createview01(self):
        self.login()

        user = self.user
        me = Contact.objects.create(user=user, is_user=user, first_name='Ryoga', last_name='Hibiki')

        response = self.client.get('/activities/activity/add-without-relation/task')
        self.assertEqual(response.status_code, 200)

        title  = 'my_task'
        status = Status.objects.all()[0]
        my_calendar = Calendar.get_user_default_calendar(self.user)

        response = self.client.post('/activities/activity/add-without-relation/task',
                                    follow=True,
                                    data={
                                            'user':             user.pk,
                                            'title':            title,
                                            'status':           status.pk,
                                            'start':            '2010-1-10',
                                            'my_participation': True,
                                            'my_calendar':      my_calendar.pk,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            act  = Activity.objects.get(type=ACTIVITYTYPE_TASK, title=title)
            task = Task.objects.get(title=title)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(act.id, task.id)
        self.assertEqual(status.id, task.status_id)

        start = task.start
        self.assertEqual(2010, start.year)
        self.assertEqual(1,   start.month)
        self.assertEqual(10,    start.day)

        self.assertEqual(2, Relation.objects.count())

        relations = Relation.objects.filter(type=REL_SUB_PART_2_ACTIVITY)
        self.assertEqual(1, len(relations))

        relation = relations[0]
        self.assertEqual(me.id,   relation.subject_entity_id)
        self.assertEqual(task.id, relation.object_entity_id)

    def test_activity_createview02(self):
        self.login()

        user = self.user
        other_user = User.objects.create_user('akane', 'akane@tendo.jp')

        contact01 = Contact.objects.create(user=user, first_name='Ryoga', last_name='Hibiki')
        contact02 = Contact.objects.create(user=user, first_name='Akane', last_name='Tendo', is_user=other_user)

        args = '&'.join(['ct_entity_for_relation=%s' % contact01.entity_type_id,
                         'id_entity_for_relation=%s' % contact01.id,
                         'entity_relation_type=%s' % REL_SUB_PART_2_ACTIVITY
                        ])
        uri = '/activities/activity/add-with-relation/meeting?' + args

        response = self.client.get(uri)
        self.assertEqual(response.status_code, 200)

        title  = 'my_meeting'
        response = self.client.post(uri, follow=True,
                                    data={
                                            'user':                user.pk,
                                            'title':               title,
                                            'start':               '2010-1-10',
                                            'start_time':          '17:30:00',
                                            'end_time':            '18:30:00',
                                            'participating_users': other_user.pk,
                                         }
                                    )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assert_(response.redirect_chain)

        try:
            meeting = Meeting.objects.get(title=title)
        except Exception, e:
            self.fail(str(e))

        start = meeting.start
        self.assertEqual(2010,  start.year)
        self.assertEqual(1,     start.month)
        self.assertEqual(10,    start.day)
        self.assertEqual(17,    start.hour)
        self.assertEqual(30,    start.minute)

        self.assertEqual(2, Relation.objects.count())

        relations = Relation.objects.filter(type=REL_SUB_PART_2_ACTIVITY)
        self.assertEqual(1, len(relations))

        relation = relations[0]
        self.assertEqual(contact02.id, relation.subject_entity_id)
        self.assertEqual(meeting.id,   relation.object_entity_id)

    def test_activity_createview03(self):
        self.login()

        response = self.client.get('/activities/activity/add-without-relation/meeting')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/activities/activity/add-without-relation/phonecall')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/activities/activity/add-without-relation/foobar')
        self.assertEqual(response.status_code, 404)

        c = Contact.objects.create(user=self.user, first_name='first_name', last_name='last_name')
        args = '&'.join(['ct_entity_for_relation=%s' % c.entity_type_id,
                         'id_entity_for_relation=%s' % c.id,
                         'entity_relation_type=%s' % REL_SUB_LINKED_2_ACTIVITY
                        ])

        response = self.client.get('/activities/activity/add-with-relation/meeting?' + args)
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/activities/activity/add-with-relation/phonecall?' + args)
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/activities/activity/add-with-relation/foobar?' + args)
        self.assertEqual(response.status_code, 404)

    def test_collision01(self):
        self.login()

        try:
            act01 = PhoneCall.objects.create(user=self.user, title='call01', call_type=PhoneCallType.objects.all()[0],
                                             start=datetime(year=2010, month=10, day=1, hour=12, minute=0),
                                             end=datetime(year=2010, month=10, day=1, hour=13, minute=0))
            act02 = Meeting.objects.create(user=self.user, title='meet01',
                                           start=datetime(year=2010, month=10, day=1, hour=14, minute=0),
                                           end=datetime(year=2010, month=10, day=1, hour=15, minute=0))

            c1 = Contact.objects.create(user=self.user, first_name='first_name1', last_name='last_name1')
            c2 = Contact.objects.create(user=self.user, first_name='first_name2', last_name='last_name2')

            Relation.create(c1, REL_SUB_PART_2_ACTIVITY, act01, user_id=self.user.id)
            Relation.create(c1, REL_SUB_PART_2_ACTIVITY, act02, user_id=self.user.id)
        except Exception, e:
            self.fail(str(e))

        try:
            #no collision
            #next day
            _check_activity_collisions(activity_start=datetime(year=2010, month=10, day=2, hour=12, minute=0),
                                       activity_end=datetime(year=2010, month=10, day=2, hour=13, minute=0),
                                       participants=[c1, c2])

            #one minute before
            _check_activity_collisions(activity_start=datetime(year=2010, month=10, day=1, hour=11, minute=0),
                                       activity_end=datetime(year=2010, month=10, day=1, hour=11, minute=59),
                                       participants=[c1, c2])

            #one minute after
            _check_activity_collisions(activity_start=datetime(year=2010, month=10, day=1, hour=13, minute=1),
                                       activity_end=datetime(year=2010, month=10, day=1, hour=13, minute=10),
                                       participants=[c1, c2])
        except ValidationError, e:
            self.fail(str(e))

        #collision with act01
        #before
        self.assertRaises(ValidationError, _check_activity_collisions,
                          activity_start=datetime(year=2010, month=10, day=1, hour=11, minute=30),
                          activity_end=datetime(year=2010, month=10, day=1, hour=12, minute=30),
                          participants=[c1, c2])

        #after
        self.assertRaises(ValidationError, _check_activity_collisions,
                          activity_start=datetime(year=2010, month=10, day=1, hour=12, minute=30),
                          activity_end=datetime(year=2010, month=10, day=1, hour=13, minute=30),
                          participants=[c1, c2])

        #shorter
        self.assertRaises(ValidationError, _check_activity_collisions,
                          activity_start=datetime(year=2010, month=10, day=1, hour=12, minute=10),
                          activity_end=datetime(year=2010, month=10, day=1, hour=12, minute=30),
                          participants=[c1, c2])

        #longer
        self.assertRaises(ValidationError, _check_activity_collisions,
                          activity_start=datetime(year=2010, month=10, day=1, hour=11, minute=0),
                          activity_end=datetime(year=2010, month=10, day=1, hour=13, minute=30),
                          participants=[c1, c2])
