from datetime import date
from decimal import Decimal
from functools import partial
from uuid import UUID, uuid4

from django.contrib.contenttypes.models import ContentType
from django.db.models.query_utils import Q
from django.utils.formats import date_format
from django.utils.timezone import now
from django.utils.translation import gettext as _

import creme.creme_core.forms.entity_filter.fields as ef_fields
import creme.creme_core.forms.entity_filter.widgets as ef_widgets
from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    EF_REGULAR,
    entity_filter_registries,
    operands,
    operators,
)
from creme.creme_core.core.entity_filter.condition_handler import (
    CustomFieldConditionHandler,
    DateCustomFieldConditionHandler,
    DateRegularFieldConditionHandler,
    FilterConditionHandler,
    PropertyConditionHandler,
    RegularFieldConditionHandler,
    RelationConditionHandler,
    RelationSubFilterConditionHandler,
    SubFilterConditionHandler,
)
from creme.creme_core.core.snapshot import Snapshot
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    CustomField,
    CustomFieldEnum,
    CustomFieldEnumValue,
    CustomFieldMultiEnum,
    CustomFieldValue,
    EntityFilter,
    EntityFilterCondition,
    FakeContact,
    FakeDocument,
    FakeDocumentCategory,
    FakeFolder,
    FakeFolderCategory,
    FakeImage,
    FakeImageCategory,
    FakeInvoice,
    FakeInvoiceLine,
    FakeOrganisation,
    FakePosition,
    FakeReport,
    FakeSector,
    Language,
    Relation,
    RelationType,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.utils.date_range import date_range_registry
from creme.creme_core.utils.meta import FieldInfo


class _ConditionHandlerTestCase(CremeTestCase):
    def assertQPkIn(self, q, *instances, negated=False):
        self.assertIs(q.negated, negated)

        children = q.children
        self.assertEqual(1, len(children), children)

        k, v = children[0]
        self.assertEqual('pk__in', k)
        self.assertSetEqual({i.pk for i in instances}, {*v})


