from decimal import Decimal
from functools import partial

from django.utils.timezone import now
from parameterized import parameterized

from creme.creme_core.core.copying import (
    CustomFieldsCopier,
    ManyToManyFieldsCopier,
    PropertiesCopier,
    RegularFieldsCopier,
    RelationAdder,
    RelationsCopier,
    StrongPropertiesCopier,
    StrongRelationsCopier,
)
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

        cls.rtype1 = RelationType.objects.builder(
            id='test-subject_employs', predicate='employs',
        ).symmetric(id='test-object_employs', predicate='is employed by').get_or_create()[0]
        cls.rtype2 = RelationType.objects.builder(
            id='test-subject_managed', predicate='is managed by',
            is_internal=True,
        ).symmetric(id='test-object_managed', predicate='manages').get_or_create()[0]
        cls.rtype3 = RelationType.objects.builder(
            id='test-subject_created', predicate='has been created by',
            is_copiable=False,
        ).symmetric(
            id='test-object_created', predicate='has created',
            is_copiable=False,
        ).get_or_create()[0]

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

        rtype4 = RelationType.objects.builder(
            id='test-subject_ct_ok', predicate='CT OK',
            models=[FakeOrganisation, FakeContact],
        ).symmetric(
            id='test-object_ct_ok', predicate='CT OK (symmetrical)',
        ).get_or_create()[0]
        rtype5 = RelationType.objects.builder(
            id='test-subject_ct_ko', predicate='CT KO', models=[FakeOrganisation],
        ).symmetric(
            id='test-object_ct_ko', predicate='CT KO (symmetrical)',
        ).get_or_create()[0]
        rtype6 = RelationType.objects.builder(
            id='test-subject_prop_1', predicate='Prop 1', properties=[self.ptype1],
        ).symmetric(
            id='test-object_prop_1', predicate='Prop 1 (symmetrical)',
        ).get_or_create()[0]
        rtype7 = RelationType.objects.builder(
            id='test-subject_prop_2', predicate='Prop 2', properties=[self.ptype2],
        ).symmetric(
            id='test-object_prop_2', predicate='Prop 2 (symmetrical)',
        ).get_or_create()[0]

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
