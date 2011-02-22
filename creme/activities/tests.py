# -*- coding: utf-8 -*-

from datetime import datetime

from django.forms.util import ValidationError
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, Relation, SetCredentials
from creme_core.constants import REL_SUB_RELATED_TO
from creme_core.tests.base import CremeTestCase

from persons.models import Contact, Organisation

from activities.models import *
from activities.constants import *
from activities.forms.activity import _check_activity_collisions


class ActivitiesTestCase(CremeTestCase):
    def login(self, is_superuser=True):
        super(ActivitiesTestCase, self).login(is_superuser, allowed_apps=['activities', 'persons']) #'creme_core'

    def _aux_build_setcreds(self):
        #role = self.user.role
        role = self.role
        SetCredentials.objects.create(role=role,
                                      value=SetCredentials.CRED_LINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )
        SetCredentials.objects.create(role=role,
                                      value=SetCredentials.CRED_VIEW   | \
                                            SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | \
                                            SetCredentials.CRED_UNLINK,
                                      set_type=SetCredentials.ESET_ALL
                                     )
    def setUp(self):
        self.populate('creme_core', 'activities') #'persons'

    def test_populate(self):
        rtypes_pks = [REL_SUB_LINKED_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT, REL_SUB_PART_2_ACTIVITY]
        rtypes = RelationType.objects.filter(pk__in=rtypes_pks)
        self.assertEqual(len(rtypes_pks), len(rtypes))

        acttypes_pks = [ACTIVITYTYPE_TASK, ACTIVITYTYPE_MEETING, ACTIVITYTYPE_PHONECALL,
                        ACTIVITYTYPE_GATHERING, ACTIVITYTYPE_SHOW, ACTIVITYTYPE_DEMO, ACTIVITYTYPE_INDISPO]
        acttypes = ActivityType.objects.filter(pk__in=acttypes_pks)
        self.assertEqual(len(acttypes_pks), len(acttypes))

    def test_portal(self):
        self.login()
        self.assertEqual(200, self.client.get('/activities/').status_code)

    def test_activity_createview01(self):
        self.login()

        user = self.user
        me = Contact.objects.create(user=user, is_user=user, first_name='Ryoga', last_name='Hibiki')
        ranma = Contact.objects.create(user=user, first_name='Ranma', last_name='Saotome')
        genma = Contact.objects.create(user=user, first_name='Genma', last_name='Saotome')
        dojo = Organisation.objects.create(user=user, name='Dojo')

        self.assertEqual(200, self.client.get('/activities/activity/add-without-relation/task').status_code)

        title  = 'my_task'
        status = Status.objects.all()[0]
        my_calendar = Calendar.get_user_default_calendar(self.user)
        field_format = '[{"ctype":"%s", "entity":"%s"}]'
        response = self.client.post('/activities/activity/add-without-relation/task',
                                    follow=True,
                                    data={
                                            'user':               user.pk,
                                            'title':              title,
                                            'status':             status.pk,
                                            'start':              '2010-1-10',
                                            'my_participation':   True,
                                            'my_calendar':        my_calendar.pk,
                                            'other_participants': genma.id,
                                            'subjects':           field_format % (ranma.entity_type_id, ranma.id),
                                            'linked_entities':    field_format % (dojo.entity_type_id, dojo.id),
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
        self.assertEqual(1,    start.month)
        self.assertEqual(10,   start.day)

        self.assertEqual(4*2, Relation.objects.count()) # * 2: relations have their symmetric ones

        count_relations = lambda type_id, subject_id: Relation.objects.filter(type=type_id, subject_entity=subject_id, object_entity=task.id).count()
        self.assertEqual(1, count_relations(type_id=REL_SUB_PART_2_ACTIVITY,   subject_id=me.id))
        self.assertEqual(1, count_relations(type_id=REL_SUB_PART_2_ACTIVITY,   subject_id=genma.id))
        self.assertEqual(1, count_relations(type_id=REL_SUB_ACTIVITY_SUBJECT,  subject_id=ranma.id))
        self.assertEqual(1, count_relations(type_id=REL_SUB_LINKED_2_ACTIVITY, subject_id=dojo.id))

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

        self.assertEqual(200, self.client.get('/activities/activity/add-without-relation/meeting').status_code)
        self.assertEqual(200, self.client.get('/activities/activity/add-without-relation/phonecall').status_code)
        self.assertEqual(404, self.client.get('/activities/activity/add-without-relation/foobar').status_code)

        c = Contact.objects.create(user=self.user, first_name='first_name', last_name='last_name')
        args = {
                'ct_entity_for_relation': c.entity_type_id,
                'id_entity_for_relation': c.id,
                'entity_relation_type':   REL_SUB_LINKED_2_ACTIVITY,
               }

        self.assertEqual(200, self.client.get('/activities/activity/add-with-relation/meeting', data=args).status_code)
        self.assertEqual(200, self.client.get('/activities/activity/add-with-relation/phonecall', data=args).status_code)
        self.assertEqual(404, self.client.get('/activities/activity/add-with-relation/foobar', data=args).status_code)

    def test_activity_createview04(self): #creds errors
        self.login(is_superuser=False)
        self._aux_build_setcreds()
        self.role.creatable_ctypes = [ContentType.objects.get_for_model(Activity)]

        user = self.user
        other_user = self.other_user

        Contact.objects.create(user=other_user, is_user=user, first_name='Ryoga', last_name='Hibiki')
        my_calendar = Calendar.get_user_default_calendar(user)

        Contact.objects.create(user=other_user, is_user=other_user, first_name='Ranma', last_name='Saotome')
        genma = Contact.objects.create(user=other_user, first_name='Genma', last_name='Saotome')
        akane = Contact.objects.create(user=other_user, first_name='Akane', last_name='Tendo')
        dojo = Organisation.objects.create(user=other_user, name='Dojo')

        field_format = '[{"ctype":"%s", "entity":"%s"}]'
        response = self.client.post('/activities/activity/add-without-relation/meeting', follow=True,
                                    data={
                                            'user':                user.pk,
                                            'title':               'Fight !!',
                                            'start':               '2011-2-22',
                                            'my_participation':    True,
                                            'my_calendar':         my_calendar.pk,
                                            'participating_users': other_user.pk,
                                            'other_participants':  genma.id,
                                            'subjects':            field_format % (akane.entity_type_id, akane.id),
                                            'linked_entities':     field_format % (dojo.entity_type_id, dojo.id),
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        try:
            errors = response.context['form'].errors
        except Exception, e:
            self.fail(str(e))

        self.assert_(errors)
        self.assertEqual(set(['my_participation', 'participating_users', 'other_participants', 'subjects', 'linked_entities']),
                         set(errors.keys())
                        )

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

            Relation.objects.create(subject_entity=c1, type_id=REL_SUB_PART_2_ACTIVITY, object_entity=act01, user=self.user)
            Relation.objects.create(subject_entity=c1, type_id=REL_SUB_PART_2_ACTIVITY, object_entity=act02, user=self.user)
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

    def _create_meeting(self):
        return Meeting.objects.create(user=self.user, title='meet01',
                                      start=datetime(year=2011, month=2, day=1, hour=14, minute=0),
                                      end=datetime(year=2011,   month=2, day=1, hour=15, minute=0)
                                     )

    def test_listview(self):
        self.login()

        PhoneCall.objects.create(user=self.user, title='call01', call_type=PhoneCallType.objects.all()[0],
                                 start=datetime(year=2010, month=10, day=1, hour=12, minute=0),
                                 end=datetime(year=2010, month=10, day=1, hour=13, minute=0))
        Meeting.objects.create(user=self.user, title='meet01',
                               start=datetime(year=2010, month=10, day=1, hour=14, minute=0),
                               end=datetime(year=2010, month=10, day=1, hour=15, minute=0))

        self.assertEqual(200, self.client.get('/activities/activities').status_code)

    def test_unlink01(self):
        self.login()

        activity = self._create_meeting()
        contact = Contact.objects.create(user=self.user, first_name='Musashi', last_name='Miyamoto')

        create_rel = Relation.objects.create
        r1 = create_rel(subject_entity=contact, type_id=REL_SUB_PART_2_ACTIVITY,   object_entity=activity, user=self.user)
        r2 = create_rel(subject_entity=contact, type_id=REL_SUB_ACTIVITY_SUBJECT,  object_entity=activity, user=self.user)
        r3 = create_rel(subject_entity=contact, type_id=REL_SUB_LINKED_2_ACTIVITY, object_entity=activity, user=self.user)
        r4 = create_rel(subject_entity=contact, type_id=REL_SUB_RELATED_TO,        object_entity=activity, user=self.user)
        self.assertEqual(3, contact.relations.filter(pk__in=[r1.id, r2.id, r3.id]).count())

        post = self.client.post

        self.assertEqual(200, post('/activities/linked_activity/unlink', data={'id': activity.id, 'object_id': contact.id}).status_code)
        self.assertEqual(0,   contact.relations.filter(pk__in=[r1.id, r2.id, r3.id]).count())
        self.assertEqual(1,   contact.relations.filter(pk=r4.id).count())

        #errors
        self.assertEqual(404, post('/activities/linked_activity/unlink', data={'id':        activity.id}).status_code)
        self.assertEqual(404, post('/activities/linked_activity/unlink', data={'object_id': contact.id}).status_code)
        self.assertEqual(404, post('/activities/linked_activity/unlink').status_code)
        self.assertEqual(404, post('/activities/linked_activity/unlink', data={'id': 1024,        'object_id': contact.id}).status_code)
        self.assertEqual(404, post('/activities/linked_activity/unlink', data={'id': activity.id, 'object_id': 1024}).status_code)

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
        relation = Relation.objects.create(subject_entity=contact, type_id=REL_SUB_PART_2_ACTIVITY, object_entity=activity, user=self.user)

        self.assertEqual(403, self.client.post('/activities/linked_activity/unlink', data={'id': activity.id, 'object_id': contact.id}).status_code)
        self.assertEqual(1,   contact.relations.filter(pk=relation.id).count())

    def test_unlink03(self): #can not unlink the contact
        self.login(is_superuser=False)

        SetCredentials.objects.create(role=self.user.role,
                                      value=SetCredentials.CRED_VIEW   | \
                                            SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | \
                                            SetCredentials.CRED_LINK   | \
                                            SetCredentials.CRED_UNLINK,
                                      set_type=SetCredentials.ESET_OWN)
        SetCredentials.objects.create(role=self.user.role,
                                      value=SetCredentials.CRED_VIEW   | \
                                            SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | \
                                            SetCredentials.CRED_LINK,
                                      set_type=SetCredentials.ESET_ALL)

        activity = self._create_meeting()
        contact = Contact.objects.create(user=self.other_user, first_name='Musashi', last_name='Miyamoto')
        relation = Relation.objects.create(subject_entity=contact, type_id=REL_SUB_PART_2_ACTIVITY, object_entity=activity, user=self.user)

        self.assertEqual(403, self.client.post('/activities/linked_activity/unlink', data={'id': activity.id, 'object_id': contact.id}).status_code)
        self.assertEqual(1,   contact.relations.filter(pk=relation.id).count())

    def test_add_participants01(self):
        self.login()

        activity = self._create_meeting()
        contact01 = Contact.objects.create(user=self.user, first_name='Musashi', last_name='Miyamoto')
        contact02 = Contact.objects.create(user=self.user, first_name='Kojiro',  last_name='Sasaki')
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
        self.assert_(activity.can_change(self.user))
        self.failIf(activity.can_link(self.user))
        self.assertEqual(403, self.client.get('/activities/activity/%s/participant/add' % activity.id).status_code)

    def test_add_participants03(self): #credentials error with selected subjects
        self.login(is_superuser=False)
        self._aux_build_setcreds()

        activity = self._create_meeting()
        self.assert_(activity.can_link(self.user))

        contact = Contact.objects.create(user=self.other_user, first_name='Musashi', last_name='Miyamoto')
        self.assert_(contact.can_change(self.user))
        self.failIf(contact.can_link(self.user))

        uri = '/activities/activity/%s/participant/add' % activity.id
        self.assertEqual(200, self.client.get(uri).status_code)

        response = self.client.post(uri, data={'participants': contact.id})
        self.assertEqual(200, response.status_code)

        try:
            errors = response.context['form'].errors
        except Exception, e:
            self.fail(str(e))

        self.assert_(errors)
        self.assertEqual(['participants'], errors.keys())
        self.assertEqual(0, Relation.objects.filter(subject_entity=activity.id, type=REL_OBJ_PART_2_ACTIVITY).count())

    def test_add_subjects01(self):
        self.login()

        activity = self._create_meeting()
        orga = Organisation.objects.create(user=self.user, name='Ghibli')

        uri = '/activities/activity/%s/subject/add' % activity.id
        self.assertEqual(200, self.client.get(uri).status_code)

        response = self.client.post(uri, data={'subjects': '[{"ctype":"%s", "entity":"%s"}]' % (orga.entity_type_id, orga.id)})
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
        self.assert_(activity.can_change(self.user))
        self.failIf(activity.can_link(self.user))
        self.assertEqual(403, self.client.get('/activities/activity/%s/subject/add' % activity.id).status_code)

    def test_add_subjects03(self): #credentials error with selected subjects
        self.login(is_superuser=False)
        self._aux_build_setcreds()

        activity = self._create_meeting()
        self.assert_(activity.can_link(self.user))

        orga = Organisation.objects.create(user=self.other_user, name='Ghibli')
        self.assert_(orga.can_change(self.user))
        self.failIf(orga.can_link(self.user))

        uri = '/activities/activity/%s/subject/add' % activity.id
        self.assertEqual(200, self.client.get(uri).status_code)

        response = self.client.post(uri, data={'subjects': '[{"ctype":"%s", "entity":"%s"}]' % (orga.entity_type_id, orga.id)})
        self.assertEqual(200, response.status_code)

        try:
            errors = response.context['form'].errors
        except Exception, e:
            self.fail(str(e))

        self.assert_(errors)
        self.assertEqual(['subjects'], errors.keys())
        self.assertEqual(0, Relation.objects.filter(subject_entity=activity.id, type=REL_OBJ_ACTIVITY_SUBJECT).count())

#TODO: complete test case