# TODO: query_for_related_conditions()
# TODO: query_for_parent_conditions()
class RegularFieldConditionHandlerTestCase(_ConditionHandlerTestCase):
    def test_init(self):
        user = self.get_root_user()

        fname = 'name'
        operator_id = operators.ICONTAINS
        value = 'Corp'
        handler = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            field_name=fname,
            operator_id=operator_id,
            values=[value],
        )
        self.assertEqual(FakeOrganisation, handler.model)
        self.assertEqual(EF_REGULAR, handler.efilter_type)
        self.assertIs(
            entity_filter_registries[EF_REGULAR], handler.efilter_registry,
        )
        self.assertIsNone(handler.subfilter_id)
        self.assertIs(handler.subfilter, False)
        self.assertEqual(fname,       handler._field_name)
        self.assertEqual(operator_id, handler._operator_id)
        self.assertEqual([value],     handler._values)

        self.assertIsNone(handler.error)
        self.assertIs(handler.applicable_on_entity_base, False)
        self.assertIs(handler.entities_are_distinct(), True)

        self.assertQEqual(
            Q(name__icontains=value),
            handler.get_q(user=user),
        )
        # TODO: test other operators

        finfo = handler.field_info
        self.assertIsInstance(finfo, FieldInfo)
        self.assertEqual(1, len(finfo))
        self.assertEqual(fname, finfo[0].name)

    def test_init__other_values(self):
        fname = 'first_name'
        operator_id = operators.STARTSWITH
        value = 'John'
        handler = RegularFieldConditionHandler(
            model=FakeContact,
            efilter_type=EF_CREDENTIALS,
            field_name=fname,
            operator_id=operator_id,
            values=[value],
        )
        self.assertEqual(FakeContact, handler.model)
        self.assertEqual(EF_CREDENTIALS, handler.efilter_type)
        self.assertIs(
            entity_filter_registries[EF_CREDENTIALS], handler.efilter_registry,
        )
        self.assertIsNone(handler.subfilter_id)
        self.assertIs(handler.subfilter, False)
        self.assertEqual(fname,       handler._field_name)
        self.assertEqual(operator_id, handler._operator_id)
        self.assertEqual([value],     handler._values)

    def test_property_error(self):
        self.assertEqual(
            "FakeOrganisation has no field named 'invalid'",
            RegularFieldConditionHandler(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                field_name='invalid',
                operator_id=operators.ICONTAINS,
                values=['Corp'],
            ).error,
        )
        self.assertEqual(
            "Operator ID '1234' is invalid",
            RegularFieldConditionHandler(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                field_name='name',
                operator_id=1234,  # <=
                values=['Corp'],
            ).error,
        )
        self.assertEqual(
            'FakeOrganisation.header_filter_search_field is not viewable',
            RegularFieldConditionHandler(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                field_name='header_filter_search_field',  # Not viewable
                operator_id=operators.ICONTAINS,
                values=['Corp'],
            ).error,
        )
        self.assertEqual(
            'FakeContact.cremeentity_ptr__description is not viewable',
            RegularFieldConditionHandler(
                efilter_type=EF_REGULAR,
                model=FakeContact,
                field_name='cremeentity_ptr__description',  # Root not viewable
                operator_id=operators.EQUALS,
                values=['contact'],
            ).error,
        )

    def test_applicable_on_entity_base(self):
        "Field belongs to CremeEntity."
        handler = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            field_name='description',
            operator_id=operators.ICONTAINS,
            values=['#important'],
        )
        self.assertIs(handler.applicable_on_entity_base, True)

    def test_build(self):
        model = FakeOrganisation
        fname = 'name'
        operator_id = operators.ICONTAINS
        value = 'Corp'
        handler = RegularFieldConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=model,
            name=fname,
            data={'operator': operator_id, 'values': [value]},
        )
        self.assertEqual(model, handler.model)
        self.assertEqual(EF_REGULAR, handler.efilter_type)
        self.assertIsNone(handler.subfilter_id)
        self.assertEqual(fname,       handler._field_name)
        self.assertEqual(operator_id, handler._operator_id)
        self.assertEqual([value],     handler._values)

    def test_build__other_values(self):
        model = FakeContact
        fname = 'last_name'
        operator_id = operators.ENDSWITH
        value = 'Doe'
        handler = RegularFieldConditionHandler.build(
            efilter_type=EF_CREDENTIALS,
            model=model,
            name=fname,
            data={'operator': operator_id, 'values': [value]},
        )
        self.assertEqual(model, handler.model)
        self.assertEqual(EF_CREDENTIALS, handler.efilter_type)
        self.assertIsNone(handler.subfilter_id)
        self.assertEqual(fname,       handler._field_name)
        self.assertEqual(operator_id, handler._operator_id)
        self.assertEqual([value],     handler._values)

    def test_build__errors(self):
        operator_id = operators.ICONTAINS
        with self.assertRaises(FilterConditionHandler.DataError):
            RegularFieldConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation, name='name',
                data=[],  # <= not a dict.
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            RegularFieldConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name='name',
                data={'operator': operator_id},
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            RegularFieldConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name='name',
                data={'values': ['Corp']},
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            RegularFieldConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name='name',
                data={
                    'values':   ['Corp'],
                    'operator': 'notanint',  # <==
                },
            )

    def test_formfield(self):
        user = self.get_root_user()

        formfield1 = RegularFieldConditionHandler.formfield(
            user=user, efilter_type=EF_REGULAR,
        )
        self.assertIsInstance(formfield1, ef_fields.RegularFieldsConditionsField)
        self.assertEqual(user, formfield1.user)
        self.assertIs(EF_REGULAR, formfield1.efilter_type)
        self.assertIs(formfield1.required, True)
        self.assertEqual(_('On regular fields'), formfield1.label)
        self.assertTrue(formfield1.help_text)

        widget1 = formfield1.widget
        self.assertIsInstance(widget1, ef_widgets.RegularFieldsConditionsWidget)
        self.assertIs(EF_REGULAR, widget1.efilter_type)

        # ---
        class MyField(ef_fields.RegularFieldsConditionsField):
            pass

        formfield2 = RegularFieldConditionHandler.formfield(
            form_class=MyField, required=False, efilter_type=EF_CREDENTIALS,
        )
        self.assertIsInstance(formfield2, MyField)
        self.assertIs(formfield2.required, False)
        self.assertIsNone(formfield2.user)
        self.assertIs(EF_CREDENTIALS, formfield2.efilter_type)

    def test_get_q__m2m(self):
        user = self.get_root_user()

        cat_id1 = 12
        cat_id2 = 45

        # One value ---
        handler1 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeDocument,
            field_name='categories',
            operator_id=operators.EQUALS,
            values=[cat_id1],
        )
        self.assertFalse(handler1.entities_are_distinct())

        self.assertQEqual(
            Q(categories__exact=cat_id1),
            handler1.get_q(user),
        )

        # Two values ---
        handler2 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeDocument,
            field_name='categories',
            operator_id=operators.EQUALS,
            values=[cat_id1, cat_id2],
        )
        self.assertFalse(handler2.entities_are_distinct())

        self.assertQEqual(
            Q(categories__in=[cat_id1, cat_id2]),
            handler2.get_q(user),
        )

    def test_accept__string(self):
        user = self.get_root_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        o1 = create_orga(name='Evil Corp', description='Very evil')
        o2 = create_orga(name='Genius incorporated')
        o3 = create_orga(name='Acme')

        handler1 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            field_name='name',
            operator_id=operators.ICONTAINS,
            values=['Corp'],
        )
        self.assertIs(handler1.accept(entity=o1, user=user), True)
        self.assertIs(handler1.accept(entity=o2, user=user), True)
        self.assertIs(handler1.accept(entity=o3, user=user), False)

        # Operator need a Boolean (not a string) (<True> version)
        handler2 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            field_name='description',
            operator_id=operators.ISEMPTY,
            values=[True],
        )
        self.assertIs(handler2.accept(entity=o1, user=user), False)
        self.assertIs(handler2.accept(entity=o2, user=user), True)

        # Operator need a Boolean (not a string) (<False> version)
        handler3 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            field_name='description',
            operator_id=operators.ISEMPTY,
            values=[False],
        )
        self.assertIs(handler3.accept(entity=o1, user=user), True)
        self.assertIs(handler3.accept(entity=o2, user=user), False)

    def test_accept__int(self):
        user = self.get_root_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        o1 = create_orga(name='Corp #1', capital=1000)
        o2 = create_orga(name='Corp #2', capital=500)
        o3 = create_orga(name='Corp #3', capital=None)

        handler1 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            field_name='capital',
            operator_id=operators.EQUALS,
            values=[1000],
        )
        self.assertIs(handler1.accept(entity=o1, user=user), True)
        self.assertIs(handler1.accept(entity=o2, user=user), False)
        self.assertIs(handler1.accept(entity=o3, user=user), False)

        # String format ---
        handler2 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            field_name='capital',
            operator_id=operators.EQUALS,
            values=['1000'],
        )
        self.assertIs(handler2.accept(entity=o1, user=user), True)
        self.assertIs(handler2.accept(entity=o2, user=user), False)
        self.assertIs(handler2.accept(entity=o3, user=user), False)

    def test_accept__boolean(self):
        user = self.get_root_user()

        create_contact = partial(FakeContact.objects.create, user=user, last_name='Doe')
        c1 = create_contact(loves_comics=True)
        c2 = create_contact(loves_comics=False)
        c3 = create_contact(loves_comics=None)

        handler1 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            field_name='loves_comics',
            operator_id=operators.EQUALS,
            values=[True],
        )
        self.assertIs(handler1.accept(entity=c1, user=user), True)
        self.assertIs(handler1.accept(entity=c2, user=user), False)
        self.assertIs(handler1.accept(entity=c3, user=user), False)

        # String format ---
        handler2 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            field_name='loves_comics',
            operator_id=operators.EQUALS,
            values=['True'],
        )
        self.assertIs(handler2.accept(entity=c1, user=user), True)
        self.assertIs(handler2.accept(entity=c2, user=user), False)
        self.assertIs(handler2.accept(entity=c3, user=user), False)

    def test_accept__decimal(self):
        user = self.get_root_user()
        handler = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeInvoiceLine,
            field_name='unit_price',
            operator_id=operators.GTE,
            values=['10.5'],
        )
        invoice = FakeInvoice.objects.create(user=user, name='Invoice#1')

        create_line = partial(
            FakeInvoiceLine.objects.create, user=user, linked_invoice=invoice,
        )
        l1 = create_line(unit_price=Decimal('11'))
        self.assertIs(handler.accept(entity=l1, user=user), True)

        l2 = create_line(unit_price=Decimal('10.4'))
        self.assertIs(handler.accept(entity=l2, user=user), False)

    def test_accept__fk(self):
        user = self.get_root_user()
        sector1, sector2 = FakeSector.objects.all()[:2]

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        o1 = create_orga(name='Evil Corp',   sector=sector1)
        o2 = create_orga(name='Genius inc.', sector=sector2)
        o3 = create_orga(name='Acme',        sector=None)

        handler1 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            field_name='sector',
            operator_id=operators.EQUALS,
            values=[sector1.id],
        )
        self.assertIs(handler1.accept(entity=o1, user=user), True)
        self.assertIs(handler1.accept(entity=o2, user=user), False)
        self.assertIs(handler1.accept(entity=o3, user=user), False)

        # String format ---
        handler2 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            field_name='sector',
            operator_id=operators.EQUALS,
            values=[str(sector1.id)],
        )
        self.assertIs(handler2.accept(entity=o1, user=user), True)
        self.assertIs(handler2.accept(entity=o2, user=user), False)
        self.assertIs(handler2.accept(entity=o3, user=user), False)

    def test_accept__fk_subfield(self):
        user = self.get_root_user()
        sector1, sector2 = FakeSector.objects.all()[:2]

        handler = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            field_name='sector__title',
            operator_id=operators.EQUALS,
            values=[sector1.title],
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        o1 = create_orga(name='Evil Corp', sector=sector1)
        self.assertIs(handler.accept(entity=o1, user=user), True)

        o2 = create_orga(name='Genius incorporated', sector=sector2)
        self.assertIs(handler.accept(entity=o2, user=user), False)

        o3 = create_orga(name='Acme', sector=None)
        self.assertIs(handler.accept(entity=o3, user=user), False)

    def test_accept__nested_fk(self):
        "Nested ForeignKey (sub-field)."
        user = self.get_root_user()

        create_cat = FakeFolderCategory.objects.create
        cat1 = create_cat(name='Pix')
        cat2 = create_cat(name='Video')

        create_folder = partial(FakeFolder.objects.create, user=user)
        folder1 = create_folder(title='Pictures', category=cat1)
        folder2 = create_folder(title='Videos',   category=cat2)
        folder3 = create_folder(title='Misc',     category=None)

        create_doc = partial(FakeDocument.objects.create, user=user)
        doc1 = create_doc(title='Pix#1',   linked_folder=folder1)
        doc2 = create_doc(title='Video#1', linked_folder=folder2)
        doc3 = create_doc(title='Text#1',  linked_folder=folder3)

        handler = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeDocument,
            field_name='linked_folder__category',
            operator_id=operators.EQUALS,
            values=[cat1.id],
        )
        self.assertIs(handler.accept(entity=doc1, user=user), True)
        self.assertIs(handler.accept(entity=doc2, user=user), False)
        self.assertIs(handler.accept(entity=doc3, user=user), False)

    def test_accept__nested_fk__nullable(self):
        "Nullable nested ForeignKey (sub-field)."
        user = self.get_root_user()

        create_efilter = EntityFilter.objects.create
        efilter1 = create_efilter(
            pk='creme_core-test_condition01',
            name='Filter#1',
            entity_type=FakeContact,
        )
        efilter2 = create_efilter(
            pk='creme_core-test_condition02',
            name='Filter#2',
            entity_type=FakeOrganisation,
        )

        create_report = partial(FakeReport.objects.create, user=user)
        r1 = create_report(name='Report1', ctype=FakeContact,      efilter=efilter1)
        r2 = create_report(name='Report2', ctype=FakeOrganisation, efilter=efilter2)
        r3 = create_report(name='Report3', ctype=FakeContact)

        handler = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeReport,
            field_name='efilter__entity_type',
            operator_id=operators.EQUALS,
            values=[efilter1.entity_type_id],
        )
        self.assertIs(handler.accept(entity=r1, user=user), True)
        self.assertIs(handler.accept(entity=r2, user=user), False)
        self.assertIs(handler.accept(entity=r3, user=user), False)

    def test_accept__fk_string(self):
        "Primary key is a CharField => BEWARE of ISEMPTY which needs a boolean value."
        user = self.get_root_user()

        create_efilter = partial(EntityFilter.objects.create, entity_type=FakeContact)
        efilter1 = create_efilter(pk='creme_core-test_condition01', name='Filter#1')
        efilter2 = create_efilter(pk='creme_core-test_condition02', name='Filter#2')

        create_report = partial(FakeReport.objects.create, user=user, ctype=FakeContact)
        r1 = create_report(name='Report1', efilter=efilter1)
        r2 = create_report(name='Report2', efilter=efilter2)
        r3 = create_report(name='Report3')

        handler1 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeReport,
            field_name='efilter',
            operator_id=operators.EQUALS,
            values=[efilter1.id],
        )
        self.assertIs(handler1.accept(entity=r1, user=user), True)
        self.assertIs(handler1.accept(entity=r2, user=user), False)
        self.assertIs(handler1.accept(entity=r3, user=user), False)

        # IS EMPTY (<True> version)---
        handler2 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeReport,
            field_name='efilter',
            operator_id=operators.ISEMPTY,
            values=[True],
        )
        self.assertIs(handler2.accept(entity=r1, user=user), False)
        self.assertIs(handler2.accept(entity=r2, user=user), False)
        self.assertIs(handler2.accept(entity=r3, user=user), True)

        # IS EMPTY (<False> version)---
        handler3 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeReport,
            field_name='efilter',
            operator_id=operators.ISEMPTY,
            values=[False],
        )
        self.assertIs(handler3.accept(entity=r1, user=user), True)
        self.assertIs(handler3.accept(entity=r2, user=user), True)
        self.assertIs(handler3.accept(entity=r3, user=user), False)

    def test_accept__operand(self):
        "Use operand resolving."
        user = self.get_root_user()
        handler = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            field_name='user',
            operator_id=operators.EQUALS,
            values=[operands.CurrentUserOperand.type_id],
        )

        create_orga = FakeOrganisation.objects.create
        o1 = create_orga(name='Evil Corp', user=user)
        self.assertIs(handler.accept(entity=o1, user=user), True)

        o2 = create_orga(name='Genius incorporated', user=self.create_user())
        self.assertIs(handler.accept(entity=o2, user=user), False)

    def test_accept__m2m(self):
        user = self.get_root_user()

        create_cat = FakeDocumentCategory.objects.create
        cat1 = create_cat(name='Picture')
        cat2 = create_cat(name='Music')

        create_doc = partial(
            FakeDocument.objects.create,
            user=user,
            linked_folder=FakeFolder.objects.create(user=user, title='My docs'),
        )
        doc1 = create_doc(title='Picture#1')
        doc1.categories.set([cat1])

        doc2 = create_doc(title='Music#1')
        doc2.categories.set([cat2])

        doc3 = create_doc(title='Video#1')

        # EQUALS ---
        handler1 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeDocument,
            field_name='categories',
            operator_id=operators.EQUALS,
            values=[cat1.id],
        )
        self.assertIs(handler1.accept(entity=doc1, user=user), True)
        self.assertIs(handler1.accept(entity=doc2, user=user), False)
        self.assertIs(handler1.accept(entity=doc3, user=user), False)

        # ISEMPTY ---
        handler2 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeDocument,
            field_name='categories',
            operator_id=operators.ISEMPTY,
            values=[True],
        )
        self.assertIs(handler2.accept(entity=doc1, user=user), False)
        self.assertIs(handler2.accept(entity=doc2, user=user), False)
        self.assertIs(handler2.accept(entity=doc3, user=user), True)

        # String format ---
        handler3 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeDocument,
            field_name='categories',
            operator_id=operators.EQUALS,
            values=[str(cat1.id)],
        )
        self.assertIs(handler3.accept(entity=doc1, user=user), True)
        self.assertIs(handler3.accept(entity=doc2, user=user), False)
        self.assertIs(handler3.accept(entity=doc3, user=user), False)

        # ISEMPTY (False) ---
        handler4 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeDocument,
            field_name='categories',
            operator_id=operators.ISEMPTY,
            values=[False],
        )
        self.assertIs(handler4.accept(entity=doc1, user=user), True)
        self.assertIs(handler4.accept(entity=doc2, user=user), True)
        self.assertIs(handler4.accept(entity=doc3, user=user), False)

    def test_accept__m2m_n_snapshot(self):
        user = self.get_root_user()
        doc = FakeDocument.objects.create(
            user=user, title='Picture#1',
            linked_folder=FakeFolder.objects.create(user=user, title='My docs'),
        )
        cat = FakeDocumentCategory.objects.create(name='Picture')

        doc = self.refresh(doc)  # to get a valid snapshot
        doc.categories.set([cat])

        handler = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeDocument,
            field_name='categories',
            operator_id=operators.EQUALS,
            values=[cat.id],
        )
        self.assertIs(handler.accept(entity=doc, user=user), True)

        # Snapshot => should use previous state
        self.assertFalse(handler.accept(
            entity=Snapshot.get_for_instance(doc).get_initial_instance(),
            user=user,
        ))

    def test_accept__m2m_subfield(self):
        user = self.get_root_user()

        create_cat = FakeDocumentCategory.objects.create
        cat1 = create_cat(name='Picture')
        cat2 = create_cat(name='Music')

        handler = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeDocument,
            field_name='categories__name',
            operator_id=operators.ICONTAINS,
            values=['pic'],
        )

        create_doc = partial(
            FakeDocument.objects.create,
            user=user,
            linked_folder=FakeFolder.objects.create(user=user, title='My docs'),
        )
        doc1 = self.refresh(create_doc(title='Picture#1'))  # refresh() for valid snapshot
        doc1.categories.set([cat1])
        self.assertIs(handler.accept(entity=doc1, user=user), True)

        doc2 = create_doc(title='Music#1')
        doc2.categories.set([cat2])
        self.assertIs(handler.accept(entity=doc2, user=user), False)

        doc3 = create_doc(title='Video#1')
        self.assertIs(handler.accept(entity=doc3, user=user), False)

        # Snapshot
        self.assertFalse(handler.accept(
            entity=Snapshot.get_for_instance(doc1).get_initial_instance(),
            user=user,
        ))

    def test_accept__nested_m2m(self):
        "Subfield is an M2M."
        user = self.get_root_user()
        cat1, cat2 = FakeImageCategory.objects.all()[:2]

        handler = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            field_name='image__categories',
            operator_id=operators.EQUALS,
            values=[cat1.id],
        )

        create_img = partial(FakeImage.objects.create, user=user)
        img1 = create_img(name='Img#1')
        img1.categories.set([cat1])

        img2 = create_img(name='Img#2')
        img2.categories.set([cat2])

        img3 = create_img(name='Img#3')

        create_contact = partial(FakeContact.objects.create, user=user)
        c1 = create_contact(last_name='Doe', image=img1)
        self.assertIs(handler.accept(entity=c1, user=user), True)

        c2 = create_contact(last_name='Doe', image=img2)
        self.assertIs(handler.accept(entity=c2, user=user), False)

        c3 = create_contact(last_name='Doe', image=img3)
        self.assertIs(handler.accept(entity=c3, user=user), False)

        c4 = create_contact(last_name='Doe')
        self.assertIs(handler.accept(entity=c4, user=user), False)

    def test_build_condition__operator_id(self):
        self.assertEqual(5, RegularFieldConditionHandler.type_id)

        fname = 'last_name'
        operator_id = operators.EQUALS
        value = 'Ikari'
        condition = RegularFieldConditionHandler.build_condition(
            model=FakeContact,
            operator=operator_id,
            field_name=fname, values=[value],
        )
        self.assertIsInstance(condition, EntityFilterCondition)
        self.assertIsNone(condition.pk)
        self.assertEqual(EF_REGULAR,                           condition.filter_type)
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(fname, condition.name)
        self.assertDictEqual(
            {'operator': operator_id, 'values': [value]}, condition.value
        )

        handler = RegularFieldConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            name=condition.name,
            data=condition.value,
        )
        self.assertIsInstance(handler, RegularFieldConditionHandler)
        self.assertEqual(FakeContact, handler.model)
        self.assertIsNone(handler.subfilter_id)
        self.assertIs(handler.subfilter, False)
        self.assertEqual(fname,       handler._field_name)
        self.assertEqual(operator_id, handler._operator_id)
        self.assertEqual([value],     handler._values)

    def test_build_condition__operator_class(self):
        fname = 'name'
        value = 'Nerv'
        condition = RegularFieldConditionHandler.build_condition(
            model=FakeOrganisation,
            operator=operators.IContainsOperator,
            field_name=fname, values=[value],
            filter_type=EF_CREDENTIALS,
        )
        self.assertIsInstance(condition, EntityFilterCondition)
        self.assertIsNone(condition.pk)
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(EF_CREDENTIALS, condition.filter_type)
        self.assertEqual(fname, condition.name)
        self.assertDictEqual(
            {'operator': operators.ICONTAINS, 'values': [value]},
            condition.value,
        )

    def test_build_condition__errors(self):
        ValueError = FilterConditionHandler.ValueError
        build_4_field = RegularFieldConditionHandler.build_condition

        self.assertRaises(
            ValueError, build_4_field,
            model=FakeContact, field_name='unknown_field',
            operator=operators.CONTAINS,
            values=['Misato'],
        )
        self.assertRaises(
            ValueError, build_4_field,
            model=FakeOrganisation, field_name='capital',
            operator=operators.GT,
            values=['Not an integer'],
        )
        self.assertRaises(
            ValueError, build_4_field,
            # NB: ISEMPTY => boolean
            model=FakeContact, field_name='description',
            operator=operators.ISEMPTY,
            values=['Not a boolean'],
        )
        self.assertRaises(
            ValueError, build_4_field,
            # NB: only one boolean is expected
            model=FakeContact, field_name='description',
            operator=operators.ISEMPTY,
            values=[True, True],
        )
        self.assertRaises(
            ValueError, build_4_field,
            model=FakeContact, field_name='civility__unknown',
            operator=operators.STARTSWITH,
            values=['Mist'],
        )
        self.assertRaises(
            ValueError, build_4_field,
            model=FakeOrganisation, field_name='capital',
            operator=operators.RANGE,
            values=[5000],
        )
        self.assertRaises(
            ValueError, build_4_field,
            model=FakeOrganisation, field_name='capital',
            operator=operators.RANGE,
            values=[5000, 50000, 100000],
        )
        self.assertRaises(
            ValueError, build_4_field,
            model=FakeOrganisation, field_name='capital',
            operator=operators.RANGE,
            values=['not an integer', 500000],
        )
        self.assertRaises(
            ValueError, build_4_field,
            model=FakeOrganisation, field_name='capital',
            operator=operators.RANGE,
            values=[500000, 'not an integer'],
        )

    def test_build_condition__emailfield(self):
        "Email + sub-part validation."
        build = partial(
            RegularFieldConditionHandler.build_condition,
            model=FakeOrganisation, field_name='email',
        )

        # Problem a part of an email address is not a valid email address
        with self.assertRaises(FilterConditionHandler.ValueError) as cm:
            build(operator=operators.EQUALS, values=['misato'])
        self.assertEqual(
            _('Condition on field «{field}»: {error}').format(
                field=_('Email address'),
                error=_('Enter a valid email address.'),
            ),
            str(cm.exception),
        )

        # ---
        with self.assertNoException():
            build(operator=operators.ISTARTSWITH, values=['misato'])

        # TODO: should not work (fix it in creme 2.6)
        with self.assertNoException():
            build(operator=operators.RANGE, values=['misato', 'yui'])

        with self.assertNoException():
            build(operator=operators.EQUALS, values=['misato@nerv.jp'])

    def test_build_condition__urlfield(self):
        "URL + sub-part validation."
        build = partial(
            RegularFieldConditionHandler.build_condition,
            model=FakeOrganisation, field_name='url_site',
        )

        # Problem a part of a URL is not a valid URL
        with self.assertRaises(FilterConditionHandler.ValueError) as cm:
            build(operator=operators.EQUALS, values=['misato'])
        self.assertEqual(
            _('Condition on field «{field}»: {error}').format(
                field=_('Web Site'),
                error=_('Enter a valid URL.'),
            ),
            str(cm.exception),
        )

        # ---
        with self.assertNoException():
            build(operator=operators.ISTARTSWITH, values=['http'])

        with self.assertNoException():
            build(operator=operators.CONTAINS_NOT, values=['http'])

        with self.assertNoException():
            build(operator=operators.EQUALS, values=['http://nerv.jp/misato'])

    def test_build_condition__credentials(self):
        "Credentials for entity FK."
        user = self.login_as_root_and_get()
        other_user = self.create_user(role=self.create_role())

        create_folder = FakeFolder.objects.create
        folder       = create_folder(title='Folder 01', user=user)
        other_folder = create_folder(title='Folder 02', user=other_user)

        build_4_field = partial(
            RegularFieldConditionHandler.build_condition,
            model=FakeDocument, operator=operators.EQUALS, field_name='linked_folder',
        )

        self.assertNoException(lambda: build_4_field(values=[str(folder.id)], user=user))
        self.assertNoException(lambda: build_4_field(values=[str(other_folder.id)], user=user))

        # other_user cannot link (not authenticated)
        with self.assertRaises(FilterConditionHandler.ValueError):
            build_4_field(values=[str(folder.id)], user=other_user)

    def test_get_q(self):
        "ForeignKey."
        user = self.get_root_user()
        sector_id = 3
        handler = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            field_name='sector',
            operator_id=operators.EQUALS,
            values=[sector_id],
        )

        self.assertQEqual(
            # Q(sector_id__exact=sector_id),  TODO ??
            Q(sector__exact=sector_id),
            handler.get_q(user)
        )

    def test_description(self):
        user = self.get_root_user()

        value = 'Corp'
        handler = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            field_name='name',
            operator_id=operators.CONTAINS,
            values=[value],
        )
        self.assertEqual(
            _('«{field}» contains {values}').format(
                field=_('Name'),
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            handler.description(user),
        )

    def test_description__operator(self):
        "Other field & operator."
        user = self.get_root_user()

        value = 'Spiegel'
        handler = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            field_name='last_name',
            operator_id=operators.STARTSWITH,
            values=[value],
        )
        self.assertEqual(
            _('«{field}» starts with {values}').format(
                field=_('Last name'),
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            handler.description(user),
        )

    def test_description__fk(self):
        user = self.get_root_user()
        position1, position2 = FakePosition.objects.all()[:2]

        handler1 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            field_name='position',
            operator_id=operators.EQUALS,
            values=[position1.id, position2.id, self.UNUSED_PK],
        )

        with self.assertNumQueries(1):
            description = handler1.description(user)

        self.assertEqual(
            _('«{field}» is {values}').format(
                field=_('Position'),
                values=_('{first} or {last}').format(
                    first=_('«{enum_value}»').format(enum_value=position1),
                    last=_('«{enum_value}»').format(enum_value=position2),
                ),
            ),
            description,
        )

        with self.assertNumQueries(0):
            handler1.description(user)

        # ---
        handler2 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            field_name='position',
            operator_id=operators.EQUALS,
            values=[position1.id, 'notanint'],
        )
        self.assertEqual(
            _('«{field}» is {values}').format(
                field=_('Position'),
                values=_('«{enum_value}»').format(enum_value='???')
            ),
            handler2.description(user),
        )

        # Operator IS_EMPTY (+False) => should not retrieve any instance
        handler3 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            field_name='position',
            operator_id=operators.ISEMPTY,
            values=[False],
        )
        self.assertEqual(
            _('«{field}» is not empty').format(field=_('Position')),
            handler3.description(user),
        )

        # Operator IS_EMPTY (+True)
        handler4 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            field_name='position',
            operator_id=operators.ISEMPTY,
            values=[True],
        )
        self.assertEqual(
            _('«{field}» is empty').format(field=_('Position')),
            handler4.description(user),
        )

    def test_description__fk_to_entity(self):
        "ForeignKey to CremeEntity."
        user = self.login_as_standard()
        self.add_credentials(user.role, own=['VIEW'])

        create_folder = partial(FakeFolder.objects.create, user=user)
        folder1 = create_folder(title='Pix')
        folder2 = create_folder(title='Music')
        folder3 = create_folder(title='ZZZ',  user=self.get_root_user())

        handler = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeDocument,
            field_name='linked_folder',
            operator_id=operators.EQUALS,
            values=[folder1.id, folder2.id, folder3.id],
        )
        fmt = _('«{enum_value}»').format
        self.assertEqual(
            _('«{field}» is {values}').format(
                field=_('Folder'),
                values=_('{first} or {last}').format(
                    first=f'{fmt(enum_value=folder2)}, {fmt(enum_value=folder1)}',
                    last=fmt(enum_value=_('Entity #{id} (not viewable)').format(id=folder3.id)),
                ),
            ),
            handler.description(user)
        )

    def test_description__m2m(self):
        user = self.get_root_user()
        cat1, cat2 = FakeImageCategory.objects.all()[:2]

        handler1 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeImage,
            field_name='categories',
            operator_id=operators.EQUALS,
            values=[cat1.id, cat2.id, self.UNUSED_PK],
        )

        with self.assertNumQueries(1):
            description = handler1.description(user)

        fmt_value = _('«{enum_value}»').format
        self.assertEqual(
            _('«{field}» is {values}').format(
                field=_('Categories'),
                values=_('{first} or {last}').format(
                    first=fmt_value(enum_value=cat1),
                    last=fmt_value(enum_value=cat2),
                ),
            ),
            description,
        )

        with self.assertNumQueries(0):
            handler1.description(user)

        # ---
        handler2 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeImage,
            field_name='categories',
            operator_id=operators.EQUALS,
            values=[cat1.id, 'notanint'],
        )
        self.assertEqual(
            _('«{field}» is {values}').format(
                field=_('Categories'),
                values=fmt_value(enum_value='???')
            ),
            handler2.description(user),
        )

    def test_description__field_choices(self):
        "Field with 'choices'."
        user = self.get_root_user()

        value = FakeInvoiceLine.Discount.PERCENT
        handler = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeInvoiceLine,
            field_name='discount_unit',
            operator_id=operators.EQUALS,
            values=[value],
        )
        self.assertEqual(
            _('«{field}» is {values}').format(
                field=_('Discount Unit'),
                values=_('«{enum_value}»').format(enum_value=_('Percent')),
            ),
            handler.description(user),
        )

    def test_description__booleanfield(self):
        user = self.get_root_user()

        handler1 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            field_name='is_a_nerd',
            operator_id=operators.EQUALS,
            values=[True],
        )
        self.assertEqual(
            _('«{field}» is {values}').format(
                field=_('Is a Nerd'),
                values=_('«{enum_value}»').format(enum_value=_('True')),
            ),
            handler1.description(user),
        )

        # ----
        handler2 = RegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            field_name='is_a_nerd',
            operator_id=operators.EQUALS,
            values=[False],
        )
        self.assertEqual(
            _('«{field}» is {values}').format(
                field=_('Is a Nerd'),
                values=_('«{enum_value}»').format(enum_value=_('False')),
            ),
            handler2.description(user),
        )

    def test_operand_currentuser(self):
        user1 = self.get_root_user()
        user2 = self.create_user(index=0)
        user3 = self.create_user(index=1)
        team = self.create_team('NOIR', user3)

        value = operands.CurrentUserOperand.type_id

        with self.assertNoException():
            handler = RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator=operators.EQUALS,
                field_name='user',
                values=[value],
            )

        self.assertQEqual(Q(user__exact=user1.id), handler.get_q(user1))
        self.assertQEqual(Q(user__exact=user2.id), handler.get_q(user2))
        self.assertQEqual(Q(user__in=[user3.id, team.id]), handler.get_q(user3))

        self.assertEqual(
            _('«{field}» is {values}').format(
                field=_('Owner user'),
                values=_('«{enum_value}»').format(enum_value=_('Current user')),
            ),
            handler.description(user1),
        )

        # ---
        with self.assertNoException():
            RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator=operators.EQUALS,
                # OK it's a CharField, you could search "__currentuser__" if you want...
                field_name='last_name',
                values=[value],
            )

        with self.assertRaises(FilterConditionHandler.ValueError):
            RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator=operators.EQUALS,
                field_name='birthday',   # <= DateField -> KO
                values=[value],
            )

        with self.assertRaises(FilterConditionHandler.ValueError):
            RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator=operators.EQUALS,
                field_name='sector',   # <= ForeignKey but not related to User
                values=[value],
            )


