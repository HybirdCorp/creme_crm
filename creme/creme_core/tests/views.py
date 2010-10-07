# -*- coding: utf-8 -*-

#from datetime import datetime

from django.test import TestCase
from django.core.serializers.json import simplejson
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import *
#from creme_core.management.commands.creme_populate import Command as PopulateCommand
#from creme_core.constants import REL_SUB_RELATED_TO


class ViewsTestCase(TestCase):
    def login(self):
        if not self.user:
            user = User.objects.create(username='Kirika')
            user.set_password(self.password)
            user.is_superuser = True
            user.save()
            self.user = user

        logged = self.client.login(username=self.user.username, password=self.password)
        self.assert_(logged, 'Not logged in')

    def setUp(self):
        #PopulateCommand().handle(application=['creme_core', 'reports'])
        self.password = 'test'
        self.user = None

        self.login()

    def test_clean(self):
        try:
            response = self.client.get('/creme_core/clean/', follow=True)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(200, response.status_code)
        #[('http://testserver/creme_logout/', 302), ('http://testserver/creme_login/', 302)]
        self.assert_(2, len(response.redirect_chain))
        last = response.redirect_chain[-1]
        self.assert_(last[0].endswith('/creme_login/'))
        self.assertEqual(302, last[1])

    def test_get_fields(self):
        ct_id = ContentType.objects.get_for_model(CremeEntity).id
        response = self.client.post('/creme_core/get_fields', data={'ct_id': ct_id})
        self.assertEqual(200,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        content = simplejson.loads(response.content)
        self.assertEqual(13, len(content))
        self.assertEqual(content[0], ["created", "Creme entity - Creation date"])
        self.assertEqual(content[1], ["modified", "Creme entity - Last modification"])
        self.assertEqual(content[2], ["user__id", "User - Id"])
        self.assertEqual(content[3], ["user__username", "User - Username"])
        self.assertEqual(content[4], ["user__first_name", "User - First name"])
        #etc...

        response = self.client.post('/creme_core/get_fields', data={'ct_id': 0})
        self.assertEqual(404,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        response = self.client.post('/creme_core/get_fields', data={'ct_id': 'notint'})
        self.assertEqual(400,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        response = self.client.post('/creme_core/get_fields', data={'ct_id': ct_id, 'deep': 'notint'})
        self.assertEqual(400,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

    def test_get_function_fields(self):
        ct_id = ContentType.objects.get_for_model(CremeEntity).id
        response = self.client.post('/creme_core/get_function_fields', data={'ct_id': ct_id})
        self.assertEqual(200,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        content = simplejson.loads(response.content)
        self.assertEqual(content, [['get_pretty_properties', 'Properties']])

        response = self.client.post('/creme_core/get_function_fields', data={'ct_id': 0})
        self.assertEqual(404,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        response = self.client.post('/creme_core/get_function_fields', data={'ct_id': 'notint'})
        self.assertEqual(400,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

    def test_get_custom_fields(self):
        ct = ContentType.objects.get_for_model(CremeEntity)
        response = self.client.post('/creme_core/get_custom_fields', data={'ct_id': ct.id})
        self.assertEqual(200,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual([], simplejson.loads(response.content))

        CustomField.objects.create(name='cf01', content_type=ct, field_type=CustomField.INT)
        CustomField.objects.create(name='cf02', content_type=ct, field_type=CustomField.FLOAT)

        response = self.client.post('/creme_core/get_custom_fields', data={'ct_id': ct.id})
        self.assertEqual([['cf01', 'cf01'], ['cf02', 'cf02']], simplejson.loads(response.content))

        response = self.client.post('/creme_core/get_custom_fields', data={'ct_id': 0})
        self.assertEqual(404,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        response = self.client.post('/creme_core/get_custom_fields', data={'ct_id': 'notint'})
        self.assertEqual(400,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])
