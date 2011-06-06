# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import *
from creme_core.tests.base import CremeTestCase

from persons.models import Contact, Organisation


__all__ = ('RelationsTestCase',)


class RelationsTestCase(CremeTestCase):
    def setUp(self):
        self.user = User.objects.create(username='name')

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
        self.assertEqual(rtype1.predicate,         subject_pred)
        self.assertEqual(rtype2.predicate,         object_pred)

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

    def test_relation02(self): #BEWARE: bad usage of Relations (see the next test for good usage)
        rtype1, rtype2 = RelationType.create(('test-subject_foobar', 'is loving'),
                                             ('test-object_foobar',  'is loved by'))

        create_entity = CremeEntity.objects.create
        relation = Relation.objects.create(user=self.user, type=rtype1,
                                           subject_entity=create_entity(user=self.user),
                                           object_entity=create_entity(user=self.user))

        #This will not update symmetric relation !!
        relation.subject_entity = create_entity(user=self.user)
        relation.object_entity  = create_entity(user=self.user)

        self.assertNotEqual(relation.subject_entity_id, relation.symmetric_relation.object_entity_id)
        self.assertNotEqual(relation.object_entity_id,  relation.symmetric_relation.subject_entity_id)

    def test_relation03(self):
        rtype1, rtype2 = RelationType.create(('test-subject_foobar', 'is loving'),
                                             ('test-object_foobar',  'is loved by'))

        create_entity = CremeEntity.objects.create
        relation = Relation.objects.create(user=self.user, type=rtype1,
                                           subject_entity=create_entity(user=self.user),
                                           object_entity=create_entity(user=self.user)
                                          )

        entity3 = create_entity(user=self.user)
        entity4 = create_entity(user=self.user)
        relation.update_links(subject_entity=entity3, object_entity=entity4, save=True)

        relation = Relation.objects.get(pk=relation.id) #refresh
        self.assertEqual(entity3.id, relation.subject_entity.id)
        self.assertEqual(entity4.id, relation.object_entity.id)

        sym = relation.symmetric_relation
        self.assertEqual(entity4.id, sym.subject_entity.id)
        self.assertEqual(entity3.id, sym.object_entity.id)

    def test_get_compatible_ones01(self):
        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'manages',       [Contact]),
                                               ('test-object_foobar',  'is managed by', [Organisation])
                                      )

        internal_rtype, internal_sym_rtype = RelationType.create(('test-subject_foobar_2', 'manages internal',       [Contact]),
                                                                 ('test-object_foobar_2',  'is managed by internal', [Organisation]),
                                                                 is_internal=True,
                                      )

        contact_ct_id = ContentType.objects.get_for_model(Contact).id

        compatibles_ids = RelationType.get_compatible_ones(contact_ct_id).values_list('id', flat=True)
        self.assertEqual(set([rtype.id]), set(compatibles_ids))

        compatibles_ids_w_internals = RelationType.get_compatible_ones(contact_ct_id, include_internals=True).values_list('id', flat=True)
        self.assertEqual(set([rtype.id, internal_rtype.id]), set(compatibles_ids_w_internals))

    def test_get_compatible_ones02(self):
        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'manages',       [Contact]),
                                               ('test-object_foobar',  'is managed by', [Organisation]),
                                               is_internal=True,
                                      )

        internal_rtype, internal_sym_rtype = RelationType.create(('test-subject_foobar_2', 'manages internal',       [Contact]),
                                                                 ('test-object_foobar_2',  'is managed by internal', [Organisation]),
                                                                 is_internal=True,
                                      )

        contact_ct_id = ContentType.objects.get_for_model(Contact).id

        compatibles_ids = RelationType.get_compatible_ones(contact_ct_id).values_list('id', flat=True)
        self.assertEqual(0,  len(compatibles_ids))
        self.assertEqual(set(), set(compatibles_ids))

        compatibles_ids = RelationType.get_compatible_ones(contact_ct_id, include_internals=True).values_list('id', flat=True)
        self.assertEqual(2,  len(compatibles_ids))
        self.assertEqual(set([rtype.id, internal_rtype.id]), set(compatibles_ids))

    def test_get_compatible_ones03(self):
        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'manages'),
                                               ('test-object_foobar',  'is managed by'))

        internal_rtype, internal_sym_rtype = RelationType.create(('test-subject_foobar_2', 'manages internal'),
                                                                 ('test-object_foobar_2',  'is managed by internal'),
                                                                 is_internal=True)

        contact_ct_id = ContentType.objects.get_for_model(Contact).id

        compatibles_ids = RelationType.get_compatible_ones(contact_ct_id).values_list('id', flat=True)
        self.assertEqual(set([rtype.id, sym_rtype.id]), set(compatibles_ids))

        compatibles_ids = RelationType.get_compatible_ones(contact_ct_id, include_internals=True).values_list('id', flat=True)
        self.assertEqual(set([rtype.id, sym_rtype.id, internal_rtype.id, internal_sym_rtype.id]), set(compatibles_ids))