class DateRegularFieldConditionHandlerTestCase(_ConditionHandlerTestCase):
    def test_init(self):
        fname = 'created'
        range_name = 'previous_year'
        handler = DateRegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            field_name=fname,
            date_range=range_name,
        )

        self.assertEqual(FakeOrganisation, handler.model)
        self.assertIsNone(handler.subfilter_id)
        self.assertIs(handler.subfilter, False)
        self.assertEqual(fname, handler._field_name)
        self.assertEqual(range_name, handler._range_name)
        self.assertIsNone(handler._start)
        self.assertIsNone(handler._end)

        self.assertIsNone(handler.error)
        self.assertIs(handler.applicable_on_entity_base, True)

        self.assertQEqual(
            Q(
                **date_range_registry.get_range(name=range_name)
                                     .get_q_dict(field=fname, now=now())
            ),
            handler.get_q(user=None),
        )

    def test_property_error(self):
        "<error> property."
        self.assertEqual(
            "FakeOrganisation has no field named 'unknown'",
            DateRegularFieldConditionHandler(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                field_name='unknown',
                date_range='previous_year',
            ).error,
        )
        self.assertEqual(
            "'sector' is not a date field",
            DateRegularFieldConditionHandler(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                field_name='sector',
                date_range='previous_year',
            ).error,
        )
        # TODO: need a not viewable date field in fake models.
        # self.assertEqual(
        #     'FakeOrganisation.header_filter_search_field is not viewable',
        #     DateRegularFieldConditionHandler(
        #         efilter_type=EF_REGULAR,
        #         model=FakeOrganisation,
        #         field_name='not_viewable_date_field',
        #         date_range='previous_year',
        #     ).error,
        # )

    def test_applicable_on_entity_base(self):
        handler = DateRegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            field_name='creation_date',
            date_range='current_quarter',
        )
        self.assertIs(handler.applicable_on_entity_base, False)

    def test_build(self):
        model = FakeContact
        fname = 'modified'
        range_name = 'yesterday'
        handler = DateRegularFieldConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=model,
            name=fname,
            data={'name': range_name},
        )
        self.assertEqual(model, handler.model)
        self.assertEqual(EF_REGULAR, handler.efilter_type)
        self.assertIsNone(handler.subfilter_id)
        self.assertEqual(fname,      handler._field_name)
        self.assertEqual(range_name, handler._range_name)
        self.assertIsNone(handler._start)
        self.assertIsNone(handler._end)

    def test_build__other_values(self):
        model = FakeOrganisation
        fname = 'created'
        range_name = 'current_year'
        handler = DateRegularFieldConditionHandler.build(
            efilter_type=EF_CREDENTIALS,
            model=model,
            name=fname,
            data={'name': range_name},
        )
        self.assertEqual(model, handler.model)
        self.assertEqual(EF_CREDENTIALS, handler.efilter_type)
        self.assertIsNone(handler.subfilter_id)
        self.assertEqual(fname,      handler._field_name)
        self.assertEqual(range_name, handler._range_name)
        self.assertIsNone(handler._start)
        self.assertIsNone(handler._end)

    def test_build__errors(self):
        with self.assertRaises(FilterConditionHandler.DataError):
            DateRegularFieldConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation, name='created',
                data=[],  # <= not a dict.
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            DateRegularFieldConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name='created',
                data={'start': 'notadict'},
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            DateRegularFieldConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name='created',
                data={'start': {'foo': 'bar'}},
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            DateRegularFieldConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name='created',
                data={'start': {'year': 'notanint'}},
            )

    def test_formfield(self):
        user = self.get_root_user()

        formfield1 = DateRegularFieldConditionHandler.formfield(user=user)
        self.assertIsInstance(formfield1, ef_fields.DateFieldsConditionsField)
        self.assertEqual(user, formfield1.user)
        self.assertIs(formfield1.required, True)
        self.assertEqual(_('On date fields'), formfield1.label)
        self.assertFalse(formfield1.help_text)

        class MyField(ef_fields.DateFieldsConditionsField):
            pass

        formfield2 = DateRegularFieldConditionHandler.formfield(form_class=MyField, required=False)
        self.assertIsInstance(formfield2, MyField)
        self.assertIs(formfield2.required, False)
        self.assertIsNone(formfield2.user)

    def test_accept__date(self):
        user = self.get_root_user()

        current_year = now().year
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        o1 = create_orga(
            name='Evil Corp',
            creation_date=date(year=current_year, month=2, day=2),
        )
        o2 = create_orga(
            name='Genius incorporated',
            creation_date=date(year=current_year - 1, month=2, day=2),
        )
        o3 = create_orga(name='Acme')

        handler = DateRegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            field_name='creation_date',
            date_range='current_year',
        )
        self.assertIs(handler.accept(entity=o1, user=user), True)
        self.assertIs(handler.accept(entity=o2, user=user), False)
        self.assertIs(handler.accept(entity=o3, user=user), False)

    def test_accept__datetime(self):
        user = self.get_root_user()

        current_year = now().year
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        o1 = create_orga(
            name='Evil Corp',
            created=self.create_datetime(year=current_year, month=2, day=2),
        )
        o2 = create_orga(
            name='Genius incorporated',
            created=self.create_datetime(year=current_year - 1, month=2, day=2),
        )

        handler = DateRegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            field_name='created',
            date_range='current_year',
        )
        self.assertIs(handler.accept(entity=o1, user=user), True)
        self.assertIs(handler.accept(entity=o2, user=user), False)

    def test_accept__fk_subfield(self):
        user = self.get_root_user()

        current_year = now().year
        create_img = partial(FakeImage.objects.create, user=user)
        img1 = create_img(
            name='Evil Corp logo',
            created=self.create_datetime(year=current_year, month=2, day=2),
        )
        img2 = create_img(
            name='Genius incorporated logo',
            created=self.create_datetime(year=current_year - 1, month=2, day=2),
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        o1 = create_orga(name='Evil Corp', image=img1)
        o2 = create_orga(name='Genius incorporated', image=img2)

        handler = DateRegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            field_name='image__created',
            date_range='current_year',
        )
        self.assertIs(handler.accept(entity=o1, user=user), True)
        self.assertIs(handler.accept(entity=o2, user=user), False)

    def test_build_condition(self):
        # GTE ---
        fname1 = 'birthday'
        condition1 = DateRegularFieldConditionHandler.build_condition(
            model=FakeContact, field_name=fname1,
            start=date(year=2000, month=1, day=1),
        )
        self.assertIsInstance(condition1, EntityFilterCondition)
        self.assertIsNone(condition1.pk)
        self.assertEqual(EF_REGULAR,                               condition1.filter_type)
        self.assertEqual(DateRegularFieldConditionHandler.type_id, condition1.type)
        self.assertEqual(fname1,                                   condition1.name)
        self.assertDictEqual(
            {'start': {'day': 1, 'month': 1, 'year': 2000}},
            condition1.value,
        )

        handler1 = DateRegularFieldConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            name=condition1.name,
            data=condition1.value,
        )
        self.assertIsInstance(handler1, DateRegularFieldConditionHandler)
        self.assertEqual(FakeContact, handler1.model)
        self.assertIsNone(handler1.subfilter_id)
        self.assertIs(handler1.subfilter, False)
        self.assertEqual(fname1, handler1._field_name)
        self.assertIsNone(handler1._range_name)
        self.assertIsNone(handler1._end)
        self.assertEqual(
            self.create_datetime(year=2000, month=1, day=1),
            handler1._start,
        )

        # LTE ---
        condition2 = DateRegularFieldConditionHandler.build_condition(
            model=FakeOrganisation, field_name='created',
            end=date(year=1999, month=12, day=31),
        )
        self.assertEqual('created', condition2.name)
        self.assertDictEqual(
            {'end': {'day': 31, 'month': 12, 'year': 1999}},
            condition2.value,
        )

        handler2 = DateRegularFieldConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            name=condition2.name,
            data=condition2.value,
        )
        self.assertEqual(FakeOrganisation, handler2.model)
        self.assertIsNone(handler2._range_name)
        self.assertIsNone(handler2._start)
        self.assertEqual(
            self.create_datetime(year=1999, month=12, day=31),
            handler2._end,
        )

        # RANGE ---
        condition3 = DateRegularFieldConditionHandler.build_condition(
            model=FakeContact, field_name='birthday',
            start=date(year=2001, month=1, day=1),
            end=date(year=2001, month=12, day=1),
        )
        self.assertDictEqual(
            {
                'start': {'day': 1, 'month': 1,  'year': 2001},
                'end':   {'day': 1, 'month': 12, 'year': 2001},
            },
            condition3.value,
        )

        # YESTERDAY ---
        range_name = 'yesterday'
        condition4 = DateRegularFieldConditionHandler.build_condition(
            model=FakeContact, field_name='birthday', date_range=range_name,
        )
        self.assertDictEqual({'name': range_name}, condition4.value)

        handler4 = DateRegularFieldConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            name=condition4.name,
            data=condition4.value,
        )
        self.assertEqual(range_name, handler4._range_name)
        self.assertIsNone(handler4._start)
        self.assertIsNone(handler4._end)

        # Filter_type ---
        condition5 = DateRegularFieldConditionHandler.build_condition(
            model=FakeContact, field_name='birthday', date_range=range_name,
            filter_type=EF_CREDENTIALS,
        )
        self.assertEqual(EF_CREDENTIALS, condition5.filter_type)
        self.assertIsNone(condition5.handler)

    def test_build_condition__errors(self):
        ValueError = FilterConditionHandler.ValueError
        build_cond = DateRegularFieldConditionHandler.build_condition

        self.assertRaises(
            ValueError, build_cond,
            model=FakeContact, field_name='unknown_field', start=date(year=2001, month=1, day=1)
        )
        self.assertRaises(
            ValueError, build_cond,
            # Not a date field
            model=FakeContact, field_name='first_name', start=date(year=2001, month=1, day=1)
        )
        self.assertRaises(
            ValueError, build_cond,
            model=FakeContact, field_name='birthday',  # No date given
        )
        self.assertRaises(
            ValueError, build_cond,
            model=FakeContact, field_name='birthday', date_range='unknown_range',
        )

    def test_description(self):
        user = self.get_root_user()

        handler = DateRegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            field_name='created',
            date_range='previous_year',
        )
        self.assertEqual(
            _('«{field}» is «{value}»').format(
                field=_('Creation date'), value=_('Previous year'),
            ),
            handler.description(user=user),
        )

    def test_description__named_range(self):
        "Other field & named range."
        user = self.get_root_user()

        handler = DateRegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            field_name='birthday',
            date_range='next_month',
        )
        self.assertEqual(
            _('«{field}» is «{value}»').format(
                field=_('Birthday'), value=_('Next month'),
            ),
            handler.description(user=user),
        )

    def test_description__custom_range(self):
        user = self.get_root_user()

        start = date(year=2000, month=6, day=1)
        handler1 = DateRegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            field_name='birthday',
            start=start,
        )
        self.assertEqual(
            _('«{field}» starts «{date}»').format(
                field=_('Birthday'),
                date=date_format(start, 'DATE_FORMAT'),
            ),
            handler1.description(user=user),
        )

        # ---
        end = date(year=2000, month=7, day=1)
        handler2 = DateRegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            field_name='birthday',
            end=end,
        )
        self.assertEqual(
            _('«{field}» ends «{date}»').format(
                field=_('Birthday'),
                date=date_format(end, 'DATE_FORMAT'),
            ),
            handler2.description(user=user),
        )

        # ---
        handler3 = DateRegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            field_name='birthday',
            start=start,
            end=end,
        )
        self.assertEqual(
            _('«{field}» is between «{start}» and «{end}»').format(
                field=_('Birthday'),
                start=date_format(start, 'DATE_FORMAT'),
                end=date_format(end, 'DATE_FORMAT'),
            ),
            handler3.description(user=user),
        )

        # ---
        handler4 = DateRegularFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            field_name='birthday',
        )
        self.assertEqual('??', handler4.description(user=user))


