from decimal import Decimal
from functools import partial

from django.core.exceptions import PermissionDenied
from django.utils.timezone import now
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.creme_core.core.cloning import (
    CustomFieldsCopier,
    EntityCloner,
    EntityClonerRegistry,
    ManyToManyFieldsCopier,
    PropertiesCopier,
    RegularFieldsCopier,
    RelationAdder,
    RelationsCopier,
    StrongPropertiesCopier,
    StrongRelationsCopier,
    entity_cloner_registry,
)
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    CustomField,
    CustomFieldBoolean,
    CustomFieldDateTime,
    CustomFieldEnum,
    CustomFieldEnumValue,
    CustomFieldFloat,
    CustomFieldInteger,
    CustomFieldMultiEnum,
    CustomFieldString,
    FakeContact,
    FakeCountry,
    FakeOrganisation,
    Language,
    Relation,
    RelationType,
)

from ..base import CremeTestCase


class CloningTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        create_rtype = RelationType.objects.smart_update_or_create
        cls.rtype1 = create_rtype(
            ('test-subject_employs', 'employs'),
            ('test-object_employs',  'is employed by'),
        )[0]
        cls.rtype2 = create_rtype(
            ('test-subject_managed', 'is managed by'),
            ('test-object_managed',  'manages'),
            is_internal=True,
        )[0]
        cls.rtype3 = create_rtype(
            ('test-subject_created', 'has been created by'),
            ('test-object_created',  'has created'),
            is_copiable=(False, False),
        )[0]

        create_ptype = CremePropertyType.objects.create
        cls.ptype1 = create_ptype(text='straightforward')
        cls.ptype2 = create_ptype(text='fast')
        cls.ptype3 = create_ptype(text='cool', is_copiable=False)

    def test_regular_fields_copier(self):
        user = self.get_root_user()
        src = FakeOrganisation(
            user=user, name='Planet express', email='contact@planet-express.com',
            description='Best shipping company in the universe',
        )
        target = FakeOrganisation()

        copier = RegularFieldsCopier(source=src, user=user)
        copier.copy_to(target)
        self.assertEqual(src.user,        target.user)
        self.assertEqual(src.name,        target.name)
        self.assertEqual(src.email,       target.email)
        self.assertEqual(src.description, target.description)

    def test_regular_fields_copier__not_clonable(self):
        user = self.get_root_user()
        src = FakeContact(
            user=user, first_name='Leela', last_name='Turanga', is_user=user,
        )
        target = FakeContact()

        copier = RegularFieldsCopier(user=user, source=src)
        self.assertEqual(src,  copier.source)
        self.assertEqual(user, copier.user)

        copier.copy_to(target)
        self.assertEqual(src.user,       target.user)
        self.assertEqual(src.first_name, target.first_name)
        self.assertEqual(src.last_name,  target.last_name)
        self.assertIsNone(target.is_user)

    def test_regular_fields_copier__exclude(self):
        class NotEmailCopier(RegularFieldsCopier):
            exclude = {'email'}

        user = self.get_root_user()
        src = FakeOrganisation(
            user=user, name='Planet express', email='contact@planet-express.com',
        )
        target = FakeOrganisation()

        copier = NotEmailCopier(user=user, source=src)
        copier.copy_to(target=target)
        self.assertEqual(src.user, target.user)
        self.assertEqual(src.name, target.name)
        self.assertFalse(target.email)

    def test_regular_fields_copier__accept_field(self):
        class OrgaCopier(RegularFieldsCopier):
            exclude = {'email'}

            def accept(this, field):
                if not super().accept(field=field):
                    return False

                return field.name != 'phone'

        user = self.get_root_user()
        src = FakeOrganisation(
            user=user,
            name='Planet express',
            email='contact@planet-express.com',
            phone='1234 56',
        )
        target = FakeOrganisation()

        copier = OrgaCopier(user=user, source=src)
        copier.copy_to(target=target)
        self.assertEqual(src.user, target.user)
        self.assertEqual(src.name, target.name)
        self.assertFalse(target.email)
        self.assertFalse(target.phone)

    def test_m2m_fields_copier(self):
        user = self.get_root_user()

        l1, l2 = Language.objects.all()[:2]

        create_contact = partial(FakeContact.objects.create, user=user)
        src = create_contact(first_name='Leela', last_name='Turanga')
        src.languages.set([l1, l2])
        src.preferred_countries.set([FakeCountry.objects.create(name='Earth')])

        target = create_contact(first_name='Amy', last_name='Wong')

        copier = ManyToManyFieldsCopier(source=src, user=user)
        copier.copy_to(target)
        self.assertCountEqual([l1, l2], target.languages.all())
        self.assertFalse(target.preferred_countries.all())

    def test_m2m_fields_copier__exclude(self):
        class NotLanguageCopier(ManyToManyFieldsCopier):
            exclude = {'languages'}

        user = self.get_root_user()

        create_contact = partial(FakeContact.objects.create, user=user)
        src = create_contact(first_name='Leela', last_name='Turanga')
        src.languages.add(Language.objects.first())
        src.preferred_countries.add(FakeCountry.objects.create(name='Earth'))

        target = create_contact(first_name='Amy', last_name='Wong')

        copier = NotLanguageCopier(source=src, user=user)
        copier.copy_to(target)
        self.assertFalse(target.languages.all())
        self.assertFalse(target.preferred_countries.all())

    def test_custom_fields_copier(self):
        create_cf = partial(CustomField.objects.create, content_type=FakeOrganisation)
        cf_int        = create_cf(name='int',        field_type=CustomField.INT)
        cf_float      = create_cf(name='float',      field_type=CustomField.FLOAT)
        cf_bool       = create_cf(name='bool',       field_type=CustomField.BOOL)
        cf_str        = create_cf(name='str',        field_type=CustomField.STR)
        cf_date       = create_cf(name='date',       field_type=CustomField.DATETIME)
        cf_enum       = create_cf(name='enum',       field_type=CustomField.ENUM)
        cf_multi_enum = create_cf(name='multi_enum', field_type=CustomField.MULTI_ENUM)

        create_enum_value = CustomFieldEnumValue.objects.create
        enum1   = create_enum_value(custom_field=cf_enum,       value='Enum1')
        m_enum1 = create_enum_value(custom_field=cf_multi_enum, value='MEnum1')
        m_enum2 = create_enum_value(custom_field=cf_multi_enum, value='MEnum2')

        user = self.get_root_user()
        src = FakeOrganisation.objects.create(user=user, name='Planet express')

        cf_values = [
            {'cls': CustomFieldInteger,  'cfield': cf_int,   'value': 50},
            {'cls': CustomFieldFloat,    'cfield': cf_float, 'value': Decimal('10.5')},
            {'cls': CustomFieldBoolean,  'cfield': cf_bool,  'value': True},
            {'cls': CustomFieldString,   'cfield': cf_str,   'value': 'foobar'},
            {'cls': CustomFieldDateTime, 'cfield': cf_date,  'value': now()},
        ]
        for cf_value in cf_values:
            cf_value['cls'].objects.create(
                custom_field=cf_value['cfield'], entity=src, value=cf_value['value'],
            )

        CustomFieldEnum.objects.create(custom_field=cf_enum, entity=src, value=enum1)
        CustomFieldMultiEnum(
            custom_field=cf_multi_enum, entity=src,
        ).set_value_n_save([m_enum1, m_enum2])

        target = FakeOrganisation.objects.create(user=user, name='Slurm corp')

        copier = CustomFieldsCopier(source=src, user=user)
        copier.copy_to(target)

        def get_cf_values(cf, entity):
            return cf.value_class.objects.get(custom_field=cf, entity=entity)

        for cf_value in cf_values:
            self.assertEqual(
                cf_value['value'],
                get_cf_values(cf_value['cfield'], target).value,
            )

        self.assertEqual(enum1, get_cf_values(cf_enum, target).value)
        self.assertCountEqual(
            [m_enum1, m_enum2], get_cf_values(cf_multi_enum, target).value.all(),
        )

    def test_properties_copier(self):
        user = self.get_root_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        src = create_orga(name='Planet express')

        create_prop = partial(CremeProperty.objects.create, creme_entity=src)
        create_prop(type=self.ptype1)
        create_prop(type=self.ptype2)
        create_prop(type=self.ptype3)  # Not copiable

        target = create_orga(name='Slurm corp')

        copier = PropertiesCopier(source=src, user=user)

        # Queries:
        #  - 1 SELECT properties
        #  - 2 x Creation of property:
        #    - 2 SAVEPOINT (start & end)
        #    - 1 INSERT CremeProperty
        #    - 1 INSERT HistoryLine
        with self.assertNumQueries(9):
            copier.copy_to(target)

        self.assertCountEqual(
            [self.ptype1, self.ptype2],
            [p.type for p in target.properties.all()],
        )

    def test_strong_properties_copier(self):
        user = self.get_root_user()

        self.ptype2.set_subject_ctypes(FakeOrganisation, FakeContact)

        ptype4 = CremePropertyType.objects.create(text='Performant')
        ptype4.set_subject_ctypes(FakeOrganisation)

        src = FakeOrganisation.objects.create(user=user, name='Planet express')

        create_prop = partial(CremeProperty.objects.create, creme_entity=src)
        create_prop(type=self.ptype1)
        create_prop(type=self.ptype2)
        create_prop(type=self.ptype3)
        create_prop(type=ptype4)

        target = FakeContact.objects.create(user=user, first_name='Philip', last_name='Fry')
        copier = StrongPropertiesCopier(source=src, user=user)

        # Queries:
        #  - 1 SELECT the properties
        #  - 1 SELECT the ContentTypes constraints
        #  - 2 x Creation of property:
        #    - 2 SAVEPOINT (start & end)
        #    - 1 INSERT CremeProperty
        #    - 1 INSERT HistoryLine
        with self.assertNumQueries(10):
            copier.copy_to(target)

        self.assertCountEqual(
            [self.ptype1, self.ptype2],
            [p.type for p in target.properties.all()],
        )

    def test_relations_copier(self):
        user = self.get_root_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        src = create_orga(name='Planet express')

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Philip', last_name='Fry')
        contact2 = create_contact(first_name='Bender', last_name='Rodriguez')
        contact3 = create_contact(first_name='Hubert', last_name='Farnsworth')

        create_rel = partial(
            Relation.objects.create, user=user, subject_entity=src,
        )
        create_rel(type=self.rtype1, object_entity=contact1)
        create_rel(type=self.rtype2, object_entity=contact2)  # Internal
        create_rel(type=self.rtype3, object_entity=contact3)  # Not copiable

        target = create_orga(name='Slurm corp')
        copier = RelationsCopier(source=src, user=user)

        # with self.assertNumQueries(14):
        copier.copy_to(target)

        self.assertListEqual(
            [(self.rtype1.id, contact1.id)],
            [*target.relations.values_list('type', 'object_entity')],
        )

    def test_relations_copier__allowed_internal(self):
        rtype = self.rtype2

        class CustomRelationsCopier(RelationsCopier):
            allowed_internal_rtype_ids = [rtype.id]

        user = self.get_root_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        src    = create_orga(name='Planet express')
        target = create_orga(name='Slurm corp')

        contact = FakeContact.objects.create(
            user=user, first_name='Bender', last_name='Rodriguez',
        )
        Relation.objects.create(
            user=user, subject_entity=src, type=rtype, object_entity=contact,
        )

        copier = CustomRelationsCopier(source=src, user=user)
        copier.copy_to(target)
        self.assertListEqual(
            [(rtype.id, contact.id)],
            [*target.relations.values_list('type', 'object_entity')],
        )

    def test_strong_relations_copier(self):
        user = self.get_root_user()

        create_rtype = RelationType.objects.smart_update_or_create
        rtype4 = create_rtype(
            ('test-subject_ct_ok', 'CT OK', [FakeOrganisation, FakeContact]),
            ('test-object_ct_ok',  'CT OK (symmetrical)'),
        )[0]  # Subject constraint on ContentTypes is OK
        rtype5 = create_rtype(
            ('test-subject_ct_ko', 'CT KO', [FakeOrganisation]),
            ('test-object_ct_ko', 'CT KO (symmetrical)'),
        )[0]  # Subject constraint on ContentTypes is NOT OK
        rtype6 = create_rtype(
            ('test-subject_prop_1', 'Prop 1', [], [self.ptype1]),
            ('test-object_prop_1',  'Prop 1 (symmetrical)'),
        )[0]  # Subject constraint for Properties
        rtype7 = create_rtype(
            ('test-subject_prop_2', 'Prop 2', [], [self.ptype2]),
            ('test-object_prop_2', 'Prop 2 (symmetrical)'),
        )[0]  # Subject constraint for Properties

        src = FakeOrganisation.objects.create(user=user, name='Planet express')

        create_prop = CremeProperty.objects.create
        create_prop(type=self.ptype1, creme_entity=src)
        create_prop(type=self.ptype2, creme_entity=src)

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Philip', last_name='Fry')
        contact2 = create_contact(first_name='Bender', last_name='Rodriguez')
        contact3 = create_contact(first_name='Hubert', last_name='Farnsworth')

        create_rel = partial(
            Relation.objects.create, user=user, subject_entity=src,
        )
        create_rel(type=self.rtype1, object_entity=contact1)
        create_rel(type=self.rtype2, object_entity=contact2)  # Internal
        create_rel(type=self.rtype3, object_entity=contact3)  # Not copiable
        create_rel(type=rtype4,      object_entity=contact3)
        create_rel(type=rtype5,      object_entity=contact3)  # CT not OK
        create_rel(type=rtype6,      object_entity=contact2)
        create_rel(type=rtype7,      object_entity=contact2)  # Properties not OK

        target = FakeContact.objects.create(user=user, first_name='Philip', last_name='Fry')
        create_prop(type=self.ptype1, creme_entity=target)

        copier = StrongRelationsCopier(source=src, user=user)

        # with self.assertNumQueries(46):
        copier.copy_to(target)

        self.assertCountEqual(
            [
                (self.rtype1.id, contact1.id),
                (rtype4.id,      contact3.id),
                (rtype6.id,      contact2.id),
            ],
            [*target.relations.values_list('type', 'object_entity')],
        )

    def test_strong_relations_copier__allowed_internal(self):
        rtype = self.rtype2

        class CustomStrongRelationsCopier(StrongRelationsCopier):
            allowed_internal_rtype_ids = [rtype.id]

        user = self.get_root_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        src    = create_orga(name='Planet express')
        target = create_orga(name='Slurm corp')

        contact = FakeContact.objects.create(
            user=user, first_name='Bender', last_name='Rodriguez',
        )
        Relation.objects.create(
            user=user, subject_entity=src, type=rtype, object_entity=contact,
        )

        copier = CustomStrongRelationsCopier(source=src, user=user)
        copier.copy_to(target)
        self.assertListEqual(
            [(rtype.id, contact.id)],
            [*target.relations.values_list('type', 'object_entity')],
        )

    def test_relation_adder(self):
        rtype = self.rtype1

        class CustomRelationAdder(RelationAdder):
            rtype_id = rtype.id

        user = self.get_root_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        src    = create_orga(name='Planet express')
        target = create_orga(name='Slurm corp')

        copier = CustomRelationAdder(source=src, user=user)
        copier.copy_to(target)
        self.assertHaveRelation(subject=target, type=rtype, object=src)

    @parameterized.expand(['enabled', 'is_copiable'])
    def test_relation_adder__disabled(self, rtype_attr):
        rtype = self.rtype1
        setattr(rtype, rtype_attr, False)
        rtype.save()

        class CustomRelationAdder(RelationAdder):
            rtype_id = rtype.id

        user = self.get_root_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        src    = create_orga(name='Planet express')
        target = create_orga(name='Slurm corp')

        copier = CustomRelationAdder(source=src, user=user)
        copier.copy_to(target)
        self.assertHaveNoRelation(subject=target, type=rtype, object=src)

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
        Relation.objects.create(
            user=user,
            subject_entity=contact,
            type=self.rtype1.symmetric_type,
            object_entity=orga,
        )
        CremeProperty.objects.create(type=self.ptype1, creme_entity=contact)

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
