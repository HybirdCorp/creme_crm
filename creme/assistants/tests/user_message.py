# -*- coding: utf-8 -*-

try:
    from datetime import datetime

    from django.contrib.auth.models import User

    from persons.models import Contact

    from activities.models import Meeting, Calendar
    from activities.constants import REL_SUB_PART_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT

    from assistants.models import UserMessage, UserMessagePriority
    from assistants.constants import PRIO_NOT_IMP_PK
    from assistants.tests.base import AssistantsTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('UserMessageTestCase',)


class UserMessageTestCase(AssistantsTestCase):
    def _create_usermessage(self, title, body, priority, users, entity):
        url = '/assistants/message/add/%s/' % entity.id if entity else \
              '/assistants/message/add/'

        if priority is None:
            priority = UserMessagePriority.objects.create(title='Important')

        response = self.client.post(url, data={'user':     self.user.pk,
                                               'title':    title,
                                               'body':     body,
                                               'priority': priority.id,
                                               'users':    [u.id for u in users],
                                              }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

    def test_create01(self):
        self.assertFalse(UserMessage.objects.exists())

        response = self.client.get('/assistants/message/add/%s/' % self.entity.id)
        self.assertEqual(200, response.status_code)

        title    = 'TITLE'
        body     = 'BODY'
        priority = UserMessagePriority.objects.create(title='Important')
        user01   = User.objects.create_user('User01', 'user01@foobar.com', 'password')
        self._create_usermessage(title, body, priority, [user01], self.entity)

        messages = UserMessage.objects.all()
        self.assertEqual(1, len(messages))

        message = messages[0]
        self.assertEqual(title,    message.title)
        self.assertEqual(body,     message.body)
        self.assertEqual(priority, message.priority)

        self.assertFalse(message.email_sent)

        self.assertEqual(self.entity.id,             message.entity_id)
        self.assertEqual(self.entity.entity_type_id, message.entity_content_type_id)

        self.assertEqual(self.user, message.sender)
        self.assertEqual(user01,    message.recipient)

        self.assertLess((datetime.now() - message.creation_date).seconds, 10)

    def test_create02(self):
        priority = UserMessagePriority.objects.create(title='Important')
        user01   = User.objects.create_user('User01', 'user01@foobar.com', 'password')
        user02   = User.objects.create_user('User02', 'user02@foobar.com', 'password')

        self._create_usermessage('TITLE', 'BODY', priority, [user01, user02], self.entity)

        messages = UserMessage.objects.all()
        self.assertEqual(2, len(messages))
        self.assertEqual(set([user01, user02]), set(msg.recipient for msg in messages))

    def test_create03(self): #without related entity
        response = self.client.get('/assistants/message/add/')
        self.assertEqual(200, response.status_code)

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
        users       = [create_user('User%s' % i, 'user%s@foobar.com' % i, 'uselesspassword') for i in xrange(1, 3)]

        team = User.objects.create(username='Team', is_team=True, role=None)
        team.teammates = users

        self._create_usermessage('TITLE', 'BODY', None, [team], self.entity)

        messages = UserMessage.objects.all()
        self.assertEqual(2, len(messages))
        self.assertEqual(set(users), set(msg.recipient for msg in messages))

    def test_create05(self): #teams and isolated usres with non void intersections
        create_user = User.objects.create_user
        users = [create_user('User%s' % i, 'user%s@foobar.com' % i, 'uselesspassword') for i in xrange(1, 5)]

        team01 = User.objects.create(username='Team01', is_team=True, role=None)
        team01.teammates = users[:2]

        team02 = User.objects.create(username='Team02', is_team=True, role=None)
        team02.teammates = users[1:3]

        self._create_usermessage('TITLE', 'BODY', None, [team01, team02, users[0], users[3]], self.entity)

        messages = UserMessage.objects.all()
        self.assertEqual(4, len(messages))
        self.assertEqual(set(users), set(msg.recipient for msg in messages))

    def test_delete01(self): #delete related entity
        priority = UserMessagePriority.objects.create(title='Important')
        user01   = User.objects.create_user('User01', 'user01@foobar.com', 'password')
        self._create_usermessage('TITLE', 'BODY', priority, [user01], self.entity)

        self.assertEqual(1, UserMessage.objects.count())

        self.entity.delete()
        self.assertEqual(0, UserMessage.objects.count())

    def test_delete02(self):
        priority = UserMessagePriority.objects.create(title='Important')
        self._create_usermessage('TITLE', 'BODY', priority, [self.user], None)

        messages = UserMessage.objects.all()
        self.assertEqual(1, len(messages))

        message = messages[0]
        self.assertEqual(self.user, message.recipient)

        response = self.client.post('/assistants/message/delete', data={'id': message.id})
        self.assertEqual(302, response.status_code)
        self.assertEqual(0,   UserMessage.objects.count())

    def test_activity_createview01(self): #test activity form hooking
        self.populate('activities', 'assistants')

        user       = self.user
        other_user = self.other_user
        self.assertEqual(0, UserMessage.objects.count())

        create_contact = Contact.objects.create
        me    = create_contact(user=user, is_user=user,       first_name='Ryoga', last_name='Hibiki')
        ranma = create_contact(user=user, is_user=other_user, first_name='Ranma', last_name='Saotome')
        genma = create_contact(user=user, first_name='Genma', last_name='Saotome')
        akane = create_contact(user=user, first_name='Akane', last_name='Tendo')

        url = '/activities/activity/add/meeting'
        self.assertEqual(200, self.client.get(url).status_code)

        title  = 'Meeting dojo'
        field_format = '[{"ctype": "%s", "entity": "%s"}]'
        my_calendar = Calendar.get_user_default_calendar(user)
        response = self.client.post(url, follow=True,
                                    data={'user':                user.pk,
                                          'title':               title,
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
        self.assertEqual(200, response.status_code)

        meeting = self.get_object_or_fail(Meeting, title=title)

        self.assertRelationCount(1, me,    REL_SUB_PART_2_ACTIVITY,  meeting)
        self.assertRelationCount(1, ranma, REL_SUB_PART_2_ACTIVITY,  meeting)
        self.assertRelationCount(1, genma, REL_SUB_PART_2_ACTIVITY,  meeting)
        self.assertRelationCount(1, akane, REL_SUB_ACTIVITY_SUBJECT, meeting)

        messages = UserMessage.objects.all()
        self.assertEqual(2, len(messages))

        message = messages[0]
        self.assertEqual(user, message.sender)
        self.assertEqual(user, message.recipient)
        self.assertLess((datetime.now() - message.creation_date).seconds, 10)
        self.assertEqual(PRIO_NOT_IMP_PK,  message.priority_id)
        self.assertFalse(message.email_sent)
        self.assertEqual(meeting.id,             message.entity_id)
        self.assertEqual(meeting.entity_type_id, message.entity_content_type_id)

        self.assertIn(unicode(meeting), message.title)

        body = message.body
        self.assertIn(unicode(akane), body)
        self.assertIn(unicode(me), body)
        self.assertIn(unicode(ranma), body)

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
        response = self.client.post('/creme_config/assistants/message_priority/delete', data={'id': priority.pk})
        self.assertEqual(200, response.status_code)
        self.assertFalse(UserMessagePriority.objects.filter(pk=priority.pk).exists())

    def test_delete_priority02(self):
        priority = UserMessagePriority.objects.create(title='Important')
        self._create_usermessage('TITLE', 'BODY', priority, [self.user], None)

        messages = UserMessage.objects.all()
        self.assertEqual(1, len(messages))

        message = messages[0]

        response = self.client.post('/creme_config/assistants/message_priority/delete', data={'id': priority.pk})
        self.assertEqual(404, response.status_code)
        self.assertTrue(UserMessagePriority.objects.filter(pk=priority.pk).exists())

        message = self.get_object_or_fail(UserMessage, pk=message.pk)
        self.assertEqual(priority, message.priority)