class CustomFieldConditionHandlerTestCase(_ConditionHandlerTestCase):
    def test_init__customfield_uuid(self):
        custom_field = CustomField.objects.create(
            name='Is a foundation?', field_type=CustomField.BOOL,
            content_type=FakeOrganisation,
        )

        operator_id = operators.EQUALS
        value = 'True'
        rname = 'customfieldboolean'
        handler = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field.uuid,
            operator_id=operator_id,
            values=[value],
            related_name=rname,
        )

        self.assertEqual(FakeOrganisation, handler.model)
        self.assertIsNone(handler.subfilter_id)
        self.assertIs(handler.subfilter, False)
        self.assertEqual(custom_field.uuid, handler._custom_field_uuid)
        self.assertEqual(operator_id,       handler._operator_id)
        self.assertEqual([value],           handler._values)
        self.assertEqual(rname,             handler._related_name)

        self.assertIsNone(handler.error)
        self.assertIs(handler.applicable_on_entity_base, True)

        with self.assertNumQueries(1):
            q = handler.get_q(user=None)

        self.assertQEqual(
            Q(pk__in=FakeOrganisation.objects.none()),
            q,
        )

        # ---
        with self.assertNumQueries(0):
            cfield2 = handler.custom_field

        self.assertEqual(custom_field, cfield2)

        with self.assertNumQueries(0):
            handler.custom_field  # NOQA

        # ---
        with self.assertRaises(TypeError):
            CustomFieldConditionHandler(
                efilter_type=EF_REGULAR,
                # model=FakeOrganisation,  # <== missing
                custom_field=custom_field.uuid,
                operator_id=operator_id,
                values=[value],
                related_name=rname,
            )

        # ---
        with self.assertRaises(TypeError):
            CustomFieldConditionHandler(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                custom_field=custom_field.uuid,
                operator_id=operator_id,
                values=[value],
                # related_name=rname,  # <== missing
            )

    def test_init__customfield_instance(self):
        custom_field = CustomField.objects.create(
            name='Is a foundation?', field_type=CustomField.BOOL,
            content_type=FakeOrganisation,
        )

        operator_id = operators.EQUALS
        value = 'True'
        handler = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            custom_field=custom_field,
            operator_id=operator_id,
            values=[value],
        )

        self.assertEqual(FakeOrganisation,     handler.model)
        self.assertEqual(custom_field.uuid,    handler._custom_field_uuid)
        self.assertEqual('customfieldboolean', handler._related_name)

    def test_property_error(self):
        "<error> property."
        custom_field = CustomField.objects.create(
            name='Base line', field_type=CustomField.STR,
            content_type=FakeOrganisation,
        )

        handler1 = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            operator_id=1234,  # <=
            values=['Corp'],
        )
        self.assertEqual("Operator ID '1234' is invalid", handler1.error)

        # ---
        handler2 = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field.uuid,
            operator_id=operators.EQUALS,
            values=['True'],
            related_name='invalid',  # <===
        )
        self.assertEqual("related_name 'invalid' is invalid", handler2.error)

    def test_build(self):
        model = FakeContact
        cfield_uuid = uuid4()
        operator_id = operators.GT
        value = 25
        rname = 'customfieldinteger'
        handler = CustomFieldConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=model,
            name=str(cfield_uuid),
            data={
                'operator': operator_id,
                'rname': rname,
                'values': [value],
            },
        )
        self.assertEqual(model, handler.model)
        self.assertEqual(EF_REGULAR, handler.efilter_type)
        self.assertIsNone(handler.subfilter_id)
        self.assertEqual(cfield_uuid, handler._custom_field_uuid)
        self.assertEqual(operator_id, handler._operator_id)
        self.assertEqual([value],     handler._values)
        self.assertEqual(rname,       handler._related_name)

    def test_build__other_values(self):
        model = FakeOrganisation
        cfield_uuid = uuid4()
        operator_id = operators.STARTSWITH
        value = 'foo'
        rname = 'customfieldstring'
        handler = CustomFieldConditionHandler.build(
            efilter_type=EF_CREDENTIALS,
            model=model,
            name=str(cfield_uuid),
            data={
                'operator': operator_id,
                'rname': rname,
                'values': [value],
            },
        )
        self.assertEqual(model, handler.model)
        self.assertEqual(EF_CREDENTIALS, handler.efilter_type)
        self.assertIsNone(handler.subfilter_id)
        self.assertEqual(cfield_uuid, handler._custom_field_uuid)
        self.assertEqual(operator_id, handler._operator_id)
        self.assertEqual([value],     handler._values)
        self.assertEqual(rname,       handler._related_name)

    def test_build__invalid_data(self):
        cfield_id = '6'
        operator_id = operators.GT
        value = 25
        rname = 'customfieldinteger'

        with self.assertRaises(FilterConditionHandler.DataError):
            CustomFieldConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation, name=cfield_id,
                data=[],  # <= not a dict.
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            CustomFieldConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name=cfield_id,
                data={
                    'operator': operator_id,
                    'rname': rname,
                    # 'value': [value],  # Missing
                },
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            CustomFieldConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name=cfield_id,
                data={
                    'operator': operator_id,
                    # 'rname': rname,  # Missing
                    'value': [value],
                },
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            CustomFieldConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name=cfield_id,
                data={
                    # 'operator': operator_id,   # Missing
                    'rname': rname,
                    'value': [value],
                },
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            CustomFieldConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name=cfield_id,
                data={
                    'operator': 'notanint',  # <==
                    'rname': rname,
                    'value': [value],
                },
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            CustomFieldConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name='notanint',  # <==
                data={
                    'operator': operator_id,
                    'rname': rname,
                    'value': [value],
                },
            )

    def test_formfield(self):
        user = self.get_root_user()

        formfield1 = CustomFieldConditionHandler.formfield(user=user)
        self.assertIsInstance(formfield1, ef_fields.CustomFieldsConditionsField)
        self.assertEqual(user, formfield1.user)
        self.assertIs(formfield1.required, True)
        self.assertEqual(_('On custom fields'), formfield1.label)
        self.assertFalse(formfield1.help_text)

        class MyField(ef_fields.CustomFieldsConditionsField):
            pass

        formfield2 = CustomFieldConditionHandler.formfield(form_class=MyField, required=False)
        self.assertIsInstance(formfield2, MyField)
        self.assertIs(formfield2.required, False)
        self.assertIsNone(formfield2.user)

    def test_accept__int(self):
        user = self.get_root_user()

        custom_field = CustomField.objects.create(
            name='Number of ships', field_type=CustomField.INT,
            content_type=FakeOrganisation,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        dragons   = create_orga(name='Red Dragons')
        swordfish = create_orga(name='Swordfish')

        klass = custom_field.value_class

        def set_cfvalue(entity, value):
            klass(custom_field=custom_field, entity=entity).set_value_n_save(value)

        set_cfvalue(bebop,   4)
        set_cfvalue(dragons, 100)

        handler1 = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            operator_id=operators.EQUALS,
            values=[4],
            related_name='customfieldint',
        )
        self.assertIs(handler1.accept(entity=bebop,     user=user), True)
        self.assertIs(handler1.accept(entity=dragons,   user=user), False)
        self.assertIs(handler1.accept(entity=swordfish, user=user), False)

        # String format ---
        handler2 = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            operator_id=operators.EQUALS,
            values=['4'],
            related_name='customfieldint',
        )
        self.assertIs(handler2.accept(entity=bebop,     user=user), True)
        self.assertIs(handler2.accept(entity=dragons,   user=user), False)
        self.assertIs(handler2.accept(entity=swordfish, user=user), False)

    def test_accept__bool(self):
        user = self.get_root_user()

        custom_field = CustomField.objects.create(
            name='Accept bounties?', field_type=CustomField.BOOL,
            content_type=FakeOrganisation,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        dragons   = create_orga(name='Red Dragons')
        swordfish = create_orga(name='Swordfish')

        klass = custom_field.value_class

        def set_cfvalue(entity, value):
            klass(custom_field=custom_field, entity=entity).set_value_n_save(value)

        set_cfvalue(bebop,   True)
        set_cfvalue(dragons, False)

        handler1 = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field.uuid,
            operator_id=operators.EQUALS,
            values=[True],
            related_name='customfieldboolean',
        )
        self.assertIs(handler1.accept(entity=bebop,     user=user), True)
        self.assertIs(handler1.accept(entity=dragons,   user=user), False)
        self.assertIs(handler1.accept(entity=swordfish, user=user), False)

        # String format ---
        handler2 = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field.uuid,
            operator_id=operators.EQUALS,
            values=['True'],
            related_name='customfieldboolean',
        )
        self.assertIs(handler2.accept(entity=bebop,     user=user), True)
        self.assertIs(handler2.accept(entity=dragons,   user=user), False)
        self.assertIs(handler2.accept(entity=swordfish, user=user), False)

    def test_accept__decimal(self):
        user = self.get_root_user()

        custom_field = CustomField.objects.create(
            name='Average turnover', field_type=CustomField.FLOAT,
            content_type=FakeOrganisation,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        dragons   = create_orga(name='Red Dragons')
        swordfish = create_orga(name='Swordfish')

        klass = custom_field.value_class

        def set_cfvalue(entity, value):
            klass(custom_field=custom_field, entity=entity).set_value_n_save(value)

        set_cfvalue(bebop,   Decimal('1000.5'))
        set_cfvalue(dragons, Decimal('4000.8'))

        handler = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            operator_id=operators.LTE,
            values=['2000'],
            related_name='customfieldfloat',
        )
        self.assertIs(handler.accept(entity=bebop,     user=user), True)
        self.assertIs(handler.accept(entity=dragons,   user=user), False)
        self.assertIs(handler.accept(entity=swordfish, user=user), False)

    def test_accept__enum(self):
        user = self.get_root_user()

        custom_field = CustomField.objects.create(
            name='Type of ship', field_type=CustomField.ENUM,
            content_type=FakeOrganisation,
        )

        create_evalue = partial(
            CustomFieldEnumValue.objects.create, custom_field=custom_field,
        )
        enum_small  = create_evalue(value='Small')
        enum_medium = create_evalue(value='Medium')
        enum_big    = create_evalue(value='Big')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='RedTail')

        create_enum = partial(CustomFieldEnum.objects.create, custom_field=custom_field)
        create_enum(entity=swordfish, value=enum_small)
        create_enum(entity=bebop,     value=enum_big)

        # EQUALS ---
        handler1 = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            operator_id=operators.EQUALS,
            values=[enum_small.id, enum_medium.id],
            related_name='customfieldenum',
        )
        self.assertIs(handler1.accept(entity=swordfish, user=user), True)
        self.assertIs(handler1.accept(entity=bebop,     user=user), False)
        self.assertIs(handler1.accept(entity=redtail,   user=user), False)

        # ISEMPTY ---
        handler2 = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            operator_id=operators.ISEMPTY,
            values=[True],
            related_name='customfieldenum',
        )
        self.assertIs(handler2.accept(entity=swordfish, user=user), False)
        self.assertIs(handler2.accept(entity=bebop,     user=user), False)
        self.assertIs(handler2.accept(entity=redtail,   user=user), True)

        # String format ---
        handler3 = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            operator_id=operators.EQUALS,
            values=[str(enum_small.id), str(enum_medium.id)],
            related_name='customfieldenum',
        )
        self.assertIs(handler3.accept(entity=swordfish, user=user), True)
        self.assertIs(handler3.accept(entity=bebop,     user=user), False)
        self.assertIs(handler3.accept(entity=redtail,   user=user), False)

    def test_accept__multienum(self):
        user = self.get_root_user()

        custom_field = CustomField.objects.create(
            name='Type of ship', field_type=CustomField.MULTI_ENUM,
            content_type=FakeOrganisation,
        )

        create_evalue = partial(
            CustomFieldEnumValue.objects.create, custom_field=custom_field,
        )
        enum_attack = create_evalue(value='Attack')
        enum_fret   = create_evalue(value='Fret')
        enum_house  = create_evalue(value='House')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='RedTail')

        cf_memum = partial(CustomFieldMultiEnum, custom_field=custom_field)
        cf_memum(entity=swordfish).set_value_n_save([enum_attack])
        cf_memum(entity=bebop).set_value_n_save([enum_fret, enum_house])

        # EQUALS ---
        handler1 = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            operator_id=operators.EQUALS,
            values=[enum_attack.id, enum_fret.id],
            related_name='customfieldmultienum',
        )
        self.assertIs(handler1.accept(entity=swordfish, user=user), True)
        self.assertIs(handler1.accept(entity=redtail,   user=user), False)
        self.assertIs(handler1.accept(entity=bebop,     user=user), True)

        # ISEMPTY ---
        handler2 = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            operator_id=operators.ISEMPTY,
            values=[True],
            related_name='customfieldmultienum',
        )
        self.assertIs(handler2.accept(entity=swordfish, user=user), False)
        self.assertIs(handler2.accept(entity=bebop,     user=user), False)
        self.assertIs(handler2.accept(entity=redtail,   user=user), True)

        # String format ---
        handler3 = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            operator_id=operators.EQUALS,
            values=[str(enum_attack.id), str(enum_fret.id)],
            related_name='customfieldmultienum',
        )
        self.assertIs(handler3.accept(entity=swordfish, user=user), True)
        self.assertIs(handler3.accept(entity=redtail,   user=user), False)
        self.assertIs(handler3.accept(entity=bebop,     user=user), True)

        # ISEMPTY (False) ---
        handler4 = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            operator_id=operators.ISEMPTY,
            values=[False],
            related_name='customfieldmultienum',
        )
        self.assertIs(handler4.accept(entity=swordfish, user=user), True)
        self.assertIs(handler4.accept(entity=bebop,     user=user), True)
        self.assertIs(handler4.accept(entity=redtail,   user=user), False)

    def test_accept__snapshot__int(self):
        user = self.get_root_user()

        custom_field = CustomField.objects.create(
            name='Number of ships', field_type=CustomField.INT,
            content_type=FakeOrganisation,
        )

        bebop = FakeOrganisation.objects.create(user=user, name='Bebop')
        CustomFieldValue.save_values_for_entities(custom_field, [bebop], 2)

        handler = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            operator_id=operators.GTE,
            values=[4],
            related_name='customfieldint',
        )

        bebop = self.refresh(bebop)
        CustomFieldValue.save_values_for_entities(custom_field, [bebop], 5)
        self.assertTrue(handler.accept(entity=bebop, user=user))
        self.assertFalse(handler.accept(
            entity=Snapshot.get_for_instance(bebop).get_initial_instance(),
            user=user,
        ))

    def test_accept__snapshot__multi_enum(self):
        user = self.get_root_user()

        custom_field = CustomField.objects.create(
            name='Type of ship', field_type=CustomField.MULTI_ENUM,
            content_type=FakeOrganisation,
        )

        create_evalue = partial(
            CustomFieldEnumValue.objects.create, custom_field=custom_field,
        )
        enum_attack = create_evalue(value='Attack')
        enum_fret   = create_evalue(value='Fret')
        enum_house  = create_evalue(value='House')

        bebop = FakeOrganisation.objects.create(user=user, name='Bebop')
        CustomFieldValue.save_values_for_entities(custom_field, [bebop], [enum_house])

        handler = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            operator_id=operators.EQUALS,
            values=[enum_attack.id, enum_fret.id],
            related_name='customfieldmultienum',
        )

        bebop = self.refresh(bebop)
        CustomFieldValue.save_values_for_entities(custom_field, [bebop], [enum_fret, enum_house])
        self.assertTrue(handler.accept(entity=bebop, user=user))
        self.assertFalse(handler.accept(
            entity=Snapshot.get_for_instance(bebop).get_initial_instance(),
            user=user,
        ))

    def test_build_condition__operator_id(self):
        custom_field = CustomField.objects.create(
            name='Size (cm)', field_type=CustomField.INT, content_type=FakeContact,
        )

        operator_id = operators.LTE
        value = 155
        rname = 'customfieldinteger'
        condition = CustomFieldConditionHandler.build_condition(
            custom_field=custom_field,
            operator=operator_id,
            values=[value],
        )
        self.assertIsInstance(condition, EntityFilterCondition)
        self.assertIsNone(condition.pk)
        self.assertEqual(EF_REGULAR,                          condition.filter_type)
        self.assertEqual(CustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(custom_field.uuid),              condition.name)
        self.assertDictEqual(
            {
                'operator': operator_id,
                'values': [str(value)],
                'rname': rname,
            },
            condition.value,
        )

        handler = CustomFieldConditionHandler.build(
            efilter_type=EF_REGULAR, model=FakeContact,
            name=condition.name, data=condition.value,
        )
        self.assertIsInstance(handler, CustomFieldConditionHandler)
        self.assertEqual(FakeContact, handler.model)
        self.assertIsNone(handler.subfilter_id)
        self.assertIs(handler.subfilter, False)
        self.assertEqual(custom_field.uuid, handler._custom_field_uuid)
        self.assertEqual(operator_id,       handler._operator_id)
        self.assertEqual([str(value)],      handler._values)
        self.assertEqual(rname,             handler._related_name)

    def test_build_condition__operator_class(self):
        custom_field = CustomField.objects.create(
            name='Size (cm)', field_type=CustomField.INT, content_type=FakeContact,
        )

        value = 155
        rname = 'customfieldinteger'
        condition = CustomFieldConditionHandler.build_condition(
            custom_field=custom_field,
            operator=operators.LTEOperator,
            values=[value],
            filter_type=EF_CREDENTIALS,
        )
        self.assertIsInstance(condition, EntityFilterCondition)
        self.assertIsNone(condition.pk)
        self.assertEqual(EF_CREDENTIALS, condition.filter_type)
        self.assertEqual(CustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(custom_field.uuid), condition.name)
        self.assertDictEqual(
            {
                'operator': operators.LTE,
                'values': [str(value)],
                'rname': rname,
            },
            condition.value,
        )

    def test_build_condition__errors(self):
        create_cf = partial(CustomField.objects.create, content_type=FakeContact)
        cf_int = create_cf(name='size (cm)', field_type=CustomField.INT)

        ValueError = FilterConditionHandler.ValueError
        build_cond = CustomFieldConditionHandler.build_condition

        self.assertRaises(
            ValueError, build_cond,
            custom_field=cf_int, operator=1216, values=[155],  # Invalid operator
        )
        with self.assertRaises(ValueError) as cm:
            build_cond(
                custom_field=cf_int, operator=operators.CONTAINS, values=['not an int'],
            )
        self.assertEqual(
            _('Condition on field «{field}»: {error}').format(
                field=cf_int.name,
                error=_('Enter a whole number.'),
            ),
            str(cm.exception),
        )

        cf_date = create_cf(name='Day', field_type=CustomField.DATE)
        with self.assertRaises(ValueError) as cm1:
            build_cond(custom_field=cf_date, operator=operators.EQUALS, values=[2011])
        self.assertEqual(
            'CustomFieldConditionHandler.build_condition(): '
            'does not manage DATE/DATETIME CustomFields',
            str(cm1.exception),
        )

        cf_datetime = create_cf(name='Day+time', field_type=CustomField.DATETIME)
        with self.assertRaises(ValueError) as cm2:
            build_cond(custom_field=cf_datetime, operator=operators.EQUALS, values=[2011])
        self.assertEqual(
            'CustomFieldConditionHandler.build_condition(): '
            'does not manage DATE/DATETIME CustomFields',
            str(cm2.exception),
        )

        cf_bool = create_cf(name='Cute?', field_type=CustomField.BOOL)
        self.assertRaises(
            ValueError, build_cond,
            custom_field=cf_bool, operator=operators.CONTAINS, values=[True],  # Bad operator
        )

    def test_build_condition__bool(self):
        "BOOL => unsupported operator."
        custom_field = CustomField.objects.create(
            name='cute ??',
            content_type=FakeContact,
            field_type=CustomField.BOOL,
        )

        with self.assertRaises(FilterConditionHandler.ValueError) as err:
            CustomFieldConditionHandler.build_condition(
                custom_field=custom_field, operator=operators.GT, values=[True],
            )

        self.assertEqual(
            str(err.exception),
            'CustomFieldConditionHandler.build_condition(): '
            'BOOL type is only compatible with EQUALS, EQUALS_NOT and ISEMPTY operators'
        )

    def test_get_q_bool(self):
        "get_q() not empty."
        user = self.get_root_user()

        custom_field = CustomField.objects.create(
            name='Is a ship?', field_type=CustomField.BOOL,
            content_type=FakeOrganisation,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop = create_orga(name='Bebop')
        create_orga(name='Swordfish')
        dragons = create_orga(name='Red Dragons')

        klass = custom_field.value_class

        def set_cfvalue(entity, value):
            klass(custom_field=custom_field, entity=entity).set_value_n_save(value)

        set_cfvalue(bebop,   True)
        set_cfvalue(dragons, False)

        handler1 = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            operator_id=operators.EQUALS,
            values=[True],
            related_name='customfieldboolean',
        )
        self.assertQEqual(
            # NB: the nested QuerySet is not compared by the query, but by its result...
            Q(pk__in=FakeOrganisation.objects.filter(id=bebop.id).values_list('id', flat=True)),
            handler1.get_q(user=None),
        )

        handler2 = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            operator_id=operators.EQUALS,
            values=[False],
            related_name='customfieldboolean',
        )
        self.assertQEqual(
            Q(pk__in=FakeOrganisation.objects.filter(id=dragons.id).values_list('id', flat=True)),
            handler2.get_q(user=None),
        )

        # String format
        handler3 = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            operator_id=operators.EQUALS,
            values=['False'],
            related_name='customfieldboolean',
        )
        self.assertQEqual(
            Q(pk__in=FakeOrganisation.objects.filter(id=dragons.id).values_list('id', flat=True)),
            handler3.get_q(user=None),
        )

    def test_description(self):
        user = self.get_root_user()

        custom_field = CustomField.objects.create(
            name='Size', field_type=CustomField.INT,
            content_type=FakeContact,
        )

        value = 25
        handler = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            operator_id=operators.EQUALS,
            values=[value],
        )
        self.assertEqual(
            _('«{field}» is {values}').format(
                field=custom_field.name,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            handler.description(user),
        )

    def test_description__operator(self):
        "Other field & operator."
        user = self.get_root_user()

        custom_field = CustomField.objects.create(
            name='Degree', field_type=CustomField.STR,
            content_type=FakeContact,
        )

        value = 'phD'
        handler = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            operator_id=operators.CONTAINS,
            values=[value],
        )
        self.assertEqual(
            _('«{field}» contains {values}').format(
                field=custom_field.name,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            handler.description(user),
        )

    def test_description__enum(self):
        user = self.get_root_user()

        custom_field = CustomField.objects.create(
            name='Mark', field_type=CustomField.ENUM,
            content_type=FakeContact,
        )

        create_evalue = partial(
            CustomFieldEnumValue.objects.create, custom_field=custom_field,
        )
        enum_A = create_evalue(value='A')
        enum_B = create_evalue(value='B')

        handler1 = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            custom_field=custom_field,
            operator_id=operators.EQUALS,
            values=[enum_A.id, enum_B.id, self.UNUSED_PK],
        )

        with self.assertNumQueries(1):
            description = handler1.description(user)

        fmt = _('«{enum_value}»').format
        self.assertEqual(
            _('«{field}» is {values}').format(
                field=custom_field.name,
                values=_('{first} or {last}').format(
                    first=fmt(enum_value=enum_A),
                    last=fmt(enum_value=enum_B),
                ),
            ),
            description,
        )

        with self.assertNumQueries(0):
            handler1.description(user)

        # ---
        handler2 = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            custom_field=custom_field,
            operator_id=operators.EQUALS,
            values=[enum_A.id, 'notanint'],
        )
        self.assertEqual(
            _('«{field}» is {values}').format(
                field=custom_field.name,
                values=_('«{enum_value}»').format(enum_value='???')
            ),
            handler2.description(user),
        )

    def test_description__multienum(self):
        user = self.get_root_user()

        custom_field = CustomField.objects.create(
            name='Colors', field_type=CustomField.MULTI_ENUM,
            content_type=FakeContact,
        )

        create_evalue = partial(
            CustomFieldEnumValue.objects.create, custom_field=custom_field,
        )
        enum_1 = create_evalue(value='Red')
        enum_2 = create_evalue(value='Green')

        handler = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            custom_field=custom_field,
            operator_id=operators.EQUALS,
            values=[enum_1.id, enum_2.id, self.UNUSED_PK],
        )

        fmt = _('«{enum_value}»').format
        self.assertEqual(
            _('«{field}» is {values}').format(
                field=custom_field.name,
                values=_('{first} or {last}').format(
                    first=fmt(enum_value=enum_1),
                    last=fmt(enum_value=enum_2),
                ),
            ),
            handler.description(user)
        )

    def test_description__deleted_customfield(self):
        user = self.get_root_user()

        handler = CustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=uuid4(),
            related_name='customfieldinteger',
            operator_id=operators.EQUALS,
            values=[42],
        )
        self.assertEqual('???', handler.description(user))


