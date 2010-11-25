# -*- coding: utf-8 -*-

from datetime import datetime

from django.test import TestCase
from django.contrib.auth.models import User

from creme_core.models import CremeEntity

from assistants.models import *


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


class TodoTestCase(AssistantsTestCase):
    def create_todo(self, title='TITLE', description='DESCRIPTION'):
        response = self.client.post('/assistants/todo/add/%s/' % self.entity.id,
                                    data={
                                            'user':        self.user.pk,
                                            'title':       title,
                                            'description': description,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

    def test_todo01(self): #create
        self.failIf(ToDo.objects.all().exists())

        response = self.client.get('/assistants/todo/add/%s/' % self.entity.id)
        self.assertEqual(response.status_code, 200)

        title = 'TITLE'
        description = 'DESCRIPTION'

        self.create_todo(title, description)

        todos = ToDo.objects.all()
        self.assertEqual(1, len(todos))

        todo = todos[0]
        self.assertEqual(title,       todo.title)
        self.assertEqual(description, todo.description)

        delta = datetime.now() - todo.creation_date
        self.assert_(delta.seconds < 10)

    def test_todo02(self): #edit
        title       = 'TITLE'
        description = 'DESCRIPTION'
        self.create_todo(title, description)
        todo = ToDo.objects.all()[0]

        response = self.client.get('/assistants/todo/edit/%s/' % todo.id)

        self.assertEqual(response.status_code, 200)

        title       += '_edited'
        description += '_edited'

        self.client.post('/assistants/todo/edit/%s/' % todo.id,
                         data={
                                'user':        self.user.pk,
                                'title':       title,
                                'description': description,
                               }
                        )
        self.assertEqual(response.status_code, 200)

        edited_todo = ToDo.objects.all()[0]
        self.assertEqual(title,       edited_todo.title)
        self.assertEqual(description, edited_todo.description)

    def test_todo03(self): #delete related entity
        self.create_todo()
        self.assertEqual(1, ToDo.objects.all().count())

        self.entity.delete()
        self.assertEqual(0, ToDo.objects.all().count())

    def test_todo04(self): #delete
        self.create_todo()
        self.assertEqual(1, ToDo.objects.all().count())

        todo     = ToDo.objects.all()[0]
        response = self.client.post('/assistants/todo/delete', data={'id': todo.id})

        self.assertEqual(302, response.status_code)
        self.assertEqual(0,   ToDo.objects.all().count())

    def test_todo05(self): #validate
        self.create_todo()
        todo = ToDo.objects.all()[0]
        self.failIf(todo.is_ok)

        response = self.client.post('/assistants/todo/validate/%s/' % todo.id)
        self.assertEqual(302, response.status_code)

        self.assert_(ToDo.objects.all()[0].is_ok)


class AlertTestCase(AssistantsTestCase):
    def create_alert(self, title='TITLE', description='DESCRIPTION', trigger_date='2010-9-29'):
        response = self.client.post('/assistants/alert/add/%s/' % self.entity.id,
                                    data={
                                            'user':         self.user.pk,
                                            'title':        title,
                                            'description':  description,
                                            'trigger_date': trigger_date,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

    def test_alert01(self): #create
        self.failIf(ToDo.objects.all().exists())

        response = self.client.get('/assistants/alert/add/%s/' % self.entity.id)
        self.assertEqual(response.status_code, 200)

        title        = 'TITLE'
        description  = 'DESCRIPTION'

        self.create_alert(title, description, '2010-9-29')

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

    def test_alert02(self): #create with errors
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

    def test_alert03(self): #edit
        title       = 'TITLE'
        description = 'DESCRIPTION'
        self.create_alert(title, description, '2010-9-29')
        alert = Alert.objects.all()[0]

        response = self.client.get('/assistants/alert/edit/%s/' % alert.id)
        self.assertEqual(response.status_code, 200)

        title       += '_edited'
        description += '_edited'

        self.client.post('/assistants/alert/edit/%s/' % alert.id,
                         data={
                                'user':         self.user.pk,
                                'title':        title,
                                'description':  description,
                                'trigger_date': '2011-10-30',
                                'trigger_time': '15:12:32',
                               }
                        )
        self.assertEqual(response.status_code, 200)

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

    def test_alert04(self): #delete related entity
        self.create_alert()
        self.assertEqual(1, Alert.objects.all().count())

        self.entity.delete()
        self.assertEqual(0, Alert.objects.all().count())

    def test_alert05(self): #delete
        self.create_alert()
        self.assertEqual(1, Alert.objects.all().count())

        alert    = Alert.objects.all()[0]
        response = self.client.post('/assistants/alert/delete', data={'id': alert.id})
        self.assertEqual(0, Alert.objects.all().count())

    def test_alert06(self): #validate
        self.create_alert()
        alert = Alert.objects.all()[0]
        self.failIf(alert.is_validated)

        response = self.client.post('/assistants/alert/validate/%s/' % alert.id)
        self.assertEqual(302, response.status_code)

        self.assert_(Alert.objects.all()[0].is_validated)


#TODO: test for Action, Memo and UserMessage
