from functools import partial

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
    FakeDocument,
    FakeOrganisation,
    Relation,
    RelationType,
)
from creme.creme_core.utils.profiling import CaptureQueriesContext

from ..base import CremeTestCase


class RelationTypeManagerTestCase(CremeTestCase):
    def test_smart_update_or_create(self):
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

    def test_smart_update_or_create__content_types(self):
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

    def test_smart_update_or_create__property_types(self):
        "CremeProperty constraints."
        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Test01')
        ptype2 = create_ptype(text='Test02')
        ptype3 = create_ptype(text='Test03')

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

    def test_smart_update_or_create__forbidden_property_types(self):
        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Test01')
        ptype2 = create_ptype(text='Test02')
        ptype3 = create_ptype(text='Test03')

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

    def build_compatible_set(self, ct_or_model=None, **kwargs):
        if ct_or_model is None:
            ct_or_model = ContentType.objects.get_for_model(FakeContact)

        return {
            *RelationType.objects
                         .compatible(ct_or_model, **kwargs)
                         .values_list('id', flat=True),
        }

    def test_compatible(self):
        orig_compat_ids = self.build_compatible_set()
        orig_internal_compat_ids = self.build_compatible_set(include_internals=True)

        rtype = RelationType.objects.builder(
            id='test-subject_foobar', predicate='manages', models=[FakeContact],
        ).symmetric(
            id='test-object_foobar', predicate='is managed by', models=[FakeOrganisation],
        ).get_or_create()[0]
        internal_rtype = RelationType.objects.builder(
            id='test-subject_foobar_2', predicate='manages internal', models=[FakeContact],
            is_internal=True,
        ).symmetric(
            id='test-object_foobar_2', predicate='is managed by internal',
            models=[FakeOrganisation],
        ).get_or_create()[0]

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

    def test_compatible__internal(self):
        orig_compat_ids = self.build_compatible_set()
        orig_internal_compat_ids = self.build_compatible_set(include_internals=True)

        rtype = RelationType.objects.builder(
            id='test-subject_foobar', predicate='manages', models=[FakeContact],
            is_internal=True,
        ).symmetric(
            id='test-object_foobar', predicate='is managed by', models=[FakeOrganisation],
        ).get_or_create()[0]

        internal_rtype = RelationType.objects.builder(
            id='test-subject_foobar_2', predicate='manages internal', models=[FakeContact],
            is_internal=True,
        ).symmetric(
            id='test-object_foobar_2', predicate='is managed by internal',
            models=[FakeOrganisation],
        ).get_or_create()[0]
        self.assertEqual(orig_compat_ids, self.build_compatible_set())

        compatibles_ids = self.build_compatible_set(include_internals=True)
        self.assertEqual(len(orig_internal_compat_ids) + 2, len(compatibles_ids))
        self.assertIn(rtype.id,          compatibles_ids)
        self.assertIn(internal_rtype.id, compatibles_ids)

    def test_compatible__no_ctype_constraint(self):
        orig_compat_ids = self.build_compatible_set()
        orig_internal_compat_ids = self.build_compatible_set(include_internals=True)

        rtype = RelationType.objects.builder(
            id='test-subject_foobar', predicate='manages',
        ).symmetric(id='test-object_foobar', predicate='is managed by').get_or_create()[0]
        internal_rtype = RelationType.objects.builder(
            id='test-subject_foobar_2', predicate='manages internal',
            is_internal=True,
        ).symmetric(
            id='test-object_foobar_2', predicate='is managed by internal',
        ).get_or_create()[0]

        compatibles_ids = self.build_compatible_set()
        self.assertEqual(len(orig_compat_ids) + 2, len(compatibles_ids))
        self.assertIn(rtype.id, compatibles_ids)
        self.assertIn(rtype.symmetric_type_id, compatibles_ids)

        compatibles_ids = self.build_compatible_set(include_internals=True)
        self.assertEqual(len(orig_internal_compat_ids) + 4, len(compatibles_ids))
        self.assertIn(rtype.id,                         compatibles_ids)
        self.assertIn(rtype.symmetric_type_id,          compatibles_ids)
        self.assertIn(internal_rtype.id,                compatibles_ids)
        self.assertIn(internal_rtype.symmetric_type_id, compatibles_ids)

        self.assertTrue(rtype.is_compatible(
            ContentType.objects.get_for_model(FakeContact).id
        ))

    def test_builder__update_or_create(self):
        subject_id = 'test-subject_foobar'
        subject_pred = 'is loving'
        object_id = 'test-object_foobar'
        object_pred  = 'is loved by'

        builder = RelationType.objects.builder(
            id=subject_id, predicate=subject_pred,
        ).symmetric(id=object_id, predicate=object_pred)

        self.assertEqual(builder.id,        subject_id)
        self.assertEqual(builder.predicate, subject_pred)
        self.assertFalse(builder.is_internal)
        self.assertFalse(builder.is_custom)
        self.assertTrue(builder.is_copiable)
        self.assertFalse(builder.minimal_display)
        self.assertTrue(builder.enabled)
        self.assertFalse([*builder.subject_models])
        self.assertFalse([*builder.subject_ctypes])
        # self.assertFalse([], [*builder.object_models]) TODO?
        self.assertFalse([*builder.subject_properties])
        # self.assertFalse([], [*builder.object_properties]) TODO?
        self.assertFalse([*builder.subject_forbidden_properties])

        sym_builder = builder.symmetric_type
        self.assertEqual(sym_builder.id,        object_id)
        self.assertEqual(sym_builder.predicate, object_pred)
        self.assertFalse(sym_builder.is_internal)
        self.assertFalse(sym_builder.is_custom)
        self.assertTrue(sym_builder.is_copiable)
        self.assertFalse(sym_builder.minimal_display)
        self.assertTrue(sym_builder.enabled)

        self.assertIs(builder, sym_builder.symmetric_type)

        rtype1, created = builder.update_or_create()
        self.assertIsInstance(rtype1, RelationType)
        self.assertEqual(subject_id, rtype1.pk)
        self.assertIs(created, True)
        self.assertEqual(object_id, rtype1.symmetric_type_id)

        rtype1 = self.refresh(rtype1)
        self.assertEqual(rtype1.id,        subject_id)
        self.assertEqual(rtype1.predicate, subject_pred)
        self.assertFalse(rtype1.is_internal)
        self.assertFalse(rtype1.is_custom)
        self.assertTrue(rtype1.is_copiable)
        self.assertFalse(rtype1.minimal_display)
        self.assertTrue(rtype1.enabled)

        rtype2 = rtype1.symmetric_type
        self.assertEqual(rtype2.id,        object_id)
        self.assertEqual(rtype2.predicate, object_pred)
        self.assertFalse(rtype2.is_internal)
        self.assertFalse(rtype2.is_custom)
        self.assertTrue(rtype2.is_copiable)
        self.assertFalse(rtype2.minimal_display)
        self.assertTrue(rtype2.enabled)

        self.assertEqual(rtype1.symmetric_type, rtype2)
        self.assertEqual(rtype2.symmetric_type, rtype1)

        self.assertFalse([*rtype1.subject_models])
        self.assertFalse(rtype1.subject_properties.all())
        self.assertFalse(rtype1.subject_forbidden_properties.all())

        self.assertFalse([*rtype2.subject_models])
        self.assertFalse(rtype2.subject_properties.all())
        self.assertFalse(rtype2.subject_forbidden_properties.all())

        # ---
        builder.predicate = new_pred = 'New predicate'
        new_rtype1, created2 = builder.update_or_create()
        self.assertIs(created2, False)
        self.assertEqual(new_pred, new_rtype1.predicate)

    def test_builder__update_or_create__constraints(self):
        "Constraints for ContentTypes & CremePropertyTypes."
        subject_id = 'test-subject_foobaz'
        subject_pred = 'is liking'
        object_id = 'test-object_foobaz'
        object_pred  = 'is liked by'

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Test #1')
        ptype2 = create_ptype(text='Test #2')
        ptype3 = create_ptype(text='Test #3')
        ptype4 = create_ptype(text='Test #4')
        ptype5 = create_ptype(text='Test #5')
        ptype6 = create_ptype(text='Test #6')

        builder = RelationType.objects.builder(
            id=subject_id, predicate=subject_pred, is_custom=True,
            models=[FakeContact, FakeOrganisation],
            properties=[str(ptype1.uuid), ptype2],
            forbidden_properties=[str(ptype4.uuid), ptype5],
        ).symmetric(
            id=object_id, predicate=object_pred,
            models=[FakeDocument],
            properties=[str(ptype3.uuid), ptype5],
            forbidden_properties=[str(ptype6.uuid), ptype2],
        )

        self.assertEqual(builder.id,        subject_id)
        self.assertEqual(builder.predicate, subject_pred)
        self.assertTrue(builder.is_custom)
        self.assertCountEqual([FakeContact, FakeOrganisation], [*builder.subject_models])
        self.assertCountEqual(
            [FakeContact, FakeOrganisation],
            [ct.model_class() for ct in builder.subject_ctypes],
        )
        self.assertCountEqual([ptype1, ptype2], [*builder.subject_properties])
        self.assertCountEqual([ptype4, ptype5], [*builder.subject_forbidden_properties])

        self.assertTrue(builder.symmetric_type.is_custom)

        rtype1 = builder.update_or_create()[0]
        self.assertEqual(rtype1.id,        subject_id)
        self.assertEqual(rtype1.predicate, subject_pred)
        self.assertTrue(rtype1.is_custom)

        rtype2 = rtype1.symmetric_type
        self.assertEqual(rtype2.id,        object_id)
        self.assertEqual(rtype2.predicate, object_pred)
        self.assertTrue(rtype2.is_custom)

        self.assertCountEqual(
            [FakeContact, FakeOrganisation], [*rtype1.subject_models],
        )
        self.assertCountEqual(
            [ptype1, ptype2], [*rtype1.subject_properties.all()],
        )
        self.assertCountEqual(
            [ptype4, ptype5], [*rtype1.subject_forbidden_properties.all()],
        )

        self.assertListEqual([FakeDocument], [*rtype2.subject_models])
        self.assertCountEqual([ptype3, ptype5], [*rtype2.subject_properties.all()])
        self.assertCountEqual([ptype6, ptype2], [*rtype2.subject_forbidden_properties.all()])

    def test_builder__update_or_create__ptype_constraints_cache(self):
        ptype = CremePropertyType.objects.create(text='Test #1')

        builder = RelationType.objects.builder(
            id='test-subject_foobaz', predicate='is liking', is_custom=True,
            properties=[ptype],
        ).symmetric(id='test-object_foobaz', predicate='is liked by')

        with self.assertNumQueries(0):
            self.assertListEqual([ptype], [*builder.subject_properties])

    def test_builder__update_or_create__disabled(self):
        builder = RelationType.objects.builder(
            id='test-subject_testproxy', predicate='knows',
            enabled=False,  # <==
        ).symmetric(id='test-object_testproxy', predicate='is known by')
        self.assertFalse(builder.enabled)

        sym_builder = builder.symmetric_type
        self.assertFalse(sym_builder.enabled)

        rtype1 = builder.update_or_create()[0]
        self.assertFalse(rtype1.enabled)
        self.assertFalse(rtype1.symmetric_type.enabled)

        builder.enabled = True
        self.assertTrue(builder.enabled)
        self.assertTrue(sym_builder.enabled)  # Synchronised

        # ---
        incomplete  = RelationType.objects.builder(
            id='test-subject_incomplete', predicate='I have no symmetric',
        )
        self.assertTrue(incomplete.enabled)

        with self.assertNoException():
            incomplete.enabled = False
        self.assertFalse(incomplete.enabled)

    def test_builder__update_or_create__is_internal(self):
        builder = RelationType.objects.builder(
            id='test-subject_testproxy', predicate='knows',
            is_internal=True,  # <==
        ).symmetric(id='test-object_testproxy', predicate='is known by')
        self.assertTrue(builder.is_internal)

        sym_builder = builder.symmetric_type
        self.assertTrue(sym_builder.is_internal)

        rtype1 = builder.update_or_create()[0]
        self.assertTrue(rtype1.is_internal)
        self.assertTrue(rtype1.symmetric_type.is_internal)

        builder.is_internal = False
        self.assertFalse(builder.is_internal)
        self.assertFalse(sym_builder.is_internal)  # Synchronised

        # ---
        incomplete  = RelationType.objects.builder(
            id='test-subject_incomplete', predicate='I have no symmetric',
        )
        self.assertFalse(incomplete.is_internal)

        with self.assertNoException():
            incomplete.is_internal = True
        self.assertTrue(incomplete.is_internal)

    def test_builder__update_or_create__is_copiable(self):
        proxy1 = RelationType.objects.builder(
            id='test-subject_copiable1', predicate='knows',
            is_copiable=False,  # <==
        ).symmetric(id='test-object_copiable1', predicate='is known by')
        self.assertFalse(proxy1.is_copiable)
        self.assertTrue(proxy1.symmetric_type.is_copiable)

        rtype1 = proxy1.update_or_create()[0]
        self.assertFalse(rtype1.is_copiable)
        self.assertTrue(rtype1.symmetric_type.is_copiable)

        # ---
        proxy2 = RelationType.objects.builder(
            id='test-subject_copiable2', predicate='knows well',
        ).symmetric(
            id='test-object_copiable2', predicate='is well known by',
            is_copiable=False,  # <==
        )
        self.assertTrue(proxy2.is_copiable)
        self.assertFalse(proxy2.symmetric_type.is_copiable)

        rtype2 = proxy2.update_or_create()[0]
        self.assertTrue(rtype2.is_copiable)
        self.assertFalse(rtype2.symmetric_type.is_copiable)

    def test_builder__update_or_create__minimal_display(self):
        proxy1 = RelationType.objects.builder(
            id='test-subject_min_display1', predicate='knows',
            minimal_display=True,  # <==
        ).symmetric(id='test-object_min_display1', predicate='is known by')
        self.assertTrue(proxy1.minimal_display)
        self.assertFalse(proxy1.symmetric_type.minimal_display)

        rtype1 = proxy1.update_or_create()[0]
        self.assertTrue(rtype1.minimal_display)
        self.assertFalse(rtype1.symmetric_type.minimal_display)

        # ---
        proxy2 = RelationType.objects.builder(
            id='test-subject_min_display2', predicate='knows well',
        ).symmetric(
            id='test-object_min_display2', predicate='is well known by',
            minimal_display=True,  # <==
        )
        self.assertFalse(proxy2.minimal_display)
        self.assertTrue(proxy2.symmetric_type.minimal_display)

        rtype2 = proxy2.update_or_create()[0]
        self.assertFalse(rtype2.minimal_display)
        self.assertTrue(rtype2.symmetric_type.minimal_display)

    def test_builder__get_or_create(self):
        subject_id = 'test-subject_foobar'
        subject_pred = 'is loving'
        object_id = 'test-object_foobar'
        object_pred  = 'is loved by'

        builder = RelationType.objects.builder(
            id=subject_id, predicate=subject_pred,
        ).symmetric(id=object_id, predicate=object_pred)

        rtype1, created1 = builder.get_or_create()
        self.assertIsInstance(rtype1, RelationType)
        self.assertEqual(subject_id, rtype1.pk)
        self.assertIs(created1, True)

        rtype1 = self.refresh(rtype1)
        self.assertEqual(rtype1.id,        subject_id)
        self.assertEqual(rtype1.predicate, subject_pred)
        self.assertFalse(rtype1.is_internal)
        self.assertFalse(rtype1.is_custom)
        self.assertTrue(rtype1.is_copiable)
        self.assertFalse(rtype1.minimal_display)
        self.assertTrue(rtype1.enabled)

        self.assertEqual(object_id, rtype1.symmetric_type_id)
        rtype2 = rtype1.symmetric_type
        self.assertEqual(rtype2.id,        object_id)
        self.assertEqual(rtype2.predicate, object_pred)
        self.assertFalse(rtype2.is_internal)
        self.assertFalse(rtype2.is_custom)
        self.assertTrue(rtype2.is_copiable)
        self.assertFalse(rtype2.minimal_display)
        self.assertTrue(rtype2.enabled)

        self.assertEqual(rtype1.symmetric_type, rtype2)
        self.assertEqual(rtype2.symmetric_type, rtype1)

        self.assertFalse([*rtype1.subject_models])
        self.assertFalse(rtype1.subject_properties.all())
        self.assertFalse(rtype1.subject_forbidden_properties.all())

        self.assertFalse([*rtype2.subject_models])
        self.assertFalse(rtype2.subject_properties.all())
        self.assertFalse(rtype2.subject_forbidden_properties.all())

        # ---
        builder.predicate = 'Other predicate'
        new_rtype1, created2 = builder.get_or_create()
        self.assertIs(created2, False)
        self.assertEqual(new_rtype1.predicate, subject_pred)

    def test_builder__get_or_create__constraints(self):
        "Constraints for ContentTypes & CremePropertyTypes."
        subject_id = 'test-subject_foobaz'
        subject_pred = 'is liking'
        object_id = 'test-object_foobaz'
        object_pred  = 'is liked by'

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Test #1')
        ptype2 = create_ptype(text='Test #2')
        ptype3 = create_ptype(text='Test #3')
        ptype4 = create_ptype(text='Test #4')
        ptype5 = create_ptype(text='Test #5')
        ptype6 = create_ptype(text='Test #6')

        builder = RelationType.objects.builder(
            id=subject_id, predicate=subject_pred, is_custom=True,
            models=[FakeContact, FakeOrganisation],
            properties=[str(ptype1.uuid), str(ptype2.uuid)],
            forbidden_properties=[str(ptype4.uuid), str(ptype5.uuid)],
        ).symmetric(
            id=object_id, predicate=object_pred,
            models=[FakeDocument],
            properties=[str(ptype3.uuid)],
            forbidden_properties=[str(ptype6.uuid)],
        )

        rtype1, created = builder.get_or_create()
        self.assertEqual(rtype1.id,        subject_id)
        self.assertEqual(rtype1.predicate, subject_pred)
        self.assertTrue(rtype1.is_custom)
        self.assertTrue(created)

        rtype2 = rtype1.symmetric_type
        self.assertEqual(rtype2.id,        object_id)
        self.assertEqual(rtype2.predicate, object_pred)
        self.assertTrue(rtype2.is_custom)

        self.assertCountEqual(
            [FakeContact, FakeOrganisation], [*rtype1.subject_models],
        )
        self.assertCountEqual(
            [ptype1, ptype2], [*rtype1.subject_properties.all()],
        )
        self.assertCountEqual(
            [ptype4, ptype5], [*rtype1.subject_forbidden_properties.all()],
        )

        self.assertListEqual([FakeDocument], [*rtype2.subject_models])
        self.assertListEqual([ptype3], [*rtype2.subject_properties.all()])
        self.assertListEqual([ptype6], [*rtype2.subject_forbidden_properties.all()])

        # ---
        builder.remove_subject_models(FakeContact)
        new_rtype1, created2 = builder.get_or_create()
        self.assertIs(created2, False)
        self.assertCountEqual(
            [FakeContact, FakeOrganisation], [*new_rtype1.subject_models],
        )

    def test_builder__get_or_create__disabled(self):
        builder = RelationType.objects.builder(
            id='test-subject_testproxy', predicate='knows',
            enabled=False,  # <==
        ).symmetric(id='test-object_testproxy', predicate='is known by')
        self.assertFalse(builder.enabled)

        rtype = builder.get_or_create()[0]
        self.assertFalse(rtype.enabled)
        self.assertFalse(rtype.symmetric_type.enabled)

    def test_builder__get_or_create__is_internal(self):
        builder = RelationType.objects.builder(
            id='test-subject_testproxy', predicate='knows',
            is_internal=True,  # <==
        ).symmetric(id='test-object_testproxy', predicate='is known by')
        self.assertTrue(builder.is_internal)

        rtype = builder.get_or_create()[0]
        self.assertTrue(rtype.is_internal)
        self.assertTrue(rtype.symmetric_type.is_internal)

    def test_builder__get_or_create__is_copiable(self):
        rtype1 = RelationType.objects.builder(
            id='test-subject_copiable1', predicate='knows',
            is_copiable=False,  # <==
        ).symmetric(id='test-object_copiable1', predicate='is known by').get_or_create()[0]
        self.assertFalse(rtype1.is_copiable)
        self.assertTrue(rtype1.symmetric_type.is_copiable)

        # ---
        rtype2 = RelationType.objects.builder(
            id='test-subject_copiable2', predicate='knows well',
        ).symmetric(
            id='test-object_copiable2', predicate='is well known by',
            is_copiable=False,  # <==
        ).get_or_create()[0]
        self.assertTrue(rtype2.is_copiable)
        self.assertFalse(rtype2.symmetric_type.is_copiable)

    def test_builder__is_custom(self):
        builder = RelationType.objects.builder(
            id='test-subject_testproxy', predicate='knows',
        ).symmetric(id='test-object_testproxy', predicate='is known by')
        self.assertFalse(builder.is_custom)

        sym_builder = builder.symmetric_type
        self.assertFalse(sym_builder.is_custom)

        builder.is_custom = True
        self.assertTrue(builder.is_custom)
        self.assertTrue(sym_builder.is_custom)  # Synchronised

        # ---
        incomplete  = RelationType.objects.builder(
            id='test-subject_incomplete', predicate='I have no symmetric',
        )
        self.assertFalse(incomplete.is_custom)

        with self.assertNoException():
            incomplete.is_custom = True
        self.assertTrue(incomplete.is_custom)

    def test_builder__get_or_create__minimal_display(self):
        rtype1 = RelationType.objects.builder(
            id='test-subject_min_display1', predicate='knows',
            minimal_display=True,  # <==
        ).symmetric(
            id='test-object_min_display1', predicate='is known by',
        ).get_or_create()[0]
        self.assertTrue(rtype1.minimal_display)
        self.assertFalse(rtype1.symmetric_type.minimal_display)

        # ---
        rtype2 = RelationType.objects.builder(
            id='test-subject_min_display2', predicate='knows well',
        ).symmetric(
            id='test-object_min_display2', predicate='is well known by',
            minimal_display=True,  # <==
        ).get_or_create()[0]
        self.assertFalse(rtype2.minimal_display)
        self.assertTrue(rtype2.symmetric_type.minimal_display)

    def test_builder__symmetric_errors(self):
        builder = RelationType.objects.builder(
            id='test-subject_err', predicate='knows',
        )

        with self.assertRaises(RuntimeError):
            builder.symmetric_type  # NOQA

        # update_or_create() ---
        with self.assertRaises(RuntimeError):
            builder.update_or_create()

        # Call twice ---
        builder.symmetric(id='test-object_err', predicate='whatever')
        with self.assertRaises(RuntimeError):
            builder.symmetric(id='test-object_err', predicate='is known by')

    def test_builder__edit_subject_models(self):
        builder = RelationType.objects.builder(
            id='test-subject_editconstr', predicate='Likes',
            models=[FakeContact],
        ).symmetric(
            id='test-object_editconstr', predicate='Is liked by',
        )

        builder.add_subject_models(FakeOrganisation, FakeDocument)
        self.assertCountEqual(
            [FakeContact, FakeOrganisation, FakeDocument],
            [*builder.subject_models],
        )

        builder.remove_subject_models(FakeOrganisation, FakeContact)
        self.assertListEqual([FakeDocument], [*builder.subject_models])

        sym = builder.symmetric_type
        sym.add_subject_models(FakeContact)
        self.assertListEqual([FakeContact], [*sym.subject_models])

    def test_builder__edit_properties(self):
        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Test #1')
        ptype2 = create_ptype(text='Test #2')
        ptype3 = create_ptype(text='Test #3')

        builder = RelationType.objects.builder(
            id='test-subject_editconstr',
            predicate='Likes',
            properties=[str(ptype1.uuid)],
            # forbidden_properties=[str(ptype4.uuid), str(ptype5.uuid)],
        ).symmetric(
            id='test-object_editconstr', predicate='Is liked by',
        )

        builder.add_subject_properties(str(ptype2.uuid), str(ptype3.uuid))
        self.assertCountEqual(
            [ptype1, ptype2, ptype3], [*builder.subject_properties],
        )

        builder.remove_subject_properties(str(ptype2.uuid), str(ptype1.uuid))
        self.assertListEqual([ptype3], [*builder.subject_properties])

        sym = builder.symmetric_type
        sym.add_subject_properties(str(ptype2.uuid))
        self.assertListEqual([ptype2], [*sym.subject_properties])

    def test_builder__edit_forbidden_properties(self):
        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Test #1')
        ptype2 = create_ptype(text='Test #2')
        ptype3 = create_ptype(text='Test #3')

        builder = RelationType.objects.builder(
            id='test-subject_editconstr',
            predicate='Likes',
            forbidden_properties=[str(ptype1.uuid)],
        ).symmetric(
            id='test-object_editconstr', predicate='Is liked by',
        )

        builder.add_subject_forbidden_properties(str(ptype2.uuid), str(ptype3.uuid))
        self.assertCountEqual(
            [ptype1, ptype2, ptype3], [*builder.subject_forbidden_properties],
        )

        builder.remove_subject_forbidden_properties(str(ptype2.uuid), str(ptype1.uuid))
        self.assertListEqual([ptype3], [*builder.subject_forbidden_properties])

        sym = builder.symmetric_type
        sym.add_subject_forbidden_properties(str(ptype2.uuid))
        self.assertListEqual([ptype2], [*sym.subject_forbidden_properties])