class DateCustomFieldConditionHandlerTestCase(_ConditionHandlerTestCase):
    def test_init__datetime(self):
        custom_field = CustomField.objects.create(
            name='First fight',
            content_type=FakeOrganisation,
            field_type=CustomField.DATETIME,
        )

        rname = 'customfielddatetime'
        range_name = 'next_year'
        handler = DateCustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field.uuid,
            related_name=rname,
            date_range=range_name,
        )

        self.assertEqual(FakeOrganisation, handler.model)
        self.assertIsNone(handler.subfilter_id)
        self.assertIs(handler.subfilter, False)
        self.assertEqual(custom_field.uuid, handler._custom_field_uuid)
        self.assertEqual(rname,             handler._related_name)
        self.assertEqual(range_name,        handler._range_name)
        self.assertIsNone(handler._start)
        self.assertIsNone(handler._end)

        self.assertIsNone(handler.error)
        self.assertIs(handler.applicable_on_entity_base, True)

        # ---
        with self.assertNumQueries(1):
            cfield2 = handler.custom_field

        self.assertEqual(custom_field, cfield2)

        with self.assertNumQueries(0):
            handler.custom_field  # NOQA

        # ---
        self.assertQEqual(
            Q(pk__in=FakeOrganisation.objects.none()),
            handler.get_q(user=None),
        )

    def test_init__datetime_start_end(self):
        "Pass a DATETIME CustomField instance + start/end."
        custom_field = CustomField.objects.create(
            name='First fight',
            content_type=FakeOrganisation,
            field_type=CustomField.DATETIME,
        )

        start = self.create_datetime(year=2019, month=8, day=1)
        end   = self.create_datetime(year=2019, month=8, day=31)
        handler = DateCustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            custom_field=custom_field,
            start=start,
            end=end,
        )
        self.assertEqual(FakeOrganisation,      handler.model)
        self.assertEqual(custom_field.uuid,     handler._custom_field_uuid)
        self.assertEqual('customfielddatetime', handler._related_name)
        self.assertIsNone(handler._range_name)
        self.assertEqual(start, handler._start)
        self.assertEqual(end,   handler._end)

        # ---
        with self.assertNumQueries(0):
            cfield2 = handler.custom_field

        self.assertEqual(custom_field, cfield2)

    def test_init__date(self):
        custom_field = CustomField.objects.create(
            name='First fight',
            content_type=FakeOrganisation,
            field_type=CustomField.DATE,
        )

        rname = 'customfielddate'
        range_name = 'previous_year'
        handler = DateCustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field.uuid,
            related_name=rname,
            date_range=range_name,
        )

        self.assertEqual(FakeOrganisation, handler.model)
        self.assertIsNone(handler.subfilter_id)
        self.assertIs(handler.subfilter, False)
        self.assertEqual(custom_field.uuid, handler._custom_field_uuid)
        self.assertEqual(rname,             handler._related_name)
        self.assertEqual(range_name,        handler._range_name)
        self.assertIsNone(handler._start)
        self.assertIsNone(handler._end)

    def test_property_error(self):
        handler = DateCustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=uuid4(),
            date_range='yesterday',
            related_name='invalid',  # <===
        )
        self.assertEqual("related_name 'invalid' is invalid", handler.error)

    def test_build__datetime(self):
        model = FakeContact
        cfield_uuid = uuid4()
        range_name = 'today'
        rname = 'customfielddatetime'
        handler = DateCustomFieldConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=model,
            name=str(cfield_uuid),
            data={
                'rname': rname,
                'name':  range_name,
            },
        )
        self.assertEqual(model, handler.model)
        self.assertEqual(EF_REGULAR, handler.efilter_type)
        self.assertIsNone(handler.subfilter_id)
        self.assertEqual(cfield_uuid, handler._custom_field_uuid)
        self.assertEqual(rname,       handler._related_name)
        self.assertEqual(range_name,  handler._range_name)
        self.assertIsNone(handler._start)
        self.assertIsNone(handler._end)

    def test_build__date(self):
        model = FakeOrganisation
        cfield_uuid = uuid4()
        range_name = 'today'
        rname = 'customfielddate'
        handler = DateCustomFieldConditionHandler.build(
            efilter_type=EF_CREDENTIALS,
            model=model,
            name=str(cfield_uuid),
            data={
                'rname': rname,
                'name':  range_name,
            },
        )
        self.assertEqual(model, handler.model)
        self.assertEqual(EF_CREDENTIALS, handler.efilter_type)
        self.assertIsNone(handler.subfilter_id)
        self.assertEqual(cfield_uuid, handler._custom_field_uuid)
        self.assertEqual(rname,       handler._related_name)
        self.assertEqual(range_name,  handler._range_name)
        self.assertIsNone(handler._start)
        self.assertIsNone(handler._end)

    def test_build__errors(self):
        cfield_id = '6'
        rname = 'customfielddatetime'

        with self.assertRaises(FilterConditionHandler.DataError):
            DateCustomFieldConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation, name=cfield_id,
                data=[],  # <= not a dict.
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            DateCustomFieldConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name=cfield_id,
                data={},  # 'rname': rname,  # Missing
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            DateCustomFieldConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name='notanint',  # <==
                data={'rname': rname},
            )

    def test_formfield(self):
        user = self.get_root_user()

        formfield1 = DateCustomFieldConditionHandler.formfield(user=user)
        self.assertIsInstance(formfield1, ef_fields.DateCustomFieldsConditionsField)
        self.assertEqual(user, formfield1.user)
        self.assertIs(formfield1.required, True)
        self.assertEqual(_('On date custom fields'), formfield1.label)
        self.assertFalse(formfield1.help_text)

        class MyField(ef_fields.DateCustomFieldsConditionsField):
            pass

        formfield2 = DateCustomFieldConditionHandler.formfield(form_class=MyField, required=False)
        self.assertIsInstance(formfield2, MyField)
        self.assertIs(formfield2.required, False)
        self.assertIsNone(formfield2.user)

    def test_accept(self):
        user = self.get_root_user()

        custom_field = CustomField.objects.create(
            name='Inauguration',
            content_type=FakeOrganisation,
            field_type=CustomField.DATE,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        o1 = create_orga(name='Evil Corp')
        o2 = create_orga(name='Genius incorporated')
        o3 = create_orga(name='Acme')

        klass = custom_field.value_class

        def set_cfvalue(entity, value):
            klass(custom_field=custom_field, entity=entity).set_value_n_save(value)

        current_year = now().year
        set_cfvalue(o1, date(year=current_year, month=2, day=2))
        set_cfvalue(o2, date(year=current_year - 1, month=2, day=2))

        handler = DateCustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            related_name='customfielddate',
            date_range='current_year',
        )
        self.assertIs(handler.accept(entity=o1, user=user), True)
        self.assertIs(handler.accept(entity=o2, user=user), False)
        self.assertIs(handler.accept(entity=o3, user=user), False)

    def test_build_condition__datetime(self):
        custom_field = CustomField.objects.create(
            name='First fight',
            content_type=FakeContact,
            field_type=CustomField.DATETIME,
        )

        rname = 'customfielddatetime'
        condition1 = DateCustomFieldConditionHandler.build_condition(
            custom_field=custom_field, start=date(year=2015, month=4, day=1),
        )
        self.assertIsInstance(condition1, EntityFilterCondition)
        self.assertIsNone(condition1.pk)
        self.assertEqual(EF_REGULAR,                              condition1.filter_type)
        self.assertEqual(DateCustomFieldConditionHandler.type_id, condition1.type)
        self.assertEqual(str(custom_field.uuid),                  condition1.name)
        self.assertDictEqual(
            {
                'rname': rname,
                'start': {'day': 1, 'month': 4, 'year': 2015},
            },
            condition1.value,
        )

        handler1 = DateCustomFieldConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=FakeContact, name=condition1.name, data=condition1.value,
        )
        self.assertIsInstance(handler1, DateCustomFieldConditionHandler)
        self.assertEqual(FakeContact, handler1.model)
        self.assertIsNone(handler1.subfilter_id)
        self.assertIs(handler1.subfilter, False)
        self.assertEqual(custom_field.uuid, handler1._custom_field_uuid)
        self.assertEqual(rname,             handler1._related_name)
        self.assertIsNone(handler1._range_name)
        self.assertIsNone(handler1._end)
        self.assertEqual(
            self.create_datetime(year=2015, month=4, day=1),
            handler1._start,
        )

        # ---
        condition2 = DateCustomFieldConditionHandler.build_condition(
            custom_field=custom_field, start=date(year=2015, month=4, day=1),
            filter_type=EF_CREDENTIALS,
        )
        self.assertEqual(EF_CREDENTIALS, condition2.filter_type)
        self.assertIsNone(condition2.handler)

    def test_build_condition__date(self):
        custom_field = CustomField.objects.create(
            name='First fight',
            content_type=FakeContact,
            field_type=CustomField.DATE,
        )

        rname = 'customfielddate'
        condition1 = DateCustomFieldConditionHandler.build_condition(
            custom_field=custom_field, start=date(year=2015, month=4, day=1),
        )
        self.assertIsInstance(condition1, EntityFilterCondition)
        self.assertIsNone(condition1.pk)
        self.assertEqual(EF_REGULAR,                              condition1.filter_type)
        self.assertEqual(DateCustomFieldConditionHandler.type_id, condition1.type)
        self.assertEqual(str(custom_field.uuid),                  condition1.name)
        self.assertDictEqual(
            {
                'rname': rname,
                'start': {'day': 1, 'month': 4, 'year': 2015},
            },
            condition1.value,
        )

        handler1 = DateCustomFieldConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=FakeContact, name=condition1.name, data=condition1.value,
        )
        self.assertIsInstance(handler1, DateCustomFieldConditionHandler)
        self.assertEqual(FakeContact, handler1.model)
        self.assertIsNone(handler1.subfilter_id)
        self.assertIs(handler1.subfilter, False)
        self.assertEqual(custom_field.uuid, handler1._custom_field_uuid)
        self.assertEqual(rname,             handler1._related_name)
        self.assertIsNone(handler1._range_name)
        self.assertIsNone(handler1._end)
        self.assertEqual(
            self.create_datetime(year=2015, month=4, day=1),
            handler1._start,
        )

        # ---
        condition2 = DateCustomFieldConditionHandler.build_condition(
            custom_field=custom_field, start=date(year=2015, month=4, day=1),
            filter_type=EF_CREDENTIALS,
        )
        self.assertEqual(EF_CREDENTIALS, condition2.filter_type)
        self.assertIsNone(condition2.handler)

    def test_build_condition__errors(self):
        ValueError = FilterConditionHandler.ValueError
        build_cond = DateCustomFieldConditionHandler.build_condition

        create_cf = partial(CustomField.objects.create, content_type=FakeContact)
        custom_field1 = create_cf(name='First flight', field_type=CustomField.INT)  # Not a DATE
        self.assertRaises(
            ValueError, build_cond,
            custom_field=custom_field1, date_range='in_future',
        )

        custom_field2 = create_cf(name='Day', field_type=CustomField.DATETIME)
        self.assertRaises(
            ValueError, build_cond,
            custom_field=custom_field2,  # No date is given
        )
        self.assertRaises(
            ValueError, build_cond,
            custom_field=custom_field2, date_range='unknown_range',
        )

    def test_get_q__datetime(self):
        "get_q() not empty (DATETIME)."
        user = self.get_root_user()

        custom_field = CustomField.objects.create(
            name='First fight', field_type=CustomField.DATETIME,
            content_type=FakeOrganisation,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop = create_orga(name='Bebop')
        create_orga(name='Swordfish')
        dragons = create_orga(name='Red Dragons')

        klass = custom_field.value_class

        def set_cfvalue(entity, value):
            klass(custom_field=custom_field, entity=entity).set_value_n_save(value)

        year = now().year
        set_cfvalue(bebop,   self.create_datetime(year=year - 1, month=6, day=5))
        set_cfvalue(dragons, self.create_datetime(year=year - 2, month=6, day=5))

        handler = DateCustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            related_name='customfielddatetime',
            date_range='previous_year',
        )

        self.assertQEqual(
            # NB: the nested QuerySet is not compared by the query, but by its result...
            Q(pk__in=FakeOrganisation.objects.filter(id=bebop.id).values_list('id', flat=True)),
            handler.get_q(user=None)
        )

    def test_get_q__date(self):
        "get_q() not empty (DATE)."
        user = self.get_root_user()

        custom_field = CustomField.objects.create(
            name='First fight', field_type=CustomField.DATE,
            content_type=FakeOrganisation,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop = create_orga(name='Bebop')
        create_orga(name='Swordfish')
        dragons = create_orga(name='Red Dragons')

        klass = custom_field.value_class

        def set_cfvalue(entity, value):
            klass(custom_field=custom_field, entity=entity).set_value_n_save(value)

        year = now().year
        set_cfvalue(bebop,   date(year=year - 1, month=6, day=5))
        set_cfvalue(dragons, date(year=year - 2, month=6, day=5))

        handler = DateCustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            custom_field=custom_field,
            related_name='customfielddate',
            date_range='previous_year',
        )

        self.assertQEqual(
            # NB: the nested QuerySet is not compared by the query, but by its result...
            Q(pk__in=FakeOrganisation.objects.filter(id=bebop.id).values_list('id', flat=True)),
            handler.get_q(user=None),
        )

    def test_description(self):
        user = self.get_root_user()

        custom_field = CustomField.objects.create(
            name='First fight', field_type=CustomField.DATETIME,
            content_type=FakeOrganisation,
        )

        handler1 = DateCustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            custom_field=custom_field,
            date_range='previous_year',
        )
        self.assertEqual(
            _('«{field}» is «{value}»').format(
                field=custom_field.name, value=_('Previous year'),
            ),
            handler1.description(user=user),
        )

        # Other named range
        handler2 = DateCustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            custom_field=custom_field,
            date_range='current_year',
        )
        self.assertEqual(
            _('«{field}» is «{value}»').format(
                field=custom_field.name, value=_('Current year'),
            ),
            handler2.description(user=user),
        )

    def test_description__custom_range(self):
        user = self.get_root_user()

        custom_field = CustomField.objects.create(
            name='First fight', field_type=CustomField.DATETIME,
            content_type=FakeOrganisation,
        )

        start = date(year=2000, month=6, day=1)
        handler1 = DateCustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            custom_field=custom_field,
            start=start,
        )
        self.assertEqual(
            _('«{field}» starts «{date}»').format(
                field=custom_field.name,
                date=date_format(start, 'DATE_FORMAT'),
            ),
            handler1.description(user=user)
        )

        # ---
        end = date(year=2000, month=7, day=1)
        handler2 = DateCustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            custom_field=custom_field,
            end=end,
        )
        self.assertEqual(
            _('«{field}» ends «{date}»').format(
                field=custom_field.name,
                date=date_format(end, 'DATE_FORMAT'),
            ),
            handler2.description(user=user),
        )

    def test_description__deleted_customfield(self):
        user = self.get_root_user()

        handler = DateCustomFieldConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            related_name='customfielddatetime',
            custom_field=uuid4(),
            date_range='previous_year',
        )
        self.assertEqual('???', handler.description(user=user))


