# -*- coding: utf-8 -*-

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models.query import QuerySet
from django.utils.translation import gettext as _

from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    FakeContact,
    FakeOrganisation,
)
from creme.creme_core.utils.profiling import CaptureQueriesContext

from ..base import CremeTestCase


class CremePropertyTypeTestCase(CremeTestCase):
    def test_create01(self):  # DEPRECATED
        pk = 'test-prop_foobar'
        text = 'is delicious'

        ptype = CremePropertyType.create(str_pk=pk, text=text)

        self.assertIsInstance(ptype, CremePropertyType)
        self.assertEqual(pk, ptype.id)
        self.assertEqual(text, ptype.text)
        self.assertFalse(ptype.is_custom)
        self.assertTrue(ptype.is_copiable)
        self.assertFalse(ptype.subject_ctypes.all())

    def test_create02(self):  # DEPRECATED
        "ContentTypes."
        pk = 'test-prop_foo'
        text = 'is wonderful'

        get_ct = ContentType.objects.get_for_model
        orga_ct = get_ct(FakeOrganisation)
        ptype = CremePropertyType.create(
            str_pk=pk, text=text,
            is_copiable=False,
            is_custom=True,
            subject_ctypes=[FakeContact, orga_ct],
        )

        self.assertTrue(ptype.is_custom)
        self.assertFalse(ptype.is_copiable)
        self.assertSetEqual(
            {get_ct(FakeContact), orga_ct}, {*ptype.subject_ctypes.all()},
        )

    def test_create03(self):  # DEPRECATED
        "Update existing."
        pk = 'test-prop_foobar'
        CremePropertyType.create(
            str_pk=pk, text='is delicious', subject_ctypes=[FakeOrganisation],
        )

        text = 'is very delicious'
        ptype = CremePropertyType.create(
            str_pk=pk,
            text=text,
            is_copiable=False,
            is_custom=True,
            subject_ctypes=[FakeContact],
        )

        self.assertEqual(text, ptype.text)
        self.assertTrue(ptype.is_custom)
        self.assertFalse(ptype.is_copiable)
        self.assertListEqual(
            [FakeContact],
            [ct.model_class() for ct in ptype.subject_ctypes.all()],
        )

    def test_create04(self):  # DEPRECATED
        "Generate pk."
        pk = 'test-prop_foobar'
        CremePropertyType.create(str_pk=pk, text='is delicious')

        text = 'is wonderful'
        ptype = CremePropertyType.create(str_pk=pk, text=text, generate_pk=True)
        self.assertEqual(pk + '1', ptype.id)
        self.assertEqual(text, ptype.text)

    def test_manager_smart_update_or_create01(self):
        pk = 'test-prop_foobar'
        text = 'is delicious'

        ptype = CremePropertyType.objects.smart_update_or_create(str_pk=pk, text=text)

        self.assertIsInstance(ptype, CremePropertyType)
        self.assertEqual(pk, ptype.id)
        self.assertEqual(text, ptype.text)
        self.assertFalse(ptype.is_custom)
        self.assertTrue(ptype.is_copiable)
        self.assertTrue(ptype.enabled)
        self.assertFalse(ptype.subject_ctypes.all())

    def test_manager_smart_update_or_create02(self):
        "ContentTypes."
        pk = 'test-prop_foo'
        text = 'is wonderful'

        get_ct = ContentType.objects.get_for_model
        orga_ct = get_ct(FakeOrganisation)
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk=pk, text=text,
            is_copiable=False,
            is_custom=True,
            subject_ctypes=[FakeContact, orga_ct],
        )

        self.assertTrue(ptype.is_custom)
        self.assertFalse(ptype.is_copiable)
        self.assertSetEqual(
            {get_ct(FakeContact), orga_ct}, {*ptype.subject_ctypes.all()},
        )

    def test_manager_smart_update_or_create03(self):
        "Update existing."
        pk = 'test-prop_foobar'
        create_ptype = CremePropertyType.objects.smart_update_or_create
        create_ptype(str_pk=pk, text='is delicious', subject_ctypes=[FakeOrganisation])

        text = 'is very delicious'
        ptype = create_ptype(
            str_pk=pk,
            text=text,
            is_copiable=False,
            is_custom=True,
            subject_ctypes=[FakeContact],
        )

        self.assertEqual(text, ptype.text)
        self.assertTrue(ptype.is_custom)
        self.assertFalse(ptype.is_copiable)
        self.assertListEqual(
            [FakeContact],
            [ct.model_class() for ct in ptype.subject_ctypes.all()],
        )

    def test_manager_smart_update_or_create04(self):
        "Generate pk."
        pk = 'test-prop_foobar'
        create_ptype = CremePropertyType.objects.smart_update_or_create
        create_ptype(str_pk=pk, text='is delicious')

        text = 'is wonderful'
        ptype = create_ptype(str_pk=pk, text=text, generate_pk=True)
        self.assertEqual(pk + '1', ptype.id)
        self.assertEqual(text, ptype.text)

    def test_manager_compatible(self):
        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-prop_delicious', text='is delicious')
        ptype2 = create_ptype(str_pk='test-prop_happy',     text='is happy')
        ptype3 = create_ptype(
            str_pk='test-prop_wonderful', text='is wonderful',
            subject_ctypes=[FakeContact],
        )

        # ---
        ptypes1 = CremePropertyType.objects.compatible(FakeContact)
        self.assertIsInstance(ptypes1, QuerySet)
        self.assertEqual(CremePropertyType, ptypes1.model)

        ptype_ids1 = {pt.id for pt in ptypes1}
        self.assertIn(ptype1.id, ptype_ids1)
        self.assertIn(ptype2.id, ptype_ids1)
        self.assertIn(ptype3.id, ptype_ids1)

        self.assertQuerysetSQLEqual(
            ptypes1,
            CremePropertyType.objects.compatible(
                ContentType.objects.get_for_model(FakeContact)
            )
        )

        # ---
        ptypes2 = CremePropertyType.objects.compatible(FakeOrganisation)
        ptype_ids2 = {pt.id for pt in ptypes2}
        self.assertIn(ptype1.id, ptype_ids2)
        self.assertIn(ptype2.id, ptype_ids2)
        self.assertNotIn(ptype3.id, ptype_ids2)


