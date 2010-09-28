# -*- coding: utf-8 -*-

from django.test import TestCase
from django.db.models import fields
from django.contrib.auth.models import User

from creme_core import models
from creme_core.utils import meta


class MetaTestCase(TestCase):
    def test_get_field_infos(self):
        text = 'TEXT'

        user   = User.objects.create(username='name')
        ptype  = models.CremePropertyType.objects.create(text=text, is_custom=True)
        entity = models.CremeEntity.objects.create(user=user)
        prop   = models.CremeProperty(type=ptype, creme_entity=entity)

        self.assertEqual((fields.CharField,    text), meta.get_field_infos(prop, 'type__text'))
        self.assertEqual((fields.BooleanField, True), meta.get_field_infos(prop, 'type__is_custom'))

        self.assertEqual((None, ''), meta.get_field_infos(prop, 'foobar__is_custom'))
        self.assertEqual((None, ''), meta.get_field_infos(prop, 'type__foobar'))

        self.assertEqual(fields.CharField, meta.get_field_infos(prop, 'creme_entity__entity_type__name')[0])