class RelationConditionHandlerTestCase(_ConditionHandlerTestCase):
    def test_init__rtype_id(self):
        user = self.get_root_user()
        rtype = RelationType.objects.builder(
            id='test-subject_love', predicate='is loving',
        ).symmetric(id='test-object_love', predicate='is loved by').get_or_create()[0]

        handler1 = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation, rtype=rtype.id, exclude=False,
        )

        self.assertEqual(FakeOrganisation, handler1.model)
        self.assertIsNone(handler1.subfilter_id)
        self.assertIs(handler1.subfilter, False)
        self.assertEqual(rtype.id, handler1._rtype_id)
        self.assertIs(handler1._exclude, False)
        self.assertIsNone(handler1._ct_key)
        self.assertIsNone(handler1._entity_uuid)

        self.assertIsNone(handler1.error)
        self.assertIs(handler1.applicable_on_entity_base, True)
        self.assertIs(handler1.entities_are_distinct(), True)

        self.assertQEqual(
            Q(pk__in=Relation.objects.none()),
            handler1.get_q(user=None),
        )

        # ---
        with self.assertNumQueries(1):
            rtype2 = handler1.relation_type

        self.assertEqual(rtype, rtype2)

        with self.assertNumQueries(0):
            handler1.relation_type  # NOQA

        # ---
        with self.assertNumQueries(0):
            e1 = handler1.entity
        self.assertIsNone(e1)

        # ---
        ctype_id = ContentType.objects.get_for_model(FakeContact).id
        handler2 = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            rtype=rtype.id, ctype=ctype_id, exclude=True,
        )

        self.assertIs(handler2._exclude, True)
        self.assertEqual(ctype_id, handler2._ct_key)

        # ---
        entity = FakeContact.objects.create(user=user, last_name='Ayanami', first_name='Rei')
        handler3 = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            rtype=rtype.id, entity=entity.uuid,
        )

        self.assertIs(handler3._exclude, False)
        self.assertEqual(entity.uuid, handler3._entity_uuid)

        # ---
        ContentType.objects.get_for_model(CremeEntity)  # pre-fill the cache

        with self.assertNumQueries(2):
            e3 = handler3.entity
        self.assertEqual(entity, e3)

        with self.assertNumQueries(0):
            handler3.entity  # NOQA

    def test_init__rtype_instance(self):
        rtype = RelationType.objects.builder(
            id='test-subject_love', predicate='is loving',
        ).symmetric(id='test-object_love', predicate='is loved by').get_or_create()[0]

        handler = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact, rtype=rtype,
        )

        self.assertEqual(FakeContact, handler.model)
        self.assertEqual(rtype.id, handler._rtype_id)
        self.assertIsNone(handler.content_type)

        # ---
        with self.assertNumQueries(0):
            rtype2 = handler.relation_type

        self.assertEqual(rtype, rtype2)

    def test_init__ctype(self):
        ctype = ContentType.objects.get_for_model(FakeContact)
        handler = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            rtype='creme_core-subject_type1', ctype=ctype,
        )

        self.assertEqual(FakeOrganisation, handler.model)
        self.assertEqual(ctype.natural_key(), handler._ct_key)
        self.assertEqual(ctype, handler.content_type)

    def test_init__entity(self):
        user = self.get_root_user()
        entity = FakeOrganisation.objects.create(user=user, name='Acme')
        handler = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            rtype='creme_core-subject_type1',
            entity=entity,
            ctype=entity.entity_type_id,  # <= should not be used
        )

        self.assertEqual(FakeOrganisation, handler.model)
        self.assertEqual(entity.uuid, handler._entity_uuid)
        self.assertIsNone(handler._ct_key)

        # --
        with self.assertNumQueries(0):
            e = handler.entity
        self.assertEqual(entity, e)

    def test_build__basic(self):
        model = FakeContact
        rtype_id = 'creme_core-subject_test1'
        handler = RelationConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=model, name=rtype_id, data={'has': True},
        )
        self.assertEqual(model, handler.model)
        self.assertEqual(EF_REGULAR, handler.efilter_type)
        self.assertIsNone(handler.subfilter_id)
        self.assertEqual(rtype_id,  handler._rtype_id)
        self.assertFalse(handler._exclude)
        self.assertIsNone(handler._ct_key)
        self.assertIsNone(handler.content_type)
        self.assertIsNone(handler._entity_uuid)

    def test_build__ctype(self):
        model = FakeOrganisation
        rtype_id = 'creme_core-subject_othertest'
        handler = RelationConditionHandler.build(
            efilter_type=EF_CREDENTIALS,
            model=model,
            name=rtype_id,
            data={
                'has': False,
                'ct': 'creme_core.fakeorganisation',
            },
        )
        self.assertEqual(model, handler.model)
        self.assertEqual(EF_CREDENTIALS, handler.efilter_type)
        self.assertEqual(rtype_id,  handler._rtype_id)
        self.assertTrue(handler._exclude)
        self.assertEqual(['creme_core', 'fakeorganisation'], handler._ct_key)
        self.assertIsNone(handler._entity_uuid)

    def test_build__entity(self):
        entity_uuid = uuid4()
        handler = RelationConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            name='creme_core-subject_test',
            data={
                'has': False,
                'entity': str(entity_uuid),
            },
        )
        self.assertIsNone(handler._ct_key)
        self.assertEqual(entity_uuid, handler._entity_uuid)

    def test_build__errors(self):
        rtype_id = 'creme_core-subject_test'

        with self.assertRaises(FilterConditionHandler.DataError):
            RelationConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name=rtype_id,
                data=[],  # <= not a dict.
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            RelationConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name=rtype_id,
                data={},  # Missing 'has': True
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            RelationConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name=rtype_id,
                data={'has': 25},  # Not a Boolean
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            RelationConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name=rtype_id,
                data={
                    'has':   False,
                    'ct': 123,  # <== not a string
                },
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            RelationConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name=rtype_id,
                data={
                    'has':   False,
                    'ct': 'creme_core',  # <==
                },
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            RelationConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name=rtype_id,
                data={
                    'has': False,
                    'entity': 'notauuid',  # <==
                },
            )

    def test_formfield(self):
        user = self.get_root_user()

        formfield1 = RelationConditionHandler.formfield(user=user)
        self.assertIsInstance(formfield1, ef_fields.RelationsConditionsField)
        self.assertEqual(user, formfield1.user)
        self.assertIs(formfield1.required, True)
        self.assertEqual(_('On relationships'), formfield1.label)
        self.assertTrue(formfield1.help_text)

        class MyField(ef_fields.RelationsConditionsField):
            pass

        formfield2 = RelationConditionHandler.formfield(form_class=MyField, required=False)
        self.assertIsInstance(formfield2, MyField)
        self.assertIs(formfield2.required, False)
        self.assertIsNone(formfield2.user)

    def test_build_condition(self):
        user = self.get_root_user()

        loves = RelationType.objects.builder(
            id='test-subject_love', predicate='is loving',
        ).symmetric(id='test-object_love', predicate='is loved by').get_or_create()[0]

        build_cond = partial(RelationConditionHandler.build_condition, model=FakeContact)
        condition1 = build_cond(rtype=loves, has=True)
        self.assertIsInstance(condition1, EntityFilterCondition)
        self.assertIsNone(condition1.pk)
        self.assertEqual(EF_REGULAR,                       condition1.filter_type)
        self.assertEqual(RelationConditionHandler.type_id, condition1.type)
        self.assertEqual(loves.id,                         condition1.name)
        self.assertDictEqual({'has': True}, condition1.value)

        handler1 = RelationConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=FakeContact, name=condition1.name, data=condition1.value,
        )
        self.assertIsInstance(handler1, RelationConditionHandler)
        self.assertEqual(FakeContact, handler1.model)
        self.assertIsNone(handler1.subfilter_id)
        self.assertIs(handler1.subfilter, False)
        self.assertEqual(loves.id, handler1._rtype_id)
        self.assertIs(handler1._exclude, False)
        self.assertIsNone(handler1._ct_key)
        self.assertIsNone(handler1.content_type)
        self.assertIsNone(handler1._entity_uuid)

        # ---
        loved = loves.symmetric_type
        condition2 = build_cond(rtype=loved, has=False, filter_type=EF_CREDENTIALS)
        self.assertEqual(loved.id, condition2.name)
        self.assertEqual(EF_CREDENTIALS, condition2.filter_type)
        self.assertDictEqual({'has': False}, condition2.value)

        handler2 = RelationConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=FakeContact, name=condition2.name, data=condition2.value,
        )
        self.assertIs(handler2._exclude, True)

        # ---
        ct = ContentType.objects.get_for_model(FakeContact)
        condition3 = build_cond(rtype=loves, ct=ct)
        self.assertEqual(loves.id, condition3.name)
        self.assertDictEqual({'has': True, 'ct': 'creme_core.fakecontact'}, condition3.value)

        handler3 = RelationConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=FakeContact, name=condition3.name, data=condition3.value,
        )
        self.assertListEqual(['creme_core', 'fakecontact'], handler3._ct_key)
        self.assertEqual(ct, handler3.content_type)

        # ---
        # NB: "ct" should not be used
        orga = FakeOrganisation.objects.create(user=user, name='Nerv')
        condition4 = build_cond(rtype=loves, ct=ct, entity=orga)
        self.assertEqual(loves.id, condition4.name)
        self.assertDictEqual(
            {'has': True, 'entity': str(orga.uuid)}, condition4.value,
        )

        handler4 = RelationConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=FakeContact, name=condition4.name, data=condition4.value,
        )
        self.assertIsNone(handler4._ct_key)
        self.assertIsNone(handler4.content_type)
        self.assertEqual(orga.uuid, handler4._entity_uuid)

    def test_get_q(self):
        "get_q() not empty."
        user = self.get_root_user()

        loves = RelationType.objects.builder(
            id='test-subject_love', predicate='is loving',
        ).symmetric(id='test-object_love', predicate='is loved by').get_or_create()[0]

        create_contact = partial(FakeContact.objects.create, user=user)
        shinji = create_contact(last_name='Ikari',     first_name='Shinji')
        rei    = create_contact(last_name='Ayanami',   first_name='Rei')
        asuka  = create_contact(last_name='Langley',   first_name='Asuka')
        misato = create_contact(last_name='Katsuragi', first_name='Misato')

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        create_rel = partial(Relation.objects.create, user=user)
        rel1 = create_rel(subject_entity=shinji, type=loves, object_entity=rei)
        # rel2 =
        create_rel(subject_entity=asuka,  type=loves, object_entity=shinji)
        # rel3 =
        create_rel(subject_entity=misato, type=loves, object_entity=nerv)

        handler1 = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact, rtype=loves.id, exclude=False,
        )
        # NB: assertQEqual causes problems with PostGre here (order in the pk__in is "random")
        # self.assertQEqual(
        #     Q(pk__in=Relation.objects
        #                      .filter(id__in=[rel1.id, rel2.id, rel3.id])
        #                      .values_list('subject_entity_id', flat=True)
        #      ),
        #     handler1.get_q(user=user)
        # )
        self.assertQPkIn(
            handler1.get_q(user=user),
            shinji, asuka, misato,
        )

        # Exclude ---
        handler2 = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact, rtype=loves.id, exclude=True,
        )
        self.assertQPkIn(
            handler2.get_q(user=user),
            shinji, asuka, misato,
            negated=True,
        )

        # CT ---
        handler3 = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            rtype=loves.id,
            ctype=ContentType.objects.get_for_model(FakeContact),
        )
        self.assertQPkIn(
            handler3.get_q(user=user),
            shinji, asuka,
        )

        # Entity ---
        handler4 = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            rtype=loves.id, entity=rei,
        )
        self.assertQEqual(
            Q(pk__in=Relation.objects
                             .filter(id=rel1.id)
                             .values_list('subject_entity_id', flat=True)),
            handler4.get_q(user=user),
        )

    def test_accept(self):
        user = self.get_root_user()
        loves = RelationType.objects.builder(
            id='test-subject_love', predicate='is loving',
        ).symmetric(id='test-object_love', predicate='is loved by').get_or_create()[0]

        create_contact = partial(FakeContact.objects.create, user=user)
        shinji = create_contact(last_name='Ikari',     first_name='Shinji')
        rei    = create_contact(last_name='Ayanami',   first_name='Rei')
        asuka  = create_contact(last_name='Langley',   first_name='Asuka')
        misato = create_contact(last_name='Katsuragi', first_name='Misato')
        gendo  = create_contact(last_name='Ikari',     first_name='Gendo')

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=shinji, type=loves, object_entity=rei)
        create_rel(subject_entity=asuka,  type=loves, object_entity=shinji)
        create_rel(subject_entity=misato, type=loves, object_entity=nerv)

        handler1 = RelationConditionHandler(
            efilter_type=EF_REGULAR, model=FakeContact, rtype=loves.id,
        )

        self.assertIs(handler1.accept(entity=shinji, user=user), True)
        self.assertIs(handler1.accept(entity=asuka,  user=user), True)
        self.assertIs(handler1.accept(entity=misato, user=user), True)
        self.assertIs(handler1.accept(entity=rei,    user=user), False)
        self.assertIs(handler1.accept(entity=gendo,  user=user), False)

        # Exclude ---
        handler2 = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact, rtype=loves.id, exclude=True,
        )
        self.assertIs(handler2.accept(entity=shinji, user=user), False)
        self.assertIs(handler2.accept(entity=misato, user=user), False)
        self.assertIs(handler2.accept(entity=asuka,  user=user), False)
        self.assertIs(handler2.accept(entity=rei,    user=user), True)
        self.assertIs(handler2.accept(entity=gendo,  user=user), True)

        # CT ---
        handler3 = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            rtype=loves.id,
            ctype=ContentType.objects.get_for_model(FakeContact),
        )
        self.assertIs(handler3.accept(entity=shinji, user=user), True)
        self.assertIs(handler3.accept(entity=misato, user=user), False)

        # Entity ---
        handler4 = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            rtype=loves.id,
            entity=rei.uuid,
        )
        self.assertIs(handler4.accept(entity=shinji, user=user), True)
        self.assertIs(handler4.accept(entity=asuka,  user=user), False)

    def test_description(self):
        user = self.get_root_user()

        rtype = RelationType.objects.builder(
            id='test-subject_love', predicate='is loving',
        ).symmetric(id='test-object_love', predicate='is loved by').get_or_create()[0]

        handler1 = RelationConditionHandler(
            efilter_type=EF_REGULAR, model=FakeOrganisation, rtype=rtype,
        )
        self.assertEqual(
            _('The entities have relationships «{predicate}»').format(predicate=rtype.predicate),
            handler1.description(user)
        )

        # ---
        ctype = ContentType.objects.get_for_model(FakeContact)
        handler2 = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation, rtype=rtype, ctype=ctype,
        )
        self.assertEqual(
            _('The entities have relationships «{predicate}» to «{model}»').format(
                predicate=rtype.predicate,
                model='Test Contacts',
            ),
            handler2.description(user),
        )

        # ---
        entity = FakeContact.objects.create(user=user, last_name='Ayanami', first_name='Rei')
        handler3 = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact, rtype=rtype, entity=entity,
        )
        self.assertEqual(
            _('The entities have relationships «{predicate}» to «{entity}»').format(
                predicate=rtype.predicate, entity=entity,
            ),
            handler3.description(user),
        )

    def test_description__exclude(self):
        user = self.get_root_user()

        rtype = RelationType.objects.builder(
            id='test-subject_like', predicate='Is liking',
        ).symmetric(id='test-object_like', predicate='is liked by').get_or_create()[0]

        handler1 = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact, rtype=rtype, exclude=True,
        )
        self.assertEqual(
            _(
                'The entities have no relationship «{predicate}»'
            ).format(predicate=rtype.predicate),
            handler1.description(user),
        )

        # ---
        ctype = ContentType.objects.get_for_model(FakeContact)
        handler2 = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            rtype=rtype,
            ctype=ctype,
            exclude=True,
        )
        self.assertEqual(
            _(
                'The entities have no relationship «{predicate}» to «{model}»'
            ).format(predicate=rtype.predicate, model='Test Contacts'),
            handler2.description(user)
        )

        # ---
        entity = FakeContact.objects.create(user=user, last_name='Ayanami', first_name='Rei')
        handler3 = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            rtype=rtype,
            entity=entity,
            exclude=True,
        )
        self.assertEqual(
            _(
                'The entities have no relationship «{predicate}» to «{entity}»'
            ).format(predicate=rtype.predicate, entity=entity),
            handler3.description(user),
        )

    def test_relation_description__credentials(self):
        user = self.login_as_standard()

        rtype = RelationType.objects.builder(
            id='test-subject_love', predicate='is loving',
        ).symmetric(id='test-object_love', predicate='is loved by').get_or_create()[0]
        entity = FakeContact.objects.create(
            user=self.get_root_user(),
            last_name='Ayanami', first_name='Rei',
        )

        handler = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact, rtype=rtype, entity=entity,
        )
        self.assertEqual(
            _('The entities have relationships «{predicate}» to «{entity}»').format(
                predicate=rtype.predicate,
                entity=_('Entity #{id} (not viewable)').format(id=entity.id),
            ),
            handler.description(user),
        )

    def test_description__errors(self):
        user = self.get_root_user()

        handler1 = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            rtype='doesnotexistanymore',
            exclude=True,
        )
        self.assertEqual('???', handler1.description(user))

        # ---
        rtype = RelationType.objects.builder(
            id='test-subject_like', predicate='is liking',
        ).symmetric(id='test-object_like', predicate='is liked by').get_or_create()[0]
        handler2 = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            rtype=rtype,
            entity=self.UNUSED_PK,
        )
        self.assertEqual(
            _('The entities have relationships «{predicate}» to «{entity}»').format(
                predicate=rtype.predicate,
                entity='???',
            ),
            handler2.description(user),
        )

        # ---
        handler3 = RelationConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            rtype=rtype,
            ctype=('invalid_app', 'invalid_model'),
            exclude=True,
        )
        self.assertEqual(
            _('The entities have no relationship «{predicate}» to «{model}»').format(
                predicate=rtype.predicate,
                model='???',
            ),
            handler3.description(user),
        )