class CremePropertyTestCase(CremeTestCase):
    def setUp(self):
        super().setUp()
        self.login()

    def test_create(self):
        text = 'is delicious'

        with self.assertNoException():
            ptype = CremePropertyType.objects.smart_update_or_create(
                str_pk='test-prop_foobar', text=text,
            )
            entity = CremeEntity.objects.create(user=self.user)
            CremeProperty.objects.create(type=ptype, creme_entity=entity)

        self.assertEqual(text, ptype.text)

        # Uniqueness
        prop02 = CremeProperty(type=ptype, creme_entity=entity)
        with self.assertRaises(ValidationError) as cm:
            prop02.full_clean()

        self.assertDictEqual(
            {
                '__all__': [
                    _('%(model_name)s with this %(field_labels)s already exists.') % {
                        'model_name': _('Property'),
                        'field_labels': f"{_('Type of property')} {_('and')} {_('Entity')}",
                    }
                ],
            },
            cm.exception.message_dict,
        )

        with self.assertRaises(IntegrityError):
            prop02.save()

    def test_manager_safe_create(self):
        text = 'is happy'

        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_foobar', text=text,
        )
        entity = CremeEntity.objects.create(user=self.user)

        CremeProperty.objects.safe_create(type=ptype, creme_entity=entity)
        self.get_object_or_fail(CremeProperty, type=ptype.id, creme_entity=entity.id)

        with self.assertNoException():
            CremeProperty.objects.safe_create(type=ptype, creme_entity=entity)

    def test_manager_safe_get_or_create(self):
        text = 'is happy'

        ptype  = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_foobar', text=text,
        )
        entity = CremeEntity.objects.create(user=self.user)

        prop1 = CremeProperty.objects.safe_get_or_create(type=ptype, creme_entity=entity)
        self.assertIsInstance(prop1, CremeProperty)
        self.assertTrue(prop1.pk)
        self.assertEqual(ptype.id,  prop1.type_id)
        self.assertEqual(entity.id, prop1.creme_entity_id)

        # ---
        with self.assertNoException():
            prop2 = CremeProperty.objects.safe_get_or_create(
                type=ptype, creme_entity=entity,
            )

        self.assertEqual(prop1, prop2)

    def test_manager_safe_multi_save01(self):
        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-prop_delicious', text='is delicious')
        ptype2 = create_ptype(str_pk='test-prop_happy',     text='is happy')

        entity1 = CremeEntity.objects.create(user=self.user)
        entity2 = CremeEntity.objects.create(user=self.user)

        count = CremeProperty.objects.safe_multi_save([
            CremeProperty(type=ptype1, creme_entity=entity1),
            CremeProperty(type=ptype2, creme_entity=entity1),
            CremeProperty(type=ptype2, creme_entity=entity2),
        ])

        self.assertEqual(3, count)

        self.get_object_or_fail(CremeProperty, type=ptype1.id, creme_entity=entity1.id)
        self.get_object_or_fail(CremeProperty, type=ptype2.id, creme_entity=entity1.id)
        self.get_object_or_fail(CremeProperty, type=ptype2.id, creme_entity=entity2.id)

    def test_manager_safe_multi_save02(self):
        "De-duplicates arguments."
        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-prop_delicious', text='is delicious')
        ptype2 = create_ptype(str_pk='test-prop_happy',     text='is happy')

        entity = CremeEntity.objects.create(user=self.user)

        count = CremeProperty.objects.safe_multi_save([
            CremeProperty(type=ptype1, creme_entity=entity),
            CremeProperty(type=ptype2, creme_entity=entity),
            CremeProperty(type=ptype1, creme_entity=entity),  # <=== duplicate
        ])

        self.assertEqual(2, count)

        self.get_object_or_fail(CremeProperty, type=ptype1.id, creme_entity=entity.id)
        self.get_object_or_fail(CremeProperty, type=ptype2.id, creme_entity=entity.id)

    def test_manager_safe_multi_save03(self):
        "Avoid creating existing properties."
        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-prop_delicious', text='is delicious')
        ptype2 = create_ptype(str_pk='test-prop_happy',     text='is happy')

        entity = CremeEntity.objects.create(user=self.user)

        def build_prop1():
            return CremeProperty(type=ptype1, creme_entity=entity)

        prop1 = build_prop1()
        prop1.save()

        count = CremeProperty.objects.safe_multi_save([
            build_prop1(),
            CremeProperty(type=ptype2, creme_entity=entity),
        ])

        self.assertEqual(1, count)

        self.assertStillExists(prop1)
        self.get_object_or_fail(CremeProperty, type=ptype2.id, creme_entity=entity.id)

    def test_manager_safe_multi_save04(self):
        "No query if no properties"
        with self.assertNumQueries(0):
            count = CremeProperty.objects.safe_multi_save([])

        self.assertEqual(0, count)

    def test_manager_safe_multi_save05(self):
        "Argument <check_existing>."
        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-prop_delicious', text='is delicious')
        ptype2 = create_ptype(str_pk='test-prop_happy',     text='is happy')

        entity = CremeEntity.objects.create(user=self.user)

        with CaptureQueriesContext() as ctxt1:
            CremeProperty.objects.safe_multi_save(
                [CremeProperty(type=ptype1, creme_entity=entity)],
                check_existing=True,
            )

        with CaptureQueriesContext() as ctxt2:
            CremeProperty.objects.safe_multi_save(
                [CremeProperty(type=ptype2, creme_entity=entity)],
                check_existing=False,
            )

        self.get_object_or_fail(CremeProperty, type=ptype1.id, creme_entity=entity.id)
        self.get_object_or_fail(CremeProperty, type=ptype2.id, creme_entity=entity.id)

        self.assertEqual(len(ctxt1), len(ctxt2) + 1)
