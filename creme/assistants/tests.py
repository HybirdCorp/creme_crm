# -*- coding: utf-8 -*-

from datetime import datetime

from django.core.serializers.json import simplejson
from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity
from creme_core.management.commands.creme_populate import Command as PopulateCommand

from assistants.models import *
from assistants.blocks import todos_block


class AssistantsAppTestCase(TestCase):
    def test_populate(self):
        PopulateCommand().handle(application=['assistants'])
        self.assertEqual(3, UserMessagePriority.objects.count())


class AssistantsTestCase(TestCase):
    def setUp(self):
        password = 'test'
        user = User(username='name')
        user.set_password(password)
        user.is_superuser = True
        user.save()
        self.user = user

        logged = self.client.login(username=user.username, password=password)
        self.assert_(logged, 'Not logged in')

        self.entity = CremeEntity.objects.create(user=self.user)

    def assertNoFormError(self, response):
        try:
            errors = response.context['form'].errors
        except Exception, e:
            pass
        else:
            if errors:
                self.fail(errors)


class TodoTestCase(AssistantsTestCase):
    def _create_todo(self, title='TITLE', description='DESCRIPTION', entity=None, user=None):
        entity = entity or self.entity
        user   = user or self.user

        response = self.client.post('/assistants/todo/add/%s/' % entity.id,
                                    data={
                                            'user':        user.pk,
                                            'title':       title,
                                            'description': description,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

    def test_todo_create(self):
        self.failIf(ToDo.objects.exists())

        response = self.client.get('/assistants/todo/add/%s/' % self.entity.id)
        self.assertEqual(200, response.status_code)

        title = 'TITLE'
        description = 'DESCRIPTION'

        self._create_todo(title, description)

        todos = ToDo.objects.all()
        self.assertEqual(1, len(todos))

        todo = todos[0]
        self.assertEqual(title,       todo.title)
        self.assertEqual(description, todo.description)

        delta = datetime.now() - todo.creation_date
        self.assert_(delta.seconds < 10)

    def test_todo_edit(self):
        title       = 'TITLE'
        description = 'DESCRIPTION'
        self._create_todo(title, description)
        todo = ToDo.objects.all()[0]

        response = self.client.get('/assistants/todo/edit/%s/' % todo.id)
        self.assertEqual(200, response.status_code)

        title       += '_edited'
        description += '_edited'
        response = self.client.post('/assistants/todo/edit/%s/' % todo.id,
                                    data={
                                            'user':        self.user.pk,
                                            'title':       title,
                                            'description': description,
                                          }
                        )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        edited_todo = ToDo.objects.all()[0]
        self.assertEqual(title,       edited_todo.title)
        self.assertEqual(description, edited_todo.description)

    def test_todo_delete01(self): #delete related entity
        self._create_todo()
        self.assertEqual(1, ToDo.objects.count())

        self.entity.delete()
        self.assertEqual(0, ToDo.objects.count())

    def test_todo_delete02(self):
        self._create_todo()
        self.assertEqual(1, ToDo.objects.count())

        todo     = ToDo.objects.all()[0]
        response = self.client.post('/assistants/todo/delete', data={'id': todo.id})

        self.assertEqual(302, response.status_code)
        self.assertEqual(0,   ToDo.objects.all().count())

    def test_todo_validate(self): #validate
        self._create_todo()
        todo = ToDo.objects.all()[0]
        self.failIf(todo.is_ok)

        response = self.client.post('/assistants/todo/validate/%s/' % todo.id)
        self.assertEqual(302, response.status_code)

        self.assert_(ToDo.objects.all()[0].is_ok)

    def test_block_reload01(self): #detailview
        for i in xrange(1, 4):
            self._create_todo('Todo%s' % i, 'Description %s' % i)

        todos = ToDo.get_todos(self.entity)
        self.assertEqual(3, len(todos))
        self.assertEqual(set(t.id for t in ToDo.objects.all()), set(t.id for t in todos))

        self.assert_(todos_block.page_size >= 2)

        response = self.client.get('/creme_core/blocks/reload/%s/%s/' % (todos_block.id_, self.entity.id))
        self.assertEqual(200, response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        content = simplejson.loads(response.content)
        self.assertEqual(1, len(content))
        self.assertEqual(2, len(content[0]))
        self.assertEqual(todos_block.id_, content[0][0])

        try:
            page = response.context['page']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(3, len(page.object_list))
        self.assertEqual(set(t.id for t in todos), set(o.id for o in page.object_list))

    def _create_several_todos(self):
        self._create_todo('Todo01', 'Description01')

        entity02 = CremeEntity.objects.create(user=self.user)
        self._create_todo('Todo02', 'Description02', entity=entity02)

        user02 = User.objects.create_user('user02', 'user@creme.org', 'password02')
        self._create_todo('Todo03', 'Description03', user=user02)

    def test_block_reload02(self): #home
        self._create_several_todos()
        self.assertEqual(3, len(ToDo.objects.all()))

        todos = ToDo.get_todos_for_home(self.user)
        self.assertEqual(2, len(todos))

        response = self.client.get('/creme_core/blocks/reload/home/%s/' % todos_block.id_)
        self.assertEqual(200, response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        content = simplejson.loads(response.content)
        self.assertEqual(1, len(content))
        self.assertEqual(2, len(content[0]))
        self.assertEqual(todos_block.id_, content[0][0])

        try:
            page = response.context['page']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(2, len(page.object_list))
        self.assertEqual(set(t.id for t in todos), set(o.id for o in page.object_list))

    def test_block_reload03(self): #portal
        self._create_several_todos()

        ct_id = ContentType.objects.get_for_model(CremeEntity).id
        todos = ToDo.get_todos_for_ctypes([ct_id], self.user)
        self.assertEqual(2, len(todos))

        response = self.client.get('/creme_core/blocks/reload/portal/%s/%s/' % (todos_block.id_, str(ct_id)))
        self.assertEqual(200, response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        content = simplejson.loads(response.content)
        self.assertEqual(1, len(content))
        self.assertEqual(2, len(content[0]))
        self.assertEqual(todos_block.id_, content[0][0])

        try:
            page = response.context['page']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(2, len(page.object_list))
        self.assertEqual(set(t.id for t in todos), set(o.id for o in page.object_list))


class AlertTestCase(AssistantsTestCase):
    def _create_alert(self, title='TITLE', description='DESCRIPTION', trigger_date='2010-9-29'):
        response = self.client.post('/assistants/alert/add/%s/' % self.entity.id,
                                    data={
                                            'user':         self.user.pk,
                                            'title':        title,
                                            'description':  description,
                                            'trigger_date': trigger_date,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

    def test_alert_create01(self):
        self.failIf(Alert.objects.exists())

        response = self.client.get('/assistants/alert/add/%s/' % self.entity.id)
        self.assertEqual(200, response.status_code)

        title        = 'TITLE'
        description  = 'DESCRIPTION'
        self._create_alert(title, description, '2010-9-29')

        alerts = Alert.objects.all()
        self.assertEqual(1, len(alerts))

        alert = alerts[0]
        self.assertEqual(title,       alert.title)
        self.assertEqual(description, alert.description)
        self.assertEqual(False,       alert.is_validated)

        self.assertEqual(self.entity.id,             alert.entity_id)
        self.assertEqual(self.entity.entity_type_id, alert.entity_content_type_id)

        tdate = alert.trigger_date
        self.assertEqual(2010, tdate.year)
        self.assertEqual(9,    tdate.month)
        self.assertEqual(29,   tdate.day)
        self.assertEqual(0,    tdate.hour)
        self.assertEqual(0,    tdate.minute)
        self.assertEqual(0,    tdate.second)

    def test_alert_create02(self): #create with errors
        def _fail_creation(post_data):
            response = self.client.post('/assistants/alert/add/%s/' % self.entity.id, data=post_data)
            self.assertEqual(response.status_code, 200)
            try:
                form = response.context['form']
            except Exception, e:
                self.fail(str(e))

            self.failIf(form.is_valid(), 'Creation should fail with data=%s' % post_data)

        _fail_creation({
                'user':         self.user.pk,
                'title':        '',
                'description':  'description',
                'trigger_date': '2010-9-29',
             })
        _fail_creation({
                'user':         self.user.pk,
                'title':        'title',
                'description':  'description',
                'trigger_date': '',
             })

    def test_alert_edit(self):
        title       = 'TITLE'
        description = 'DESCRIPTION'
        self._create_alert(title, description, '2010-9-29')
        alert = Alert.objects.all()[0]

        response = self.client.get('/assistants/alert/edit/%s/' % alert.id)
        self.assertEqual(200, response.status_code)

        title       += '_edited'
        description += '_edited'

        response = self.client.post('/assistants/alert/edit/%s/' % alert.id,
                                    data={
                                            'user':         self.user.pk,
                                            'title':        title,
                                            'description':  description,
                                            'trigger_date': '2011-10-30',
                                            'trigger_time': '15:12:32',
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        edited_alert = Alert.objects.all()[0]
        self.assertEqual(title,       edited_alert.title)
        self.assertEqual(description, edited_alert.description)

        tdate = edited_alert.trigger_date
        self.assertEqual(2011, tdate.year)
        self.assertEqual(10,   tdate.month)
        self.assertEqual(30,   tdate.day)
        self.assertEqual(15,   tdate.hour)
        self.assertEqual(12,   tdate.minute)
        #self.assertEqual(32,   tdate.second) #don't care about seconds

    def test_alert_delete01(self): #delete related entity
        self._create_alert()
        self.assertEqual(1, Alert.objects.count())

        self.entity.delete()
        self.assertEqual(0, Alert.objects.count())

    def test_alert_delete02(self): #delete
        self._create_alert()
        self.assertEqual(1, Alert.objects.count())

        alert    = Alert.objects.all()[0]
        response = self.client.post('/assistants/alert/delete', data={'id': alert.id})
        self.assertEqual(0, Alert.objects.count())

    def test_alert_validate(self): #validate
        self._create_alert()
        alert = Alert.objects.all()[0]
        self.failIf(alert.is_validated)

        response = self.client.post('/assistants/alert/validate/%s/' % alert.id)
        self.assertEqual(302, response.status_code)

        self.assert_(Alert.objects.all()[0].is_validated)


class MemoTestCase(AssistantsTestCase):
    def _create_memo(self, content, on_homepage, entity):
        response = self.client.post('/assistants/memo/add/%s/' % entity.id,
                                    data={
                                            'user':        self.user.pk,
                                            'content':     content,
                                            'on_homepage': on_homepage,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

    def test_memo_create(self):
        self.failIf(Memo.objects.exists())

        response = self.client.get('/assistants/memo/add/%s/' % self.entity.id)
        self.assertEqual(200, response.status_code)

        content  = 'CONTENT'
        homepage = True
        self._create_memo(content, homepage, self.entity)

        memos = Memo.objects.all()
        self.assertEqual(1, len(memos))

        memo = memos[0]
        self.assertEqual(content,      memo.content)
        self.assertEqual(homepage,     memo.on_homepage)
        self.assertEqual(self.user.id, memo.user_id)

        self.assertEqual(self.entity.id,             memo.entity_id)
        self.assertEqual(self.entity.entity_type_id, memo.entity_content_type_id)

        self.assert_((datetime.now() - memo.creation_date).seconds < 10)

    def test_memo_edit(self):
        content  = 'CONTENT'
        homepage = True
        self._create_memo(content, homepage, self.entity)
        memo = Memo.objects.all()[0]

        response = self.client.get('/assistants/memo/edit/%s/' % memo.id)
        self.assertEqual(200, response.status_code)

        content += '_edited'
        homepage = not homepage
        response = self.client.post('/assistants/memo/edit/%s/' % memo.id,
                                    data={
                                            'user':        self.user.pk,
                                            'content':     content,
                                            'on_homepage': homepage,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        memo = Memo.objects.get(pk=memo.id)
        self.assertEqual(content,  memo.content)
        self.assertEqual(homepage, memo.on_homepage)

    def test_memo_delete01(self): #delete related entity
        self._create_memo('CONTENT', True, self.entity)
        self.assertEqual(1, Memo.objects.count())

        self.entity.delete()
        self.assertEqual(0, Memo.objects.count())

    def test_memo_delete02(self):
        self._create_memo('CONTENT', True, self.entity)
        memo = Memo.objects.all()[0]

        response = self.client.post('/assistants/memo/delete', data={'id': memo.id})
        self.assertEqual(302, response.status_code)
        self.assertEqual(0,   Memo.objects.count())


class UserMessageTestCase(AssistantsTestCase):
    def _create_usermessage(self, title, body, priority, users, entity):
        url = '/assistants/message/add/%s/' % entity.id if entity else \
              '/assistants/message/add/'

        if priority is None:
            priority = UserMessagePriority.objects.create(title='Important')

        response = self.client.post(url,
                                    data={
                                            'user':     self.user.pk,
                                            'title':    title,
                                            'body':     body,
                                            'priority': priority.id,
                                            'users':    [u.id for u in users],
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

    def test_usermessage_create01(self):
        self.failIf(UserMessage.objects.exists())

        response = self.client.get('/assistants/message/add/%s/' % self.entity.id)
        self.assertEqual(200, response.status_code)

        title    = 'TITLE'
        body     = 'BODY'
        priority = UserMessagePriority.objects.create(title='Important')
        user01  = User.objects.create_user('User01', 'user01@foobar.com', 'password')

        self._create_usermessage(title, body, priority, [user01], self.entity)

        messages = UserMessage.objects.all()
        self.assertEqual(1, len(messages))

        message = messages[0]
        self.assertEqual(title,        message.title)
        self.assertEqual(body,         message.body)
        self.assertEqual(priority.id,  message.priority_id)

        self.failIf(message.email_sent)

        self.assertEqual(self.entity.id,             message.entity_id)
        self.assertEqual(self.entity.entity_type_id, message.entity_content_type_id)

        self.assertEqual(self.user.id, message.sender_id)
        self.assertEqual(user01.id,    message.recipient_id)

        self.assert_((datetime.now() - message.creation_date).seconds < 10)

    def test_usermessage_create02(self):
        priority = UserMessagePriority.objects.create(title='Important')
        user01   = User.objects.create_user('User01', 'user01@foobar.com', 'password')
        user02   = User.objects.create_user('User02', 'user02@foobar.com', 'password')

        self._create_usermessage('TITLE', 'BODY', priority, [user01, user02], self.entity)

        messages = UserMessage.objects.all()
        self.assertEqual(2, len(messages))
        self.assertEqual(set([user01.id, user02.id]), set(msg.recipient_id for msg in messages))

    def test_usermessage_create03(self): #without related entity
        response = self.client.get('/assistants/message/add/')
        self.assertEqual(200, response.status_code)

        priority = UserMessagePriority.objects.create(title='Important')
        user01  = User.objects.create_user('User01', 'user01@foobar.com', 'password')

        self._create_usermessage('TITLE', 'BODY', priority, [user01], None)

        messages = UserMessage.objects.all()
        self.assertEqual(1, len(messages))

        message = messages[0]
        self.assert_(message.entity_id is None)
        self.assert_(message.entity_content_type_id is None)
        self.assert_(message.creme_entity is None)

    def test_usermessage_create04(self): #one team
        create_user = User.objects.create_user
        users       = [create_user('User%s' % i, 'user%s@foobar.com' % i, 'uselesspassword') for i in xrange(1, 3)]

        team = User.objects.create(username='Team', is_team=True, role=None)
        team.teammates = users

        self._create_usermessage('TITLE', 'BODY', None, [team], self.entity)

        messages = UserMessage.objects.all()
        self.assertEqual(2, len(messages))
        self.assertEqual(set(u.id for u in users), set(msg.recipient_id for msg in messages))

    def test_usermessage_create05(self): #teams and isolated usres with non void intersections
        create_user = User.objects.create_user
        users = [create_user('User%s' % i, 'user%s@foobar.com' % i, 'uselesspassword') for i in xrange(1, 5)]

        team01 = User.objects.create(username='Team01', is_team=True, role=None)
        team01.teammates = users[:2]

        team02 = User.objects.create(username='Team02', is_team=True, role=None)
        team02.teammates = users[1:3]

        self._create_usermessage('TITLE', 'BODY', None, [team01, team02, users[0], users[3]], self.entity)

        messages = UserMessage.objects.all()
        self.assertEqual(4, len(messages))
        self.assertEqual(set(u.id for u in users), set(msg.recipient_id for msg in messages))

    def test_usermessage_delete01(self): #delete related entity
        priority = UserMessagePriority.objects.create(title='Important')
        user01   = User.objects.create_user('User01', 'user01@foobar.com', 'password')
        self._create_usermessage('TITLE', 'BODY', priority, [user01], self.entity)

        self.assertEqual(1, UserMessage.objects.count())

        self.entity.delete()
        self.assertEqual(0, UserMessage.objects.count())

    def test_usermessage_delete02(self):
        priority = UserMessagePriority.objects.create(title='Important')
        self._create_usermessage('TITLE', 'BODY', priority, [self.user], None)

        messages = UserMessage.objects.all()
        self.assertEqual(1, len(messages))

        message = messages[0]
        self.assertEqual(self.user.id, message.recipient_id)

        response = self.client.post('/assistants/message/delete', data={'id': message.id})

        self.assertEqual(302, response.status_code)
        self.assertEqual(0,   UserMessage.objects.count())


class ActionTestCase(AssistantsTestCase):
    def _create_action(self, deadline, title='TITLE', descr='DESCRIPTION', reaction='REACTION', entity=None, user=None):
        entity = entity or self.entity
        user   = user or self.user

        response = self.client.post('/assistants/action/add/%s/' % entity.id,
                                    data={
                                            'user':              user.pk,
                                            'title':             title,
                                            'description':       descr,
                                            'expected_reaction': reaction,
                                            'deadline':          deadline
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

    def test_action_create(self):
        self.failIf(Action.objects.exists())

        response = self.client.get('/assistants/action/add/%s/' % self.entity.id)
        self.assertEqual(200, response.status_code)

        title    = 'TITLE'
        descr    = 'DESCRIPTION'
        reaction = 'REACTION'
        deadline = '2010-12-24'
        self._create_action(deadline, title, descr, reaction)

        actions = Action.objects.all()
        self.assertEqual(1, len(actions))

        action = actions[0]
        self.assertEqual(title,        action.title)
        self.assertEqual(descr,        action.description)
        self.assertEqual(reaction,     action.expected_reaction)
        self.assertEqual(self.user.id, action.for_user_id)

        self.assertEqual(self.entity.entity_type_id, action.entity_content_type_id)
        self.assertEqual(self.entity.id,             action.entity_id)

        self.assert_((datetime.now() - action.creation_date).seconds < 10)

        deadline = action.deadline
        self.assertEqual(2010, deadline.year)
        self.assertEqual(12,   deadline.month)
        self.assertEqual(24,   deadline.day)
        self.assertEqual(0,    deadline.hour)
        self.assertEqual(0,    deadline.minute)
        self.assertEqual(0,    deadline.second)

    def test_action_edit(self):
        title    = 'TITLE'
        descr    = 'DESCRIPTION'
        reaction = 'REACTION'
        self._create_action('2010-12-24', title, descr, reaction)
        action = Action.objects.all()[0]

        response = self.client.get('/assistants/action/edit/%s/' % action.id)
        self.assertEqual(200, response.status_code)

        title    += '_edited'
        descr    += '_edited'
        reaction += '_edited'
        deadline = '2011-11-25'
        self.client.post('/assistants/action/edit/%s/' % action.id,
                         data={
                                'user':        self.user.pk,
                                'title':             title,
                                'description':       descr,
                                'expected_reaction': reaction,
                                'deadline':          deadline,
                                'deadline_time':     '17:37:00',
                               }
                        )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        action = Action.objects.get(pk=action.id)
        self.assertEqual(title,    action.title)
        self.assertEqual(descr,    action.description)
        self.assertEqual(reaction, action.expected_reaction)

        deadline = action.deadline
        self.assertEqual(2011, deadline.year)
        self.assertEqual(11,   deadline.month)
        self.assertEqual(25,   deadline.day)
        self.assertEqual(17,   deadline.hour)
        self.assertEqual(37,   deadline.minute)

    def test_action_delete01(self): #delete related entity
        self._create_action('2010-12-24', 'title', 'descr', 'reaction')
        self.assertEqual(1, Action.objects.count())

        self.entity.delete()
        self.assertEqual(0, Action.objects.count())

    def test_action_delete02(self):
        self._create_action('2010-12-24', 'title', 'descr', 'reaction')

        action= Action.objects.all()[0]
        response = self.client.post('/assistants/action/delete', data={'id': action.id})
        self.assertEqual(302, response.status_code)
        self.assertEqual(0,   Action.objects.all().count())

    def test_action_validate(self):
        self._create_action('2010-12-24', 'title', 'descr', 'reaction')
        action = Action.objects.all()[0]
        self.failIf(action.is_ok)
        self.assertEqual(None, action.validation_date)

        response = self.client.post('/assistants/action/validate/%s/' % action.id)
        self.assertEqual(302, response.status_code)

        action = Action.objects.get(pk=action.id)
        self.assert_(action.is_ok)
        self.assert_((datetime.now() - action.validation_date).seconds < 10)

    #TODO: test usermessage + hook in activity form
    #TODO: improve block reloading tests with several blocks
