# -*- coding: utf-8 -*-

try:
    from datetime import datetime

    from django.core.serializers.json import simplejson
    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import CremeEntity, Relation
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact

    from activities.models import Meeting, Calendar
    from activities.constants import REL_SUB_PART_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT

    from assistants.models import *
    from assistants.blocks import todos_block
    from assistants.constants import PRIO_NOT_IMP_PK
except Exception as e:
    print 'Error:', e


class AssistantsAppTestCase(CremeTestCase):
    def test_populate(self):
        self.populate('assistants')
        self.assertEqual(3, UserMessagePriority.objects.count())


class AssistantsTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config')
        self.login()
        self.entity = CremeEntity.objects.create(user=self.user)


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

        try:
            todo = ToDo.objects.get(title=title, description=description)
        except ToDo.DoesNotExist:
            self.fail('Todo not created ?!')

        return todo

    def test_todo_create(self):
        self.assertFalse(ToDo.objects.exists())

        response = self.client.get('/assistants/todo/add/%s/' % self.entity.id)
        self.assertEqual(200, response.status_code)

        todo = self._create_todo('Title', 'Description')
        self.assertEqual(1, ToDo.objects.count())
        self.assertEqual(self.entity.id,             todo.entity_id)
        self.assertEqual(self.entity.entity_type_id, todo.entity_content_type_id)
        self.assertLess((datetime.now() - todo.creation_date).seconds, 10)

    def test_todo_edit(self):
        title       = 'Title'
        description = 'Description'
        todo = self._create_todo(title, description)

        url = '/assistants/todo/edit/%s/' % todo.id
        self.assertEqual(200, self.client.get(url).status_code)

        title       += '_edited'
        description += '_edited'
        response = self.client.post(url, data={
                                                'user':        self.user.pk,
                                                'title':       title,
                                                'description': description,
                                              }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        todo = ToDo.objects.get(pk=todo.id)
        self.assertEqual(title,       todo.title)
        self.assertEqual(description, todo.description)

    def test_todo_delete01(self): #delete related entity
        self._create_todo()
        self.assertEqual(1, ToDo.objects.count())

        self.entity.delete()
        self.assertEqual(0, ToDo.objects.count())

    def test_todo_delete02(self):
        todo = self._create_todo()
        self.assertEqual(1, ToDo.objects.count())

        ct   = ContentType.objects.get_for_model(ToDo)
        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': todo.id})
        self.assertEqual(302, response.status_code)
        self.assertEqual(0,   ToDo.objects.count())

    def test_todo_validate(self): #validate
        todo = self._create_todo()
        self.assertFalse(todo.is_ok)

        response = self.client.post('/assistants/todo/validate/%s/' % todo.id)
        self.assertEqual(302, response.status_code)
        self.assertIs(True, ToDo.objects.get(pk=todo.id).is_ok)

    def test_block_reload01(self): #detailview
        for i in xrange(1, 4):
            self._create_todo('Todo%s' % i, 'Description %s' % i)

        todos = ToDo.get_todos(self.entity)
        self.assertEqual(3, len(todos))
        self.assertEqual(set(t.id for t in ToDo.objects.all()), set(t.id for t in todos))

        self.assertGreaterEqual(todos_block.page_size, 2)

        response = self.client.get('/creme_core/blocks/reload/%s/%s/' % (todos_block.id_, self.entity.id))
        self.assertEqual(200, response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        content = simplejson.loads(response.content)
        self.assertEqual(1, len(content))
        self.assertEqual(2, len(content[0]))
        self.assertEqual(todos_block.id_, content[0][0])

        try:
            page = response.context['page']
        except Exception as e:
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
        self.assertEqual(3, ToDo.objects.count())

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
        except Exception as e:
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
        except Exception as e:
            self.fail(str(e))

        self.assertEqual(2, len(page.object_list))
        self.assertEqual(set(t.id for t in todos), set(o.id for o in page.object_list))

    def _oldify_todo(self, todo, years_delta=1):
        cdate = todo.creation_date
        todo.creation_date = cdate.replace(year=cdate.year - years_delta)
        todo.save()

    def test_function_field01(self):
        funf = CremeEntity.function_fields.get('assistants-get_todos')
        self.assertIsNotNone(funf)
        self.assertEqual(u'<ul></ul>', funf(self.entity).for_html())

    def test_function_field02(self):
        funf = CremeEntity.function_fields.get('assistants-get_todos')
        self._oldify_todo(self._create_todo('Todo01', 'Description01'))
        self._create_todo('Todo02', 'Description02')

        todo3 = self._create_todo('Todo03', 'Description03')
        todo3.is_ok = True
        todo3.save()

        with self.assertNumQueries(1):
            result = funf(self.entity)

        self.assertEqual(u'<ul><li>Todo02</li><li>Todo01</li></ul>', result.for_html())

        # limit to 3 ToDos
        #self._create_todo('Todo03', 'Description03')
        #self._create_todo('Todo04', 'Description04')
        #self.assertEqual(u'<ul><li>Todo04</li><li>Todo03</li><li>Todo02</li></ul>', funf(self.entity))

    def test_function_field03(self): #prefetch with 'populate_entities()'
        self._oldify_todo(self._create_todo('Todo01', 'Description01'))
        self._create_todo('Todo02', 'Description02')

        todo3 = self._create_todo('Todo03', 'Description03')
        todo3.is_ok = True
        todo3.save()

        entity02 = CremeEntity.objects.create(user=self.user)
        self._create_todo('Todo04', 'Description04', entity=entity02)

        funf = CremeEntity.function_fields.get('assistants-get_todos')

        with self.assertNumQueries(1):
            funf.populate_entities([self.entity, entity02])

        with self.assertNumQueries(0):
            result1 = funf(self.entity)
            result2 = funf(entity02)

        self.assertEqual(u'<ul><li>Todo02</li><li>Todo01</li></ul>', result1.for_html())
        self.assertEqual(u'<ul><li>Todo04</li></ul>',                result2.for_html())


class AlertTestCase(AssistantsTestCase):
    def _create_alert(self, title='TITLE', description='DESCRIPTION', trigger_date='2010-9-29', entity=None):
        entity = entity or self.entity
        response = self.client.post('/assistants/alert/add/%s/' % entity.id,
                                    data={
                                            'user':         self.user.pk,
                                            'title':        title,
                                            'description':  description,
                                            'trigger_date': trigger_date,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        try:
            alert = Alert.objects.get(title=title, description=description)
        except Alert.DoesNotExist:
            self.fail('Alert not created ?!')

        return alert

    def test_alert_create01(self):
        self.assertFalse(Alert.objects.exists())

        response = self.client.get('/assistants/alert/add/%s/' % self.entity.id)
        self.assertEqual(200, response.status_code)

        alert = self._create_alert('Title', 'Description', '2010-9-29')
        self.assertEqual(1, Alert.objects.count())

        self.assertIs(False,          alert.is_validated)
        self.assertEqual(self.user,   alert.user)

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
            self.assertEqual(200, response.status_code)
            try:
                form = response.context['form']
            except Exception as e:
                self.fail(str(e))

            self.assertFalse(form.is_valid(), 'Creation should fail with data=%s' % post_data)

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
        title       = 'Title'
        description = 'Description'
        alert = self._create_alert(title, description, '2010-9-29')

        url = '/assistants/alert/edit/%s/' % alert.id
        self.assertEqual(200, self.client.get(url).status_code)

        title       += '_edited'
        description += '_edited'
        response = self.client.post(url, data={
                                                'user':         self.user.pk,
                                                'title':        title,
                                                'description':  description,
                                                'trigger_date': '2011-10-30',
                                                'trigger_time': '15:12:32',
                                              }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        alert = Alert.objects.get(pk=alert.id)
        self.assertEqual(title,       alert.title)
        self.assertEqual(description, alert.description)

        tdate = alert.trigger_date
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
        alert = self._create_alert()
        self.assertEqual(1, Alert.objects.count())

        ct = ContentType.objects.get_for_model(Alert)
        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': alert.id})
        self.assertEqual(0, Alert.objects.count())

    def test_alert_validate(self): #validate
        alert = self._create_alert()
        self.assertFalse(alert.is_validated)

        response = self.client.post('/assistants/alert/validate/%s/' % alert.id)
        self.assertEqual(302, response.status_code)

        self.assertTrue(Alert.objects.get(pk=alert.id).is_validated)

    def test_function_field01(self):
        funf = CremeEntity.function_fields.get('assistants-get_alerts')
        self.assertIsNotNone(funf)
        self.assertEqual(u'<ul></ul>', funf(self.entity).for_html())

    def test_function_field02(self):
        funf = CremeEntity.function_fields.get('assistants-get_alerts')

        self._create_alert('Alert01', 'Description01', trigger_date='2011-10-21')
        self._create_alert('Alert02', 'Description02', trigger_date='2010-10-20')

        alert3 = self._create_alert('Alert03', 'Description03', trigger_date='2010-10-3')
        alert3.is_validated = True
        alert3.save()

        with self.assertNumQueries(1):
            result = funf(self.entity)

        self.assertEqual(u'<ul><li>Alert02</li><li>Alert01</li></ul>', result.for_html())

    def test_function_field03(self): #prefetch with 'populate_entities()'
        self._create_alert('Alert01', 'Description01', trigger_date='2011-10-21')
        self._create_alert('Alert02', 'Description02', trigger_date='2010-10-20')

        entity02 = CremeEntity.objects.create(user=self.user)

        alert3 = self._create_alert('Alert03', 'Description03', trigger_date='2010-10-3', entity=entity02)
        alert3.is_validated = True
        alert3.save()

        self._create_alert('Alert04', 'Description04', trigger_date='2010-10-3', entity=entity02)

        funf = CremeEntity.function_fields.get('assistants-get_alerts')

        with self.assertNumQueries(1):
            funf.populate_entities([self.entity, entity02])

        with self.assertNumQueries(0):
            result1 = funf(self.entity)
            result2 = funf(entity02)

        self.assertEqual(u'<ul><li>Alert02</li><li>Alert01</li></ul>', result1.for_html())
        self.assertEqual(u'<ul><li>Alert04</li></ul>',                 result2.for_html())


class MemoTestCase(AssistantsTestCase):
    def _create_memo(self, content='Content', on_homepage=True, entity=None):
        entity = entity or self.entity
        response = self.client.post('/assistants/memo/add/%s/' % entity.id,
                                    data={
                                            'user':        self.user.pk,
                                            'content':     content,
                                            'on_homepage': on_homepage,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        try:
            memo = Memo.objects.get(content=content)
        except Memo.DoesNotExist:
            self.fail('Memo not created ?!')

        return memo

    def test_memo_create(self):
        self.assertFalse(Memo.objects.exists())

        response = self.client.get('/assistants/memo/add/%s/' % self.entity.id)
        self.assertEqual(200, response.status_code)

        homepage = True
        memo = self._create_memo('Content', homepage)
        self.assertEqual(1, Memo.objects.count())

        self.assertEqual(homepage,  memo.on_homepage)
        self.assertEqual(self.user, memo.user)

        self.assertEqual(self.entity.id,             memo.entity_id)
        self.assertEqual(self.entity.entity_type_id, memo.entity_content_type_id)

        self.assertLess((datetime.now() - memo.creation_date).seconds, 10)

    def test_memo_edit(self):
        content  = 'content'
        homepage = True
        memo = self._create_memo(content, homepage)

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
        self._create_memo()
        self.assertEqual(1, Memo.objects.count())

        self.entity.delete()
        self.assertEqual(0, Memo.objects.count())

    def test_memo_delete02(self):
        memo = self._create_memo()
        ct = ContentType.objects.get_for_model(Memo)
        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': memo.id})
        self.assertEqual(302, response.status_code)
        self.assertEqual(0,   Memo.objects.count())

    def test_function_field01(self):
        funf = CremeEntity.function_fields.get('assistants-get_memos')
        self.assertIsNotNone(funf)
        self.assertEqual(u'<ul></ul>', funf(self.entity).for_html())

    def _oldify_memo(self, memo, years_delta=1):
        cdate = memo.creation_date
        memo.creation_date = cdate.replace(year=cdate.year - years_delta)
        memo.save()

    def test_function_field02(self):
        funf = CremeEntity.function_fields.get('assistants-get_memos')

        self._oldify_memo(self._create_memo('Content01'))
        self._create_memo('Content02')

        with self.assertNumQueries(1):
            result = funf(self.entity)

        self.assertEqual(u'<ul><li>Content02</li><li>Content01</li></ul>', result.for_html())

    def test_function_field03(self): #prefetch with 'populate_entities()'
        self._oldify_memo(self._create_memo('Content01'))
        self._create_memo('Content02')

        entity02 = CremeEntity.objects.create(user=self.user)
        self._oldify_memo(self._create_memo('Content03', entity=entity02))
        self._create_memo('Content04', entity=entity02)

        funf = CremeEntity.function_fields.get('assistants-get_memos')

        with self.assertNumQueries(1):
            funf.populate_entities([self.entity, entity02])

        with self.assertNumQueries(0):
            result1 = funf(self.entity)
            result2 = funf(entity02)

        self.assertEqual(u'<ul><li>Content02</li><li>Content01</li></ul>', result1.for_html())
        self.assertEqual(u'<ul><li>Content04</li><li>Content03</li></ul>', result2.for_html())


class UserMessageTestCase(AssistantsTestCase):
    def _create_usermessage(self, title, body, priority, users, entity):
        url = '/assistants/message/add/%s/' % entity.id if entity else \
              '/assistants/message/add/'

        if priority is None:
            priority = UserMessagePriority.objects.create(title='Important')

        response = self.client.post(url, data={
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
        self.assertFalse(UserMessage.objects.exists())

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

        self.assertFalse(message.email_sent)

        self.assertEqual(self.entity.id,             message.entity_id)
        self.assertEqual(self.entity.entity_type_id, message.entity_content_type_id)

        self.assertEqual(self.user.id, message.sender_id)
        self.assertEqual(user01.id,    message.recipient_id)

        self.assertLess((datetime.now() - message.creation_date).seconds, 10)

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
        self.assertIsNone(message.entity_id)
        self.assertIsNone(message.entity_content_type_id)
        self.assertIsNone(message.creme_entity)

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

    def test_activity_createview01(self): #test activity form hooking
        self.populate('activities', 'assistants')

        user       = self.user
        other_user = self.other_user
        self.assertEqual(0, UserMessage.objects.count())

        me    = Contact.objects.create(user=user, is_user=user,       first_name='Ryoga', last_name='Hibiki')
        ranma = Contact.objects.create(user=user, is_user=other_user, first_name='Ranma', last_name='Saotome')
        genma = Contact.objects.create(user=user, first_name='Genma', last_name='Saotome')
        akane = Contact.objects.create(user=user, first_name='Akane', last_name='Tendo')

        url = '/activities/activity/add/meeting'
        self.assertEqual(200, self.client.get(url).status_code)

        title  = 'Meeting dojo'
        field_format = '[{"ctype": "%s", "entity": "%s"}]'
        my_calendar = Calendar.get_user_default_calendar(user)
        response = self.client.post(url, follow=True,
                                    data={
                                            'user':                user.pk,
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

        try:
            meeting = Meeting.objects.get(title=title)
        except Exception as e:
            self.fail(str(e))

        count_relations = lambda type_id, subject_id: Relation.objects.filter(type=type_id, subject_entity=subject_id, object_entity=meeting.id).count()
        self.assertEqual(1, count_relations(type_id=REL_SUB_PART_2_ACTIVITY,   subject_id=me.id))
        self.assertEqual(1, count_relations(type_id=REL_SUB_PART_2_ACTIVITY,   subject_id=ranma.id))
        self.assertEqual(1, count_relations(type_id=REL_SUB_PART_2_ACTIVITY,   subject_id=genma.id))
        self.assertEqual(1, count_relations(type_id=REL_SUB_ACTIVITY_SUBJECT,  subject_id=akane.id))

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

        self.assert_(unicode(meeting) in message.title)

        body = message.body
        self.assertIn(unicode(akane), body)
        self.assertIn(unicode(me), body)
        self.assertIn(unicode(ranma), body)


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
        self.assertFalse(Action.objects.exists())

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
        self.assertEqual(title,     action.title)
        self.assertEqual(descr,     action.description)
        self.assertEqual(reaction,  action.expected_reaction)
        self.assertEqual(self.user, action.user)

        self.assertEqual(self.entity.entity_type_id, action.entity_content_type_id)
        self.assertEqual(self.entity.id,             action.entity_id)
        self.assertEqual(self.entity.id,             action.creme_entity.id)

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

        url = '/assistants/action/edit/%s/' % action.id
        self.assertEqual(200, self.client.get(url).status_code)

        title    += '_edited'
        descr    += '_edited'
        reaction += '_edited'
        deadline = '2011-11-25'
        response = self.client.post(url, data={
                                                'user':              self.user.pk,
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
        ct = ContentType.objects.get_for_model(Action)
        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': action.id})
        self.assertEqual(302, response.status_code)
        self.assertEqual(0,   Action.objects.all().count())

    def test_action_validate(self):
        self._create_action('2010-12-24', 'title', 'descr', 'reaction')
        action = Action.objects.all()[0]
        self.assertFalse(action.is_ok)
        self.assertIsNone(action.validation_date)

        response = self.client.post('/assistants/action/validate/%s/' % action.id)
        self.assertEqual(302, response.status_code)

        action = Action.objects.get(pk=action.id)
        self.assertTrue(action.is_ok)
        self.assertLess((datetime.now() - action.validation_date).seconds, 10)

    #TODO: improve block reloading tests with several blocks
