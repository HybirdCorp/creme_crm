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

        response = self.client.get('/activities/activity/add-without-relation/task')
        self.assertEqual(response.status_code, 200)

        title  = 'my_task'
        status = TaskStatus.objects.all()[0]
        response = self.client.post('/activities/activity/add-without-relation/task',
                                    follow=True,
                                    data={
                                            'user':   self.user.pk,
                                            'title':  title,
                                            'status': status.pk,
                                            'start':  '2010-1-10',
                                         }
                                   )
        self.assertEqual(response.status_code, 200)
        self.assertNoFormError(response)

        try:
            act  = Activity.objects.get(type=ACTIVITYTYPE_TASK, title=title)
            task = Task.objects.get(title=title)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(act.id, task.id)
        self.assertEqual(status.id, task.status_id)

        start = task.start
        self.assertEqual(2010, start.year)
        self.assertEqual(1,    start.month)
        self.assertEqual(10,   start.day)

    def test_activity_createview02(self):
        self.login()

        c = Contact.objects.create(user=self.user, first_name='first_name', last_name='last_name')

        args = '&'.join(['ct_entity_for_relation=%s' % c.entity_type_id,
                         'id_entity_for_relation=%s' % c.id,
                         'entity_relation_type=%s' % REL_SUB_PART_2_ACTIVITY
                        ])
        uri = '/activities/activity/add-with-relation/meeting?' + args

        response = self.client.get(uri)
        self.assertEqual(response.status_code, 200)

        title  = 'my_meeting'
        response = self.client.post(uri, follow=True,
                                    data={
                                            'user':       self.user.pk,
                                            'title':      title,
                                            'start':      '2010-1-10',
                                            'start_time': '17:30:00',
                                            'end_time':   '18:30:00',
                                         }
                                    )
        self.assertNoFormError(response)
        self.assertEqual(response.status_code, 200)
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
