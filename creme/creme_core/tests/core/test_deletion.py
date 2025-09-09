from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError
from django.test.utils import override_settings
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.creme_core.core.deletion import (
    REPLACERS_MAP,
    EntityDeletor,
    EntityDeletorRegistry,
    FixedValueReplacer,
    SETReplacer,
    entity_deletor_registry,
)
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    FakeCivility,
    FakeContact,
    FakeDocument,
    FakeDocumentCategory,
    FakeInvoice,
    FakeInvoiceLine,
    FakeOrganisation,
    FakeSector,
    FakeTicket,
    FakeTicketPriority,
    Relation,
    RelationType,
)

from ..base import CremeTestCase


class DeletionTestCase(CremeTestCase):
    def test_replacer_by_fixed_value01(self):
        civ = FakeCivility.objects.create(title='Kun')

        model_field = FakeContact._meta.get_field('civility')
        replacer1 = FixedValueReplacer(model_field=model_field, value=civ)
        self.assertEqual(model_field, replacer1.model_field)
        self.assertEqual(civ, replacer1._fixed_value)

        serialized = {
            'ctype': ContentType.objects.get_for_model(FakeContact).natural_key(),
            'field': 'civility',
            'pk':    civ.pk,
        }
        self.assertEqual(serialized, replacer1.as_dict())

        replacer2 = FixedValueReplacer.from_dict(serialized)
        self.assertIsInstance(replacer2, FixedValueReplacer)
        self.assertEqual(model_field,    replacer2.model_field)
        self.assertEqual(civ,            replacer2.get_value())

        self.assertEqual(
            _('In «{model} - {field}», replace by «{new}»').format(
                model='Test Contact',
                field=_('Civility'),
                new=civ.title,
            ),
            str(replacer1),
        )

    def test_replacer_by_fixed_value02(self):
        "<None> value + other ContentType."
        model_field = FakeOrganisation._meta.get_field('sector')
        replacer1 = FixedValueReplacer(model_field=model_field, value=None)

        serialized = {
            'ctype': ContentType.objects.get_for_model(FakeOrganisation).natural_key(),
            'field': 'sector',
        }
        self.assertEqual(serialized, replacer1.as_dict())

        replacer2 = FixedValueReplacer.from_dict(serialized)
        self.assertIsInstance(replacer2, FixedValueReplacer)
        self.assertEqual(model_field, replacer2.model_field)
        self.assertIsNone(replacer2.get_value())

        self.assertEqual(
            _('Empty «{model} - {field}»').format(
                model='Test Organisation',
                field=_('Sector'),
            ),
            str(replacer1),
        )

    def test_replacer_by_fixed_value03(self):
        "Explicit & implicit values."
        self.assertEqual(
            _('Empty «{model} - {field}»').format(
                model='Test Contact',
                field=_('Civility'),
            ),
            str(FixedValueReplacer(
                model_field=FakeContact._meta.get_field('civility')
            )),
        )

        sector = FakeSector.objects.create(title='Ninja')
        self.assertEqual(
            _('In «{model} - {field}», replace by «{new}»').format(
                model='Test Organisation',
                field=_('Sector'),
                new=sector.title,
            ),
            str(FixedValueReplacer(
                model_field=FakeOrganisation._meta.get_field('sector'),
                value=sector,
            ))
        )

    def test_replacer_by_fixed_value04(self):
        "ManyToMany."
        cat = FakeDocumentCategory.objects.create(name='PNGs')
        m2m = FakeDocument._meta.get_field('categories')

        self.assertEqual(
            _('In «{model} - {field}», replace by «{new}»').format(
                model='Test Document',
                field=_('Categories'),
                new=cat.name,
            ),
            str(FixedValueReplacer(model_field=m2m, value=cat)),
        )

        self.assertEqual(
            _('Remove from «{model} - {field}»').format(
                model='Test Document',
                field=_('Categories'),
            ),
            str(FixedValueReplacer(model_field=m2m)),
        )

    def test_replacer_for_SET(self):
        self.assertFalse(FakeTicketPriority.objects.filter(name='Deleted'))

        model_field = FakeTicket._meta.get_field('priority')
        replacer1 = SETReplacer(model_field=model_field)
        self.assertEqual(model_field, replacer1.model_field)

        value = replacer1.get_value()
        self.assertIsInstance(value, FakeTicketPriority)
        self.assertEqual('Deleted', value.name)

        serialized = {
            'ctype': ContentType.objects.get_for_model(FakeTicket).natural_key(),
            'field': 'priority',
        }
        self.assertEqual(serialized, replacer1.as_dict())

        replacer2 = SETReplacer.from_dict(serialized)
        self.assertIsInstance(replacer2, SETReplacer)
        self.assertEqual(model_field,    replacer2.model_field)
        self.assertEqual(value,          replacer2.get_value())

        self.assertEqual(
            _('In «{model} - {field}», replace by a fallback value').format(
                model='Test Ticket',
                field=_('Priority'),
            ),
            str(replacer1),
        )

    def test_registry01(self):
        "FixedValueReplacer."
        sector = FakeSector.objects.first()

        field1 = FakeOrganisation._meta.get_field('sector')
        field2 = FakeContact._meta.get_field('sector')
        replacer1 = FixedValueReplacer(model_field=field1, value=None)
        replacer2 = FixedValueReplacer(model_field=field2, value=sector)

        get_ct = ContentType.objects.get_for_model
        serialized = [
            [
                'fixed_value',
                {
                    'ctype': get_ct(FakeOrganisation).natural_key(),
                    'field': 'sector',
                },
            ], [
                'fixed_value',
                {
                    'ctype': get_ct(FakeContact).natural_key(),
                    'field': 'sector',
                    'pk': sector.pk,
                },
            ],
        ]
        self.assertEqual(
            serialized,
            REPLACERS_MAP.serialize([replacer1, replacer2])
        )

        replacers = REPLACERS_MAP.deserialize(serialized)
        self.assertIsList(replacers, length=2)

        d_replacer1 = replacers[0]
        self.assertIsInstance(d_replacer1, FixedValueReplacer)
        self.assertEqual(field1, d_replacer1.model_field)
        self.assertIsNone(d_replacer1.get_value())

        d_replacer2 = replacers[1]
        self.assertIsInstance(d_replacer2, FixedValueReplacer)
        self.assertEqual(field2, d_replacer2.model_field)
        self.assertEqual(sector, d_replacer2.get_value())

    def test_registry02(self):
        "SETReplacer."
        field = FakeTicket._meta.get_field('priority')
        replacer = SETReplacer(model_field=field)

        serialized = [
            [
                'SET',
                {
                    'ctype': ContentType.objects.get_for_model(FakeTicket).natural_key(),
                    'field': 'priority',
                },
            ],
        ]
        self.assertEqual(serialized, REPLACERS_MAP.serialize([replacer]))

        replacers = REPLACERS_MAP.deserialize(serialized)
        self.assertIsList(replacers, length=1)

        d_replacer = replacers[0]
        self.assertIsInstance(d_replacer, SETReplacer)
        self.assertEqual(field, d_replacer.model_field)


