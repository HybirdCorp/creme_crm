# -*- coding: utf-8 -*-

from django.test import TestCase
from django.core.serializers.json import simplejson
from django.contrib.auth.models import User

from creme_core.management.commands.creme_populate import Command as PopulateCommand

from products.models import *


class ProductsTestCase(TestCase):
    def login(self):
        if not self.user:
            user = User.objects.create(username='user01')
            user.set_password(self.password)
            user.is_superuser = True
            user.save()
            self.user = user

        logged = self.client.login(username=self.user.username, password=self.password)
        self.assert_(logged, 'Not logged in')

    def setUp(self):
        PopulateCommand().handle(application=['creme_core', 'products'])
        self.password = 'test'
        self.user = None

    def test_populate(self):
        self.assert_(ServiceCategory.objects.exists())
        self.assert_(Category.objects.exists())
        self.assert_(SubCategory.objects.exists())

    def test_ajaxview01(self):
        self.login()

        response = self.client.post('/products/sub_category/load')
        self.assertEqual(response.status_code, 200)

        #{'result': [{'text': u'Choose a category', 'id': ''}]}
        try:
            content = simplejson.loads(response.content)['result']
            self.assertEqual(1, len(content))

            dic = content[0]
            self.assert_(dic['text'])
            self.failIf(dic['id'])
        except Exception, e:
            self.fail(str(e))

        name1 = 'subcat1'
        name2 = 'subcat2'
        cat = Category.objects.create(name='category', description='description')
        subcat1 = SubCategory.objects.create(name=name1, description='description', category=cat)
        subcat2 = SubCategory.objects.create(name=name2, description='description', category=cat)

        response = self.client.post('/products/sub_category/load', data={'record_id': cat.id})
        self.assertEqual(response.status_code, 200)

        #{'result': [{'text': 'subcat1', 'id': 8}, {'text': 'subcat2', 'id': 9}]}
        try:
            content = simplejson.loads(response.content)['result']
            self.assertEqual(2, len(content))
            dic = content[0]
            self.assertEqual(name1,      dic['text'])
            self.assertEqual(subcat1.id, dic['id'])

            dic = content[1]
            self.assertEqual(name2,      dic['text'])
            self.assertEqual(subcat2.id, dic['id'])
        except Exception, e:
            self.fail(str(e))


    #TODO: test other views..
