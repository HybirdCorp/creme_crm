from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _

from creme.creme_core.core.cloning import (
    EntityCloner,
    EntityClonerRegistry,
    entity_cloner_registry,
)
from creme.creme_core.core.copying import RegularFieldsCopier
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    CustomField,
    CustomFieldInteger,
    FakeContact,
    FakeOrganisation,
    Language,
    Relation,
    RelationType,
)

from ..base import CremeTestCase


class CloningTestCase(CremeTestCase):
    def test_registry(self):
        registry = EntityClonerRegistry()
        self.assertIsNone(registry.get(FakeOrganisation))

        registry.register(FakeOrganisation)
        self.assertIsInstance(registry.get(FakeOrganisation), EntityCloner)
        self.assertIsNone(registry.get(FakeContact))

        registry.register(FakeContact).unregister(FakeOrganisation)
        self.assertIsNone(registry.get(FakeOrganisation))
        self.assertIsInstance(registry.get(FakeContact), EntityCloner)

        self.assertIsInstance(entity_cloner_registry, EntityClonerRegistry)

    def test_registry__register_error(self):
        registry = EntityClonerRegistry().register(FakeOrganisation)

        class FakeOrganisationCloner(EntityCloner):
            pass

        with self.assertRaises(registry.RegistrationError) as cm:
            registry.register(FakeOrganisation, cloner_class=FakeOrganisationCloner)

        self.assertEqual(
            '<FakeOrganisation> has already a cloner',
            str(cm.exception),
        )

    def test_registry__unregister_error(self):
        registry = EntityClonerRegistry()

        with self.assertRaises(registry.UnRegistrationError) as cm:
            registry.unregister(FakeOrganisation)

        self.assertEqual(
            '<FakeOrganisation> has no cloner (not registered or already unregistered)',
            str(cm.exception),
        )

    def test_regular_cloner(self):
        cloner = EntityCloner()

        user = self.get_root_user()
        contact = FakeContact.objects.create(user=user, first_name='Philip', last_name='Fry')
        self.assertIsNone(cloner.check_permissions(user=user, entity=contact))

        lang = Language.objects.first()
        contact.languages.add(lang)

        cfield = CustomField.objects.create(
            content_type=FakeContact, name='size (cm)', field_type=CustomField.INT,
        )
        CustomFieldInteger.objects.create(custom_field=cfield, entity=contact, value=180)

        orga = FakeOrganisation.objects.create(user=user, name='Planet express')

        rtype = RelationType.objects.builder(
            id='test-object_employs', predicate='is employed by',
        ).symmetric(
            id='test-subject_employs', predicate='employs',
        ).get_or_create()[0]
        Relation.objects.create(
            user=user, subject_entity=contact, type=rtype, object_entity=orga,
        )

        ptype = CremePropertyType.objects.create(text='straightforward')
        CremeProperty.objects.create(type=ptype, creme_entity=contact)

        clone = cloner.perform(user=user, entity=contact)
        self.assertIsInstance(clone, FakeContact)
        self.assertIsNotNone(clone.pk)
        self.assertNotEqual(contact.pk, clone.pk)

        self.assertEqual(contact.user, clone.user)
        self.assertEqual(contact.first_name, clone.first_name)
        self.assertEqual(contact.last_name,  clone.last_name)

        self.assertListEqual([lang], [*clone.languages.all()])

        self.assertEqual(
            180, CustomFieldInteger.objects.get(custom_field=cfield, entity=clone).value,
        )

        self.assertSameRelationsNProperties(entity1=contact, entity2=clone)

    def test_regular_cloner_permissions__not_superuser(self):
        cloner = EntityCloner()

        orga = FakeOrganisation.objects.create(
            user=self.get_root_user(), name='Planet express',
        )

        role = self.create_role(
            name='Can clone', allowed_apps=['creme_core'],
            creatable_models=[FakeOrganisation],
        )
        self.add_credentials(role, all=['VIEW'])

        user = self.create_user(role=role)
        self.assertTrue(user.has_perm_to_view(orga))

        with self.assertNoException():
            cloner.check_permissions(user=user, entity=orga)

    def test_regular_cloner_permissions__view_perm(self):
        registry = EntityClonerRegistry().register(FakeOrganisation)
        cloner = registry.get(FakeOrganisation)

        orga = FakeOrganisation.objects.create(
            user=self.get_root_user(), name='Planet express',
        )

        role = self.create_role(
            name='Cannot view', allowed_apps=['creme_core'], creatable_models=[FakeOrganisation],
        )
        self.add_credentials(role, all='!VIEW')

        user = self.create_user(role=role)

        with self.assertRaises(PermissionDenied) as cm:
            cloner.check_permissions(user=user, entity=orga)

        self.assertEqual(
            _('You are not allowed to view this entity: {}').format(
                _('Entity #{id} (not viewable)').format(id=orga.id)
            ),
            str(cm.exception),
        )

    def test_regular_cloner_permissions__creation_perm(self):
        registry = EntityClonerRegistry().register(FakeOrganisation)
        cloner = registry.get(FakeOrganisation)

        orga = FakeOrganisation.objects.create(
            user=self.get_root_user(), name='Planet express',
        )

        role = self.create_role(
            name='Cannot create', allowed_apps=['creme_core'],
            # creatable_models=[FakeOrganisation],
        )
        self.add_credentials(role, all='*')

        user = self.create_user(role=role)

        with self.assertRaises(PermissionDenied) as cm:
            cloner.check_permissions(user=user, entity=orga)

        self.assertEqual(
            _(
                'You are not allowed to create: %(model)s'
            ) % {'model': 'Test Organisation'},
            str(cm.exception),
        )

    def test_regular_cloner_permissions__is_deleted(self):
        registry = EntityClonerRegistry().register(FakeOrganisation)
        cloner = registry.get(FakeOrganisation)

        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(
            user=user, name='Planet express', is_deleted=True,
        )

        with self.assertRaises(ConflictError) as cm:
            cloner.check_permissions(user=user, entity=orga)

        self.assertEqual(
            _('A deleted entity cannot be cloned'),
            str(cm.exception),
        )

    def test_custom_cloner(self):
        class NotEmailCopier(RegularFieldsCopier):
            exclude = ['email']

        class FakeOrganisationCloner(EntityCloner):
            pre_save_copiers = [NotEmailCopier]

        cloner = FakeOrganisationCloner()

        root = self.get_root_user()
        orga = FakeOrganisation.objects.create(
            user=root, name='Planet express', email='contact@planet-express.com',
        )

        clone = cloner.perform(user=root, entity=orga)
        self.assertEqual(orga.name, clone.name)
        self.assertFalse(clone.email)
