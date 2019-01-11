# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.auth import get_user_model
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.models import CremeEntity, RelationType, Relation
    from ..base import CremeTestCase
    from ..fake_models import FakeContact, FakeOrganisation
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class RelationsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contact_ct_id = ContentType.objects.get_for_model(FakeContact).id

    def setUp(self):
        self.user = get_user_model().objects.create(username='name')

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

        # This will not update symmetric relation !!
        relation.subject_entity = create_entity(user=self.user)
        relation.object_entity  = create_entity(user=self.user)

        self.assertNotEqual(relation.subject_entity_id, relation.symmetric_relation.object_entity_id)
        self.assertNotEqual(relation.object_entity_id,  relation.symmetric_relation.subject_entity_id)

    def test_delete_rtype(self):
        rtype1, rtype2 = RelationType.create(('test-subject_foobar', 'is loving'),
                                             ('test-object_foobar',  'is loved by'))
        rtype1.delete()
        self.assertRaises(RelationType.DoesNotExist, RelationType.objects.get, id=rtype1.id)
        self.assertRaises(RelationType.DoesNotExist, RelationType.objects.get, id=rtype2.id)

    def build_compatible_set(self, **kwargs):
        return set(RelationType.get_compatible_ones(self.contact_ct_id, **kwargs)
                               .values_list('id', flat=True)
                  )

    def test_get_compatible_ones01(self):
        orig_compat_ids = self.build_compatible_set()
        orig_internal_compat_ids = self.build_compatible_set(include_internals=True)

        create_rtype = RelationType.create
        rtype = create_rtype(('test-subject_foobar', 'manages',       [FakeContact]),
                             ('test-object_foobar',  'is managed by', [FakeOrganisation])
                            )[0]
        internal_rtype = create_rtype(('test-subject_foobar_2', 'manages internal',       [FakeContact]),
                                      ('test-object_foobar_2',  'is managed by internal', [FakeOrganisation]),
                                      is_internal=True,
                                     )[0]

        compatibles_ids = self.build_compatible_set()
        self.assertEqual(len(orig_compat_ids) + 1, len(compatibles_ids))
        self.assertIn(rtype.id, compatibles_ids)

        compatibles_ids = self.build_compatible_set(include_internals=True)
        self.assertEqual(len(orig_internal_compat_ids) + 2, len(compatibles_ids))
        self.assertIn(rtype.id,          compatibles_ids)
        self.assertIn(internal_rtype.id, compatibles_ids)

        self.assertTrue(rtype.is_compatible(self.contact_ct_id))
        self.assertFalse(rtype.is_compatible(ContentType.objects.get_for_model(FakeOrganisation).id))

    def test_get_compatible_ones02(self):
        orig_compat_ids = self.build_compatible_set()
        orig_internal_compat_ids = self.build_compatible_set(include_internals=True)

        create_rtype = RelationType.create
        rtype = create_rtype(('test-subject_foobar', 'manages',       [FakeContact]),
                             ('test-object_foobar',  'is managed by', [FakeOrganisation]),
                             is_internal=True,
                            )[0]

        internal_rtype = create_rtype(('test-subject_foobar_2', 'manages internal',       [FakeContact]),
                                      ('test-object_foobar_2',  'is managed by internal', [FakeOrganisation]),
                                      is_internal=True,
                                     )[0]
        self.assertEqual(orig_compat_ids, self.build_compatible_set())

        compatibles_ids = self.build_compatible_set(include_internals=True)
        self.assertEqual(len(orig_internal_compat_ids) + 2, len(compatibles_ids))
        self.assertIn(rtype.id,          compatibles_ids)
        self.assertIn(internal_rtype.id, compatibles_ids)

    def test_get_compatible_ones03(self):
        orig_compat_ids = self.build_compatible_set()
        orig_internal_compat_ids = self.build_compatible_set(include_internals=True)

        create_rtype = RelationType.create
        rtype, sym_rtype = create_rtype(('test-subject_foobar', 'manages'),
                                        ('test-object_foobar',  'is managed by')
                                       )
        internal_rtype, internal_sym_rtype = create_rtype(
                ('test-subject_foobar_2', 'manages internal'),
                ('test-object_foobar_2',  'is managed by internal'),
                is_internal=True,
            )

        compatibles_ids = self.build_compatible_set()
        self.assertEqual(len(orig_compat_ids) + 2, len(compatibles_ids))
        self.assertIn(rtype.id, compatibles_ids)
        self.assertIn(sym_rtype.id, compatibles_ids)

        compatibles_ids = self.build_compatible_set(include_internals=True)
        self.assertEqual(len(orig_internal_compat_ids) + 4, len(compatibles_ids))
        self.assertIn(rtype.id,              compatibles_ids)
        self.assertIn(sym_rtype.id,          compatibles_ids)
        self.assertIn(internal_rtype.id,     compatibles_ids)
        self.assertIn(internal_sym_rtype.id, compatibles_ids)

        self.assertTrue(rtype.is_compatible(self.contact_ct_id))

    def test_manager_safe_create(self):
        rtype, srtype = RelationType.create(
            ('test-subject_challenge', 'challenges'),
            ('test-object_challenge',  'is challenged by')
        )

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        res = Relation.objects.safe_create(
            user=user, subject_entity=ryuko, type=rtype, object_entity=satsuki,
        )
        self.assertIsNone(res)

        rel = self.get_object_or_fail(Relation, type=rtype)
        self.assertEqual(rtype.id,   rel.type_id)
        self.assertEqual(ryuko.id,   rel.subject_entity_id)
        self.assertEqual(satsuki.id, rel.object_entity_id)
        self.assertEqual(user.id,    rel.user_id)
        self.assertEqual(srtype,     rel.symmetric_relation.type)

        # ---
        with self.assertNoException():
            Relation.objects.safe_create(
                user=user, subject_entity=ryuko, type=rtype, object_entity=satsuki,
            )

    def test_manager_safe_get_or_create01(self):
        rtype, srtype = RelationType.create(
            ('test-subject_challenge', 'challenges'),
            ('test-object_challenge',  'is challenged by')
        )

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        rel1 = Relation.objects.safe_get_or_create(
            user=user, subject_entity=ryuko, type=rtype, object_entity=satsuki,
        )
        self.assertIsInstance(rel1, Relation)
        self.assertTrue(rel1.pk)
        self.assertEqual(rtype.id,   rel1.type_id)
        self.assertEqual(ryuko.id,   rel1.subject_entity_id)
        self.assertEqual(satsuki.id, rel1.object_entity_id)
        self.assertEqual(user.id,    rel1.user_id)
        self.assertEqual(srtype,     rel1.symmetric_relation.type)

        # ---
        with self.assertNoException():
            rel2 = Relation.objects.safe_get_or_create(
                user=user, subject_entity=ryuko, type=rtype, object_entity=satsuki,
            )

        self.assertEqual(rel1, rel2)

    def test_manager_safe_get_or_create02(self):
        "Give user ID (not user instance)"
        rtype, srtype = RelationType.create(
            ('test-subject_challenge', 'challenges'),
            ('test-object_challenge',  'is challenged by')
        )

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        rel1 = Relation.objects.safe_get_or_create(
            user_id=user.id, subject_entity=ryuko, type=rtype, object_entity=satsuki,
        )
        self.assertIsInstance(rel1, Relation)
        self.assertTrue(rel1.pk)
        self.assertEqual(rtype.id,   rel1.type_id)
        self.assertEqual(ryuko.id,   rel1.subject_entity_id)
        self.assertEqual(satsuki.id, rel1.object_entity_id)
        self.assertEqual(user.id,    rel1.user_id)
        self.assertEqual(srtype,     rel1.symmetric_relation.type)

        # ---
        with self.assertNoException():
            rel2 = Relation.objects.safe_get_or_create(
                user_id=user.id, subject_entity=ryuko, type=rtype, object_entity=satsuki,
            )

        self.assertEqual(rel1, rel2)

    def test_manager_safe_multi_save01(self):
        "Create several relation"
        rtype1, srtype1 = RelationType.create(
            ('test-subject_challenge', 'challenges'),
            ('test-object_challenge',  'is challenged by')
        )
        rtype2, srtype2 = RelationType.create(
            ('test-subject_foobar', 'loves'),
            ('test-object_foobar',  'is loved by')
        )

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        count = Relation.objects.safe_multi_save([
            Relation(user=user, subject_entity=ryuko, type=rtype1, object_entity=satsuki),
            Relation(user=user, subject_entity=ryuko, type=rtype2, object_entity=satsuki),
        ])

        self.assertEqual(2, count)

        rel1 = self.get_object_or_fail(Relation, type=rtype1)
        self.assertEqual(ryuko.id,   rel1.subject_entity_id)
        self.assertEqual(satsuki.id, rel1.object_entity_id)
        self.assertEqual(user.id,    rel1.user_id)
        self.assertEqual(srtype1,    rel1.symmetric_relation.type)

        rel2 = self.get_object_or_fail(Relation, type=rtype2)
        self.assertEqual(ryuko.id,   rel2.subject_entity_id)
        self.assertEqual(satsuki.id, rel2.object_entity_id)
        self.assertEqual(user.id,    rel2.user_id)
        self.assertEqual(srtype2,    rel2.symmetric_relation.type)

    def test_manager_safe_multi_save02(self):
        "De-duplicates arguments"
        rtype = RelationType.create(('test-subject_foobar', 'challenges'),
                                    ('test-object_foobar',  'is challenged by')
                                   )[0]

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        def build_rel():
            return Relation(user=user, subject_entity=ryuko, type=rtype, object_entity=satsuki)

        with self.assertNoException():
            count = Relation.objects.safe_multi_save([build_rel(), build_rel()])

        rel = self.get_object_or_fail(Relation, type=rtype)
        self.assertEqual(ryuko.id,   rel.subject_entity_id)
        self.assertEqual(satsuki.id, rel.object_entity_id)
        self.assertEqual(user.id,    rel.user_id)

        self.assertEqual(1, count)

    def test_manager_safe_multi_save03(self):
        "Avoid creating existing relations"
        rtype1 = RelationType.create(
            ('test-subject_challenge', 'challenges'),
            ('test-object_challenge',  'is challenged by')
        )[0]
        rtype2 = RelationType.create(
            ('test-subject_foobar', 'loves'),
            ('test-object_foobar',  'is loved by')
        )[0]

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        def build_rel1():
            return Relation(user=user, subject_entity=ryuko, type=rtype1, object_entity=satsuki)

        rel1 = build_rel1()
        rel1.save()

        with self.assertNoException():
            Relation.objects.safe_multi_save([
                build_rel1(),
                Relation(user=user, subject_entity=ryuko, type=rtype2, object_entity=satsuki),
                build_rel1(),
            ])

        self.assertStillExists(rel1)

        rel2 = self.get_object_or_fail(Relation, type=rtype2)
        self.assertEqual(ryuko.id,   rel2.subject_entity_id)
        self.assertEqual(satsuki.id, rel2.object_entity_id)
        self.assertEqual(user.id,    rel2.user_id)

    def test_manager_safe_multi_save04(self):
        "No query if no relations"
        with self.assertNumQueries(0):
            count = Relation.objects.safe_multi_save([])

        self.assertEqual(0, count)
