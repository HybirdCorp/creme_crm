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
    def test_manager_smart_update_or_create01(self):
        # pk = 'test-prop_foobar'
        uid = 'f4dc2004-30d1-46b2-95e0-7164bf286969'
        text = 'is delicious'

        # ptype = CremePropertyType.objects.smart_update_or_create(str_pk=pk, text=text)
        ptype = CremePropertyType.objects.smart_update_or_create(uuid=uid, text=text)

        self.assertIsInstance(ptype, CremePropertyType)
        # self.assertEqual(pk, ptype.id)
        self.assertEqual(uid, ptype.uuid)
        self.assertEqual('', ptype.app_label)
        self.assertEqual(text, ptype.text)
        self.assertFalse(ptype.is_custom)
        self.assertTrue(ptype.is_copiable)
        self.assertTrue(ptype.enabled)
        self.assertFalse(ptype.subject_ctypes.all())
        self.assertFalse([*ptype.subject_models])

    def test_manager_smart_update_or_create02(self):
        "ContentTypes& app label."
        # pk = 'test-prop_foo'
        uid = '73b2c0b5-10a8-443a-9e07-1f2398e889ea'
        text = 'is wonderful'
        label = 'creme_core'

        get_ct = ContentType.objects.get_for_model
        orga_ct = get_ct(FakeOrganisation)
        ptype = CremePropertyType.objects.smart_update_or_create(
            # str_pk=pk,
            uuid=uid,
            text=text,
            app_label=label,
            is_copiable=False,
            is_custom=True,
            subject_ctypes=[FakeContact, orga_ct],
        )

        self.assertEqual(label, ptype.app_label)
        self.assertTrue(ptype.is_custom)
        self.assertFalse(ptype.is_copiable)
        self.assertCountEqual(
            [get_ct(FakeContact), orga_ct], [*ptype.subject_ctypes.all()],
        )
        self.assertCountEqual(
            [FakeContact, FakeOrganisation], [*ptype.subject_models],
        )

    def test_manager_smart_update_or_create03(self):
        "Update existing."
        # pk = 'test-prop_foobar'
        uid = '85df6868-beee-41b3-a263-a139f6dfde27'
        create_ptype = CremePropertyType.objects.smart_update_or_create
        # create_ptype(str_pk=pk, text='is delicious', subject_ctypes=[FakeOrganisation])
        create_ptype(uuid=uid, text='is delicious', subject_ctypes=[FakeOrganisation])

        text = 'is very delicious'
        ptype = create_ptype(
            # str_pk=pk,
            uuid=uid,
            text=text,
            is_copiable=False,
            is_custom=True,
            subject_ctypes=[FakeContact],
        )

        self.assertEqual(text, ptype.text)
        self.assertTrue(ptype.is_custom)
        self.assertFalse(ptype.is_copiable)
        self.assertListEqual([FakeContact], [*ptype.subject_models])

    # def test_manager_smart_update_or_create04(self):
    #     "Generate pk."
    #     pk = 'test-prop_foobar'
    #     create_ptype = CremePropertyType.objects.smart_update_or_create
    #     create_ptype(str_pk=pk, text='is delicious')
    #
    #     text = 'is wonderful'
    #     ptype = create_ptype(str_pk=pk, text=text, generate_pk=True)
    #     self.assertEqual(pk + '1', ptype.id)
    #     self.assertEqual(text, ptype.text)
    def test_manager_smart_update_or_create04(self):
        "Generate uuid."
        create_ptype = CremePropertyType.objects.smart_update_or_create
        text1 = 'is delicious'
        ptype1 = create_ptype(
            text=text1,
            is_custom=True,
            is_copiable=False,
        )
        self.assertTrue(ptype1.uuid)
        self.assertEqual(text1, ptype1.text)
        self.assertEqual('', ptype1.app_label)
        self.assertTrue(ptype1.is_custom)
        self.assertFalse(ptype1.is_copiable)
        self.assertFalse([*ptype1.subject_models])

        text2 = 'is yummy'
        label2 = 'documents'
        ptype2 = create_ptype(
            text=text2,
            app_label=label2,
            is_custom=False,
            is_copiable=True,
            subject_ctypes=[FakeContact],
        )
        self.assertTrue(ptype2.uuid)
        self.assertEqual(text2, ptype2.text)
        self.assertEqual(label2, ptype2.app_label)
        self.assertFalse(ptype2.is_custom)
        self.assertTrue(ptype2.is_copiable)
        self.assertListEqual([FakeContact], [*ptype2.subject_models])

        self.assertNotEqual(ptype1.uuid, ptype2.uuid)

    def test_manager_compatible(self):
        create_ptype = CremePropertyType.objects.smart_update_or_create
        # ptype1 = create_ptype(str_pk='test-prop_delicious', text='is delicious')
        # ptype2 = create_ptype(str_pk='test-prop_happy',     text='is happy')
        # ptype3 = create_ptype(
        #     str_pk='test-prop_wonderful', text='is wonderful',
        #     subject_ctypes=[FakeContact],
        # )
        ptype1 = create_ptype(text='is delicious')
        ptype2 = create_ptype(text='is happy')
        ptype3 = create_ptype(text='is wonderful', subject_ctypes=[FakeContact])

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
    def test_create(self):
        text = 'is delicious'

        with self.assertNoException():
            # ptype = CremePropertyType.objects.smart_update_or_create(
            #     str_pk='test-prop_foobar', text=text,
            # )
            ptype = CremePropertyType.objects.create(text=text)
            entity = CremeEntity.objects.create(user=self.get_root_user())
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

        # ptype = CremePropertyType.objects.smart_update_or_create(
        #     str_pk='test-prop_foobar', text=text,
        # )
        ptype = CremePropertyType.objects.create(text=text)
        entity = CremeEntity.objects.create(user=self.get_root_user())

        CremeProperty.objects.safe_create(type=ptype, creme_entity=entity)
        self.assertHasProperty(entity=entity, ptype=ptype)

        with self.assertNoException():
            CremeProperty.objects.safe_create(type=ptype, creme_entity=entity)

    def test_manager_safe_get_or_create(self):
        text = 'is happy'

        # ptype  = CremePropertyType.objects.smart_update_or_create(
        #     str_pk='test-prop_foobar', text=text,
        # )
        ptype  = CremePropertyType.objects.create(text=text)
        entity = CremeEntity.objects.create(user=self.get_root_user())

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
        # create_ptype = CremePropertyType.objects.smart_update_or_create
        # ptype1 = create_ptype(str_pk='test-prop_delicious', text='is delicious')
        # ptype2 = create_ptype(str_pk='test-prop_happy',     text='is happy')
        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='is delicious')
        ptype2 = create_ptype(text='is happy')

        user = self.get_root_user()
        entity1 = CremeEntity.objects.create(user=user)
        entity2 = CremeEntity.objects.create(user=user)

        count = CremeProperty.objects.safe_multi_save([
            CremeProperty(type=ptype1, creme_entity=entity1),
            CremeProperty(type=ptype2, creme_entity=entity1),
            CremeProperty(type=ptype2, creme_entity=entity2),
        ])

        self.assertEqual(3, count)

        self.assertHasProperty(entity=entity1, ptype=ptype1)
        self.assertHasProperty(entity=entity1, ptype=ptype2)
        self.assertHasProperty(entity=entity2, ptype=ptype2)

    def test_manager_safe_multi_save02(self):
        "De-duplicates arguments."
        # create_ptype = CremePropertyType.objects.smart_update_or_create
        # ptype1 = create_ptype(str_pk='test-prop_delicious', text='is delicious')
        # ptype2 = create_ptype(str_pk='test-prop_happy',     text='is happy')
        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='is delicious')
        ptype2 = create_ptype(text='is happy')

        entity = CremeEntity.objects.create(user=self.get_root_user())

        count = CremeProperty.objects.safe_multi_save([
            CremeProperty(type=ptype1, creme_entity=entity),
            CremeProperty(type=ptype2, creme_entity=entity),
            CremeProperty(type=ptype1, creme_entity=entity),  # <=== duplicate
        ])

        self.assertEqual(2, count)

        self.assertHasProperty(entity=entity, ptype=ptype1)
        self.assertHasProperty(entity=entity, ptype=ptype2)

    def test_manager_safe_multi_save03(self):
        "Avoid creating existing properties."
        # create_ptype = CremePropertyType.objects.smart_update_or_create
        # ptype1 = create_ptype(str_pk='test-prop_delicious', text='is delicious')
        # ptype2 = create_ptype(str_pk='test-prop_happy',     text='is happy')
        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='is delicious')
        ptype2 = create_ptype(text='is happy')

        entity = CremeEntity.objects.create(user=self.get_root_user())

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
        self.assertHasProperty(entity=entity, ptype=ptype2)

    def test_manager_safe_multi_save04(self):
        "No query if no properties"
        with self.assertNumQueries(0):
            count = CremeProperty.objects.safe_multi_save([])

        self.assertEqual(0, count)

    def test_manager_safe_multi_save05(self):
        "Argument <check_existing>."
        # create_ptype = CremePropertyType.objects.smart_update_or_create
        # ptype1 = create_ptype(str_pk='test-prop_delicious', text='is delicious')
        # ptype2 = create_ptype(str_pk='test-prop_happy',     text='is happy')
        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='is delicious')
        ptype2 = create_ptype(text='is happy')

        entity = CremeEntity.objects.create(user=self.get_root_user())

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

        self.assertHasProperty(entity=entity, ptype=ptype1)
        self.assertHasProperty(entity=entity, ptype=ptype2)

        self.assertEqual(len(ctxt1), len(ctxt2) + 1)