@override_settings(ENTITIES_DELETION_ALLOWED=True)
class EntityDeletionTestCase(CremeTestCase):
    def test_basic(self):
        registry = EntityDeletorRegistry()
        self.assertIsNone(registry.get(FakeOrganisation))

        registry.register(FakeOrganisation)
        deletor = registry.get(FakeOrganisation)
        self.assertIsInstance(deletor, EntityDeletor)

        root = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=root, name='Olympus')
        self.assertIsNone(deletor.check_permissions(user=root, entity=orga))

        # ---
        role1 = self.create_role(name='Can delete own', allowed_apps=['creme_core'])
        self.add_credentials(role1, all=['DELETE'])

        basic_user = self.create_user(index=0, role=role1)
        self.assertTrue(basic_user.has_perm_to_delete(orga))
        with self.assertNoException():
            deletor.check_permissions(user=basic_user, entity=orga)

        # ---
        role2 = self.create_role(name='Cannot delete', allowed_apps=['creme_core'])
        self.add_credentials(role2, all='!DELETE', own='*')

        forbidden_user = self.create_user(index=1, role=role2)
        self.assertTrue(forbidden_user.has_perm_to_change(orga))
        self.assertFalse(forbidden_user.has_perm_to_delete(orga))

        with self.assertRaises(PermissionDenied) as cm:
            deletor.check_permissions(user=forbidden_user, entity=orga)
        self.assertEqual(
            _('You are not allowed to delete this entity by your role'),
            str(cm.exception),
        )

        # ---
        deletor.perform(user=root, entity=orga)
        orga = self.assertStillExists(orga)
        self.assertTrue(orga.is_deleted)

        deletor.perform(user=root, entity=orga)
        self.assertDoesNotExist(orga)

    def test_register_deletor(self):
        class FakeDeletor(EntityDeletor):
            pass

        registry = EntityDeletorRegistry().register(
            FakeOrganisation, deletor_class=FakeDeletor,
        ).register(FakeContact)

        orga_deletor = registry.get(FakeOrganisation)
        self.assertIsInstance(orga_deletor, FakeDeletor)

        contact_deletor = registry.get(FakeContact)
        self.assertIsInstance(contact_deletor, EntityDeletor)
        self.assertNotIsInstance(contact_deletor, FakeDeletor)

        # ---
        with self.assertRaises(registry.RegistrationError):
            registry.register(FakeContact, deletor_class=FakeDeletor)

    def test_unregister(self):
        class FakeDeletor(EntityDeletor):
            pass

        registry = EntityDeletorRegistry().register(
            FakeOrganisation, deletor_class=FakeDeletor,
        ).register(FakeContact)

        with self.assertNoException():
            registry.unregister(FakeOrganisation)

        self.assertIsNone(registry.get(FakeOrganisation))
        self.assertIsNotNone(registry.get(FakeContact))

        # ---
        with self.assertRaises(registry.UnRegistrationError):
            registry.unregister(FakeOrganisation)

    @override_settings(ENTITIES_DELETION_ALLOWED=False)
    def test_deletion_not_allowed(self):
        registry = EntityDeletorRegistry().register(FakeOrganisation)
        deletor = registry.get(FakeOrganisation)

        root = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=root, name='Olympus')

        with self.assertNoException():
            deletor.check_permissions(user=root, entity=orga)

        deletor.perform(user=root, entity=orga)
        orga = self.assertStillExists(orga)
        self.assertTrue(orga.is_deleted)

        # ---
        with self.assertRaises(ConflictError) as cm:
            deletor.check_permissions(user=root, entity=orga)
        self.assertEqual(
            _('Deletion has been disabled by your administrator'),
            str(cm.exception),
        )

        # ---
        staff_user = self.create_user(is_staff=True)
        with self.assertNoException():
            deletor.check_permissions(user=staff_user, entity=orga)

    def test_dependencies(self):
        "Relations (not internal ones) & properties are deleted correctly."
        user = self.get_root_user()
        deletor = EntityDeletor()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity1 = create_orga(name='Nerv', is_deleted=True)
        entity2 = create_orga(name='Seele')
        entity3 = create_orga(name='Neo tokyo')

        rtype1 = RelationType.objects.builder(
            id='test-subject_linked', predicate='is linked to',
            is_custom=True,
        ).symmetric(id='test-object_linked', predicate='is linked to').get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_provides', predicate='provides',
        ).symmetric(id='test-object_provides',  predicate='provided by').get_or_create()[0]

        create_rel = partial(Relation.objects.create, user=user, subject_entity=entity1)
        rel1 = create_rel(type=rtype1, object_entity=entity2)
        rel2 = create_rel(type=rtype2, object_entity=entity3)
        rel3 = create_rel(type=rtype2, object_entity=entity3, subject_entity=entity2)

        ptype = CremePropertyType.objects.create(text='has eva')
        create_prop = partial(CremeProperty.objects.create, type=ptype)
        prop1 = create_prop(creme_entity=entity1)
        prop2 = create_prop(creme_entity=entity2)

        deletor.perform(user=user, entity=entity1)
        self.assertDoesNotExist(entity1)
        self.assertStillExists(entity2)
        self.assertStillExists(entity3)

        self.assertDoesNotExist(rel1)
        self.assertDoesNotExist(rel2)
        self.assertStillExists(rel3)

        self.assertDoesNotExist(prop1)
        self.assertStillExists(prop2)

    def test_dependencies__error(self):
        "Dependencies problem (with internal Relations)."
        user = self.get_root_user()
        deletor = EntityDeletor()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity1 = create_orga(name='Nerv', is_deleted=True)
        entity2 = create_orga(name='Seele')

        rtype = RelationType.objects.builder(
            id='test-subject_daughter', predicate='is a daughter of',
            is_internal=True,  # <==
        ).symmetric(
            id='test-object_daughter', predicate='has a daughter',
        ).get_or_create()[0]
        rel = Relation.objects.create(
            user=user, type=rtype, subject_entity=entity1, object_entity=entity2,
        )

        with self.assertRaises(ProtectedError) as cm:
            deletor.perform(user=user, entity=entity1)

        self.assertStillExists(entity1)
        self.assertStillExists(entity2)

        exc_args = cm.exception.args
        self.assertIsTuple(exc_args, length=2)
        self.assertIsInstance(exc_args[0], str)
        self.assertSetEqual({rel, rel.symmetric_relation}, exc_args[1])

    @parameterized.expand([True, False])
    def test_delete_entity_auxiliary(self, deletion_allowed):
        deletor = EntityDeletor()

        user = self.get_root_user()
        invoice = FakeInvoice.objects.create(user=user, name='Invoice#1')
        line = FakeInvoiceLine.objects.create(user=user, linked_invoice=invoice)

        with override_settings(ENTITIES_DELETION_ALLOWED=deletion_allowed):
            with self.assertNoException():
                deletor.check_permissions(user=user, entity=line)

            deletor.perform(user=user, entity=line)

        self.assertDoesNotExist(line)
        self.assertStillExists(invoice)

    def test_global_registry(self):
        self.assertIsInstance(entity_deletor_registry, EntityDeletorRegistry)
        self.assertIsNotNone(entity_deletor_registry.get(FakeContact))
        self.assertIsNotNone(entity_deletor_registry.get(FakeOrganisation))