class RelationTypeTestCase(CremeTestCase):
    def test_delete(self):
        rtype = RelationType.objects.builder(
            id='test-subject_foobar', predicate='is loving',
        ).symmetric(id='test-object_foobar', predicate='is loved by').get_or_create()[0]

        rtype.delete()
        self.assertDoesNotExist(rtype)
        self.assertDoesNotExist(rtype.symmetric_type)

    def test_portable_key(self):
        rtype = RelationType.objects.builder(
            id='test-subject_foobar', predicate='is loving',
        ).symmetric(
            id='test-object_foobar', predicate='is loved by',
        ).get_or_create()[0]

        with self.assertNoException():
            key = rtype.portable_key()
        self.assertEqual(rtype.id, key)

        # ---
        with self.assertNoException():
            got_rtype = RelationType.objects.get_by_portable_key(key)
        self.assertEqual(rtype, got_rtype)

    def test_is_not_internal_or_die__success(self):
        rtype = RelationType.objects.builder(
            id='test-subject_disabled', predicate='is disabled',
        ).symmetric(id='test-object_disabled', predicate='what ever').get_or_create()[0]

        with self.assertNoException():
            rtype.is_not_internal_or_die()

    def test_is_not_internal_or_die__fail(self):
        rtype = RelationType.objects.builder(
            id='test-subject_internal', predicate='is internal', is_internal=True,
        ).symmetric(id='test-object_internal', predicate='is internal too').get_or_create()[0]

        with self.assertRaises(ConflictError):
            self.refresh(rtype).is_not_internal_or_die()

    def test_is_enabled_or_die(self):
        rtype = RelationType.objects.builder(
            id='test-subject_disabled', predicate='is disabled',
        ).symmetric(id='test-object_disabled', predicate='what ever').get_or_create()[0]

        with self.assertNoException():
            rtype.is_enabled_or_die()

        rtype.enabled = False
        rtype.save()

        with self.assertRaises(ConflictError):
            self.refresh(rtype).is_enabled_or_die()

    def test_is_compatible(self):
        rtype1 = RelationType.objects.builder(
            id='test-subject_manages', predicate='manages',
        ).symmetric(
            id='test-object_manages', predicate='is managed by',
            models=[FakeContact, FakeOrganisation],
        ).get_or_create()[0]
        rtype2 = rtype1.symmetric_type

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

    def test_is_compatible__no_prefetch(self):
        "Queries (no prefetch)."
        rtype = RelationType.objects.builder(
            id='test-subject_manages', predicate='manages', models=[FakeContact],
        ).symmetric(
            id='test-object_manages', predicate='is managed by', models=[FakeOrganisation],
        ).get_or_create()[0]

        contact_ct = ContentType.objects.get_for_model(FakeContact)

        with self.assertNumQueries(1):
            rtype.is_compatible(contact_ct)

        with self.assertNumQueries(1):
            rtype.is_compatible(contact_ct.id)

    def test_is_compatible__prefetch(self):
        "Queries (prefetch)."
        rtype = RelationType.objects.builder(
            id='test-subject_manages', predicate='manages', models=[FakeContact],
        ).symmetric(
            id='test-object_manages', predicate='is managed by', models=[FakeOrganisation],
        ).get_or_create()[0]

        contact_ct = ContentType.objects.get_for_model(FakeContact)

        with self.assertNumQueries(1):
            prefetch_related_objects([rtype], 'subject_ctypes')

        with self.assertNumQueries(0):
            rtype.is_compatible(contact_ct)

        with self.assertNumQueries(0):
            rtype.is_compatible(contact_ct.id)


class RelationManagerTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.get_root_user()

    def test_safe_create(self):
        rtype = RelationType.objects.builder(
            id='test-subject_challenge', predicate='challenges',
        ).symmetric(id='test-object_challenge', predicate='is challenged by').get_or_create()[0]

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        res = Relation.objects.safe_create(
            user=user, subject_entity=ryuko, type=rtype, object_entity=satsuki,
        )
        self.assertIsNone(res)

        rel = self.get_object_or_fail(Relation, type=rtype)
        self.assertEqual(rtype.id,             rel.type_id)
        self.assertEqual(ryuko.id,             rel.subject_entity_id)
        self.assertEqual(satsuki.entity_type,  rel.object_ctype)
        self.assertEqual(satsuki.id,           rel.object_entity_id)
        self.assertEqual(satsuki,              rel.real_object)
        self.assertEqual(user.id,              rel.user_id)
        self.assertEqual(rtype.symmetric_type, rel.symmetric_relation.type)

        # ---
        with self.assertNoException():
            Relation.objects.safe_create(
                user=user, subject_entity=ryuko, type=rtype, object_entity=satsuki,
            )

    def test_safe_get_or_create__user_instance(self):
        rtype = RelationType.objects.builder(
            id='test-subject_challenge', predicate='challenges',
        ).symmetric(id='test-object_challenge', predicate='is challenged by').get_or_create()[0]

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        rel1 = Relation.objects.safe_get_or_create(
            user=user, subject_entity=ryuko, type=rtype, object_entity=satsuki,
        )
        self.assertIsInstance(rel1, Relation)
        self.assertTrue(rel1.pk)
        self.assertEqual(rtype.id,             rel1.type_id)
        self.assertEqual(ryuko.id,             rel1.subject_entity_id)
        self.assertEqual(satsuki.entity_type,  rel1.object_ctype)
        self.assertEqual(satsuki.id,           rel1.object_entity_id)
        self.assertEqual(user.id,              rel1.user_id)
        self.assertEqual(rtype.symmetric_type, rel1.symmetric_relation.type)

        # ---
        with self.assertNoException():
            rel2 = Relation.objects.safe_get_or_create(
                user=user, subject_entity=ryuko, type=rtype, object_entity=satsuki,
            )

        self.assertEqual(rel1, rel2)

    def test_manager_safe_get_or_create__user_id(self):
        "Give user ID (not user instance)."
        rtype = RelationType.objects.builder(
            id='test-subject_challenge', predicate='challenges',
        ).symmetric(id='test-object_challenge', predicate='is challenged by').get_or_create()[0]

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        rel1 = Relation.objects.safe_get_or_create(
            user_id=user.id, subject_entity=ryuko, type=rtype, object_entity=satsuki,
        )
        self.assertIsInstance(rel1, Relation)
        self.assertTrue(rel1.pk)
        self.assertEqual(rtype.id,             rel1.type_id)
        self.assertEqual(ryuko.id,             rel1.subject_entity_id)
        self.assertEqual(satsuki.id,           rel1.object_entity_id)
        self.assertEqual(user.id,              rel1.user_id)
        self.assertEqual(rtype.symmetric_type, rel1.symmetric_relation.type)

        # ---
        with self.assertNoException():
            rel2 = Relation.objects.safe_get_or_create(
                user_id=user.id, subject_entity=ryuko, type=rtype, object_entity=satsuki,
            )

        self.assertEqual(rel1, rel2)

    def test_safe_multi_save(self):
        "Create several relation."
        rtype1 = RelationType.objects.builder(
            id='test-subject_challenge', predicate='challenges',
        ).symmetric(id='test-object_challenge', predicate='is challenged by').get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_foobar', predicate='loves',
        ).symmetric(id='test-object_foobar', predicate='is loved by').get_or_create()[0]

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        count = Relation.objects.safe_multi_save([
            Relation(user=user, subject_entity=ryuko, type=rtype1, real_object=satsuki),
            Relation(user=user, subject_entity=ryuko, type=rtype2, object_entity=satsuki),
        ])

        self.assertEqual(2, count)

        rel1 = self.get_object_or_fail(Relation, type=rtype1)
        self.assertEqual(ryuko.id,              rel1.subject_entity_id)
        self.assertEqual(satsuki.entity_type,   rel1.object_ctype)
        self.assertEqual(satsuki.id,            rel1.object_entity_id)
        self.assertEqual(user.id,               rel1.user_id)
        self.assertEqual(rtype1.symmetric_type, rel1.symmetric_relation.type)

        rel2 = self.get_object_or_fail(Relation, type=rtype2)
        self.assertEqual(ryuko.id,              rel2.subject_entity_id)
        self.assertEqual(satsuki.id,            rel2.object_entity_id)
        self.assertEqual(user.id,               rel2.user_id)
        self.assertEqual(rtype2.symmetric_type, rel2.symmetric_relation.type)

    def test_safe_multi_save__duplicates(self):
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
                user=user, subject_entity=ryuko, type=rtype, real_object=satsuki,
            )

        with self.assertNoException():
            count = Relation.objects.safe_multi_save([build_rel(), build_rel()])

        rel = self.get_object_or_fail(Relation, type=rtype)
        self.assertEqual(ryuko.id,   rel.subject_entity_id)
        self.assertEqual(satsuki,    rel.real_object)
        self.assertEqual(user.id,    rel.user_id)

        self.assertEqual(1, count)

    def test_safe_multi_save__existing_relations(self):
        "Avoid creating existing relations."
        rtype1 = RelationType.objects.builder(
            id='test-subject_challenge', predicate='challenges',
        ).symmetric(id='test-object_challenge', predicate='is challenged by').get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_foobar', predicate='loves',
        ).symmetric(id='test-object_foobar', predicate='is loved by').get_or_create()[0]

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        def build_rel1():
            return Relation(
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

    def test_safe_multi_save__empty(self):
        "No query if no relations."
        with self.assertNumQueries(0):
            count = Relation.objects.safe_multi_save([])

        self.assertEqual(0, count)

    def test_safe_multi_save__check_existing(self):
        "Argument <check_existing>."
        rtype1 = RelationType.objects.builder(
            id='test-subject_challenge', predicate='challenges',
        ).symmetric(id='test-object_challenge', predicate='is challenged by').get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_foobar', predicate='loves',
        ).symmetric(id='test-object_foobar', predicate='is loved by').get_or_create()[0]

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        build_rel = partial(Relation, user=user, subject_entity=ryuko, real_object=satsuki)

        with CaptureQueriesContext() as ctxt1:
            Relation.objects.safe_multi_save(
                [build_rel(type=rtype1)], check_existing=True,
            )

        with CaptureQueriesContext() as ctxt2:
            Relation.objects.safe_multi_save(
                [build_rel(type=rtype2)], check_existing=False,
            )

        self.assertHaveRelation(subject=ryuko, type=rtype1.id, object=satsuki)
        self.assertHaveRelation(subject=ryuko, type=rtype2.id, object=satsuki)

        self.assertEqual(len(ctxt1), len(ctxt2) + 1)


class RelationTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.get_root_user()

    def test_create(self):
        user = self.user

        rtype = RelationType.objects.builder(
            id='test-subject_foobar', predicate='is loving',
        ).symmetric(id='test-object_foobar', predicate='is loved by').get_or_create()[0]

        with self.assertNoException():
            entity1 = CremeEntity.objects.create(user=user)
            entity2 = CremeEntity.objects.create(user=user)

            relation = Relation.objects.create(
                user=user, type=rtype, subject_entity=entity1, real_object=entity2,
            )

        sym = relation.symmetric_relation
        self.assertEqual(sym.type,           rtype.symmetric_type)
        self.assertEqual(sym.subject_entity, entity2)
        self.assertEqual(sym.object_entity,  entity1)

    def test_error(self):
        "BEWARE: don't do this ! Bad usage of Relations."
        rtype = RelationType.objects.builder(
            id='test-subject_foobar', predicate='is loving',
        ).symmetric(id='test-object_foobar', predicate='is loved by').get_or_create()[0]

        create_entity = partial(CremeEntity.objects.create, user=self.user)
        relation = Relation.objects.create(
            user=self.user, type=rtype,
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

    def test_clean__no_constraint(self):
        rtype = RelationType.objects.builder(
            id='test-subject_loves', predicate='loves',
        ).symmetric(id='test-object_loves', predicate='is loved by').get_or_create()[0]

        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        ryuko   = create_contact(first_name='Ryuko',   last_name='Matoi')
        satsuki = create_contact(first_name='Satsuki', last_name='Kiryuin')

        rel = Relation(user=user, subject_entity=ryuko, real_object=satsuki, type=rtype)

        with self.assertNoException():
            rel.clean()

    def test_clean__content_type_constraints(self):
        rtype = RelationType.objects.builder(
            id='test-subject_loves', predicate='loves', models=[FakeContact],
        ).symmetric(
            id='test-object_loves', predicate='is loved by', models=[FakeContact],
        ).get_or_create()[0]

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
        self.assertValidationError(
            cm1.exception,
            messages=msg % {
                'entity': orga,
                'model': 'Test Organisation',
                'predicate': rtype.symmetric_type.predicate,
            },
        )

        # ---
        rel3 = Relation(user=user, subject_entity=orga, real_object=satsuki, type=rtype)
        with self.assertRaises(ValidationError) as cm2:
            rel3.clean()

        self.assertValidationError(
            cm2.exception,
            messages=msg % {
                'entity': orga,
                'model': 'Test Organisation',
                'predicate': rtype.predicate,
            },
        )

    def test_clean__property_constraints(self):
        "Mandatory CremeProperties constraints."
        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is strong')
        ptype2 = create_ptype(text='Is cute')
        ptype3 = create_ptype(text='Is smart')

        rtype = RelationType.objects.builder(
            id='test-subject_loves', predicate='loves',
            models=[FakeContact], properties=[ptype1, ptype2],
        ).symmetric(
            id='test-object_loves', predicate='is loved by',
            models=[FakeContact], properties=[ptype3],
        ).get_or_create()[0]

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

        self.assertValidationError(
            cm2.exception,
            messages=msg % {
                'entity': satsuki,
                'property': ptype3.text,
                'predicate': rtype.symmetric_type.predicate,
            },
        )

        # ---
        CremeProperty.objects.create(creme_entity=satsuki, type=ptype3)
        satsuki = self.refresh(satsuki)

        rel3 = Relation(user=user, subject_entity=ryuko, real_object=satsuki, type=rtype)
        with self.assertNoException():
            rel3.clean()

    def test_clean__forbidden_properties(self):
        "Forbidden CremeProperties constraints."
        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is strong')
        ptype2 = create_ptype(text='Is cute')
        ptype3 = create_ptype(text='Is smart')

        rtype = RelationType.objects.builder(
            id='test-subject_loves', predicate='loves', forbidden_properties=[ptype2],
        ).symmetric(
            id='test-object_loves', predicate='is loved by', forbidden_properties=[ptype3],
        ).get_or_create()[0]

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
        self.assertValidationError(
            cm1.exception,
            messages=msg % {
                'entity': satsuki,
                'property': ptype3.text,
                'predicate': rtype.symmetric_type.predicate,
            },
        )

        # ---
        CremeProperty.objects.create(creme_entity=ryuko, type=ptype2)
        ryuko = self.refresh(ryuko)

        rel3 = Relation(user=user, subject_entity=ryuko, real_object=satsuki, type=rtype)
        with self.assertRaises(ValidationError) as cm2:
            rel3.clean()

        self.assertValidationError(
            cm2.exception,
            messages=msg % {
                'entity': ryuko,
                'property': ptype2.text,
                'predicate': rtype.predicate,
            },
        )

    def test_clean_subject_entity__properties(self):
        "Mandatory Property + argument 'property_types'."
        ptype = CremePropertyType.objects.create(text='Is cute')
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

        self.assertValidationError(
            cm.exception,
            messages=Relation.error_messages['missing_subject_property'] % {
                'entity': ryuko,
                'property': ptype.text,
                'predicate': rtype.predicate,
            },
        )

        # --
        with self.assertNoException():
            rel.clean_subject_entity(property_types=[ptype])

    def test_clean_subject_entity__forbidden_properties(self):
        "Forbidden Property + argument 'property_types'."
        ptype = CremePropertyType.objects.create(text='Is not cute')
        rtype = RelationType.objects.builder(
            id='test-subject_loved', predicate='is loved by',
            forbidden_properties=[ptype],
        ).symmetric(id='test-object_loved', predicate='loves').get_or_create()[0]

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
        self.assertValidationError(cm1.exception, messages=message)

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

        self.assertValidationError(cm2.exception, messages=message)
