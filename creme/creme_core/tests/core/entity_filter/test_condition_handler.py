# -*- coding: utf-8 -*-

from datetime import date
from decimal import Decimal
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.db.models.query_utils import Q
from django.utils.formats import date_format
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    EF_USER,
    _EntityFilterRegistry,
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
from creme.creme_core.forms.entity_filter import fields as ef_fields
from creme.creme_core.forms.entity_filter import widgets as ef_widgets
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    CremeUser,
    CustomField,
    CustomFieldEnum,
    CustomFieldEnumValue,
    CustomFieldMultiEnum,
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
    Relation,
    RelationType,
    SetCredentials,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.utils.date_range import date_range_registry
from creme.creme_core.utils.meta import FieldInfo


# TODO: query_for_related_conditions()
# TODO: query_for_parent_conditions()
class FilterConditionHandlerTestCase(CremeTestCase):
    def assertQPkIn(self, q, *instances, negated=False):
        self.assertIs(q.negated, negated)

        children = q.children
        self.assertEqual(1, len(children), children)

        k, v = children[0]
        self.assertEqual('pk__in', k)
        self.assertSetEqual({i.pk for i in instances}, {*v})

    def test_regularfield_init(self):
        user = self.create_user()

        fname = 'name'
        operator_id = operators.ICONTAINS
        value = 'Corp'
        handler = RegularFieldConditionHandler(
            model=FakeOrganisation,
            field_name=fname,
            operator_id=operator_id,
            values=[value],
        )
        self.assertEqual(FakeOrganisation, handler.model)
        self.assertIsNone(handler.subfilter_id)
        self.assertIs(handler.subfilter, False)
        self.assertEqual(fname,       handler._field_name)
        self.assertEqual(operator_id, handler._operator_id)
        self.assertEqual([value],     handler._values)

        self.assertIsNone(handler.error)
        self.assertIs(handler.applicable_on_entity_base, False)

        self.assertQEqual(
            Q(name__icontains=value),
            handler.get_q(user=user),
        )
        # TODO: test other operators

        finfo = handler.field_info
        self.assertIsInstance(finfo, FieldInfo)
        self.assertEqual(1, len(finfo))
        self.assertEqual(fname, finfo[0].name)

    def test_regularfield_error(self):
        "<error> property."
        handler1 = RegularFieldConditionHandler(
            model=FakeOrganisation,
            field_name='invalid',
            operator_id=operators.ICONTAINS,
            values=['Corp'],
        )
        self.assertEqual(
            "FakeOrganisation has no field named 'invalid'",
            handler1.error,
        )

        # ---
        handler2 = RegularFieldConditionHandler(
            model=FakeOrganisation,
            field_name='name',
            operator_id=1234,  # <=
            values=['Corp'],
        )
        self.assertEqual(
            "Operator ID '1234' is invalid",
            handler2.error,
        )

    def test_regularfield_applicable_on_entity_base(self):
        "Field belongs to CremeEntity."
        handler = RegularFieldConditionHandler(
            model=FakeOrganisation,
            field_name='description',
            operator_id=operators.ICONTAINS,
            values=['#important'],
        )
        self.assertIs(handler.applicable_on_entity_base, True)

    def test_regularfield_build01(self):
        fname = 'name'
        operator_id = operators.ICONTAINS
        value = 'Corp'
        handler = RegularFieldConditionHandler.build(
            model=FakeOrganisation,
            name=fname,
            data={'operator': operator_id, 'values': [value]},
        )
        self.assertEqual(FakeOrganisation, handler.model)
        self.assertIsNone(handler.subfilter_id)
        self.assertEqual(fname,       handler._field_name)
        self.assertEqual(operator_id, handler._operator_id)
        self.assertEqual([value],     handler._values)

    def test_regularfield_build02(self):
        "Invalid data."
        operator_id = operators.ICONTAINS
        with self.assertRaises(FilterConditionHandler.DataError):
            RegularFieldConditionHandler.build(
                model=FakeOrganisation, name='name',
                data=[],  # <= not a dict.
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            RegularFieldConditionHandler.build(
                model=FakeOrganisation,
                name='name',
                data={'operator': operator_id},
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            RegularFieldConditionHandler.build(
                model=FakeOrganisation,
                name='name',
                data={'values': ['Corp']},
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            RegularFieldConditionHandler.build(
                model=FakeOrganisation,
                name='name',
                data={
                    'values':   ['Corp'],
                    'operator': 'notanint',  # <==
                },
            )

    def test_regularfield_formfield(self):
        user = self.create_user()
        efilter_registry = _EntityFilterRegistry(id=None, verbose_name='Test')

        formfield1 = RegularFieldConditionHandler.formfield(
            user=user,
            efilter_registry=efilter_registry,
        )
        self.assertIsInstance(formfield1, ef_fields.RegularFieldsConditionsField)
        self.assertEqual(user, formfield1.user)
        self.assertIs(efilter_registry, formfield1.efilter_registry)
        self.assertIs(formfield1.required, True)
        self.assertEqual(_('On regular fields'), formfield1.label)
        self.assertTrue(formfield1.help_text)

        widget1 = formfield1.widget
        self.assertIsInstance(widget1, ef_widgets.RegularFieldsConditionsWidget)
        self.assertIs(efilter_registry, widget1.efilter_registry)

        class MyField(ef_fields.RegularFieldsConditionsField):
            pass

        formfield2 = RegularFieldConditionHandler.formfield(form_class=MyField, required=False)
        self.assertIsInstance(formfield2, MyField)
        self.assertIs(formfield2.required, False)
        self.assertIsNone(formfield2.user)

    def test_regularfield_accept_string(self):
        user = self.create_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        o1 = create_orga(name='Evil Corp', description='Very evil')
        o2 = create_orga(name='Genius incorporated')
        o3 = create_orga(name='Acme')

        handler1 = RegularFieldConditionHandler(
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
            model=FakeOrganisation,
            field_name='description',
            operator_id=operators.ISEMPTY,
            values=[True],
        )
        self.assertIs(handler2.accept(entity=o1, user=user), False)
        self.assertIs(handler2.accept(entity=o2, user=user), True)

        # Operator need a Boolean (not a string) (<False> version)
        handler3 = RegularFieldConditionHandler(
            model=FakeOrganisation,
            field_name='description',
            operator_id=operators.ISEMPTY,
            values=[False],
        )
        self.assertIs(handler3.accept(entity=o1, user=user), True)
        self.assertIs(handler3.accept(entity=o2, user=user), False)

    def test_regularfield_accept_int(self):
        user = self.create_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        o1 = create_orga(name='Corp #1', capital=1000)
        o2 = create_orga(name='Corp #2', capital=500)
        o3 = create_orga(name='Corp #3', capital=None)

        handler1 = RegularFieldConditionHandler(
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
            model=FakeOrganisation,
            field_name='capital',
            operator_id=operators.EQUALS,
            values=['1000'],
        )
        self.assertIs(handler2.accept(entity=o1, user=user), True)
        self.assertIs(handler2.accept(entity=o2, user=user), False)
        self.assertIs(handler2.accept(entity=o3, user=user), False)

    def test_regularfield_accept_boolean(self):
        user = self.create_user()

        create_contact = partial(FakeContact.objects.create, user=user, last_name='Doe')
        c1 = create_contact(loves_comics=True)
        c2 = create_contact(loves_comics=False)
        c3 = create_contact(loves_comics=None)

        handler1 = RegularFieldConditionHandler(
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
            model=FakeContact,
            field_name='loves_comics',
            operator_id=operators.EQUALS,
            values=['True'],
        )
        self.assertIs(handler2.accept(entity=c1, user=user), True)
        self.assertIs(handler2.accept(entity=c2, user=user), False)
        self.assertIs(handler2.accept(entity=c3, user=user), False)

    def test_regularfield_accept_decimal(self):
        user = self.create_user()
        handler = RegularFieldConditionHandler(
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

    def test_regularfield_accept_fk01(self):
        "ForeignKey."
        user = self.create_user()
        sector1, sector2 = FakeSector.objects.all()[:2]

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        o1 = create_orga(name='Evil Corp',   sector=sector1)
        o2 = create_orga(name='Genius inc.', sector=sector2)
        o3 = create_orga(name='Acme',        sector=None)

        handler1 = RegularFieldConditionHandler(
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
            model=FakeOrganisation,
            field_name='sector',
            operator_id=operators.EQUALS,
            values=[str(sector1.id)],
        )
        self.assertIs(handler2.accept(entity=o1, user=user), True)
        self.assertIs(handler2.accept(entity=o2, user=user), False)
        self.assertIs(handler2.accept(entity=o3, user=user), False)

    def test_regularfield_accept_fk02(self):
        "ForeignKey sub-field."
        user = self.create_user()
        sector1, sector2 = FakeSector.objects.all()[:2]

        handler = RegularFieldConditionHandler(
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

    def test_regularfield_accept_fk03(self):
        "Nested ForeignKey (sub-field)."
        user = self.create_user()

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
            model=FakeDocument,
            field_name='linked_folder__category',
            operator_id=operators.EQUALS,
            values=[cat1.id],
        )
        self.assertIs(handler.accept(entity=doc1, user=user), True)
        self.assertIs(handler.accept(entity=doc2, user=user), False)
        self.assertIs(handler.accept(entity=doc3, user=user), False)

    def test_regularfield_accept_fk04(self):
        "Nullable nested ForeignKey (sub-field)."
        user = self.create_user()

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
            model=FakeReport,
            field_name='efilter__entity_type',
            operator_id=operators.EQUALS,
            values=[efilter1.entity_type_id],
        )
        self.assertIs(handler.accept(entity=r1, user=user), True)
        self.assertIs(handler.accept(entity=r2, user=user), False)
        self.assertIs(handler.accept(entity=r3, user=user), False)

    def test_regularfield_accept_fk05(self):
        "Primary key is a CharField => BEWARE to ISEMPTY which need boolean value."
        user = self.create_user()

        create_efilter = partial(EntityFilter.objects.create, entity_type=FakeContact)
        efilter1 = create_efilter(pk='creme_core-test_condition01', name='Filter#1')
        efilter2 = create_efilter(pk='creme_core-test_condition02', name='Filter#2')

        create_report = partial(FakeReport.objects.create, user=user, ctype=FakeContact)
        r1 = create_report(name='Report1', efilter=efilter1)
        r2 = create_report(name='Report2', efilter=efilter2)
        r3 = create_report(name='Report3')

        handler1 = RegularFieldConditionHandler(
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
            model=FakeReport,
            field_name='efilter',
            operator_id=operators.ISEMPTY,
            values=[False],
        )
        self.assertIs(handler3.accept(entity=r1, user=user), True)
        self.assertIs(handler3.accept(entity=r2, user=user), True)
        self.assertIs(handler3.accept(entity=r3, user=user), False)

    def test_regularfield_accept_operand(self):
        "Use operand resolving."
        user = self.login()
        handler = RegularFieldConditionHandler(
            model=FakeOrganisation,
            field_name='user',
            operator_id=operators.EQUALS,
            values=[operands.CurrentUserOperand.type_id],
        )

        create_orga = FakeOrganisation.objects.create
        o1 = create_orga(name='Evil Corp', user=user)
        self.assertIs(handler.accept(entity=o1, user=user), True)

        o2 = create_orga(name='Genius incorporated', user=self.other_user)
        self.assertIs(handler.accept(entity=o2, user=user), False)

    def test_regularfield_accept_m2m_01(self):
        "M2M."
        user = self.create_user()

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
            model=FakeDocument,
            field_name='categories',
            operator_id=operators.ISEMPTY,
            values=[False],
        )
        self.assertIs(handler4.accept(entity=doc1, user=user), True)
        self.assertIs(handler4.accept(entity=doc2, user=user), True)
        self.assertIs(handler4.accept(entity=doc3, user=user), False)

    def test_regularfield_accept_m2m_02(self):
        "M2M + subfield."
        user = self.create_user()

        create_cat = FakeDocumentCategory.objects.create
        cat1 = create_cat(name='Picture')
        cat2 = create_cat(name='Music')

        handler = RegularFieldConditionHandler(
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
        doc1 = create_doc(title='Picture#1')
        doc1.categories.set([cat1])
        self.assertIs(handler.accept(entity=doc1, user=user), True)

        doc2 = create_doc(title='Music#1')
        doc2.categories.set([cat2])
        self.assertIs(handler.accept(entity=doc2, user=user), False)

        doc3 = create_doc(title='Video#1')
        self.assertIs(handler.accept(entity=doc3, user=user), False)

    def test_regularfield_accept_m2m_03(self):
        "Subfield is a M2M."
        user = self.create_user()
        cat1, cat2 = FakeImageCategory.objects.all()[:2]

        handler = RegularFieldConditionHandler(
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

    def test_regularfield_condition01(self):
        "Build condition."
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
        self.assertEqual(EF_USER,                              condition.filter_type)
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(fname, condition.name)
        self.assertDictEqual(
            {'operator': operator_id, 'values': [value]}, condition.value
        )

        handler = RegularFieldConditionHandler.build(
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

    def test_regularfield_condition02(self):
        "Operator class."
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
            condition.value
        )

    def test_regularfield_condition03(self):
        "Build condition + errors."
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

    def test_regularfield_condition04(self):
        "Email + sub-part validation."
        build = partial(
            RegularFieldConditionHandler.build_condition,
            model=FakeOrganisation, field_name='email',
        )

        # Problem a part of a email address is not a valid email address
        with self.assertRaises(FilterConditionHandler.ValueError) as cm:
            build(operator=operators.EQUALS, values=['misato'])
        self.assertEqual(
            "['{}']".format(_('Enter a valid email address.')),
            cm.exception.args[0],
        )

        # ---
        with self.assertNoException():
            build(operator=operators.ISTARTSWITH, values=['misato'])

        with self.assertNoException():
            build(operator=operators.RANGE, values=['misato', 'yui'])

        with self.assertNoException():
            build(operator=operators.EQUALS, values=['misato@nerv.jp'])

    def test_regularfield_condition05(self):
        "Credentials for entity FK."
        user = self.login()
        other_user = self.other_user

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

    def test_regularfield_get_q(self):
        "ForeignKey."
        user = self.create_user()
        sector_id = 3
        handler = RegularFieldConditionHandler(
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

    def test_regularfield_description01(self):
        user = self.create_user()

        value = 'Corp'
        handler = RegularFieldConditionHandler(
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

    def test_regularfield_description02(self):
        "Other field & operator."
        user = self.create_user()

        value = 'Spiegel'
        handler = RegularFieldConditionHandler(
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

    def test_regularfield_description03(self):
        "ForeignKey."
        user = self.create_user()
        position1, position2 = FakePosition.objects.all()[:2]

        handler1 = RegularFieldConditionHandler(
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

    def test_regularfield_description04(self):
        "ForeignKey to CremeEntity."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role, value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_OWN,
        )

        create_folder = partial(FakeFolder.objects.create, user=user)
        folder1 = create_folder(title='Pix')
        folder2 = create_folder(title='Music')
        folder3 = create_folder(title='ZZZ',  user=self.other_user)

        handler = RegularFieldConditionHandler(
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

    def test_regularfield_description05(self):
        "ManyToManyField."
        user = self.create_user()
        cat1, cat2 = FakeImageCategory.objects.all()[:2]

        handler1 = RegularFieldConditionHandler(
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

    def test_dateregularfield_init(self):
        fname = 'created'
        range_name = 'previous_year'
        handler = DateRegularFieldConditionHandler(
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

    def test_dateregularfield_error(self):
        "<error> property."
        handler1 = DateRegularFieldConditionHandler(
            model=FakeOrganisation,
            field_name='unknown',
            date_range='previous_year',
        )
        self.assertEqual(
            "FakeOrganisation has no field named 'unknown'",
            handler1.error,
        )

        handler2 = DateRegularFieldConditionHandler(
            model=FakeOrganisation,
            field_name='sector',
            date_range='previous_year',
        )
        self.assertEqual("'sector' is not a date field", handler2.error)

    def test_dateregularfield_applicable_on_entity_base(self):
        handler = DateRegularFieldConditionHandler(
            model=FakeOrganisation,
            field_name='creation_date',
            date_range='current_quarter',
        )
        self.assertIs(handler.applicable_on_entity_base, False)

    def test_dateregularfield_build01(self):
        fname = 'modified'
        range_name = 'yesterday'
        handler = DateRegularFieldConditionHandler.build(
            model=FakeContact,
            name=fname,
            data={'name': range_name},
        )
        self.assertEqual(FakeContact, handler.model)
        self.assertIsNone(handler.subfilter_id)
        self.assertEqual(fname,      handler._field_name)
        self.assertEqual(range_name, handler._range_name)
        self.assertIsNone(handler._start)
        self.assertIsNone(handler._end)

    def test_dateregularfield_build02(self):
        "Invalid data."
        with self.assertRaises(FilterConditionHandler.DataError):
            DateRegularFieldConditionHandler.build(
                model=FakeOrganisation, name='created',
                data=[],  # <= not a dict.
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            DateRegularFieldConditionHandler.build(
                model=FakeOrganisation,
                name='name',
                data={'start': 'notadict'},
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            DateRegularFieldConditionHandler.build(
                model=FakeOrganisation,
                name='name',
                data={'start': {'foo': 'bar'}},
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            DateRegularFieldConditionHandler.build(
                model=FakeOrganisation,
                name='name',
                data={'start': {'year': 'notanint'}},
            )

    def test_dateregularfield_formfield(self):
        user = self.create_user()

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

    def test_dateregularfield_condition01(self):
        "Build condition."
        # GTE ---
        fname1 = 'birthday'
        condition1 = DateRegularFieldConditionHandler.build_condition(
            model=FakeContact, field_name=fname1,
            start=date(year=2000, month=1, day=1),
        )
        self.assertIsInstance(condition1, EntityFilterCondition)
        self.assertIsNone(condition1.pk)
        self.assertEqual(EF_USER,                                  condition1.filter_type)
        self.assertEqual(DateRegularFieldConditionHandler.type_id, condition1.type)
        self.assertEqual(fname1,                                   condition1.name)
        self.assertDictEqual(
            {'start': {'day': 1, 'month': 1, 'year': 2000}},
            condition1.value,
        )

        handler1 = DateRegularFieldConditionHandler.build(
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

    def test_dateregularfield_condition02(self):
        "Build condition + errors."
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

    def test_dateregularfield_description01(self):
        user = self.create_user()

        handler = DateRegularFieldConditionHandler(
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

    def test_dateregularfield_description02(self):
        "Other field & named range."
        user = self.create_user()

        handler = DateRegularFieldConditionHandler(
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

    def test_dateregularfield_description03(self):
        "Custom ranges."
        user = self.create_user()

        start = date(year=2000, month=6, day=1)
        handler1 = DateRegularFieldConditionHandler(
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
            model=FakeContact,
            field_name='birthday',
        )
        self.assertEqual('??', handler4.description(user=user))

    def test_customfield_init01(self):
        custom_field = CustomField.objects.create(
            name='Is a foundation?', field_type=CustomField.BOOL,
            content_type=FakeOrganisation,
        )

        operator_id = operators.EQUALS
        value = 'True'
        rname = 'customfieldboolean'
        handler = CustomFieldConditionHandler(
            model=FakeOrganisation,
            custom_field=custom_field.id,
            operator_id=operator_id,
            values=[value],
            related_name=rname,
        )

        self.assertEqual(FakeOrganisation, handler.model)
        self.assertIsNone(handler.subfilter_id)
        self.assertIs(handler.subfilter, False)
        self.assertEqual(custom_field.id, handler._custom_field_id)
        self.assertEqual(operator_id,     handler._operator_id)
        self.assertEqual([value],         handler._values)
        self.assertEqual(rname,           handler._related_name)

        self.assertIsNone(handler.error)
        self.assertIs(handler.applicable_on_entity_base, True)

        self.assertQEqual(
            Q(pk__in=FakeOrganisation.objects.none()),
            handler.get_q(user=None)
        )

        # ---
        with self.assertNumQueries(1):
            cfield2 = handler.custom_field

        self.assertEqual(custom_field, cfield2)

        with self.assertNumQueries(0):
            handler.custom_field  # NOQA

        # ---
        with self.assertRaises(TypeError):
            CustomFieldConditionHandler(
                # model=FakeOrganisation,  # <== missing
                custom_field=custom_field.id,
                operator_id=operator_id,
                values=[value],
                related_name=rname,
            )

        # ---
        with self.assertRaises(TypeError):
            CustomFieldConditionHandler(
                model=FakeOrganisation,
                custom_field=custom_field.id,
                operator_id=operator_id,
                values=[value],
                # related_name=rname,  # <== missing
            )

    def test_customfield_init02(self):
        "Pass a CustomField instance."
        custom_field = CustomField.objects.create(
            name='Is a foundation?', field_type=CustomField.BOOL,
            content_type=FakeOrganisation,
        )

        operator_id = operators.EQUALS
        value = 'True'
        handler = CustomFieldConditionHandler(
            custom_field=custom_field,
            operator_id=operator_id,
            values=[value],
        )

        self.assertEqual(FakeOrganisation,     handler.model)
        self.assertEqual(custom_field.id,      handler._custom_field_id)
        self.assertEqual('customfieldboolean', handler._related_name)

    def test_customfield_error(self):
        "<error> property."
        custom_field = CustomField.objects.create(
            name='Base line', field_type=CustomField.STR,
            content_type=FakeOrganisation,
        )

        handler1 = CustomFieldConditionHandler(
            model=FakeOrganisation,
            custom_field=custom_field,
            operator_id=1234,  # <=
            values=['Corp'],
        )
        self.assertEqual("Operator ID '1234' is invalid", handler1.error)

        # ---
        handler2 = CustomFieldConditionHandler(
            model=FakeOrganisation,
            custom_field=custom_field.id,
            operator_id=operators.EQUALS,
            values=['True'],
            related_name='invalid',  # <===
        )
        self.assertEqual("related_name 'invalid' is invalid", handler2.error)

    def test_customfield_build01(self):
        cfield_id = 6
        operator_id = operators.GT
        value = 25
        rname = 'customfieldinteger'
        handler = CustomFieldConditionHandler.build(
            model=FakeContact,
            name=str(cfield_id),
            data={
                'operator': operator_id,
                'rname': rname,
                'values': [value],
            },
        )
        self.assertEqual(FakeContact, handler.model)
        self.assertIsNone(handler.subfilter_id)
        self.assertEqual(cfield_id,   handler._custom_field_id)
        self.assertEqual(operator_id, handler._operator_id)
        self.assertEqual([value],     handler._values)
        self.assertEqual(rname,       handler._related_name)

    def test_customfield_build02(self):
        cfield_id = '6'
        operator_id = operators.GT
        value = 25
        rname = 'customfieldinteger'

        with self.assertRaises(FilterConditionHandler.DataError):
            CustomFieldConditionHandler.build(
                model=FakeOrganisation, name=cfield_id,
                data=[],  # <= not a dict.
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            CustomFieldConditionHandler.build(
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
                model=FakeOrganisation,
                name='notanint',  # <==
                data={
                    'operator': operator_id,
                    'rname': rname,
                    'value': [value],
                },
            )

    def test_customfield_formfield(self):
        user = self.create_user()

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

    def test_customfield_accept_int(self):
        user = self.create_user()

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
            model=FakeOrganisation,
            custom_field=custom_field.id,
            operator_id=operators.EQUALS,
            values=[4],
            related_name='customfieldint',
        )
        self.assertIs(handler1.accept(entity=bebop,     user=user), True)
        self.assertIs(handler1.accept(entity=dragons,   user=user), False)
        self.assertIs(handler1.accept(entity=swordfish, user=user), False)

        # String format ---
        handler2 = CustomFieldConditionHandler(
            model=FakeOrganisation,
            custom_field=custom_field.id,
            operator_id=operators.EQUALS,
            values=['4'],
            related_name='customfieldint',
        )
        self.assertIs(handler2.accept(entity=bebop,     user=user), True)
        self.assertIs(handler2.accept(entity=dragons,   user=user), False)
        self.assertIs(handler2.accept(entity=swordfish, user=user), False)

    def test_customfield_accept_bool(self):
        user = self.create_user()

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
            model=FakeOrganisation,
            custom_field=custom_field.id,
            operator_id=operators.EQUALS,
            values=[True],
            related_name='customfieldboolean',
        )
        self.assertIs(handler1.accept(entity=bebop,     user=user), True)
        self.assertIs(handler1.accept(entity=dragons,   user=user), False)
        self.assertIs(handler1.accept(entity=swordfish, user=user), False)

        # String format ---
        handler2 = CustomFieldConditionHandler(
            model=FakeOrganisation,
            custom_field=custom_field.id,
            operator_id=operators.EQUALS,
            values=['True'],
            related_name='customfieldboolean',
        )
        self.assertIs(handler2.accept(entity=bebop,     user=user), True)
        self.assertIs(handler2.accept(entity=dragons,   user=user), False)
        self.assertIs(handler2.accept(entity=swordfish, user=user), False)

    def test_customfield_accept_decimal(self):
        user = self.create_user()

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
            model=FakeOrganisation,
            custom_field=custom_field.id,
            operator_id=operators.LTE,
            values=['2000'],
            related_name='customfieldfloat',
        )
        self.assertIs(handler.accept(entity=bebop,     user=user), True)
        self.assertIs(handler.accept(entity=dragons,   user=user), False)
        self.assertIs(handler.accept(entity=swordfish, user=user), False)

    def test_customfield_accept_enum(self):
        user = self.create_user()

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
            model=FakeOrganisation,
            custom_field=custom_field.id,
            operator_id=operators.EQUALS,
            values=[enum_small.id, enum_medium.id],
            related_name='customfieldenum',
        )
        self.assertIs(handler1.accept(entity=swordfish, user=user), True)
        self.assertIs(handler1.accept(entity=bebop,     user=user), False)
        self.assertIs(handler1.accept(entity=redtail,   user=user), False)

        # ISEMPTY ---
        handler2 = CustomFieldConditionHandler(
            model=FakeOrganisation,
            custom_field=custom_field.id,
            operator_id=operators.ISEMPTY,
            values=[True],
            related_name='customfieldenum',
        )
        self.assertIs(handler2.accept(entity=swordfish, user=user), False)
        self.assertIs(handler2.accept(entity=bebop,     user=user), False)
        self.assertIs(handler2.accept(entity=redtail,   user=user), True)

        # String format ---
        handler3 = CustomFieldConditionHandler(
            model=FakeOrganisation,
            custom_field=custom_field.id,
            operator_id=operators.EQUALS,
            values=[str(enum_small.id), str(enum_medium.id)],
            related_name='customfieldenum',
        )
        self.assertIs(handler3.accept(entity=swordfish, user=user), True)
        self.assertIs(handler3.accept(entity=bebop,     user=user), False)
        self.assertIs(handler3.accept(entity=redtail,   user=user), False)

    def test_customfield_accept_multienum(self):
        "MULTI_ENUM."
        user = self.create_user()

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
            model=FakeOrganisation,
            custom_field=custom_field.id,
            operator_id=operators.EQUALS,
            values=[enum_attack.id, enum_fret.id],
            related_name='customfieldmultienum',
        )
        self.assertIs(handler1.accept(entity=swordfish, user=user), True)
        self.assertIs(handler1.accept(entity=redtail,   user=user), False)
        self.assertIs(handler1.accept(entity=bebop,     user=user), True)

        # ISEMPTY ---
        handler2 = CustomFieldConditionHandler(
            model=FakeOrganisation,
            custom_field=custom_field.id,
            operator_id=operators.ISEMPTY,
            values=[True],
            related_name='customfieldmultienum',
        )
        self.assertIs(handler2.accept(entity=swordfish, user=user), False)
        self.assertIs(handler2.accept(entity=bebop,     user=user), False)
        self.assertIs(handler2.accept(entity=redtail,   user=user), True)

        # String format ---
        handler3 = CustomFieldConditionHandler(
            model=FakeOrganisation,
            custom_field=custom_field.id,
            operator_id=operators.EQUALS,
            values=[str(enum_attack.id), str(enum_fret.id)],
            related_name='customfieldmultienum',
        )
        self.assertIs(handler3.accept(entity=swordfish, user=user), True)
        self.assertIs(handler3.accept(entity=redtail,   user=user), False)
        self.assertIs(handler3.accept(entity=bebop,     user=user), True)

        # ISEMPTY (False) ---
        handler4 = CustomFieldConditionHandler(
            model=FakeOrganisation,
            custom_field=custom_field.id,
            operator_id=operators.ISEMPTY,
            values=[False],
            related_name='customfieldmultienum',
        )
        self.assertIs(handler4.accept(entity=swordfish, user=user), True)
        self.assertIs(handler4.accept(entity=bebop,     user=user), True)
        self.assertIs(handler4.accept(entity=redtail,   user=user), False)

    def test_customfield_condition01(self):
        "Build condition."
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
        self.assertEqual(EF_USER,                             condition.filter_type)
        self.assertEqual(CustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(custom_field.id),                condition.name)
        self.assertDictEqual(
            {
                'operator': operator_id,
                'values': [str(value)],
                'rname': rname,
            },
            condition.value,
        )

        handler = CustomFieldConditionHandler.build(
            model=FakeContact,
            name=condition.name,
            data=condition.value,
        )
        self.assertIsInstance(handler, CustomFieldConditionHandler)
        self.assertEqual(FakeContact, handler.model)
        self.assertIsNone(handler.subfilter_id)
        self.assertIs(handler.subfilter, False)
        self.assertEqual(custom_field.id, handler._custom_field_id)
        self.assertEqual(operator_id,     handler._operator_id)
        self.assertEqual([str(value)],    handler._values)
        self.assertEqual(rname,           handler._related_name)

    def test_customfield_condition02(self):
        "Build condition + operator class."
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
        self.assertEqual(str(custom_field.id), condition.name)
        self.assertDictEqual(
            {
                'operator': operators.LTE,
                'values': [str(value)],
                'rname': rname,
            },
            condition.value,
        )

    def test_customfield_condition03(self):
        "Build condition + errors."
        create_cf = partial(CustomField.objects.create, content_type=FakeContact)
        cf_int = create_cf(name='size (cm)', field_type=CustomField.INT)

        ValueError = FilterConditionHandler.ValueError
        build_cond = CustomFieldConditionHandler.build_condition

        self.assertRaises(
            ValueError, build_cond,
            custom_field=cf_int, operator=1216, values=155,  # Invalid operator
        )
        self.assertRaises(
            ValueError, build_cond,
            custom_field=cf_int, operator=operators.CONTAINS, values='not an int',
        )

        cf_date = create_cf(name='Day', field_type=CustomField.DATETIME)
        self.assertRaises(
            ValueError, build_cond,
            custom_field=cf_date, operator=operators.EQUALS, values=2011,  # DATE
        )

        cf_bool = create_cf(name='Cute ?', field_type=CustomField.BOOL)
        self.assertRaises(
            ValueError, build_cond,
            custom_field=cf_bool, operator=operators.CONTAINS, values=True,  # Bad operator
        )

    def test_customfield_condition04(self):
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

    def test_customfield_get_q_bool(self):
        "get_q() not empty."
        user = self.create_user()

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
            model=FakeOrganisation,
            custom_field=custom_field.id,
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
            model=FakeOrganisation,
            custom_field=custom_field.id,
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
            model=FakeOrganisation,
            custom_field=custom_field.id,
            operator_id=operators.EQUALS,
            values=['False'],
            related_name='customfieldboolean',
        )
        self.assertQEqual(
            Q(pk__in=FakeOrganisation.objects.filter(id=dragons.id).values_list('id', flat=True)),
            handler3.get_q(user=None),
        )

    def test_customfield_description01(self):
        user = self.create_user()

        custom_field = CustomField.objects.create(
            name='Size', field_type=CustomField.INT,
            content_type=FakeContact,
        )

        value = 25
        handler = CustomFieldConditionHandler(
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

    def test_customfield_description02(self):
        "Other field & operator."
        user = self.create_user()

        custom_field = CustomField.objects.create(
            name='Degree', field_type=CustomField.STR,
            content_type=FakeContact,
        )

        value = 'phD'
        handler = CustomFieldConditionHandler(
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

    def test_customfield_description03(self):
        "ENUM."
        user = self.create_user()

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

    def test_customfield_description04(self):
        "MULTI_ENUM."
        user = self.create_user()

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

    def test_customfield_description05(self):
        "Deleted CustomField."
        user = self.create_user()

        handler = CustomFieldConditionHandler(
            model=FakeOrganisation,
            custom_field=1025,
            related_name='customfieldinteger',
            operator_id=operators.EQUALS,
            values=[42],
        )
        self.assertEqual('???', handler.description(user))

    def test_datecustomfield_init01(self):
        custom_field = CustomField.objects.create(
            name='First fight',
            content_type=FakeOrganisation,
            field_type=CustomField.DATETIME,
        )

        rname = 'customfielddatetime'
        range_name = 'next_year'
        handler = DateCustomFieldConditionHandler(
            model=FakeOrganisation,
            custom_field=custom_field.id,
            related_name=rname,
            date_range=range_name,
        )

        self.assertEqual(FakeOrganisation, handler.model)
        self.assertIsNone(handler.subfilter_id)
        self.assertIs(handler.subfilter, False)
        self.assertEqual(custom_field.id, handler._custom_field_id)
        self.assertEqual(rname,           handler._related_name)
        self.assertEqual(range_name,      handler._range_name)
        self.assertIsNone(handler._start)
        self.assertIsNone(handler._end)

        self.assertIsNone(handler.error)
        self.assertIs(handler.applicable_on_entity_base, True)

        self.assertQEqual(
            Q(pk__in=FakeOrganisation.objects.none()),
            handler.get_q(user=None),
        )

        # ---
        with self.assertNumQueries(1):
            cfield2 = handler.custom_field

        self.assertEqual(custom_field, cfield2)

        with self.assertNumQueries(0):
            handler.custom_field  # NOQA

    def test_datecustomfield_init02(self):
        "Pass a CustomField instance + start/end."
        custom_field = CustomField.objects.create(
            name='First fight',
            content_type=FakeOrganisation,
            field_type=CustomField.DATETIME,
        )

        start = self.create_datetime(year=2019, month=8, day=1)
        end   = self.create_datetime(year=2019, month=8, day=31)
        handler = DateCustomFieldConditionHandler(
            custom_field=custom_field,
            start=start,
            end=end,
        )

        self.assertEqual(FakeOrganisation,      handler.model)
        self.assertEqual(custom_field.id,       handler._custom_field_id)
        self.assertEqual('customfielddatetime', handler._related_name)
        self.assertIsNone(handler._range_name)
        self.assertEqual(start, handler._start)
        self.assertEqual(end,   handler._end)

        # ---
        with self.assertNumQueries(0):
            cfield2 = handler.custom_field

        self.assertEqual(custom_field, cfield2)

    def test_datecustomfield_error(self):
        "<error> property."
        handler = DateCustomFieldConditionHandler(
            model=FakeOrganisation,
            custom_field=12,
            date_range='yesterday',
            related_name='invalid',  # <===
        )
        self.assertEqual("related_name 'invalid' is invalid", handler.error)

    def test_datecustomfield_build01(self):
        cfield_id = 6
        range_name = 'today'
        rname = 'customfielddatetime'
        handler = DateCustomFieldConditionHandler.build(
            model=FakeContact,
            name=str(cfield_id),
            data={
                'rname': rname,
                'name':  range_name,
            },
        )
        self.assertEqual(FakeContact, handler.model)
        self.assertIsNone(handler.subfilter_id)
        self.assertEqual(cfield_id,   handler._custom_field_id)
        self.assertEqual(rname,       handler._related_name)
        self.assertEqual(range_name,  handler._range_name)
        self.assertIsNone(handler._start)
        self.assertIsNone(handler._end)

    def test_datecustomfield_build02(self):
        cfield_id = '6'
        rname = 'customfielddatetime'

        with self.assertRaises(FilterConditionHandler.DataError):
            DateCustomFieldConditionHandler.build(
                model=FakeOrganisation, name=cfield_id,
                data=[],  # <= not a dict.
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            DateCustomFieldConditionHandler.build(
                model=FakeOrganisation,
                name=cfield_id,
                data={},  # 'rname': rname,  # Missing
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            DateCustomFieldConditionHandler.build(
                model=FakeOrganisation,
                name='notanint',  # <==
                data={'rname': rname},
            )

    def test_datecustomfield_formfield(self):
        user = self.create_user()

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

    def test_datecustomfield_condition01(self):
        "Build condition."
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
        self.assertEqual(EF_USER,                                 condition1.filter_type)
        self.assertEqual(DateCustomFieldConditionHandler.type_id, condition1.type)
        self.assertEqual(str(custom_field.id),                    condition1.name)
        self.assertDictEqual(
            {
                'rname': rname,
                'start': {'day': 1, 'month': 4, 'year': 2015},
            },
            condition1.value,
        )

        handler1 = DateCustomFieldConditionHandler.build(
            model=FakeContact,
            name=condition1.name,
            data=condition1.value,
        )
        self.assertIsInstance(handler1, DateCustomFieldConditionHandler)
        self.assertEqual(FakeContact, handler1.model)
        self.assertIsNone(handler1.subfilter_id)
        self.assertIs(handler1.subfilter, False)
        self.assertEqual(custom_field.id, handler1._custom_field_id)
        self.assertEqual(rname,           handler1._related_name)
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

    def test_datecustomfield_condition02(self):
        "Build condition + errors."
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

    def test_datecustomfield_get_q(self):
        "get_q() not empty."
        user = self.create_user()

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
            model=FakeOrganisation,
            custom_field=custom_field.id,
            related_name='customfielddatetime',
            date_range='previous_year',
        )

        self.assertQEqual(
            # NB: the nested QuerySet is not compared by the query, but by its result...
            Q(pk__in=FakeOrganisation.objects.filter(id=bebop.id).values_list('id', flat=True)),
            handler.get_q(user=None)
        )

    def test_datecustomfield_description01(self):
        user = self.create_user()

        custom_field = CustomField.objects.create(
            name='First fight', field_type=CustomField.DATETIME,
            content_type=FakeOrganisation,
        )

        handler1 = DateCustomFieldConditionHandler(
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
            custom_field=custom_field,
            date_range='current_year',
        )
        self.assertEqual(
            _('«{field}» is «{value}»').format(
                field=custom_field.name, value=_('Current year'),
            ),
            handler2.description(user=user),
        )

    def test_datecustomfield_description02(self):
        "Custom ranges."
        user = self.create_user()

        custom_field = CustomField.objects.create(
            name='First fight', field_type=CustomField.DATETIME,
            content_type=FakeOrganisation,
        )

        start = date(year=2000, month=6, day=1)
        handler1 = DateCustomFieldConditionHandler(
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

    def test_datecustomfield_description03(self):
        "Deleted CustomField."
        user = self.create_user()

        handler = DateCustomFieldConditionHandler(
            model=FakeOrganisation,
            related_name='customfielddatetime',
            custom_field=self.UNUSED_PK,
            date_range='previous_year',
        )
        self.assertEqual('???', handler.description(user=user))

    def test_relation_init01(self):
        user = self.create_user()
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by')
        )[0]

        handler1 = RelationConditionHandler(
            model=FakeOrganisation,
            rtype=rtype.id,
            exclude=False,
        )

        self.assertEqual(FakeOrganisation, handler1.model)
        self.assertIsNone(handler1.subfilter_id)
        self.assertIs(handler1.subfilter, False)
        self.assertEqual(rtype.id, handler1._rtype_id)
        self.assertIs(handler1._exclude, False)
        self.assertIsNone(handler1._ct_id)
        self.assertIsNone(handler1._entity_id)

        self.assertIsNone(handler1.error)
        self.assertIs(handler1.applicable_on_entity_base, True)

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
            model=FakeOrganisation,
            rtype=rtype.id,
            ctype=ctype_id,
            exclude=True,
        )

        self.assertIs(handler2._exclude, True)
        self.assertEqual(ctype_id, handler2._ct_id)

        # ---
        entity = FakeContact.objects.create(user=user, last_name='Ayanami', first_name='Rei')
        handler3 = RelationConditionHandler(
            model=FakeOrganisation,
            rtype=rtype.id,
            entity=entity.id,
        )

        self.assertIs(handler3._exclude, False)
        self.assertEqual(entity.id, handler3._entity_id)

        # ---
        ContentType.objects.get_for_model(CremeEntity)  # pre-fill the cache

        with self.assertNumQueries(2):
            e3 = handler3.entity
        self.assertEqual(entity, e3)

        with self.assertNumQueries(0):
            handler3.entity  # NOQA

    def test_relation_init02(self):
        "Pass an instance of RelationType."
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by'),
        )[0]

        handler = RelationConditionHandler(
            model=FakeContact,
            rtype=rtype,
        )

        self.assertEqual(FakeContact, handler.model)
        self.assertEqual(rtype.id, handler._rtype_id)
        self.assertIsNone(handler.content_type)

        # ---
        with self.assertNumQueries(0):
            rtype2 = handler.relation_type

        self.assertEqual(rtype, rtype2)

    def test_relation_init03(self):
        "Pass an instance of ContentType."
        ctype = ContentType.objects.get_for_model(FakeContact)
        handler = RelationConditionHandler(
            model=FakeOrganisation,
            rtype='creme_core-subject_type1',
            ctype=ctype,
        )

        self.assertEqual(FakeOrganisation, handler.model)
        self.assertEqual(ctype.id, handler._ct_id)
        self.assertEqual(ctype, handler.content_type)

    def test_relation_init04(self):
        "Pass an instance of CremeEntity."
        user = self.create_user()
        entity = FakeOrganisation.objects.create(user=user, name='Acme')
        handler = RelationConditionHandler(
            model=FakeOrganisation,
            rtype='creme_core-subject_type1',
            entity=entity,
            ctype=12,  # <= should not be used
        )

        self.assertEqual(FakeOrganisation, handler.model)
        self.assertEqual(entity.id, handler._entity_id)
        self.assertIsNone(handler._ct_id)

        # --
        with self.assertNumQueries(0):
            e = handler.entity
        self.assertEqual(entity, e)

    def test_relation_build01(self):
        rtype_id1 = 'creme_core-subject_test1'
        handler1 = RelationConditionHandler.build(
            model=FakeContact,
            name=rtype_id1,
            data={'has': True},
        )
        self.assertEqual(FakeContact, handler1.model)
        self.assertIsNone(handler1.subfilter_id)
        self.assertEqual(rtype_id1,  handler1._rtype_id)
        self.assertFalse(handler1._exclude)
        self.assertIsNone(handler1._ct_id)
        self.assertIsNone(handler1._entity_id)

        # --
        rtype_id2 = 'creme_core-subject_test2'
        ct_id = 56
        handler2 = RelationConditionHandler.build(
            model=FakeOrganisation,
            name=rtype_id2,
            data={
                'has': False,
                'ct_id': ct_id,
            },
        )
        self.assertEqual(FakeOrganisation, handler2.model)
        self.assertEqual(rtype_id2,  handler2._rtype_id)
        self.assertTrue(handler2._exclude)
        self.assertEqual(ct_id, handler2._ct_id)
        self.assertIsNone(handler2._entity_id)

        # --
        entity_id = 564
        handler3 = RelationConditionHandler.build(
            model=FakeOrganisation,
            name=rtype_id2,
            data={
                'has': False,
                'entity_id': entity_id,
            },
        )
        self.assertIsNone(handler3._ct_id)
        self.assertEqual(entity_id, handler3._entity_id)

    def test_relation_build02(self):
        "Errors."
        rtype_id = 'creme_core-subject_test'

        with self.assertRaises(FilterConditionHandler.DataError):
            RelationConditionHandler.build(
                model=FakeOrganisation,
                name=rtype_id,
                data=[],  # <= not a dict.
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            RelationConditionHandler.build(
                model=FakeOrganisation,
                name=rtype_id,
                data={},  # Missing 'has': True
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            RelationConditionHandler.build(
                model=FakeOrganisation,
                name=rtype_id,
                data={'has': 25},  # Not a Boolean
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            RelationConditionHandler.build(
                model=FakeOrganisation,
                name=rtype_id,
                data={
                    'has':   False,
                    'ct_id': 'notanint',  # <==
                },
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            RelationConditionHandler.build(
                model=FakeOrganisation,
                name=rtype_id,
                data={
                    'has': False,
                    'entity_id': 'notanint',  # <==
                },
            )

    def test_relation_formfield(self):
        user = self.create_user()

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

    def test_relation_condition(self):
        "Build condition."
        user = self.create_user()

        loves, loved = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by'),
        )

        build_cond = partial(RelationConditionHandler.build_condition, model=FakeContact)
        condition1 = build_cond(rtype=loves, has=True)
        self.assertIsInstance(condition1, EntityFilterCondition)
        self.assertIsNone(condition1.pk)
        self.assertEqual(EF_USER,                          condition1.filter_type)
        self.assertEqual(RelationConditionHandler.type_id, condition1.type)
        self.assertEqual(loves.id,                         condition1.name)
        self.assertDictEqual({'has': True}, condition1.value)

        handler1 = RelationConditionHandler.build(
            model=FakeContact,
            name=condition1.name,
            data=condition1.value,
        )
        self.assertIsInstance(handler1, RelationConditionHandler)
        self.assertEqual(FakeContact, handler1.model)
        self.assertIsNone(handler1.subfilter_id)
        self.assertIs(handler1.subfilter, False)
        self.assertEqual(loves.id, handler1._rtype_id)
        self.assertIs(handler1._exclude, False)
        self.assertIsNone(handler1._ct_id)
        self.assertIsNone(handler1._entity_id)

        # ---
        condition2 = build_cond(rtype=loved, has=False, filter_type=EF_CREDENTIALS)
        self.assertEqual(loved.id, condition2.name)
        self.assertEqual(EF_CREDENTIALS, condition2.filter_type)
        self.assertDictEqual({'has': False}, condition2.value)

        handler2 = RelationConditionHandler.build(
            model=FakeContact,
            name=condition2.name,
            data=condition2.value,
        )
        self.assertIs(handler2._exclude, True)

        # ---
        ct = ContentType.objects.get_for_model(FakeContact)
        condition3 = build_cond(rtype=loves, ct=ct)
        self.assertEqual(loves.id, condition3.name)
        self.assertDictEqual({'has': True, 'ct_id': ct.id}, condition3.value)

        handler3 = RelationConditionHandler.build(
            model=FakeContact,
            name=condition3.name,
            data=condition3.value,
        )
        self.assertEqual(ct.id, handler3._ct_id)

        # ---
        # NB: "ct" should not be used
        orga = FakeOrganisation.objects.create(user=user, name='Nerv')
        condition4 = build_cond(rtype=loves, ct=ct, entity=orga)
        self.assertEqual(loves.id, condition4.name)
        self.assertDictEqual(
            {'has': True, 'entity_id': orga.id}, condition4.value,
        )

        handler4 = RelationConditionHandler.build(
            model=FakeContact,
            name=condition4.name,
            data=condition4.value,
        )
        self.assertIsNone(handler4._ct_id)
        self.assertEqual(orga.id, handler4._entity_id)

    def test_relation_get_q(self):
        "get_q() not empty."
        user = self.create_user()

        loves, loved = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by'),
        )

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
            model=FakeContact, rtype=loves.id, exclude=True,
        )
        self.assertQPkIn(
            handler2.get_q(user=user),
            shinji, asuka, misato,
            negated=True,
        )

        # CT ---
        handler3 = RelationConditionHandler(
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
            model=FakeContact,
            rtype=loves.id,
            entity=rei.id,
        )
        self.assertQEqual(
            Q(pk__in=Relation.objects
                             .filter(id=rel1.id)
                             .values_list('subject_entity_id', flat=True)),
            handler4.get_q(user=user),
        )

    def test_relation_accept(self):
        user = self.create_user()
        loves = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by'),
        )[0]

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

        handler1 = RelationConditionHandler(model=FakeContact, rtype=loves.id)

        self.assertIs(handler1.accept(entity=shinji, user=user), True)
        self.assertIs(handler1.accept(entity=asuka,  user=user), True)
        self.assertIs(handler1.accept(entity=misato, user=user), True)
        self.assertIs(handler1.accept(entity=rei,    user=user), False)
        self.assertIs(handler1.accept(entity=gendo,  user=user), False)

        # Exclude ---
        handler2 = RelationConditionHandler(
            model=FakeContact, rtype=loves.id, exclude=True,
        )
        self.assertIs(handler2.accept(entity=shinji, user=user), False)
        self.assertIs(handler2.accept(entity=misato, user=user), False)
        self.assertIs(handler2.accept(entity=asuka,  user=user), False)
        self.assertIs(handler2.accept(entity=rei,    user=user), True)
        self.assertIs(handler2.accept(entity=gendo,  user=user), True)

        # CT ---
        handler3 = RelationConditionHandler(
            model=FakeContact,
            rtype=loves.id,
            ctype=ContentType.objects.get_for_model(FakeContact),
        )
        self.assertIs(handler3.accept(entity=shinji, user=user), True)
        self.assertIs(handler3.accept(entity=misato, user=user), False)

        # Entity ---
        handler4 = RelationConditionHandler(
            model=FakeContact,
            rtype=loves.id,
            entity=rei.id,
        )
        self.assertIs(handler4.accept(entity=shinji, user=user), True)
        self.assertIs(handler4.accept(entity=asuka,  user=user), False)

    def test_relation_description01(self):
        user = self.login()

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by'),
        )[0]

        handler1 = RelationConditionHandler(
            model=FakeOrganisation,
            rtype=rtype,
        )
        self.assertEqual(
            _('The entities have relationships «{predicate}»').format(predicate=rtype.predicate),
            handler1.description(user)
        )

        # ---
        ctype = ContentType.objects.get_for_model(FakeContact)
        handler2 = RelationConditionHandler(
            model=FakeOrganisation,
            rtype=rtype,
            ctype=ctype,
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
            model=FakeContact,
            rtype=rtype,
            entity=entity,
        )
        self.assertEqual(
            _('The entities have relationships «{predicate}» to «{entity}»').format(
                predicate=rtype.predicate,
                entity=entity,
            ),
            handler3.description(user),
        )

    def test_relation_description02(self):
        user = self.login()

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_like', 'Is liking'),
            ('test-object_like',  'Is liked by'),
        )[0]

        handler1 = RelationConditionHandler(
            model=FakeContact,
            rtype=rtype,
            exclude=True,
        )
        self.assertEqual(
            _('The entities have no relationship «{predicate}»').format(predicate=rtype.predicate),
            handler1.description(user),
        )

        # ---
        ctype = ContentType.objects.get_for_model(FakeContact)
        handler2 = RelationConditionHandler(
            model=FakeOrganisation,
            rtype=rtype,
            ctype=ctype,
            exclude=True,
        )
        self.assertEqual(
            _('The entities have no relationship «{predicate}» to «{model}»').format(
                predicate=rtype.predicate,
                model='Test Contacts',
            ),
            handler2.description(user)
        )

        # ---
        entity = FakeContact.objects.create(user=user, last_name='Ayanami', first_name='Rei')
        handler3 = RelationConditionHandler(
            model=FakeContact,
            rtype=rtype,
            entity=entity,
            exclude=True,
        )
        self.assertEqual(
            _('The entities have no relationship «{predicate}» to «{entity}»').format(
                predicate=rtype.predicate,
                entity=entity,
            ),
            handler3.description(user),
        )

    def test_relation_description03(self):
        "Credentials."
        user = self.login(is_superuser=False)

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by'),
        )[0]
        entity = FakeContact.objects.create(
            user=self.other_user,
            last_name='Ayanami', first_name='Rei',
        )

        handler = RelationConditionHandler(
            model=FakeContact,
            rtype=rtype,
            entity=entity,
        )
        self.assertEqual(
            _('The entities have relationships «{predicate}» to «{entity}»').format(
                predicate=rtype.predicate,
                entity=_('Entity #{id} (not viewable)').format(id=entity.id),
            ),
            handler.description(user),
        )

    def test_relation_description04(self):
        "Errors."
        user = self.login()

        handler1 = RelationConditionHandler(
            model=FakeContact,
            rtype='doesnotexistanymore',
            exclude=True,
        )
        self.assertEqual('???', handler1.description(user))

        # ---
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_like', 'Is liking'),
            ('test-object_like',  'Is liked by'),
        )[0]
        handler2 = RelationConditionHandler(
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
            model=FakeOrganisation,
            rtype=rtype,
            ctype=self.UNUSED_PK,
            exclude=True,
        )
        self.assertEqual(
            _('The entities have no relationship «{predicate}» to «{model}»').format(
                predicate=rtype.predicate,
                model='???',
            ),
            handler3.description(user)
        )

    def test_subfilter_init01(self):
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

        self.assertQEqual(Q(name__exact='Bebop'), handler.get_q(user=None))

        # --
        with self.assertRaises(TypeError):
            SubFilterConditionHandler(
                # model=FakeOrganisation,  # No model passed
                subfilter=sub_efilter.id,
            )

    def test_subfilter_init02(self):
        "Pass EntityFilter instance."
        sub_efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01', model=FakeOrganisation, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation, field_name='name',
                    operator=operators.EQUALS, values=['Bebop'],
                ),
            ],
        )

        handler = SubFilterConditionHandler(subfilter=sub_efilter)
        self.assertEqual(FakeOrganisation, handler.model)
        self.assertEqual(sub_efilter.id, handler.subfilter_id)
        self.assertEqual(sub_efilter.id, handler._subfilter_id)

        with self.assertNumQueries(0):
            subfilter = handler.subfilter

        self.assertEqual(sub_efilter, subfilter)

    def test_subfilter_build(self):
        subfilter_id = 'creme_core-subject_test1'
        handler1 = SubFilterConditionHandler.build(
            model=FakeContact,
            name=subfilter_id,
            data=None,
        )
        self.assertEqual(FakeContact, handler1.model)
        self.assertEqual(subfilter_id,  handler1.subfilter_id)

    def test_subfilter_error(self):
        handler = SubFilterConditionHandler(
            model=FakeOrganisation,
            subfilter='invalid',
        )
        self.assertEqual("'invalid' is not a valid filter ID", handler.error)

    def test_subfilter_applicable_on_entity_base(self):
        sub_efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='description',
                    operator=operators.ICONTAINS, values=['Alchemist'],
                ),
            ],
        )

        handler = SubFilterConditionHandler(subfilter=sub_efilter)
        self.assertIs(handler.applicable_on_entity_base, True)

    def test_subfilter_formfield(self):
        user = self.create_user()

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

    def test_subfilter_accept(self):
        user = self.create_user()
        sub_efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='last_name',
                    operator=operators.EQUALS, values=['Elric'],
                ),
            ],
        )

        handler = SubFilterConditionHandler(subfilter=sub_efilter)

        create_contact = partial(FakeContact.objects.create, user=user)
        ed  = create_contact(first_name='Edward',   last_name='Elric')
        al  = create_contact(first_name='Alphonse', last_name='Elric')
        roy = create_contact(first_name='Roy',      last_name='Mustang')

        self.assertIs(handler.accept(entity=ed,  user=user), True)
        self.assertIs(handler.accept(entity=al,  user=user), True)
        self.assertIs(handler.accept(entity=roy, user=user), False)

    def test_subfilter_condition(self):
        "Build condition."
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
        self.assertEqual(EF_USER,                           condition1.filter_type)
        self.assertEqual(SubFilterConditionHandler.type_id, condition1.type)
        self.assertEqual(sub_efilter.id,                    condition1.name)
        self.assertEqual('',                                condition1.raw_value)
        self.assertIsNone(condition1.value)

        handler1 = SubFilterConditionHandler.build(
            model=FakeContact,
            name=condition1.name,
            data=condition1.value,
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

    def test_subfilter_description01(self):
        user = self.create_user()
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
            model=FakeOrganisation,
            subfilter=sub_efilter.id,
        )
        self.assertEqual(
            _('Entities are accepted by the filter «{}»').format(sub_efilter.name),
            handler.description(user)
        )

    def test_subfilter_description02(self):
        user = self.create_user()
        handler = SubFilterConditionHandler(
            model=FakeOrganisation,
            subfilter='doesnotexist',
        )
        self.assertEqual('???', handler.description(user))

    def test_relation_subfilter_init01(self):
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
            model=FakeOrganisation,
            subfilter=sub_efilter.id,
            rtype=rtype_id,
            exclude=False,
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

    def test_relation_subfilter_init02(self):
        "Pass an EntityFilter instance."
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

    def test_relation_subfilter_init03(self):
        "Pass a RelationType instance."
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by'),
        )[0]

        handler = RelationSubFilterConditionHandler(
            model=FakeContact,
            subfilter='creme_core-test_filter',
            rtype=rtype,
        )
        self.assertIs(handler._exclude, False)
        self.assertEqual(rtype.id, handler._rtype_id)

    def test_relation_subfilter_build01(self):
        rtype_id = 'creme_core-subject_test'
        subfilter_id = 'creme_core-filter_test'
        handler = RelationSubFilterConditionHandler.build(
            model=FakeContact,
            name=rtype_id,
            data={
                'has': True,
                'filter_id': subfilter_id,
            },
        )
        self.assertEqual(FakeContact,  handler.model)
        self.assertEqual(subfilter_id, handler.subfilter_id)
        self.assertEqual(rtype_id,     handler._rtype_id)
        self.assertFalse(handler._exclude)

    def test_relation_subfilter_build02(self):
        "Errors."
        rtype_id = 'creme_core-subject_test'
        subfilter_id = 'creme_core-filter_test'

        with self.assertRaises(FilterConditionHandler.DataError):
            RelationSubFilterConditionHandler.build(
                model=FakeOrganisation,
                name=rtype_id,
                data=[],  # <= not a dict.
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            RelationSubFilterConditionHandler.build(
                model=FakeOrganisation,
                name=rtype_id,
                data={
                    # 'has': True  # Missing
                    'filter_id': subfilter_id,
                },
            )

        with self.assertRaises(FilterConditionHandler.DataError):
            RelationSubFilterConditionHandler.build(
                model=FakeOrganisation,
                name=rtype_id,
                data={
                    'has': 25,   # Not a Boolean
                    'filter_id': subfilter_id,
                },
            )

    def test_relation_subfilter_error(self):
        handler = RelationSubFilterConditionHandler(
            model=FakeOrganisation,
            subfilter='invalid',
            rtype='creme_core-subject_test',
        )
        self.assertEqual("'invalid' is not a valid filter ID", handler.error)

    def test_relation_subfilter_formfield(self):
        user = self.create_user()

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

    def test_relation_subfilter_condition(self):
        "Build condition."
        loves, loved = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by'),
        )

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
        self.assertEqual(EF_USER,                                   condition1.filter_type)
        self.assertEqual(RelationSubFilterConditionHandler.type_id, condition1.type)
        self.assertEqual(loves.id,                                  condition1.name)
        self.assertDictEqual(
            {'filter_id': sub_efilter1.id, 'has': True},
            condition1.value,
        )

        handler1 = RelationSubFilterConditionHandler.build(
            model=FakeContact,
            name=condition1.name,
            data=condition1.value,
        )
        self.assertIsInstance(handler1, RelationSubFilterConditionHandler)
        self.assertEqual(FakeContact, handler1.model)
        self.assertEqual(sub_efilter1.id, handler1.subfilter_id)
        self.assertEqual(sub_efilter1,    handler1.subfilter)
        self.assertEqual(sub_efilter1.id, handler1._subfilter_id)
        self.assertEqual(loves.id,        handler1._rtype_id)
        self.assertIs(handler1._exclude, False)

        # ---
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
            model=FakeContact,
            name=condition2.name,
            data=condition2.value,
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

    def test_relation_subfilter_get_q(self):
        "get_q() not empty."
        user = self.create_user()

        loves, loved = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by'),
        )

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
            model=FakeOrganisation,
            subfilter=sub_filter.id,
            rtype=loves.id,
        )
        self.assertQPkIn(handler1.get_q(user=user), shinji, asuka)

        # Exclude ---
        handler2 = RelationSubFilterConditionHandler(
            model=FakeOrganisation,
            subfilter=sub_filter.id,
            rtype=loves.id,
            exclude=True,
        )
        self.assertQPkIn(
            handler2.get_q(user=user),
            shinji, asuka,
            negated=True,
        )

    def test_relation_subfilter_description01(self):
        user = self.create_user()

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by'),
        )[0]

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
            model=FakeOrganisation,
            rtype=rtype,
            subfilter=sub_filter,
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
            model=FakeOrganisation,
            rtype=rtype,
            subfilter=sub_filter,
            exclude=True
        )
        self.assertEqual(
            _('The entities have no relationship «{predicate}» to «{filter}»').format(
                predicate=rtype.predicate,
                filter=sub_filter,
            ),
            handler2.description(user),
        )

    def test_relation_subfilter_description02(self):
        user = self.create_user()

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
            model=FakeOrganisation,
            rtype='deosnotexist',
            subfilter=sub_filter,
        )
        self.assertEqual('???', handler1.description(user))

        # ---
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by'),
        )[0]

        handler2 = RelationSubFilterConditionHandler(
            model=FakeOrganisation,
            rtype=rtype,
            subfilter='doesnotexist',
        )
        self.assertEqual(
            _('The entities have relationships «{predicate}» to «{filter}»').format(
                predicate=rtype.predicate,
                filter='???',
            ),
            handler2.description(user),
        )

    def test_property_init01(self):
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_kawaii', text='Kawaii',
        )

        handler = PropertyConditionHandler(
            model=FakeOrganisation,
            ptype=ptype.id,
            exclude=False,
        )

        self.assertEqual(FakeOrganisation, handler.model)
        self.assertIsNone(handler.subfilter_id)
        self.assertIs(handler.subfilter, False)
        self.assertEqual(ptype.id, handler._ptype_id)
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

    def test_property_init02(self):
        "Pass a CremePropertyType instance."
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_kawaii', text='Kawaii',
        )

        handler = PropertyConditionHandler(
            model=FakeContact,
            ptype=ptype,
            exclude=True,
        )

        self.assertEqual(FakeContact, handler.model)
        self.assertEqual(ptype.id, handler._ptype_id)
        self.assertIs(handler._exclude, True)

        # ---
        with self.assertNumQueries(0):
            ptype2 = handler.property_type

        self.assertEqual(ptype, ptype2)

    def test_property_build01(self):
        ptype_id1 = 'creme_core-test1'
        handler1 = PropertyConditionHandler.build(
            model=FakeOrganisation,
            name=ptype_id1,
            data=True,
        )
        self.assertEqual(FakeOrganisation, handler1.model)
        self.assertIsNone(handler1.subfilter_id)
        self.assertEqual(ptype_id1, handler1._ptype_id)
        self.assertFalse(handler1._exclude)

        # --
        ptype_id2 = 'creme_core-test2'
        handler2 = PropertyConditionHandler.build(
            model=FakeContact,
            name=ptype_id2,
            data=False,
        )
        self.assertEqual(FakeContact, handler2.model)
        self.assertEqual(ptype_id2,   handler2._ptype_id)
        self.assertTrue(handler2._exclude)

    def test_property_build02(self):
        "Errors."
        with self.assertRaises(FilterConditionHandler.DataError):
            PropertyConditionHandler.build(
                model=FakeOrganisation,
                name='creme_core-test',
                data=[],  # <= not a Boolean.
            )

    def test_property_formfield(self):
        user = self.create_user()

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

    def test_property_condition(self):
        "Build condition."
        ptype1 = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_kawaii', text='Kawaii',
        )

        condition1 = PropertyConditionHandler.build_condition(
            model=FakeContact, ptype=ptype1, has=True,
        )
        self.assertIsInstance(condition1, EntityFilterCondition)
        self.assertIsNone(condition1.pk)
        self.assertEqual(EF_USER,                          condition1.filter_type)
        self.assertEqual(PropertyConditionHandler.type_id, condition1.type)
        self.assertEqual(ptype1.id,                        condition1.name)
        self.assertEqual(True,                             condition1.value)

        handler1 = PropertyConditionHandler.build(
            model=FakeContact,
            name=condition1.name,
            data=condition1.value,
        )
        self.assertIsInstance(handler1, PropertyConditionHandler)
        self.assertEqual(FakeContact, handler1.model)
        self.assertIsNone(handler1.subfilter_id)
        self.assertIs(handler1.subfilter, False)
        self.assertEqual(ptype1.id, handler1._ptype_id)
        self.assertIs(handler1._exclude, False)

        # ---
        ptype2 = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_cute', text='Cute',
        )
        condition2 = PropertyConditionHandler.build_condition(
            model=FakeContact, ptype=ptype2, has=False,
            filter_type=EF_CREDENTIALS,
        )
        self.assertEqual(EF_CREDENTIALS, condition2.filter_type)
        self.assertEqual(ptype2.id,      condition2.name)
        self.assertIs(condition2.value, False)

        handler2 = PropertyConditionHandler.build(
            model=FakeContact,
            name=condition2.name,
            data=condition2.value,
        )
        self.assertEqual(ptype2.id, handler2._ptype_id)
        self.assertIs(handler2._exclude, True)

    def test_property_get_q(self):
        "get_q() not empty."
        user = self.create_user()

        create_ptype = CremePropertyType.objects.smart_update_or_create
        cute  = create_ptype(str_pk='test-prop_cute',  text='Cute')
        pilot = create_ptype(str_pk='test-prop_pilot', text='Pilot')

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
            model=FakeContact,
            ptype=cute.id,
        )
        self.assertQEqual(
            Q(pk__in=CremeProperty.objects
                                  .filter(id__in=[properties[0].id, properties[2].id])
                                  .values_list('creme_entity_id', flat=True)),
            handler1.get_q(user=user)
        )

        # Exclude ---
        handler2 = PropertyConditionHandler(
            model=FakeContact,
            ptype=cute.id,
            exclude=True,
        )
        self.assertQEqual(
            ~Q(pk__in=CremeProperty.objects
                                   .filter(id__in=[properties[0].id, properties[2].id])
                                   .values_list('creme_entity_id', flat=True)),
            handler2.get_q(user=user)
        )

    def test_property_accept(self):
        user = self.create_user()
        create_ptype = CremePropertyType.objects.smart_update_or_create
        cute = create_ptype(str_pk='test-prop_cute',  text='Cute')
        pilot = create_ptype(str_pk='test-prop_pilot', text='Pilot')

        create_contact = partial(FakeContact.objects.create, user=user)
        shinji = create_contact(last_name='Ikari',     first_name='Shinji')
        rei    = create_contact(last_name='Ayanami',   first_name='Rei')
        misato = create_contact(last_name='Katsuragi', first_name='Misato')

        create_prop = CremeProperty.objects.create
        create_prop(creme_entity=rei,    type=cute)
        create_prop(creme_entity=shinji, type=pilot)

        handler1 = PropertyConditionHandler(model=FakeContact, ptype=cute.id)
        self.assertIs(handler1.accept(entity=rei,    user=user), True)
        self.assertIs(handler1.accept(entity=shinji, user=user), False)
        self.assertIs(handler1.accept(entity=misato, user=user), False)

        # Exclude ---
        handler2 = PropertyConditionHandler(
            model=FakeContact,
            ptype=cute.id,
            exclude=True,
        )
        self.assertIs(handler2.accept(entity=rei,    user=user), False)
        self.assertIs(handler2.accept(entity=shinji, user=user), True)
        self.assertIs(handler2.accept(entity=misato, user=user), True)

    def test_property_description01(self):
        user = self.create_user()
        cute = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_cute', text='Cute',
        )
        handler = PropertyConditionHandler(
            model=FakeOrganisation,
            ptype=cute,
            exclude=False,
        )
        self.assertEqual(
            _('The entities have the property «{}»').format(cute.text),
            handler.description(user),
        )

    def test_property_description02(self):
        user = self.create_user()
        cute = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_kawaii', text='Kawaii',
        )
        handler = PropertyConditionHandler(
            model=FakeOrganisation,
            ptype=cute,
            exclude=True,
        )
        self.assertEqual(
            _('The entities have no property «{}»').format(cute.text),
            handler.description(user),
        )

    def test_property_description03(self):
        "Deleted CremePropertyType."
        user = self.create_user()
        handler = PropertyConditionHandler(
            model=FakeOrganisation,
            ptype='doesnotexist',
        )
        self.assertEqual('???', handler.description(user))

    def test_operand_currentuser(self):
        user = self.login()

        user2 = CremeUser.objects.create(**self.USERS_DATA[2])
        team = CremeUser.objects.create(username='NOIR', is_team=True)
        team.teammates = [user2]

        value = operands.CurrentUserOperand.type_id

        with self.assertNoException():
            handler = RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator=operators.EQUALS,
                field_name='user',
                values=[value],
            )

        self.assertQEqual(Q(user__exact=user.id), handler.get_q(user))
        other = self.other_user
        self.assertQEqual(Q(user__exact=other.id), handler.get_q(other))
        self.assertQEqual(Q(user__in=[user2.id, team.id]), handler.get_q(user2))

        self.assertEqual(
            _('«{field}» is {values}').format(
                field=_('Owner user'),
                values=_('«{enum_value}»').format(enum_value=_('Current user')),
            ),
            handler.description(user),
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
