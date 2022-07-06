from functools import partial

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import prefetch_related_objects
from django.utils.translation import gettext as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    FakeContact,
    FakeOrganisation,
    Relation,
    RelationType,
)
from creme.creme_core.utils.profiling import CaptureQueriesContext

from ..base import CremeTestCase
from ..fake_models import FakeDocument


class RelationsTestCase(CremeTestCase):
    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create(username='name')

    # def test_relation_type_create(self):  # DEPRECATED
    #     subject_pred = 'is loving'
    #     object_pred  = 'is loved by'
    #
    #     with self.assertNoException():
    #         rtype1, rtype2 = RelationType.create(
    #             ('test-subject_foobar', subject_pred),
    #             ('test-object_foobar',  object_pred),
    #         )
    #
    #     self.assertEqual(rtype1.symmetric_type, rtype2)
    #     self.assertEqual(rtype2.symmetric_type, rtype1)
    #     self.assertEqual(rtype1.predicate,      subject_pred)
    #     self.assertEqual(rtype2.predicate,      object_pred)

    def test_type_manager_smart_update_or_create01(self):
        subject_id = 'test-subject_foobar'
        subject_pred = 'is loving'
        object_id = 'test-object_foobar'
        object_pred  = 'is loved by'

        with self.assertNoException():
            rtype1, rtype2 = RelationType.objects.smart_update_or_create(
                (subject_id, subject_pred),
                (object_id,  object_pred),
            )

        self.assertIsInstance(rtype1, RelationType)
        self.assertIsInstance(rtype2, RelationType)

        rtype1 = self.refresh(rtype1)
        rtype2 = self.refresh(rtype2)

        self.assertEqual(rtype1.id,             subject_id)
        self.assertEqual(rtype2.id,             object_id)
        self.assertEqual(rtype1.symmetric_type, rtype2)
        self.assertEqual(rtype2.symmetric_type, rtype1)
        self.assertEqual(rtype1.predicate,      subject_pred)
        self.assertEqual(rtype2.predicate,      object_pred)
        self.assertFalse(rtype1.is_internal)
        self.assertFalse(rtype2.is_internal)
        self.assertFalse(rtype1.is_custom)
        self.assertFalse(rtype2.is_custom)
        self.assertTrue(rtype1.is_copiable)
        self.assertTrue(rtype2.is_copiable)
        self.assertFalse(rtype1.minimal_display)
        self.assertFalse(rtype2.minimal_display)
        self.assertTrue(rtype1.enabled)
        self.assertTrue(rtype2.enabled)

        self.assertFalse(rtype1.subject_ctypes.all())
        self.assertFalse([*rtype1.subject_models])
        self.assertFalse(rtype1.object_ctypes.all())
        self.assertFalse([*rtype1.object_models])
        self.assertFalse(rtype1.subject_properties.all())
        self.assertFalse(rtype1.object_properties.all())

        self.assertFalse(rtype2.subject_ctypes.all())
        self.assertFalse(rtype2.object_ctypes.all())
        self.assertFalse(rtype2.subject_properties.all())
        self.assertFalse(rtype2.object_properties.all())

    def test_type_manager_smart_update_or_create02(self):
        "ContentType constraints + custom."
        subject_id = 'test-subject_baz'
        subject_pred = 'owns'
        object_id = 'test-object_baz'
        object_pred  = 'is owned by'

        with self.assertNoException():
            rtype1, rtype2 = RelationType.objects.smart_update_or_create(
                (subject_id, subject_pred, [FakeContact, FakeOrganisation]),
                (object_id,  object_pred,  [FakeDocument]),
                is_custom=True,
                is_copiable=(True, False),
            )

        self.assertEqual(rtype1.id,             subject_id)
        self.assertEqual(rtype2.id,             object_id)
        self.assertEqual(rtype1.symmetric_type, rtype2)
        self.assertEqual(rtype2.symmetric_type, rtype1)
        self.assertEqual(rtype1.predicate,      subject_pred)
        self.assertEqual(rtype2.predicate,      object_pred)
        self.assertFalse(rtype1.is_internal)
        self.assertTrue(rtype1.enabled)

        self.assertTrue(rtype1.is_copiable)
        self.assertFalse(rtype2.is_copiable)

        self.assertTrue(rtype1.is_custom)
        self.assertTrue(rtype2.is_custom)

        get_ct = ContentType.objects.get_for_model
        self.assertCountEqual(
            [get_ct(FakeContact), get_ct(FakeOrganisation)],
            rtype1.subject_ctypes.all(),
        )
        self.assertCountEqual(
            [FakeContact, FakeOrganisation],
            [*rtype1.subject_models],
        )
        self.assertCountEqual([get_ct(FakeDocument)], rtype1.object_ctypes.all())
        self.assertCountEqual([FakeDocument], [*rtype1.object_models])
        self.assertFalse(rtype1.subject_properties.all())
        self.assertFalse(rtype1.object_properties.all())

        self.assertListEqual([FakeDocument], [*rtype2.subject_models])
        self.assertCountEqual(
            [FakeContact, FakeOrganisation],
            [*rtype2.object_models],
        )
        self.assertFalse(rtype2.subject_properties.all())

        # Update
        subject_pred = f'{subject_pred} (updated)'
        object_pred  = f'{object_pred} (updated)'

        with self.assertNoException():
            new_rtype1, new_rtype2 = RelationType.objects.smart_update_or_create(
                (subject_id, subject_pred, [FakeOrganisation]),
                (object_id,  object_pred,  [FakeContact]),
                is_custom=False,
                is_copiable=(False, True),
            )

        new_rtype1 = self.refresh(new_rtype1)
        new_rtype2 = self.refresh(new_rtype2)

        self.assertEqual(new_rtype1.symmetric_type, new_rtype2)
        self.assertEqual(new_rtype2.symmetric_type, new_rtype1)
        self.assertEqual(new_rtype1.predicate,      subject_pred)
        self.assertEqual(new_rtype2.predicate,      object_pred)

        self.assertFalse(new_rtype1.is_copiable)
        self.assertTrue(new_rtype2.is_copiable)

        self.assertFalse(new_rtype1.is_custom)
        self.assertFalse(new_rtype2.is_custom)

        self.assertListEqual([FakeOrganisation], [*new_rtype1.subject_models])
        self.assertListEqual([FakeContact],      [*new_rtype1.object_models])

    def test_type_manager_smart_update_or_create03(self):
        "CremeProperty constraints."
        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-ptype01', text='Test01')
        ptype2 = create_ptype(str_pk='test-ptype02', text='Test02')
        ptype3 = create_ptype(str_pk='test-ptype03', text='Test03')

        with self.assertNoException():
            rtype1, rtype2 = RelationType.objects.smart_update_or_create(
                ('test-subject_foobaz', 'owns',        [], [ptype1, ptype2]),
                ('test-object_foobaz',  'is owned by', [], [ptype3]),
                minimal_display=(True, False),
            )

        self.assertTrue(rtype1.minimal_display)
        self.assertFalse(rtype2.minimal_display)

        self.assertCountEqual([ptype1, ptype2], rtype1.subject_properties.all())
        self.assertCountEqual([ptype3],         rtype1.object_properties.all())

        self.assertCountEqual([ptype3],         rtype2.subject_properties.all())
        self.assertCountEqual([ptype1, ptype2], rtype2.object_properties.all())

        self.assertFalse(rtype1.subject_forbidden_properties.all())
        self.assertFalse(rtype2.subject_forbidden_properties.all())

        self.assertFalse(rtype1.object_forbidden_properties.all())
        self.assertFalse(rtype2.object_forbidden_properties.all())

        # Update
        with self.assertNoException():
            new_rtype1, new_rtype2 = RelationType.objects.smart_update_or_create(
                ('test-subject_foobaz', 'owns',        [], [ptype2]),
                ('test-object_foobaz',  'is owned by', [], [ptype1, ptype3]),
                minimal_display=(False, True),
            )

        self.assertFalse(new_rtype1.minimal_display)
        self.assertTrue(new_rtype2.minimal_display)

        self.assertCountEqual([ptype2],         new_rtype1.subject_properties.all())
        self.assertCountEqual([ptype1, ptype3], new_rtype1.object_properties.all())

    def test_type_manager_smart_update_or_create04(self):
        "CremeProperty constraints."
        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-ptype01', text='Test01')
        ptype2 = create_ptype(str_pk='test-ptype02', text='Test02')
        ptype3 = create_ptype(str_pk='test-ptype03', text='Test03')

        with self.assertNoException():
            rtype1, rtype2 = RelationType.objects.smart_update_or_create(
                ('test-subject_foobaz', 'owns',        [], [], [ptype1, ptype2]),
                ('test-object_foobaz',  'is owned by', [], [], [ptype3]),
            )

        self.assertFalse(rtype1.subject_properties.all())
        self.assertFalse(rtype2.subject_properties.all())

        self.assertCountEqual([ptype1, ptype2], rtype1.subject_forbidden_properties.all())
        self.assertCountEqual([ptype3],         rtype2.subject_forbidden_properties.all())

        self.assertCountEqual([ptype3],         rtype1.object_forbidden_properties.all())
        self.assertCountEqual([ptype1, ptype2], rtype2.object_forbidden_properties.all())

        # Update
        with self.assertNoException():
            new_rtype1 = RelationType.objects.smart_update_or_create(
                ('test-subject_foobaz', 'owns',        [], [], [ptype1]),
                ('test-object_foobaz',  'is owned by', [], [], [ptype2, ptype3]),
            )[0]

        self.assertCountEqual([ptype1],         new_rtype1.subject_forbidden_properties.all())
        self.assertCountEqual([ptype2, ptype3], new_rtype1.object_forbidden_properties.all())

    def test_relation01(self):
        user = self.user

        rtype1, rtype2 = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by'),
        )

        with self.assertNoException():
            entity1 = CremeEntity.objects.create(user=user)
            entity2 = CremeEntity.objects.create(user=user)

            relation = Relation.objects.create(
                # user=user, type=rtype1, subject_entity=entity1, object_entity=entity2,
                user=user, type=rtype1, subject_entity=entity1, real_object=entity2,
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

    def test_is_not_internal_or_die01(self):
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_disabled', 'is disabled'),
            ('test-object_disabled',  'what ever'),
        )[0]

        with self.assertNoException():
            rtype.is_not_internal_or_die()

    def test_is_not_internal_or_die02(self):
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_internal', 'is internal'),
            ('test-object_internal',  'is internal too'),
            is_internal=True,
        )[0]

        with self.assertRaises(ConflictError):
            self.refresh(rtype).is_not_internal_or_die()

    def test_is_enabled_or_die(self):
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_disabled', 'is disabled'),
            ('test-object_disabled',  'what ever'),
        )[0]

        with self.assertNoException():
            rtype.is_enabled_or_die()

        rtype.enabled = False
        rtype.save()

        with self.assertRaises(ConflictError):
            self.refresh(rtype).is_enabled_or_die()

    def test_is_compatible01(self):
        rtype1, rtype2 = RelationType.objects.smart_update_or_create(
            ('test-subject_manages', 'manages'),
            ('test-object_manages',  'is managed by', [FakeContact, FakeOrganisation]),
        )

        # No constraint
        get_ct = ContentType.objects.get_for_model
        contact_ct = get_ct(FakeContact)
        self.assertTrue(rtype1.is_compatible(contact_ct))
        self.assertTrue(rtype1.is_compatible(contact_ct.id))
        self.assertTrue(rtype1.is_compatible(FakeContact))
        self.assertTrue(rtype1.is_compatible(FakeContact()))

        self.assertTrue(rtype1.is_compatible(FakeOrganisation))
        self.assertTrue(rtype1.is_compatible(FakeDocument))

        # Constraint
        self.assertTrue(rtype2.is_compatible(contact_ct))
        self.assertTrue(rtype2.is_compatible(contact_ct.id))
        self.assertTrue(rtype2.is_compatible(FakeContact))
        self.assertTrue(rtype2.is_compatible(FakeContact()))
        self.assertTrue(rtype2.is_compatible(FakeOrganisation))

        doc_ct = get_ct(FakeDocument)
        self.assertFalse(rtype2.is_compatible(doc_ct))
        self.assertFalse(rtype2.is_compatible(doc_ct.id))
        self.assertFalse(rtype2.is_compatible(FakeDocument))
        self.assertFalse(rtype2.is_compatible(FakeDocument()))

    def test_is_compatible02(self):
        "Queries (no prefetch)."
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_manages', 'manages',       [FakeContact]),
            ('test-object_manages',  'is managed by', [FakeOrganisation]),
        )[0]

        contact_ct = ContentType.objects.get_for_model(FakeContact)

        with self.assertNumQueries(1):
            rtype.is_compatible(contact_ct)

        with self.assertNumQueries(1):
            rtype.is_compatible(contact_ct.id)

    def test_is_compatible03(self):
        "Queries (prefetch)."
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_manages', 'manages',       [FakeContact]),
            ('test-object_manages',  'is managed by', [FakeOrganisation]),
        )[0]

        contact_ct = ContentType.objects.get_for_model(FakeContact)

        with self.assertNumQueries(1):
            prefetch_related_objects([rtype], 'subject_ctypes')

        with self.assertNumQueries(0):
            rtype.is_compatible(contact_ct)

        with self.assertNumQueries(0):
            rtype.is_compatible(contact_ct.id)

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
        if ct_or_model is None:
            ct_or_model = ContentType.objects.get_for_model(FakeContact)

        return {
            *RelationType.objects
                         .compatible(ct_or_model, **kwargs)
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

        contact_ct = ContentType.objects.get_for_model(FakeContact)
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

        self.assertTrue(rtype.is_compatible(
            ContentType.objects.get_for_model(FakeContact).id
        ))

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
        self.assertEqual(satsuki.entity_type, rel.object_ctype)
        self.assertEqual(satsuki.id, rel.object_entity_id)
        self.assertEqual(satsuki,    rel.real_object)
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
        self.assertEqual(rtype.id,            rel1.type_id)
        self.assertEqual(ryuko.id,            rel1.subject_entity_id)
        self.assertEqual(satsuki.entity_type, rel1.object_ctype)
        self.assertEqual(satsuki.id,          rel1.object_entity_id)
        self.assertEqual(user.id,             rel1.user_id)
        self.assertEqual(srtype,              rel1.symmetric_relation.type)

        # ---
        with self.assertNoException():
            rel2 = Relation.objects.safe_get_or_create(
                user=user, subject_entity=ryuko, type=rtype, object_entity=satsuki,
            )

        self.assertEqual(rel1, rel2)

    def test_manager_safe_get_or_create02(self):
        "Give user ID (not user instance)."
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
            # Relation(user=user, subject_entity=ryuko, type=rtype1, object_entity=satsuki),
            Relation(user=user, subject_entity=ryuko, type=rtype1, real_object=satsuki),
            Relation(user=user, subject_entity=ryuko, type=rtype2, object_entity=satsuki),
        ])

        self.assertEqual(2, count)

        rel1 = self.get_object_or_fail(Relation, type=rtype1)
        self.assertEqual(ryuko.id,            rel1.subject_entity_id)
        self.assertEqual(satsuki.entity_type, rel1.object_ctype)
        self.assertEqual(satsuki.id,          rel1.object_entity_id)
        self.assertEqual(user.id,             rel1.user_id)
        self.assertEqual(srtype1,             rel1.symmetric_relation.type)

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
                # user=user, subject_entity=ryuko, type=rtype, object_entity=satsuki,
                user=user, subject_entity=ryuko, type=rtype, real_object=satsuki,
            )

        with self.assertNoException():
            count = Relation.objects.safe_multi_save([build_rel(), build_rel()])

        rel = self.get_object_or_fail(Relation, type=rtype)
        self.assertEqual(ryuko.id,   rel.subject_entity_id)
        self.assertEqual(satsuki,    rel.real_object)
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
                # user=user, subject_entity=ryuko, type=rtype1, object_entity=satsuki,
                user=user, subject_entity=ryuko, type=rtype1, real_object=satsuki,
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
        self.assertEqual(ryuko.id, rel2.subject_entity_id)
        self.assertEqual(satsuki,  rel2.real_object)
        self.assertEqual(user.id,  rel2.user_id)

    def test_manager_safe_multi_save04(self):
        "No query if no relations."
        with self.assertNumQueries(0):
            count = Relation.objects.safe_multi_save([])

        self.assertEqual(0, count)

    def test_manager_safe_multi_save05(self):
        "Argument <check_existing>."
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

        # build_rel = partial(Relation, user=user, subject_entity=ryuko, object_entity=satsuki)
        build_rel = partial(Relation, user=user, subject_entity=ryuko, real_object=satsuki)

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

    def test_clean01(self):
        "No constraint."
        create_rtype = RelationType.objects.smart_update_or_create
        rtype = create_rtype(
            ('test-subject_loves', 'loves'),
            ('test-object_loves',  'is loved by'),
        )[0]

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        rel = Relation(user=user, subject_entity=ryuko, real_object=satsuki, type=rtype)

        with self.assertNoException():
            rel.clean()

    def test_clean02(self):
        "ContentType constraints."
        create_rtype = RelationType.objects.smart_update_or_create
        rtype, sym_rtype = create_rtype(
            ('test-subject_loves', 'loves',       [FakeContact]),
            ('test-object_loves',  'is loved by', [FakeContact]),
        )

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        rel1 = Relation(user=user, subject_entity=ryuko, real_object=satsuki, type=rtype)
        with self.assertNoException():
            rel1.clean()

        # ---
        orga = FakeOrganisation.objects.create(user=user, name='Honnoji')

        rel2 = Relation(user=user, subject_entity=ryuko, real_object=orga, type=rtype)
        with self.assertRaises(ValidationError) as cm1:
            rel2.clean()

        msg = _(
            'The entity «%(entity)s» is a «%(model)s» which is not '
            'allowed by the relationship «%(predicate)s».'
        )
        self.assertListEqual(
            [
                msg % {
                    'entity': orga,
                    'model': 'Test Organisation',
                    # 'predicate': rtype.predicate,
                    'predicate': sym_rtype.predicate,
                },
            ],
            cm1.exception.messages,
        )

        # ---
        rel3 = Relation(user=user, subject_entity=orga, real_object=satsuki, type=rtype)
        with self.assertRaises(ValidationError) as cm2:
            rel3.clean()

        self.assertListEqual(
            [
                msg % {
                    'entity': orga,
                    'model': 'Test Organisation',
                    'predicate': rtype.predicate,
                },
            ],
            cm2.exception.messages,
        )

    def test_clean03(self):
        "Mandatory CremeProperties constraints."
        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-prop_strong', text='Is strong')
        ptype2 = create_ptype(str_pk='test-prop_cute',   text='Is cute')
        ptype3 = create_ptype(str_pk='test-prop_smart',  text='Is smart')

        create_rtype = RelationType.objects.smart_update_or_create
        rtype, sym_rtype = create_rtype(
            ('test-subject_loves', 'loves',       [FakeContact], [ptype1, ptype2]),
            ('test-object_loves',  'is loved by', [FakeContact], [ptype3]),
        )

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        CremeProperty.objects.create(creme_entity=ryuko, type=ptype1)

        # ---
        rel1 = Relation(user=user, subject_entity=ryuko, real_object=satsuki, type=rtype)
        with self.assertRaises(ValidationError) as cm1:
            rel1.clean()

        msg = _(
            'The entity «%(entity)s» has no property «%(property)s» '
            'which is required by the relationship «%(predicate)s».'
        )
        self.assertListEqual(
            [
                msg % {
                    'entity': ryuko,
                    'property': ptype2.text,
                    'predicate': rtype.predicate,
                },
            ],
            cm1.exception.messages,
        )

        # ---
        CremeProperty.objects.create(creme_entity=ryuko, type=ptype2)
        ryuko = self.refresh(ryuko)

        rel2 = Relation(user=user, subject_entity=ryuko, real_object=satsuki, type=rtype)
        with self.assertRaises(ValidationError) as cm2:
            rel2.clean()

        self.assertListEqual(
            [
                msg % {
                    'entity': satsuki,
                    'property': ptype3.text,
                    'predicate': sym_rtype.predicate,
                },
            ],
            cm2.exception.messages,
        )

        # ---
        CremeProperty.objects.create(creme_entity=satsuki, type=ptype3)
        satsuki = self.refresh(satsuki)

        rel3 = Relation(user=user, subject_entity=ryuko, real_object=satsuki, type=rtype)
        with self.assertNoException():
            rel3.clean()

    def test_clean04(self):
        "Forbidden CremeProperties constraints."
        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-prop_strong', text='Is strong')
        ptype2 = create_ptype(str_pk='test-prop_cute',   text='Is cute')
        ptype3 = create_ptype(str_pk='test-prop_smart',  text='Is smart')

        create_rtype = RelationType.objects.smart_update_or_create
        rtype, sym_rtype = create_rtype(
            ('test-subject_loves', 'loves',       [], [], [ptype2]),
            ('test-object_loves',  'is loved by', [], [], [ptype3]),
        )

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        create_ptype = CremeProperty.objects.create
        create_ptype(creme_entity=ryuko, type=ptype1)
        create_ptype(creme_entity=ryuko, type=ptype3)

        rel1 = Relation(user=user, subject_entity=ryuko, real_object=satsuki, type=rtype)
        with self.assertNoException():
            rel1.clean()

        # ---
        create_ptype(creme_entity=satsuki, type=ptype3)
        satsuki = self.refresh(satsuki)
        rel2 = Relation(user=user, subject_entity=ryuko, real_object=satsuki, type=rtype)
        with self.assertRaises(ValidationError) as cm1:
            rel2.clean()

        msg = _(
            'The entity «%(entity)s» has the property «%(property)s» '
            'which is forbidden by the relationship «%(predicate)s».'
        )
        self.assertListEqual(
            [
                msg % {
                    'entity': satsuki,
                    'property': ptype3.text,
                    'predicate': sym_rtype.predicate,
                },
            ],
            cm1.exception.messages,
        )

        # ---
        CremeProperty.objects.create(creme_entity=ryuko, type=ptype2)
        ryuko = self.refresh(ryuko)

        rel3 = Relation(user=user, subject_entity=ryuko, real_object=satsuki, type=rtype)
        with self.assertRaises(ValidationError) as cm2:
            rel3.clean()

        self.assertListEqual(
            [
                msg % {
                    'entity': ryuko,
                    'property': ptype2.text,
                    'predicate': rtype.predicate,
                },
            ],
            cm2.exception.messages,
        )

    def test_clean_subject_entity01(self):
        "Mandatory Property + argument 'property_types'."
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_cute', text='Is cute',
        )
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_loved', 'is loved by', [], [ptype]),
            ('test-object_loved',  'loves'),
        )[0]

        ryuko = FakeContact.objects.create(
            user=self.user, first_name='Ryuko', last_name='Matoi',
        )

        # ---
        rel = Relation(
            # user=self.user,
            subject_entity=ryuko,
            type=rtype,
            # real_object=satsuki,
        )
        with self.assertRaises(ValidationError) as cm:
            rel.clean_subject_entity(property_types=[])

        self.assertListEqual(
            [
                Relation.error_messages['missing_subject_property'] % {
                    'entity': ryuko,
                    'property': ptype.text,
                    'predicate': rtype.predicate,
                },
            ],
            cm.exception.messages,
        )

        # --
        with self.assertNoException():
            rel.clean_subject_entity(property_types=[ptype])

    def test_clean_subject_entity02(self):
        "Forbidden Property + argument 'property_types'."
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_not_cute', text='Is not cute',
        )
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_loved', 'is loved by', [], [], [ptype]),
            ('test-object_loved',  'loves'),
        )[0]

        ryuko = FakeContact.objects.create(
            user=self.user, first_name='Ryuko', last_name='Matoi',
        )

        # ---
        rel1 = Relation(
            # user=self.user,
            subject_entity=ryuko,
            type=rtype,
            # real_object=satsuki,
        )

        with self.assertRaises(ValidationError) as cm1:
            rel1.clean_subject_entity(property_types=[ptype])

        message = Relation.error_messages['refused_subject_property'] % {
            'entity': ryuko,
            'property': ptype.text,
            'predicate': rtype.predicate,
        }
        self.assertListEqual([message], cm1.exception.messages)

        # --
        with self.assertNoException():
            rel1.clean_subject_entity(property_types=[])

        # ---
        CremeProperty.objects.create(creme_entity=ryuko, type=ptype)
        ryuko = self.refresh(ryuko)

        rel2 = Relation(
            # user=self.user,
            subject_entity=ryuko,
            type=rtype,
            # real_object=satsuki,
        )

        with self.assertRaises(ValidationError) as cm2:
            rel2.clean_subject_entity()

        self.assertListEqual([message], cm2.exception.messages)