class SubFilterConditionHandlerTestCase(_ConditionHandlerTestCase):
    def test_init__efilter_id(self):
        sub_efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01', model=FakeOrganisation, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation, field_name='name',
                    operator=operators.EQUALS, values=['Bebop'],
                ),
            ],
        )

        handler = SubFilterConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            subfilter=sub_efilter.id,
        )
        self.assertEqual(FakeOrganisation, handler.model)
        self.assertEqual(sub_efilter.id, handler.subfilter_id)
        self.assertEqual(sub_efilter.id, handler._subfilter_id)

        with self.assertNumQueries(1):
            subfilter = handler.subfilter

        self.assertEqual(sub_efilter, subfilter)

        with self.assertNumQueries(0):
            handler.subfilter  # NOQA

        self.assertIsNone(handler.error)
        self.assertIs(handler.applicable_on_entity_base, False)
        self.assertIs(handler.entities_are_distinct(), True)

        self.assertQEqual(Q(name__exact='Bebop'), handler.get_q(user=None))

        # --
        with self.assertRaises(TypeError):
            SubFilterConditionHandler(
                efilter_type=EF_REGULAR,
                # model=FakeOrganisation,  # No model passed
                subfilter=sub_efilter.id,
            )

    def test_init__efilter_instance(self):
        sub_efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01', model=FakeOrganisation, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation, field_name='name',
                    operator=operators.EQUALS, values=['Bebop'],
                ),
            ],
        )

        handler = SubFilterConditionHandler(
            efilter_type=EF_REGULAR, subfilter=sub_efilter,
        )
        self.assertEqual(FakeOrganisation, handler.model)
        self.assertEqual(sub_efilter.id, handler.subfilter_id)
        self.assertEqual(sub_efilter.id, handler._subfilter_id)

        with self.assertNumQueries(0):
            subfilter = handler.subfilter

        self.assertEqual(sub_efilter, subfilter)

    def test_property_error(self):
        handler = SubFilterConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation, subfilter='invalid',
        )
        self.assertEqual("'invalid' is not a valid filter ID", handler.error)

    def test_build(self):
        model = FakeContact
        subfilter_id = 'creme_core-subject_test1'
        handler = SubFilterConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=model,
            name=subfilter_id,
            data=None,
        )
        self.assertEqual(model, handler.model)
        self.assertEqual(EF_REGULAR, handler.efilter_type)
        self.assertEqual(subfilter_id, handler.subfilter_id)

    def test_build__other_values(self):
        model = FakeOrganisation
        subfilter_id = 'creme_core-subject_othertest'
        handler1 = SubFilterConditionHandler.build(
            efilter_type=EF_CREDENTIALS,
            model=model,
            name=subfilter_id,
            data=None,
        )
        self.assertEqual(model, handler1.model)
        self.assertEqual(EF_CREDENTIALS, handler1.efilter_type)
        self.assertEqual(subfilter_id, handler1.subfilter_id)

    def test_applicable_on_entity_base(self):
        sub_efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='description',
                    operator=operators.ICONTAINS, values=['Alchemist'],
                ),
            ],
        )

        handler = SubFilterConditionHandler(efilter_type=EF_REGULAR, subfilter=sub_efilter)
        self.assertIs(handler.applicable_on_entity_base, True)

    def test_distinct(self):
        l1, l2 = Language.objects.all()[:2]

        sub_cond = RegularFieldConditionHandler.build_condition(
            model=FakeContact, field_name='languages',
            operator=operators.EQUALS, values=[l1.id, l2.id],
        )
        self.assertFalse(sub_cond.handler.entities_are_distinct())

        sub_efilter = EntityFilter.objects.create(
            id='test-sub_filter01', name='Sub Filter on languages', entity_type=FakeContact,
        ).set_conditions([sub_cond])

        handler = SubFilterConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            subfilter=sub_efilter.id,
        )
        self.assertFalse(handler.entities_are_distinct())
        self.assertQEqual(Q(languages__in=[l1.id, l2.id]), handler.get_q(user=None))

    def test_formfield(self):
        user = self.get_root_user()

        formfield1 = SubFilterConditionHandler.formfield(user=user)
        self.assertIsInstance(formfield1, ef_fields.SubfiltersConditionsField)
        self.assertEqual(user, formfield1.user)
        self.assertIs(formfield1.required, True)
        self.assertEqual(_('Sub-filters'), formfield1.label)
        self.assertFalse(formfield1.help_text)

        class MyField(ef_fields.SubfiltersConditionsField):
            pass

        formfield2 = SubFilterConditionHandler.formfield(form_class=MyField, required=False)
        self.assertIsInstance(formfield2, MyField)
        self.assertIs(formfield2.required, False)
        self.assertIsNone(formfield2.user)

    def test_accept(self):
        user = self.get_root_user()
        sub_efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='last_name',
                    operator=operators.EQUALS, values=['Elric'],
                ),
            ],
        )

        handler = SubFilterConditionHandler(
            efilter_type=EF_REGULAR, subfilter=sub_efilter,
        )

        create_contact = partial(FakeContact.objects.create, user=user)
        ed  = create_contact(first_name='Edward',   last_name='Elric')
        al  = create_contact(first_name='Alphonse', last_name='Elric')
        roy = create_contact(first_name='Roy',      last_name='Mustang')

        self.assertIs(handler.accept(entity=ed,  user=user), True)
        self.assertIs(handler.accept(entity=al,  user=user), True)
        self.assertIs(handler.accept(entity=roy, user=user), False)

    def test_build_condition(self):
        sub_efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='last_name',
                    operator=operators.EQUALS, values=['Spiegel'],
                ),
            ],
        )

        condition1 = SubFilterConditionHandler.build_condition(sub_efilter)
        self.assertIsInstance(condition1, EntityFilterCondition)
        self.assertIsNone(condition1.pk)
        self.assertEqual(EF_REGULAR,                        condition1.filter_type)
        self.assertEqual(SubFilterConditionHandler.type_id, condition1.type)
        self.assertEqual(sub_efilter.id,                    condition1.name)
        self.assertDictEqual({}, condition1.value)

        handler1 = SubFilterConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=FakeContact, name=condition1.name, data=condition1.value,
        )
        self.assertIsInstance(handler1, SubFilterConditionHandler)
        self.assertEqual(FakeContact, handler1.model)
        self.assertEqual(sub_efilter.id, handler1.subfilter_id)
        self.assertEqual(sub_efilter.id, handler1._subfilter_id)
        self.assertEqual(sub_efilter, handler1.subfilter)

        # ---
        condition2 = SubFilterConditionHandler.build_condition(
            sub_efilter, filter_type=EF_CREDENTIALS,
        )
        self.assertEqual(EF_CREDENTIALS, condition2.filter_type)
        # self.assertIsNone(condition2.handler) TODO ?

    def test_description(self):
        user = self.get_root_user()
        sub_efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01', model=FakeOrganisation, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation, field_name='name',
                    operator=operators.EQUALS, values=['Bebop'],
                ),
            ],
        )

        handler = SubFilterConditionHandler(
            efilter_type=EF_REGULAR, model=FakeOrganisation,
            subfilter=sub_efilter.id,
        )
        self.assertEqual(
            _('Entities are accepted by the filter «{}»').format(sub_efilter.name),
            handler.description(user)
        )

    def test_description__error(self):
        user = self.get_root_user()
        handler = SubFilterConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            subfilter='doesnotexist',
        )
        self.assertEqual('???', handler.description(user))


