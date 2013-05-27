# -*- coding: utf-8 -*-

try:
    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.models import *
    from ..base import CremeTestCase

    from creme.persons.models import Contact, Organisation
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('RelationsTestCase',)


class RelationsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_config')
        cls.contact_ct_id = ContentType.objects.get_for_model(Contact).id

        Relation.objects.all().delete()
        RelationType.objects.all().delete()

    def setUp(self):
        self.user = User.objects.create(username='name')

    def test_relation01(self):
        subject_pred = 'is loving'
        object_pred  = 'is loved by'

        with self.assertNoException():
            rtype1, rtype2 = RelationType.create(('test-subject_foobar', subject_pred),
                                                 ('test-object_foobar',  object_pred))

        self.assertEqual(rtype1.symmetric_type, rtype2)
        self.assertEqual(rtype2.symmetric_type, rtype1)
        self.assertEqual(rtype1.predicate,      subject_pred)
        self.assertEqual(rtype2.predicate,      object_pred)

        with self.assertNoException():
            entity1  = CremeEntity.objects.create(user=self.user)
            entity2  = CremeEntity.objects.create(user=self.user)
            relation = Relation.objects.create(user=self.user, type=rtype1,
                                               subject_entity=entity1, object_entity=entity2
                                              )

        sym = relation.symmetric_relation
        self.assertEqual(sym.type,           rtype2)
        self.assertEqual(sym.subject_entity, entity2)
        self.assertEqual(sym.object_entity,  entity1)

    def test_relation02(self):
        "BEWARE: don't do this ! Bad usage of Relations"
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

    def test_relation03(self): #TODO: deprecated
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

    def test_relation04(self):
        rtype1, rtype2 = RelationType.create(('test-subject_foobar', 'is loving'),
                                             ('test-object_foobar',  'is loved by'))
        rtype1.delete()
        self.assertRaises(RelationType.DoesNotExist, RelationType.objects.get, id=rtype1.id)
        self.assertRaises(RelationType.DoesNotExist, RelationType.objects.get, id=rtype2.id)

    def build_compatible_set(self, **kwargs):
        return set(RelationType.get_compatible_ones(self.contact_ct_id, **kwargs).values_list('id', flat=True))

    def test_get_compatible_ones01(self):
        original_compatibles_ids = self.build_compatible_set()
        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'manages',       [Contact]),
                                               ('test-object_foobar',  'is managed by', [Organisation])
                                              )
        internal_rtype, internal_sym_rtype = RelationType.create(('test-subject_foobar_2', 'manages internal',       [Contact]),
                                                                 ('test-object_foobar_2',  'is managed by internal', [Organisation]),
                                                                 is_internal=True,
                                                                )

        compatibles_ids = self.build_compatible_set()
        self.assertEqual(len(original_compatibles_ids) + 1, len(compatibles_ids))
        self.assertIn(rtype.id, compatibles_ids)

        compatibles_ids = self.build_compatible_set(include_internals=True)
        self.assertEqual(len(original_compatibles_ids) + 2, len(compatibles_ids))
        self.assertIn(rtype.id,          compatibles_ids)
        self.assertIn(internal_rtype.id, compatibles_ids)

        self.assertTrue(rtype.is_compatible(self.contact_ct_id))
        self.assertFalse(rtype.is_compatible(ContentType.objects.get_for_model(Organisation).id))

    def test_get_compatible_ones02(self):
        original_compatibles_ids = self.build_compatible_set()
        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'manages',       [Contact]),
                                               ('test-object_foobar',  'is managed by', [Organisation]),
                                               is_internal=True,
                                              )

        internal_rtype, internal_sym_rtype = RelationType.create(('test-subject_foobar_2', 'manages internal',       [Contact]),
                                                                 ('test-object_foobar_2',  'is managed by internal', [Organisation]),
                                                                 is_internal=True,
                                                                )
        self.assertEqual(original_compatibles_ids, self.build_compatible_set())

        compatibles_ids = self.build_compatible_set(include_internals=True)
        self.assertEqual(len(original_compatibles_ids) + 2, len(compatibles_ids))
        self.assertIn(rtype.id,          compatibles_ids)
        self.assertIn(internal_rtype.id, compatibles_ids)

    def test_get_compatible_ones03(self):
        original_compatibles_ids = self.build_compatible_set()
        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'manages'),
                                               ('test-object_foobar',  'is managed by')
                                              )
        internal_rtype, internal_sym_rtype = RelationType.create(('test-subject_foobar_2', 'manages internal'),
                                                                 ('test-object_foobar_2',  'is managed by internal'),
                                                                 is_internal=True
                                                                )

        compatibles_ids = self.build_compatible_set()
        self.assertEqual(len(original_compatibles_ids) + 2, len(compatibles_ids))
        self.assertIn(rtype.id, compatibles_ids)
        self.assertIn(sym_rtype.id, compatibles_ids)

        compatibles_ids = self.build_compatible_set(include_internals=True)
        self.assertEqual(len(original_compatibles_ids) + 4, len(compatibles_ids))
        self.assertIn(rtype.id,              compatibles_ids)
        self.assertIn(sym_rtype.id,          compatibles_ids)
        self.assertIn(internal_rtype.id,     compatibles_ids)
        self.assertIn(internal_sym_rtype.id, compatibles_ids)

        self.assertTrue(rtype.is_compatible(self.contact_ct_id))
