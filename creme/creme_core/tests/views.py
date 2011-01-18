# -*- coding: utf-8 -*-

from django.test import TestCase
from django.core.serializers.json import simplejson
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import *


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
        self.password = 'test'
        self.user = None

        self.login()

    def test_clean(self):
        try:
            response = self.client.get('/creme_core/clean/', follow=True)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(200, response.status_code)
        self.assertEqual(2,   len(response.redirect_chain))

        last = response.redirect_chain[-1]
        self.assert_(last[0].endswith('/creme_login/'))
        self.assertEqual(302, last[1])

    def test_get_fields(self):
        ct_id = ContentType.objects.get_for_model(CremeEntity).id
        response = self.client.post('/creme_core/get_fields', data={'ct_id': ct_id})
        self.assertEqual(200,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        content = simplejson.loads(response.content)
        self.assertEqual(6, len(content))
        self.assertEqual(content[0], ["created",          "Creme entity - " + _('Creation date')])
        self.assertEqual(content[1], ["modified",         "Creme entity - " + _("Last modification")])
        self.assertEqual(content[2], ["user__username",   _("User") + " - " + _("Username")])
        self.assertEqual(content[3], ["user__first_name", _("User") + " - " + _("First name")])
        self.assertEqual(content[4], ["user__last_name", _("User") + " - " + _("Last name")])
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
        self.assertEqual(content, [['get_pretty_properties', _('Properties')]])

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

    def test_get_creme_entity_as_json01(self):
        try:
            entity = CremeEntity.objects.create(user=self.user)
        except Exception, e:
            self.fail(str(e))

        response = self.client.post('/creme_core/entity/json', data={'pk': entity.id})
        self.assertEqual(200,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        json_data = simplejson.loads(response.content)
        #[{'pk': 1,
        #  'model': 'creme_core.cremeentity',
        #  'fields': {'is_actived': False,
        #             'is_deleted': False,
        #             'created': '2010-11-09 14:34:04',
        #             'header_filter_search_field': '',
        #             'entity_type': 100,
        #             'modified': '2010-11-09 14:34:04',
        #             'user': 1
        #            }
        #}]
        try:
            dic = json_data[0]
            pk     = dic['pk']
            model  = dic['model']
            fields = dic['fields']
            user = fields['user']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(entity.id, pk)
        self.assertEqual('creme_core.cremeentity', model)
        self.assertEqual(self.user.id, user)

    def test_get_creme_entity_as_json02(self):
        try:
            entity = CremeEntity.objects.create(user=self.user)
        except Exception, e:
            self.fail(str(e))

        response = self.client.post('/creme_core/entity/json', data={'pk': entity.id, 'fields': ['user', 'entity_type']})
        self.assertEqual(200, response.status_code)

        json_data = simplejson.loads(response.content)
        #[{'pk': 1,
        #  'model': 'creme_core.cremeentity',
        #  'fields': {'user': 1, 'entity_type': 100}}
        #]
        try:
            fields = json_data[0]['fields']
            user = fields['user']
            entity_type = fields['entity_type']
        except Exception, e:
            self.fail(str(e))

            self.assertEqual(self.user.id, user)
            self.assertEqual(ContentType.objects.get_for_model(CremeEntity).id, entity_type)

    def test_get_creme_entity_repr(self):
        try:
            entity = CremeEntity.objects.create(user=self.user)
        except Exception, e:
            self.fail(str(e))

        response = self.client.get('/creme_core/entity/get_repr/%s' % entity.id)
        self.assertEqual(200,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual('Creme entity: %s' % entity.id, response.content)
