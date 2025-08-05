from uuid import uuid4

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
from ..fake_models import FakeActivity


class CremePropertyTypeTestCase(CremeTestCase):
    # def test_manager_smart_update_or_create01(self):  # DEPRECATED
    #     uid = 'f4dc2004-30d1-46b2-95e0-7164bf286969'
    #     text = 'is delicious'
    #
    #     ptype = CremePropertyType.objects.smart_update_or_create(uuid=uid, text=text)
    #
    #     self.assertIsInstance(ptype, CremePropertyType)
    #     self.assertEqual(uid, ptype.uuid)
    #     self.assertEqual('', ptype.app_label)
    #     self.assertEqual(text, ptype.text)
    #     self.assertFalse(ptype.is_custom)
    #     self.assertTrue(ptype.is_copiable)
    #     self.assertTrue(ptype.enabled)
    #     self.assertFalse(ptype.subject_ctypes.all())
    #     self.assertFalse([*ptype.subject_models])
    #
    # def test_manager_smart_update_or_create02(self):  # DEPRECATED
    #     "ContentTypes & app label."
    #     uid = '73b2c0b5-10a8-443a-9e07-1f2398e889ea'
    #     text = 'is wonderful'
    #     label = 'creme_core'
    #
    #     get_ct = ContentType.objects.get_for_model
    #     orga_ct = get_ct(FakeOrganisation)
    #     ptype = CremePropertyType.objects.smart_update_or_create(
    #         uuid=uid,
    #         text=text,
    #         app_label=label,
    #         is_copiable=False,
    #         is_custom=True,
    #         subject_ctypes=[FakeContact, orga_ct],
    #     )
    #
    #     self.assertEqual(label, ptype.app_label)
    #     self.assertTrue(ptype.is_custom)
    #     self.assertFalse(ptype.is_copiable)
    #     self.assertCountEqual(
    #         [get_ct(FakeContact), orga_ct], [*ptype.subject_ctypes.all()],
    #     )
    #     self.assertCountEqual(
    #         [FakeContact, FakeOrganisation], [*ptype.subject_models],
    #     )
    #
    # def test_manager_smart_update_or_create03(self):  # DEPRECATED
    #     "Update existing."
    #     uid = '85df6868-beee-41b3-a263-a139f6dfde27'
    #     create_ptype = CremePropertyType.objects.smart_update_or_create
    #     create_ptype(uuid=uid, text='is delicious', subject_ctypes=[FakeOrganisation])
    #
    #     text = 'is very delicious'
    #     ptype = create_ptype(
    #         uuid=uid,
    #         text=text,
    #         is_copiable=False,
    #         is_custom=True,
    #         subject_ctypes=[FakeContact],
    #     )
    #
    #     self.assertEqual(text, ptype.text)
    #     self.assertTrue(ptype.is_custom)
    #     self.assertFalse(ptype.is_copiable)
    #     self.assertListEqual([FakeContact], [*ptype.subject_models])
    #
    # def test_manager_smart_update_or_create04(self):  # DEPRECATED
    #     "Generate uuid."
    #     create_ptype = CremePropertyType.objects.smart_update_or_create
    #     text1 = 'is delicious'
    #     ptype1 = create_ptype(
    #         text=text1,
    #         is_custom=True,
    #         is_copiable=False,
    #     )
    #     self.assertTrue(ptype1.uuid)
    #     self.assertEqual(text1, ptype1.text)
    #     self.assertEqual('', ptype1.app_label)
    #     self.assertTrue(ptype1.is_custom)
    #     self.assertFalse(ptype1.is_copiable)
    #     self.assertFalse([*ptype1.subject_models])
    #
    #     text2 = 'is yummy'
    #     label2 = 'documents'
    #     ptype2 = create_ptype(
    #         text=text2,
    #         app_label=label2,
    #         is_custom=False,
    #         is_copiable=True,
    #         subject_ctypes=[FakeContact],
    #     )
    #     self.assertTrue(ptype2.uuid)
    #     self.assertEqual(text2, ptype2.text)
    #     self.assertEqual(label2, ptype2.app_label)
    #     self.assertFalse(ptype2.is_custom)
    #     self.assertTrue(ptype2.is_copiable)
    #     self.assertListEqual([FakeContact], [*ptype2.subject_models])
    #
    #     self.assertNotEqual(ptype1.uuid, ptype2.uuid)

    def test_manager_compatible(self):
        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='is delicious')
        ptype2 = create_ptype(text='is happy')
        ptype3 = create_ptype(text='is wonderful').set_subject_ctypes(FakeContact)

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

    def test_manager_proxy__get_or_create__minimal(self):
        count = CremePropertyType.objects.count()

        uuid = uuid4()
        text1 = 'Is smart'
        proxy1 = CremePropertyType.objects.proxy(uuid=uuid, text=text1)
        self.assertEqual(count, CremePropertyType.objects.count())
        self.assertEqual(uuid, proxy1.uuid)
        self.assertEqual(text1, proxy1.text)
        self.assertEqual('',   proxy1.app_label)
        self.assertEqual('',   proxy1.description)
        self.assertIs(proxy1.is_custom, False)
        self.assertIs(proxy1.is_copiable, True)
        self.assertIs(proxy1.enabled, True)
        self.assertFalse([*proxy1.subject_models])
        self.assertFalse([*proxy1.subject_ctypes])

        ptype1, created1 = proxy1.get_or_create()
        self.assertIs(created1, True)
        self.assertIsInstance(ptype1, CremePropertyType)
        self.assertIsNotNone(ptype1.pk)
        self.assertEqual(uuid, ptype1.uuid)
        self.assertEqual(text1, ptype1.text)
        self.assertEqual('',   ptype1.app_label)
        self.assertEqual('',   ptype1.description)
        self.assertIs(ptype1.is_custom, False)
        self.assertIs(ptype1.is_copiable, True)
        self.assertIs(ptype1.enabled, True)
        self.assertFalse([*ptype1.subject_ctypes.all()])

        self.assertEqual(count + 1, CremePropertyType.objects.count())

        # get_or_create() again ---
        ptype2, created2 = proxy1.get_or_create()
        self.assertIs(created2, False)
        self.assertIsInstance(ptype2, CremePropertyType)
        self.assertEqual(count + 1, CremePropertyType.objects.count())

        # New proxy ---
        proxy2 = CremePropertyType.objects.proxy(uuid=uuid, text='Other text')
        ptype3, created3 = proxy2.get_or_create()
        self.assertIs(created3, False)
        self.assertEqual(text1, ptype3.text)
        self.assertEqual(count + 1, CremePropertyType.objects.count())

    def test_manager_proxy__get_or_create__more_arguments(self):
        get_ct = ContentType.objects.get_for_model
        contact_ct = get_ct(FakeContact)
        orga_ct = get_ct(FakeOrganisation)

        uuid = uuid4()
        text = 'Is cool'
        description = "Lookin cool"
        app_label = 'creme_core'

        proxy = CremePropertyType.objects.proxy(
            uuid=uuid, text=text, app_label=app_label, description=description,
            is_custom=True, is_copiable=False, enabled=False,
            subject_models=[FakeContact, FakeOrganisation],
        )
        self.assertEqual(uuid, proxy.uuid)
        self.assertEqual(text, proxy.text)
        self.assertEqual(app_label,   proxy.app_label)
        self.assertEqual(description, proxy.description)
        self.assertIs(proxy.is_custom, True)
        self.assertIs(proxy.is_copiable, False)
        self.assertIs(proxy.enabled, False)
        self.assertCountEqual([FakeContact, FakeOrganisation], [*proxy.subject_models])
        self.assertCountEqual([contact_ct, orga_ct],           [*proxy.subject_ctypes])

        ptype, created = proxy.get_or_create()
        self.assertIsInstance(ptype, CremePropertyType)
        self.assertIsNotNone(ptype.pk)
        self.assertEqual(uuid, ptype.uuid)
        self.assertEqual(text, ptype.text)
        self.assertEqual(app_label,   ptype.app_label)
        self.assertEqual(description, ptype.description)
        self.assertIs(ptype.is_custom, True)
        self.assertIs(ptype.is_copiable, False)
        self.assertIs(ptype.enabled, False)
        self.assertCountEqual([contact_ct, orga_ct], [*ptype.subject_ctypes.all()])

    def test_manager_proxy__update_or_create(self):
        get_ct = ContentType.objects.get_for_model
        contact_ct = get_ct(FakeContact)
        orga_ct = get_ct(FakeOrganisation)

        uuid = uuid4()

        text1 = 'Is cool'
        description1 = 'Lookin cool'
        app_label = 'creme_core'

        # Create ---
        ptype1, created1 = CremePropertyType.objects.proxy(
            uuid=uuid, text=text1, app_label=app_label, description=description1,
            is_custom=True, is_copiable=False,
            subject_models=[FakeContact, FakeOrganisation],
        ).update_or_create()
        self.assertIs(created1, True)
        self.assertIsInstance(ptype1, CremePropertyType)
        self.assertIsNotNone(ptype1.pk)
        self.assertEqual(uuid, ptype1.uuid)
        self.assertEqual(text1, ptype1.text)
        self.assertEqual(app_label,   ptype1.app_label)
        self.assertEqual(description1, ptype1.description)
        self.assertTrue(ptype1.is_custom)
        self.assertFalse(ptype1.is_copiable)
        self.assertTrue(ptype1.enabled)
        self.assertCountEqual([contact_ct, orga_ct], [*ptype1.subject_ctypes.all()])

        # Update ---
        text2 = 'Is very cool'
        description2 = "Lookin' cool"
        ptype2, created2 = CremePropertyType.objects.proxy(
            uuid=uuid, text=text2, app_label=app_label, description=description2,
            subject_models=[FakeContact, FakeActivity],
        ).update_or_create()
        self.assertIs(created2, False)
        self.assertIsInstance(ptype2, CremePropertyType)
        self.assertEqual(ptype1.pk, ptype2.pk)
        self.assertEqual(uuid,  ptype2.uuid)
        self.assertEqual(text2, ptype2.text)
        self.assertCountEqual(
            [contact_ct, get_ct(FakeActivity)], [*ptype1.subject_ctypes.all()],
        )

    def test_manager_proxy__errors(self):
        with self.assertRaises(ValueError):
            CremePropertyType.objects.proxy(id=1, uuid=uuid4(), text='Is smart')

        with self.assertRaises(ValueError):
            CremePropertyType.objects.proxy(pk=1, uuid=uuid4(), text='Is smart')

        proxy = CremePropertyType.objects.proxy(uuid=uuid4(), text='Is smart')
        with self.assertRaises(AttributeError):
            proxy.save  # NOQA

    def test_manager_proxy__set_attr(self):
        proxy = CremePropertyType.objects.proxy(uuid=uuid4(), text='Is smart')

        proxy.text = text = 'Is smart'
        self.assertEqual(text, proxy.text)

        proxy.description = description = 'Blablabla'
        self.assertEqual(description, proxy.description)

        ptype = proxy.get_or_create()[0]
        self.assertEqual(text,        ptype.text)
        self.assertEqual(description, ptype.description)

        with self.assertRaises(AttributeError):
            proxy.id = 12

        with self.assertRaises(AttributeError):
            proxy.pk = 12

    def test_manager_proxy__update_models(self):
        get_ct = ContentType.objects.get_for_model
        contact_ct = get_ct(FakeContact)
        orga_ct = get_ct(FakeOrganisation)
        activity_ct = get_ct(FakeActivity)

        proxy = CremePropertyType.objects.proxy(
            uuid=uuid4(), text='Is smart', subject_models=[FakeContact],
        )

        proxy.add_models(FakeOrganisation, FakeActivity, FakeContact)
        self.assertCountEqual(
            [contact_ct, orga_ct, activity_ct], [*proxy.subject_ctypes],
        )

        proxy.remove_models(FakeOrganisation, FakeContact)
        self.assertCountEqual([activity_ct], [*proxy.subject_ctypes])

        ptype = proxy.get_or_create()[0]
        self.assertCountEqual([activity_ct], [*ptype.subject_ctypes.all()])

    def test_init(self):
        text = 'wonderful'
        description = 'is wonderful'
        ptype = CremePropertyType.objects.create(text=text, description=description)
        self.assertIsNotNone(ptype.pk)
        self.assertEqual(text,        ptype.text)
        self.assertEqual(description, ptype.description)
        self.assertFalse(ptype.is_custom)
        self.assertTrue(ptype.is_copiable)
        self.assertTrue(ptype.enabled)

        with self.assertNumQueries(1):
            self.assertEqual(0, ptype.properties_count)

        with self.assertNumQueries(0):
            self.assertEqual(0, ptype.properties_count)

    def test_properties_count(self):
        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='wonderful')
        ptype2 = create_ptype(text='cool')

        user = self.get_root_user()
        create_prop = CremeProperty.objects.create
        c = FakeContact.objects.create(user=user, first_name='Winston', last_name='Smith')
        o = FakeOrganisation.objects.create(user=user, name='Angsoc')
        create_prop(type=ptype1, creme_entity=c)
        create_prop(type=ptype1, creme_entity=o)
        create_prop(type=ptype2, creme_entity=o)
        self.assertEqual(2, ptype1.properties_count)
        self.assertEqual(1, ptype2.properties_count)

    def test_set_subjects_ctypes(self):
        get_ct = ContentType.objects.get_for_model
        orga_ct = get_ct(FakeOrganisation)
        ptype = CremePropertyType.objects.create(
            text='is wonderful',
        ).set_subject_ctypes(FakeContact, orga_ct)
        self.assertIsInstance(ptype, CremePropertyType)
        self.assertCountEqual(
            [get_ct(FakeContact), orga_ct], [*ptype.subject_ctypes.all()],
        )

    def test_is_compatible1(self):
        ptype = CremePropertyType.objects.create(text='is wonderful')
        self.assertTrue(ptype.is_compatible(FakeOrganisation))
        self.assertTrue(ptype.is_compatible(ContentType.objects.get_for_model(FakeContact)))

    def test_is_compatible2(self):
        ptype = CremePropertyType.objects.create(
            text='is wonderful',
        ).set_subject_ctypes(FakeContact, FakeOrganisation)

        with self.assertNumQueries(1):
            self.assertTrue(ptype.is_compatible(FakeOrganisation))

        with self.assertNumQueries(1):
            self.assertTrue(ptype.is_compatible(FakeContact))

        self.assertFalse(ptype.is_compatible(FakeActivity))

        get_ct = ContentType.objects.get_for_model
        self.assertTrue(ptype.is_compatible(get_ct(FakeContact)))
        self.assertFalse(ptype.is_compatible(get_ct(FakeActivity)))

        # Cached ---
        ptype = CremePropertyType.objects.filter(
            id=ptype.id,
        ).prefetch_related('subject_ctypes').first()

        with self.assertNumQueries(0):
            self.assertTrue(ptype.is_compatible(FakeOrganisation))


class CremePropertyTestCase(CremeTestCase):
    def test_create(self):
        text = 'is delicious'

        with self.assertNoException():
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

        ptype = CremePropertyType.objects.create(text=text)
        entity = CremeEntity.objects.create(user=self.get_root_user())

        CremeProperty.objects.safe_create(type=ptype, creme_entity=entity)
        self.assertHasProperty(entity=entity, ptype=ptype)

        with self.assertNoException():
            CremeProperty.objects.safe_create(type=ptype, creme_entity=entity)

    def test_manager_safe_get_or_create(self):
        text = 'is happy'

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
