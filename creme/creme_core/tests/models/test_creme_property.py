# -*- coding: utf-8 -*-

try:
    from django.db import IntegrityError

    from ..base import CremeTestCase
    from creme.creme_core.models import CremeEntity, CremePropertyType, CremeProperty
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class CremePropertyTestCase(CremeTestCase):
    def setUp(self):
        self.login()

    def test_create(self):
        text = 'is delicious'

        with self.assertNoException():
            ptype  = CremePropertyType.create(str_pk='test-prop_foobar', text=text)
            entity = CremeEntity.objects.create(user=self.user)
            CremeProperty.objects.create(type=ptype, creme_entity=entity)

        self.assertEqual(text, ptype.text)

        # Uniqueness
        with self.assertRaises(IntegrityError):
            CremeProperty.objects.create(type=ptype, creme_entity=entity)

    def test_manager_safe_create(self):
        text = 'is happy'

        ptype  = CremePropertyType.create(str_pk='test-prop_foobar', text=text)
        entity = CremeEntity.objects.create(user=self.user)

        CremeProperty.objects.safe_create(type=ptype, creme_entity=entity)
        self.get_object_or_fail(CremeProperty, type=ptype.id, creme_entity=entity.id)

        with self.assertNoException():
            CremeProperty.objects.safe_create(type=ptype, creme_entity=entity)

    def test_manager_safe_get_or_create(self):
        text = 'is happy'

        ptype  = CremePropertyType.create(str_pk='test-prop_foobar', text=text)
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
        create_ptype = CremePropertyType.create
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
        "De-duplicates arguments"
        create_ptype = CremePropertyType.create
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
        "Avoid creating existing properties"
        create_ptype = CremePropertyType.create
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
