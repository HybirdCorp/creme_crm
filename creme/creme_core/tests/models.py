# -*- coding: utf-8 -*-

from django.test import TestCase
from django.contrib.auth.models import User

from creme_core.models import *


class ModelsTestCase(TestCase):
    def test_property01(self):
        try:
            user   = User.objects.create(username='name')
            ptype  = CremePropertyType.objects.create(text='TEXT')
            entity = CremeEntity.objects.create(user=user)
            prop   = CremeProperty(type=ptype, creme_entity=entity)
        except Exception, e:
            self.fail(str(e))