# -*- coding: utf-8 -*-

from datetime import datetime

from django.test import TestCase
from django.contrib.auth.models import User

from creme_core.models import *


class ModelsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='name')

    def test_entity01(self):
        try:
            entity = CremeEntity.objects.create(user=self.user)
        except Exception, e:
            self.fail(str(e))

        now = datetime.now()

        self.assert_((now - entity.created).seconds < 10)
        self.assert_((now - entity.modified).seconds < 10)


    def test_property01(self):
        text = 'TEXT'

        try:
            ptype  = CremePropertyType.create(str_pk='test-prop_foobar', text=text)
            entity = CremeEntity.objects.create(user=self.user)
            prop   = CremeProperty.objects.create(type=ptype, creme_entity=entity)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(text, ptype.text)

    def test_relation01(self):
        subject_pred = 'is loving'
        object_pred  = 'is loved by'

        try:
            rtype1, rtype2 = RelationType.create(('test-subject_foobar', subject_pred),
                                                 ('test-object_foobar',  object_pred))
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(rtype1.symmetric_type.id, rtype2.id)
        self.assertEqual(rtype2.symmetric_type.id, rtype1.id)
        self.assertEqual(rtype1.predicate, subject_pred)
        self.assertEqual(rtype2.predicate, object_pred)

        try:
            entity1  = CremeEntity.objects.create(user=self.user)
            entity2  = CremeEntity.objects.create(user=self.user)
            relation = Relation.objects.create(user=self.user, type=rtype1,
                                               subject_entity=entity1, object_entity=entity2)
        except Exception, e:
            self.fail(str(e))

        sym = relation.symmetric_relation
        self.assertEqual(sym.type.id, rtype2.id)
        self.assertEqual(sym.subject_entity.id, entity2.id)
        self.assertEqual(sym.object_entity.id,  entity1.id)
