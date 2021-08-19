# -*- coding: utf-8 -*-

from functools import partial

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from creme.creme_core.models import (
    CremeEntity,
    FakeContact,
    FakeOrganisation,
    Relation,
    RelationType,
)
from creme.creme_core.utils.profiling import CaptureQueriesContext

from ..base import CremeTestCase


class RelationsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contact_ct = ContentType.objects.get_for_model(FakeContact)

    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create(username='name')

    def test_relation_type_create(self):  # DEPRECATED
        subject_pred = 'is loving'
        object_pred  = 'is loved by'

        with self.assertNoException():
            rtype1, rtype2 = RelationType.create(
                ('test-subject_foobar', subject_pred),
                ('test-object_foobar',  object_pred),
            )

        self.assertEqual(rtype1.symmetric_type, rtype2)
        self.assertEqual(rtype2.symmetric_type, rtype1)
        self.assertEqual(rtype1.predicate,      subject_pred)
        self.assertEqual(rtype2.predicate,      object_pred)

    def test_relation01(self):
        user = self.user
        subject_id = 'test-subject_foobar'
        subject_pred = 'is loving'
        object_id = 'test-object_foobar'
        object_pred  = 'is loved by'

        with self.assertNoException():
            rtype1, rtype2 = RelationType.objects.smart_update_or_create(
                (subject_id, subject_pred),
                (object_id,  object_pred),
            )

        self.assertEqual(rtype1.id,             subject_id)
        self.assertEqual(rtype2.id,             object_id)
        self.assertEqual(rtype1.symmetric_type, rtype2)
        self.assertEqual(rtype2.symmetric_type, rtype1)
        self.assertEqual(rtype1.predicate,      subject_pred)
        self.assertEqual(rtype2.predicate,      object_pred)

        with self.assertNoException():
            entity1 = CremeEntity.objects.create(user=user)
            entity2 = CremeEntity.objects.create(user=user)

            relation = Relation.objects.create(
                user=user, type=rtype1, subject_entity=entity1, object_entity=entity2,
            )

        sym = relation.symmetric_relation
        self.assertEqual(sym.type,           rtype2)
        self.assertEqual(sym.subject_entity, entity2)
        self.assertEqual(sym.object_entity,  entity1)

    def test_relation02(self):
        "BEWARE: don't do this ! Bad usage of Relations."
        rtype1, rtype2 = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by'),
        )

        create_entity = partial(CremeEntity.objects.create, user=self.user)
        relation = Relation.objects.create(
            user=self.user, type=rtype1,
            subject_entity=create_entity(),
            object_entity=create_entity()
        )

        # This will not update symmetric relation !!
        relation.subject_entity = create_entity()
        relation.object_entity  = create_entity()

        self.assertNotEqual(
            relation.subject_entity_id,
            relation.symmetric_relation.object_entity_id,
        )
        self.assertNotEqual(
            relation.object_entity_id,
            relation.symmetric_relation.subject_entity_id,
        )

        # --
        with self.assertLogs(level='WARNING') as logs_manager:
            with self.assertNumQueries(0):
                relation.save()

        self.assertEqual(
            logs_manager.output,
            [
                f'WARNING:creme.creme_core.models.relation:'
                f'Relation.save(): '
                f'try to update instance pk={relation.id} (should only be created).',
            ],
        )

    def test_delete_rtype(self):
        rtype1, rtype2 = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by'),
        )
        rtype1.delete()

        get_rtype = RelationType.objects.get
        self.assertRaises(RelationType.DoesNotExist, get_rtype, id=rtype1.id)
        self.assertRaises(RelationType.DoesNotExist, get_rtype, id=rtype2.id)

    def build_compatible_set(self, ct_or_model=None, **kwargs):
        return {
            *RelationType.objects
                         .compatible(ct_or_model or self.contact_ct, **kwargs)
                         .values_list('id', flat=True),
        }

    def test_manager_compatible01(self):
        orig_compat_ids = self.build_compatible_set()
        orig_internal_compat_ids = self.build_compatible_set(include_internals=True)

        create_rtype = RelationType.objects.smart_update_or_create
        rtype = create_rtype(
            ('test-subject_foobar', 'manages',       [FakeContact]),
            ('test-object_foobar',  'is managed by', [FakeOrganisation]),
        )[0]
        internal_rtype = create_rtype(
            ('test-subject_foobar_2', 'manages internal',       [FakeContact]),
            ('test-object_foobar_2',  'is managed by internal', [FakeOrganisation]),
            is_internal=True,
        )[0]

        compatibles_ids = self.build_compatible_set()
        self.assertEqual(len(orig_compat_ids) + 1, len(compatibles_ids))
        self.assertIn(rtype.id, compatibles_ids)

        compatibles_internal_ids = self.build_compatible_set(include_internals=True)
        self.assertEqual(len(orig_internal_compat_ids) + 2, len(compatibles_internal_ids))
        self.assertIn(rtype.id,          compatibles_internal_ids)
        self.assertIn(internal_rtype.id, compatibles_internal_ids)

        contact_ct = self.contact_ct
        self.assertTrue(rtype.is_compatible(contact_ct.id))
        self.assertTrue(rtype.is_compatible(contact_ct))
        self.assertTrue(rtype.is_compatible(str(contact_ct.id)))
        self.assertTrue(rtype.is_compatible(FakeContact))
        self.assertTrue(rtype.is_compatible(FakeContact()))

        orga_ct = ContentType.objects.get_for_model(FakeOrganisation)
        self.assertFalse(rtype.is_compatible(orga_ct.id))
        self.assertFalse(rtype.is_compatible(orga_ct))
        self.assertFalse(rtype.is_compatible(str(orga_ct.id)))
        self.assertFalse(rtype.is_compatible(FakeOrganisation))
        self.assertFalse(rtype.is_compatible(FakeOrganisation()))

        # Model as argument
        self.assertSetEqual(
            compatibles_ids,
            self.build_compatible_set(FakeContact),
        )

    def test_manager_compatible02(self):
        orig_compat_ids = self.build_compatible_set()
        orig_internal_compat_ids = self.build_compatible_set(include_internals=True)

        create_rtype = RelationType.objects.smart_update_or_create
        rtype = create_rtype(
            ('test-subject_foobar', 'manages',       [FakeContact]),
            ('test-object_foobar',  'is managed by', [FakeOrganisation]),
            is_internal=True,
        )[0]

        internal_rtype = create_rtype(
            ('test-subject_foobar_2', 'manages internal',       [FakeContact]),
            ('test-object_foobar_2',  'is managed by internal', [FakeOrganisation]),
            is_internal=True,
        )[0]
        self.assertEqual(orig_compat_ids, self.build_compatible_set())

        compatibles_ids = self.build_compatible_set(include_internals=True)
        self.assertEqual(len(orig_internal_compat_ids) + 2, len(compatibles_ids))
        self.assertIn(rtype.id,          compatibles_ids)
        self.assertIn(internal_rtype.id, compatibles_ids)

    def test_manager_compatible03(self):
        orig_compat_ids = self.build_compatible_set()
        orig_internal_compat_ids = self.build_compatible_set(include_internals=True)

        create_rtype = RelationType.objects.smart_update_or_create
        rtype, sym_rtype = create_rtype(
            ('test-subject_foobar', 'manages'),
            ('test-object_foobar',  'is managed by'),
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

        self.assertTrue(rtype.is_compatible(self.contact_ct.id))

    def test_manager_safe_create(self):
        rtype, srtype = RelationType.objects.smart_update_or_create(
            ('test-subject_challenge', 'challenges'),
            ('test-object_challenge',  'is challenged by'),
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
        rtype, srtype = RelationType.objects.smart_update_or_create(
            ('test-subject_challenge', 'challenges'),
            ('test-object_challenge',  'is challenged by'),
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
        rtype, srtype = RelationType.objects.smart_update_or_create(
            ('test-subject_challenge', 'challenges'),
            ('test-object_challenge',  'is challenged by'),
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
        "Create several relation."
        create_rtype = RelationType.objects.smart_update_or_create
        rtype1, srtype1 = create_rtype(
            ('test-subject_challenge', 'challenges'),
            ('test-object_challenge',  'is challenged by'),
        )
        rtype2, srtype2 = create_rtype(
            ('test-subject_foobar', 'loves'),
            ('test-object_foobar',  'is loved by'),
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
        "De-duplicates arguments."
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'challenges'),
            ('test-object_foobar',  'is challenged by'),
        )[0]

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        def build_rel():
            return Relation(
                user=user, subject_entity=ryuko, type=rtype, object_entity=satsuki,
            )

        with self.assertNoException():
            count = Relation.objects.safe_multi_save([build_rel(), build_rel()])

        rel = self.get_object_or_fail(Relation, type=rtype)
        self.assertEqual(ryuko.id,   rel.subject_entity_id)
        self.assertEqual(satsuki.id, rel.object_entity_id)
        self.assertEqual(user.id,    rel.user_id)

        self.assertEqual(1, count)

    def test_manager_safe_multi_save03(self):
        "Avoid creating existing relations."
        create_rtype = RelationType.objects.smart_update_or_create
        rtype1 = create_rtype(
            ('test-subject_challenge', 'challenges'),
            ('test-object_challenge',  'is challenged by'),
        )[0]
        rtype2 = create_rtype(
            ('test-subject_foobar', 'loves'),
            ('test-object_foobar',  'is loved by'),
        )[0]

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        def build_rel1():
            return Relation(
                user=user, subject_entity=ryuko, type=rtype1, object_entity=satsuki,
            )

        rel1 = build_rel1()
        rel1.save()

        with self.assertNoException():
            Relation.objects.safe_multi_save([
                build_rel1(),
                Relation(
                    user=user, subject_entity=ryuko, type=rtype2, object_entity=satsuki,
                ),
                build_rel1(),
            ])

        self.assertStillExists(rel1)

        rel2 = self.get_object_or_fail(Relation, type=rtype2)
        self.assertEqual(ryuko.id,   rel2.subject_entity_id)
        self.assertEqual(satsuki.id, rel2.object_entity_id)
        self.assertEqual(user.id,    rel2.user_id)

    def test_manager_safe_multi_save04(self):
        "No query if no relations."
        with self.assertNumQueries(0):
            count = Relation.objects.safe_multi_save([])

        self.assertEqual(0, count)

    def test_manager_safe_multi_save05(self):
        "Argument <check_existing>."
        create_rtype = RelationType.objects.smart_update_or_create
        rtype1, srtype1 = create_rtype(
            ('test-subject_challenge', 'challenges'),
            ('test-object_challenge',  'is challenged by'),
        )
        rtype2, srtype2 = create_rtype(
            ('test-subject_foobar', 'loves'),
            ('test-object_foobar',  'is loved by'),
        )

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        build_rel = partial(Relation, user=user, subject_entity=ryuko, object_entity=satsuki)

        with CaptureQueriesContext() as ctxt1:
            Relation.objects.safe_multi_save(
                [build_rel(type=rtype1)], check_existing=True,
            )

        with CaptureQueriesContext() as ctxt2:
            Relation.objects.safe_multi_save(
                [build_rel(type=rtype2)], check_existing=False,
            )

        self.assertRelationCount(1, subject_entity=ryuko, type_id=rtype1.id, object_entity=satsuki)
        self.assertRelationCount(1, subject_entity=ryuko, type_id=rtype2.id, object_entity=satsuki)

        self.assertEqual(len(ctxt1), len(ctxt2) + 1)
