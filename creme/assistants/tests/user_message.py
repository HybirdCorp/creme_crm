# -*- coding: utf-8 -*-

try:
    from datetime import datetime
    from functools import partial

    from django.contrib.auth.models import User
    from django.utils.simplejson.encoder import JSONEncoder

    from creme.persons.models import Contact

    from creme.activities.models import Activity, Calendar
    from creme.activities.constants import *

    from ..models import UserMessage, UserMessagePriority
    from ..constants import PRIO_NOT_IMP_PK
    from .base import AssistantsTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('UserMessageTestCase',)


class UserMessageTestCase(AssistantsTestCase):
    DEL_PRIORITY_URL = '/creme_config/assistants/message_priority/delete'

    @classmethod
    def setUpClass(cls):
        AssistantsTestCase.setUpClass()
        cls.populate('activities', 'assistants')

    def _build_add_url(self, entity=None):
        return '/assistants/message/add/%s/' % entity.id if entity else \
               '/assistants/message/add/'

    def _create_usermessage(self, title, body, priority, users, entity):
        if priority is None:
            priority = UserMessagePriority.objects.create(title='Important')

        response = self.client.post(self._build_add_url(entity),
                                    data={'user':     self.user.pk,
                                          'title':    title,
                                          'body':     body,
                                          'priority': priority.id,
                                          'users':    [u.id for u in users],
                                         }
                                   )
        self.assertNoFormError(response)

    def test_create01(self):
        self.assertFalse(UserMessage.objects.exists())

        entity = self.entity
        self.assertGET200(self._build_add_url(entity))

        title    = 'TITLE'
        body     = 'BODY'
        priority = UserMessagePriority.objects.create(title='Important')
        user01   = User.objects.create_user('User01', 'user01@foobar.com', 'password')
        self._create_usermessage(title, body, priority, [user01], entity)

        messages = UserMessage.objects.all()
        self.assertEqual(1, len(messages))

        message = messages[0]
        self.assertEqual(title,    message.title)
        self.assertEqual(body,     message.body)
        self.assertEqual(priority, message.priority)

        self.assertFalse(message.email_sent)

        self.assertEqual(entity.id,             message.entity_id)
        self.assertEqual(entity.entity_type_id, message.entity_content_type_id)

        self.assertEqual(self.user, message.sender)
        self.assertEqual(user01,    message.recipient)

        self.assertLess((datetime.now() - message.creation_date).seconds, 10)

        self.assertEqual(title, unicode(message))

    def test_create02(self):
        priority = UserMessagePriority.objects.create(title='Important')
        user01   = User.objects.create_user('User01', 'user01@foobar.com', 'password')
        user02   = User.objects.create_user('User02', 'user02@foobar.com', 'password')

        self._create_usermessage('TITLE', 'BODY', priority, [user01, user02], self.entity)

        messages = UserMessage.objects.all()
        self.assertEqual(2, len(messages))
        self.assertEqual(set([user01, user02]), set(msg.recipient for msg in messages))

    def test_create03(self):
        "Without related entity"
        self.assertGET200(self._build_add_url())

        priority = UserMessagePriority.objects.create(title='Important')
        user01  = User.objects.create_user('User01', 'user01@foobar.com', 'password')

        self._create_usermessage('TITLE', 'BODY', priority, [user01], None)

        messages = UserMessage.objects.all()
        self.assertEqual(1, len(messages))

        message = messages[0]
        self.assertIsNone(message.entity_id)
        self.assertIsNone(message.entity_content_type_id)
        self.assertIsNone(message.creme_entity)

    def test_create04(self): #one team
        create_user = User.objects.create_user
        users       = [create_user('User%s' % i, 'user%s@foobar.com' % i, 'uselesspassword')
                            for i in xrange(1, 3)
                      ]

        team = User.objects.create(username='Team', is_team=True, role=None)
        team.teammates = users

        self._create_usermessage('TITLE', 'BODY', None, [team], self.entity)

        messages = UserMessage.objects.all()
        self.assertEqual(2, len(messages))
        self.assertEqual(set(users), set(msg.recipient for msg in messages))

    def test_create05(self):
        "Teams and isolated usres with non void intersections"
        create_user = User.objects.create_user
        users = [create_user('User%s' % i, 'user%s@foobar.com' % i, 'uselesspassword')
                    for i in xrange(1, 5)
                ]

        team01 = User.objects.create(username='Team01', is_team=True, role=None)
        team01.teammates = users[:2]

        team02 = User.objects.create(username='Team02', is_team=True, role=None)
        team02.teammates = users[1:3]

        self._create_usermessage('TITLE', 'BODY', None, [team01, team02, users[0], users[3]], self.entity)

        messages = UserMessage.objects.all()
        self.assertEqual(4, len(messages))
        self.assertEqual(set(users), set(msg.recipient for msg in messages))

    def test_delete_related01(self):
        priority = UserMessagePriority.objects.create(title='Important')
        user01   = User.objects.create_user('User01', 'user01@foobar.com', 'password')
        self._create_usermessage('TITLE', 'BODY', priority, [user01], self.entity)

        self.assertEqual(1, UserMessage.objects.count())

        self.entity.delete()
        self.assertFalse(UserMessage.objects.all())

    def test_delete01(self):
        priority = UserMessagePriority.objects.create(title='Important')
        self._create_usermessage('TITLE', 'BODY', priority, [self.user], None)

        messages = UserMessage.objects.all()
        self.assertEqual(1, len(messages))

        message = messages[0]
        self.assertEqual(self.user, message.recipient)

        response = self.assertPOST(302, '/assistants/message/delete', data={'id': message.id})
        self.assertFalse(UserMessage.objects.all())

    def test_activity_createview01(self):
        "Test activity form hooking"
        user       = self.user
        other_user = self.other_user
        self.assertEqual(0, UserMessage.objects.count())

        create_contact = partial(Contact.objects.create, user=user)
        me    = create_contact(is_user=user,       first_name='Ryoga', last_name='Hibiki')
        ranma = create_contact(is_user=other_user, first_name='Ranma', last_name='Saotome')
        genma = create_contact(first_name='Genma', last_name='Saotome')
        akane = create_contact(first_name='Akane', last_name='Tendo')

        url = '/activities/activity/add'
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertIn('informed_users', fields)

        title  = 'Meeting dojo'
        field_format = '[{"ctype": "%s", "entity": "%s"}]'
        my_calendar = Calendar.get_user_default_calendar(user)
        response = self.client.post(url, follow=True,
                                    data={'user':                user.pk,
                                          'title':               title,
                                          'type_selector':       JSONEncoder().encode({'type': ACTIVITYTYPE_MEETING,
                                                                                       'sub_type': ACTIVITYSUBTYPE_MEETING_NETWORK,
                                                                                      }
                                                                                     ),
                                          'start':               '2010-1-10',
                                          'my_participation':    True,
                                          'my_calendar':         my_calendar.pk,
                                          'participating_users': other_user.pk,
                                          'informed_users':      [user.id, other_user.id],
                                          'other_participants':  genma.id,
                                          'subjects':            field_format % (akane.entity_type_id, akane.id),
                                         }
                                   )
        self.assertNoFormError(response)

        meeting = self.get_object_or_fail(Activity, title=title, type=ACTIVITYTYPE_MEETING)

        self.assertRelationCount(1, me,    REL_SUB_PART_2_ACTIVITY,  meeting)
        self.assertRelationCount(1, ranma, REL_SUB_PART_2_ACTIVITY,  meeting)
        self.assertRelationCount(1, genma, REL_SUB_PART_2_ACTIVITY,  meeting)
        self.assertRelationCount(1, akane, REL_SUB_ACTIVITY_SUBJECT, meeting)

        messages = UserMessage.objects.all()
        self.assertEqual(2, len(messages))

        message = messages[0]
        self.assertEqual(user, message.sender)
        #self.assertEqual(user, message.recipient)
        self.assertLess((datetime.now() - message.creation_date).seconds, 10)
        self.assertEqual(PRIO_NOT_IMP_PK,  message.priority_id)
        self.assertFalse(message.email_sent)
        self.assertEqual(meeting.id,             message.entity_id)
        self.assertEqual(meeting.entity_type_id, message.entity_content_type_id)

        self.assertEqual(set([user, other_user]), set(msg.recipient for msg in messages))

        self.assertIn(unicode(meeting), message.title)

        body = message.body
        self.assertIn(unicode(akane), body)
        self.assertIn(unicode(me), body)
        self.assertIn(unicode(ranma), body)

    def test_activity_createview02(self):
        "Pop-up form is not hooked"
        response = self.assertGET200('/activities/activity/add_popup')

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('informed_users', fields)

    def test_merge(self):
        def creator(contact01, contact02):
            priority = UserMessagePriority.objects.create(title='Important')
            user01 = User.objects.create_user('User01', 'user01@foobar.com', 'password')
            self._create_usermessage('Beware', 'This guy wants to fight against you', priority, [user01], contact01)
            self._create_usermessage('Oh',     'This guy wants to meet you',          priority, [user01], contact02)
            self.assertEqual(2, UserMessage.objects.count())

        def assertor(contact01):
            messages = UserMessage.objects.all()
            self.assertEqual(2, len(messages))

            for msg in messages:
                self.assertEqual(contact01, msg.creme_entity)

        self.aux_test_merge(creator, assertor)

    def test_delete_priority01(self):
        priority = UserMessagePriority.objects.create(title='Important')
        self.assertPOST200(self.DEL_PRIORITY_URL, data={'id': priority.pk})
        self.assertFalse(UserMessagePriority.objects.filter(pk=priority.pk).exists())

    def test_delete_priority02(self):
        priority = UserMessagePriority.objects.create(title='Important')
        self._create_usermessage('TITLE', 'BODY', priority, [self.user], None)

        messages = UserMessage.objects.all()
        self.assertEqual(1, len(messages))

        message = messages[0]

        self.assertPOST404(self.DEL_PRIORITY_URL, data={'id': priority.pk})
        self.assertTrue(UserMessagePriority.objects.filter(pk=priority.pk).exists())

        message = self.get_object_or_fail(UserMessage, pk=message.pk)
        self.assertEqual(priority, message.priority)