class RelationSubFilterConditionHandlerTestCase(_ConditionHandlerTestCase):
    def test_init__efilter_id(self):
        sub_efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='last_name',
                    operator=operators.EQUALS, values=['Spiegel'],
                ),
            ],
        )
        rtype_id = 'creme_core-subject_loves'
        handler = RelationSubFilterConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            subfilter=sub_efilter.id, rtype=rtype_id, exclude=False,
        )
        self.assertEqual(FakeOrganisation, handler.model)
        self.assertEqual(rtype_id, handler._rtype_id)
        self.assertIs(handler._exclude, False)
        self.assertEqual(sub_efilter.id, handler.subfilter_id)
        self.assertEqual(sub_efilter.id, handler._subfilter_id)

        with self.assertNumQueries(1):
            subfilter = handler.subfilter

        self.assertEqual(sub_efilter, subfilter)

        with self.assertNumQueries(0):
            handler.subfilter  # NOQA

        self.assertIsNone(handler.error)
        self.assertIs(handler.applicable_on_entity_base, True)

        self.assertQEqual(
            Q(pk__in=Relation.objects.none()),
            handler.get_q(user=None)
        )

    def test_init__efilter_instance(self):
        sub_efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='last_name',
                    operator=operators.EQUALS, values=['Spiegel'],
                ),
            ],
        )
        handler = RelationSubFilterConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            subfilter=sub_efilter,
            rtype='creme_core-subject_loves',
            exclude=True,
        )
        self.assertEqual(FakeContact, handler.model)
        self.assertIs(handler._exclude, True)
        self.assertEqual(sub_efilter.id, handler.subfilter_id)
        self.assertEqual(sub_efilter.id, handler._subfilter_id)

        with self.assertNumQueries(0):
            subfilter = handler.subfilter

        self.assertEqual(sub_efilter, subfilter)

    def test_init__rtype_instance(self):
        rtype = RelationType.objects.builder(
            id='test-subject_love', predicate='is loving',
        ).symmetric(id='test-object_love', predicate='is loved by').get_or_create()[0]

        handler = RelationSubFilterConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact,
            subfilter='creme_core-test_filter',
            rtype=rtype,
        )
        self.assertIs(handler._exclude, False)
        self.assertEqual(rtype.id, handler._rtype_id)

    def test_property_error(self):
        handler = RelationSubFilterConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            subfilter='invalid',
            rtype='creme_core-subject_test',
        )
        self.assertEqual("'invalid' is not a valid filter ID", handler.error)

    def test_build(self):
        model = FakeContact
        rtype_id = 'creme_core-subject_test'
        subfilter_id = 'creme_core-filter_test'
        handler = RelationSubFilterConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=model,
            name=rtype_id,
            data={
                'has': True,
                'filter_id': subfilter_id,
            },
        )
        self.assertEqual(model, handler.model)
        self.assertEqual(EF_REGULAR, handler.efilter_type)
        self.assertEqual(subfilter_id, handler.subfilter_id)
        self.assertEqual(rtype_id, handler._rtype_id)
        self.assertFalse(handler._exclude)

    def test_build__other_values(self):
        model = FakeOrganisation
        rtype_id = 'creme_core-subject_other'
        subfilter_id = 'creme_core-filter_other'
        handler = RelationSubFilterConditionHandler.build(
            efilter_type=EF_CREDENTIALS,
            model=model,
            name=rtype_id,
            data={
                'has': True,
                'filter_id': subfilter_id,
            },
        )
        self.assertEqual(model, handler.model)
        self.assertEqual(EF_CREDENTIALS, handler.efilter_type)
        self.assertEqual(subfilter_id, handler.subfilter_id)
        self.assertEqual(rtype_id, handler._rtype_id)
        self.assertFalse(handler._exclude)

    def test_build__errors(self):
        rtype_id = 'creme_core-subject_test'
        subfilter_id = 'creme_core-filter_test'

        with self.assertRaises(FilterConditionHandler.DataError):
            RelationSubFilterConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name=rtype_id,
                data=[],  # <= not a dict.
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            RelationSubFilterConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name=rtype_id,
                data={
                    # 'has': True  # Missing
                    'filter_id': subfilter_id,
                },
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            RelationSubFilterConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name=rtype_id,
                data={
                    'has': 25,   # Not a Boolean
                    'filter_id': subfilter_id,
                },
            )

    def test_formfield(self):
        user = self.get_root_user()

        formfield1 = RelationSubFilterConditionHandler.formfield(user=user)
        self.assertIsInstance(formfield1, ef_fields.RelationSubfiltersConditionsField)
        self.assertEqual(user, formfield1.user)
        self.assertIs(formfield1.required, True)
        self.assertEqual(
            _('On relationships with results of other filters'),
            formfield1.label,
        )
        self.assertFalse(formfield1.help_text)

        class MyField(ef_fields.RelationSubfiltersConditionsField):
            pass

        formfield2 = RelationSubFilterConditionHandler.formfield(
            form_class=MyField, required=False,
        )
        self.assertIsInstance(formfield2, MyField)
        self.assertIs(formfield2.required, False)
        self.assertIsNone(formfield2.user)

    def test_build_condition(self):
        loves = RelationType.objects.builder(
            id='test-subject_love', predicate='Is loving',
        ).symmetric(id='test-object_love', predicate='is loved by').get_or_create()[0]

        def build_filter(pk):
            return EntityFilter.objects.smart_update_or_create(
                pk=pk, name='Filter Rei', model=FakeContact, is_custom=True,
                conditions=[
                    RegularFieldConditionHandler.build_condition(
                        model=FakeContact, field_name='last_name',
                        operator=operators.STARTSWITH, values=['Ayanami'],
                    ),
                ],
            )

        sub_efilter1 = build_filter('test-filter01')

        condition1 = RelationSubFilterConditionHandler.build_condition(
            model=FakeContact, rtype=loves, has=True, subfilter=sub_efilter1,
        )
        self.assertIsInstance(condition1, EntityFilterCondition)
        self.assertIsNone(condition1.pk)
        self.assertEqual(EF_REGULAR,                                condition1.filter_type)
        self.assertEqual(RelationSubFilterConditionHandler.type_id, condition1.type)
        self.assertEqual(loves.id,                                  condition1.name)
        self.assertDictEqual(
            {'filter_id': sub_efilter1.id, 'has': True},
            condition1.value,
        )

        handler1 = RelationSubFilterConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=FakeContact, name=condition1.name, data=condition1.value,
        )
        self.assertIsInstance(handler1, RelationSubFilterConditionHandler)
        self.assertEqual(FakeContact, handler1.model)
        self.assertEqual(sub_efilter1.id, handler1.subfilter_id)
        self.assertEqual(sub_efilter1,    handler1.subfilter)
        self.assertEqual(sub_efilter1.id, handler1._subfilter_id)
        self.assertEqual(loves.id,        handler1._rtype_id)
        self.assertIs(handler1._exclude, False)

        # ---
        loved = loves.symmetric_type
        sub_efilter2 = build_filter('test-filter01')
        condition2 = RelationSubFilterConditionHandler.build_condition(
            model=FakeContact, rtype=loved, has=False, subfilter=sub_efilter2,
        )
        self.assertEqual(loved.id, condition2.name)
        self.assertDictEqual(
            {'filter_id': sub_efilter2.id, 'has': False},
            condition2.value,
        )

        handler2 = RelationSubFilterConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=FakeContact, name=condition2.name, data=condition2.value,
        )
        self.assertIsInstance(handler2, RelationSubFilterConditionHandler)
        self.assertEqual(FakeContact,  handler2.model)
        self.assertEqual(sub_efilter2, handler2.subfilter)
        self.assertEqual(loved.id,     handler2._rtype_id)
        self.assertIs(handler2._exclude, True)

        # ---
        condition3 = RelationSubFilterConditionHandler.build_condition(
            model=FakeContact, rtype=loved, subfilter=sub_efilter2,
            filter_type=EF_CREDENTIALS,
        )
        self.assertEqual(EF_CREDENTIALS, condition3.filter_type)
        # self.assertIsNone(condition3.handler) TODO ??

    def test_get_q(self):
        "get_q() not empty."
        user = self.get_root_user()

        loves = RelationType.objects.builder(
            id='test-subject_love', predicate='is loving',
        ).symmetric(id='test-object_love', predicate='is loved by').get_or_create()[0]

        create_contact = partial(FakeContact.objects.create, user=user)
        shinji = create_contact(last_name='Ikari',     first_name='Shinji')
        yui    = create_contact(last_name='Ikari',     first_name='Yui')
        rei    = create_contact(last_name='Ayanami',   first_name='Rei')
        asuka  = create_contact(last_name='Langley',   first_name='Asuka')
        misato = create_contact(last_name='Katsuragi', first_name='Misato')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=shinji, type=loves, object_entity=yui)
        create_rel(subject_entity=asuka,  type=loves, object_entity=shinji)
        create_rel(subject_entity=rei,    type=loves, object_entity=misato)

        sub_filter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter Ikari', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='last_name',
                    operator=operators.STARTSWITH, values=['Ikari'],
                ),
            ],
        )

        handler1 = RelationSubFilterConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            subfilter=sub_filter.id, rtype=loves.id,
        )
        self.assertQPkIn(handler1.get_q(user=user), shinji, asuka)

        # Exclude ---
        handler2 = RelationSubFilterConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            subfilter=sub_filter.id, rtype=loves.id, exclude=True,
        )
        self.assertQPkIn(
            handler2.get_q(user=user),
            shinji, asuka,
            negated=True,
        )

    def test_description(self):
        user = self.get_root_user()

        rtype = RelationType.objects.builder(
            id='test-subject_love', predicate='is loving',
        ).symmetric(id='test-object_love', predicate='is loved by').get_or_create()[0]

        sub_filter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter Ikari', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='last_name',
                    operator=operators.STARTSWITH, values=['Ikari'],
                ),
            ],
        )

        handler1 = RelationSubFilterConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            rtype=rtype, subfilter=sub_filter,
        )
        self.assertEqual(
            _('The entities have relationships «{predicate}» to «{filter}»').format(
                predicate=rtype.predicate,
                filter=sub_filter,
            ),
            handler1.description(user),
        )

        # --- exclude
        handler2 = RelationSubFilterConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            rtype=rtype, subfilter=sub_filter, exclude=True,
        )
        self.assertEqual(
            _('The entities have no relationship «{predicate}» to «{filter}»').format(
                predicate=rtype.predicate,
                filter=sub_filter,
            ),
            handler2.description(user),
        )

    def test_description__errors(self):
        user = self.get_root_user()

        sub_filter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter Ikari', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='last_name',
                    operator=operators.STARTSWITH, values=['Ikari'],
                ),
            ],
        )

        handler1 = RelationSubFilterConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            rtype='deosnotexist', subfilter=sub_filter,
        )
        self.assertEqual('???', handler1.description(user))

        # ---
        rtype = RelationType.objects.builder(
            id='test-subject_love', predicate='is loving',
        ).symmetric(id='test-object_love', predicate='is loved by').get_or_create()[0]

        handler2 = RelationSubFilterConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            rtype=rtype, subfilter='doesnotexist',
        )
        self.assertEqual(
            _('The entities have relationships «{predicate}» to «{filter}»').format(
                predicate=rtype.predicate,
                filter='???',
            ),
            handler2.description(user),
        )


class PropertyConditionHandlerTestCase(_ConditionHandlerTestCase):
    def test_init__ptype_uuid(self):
        ptype = CremePropertyType.objects.create(text='Kawaii')

        handler = PropertyConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            ptype=ptype.uuid, exclude=False,
        )
        self.assertEqual(FakeOrganisation, handler.model)
        self.assertIsNone(handler.subfilter_id)
        self.assertIs(handler.subfilter, False)
        self.assertEqual(ptype.uuid, handler._ptype_uuid)
        self.assertIs(handler._exclude, False)

        self.assertIsNone(handler.error)
        self.assertIs(handler.applicable_on_entity_base, True)

        self.assertQEqual(
            Q(pk__in=CremeProperty.objects.none()),
            handler.get_q(user=None),
        )

        # ---
        with self.assertNumQueries(1):
            ptype2 = handler.property_type

        self.assertEqual(ptype, ptype2)

        with self.assertNumQueries(0):
            handler.property_type  # NOQA

    def test_init__ptype_instance(self):
        ptype = CremePropertyType.objects.create(text='Kawaii')

        handler = PropertyConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact, ptype=ptype, exclude=True,
        )
        self.assertEqual(FakeContact, handler.model)
        self.assertEqual(ptype.uuid, handler._ptype_uuid)
        self.assertIs(handler._exclude, True)

        # ---
        with self.assertNumQueries(0):
            ptype2 = handler.property_type

        self.assertEqual(ptype, ptype2)

    def test_init__ptype_uuid_str(self):
        ptype = CremePropertyType.objects.create(text='Kawaii')
        handler = PropertyConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeContact, ptype=str(ptype.uuid), exclude=True,
        )
        self.assertEqual(ptype.uuid, handler._ptype_uuid)

    def test_build(self):
        model = FakeOrganisation
        ptype_uuid = '5fc20397-ab37-43a8-8abc-42a7218e89d0'
        handler = PropertyConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=model, name=ptype_uuid, data={'has': True},
        )
        self.assertEqual(model, handler.model)
        self.assertEqual(EF_REGULAR, handler.efilter_type)
        self.assertIsNone(handler.subfilter_id)
        self.assertEqual(UUID(ptype_uuid), handler._ptype_uuid)
        self.assertFalse(handler._exclude)

    def test_build__other_values(self):
        model = FakeOrganisation
        ptype_uuid = 'd8acaa7b-7c9f-465c-8200-02c5540e5959'
        handler = PropertyConditionHandler.build(
            efilter_type=EF_CREDENTIALS,
            model=model,
            name=ptype_uuid,
            data={'has': False},
        )
        self.assertEqual(model, handler.model)
        self.assertEqual(EF_CREDENTIALS, handler.efilter_type)
        self.assertEqual(UUID(ptype_uuid), handler._ptype_uuid)
        self.assertTrue(handler._exclude)

    def test_build__errors(self):
        with self.assertRaises(FilterConditionHandler.DataError):
            PropertyConditionHandler.build(
                efilter_type=EF_REGULAR,
                model=FakeOrganisation,
                name='creme_core-test',
                data=[],  # <= not a Boolean.
            )

    def test_formfield(self):
        user = self.get_root_user()

        formfield1 = PropertyConditionHandler.formfield(user=user)
        self.assertIsInstance(formfield1, ef_fields.PropertiesConditionsField)
        self.assertEqual(user, formfield1.user)
        self.assertIs(formfield1.required, True)
        self.assertEqual(_('On properties'), formfield1.label)
        self.assertFalse(formfield1.help_text)

        class MyField(ef_fields.PropertiesConditionsField):
            pass

        formfield2 = PropertyConditionHandler.formfield(form_class=MyField, required=False)
        self.assertIsInstance(formfield2, MyField)
        self.assertIs(formfield2.required, False)
        self.assertIsNone(formfield2.user)

    def test_build_condition(self):
        ptype1 = CremePropertyType.objects.create(text='Kawaii')

        condition1 = PropertyConditionHandler.build_condition(
            model=FakeContact, ptype=ptype1, has=True,
        )
        self.assertIsInstance(condition1, EntityFilterCondition)
        self.assertIsNone(condition1.pk)
        self.assertEqual(EF_REGULAR,                       condition1.filter_type)
        self.assertEqual(PropertyConditionHandler.type_id, condition1.type)
        self.assertEqual(str(ptype1.uuid), condition1.name)
        self.assertDictEqual({'has': True}, condition1.value)

        handler1 = PropertyConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=FakeContact, name=condition1.name, data=condition1.value,
        )
        self.assertIsInstance(handler1, PropertyConditionHandler)
        self.assertEqual(FakeContact, handler1.model)
        self.assertIsNone(handler1.subfilter_id)
        self.assertIs(handler1.subfilter, False)
        self.assertEqual(ptype1.uuid, handler1._ptype_uuid)
        self.assertIs(handler1._exclude, False)

        # ---
        ptype2 = CremePropertyType.objects.create(text='Cute')
        condition2 = PropertyConditionHandler.build_condition(
            model=FakeContact, ptype=ptype2, has=False,
            filter_type=EF_CREDENTIALS,
        )
        self.assertEqual(EF_CREDENTIALS, condition2.filter_type)
        self.assertEqual(str(ptype2.uuid), condition2.name)
        self.assertDictEqual({'has': False}, condition2.value)

        handler2 = PropertyConditionHandler.build(
            efilter_type=EF_REGULAR,
            model=FakeContact, name=condition2.name, data=condition2.value,
        )
        self.assertEqual(ptype2.uuid, handler2._ptype_uuid)
        self.assertIs(handler2._exclude, True)

    def test_get_q(self):
        "get_q() not empty."
        user = self.get_root_user()

        create_ptype = CremePropertyType.objects.create
        cute  = create_ptype(text='Cute')
        pilot = create_ptype(text='Pilot')

        create_contact = partial(FakeContact.objects.create, user=user)
        contacts = {
            'shinji': create_contact(last_name='Ikari',     first_name='Shinji'),
            'rei':    create_contact(last_name='Ayanami',   first_name='Rei'),
            'asuka':  create_contact(last_name='Langley',   first_name='Asuka'),
            'misato': create_contact(last_name='Katsuragi', first_name='Misato'),
        }

        create_prop = CremeProperty.objects.create
        properties = [
            create_prop(creme_entity=contacts['rei'],    type=cute),
            create_prop(creme_entity=contacts['rei'],    type=pilot),
            create_prop(creme_entity=contacts['misato'], type=cute),
            create_prop(creme_entity=contacts['shinji'], type=pilot),
        ]

        handler1 = PropertyConditionHandler(
            efilter_type=EF_REGULAR, model=FakeContact, ptype=cute,
        )
        self.assertQEqual(
            Q(pk__in=CremeProperty.objects
                                  .filter(id__in=[properties[0].id, properties[2].id])
                                  .values_list('creme_entity_id', flat=True)),
            handler1.get_q(user=user),
        )

        # Exclude ---
        handler2 = PropertyConditionHandler(
            efilter_type=EF_REGULAR, model=FakeContact, ptype=cute, exclude=True,
        )
        self.assertQEqual(
            ~Q(pk__in=CremeProperty.objects
                                   .filter(id__in=[properties[0].id, properties[2].id])
                                   .values_list('creme_entity_id', flat=True)),
            handler2.get_q(user=user),
        )

    def test_accept(self):
        user = self.get_root_user()
        create_ptype = CremePropertyType.objects.create
        cute  = create_ptype(text='Cute')
        pilot = create_ptype(text='Pilot')

        create_contact = partial(FakeContact.objects.create, user=user)
        shinji = create_contact(last_name='Ikari',     first_name='Shinji')
        rei    = create_contact(last_name='Ayanami',   first_name='Rei')
        misato = create_contact(last_name='Katsuragi', first_name='Misato')

        create_prop = CremeProperty.objects.create
        create_prop(creme_entity=rei,    type=cute)
        create_prop(creme_entity=shinji, type=pilot)

        handler1 = PropertyConditionHandler(
            efilter_type=EF_REGULAR, model=FakeContact, ptype=cute,
        )
        self.assertIs(handler1.accept(entity=rei,    user=user), True)
        self.assertIs(handler1.accept(entity=shinji, user=user), False)
        self.assertIs(handler1.accept(entity=misato, user=user), False)

        # Exclude ---
        handler2 = PropertyConditionHandler(
            efilter_type=EF_REGULAR, model=FakeContact, ptype=cute, exclude=True,
        )
        self.assertIs(handler2.accept(entity=rei,    user=user), False)
        self.assertIs(handler2.accept(entity=shinji, user=user), True)
        self.assertIs(handler2.accept(entity=misato, user=user), True)

    def test_description(self):
        user = self.get_root_user()
        cute = CremePropertyType.objects.create(text='Cute')
        handler = PropertyConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation, ptype=cute, exclude=False,
        )
        self.assertEqual(
            _('The entities have the property «{}»').format(cute.text),
            handler.description(user),
        )

    def test_description__exclude(self):
        user = self.get_root_user()
        cute = CremePropertyType.objects.create(text='Kawaii')
        handler = PropertyConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation, ptype=cute, exclude=True,
        )
        self.assertEqual(
            _('The entities have no property «{}»').format(cute.text),
            handler.description(user),
        )

    def test_description__deleted_ptype(self):
        user = self.get_root_user()
        handler = PropertyConditionHandler(
            efilter_type=EF_REGULAR,
            model=FakeOrganisation,
            ptype=UUID('e61782ee-cc12-4239-9274-bd464c21f473'),
        )
        self.assertEqual('???', handler.description(user))
