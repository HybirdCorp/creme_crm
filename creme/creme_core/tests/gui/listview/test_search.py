# -*- coding: utf-8 -*-

from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.db.models import CharField, ForeignKey, IntegerField

from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellFunctionField,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.function_field import FunctionField
from creme.creme_core.forms import listview as lv_form
from creme.creme_core.gui.listview import search as lv_search
from creme.creme_core.models import (
    CremeUser,
    CustomField,
    FakeContact,
    FakeEmailCampaign,
    FakeInvoiceLine,
    FakeOrganisation,
    FakeSector,
    RelationType,
)
from creme.creme_core.tests.base import CremeTestCase


class ListViewSearchTestCase(CremeTestCase):
    class PhoneFunctionField(FunctionField):
        name = 'phone_or_mobile'
        verbose_name = 'Phone or mobile'

        def __call__(self, entity, user):
            return self.result_type(entity.phone or entity.mobile)

    class IsAdultFunctionField(FunctionField):
        name = 'is_adult'
        verbose_name = 'Is adult'

        def __call__(self, entity, user):
            # TODO: BOOL ?
            birthday = entity.birthday

            return self.result_type('?' if birthday is None else birthday.year > 2000)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = CremeUser(
            username='yui', email='kawa.yui@kimengumi.jp',
            first_name='Yui', last_name='Kawa',
        )

    def test_regularrelatedfield_registry01(self):
        "Register by related model."
        class MyUserFKField(lv_form.ListViewSearchField):
            pass

        registry = lv_search.RegularRelatedFieldSearchRegistry(
        ).register_related_model(model=CremeUser, sfield_builder=MyUserFKField)

        get_field = partial(registry.get_field, user=self.user)
        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        self.assertIsInstance(get_field(cell=build_cell(name='user')),    MyUserFKField)
        self.assertIsInstance(get_field(cell=build_cell(name='is_user')), MyUserFKField)

        sector_field = get_field(cell=build_cell(name='sector'))
        self.assertEqual(lv_form.RegularRelatedField, type(sector_field))

        builder = registry.builder_4_related_model
        self.assertIsNone(builder(FakeSector))
        self.assertEqual(MyUserFKField, builder(CremeUser))

    def test_regularrelatedfield_registry02(self):
        "Register default."
        class MyFKField(lv_form.ListViewSearchField):
            pass

        registry = lv_search.RegularRelatedFieldSearchRegistry(
        ).register_default(MyFKField)

        get_field = partial(registry.get_field, user=self.user)
        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        self.assertIsInstance(get_field(cell=build_cell(name='sector')), MyFKField)
        self.assertEqual(MyFKField, registry.default_builder)

    def test_regularrelatedfield_registry03(self):
        "ForeignKey to entity."
        registry = lv_search.RegularRelatedFieldSearchRegistry()
        cell = EntityCellRegularField.build(
            model=FakeInvoiceLine, name='linked_invoice',
        )
        self.assertIsInstance(
            registry.get_field(cell=cell, user=self.user),
            lv_form.EntityRelatedField,
        )

    def test_regularrelatedfield_registry04(self):
        "register_related_model(): register a sub-registry."
        user1 = self.user
        user2 = CremeUser(
            username='chie', email='uru.chie@kimengumi.jp',
            first_name='Chie', last_name='Uru',
        )

        class MyUserField1(lv_form.ListViewSearchField):
            pass

        class MyUserField2(lv_form.ListViewSearchField):
            pass

        class MyUserRegistry(lv_search.AbstractListViewSearchFieldRegistry):
            def get_field(self, *, cell, user, **kwarg):
                cls = MyUserField1 if user.username == user1.username else MyUserField2

                return cls(cell=cell, user=user)

        registry = lv_search.RegularRelatedFieldSearchRegistry(
        ).register_related_model(model=CremeUser, sfield_builder=MyUserRegistry)

        cell = EntityCellRegularField.build(model=FakeContact, name='user')
        get_field = registry.get_field
        self.assertIsInstance(get_field(cell=cell, user=user1), MyUserField1)
        self.assertIsInstance(get_field(cell=cell, user=user2), MyUserField2)

    def test_regularrelatedfield_registry05(self):
        "register_default(): register a sub-registry."
        user1 = self.user
        user2 = CremeUser(
            username='chie', email='uru.chie@kimengumi.jp',
            first_name='Chie', last_name='Uru',
        )

        class MyFKField1(lv_form.ListViewSearchField):
            pass

        class MyFKField2(lv_form.ListViewSearchField):
            pass

        class MyRegistry(lv_search.AbstractListViewSearchFieldRegistry):
            def get_field(self, *, cell, user, **kwarg):
                cls = MyFKField1 if user.username == user1.username else MyFKField2

                return cls(cell=cell, user=user)

        registry = lv_search.RegularRelatedFieldSearchRegistry(
        ).register_default(MyRegistry)

        cell = EntityCellRegularField.build(model=FakeContact, name='user')
        get_field = registry.get_field
        self.assertIsInstance(get_field(cell=cell, user=user1), MyFKField1)
        self.assertIsInstance(get_field(cell=cell, user=user2), MyFKField2)

    def test_regularrelatedfield_registry06(self):
        "Default is a sub-registry."
        user1 = self.user
        user2 = CremeUser(
            username='chie', email='uru.chie@kimengumi.jp',
            first_name='Chie', last_name='Uru',
        )

        class MyFKField1(lv_form.ListViewSearchField):
            pass

        class MyFKField2(lv_form.ListViewSearchField):
            pass

        class MyRegistry(lv_search.AbstractListViewSearchFieldRegistry):
            def get_field(self, *, cell, user, **kwarg):
                cls = MyFKField1 if user.username == user1.username else MyFKField2

                return cls(cell=cell, user=user)

        registry = lv_search.RegularRelatedFieldSearchRegistry(default=MyRegistry)

        cell = EntityCellRegularField.build(model=FakeContact, name='user')
        get_field = registry.get_field
        self.assertIsInstance(get_field(cell=cell, user=user1), MyFKField1)
        self.assertIsInstance(get_field(cell=cell, user=user2), MyFKField2)

    def test_regularfield_registry01(self):
        "Register by type."
        user = self.user
        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        str_cell = build_cell(name='name')

        registry = lv_search.RegularFieldSearchRegistry(to_register=())
        str_field = registry.get_field(cell=str_cell, user=user)
        self.assertIsInstance(str_field, lv_form.ListViewSearchField)
        self.assertEqual(str_cell, str_field.cell)
        self.assertEqual(user,     str_field.user)

        self.assertIsNone(registry.builder_4_model_field_type(CharField))
        self.assertIsNone(
            registry.builder_4_model_field(model=FakeOrganisation, field_name='name')
        )

        # ---
        class MyField(lv_form.RegularCharField):
            pass

        registry.register_model_field_type(type=CharField, sfield_builder=MyField)
        str_field = registry.get_field(cell=str_cell, user=self.user)
        self.assertIsInstance(str_field, MyField)
        self.assertEqual(MyField, registry.builder_4_model_field_type(CharField))
        self.assertIsNone(
            registry.builder_4_model_field(model=FakeOrganisation, field_name='name')
        )

        int_cell = build_cell(name='capital')
        int_field = registry.get_field(cell=int_cell, user=self.user)
        self.assertIsInstance(int_field, lv_form.ListViewSearchField)
        self.assertNotIsInstance(int_field, MyField)
        self.assertIsNone(registry.builder_4_model_field_type(IntegerField))

    def test_regularfield_registry02(self):
        "Register by type => inheritance."
        class MyField(lv_form.RegularCharField):
            pass

        # NB: "capital" is a PositiveIntegerField (inheriting IntegerField)
        int_cell = EntityCellRegularField.build(model=FakeOrganisation, name='capital')
        registry = lv_search.RegularFieldSearchRegistry(to_register=())
        registry.register_model_field_type(type=IntegerField, sfield_builder=MyField)

        int_field = registry.get_field(cell=int_cell, user=self.user)
        self.assertIsInstance(int_field, MyField)

    def test_regularfield_registry03(self):
        "Register by field."
        class LVField(lv_form.RegularCharField):
            pass

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        fname_cell = build_cell(name='first_name')
        lname_cell = build_cell(name='last_name')

        registry = lv_search.RegularFieldSearchRegistry(to_register=())

        registry.register_model_field(
            model=FakeContact, field_name='first_name', sfield_builder=LVField,
        )
        fname_field = registry.get_field(cell=fname_cell, user=self.user)
        self.assertIsInstance(fname_field, LVField)
        self.assertEqual(
            LVField,
            registry.builder_4_model_field(model=FakeContact, field_name='first_name'),
        )

        lname_field = registry.get_field(cell=lname_cell, user=self.user)
        self.assertIsInstance(lname_field, lv_form.ListViewSearchField)
        self.assertNotIsInstance(lname_field, LVField)

    def test_regularfield_registry04(self):
        "Choices."
        class MyCharField(lv_form.RegularCharField):
            pass

        class MyChoiceField(lv_form.RegularChoiceField):
            pass

        build_cell = partial(EntityCellRegularField.build, model=FakeInvoiceLine)

        registry = lv_search.RegularFieldSearchRegistry(
            to_register=[(CharField, MyCharField)],
            choice_sfield_builder=MyChoiceField,
        )

        user = self.user
        item_field = registry.get_field(cell=build_cell(name='item'), user=user)
        self.assertIsInstance(item_field, MyCharField)

        unit_field = registry.get_field(cell=build_cell(name='discount_unit'), user=user)
        self.assertIsInstance(unit_field, MyChoiceField)

    def test_regularfield_registry05(self):
        "Choices field + field registered specifically."
        class MyChoiceField(lv_form.RegularChoiceField):
            pass

        class MyUnitField(lv_form.RegularChoiceField):
            pass

        registry = lv_search.RegularFieldSearchRegistry(
            choice_sfield_builder=MyChoiceField,
        )
        registry.register_model_field(
            model=FakeInvoiceLine, field_name='discount_unit', sfield_builder=MyUnitField,
        )

        unit_cell = EntityCellRegularField.build(model=FakeInvoiceLine, name='discount_unit')
        unit_field = registry.get_field(cell=unit_cell, user=self.user)
        self.assertIsInstance(unit_field, MyUnitField)

    def test_regularfield_registry06(self):
        "register_model_field():  sub-registry."
        user1 = self.user
        user2 = CremeUser(
            username='chie', email='uru.chie@kimengumi.jp',
            first_name='Chie', last_name='Uru',
        )

        class MyField1(lv_form.ListViewSearchField):
            pass

        class MyField2(lv_form.ListViewSearchField):
            pass

        class MyRegistry(lv_search.AbstractListViewSearchFieldRegistry):
            def get_field(self, *, cell, user, **kwarg):
                cls = MyField1 if user.username == user1.username else MyField2

                return cls(cell=cell, user=user)

        registry = lv_search.RegularFieldSearchRegistry().register_model_field(
            model=FakeContact,
            field_name='first_name',
            sfield_builder=MyRegistry
        )

        cell = EntityCellRegularField.build(model=FakeContact, name='first_name')
        get_field = registry.get_field
        self.assertIsInstance(get_field(cell=cell, user=user1), MyField1)
        self.assertIsInstance(get_field(cell=cell, user=user2), MyField2)

    def test_regularfield_registry07(self):
        "Choices + sub-registry."
        user1 = self.user
        user2 = CremeUser(
            username='chie', email='uru.chie@kimengumi.jp',
            first_name='Chie', last_name='Uru',
        )

        class MyChoiceField1(lv_form.ListViewSearchField):
            pass

        class MyChoiceField2(lv_form.ListViewSearchField):
            pass

        class MyChoiceRegistry(lv_search.AbstractListViewSearchFieldRegistry):
            def get_field(self, *, cell, user, **kwarg):
                cls = MyChoiceField1 if user.username == user1.username else MyChoiceField2

                return cls(cell=cell, user=user)

        registry = lv_search.RegularFieldSearchRegistry().register_choice_builder(MyChoiceRegistry)

        cell = EntityCellRegularField.build(model=FakeInvoiceLine, name='discount_unit')

        get_field = registry.get_field
        self.assertIsInstance(get_field(cell=cell, user=user1), MyChoiceField1)
        self.assertIsInstance(get_field(cell=cell, user=user2), MyChoiceField2)

        self.assertIsInstance(registry.choice_builder, MyChoiceRegistry)

    def test_regularfield_registry_default01(self):
        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        get_field = partial(
            lv_search.RegularFieldSearchRegistry().get_field, user=self.user,
        )
        self.assertIsInstance(
            get_field(cell=build_cell(name='first_name')),
            lv_form.RegularCharField,
        )
        self.assertIsInstance(
            get_field(cell=build_cell(name='is_a_nerd')),
            lv_form.RegularBooleanField,
        )
        self.assertIsInstance(
            get_field(cell=build_cell(name='birthday')),
            lv_form.RegularDateField,
        )
        self.assertIsInstance(
            get_field(cell=build_cell(model=FakeOrganisation, name='capital')),
            lv_form.RegularPositiveIntegerField,
        )
        self.assertIsInstance(
            get_field(cell=build_cell(model=FakeInvoiceLine, name='discount')),
            lv_form.RegularDecimalField,
        )

        # Sub field
        self.assertIsInstance(
            get_field(cell=build_cell(name='position__title')),
            lv_form.RegularCharField,
        )

        # ForeignKey
        self.assertIsInstance(
            get_field(cell=build_cell(name='position')),
            lv_form.RegularRelatedField,
        )

        # ManyToMany
        self.assertIsInstance(
            get_field(cell=build_cell(name='languages')),
            lv_form.RegularRelatedField,
        )

    def test_regularfield_registry_default02(self):
        "Choices."
        build_cell = partial(EntityCellRegularField.build, model=FakeInvoiceLine)
        get_field = partial(
            lv_search.RegularFieldSearchRegistry().get_field, user=self.user,
        )
        self.assertIsInstance(
            get_field(cell=build_cell(name='item')),
            lv_form.RegularCharField,
        )
        self.assertIsInstance(
            get_field(cell=build_cell(name='discount_unit')),
            lv_form.RegularChoiceField,
        )

    def test_regularfield_registry_default03(self):
        "ForeignKey to entity."
        cell = EntityCellRegularField.build(model=FakeInvoiceLine, name='linked_invoice')
        self.assertIsInstance(
            lv_search.RegularFieldSearchRegistry().get_field(user=self.user, cell=cell),
            lv_form.EntityRelatedField,
        )

    def test_regularfield_registry_default04(self):
        "ManyToManyField to entity."
        cell = EntityCellRegularField.build(model=FakeEmailCampaign, name='mailing_lists')
        self.assertIsInstance(
            lv_search.RegularFieldSearchRegistry().get_field(user=self.user, cell=cell),
            lv_form.EntityRelatedField,
        )

    def test_customfield_registry01(self):
        create_cfield = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeContact),
        )
        str_cfield = create_cfield(name='A', field_type=CustomField.STR)
        int_cfield = create_cfield(name='B', field_type=CustomField.INT)

        str_cell = EntityCellCustomField(customfield=str_cfield)
        int_cell = EntityCellCustomField(customfield=int_cfield)

        registry = lv_search.CustomFieldSearchRegistry(to_register=())
        field = registry.get_field(cell=str_cell, user=self.user)
        self.assertIsInstance(field, lv_form.ListViewSearchField)
        # self.assertFalse(field.widget.type)

        builder = registry.builder
        self.assertIsNone(builder(CustomField.STR))

        # ---
        class MyCustomField(lv_form.CustomCharField):
            pass

        registry.register(type=CustomField.STR, sfield_builder=MyCustomField)
        str_field = registry.get_field(cell=str_cell, user=self.user)
        self.assertIsInstance(str_field, MyCustomField)

        int_field = registry.get_field(cell=int_cell, user=self.user)
        self.assertIsInstance(int_field, lv_form.ListViewSearchField)

        self.assertEqual(MyCustomField, builder(CustomField.STR))
        self.assertIsNone(builder(CustomField.INT))

    def test_customfield_registry02(self):
        "Default data."
        user = self.user
        create_cfield = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeContact),
        )
        str_cfield   = create_cfield(name='A', field_type=CustomField.STR)
        int_cfield   = create_cfield(name='B', field_type=CustomField.INT)
        bool_cfield  = create_cfield(name='C', field_type=CustomField.BOOL)
        deci_cfield  = create_cfield(name='D', field_type=CustomField.FLOAT)
        dt_cfield    = create_cfield(name='E', field_type=CustomField.DATETIME)
        enum_cfield  = create_cfield(name='F', field_type=CustomField.ENUM)
        menum_cfield = create_cfield(name='G', field_type=CustomField.MULTI_ENUM)

        registry = lv_search.CustomFieldSearchRegistry()

        str_field = registry.get_field(
            cell=EntityCellCustomField(customfield=str_cfield),
            user=user,
        )
        self.assertIsInstance(str_field, lv_form.CustomCharField)

        int_field = registry.get_field(
            cell=EntityCellCustomField(customfield=int_cfield),
            user=user,
        )
        self.assertIsInstance(int_field, lv_form.CustomIntegerField)

        bool_field = registry.get_field(
            cell=EntityCellCustomField(customfield=bool_cfield),
            user=user,
        )
        self.assertIsInstance(bool_field, lv_form.CustomBooleanField)

        deci_field = registry.get_field(
            cell=EntityCellCustomField(customfield=deci_cfield),
            user=user,
        )
        self.assertIsInstance(deci_field, lv_form.CustomDecimalField)

        dt_field = registry.get_field(
            cell=EntityCellCustomField(customfield=dt_cfield),
            user=user,
        )
        self.assertIsInstance(dt_field, lv_form.CustomDatetimeField)

        enum_field = registry.get_field(
            cell=EntityCellCustomField(customfield=enum_cfield),
            user=user,
        )
        self.assertIsInstance(enum_field, lv_form.CustomChoiceField)

        menum_field = registry.get_field(
            cell=EntityCellCustomField(customfield=menum_cfield),
            user=user,
        )
        self.assertIsInstance(menum_field, lv_form.CustomChoiceField)

    def test_customfield_registry03(self):
        "Sub-registry."
        user1 = self.user
        user2 = CremeUser(
            username='chie', email='uru.chie@kimengumi.jp',
            first_name='Chie', last_name='Uru',
        )

        class MyCustomField1(lv_form.ListViewSearchField):
            pass

        class MyCustomField2(lv_form.ListViewSearchField):
            pass

        class MyCustomRegistry(lv_search.AbstractListViewSearchFieldRegistry):
            def get_field(self, *, cell, user, **kwarg):
                cls = MyCustomField1 if user.username == user1.username else MyCustomField2

                return cls(cell=cell, user=user)

        cfield = CustomField.objects.create(
            content_type=FakeContact,
            name='A', field_type=CustomField.STR,
        )

        cell = EntityCellCustomField(customfield=cfield)

        registry = lv_search.CustomFieldSearchRegistry().register(
            type=CustomField.STR, sfield_builder=MyCustomRegistry,
        )

        get_field = registry.get_field
        self.assertIsInstance(get_field(cell=cell, user=user1), MyCustomField1)
        self.assertIsInstance(get_field(cell=cell, user=user2), MyCustomField2)

    def test_functionfield_registry01(self):
        "Default data."
        registry = lv_search.FunctionFieldSearchRegistry()

        funfield1 = self.PhoneFunctionField()
        cell1 = EntityCellFunctionField(model=FakeContact, func_field=funfield1)

        field = registry.get_field(cell=cell1, user=self.user)
        self.assertIsInstance(field, lv_form.ListViewSearchField)
        self.assertIsNone(registry.builder(funfield1))

        # ---
        class MyField(lv_form.ListViewSearchField):
            pass

        funfield2 = self.IsAdultFunctionField()
        cell2 = EntityCellFunctionField(model=FakeContact, func_field=funfield2)

        registry.register(ffield=funfield2, sfield_builder=MyField)
        self.assertIsInstance(registry.get_field(cell=cell2, user=self.user), MyField)

        field1 = registry.get_field(cell=cell1, user=self.user)
        self.assertIsInstance(field1, lv_form.ListViewSearchField)
        self.assertNotIsInstance(field1, MyField)

        self.assertIsNone(registry.builder(funfield1))
        self.assertEqual(MyField, registry.builder(funfield2))

    def test_functionfield_registry02(self):
        "Register in constructor."
        class MyField(lv_form.ListViewSearchField):
            pass

        registry = lv_search.FunctionFieldSearchRegistry(
            to_register=[(self.PhoneFunctionField, MyField)],
        )

        cell = EntityCellFunctionField(
            model=FakeContact, func_field=self.PhoneFunctionField(),
        )
        self.assertIsInstance(registry.get_field(cell=cell, user=self.user), MyField)

    def test_functionfield_registry03(self):
        "Function field with default search-field."
        registry = lv_search.FunctionFieldSearchRegistry()

        class MySearchField1(lv_form.ListViewSearchField):
            pass

        class SearchablePhoneFunctionField(self.PhoneFunctionField):
            search_field_builder = MySearchField1

        funfield = SearchablePhoneFunctionField()
        cell = EntityCellFunctionField(model=FakeContact, func_field=funfield)
        self.assertIsInstance(
            registry.get_field(cell=cell, user=self.user),
            MySearchField1
        )

        # ---
        class MySearchField2(lv_form.ListViewSearchField):
            pass

        registry.register(ffield=funfield, sfield_builder=MySearchField2)
        self.assertIsInstance(
            registry.get_field(cell=cell, user=self.user),
            MySearchField2,
        )

    def test_functionfield_registry04(self):
        "Register sub-registry."
        user1 = self.user
        user2 = CremeUser(
            username='chie', email='uru.chie@kimengumi.jp',
            first_name='Chie', last_name='Uru',
        )

        class MyFunField1(lv_form.ListViewSearchField):
            pass

        class MyFunField2(lv_form.ListViewSearchField):
            pass

        class MyFunRegistry(lv_search.AbstractListViewSearchFieldRegistry):
            def get_field(self, *, cell, user, **kwarg):
                cls = MyFunField1 if user.username == user1.username else MyFunField2

                return cls(cell=cell, user=user)

        funfield = self.PhoneFunctionField()
        cell = EntityCellFunctionField(model=FakeContact, func_field=funfield)

        registry = lv_search.FunctionFieldSearchRegistry()\
                            .register(ffield=funfield, sfield_builder=MyFunRegistry)
        get_field = registry.get_field
        self.assertIsInstance(get_field(cell=cell, user=user1), MyFunField1)
        self.assertIsInstance(get_field(cell=cell, user=user2), MyFunField2)

    def test_functionfield_registry05(self):
        "Sub-registry defined in FunctionField attribute."
        user1 = self.user
        user2 = CremeUser(
            username='chie', email='uru.chie@kimengumi.jp',
            first_name='Chie', last_name='Uru',
        )

        class MyFunField1(lv_form.ListViewSearchField):
            pass

        class MyFunField2(lv_form.ListViewSearchField):
            pass

        class MyFunRegistry(lv_search.AbstractListViewSearchFieldRegistry):
            def get_field(self, *, cell, user, **kwarg):
                cls = MyFunField1 if user.username == user1.username else MyFunField2

                return cls(cell=cell, user=user)

        class SearchablePhoneFunctionField(self.PhoneFunctionField):
            search_field_builder = MyFunRegistry

        funfield = SearchablePhoneFunctionField()
        cell = EntityCellFunctionField(model=FakeContact, func_field=funfield)

        registry = lv_search.FunctionFieldSearchRegistry()
        get_field = registry.get_field
        self.assertIsInstance(get_field(cell=cell, user=user1), MyFunField1)
        self.assertIsInstance(get_field(cell=cell, user=user2), MyFunField2)

    def test_relationtype_registry01(self):
        "Default data + register() method."
        registry = lv_search.RelationSearchRegistry()

        cell1 = EntityCellRelation.build(model=FakeContact, rtype_id=REL_SUB_HAS)

        field = registry.get_field(cell=cell1, user=self.user)
        self.assertIsInstance(field, lv_form.RelationField)
        self.assertIsNone(registry.builder(REL_SUB_HAS))
        self.assertEqual(lv_form.RelationField, registry.default_builder)

        # ---
        class MyRelationField(lv_form.ListViewSearchField):
            pass

        rtype2 = RelationType.objects.smart_update_or_create(
            ('test-subject_loves', 'loves'),
            ('test-object_loved',  'is loved by'),
        )[0]
        cell2 = EntityCellRelation(model=FakeContact, rtype=rtype2)

        registry.register(rtype_id=rtype2.id, sfield_builder=MyRelationField)
        self.assertIsInstance(
            registry.get_field(cell=cell2, user=self.user), MyRelationField,
        )
        self.assertIsInstance(
            registry.get_field(cell=cell1, user=self.user), lv_form.RelationField,
        )

        self.assertIsNone(registry.builder(REL_SUB_HAS))
        self.assertEqual(MyRelationField, registry.builder(rtype2.id))

    def test_relationtype_registry02(self):
        "Register in constructor."
        class MyRelationField(lv_form.ListViewSearchField):
            pass

        registry = lv_search.RelationSearchRegistry(to_register=[
            (REL_SUB_HAS, MyRelationField),
        ])

        cell = EntityCellRelation.build(model=FakeContact, rtype_id=REL_SUB_HAS)
        self.assertIsInstance(registry.get_field(cell=cell, user=self.user), MyRelationField)

    def test_relationtype_registry03(self):
        "Set default."
        class MyRelationField(lv_form.ListViewSearchField):
            pass

        registry = lv_search.RelationSearchRegistry(default=MyRelationField)
        self.assertEqual(MyRelationField, registry.default_builder)

        cell = EntityCellRelation.build(model=FakeContact, rtype_id=REL_SUB_HAS)
        self.assertIsInstance(registry.get_field(cell=cell, user=self.user), MyRelationField)

    def test_relationtype_registry04(self):
        "Register sub-registry."
        user1 = self.user
        user2 = CremeUser(
            username='chie', email='uru.chie@kimengumi.jp',
            first_name='Chie', last_name='Uru',
        )

        class MyRelationField1(lv_form.ListViewSearchField):
            pass

        class MyRelationField2(lv_form.ListViewSearchField):
            pass

        class MyRelRegistry(lv_search.AbstractListViewSearchFieldRegistry):
            def get_field(self, *, cell, user, **kwarg):
                cls = (
                    MyRelationField1
                    if user.username == user1.username else
                    MyRelationField2
                )

                return cls(cell=cell, user=user)

        registry = lv_search.RelationSearchRegistry(to_register=[
            (REL_SUB_HAS, MyRelRegistry),
        ])

        cell = EntityCellRelation.build(model=FakeContact, rtype_id=REL_SUB_HAS)
        get_field = registry.get_field
        self.assertIsInstance(get_field(cell=cell, user=user1), MyRelationField1)
        self.assertIsInstance(get_field(cell=cell, user=user2), MyRelationField2)

    def test_relationtype_registry05(self):
        "Default is a sub-registry."
        user1 = self.user
        user2 = CremeUser(
            username='chie', email='uru.chie@kimengumi.jp',
            first_name='Chie', last_name='Uru',
        )

        class MyRelationField1(lv_form.ListViewSearchField):
            pass

        class MyRelationField2(lv_form.ListViewSearchField):
            pass

        class MyRelRegistry(lv_search.AbstractListViewSearchFieldRegistry):
            def get_field(self, *, cell, user, **kwarg):
                cls = (
                    MyRelationField1
                    if user.username == user1.username else
                    MyRelationField2
                )

                return cls(cell=cell, user=user)

        registry = lv_search.RelationSearchRegistry(default=MyRelRegistry)

        cell = EntityCellRelation.build(model=FakeContact, rtype_id=REL_SUB_HAS)
        get_field = registry.get_field
        self.assertIsInstance(get_field(cell=cell, user=user1), MyRelationField1)
        self.assertIsInstance(get_field(cell=cell, user=user2), MyRelationField2)

    def test_relationtype_registry06(self):
        "Register a default sub-registry."
        user1 = self.user
        user2 = CremeUser(
            username='chie', email='uru.chie@kimengumi.jp',
            first_name='Chie', last_name='Uru',
        )

        class MyRelationField1(lv_form.ListViewSearchField):
            pass

        class MyRelationField2(lv_form.ListViewSearchField):
            pass

        class MyRelRegistry(lv_search.AbstractListViewSearchFieldRegistry):
            def get_field(self, *, cell, user, **kwarg):
                cls = (
                    MyRelationField1
                    if user.username == user1.username else
                    MyRelationField2
                )

                return cls(cell=cell, user=user)

        registry = lv_search.RelationSearchRegistry().register_default(MyRelRegistry)

        cell = EntityCellRelation.build(model=FakeContact, rtype_id=REL_SUB_HAS)
        get_field = registry.get_field
        self.assertIsInstance(get_field(cell=cell, user=user1), MyRelationField1)
        self.assertIsInstance(get_field(cell=cell, user=user2), MyRelationField2)

    def test_cell_registry_regularfield(self):
        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        get_field = lv_search.ListViewSearchFieldRegistry().get_field
        user = self.user
        self.assertIsInstance(
            get_field(cell=build_cell(name='first_name'), user=user),
            lv_form.RegularCharField,
        )
        self.assertIsInstance(
            get_field(cell=build_cell(name='is_a_nerd'), user=user),
            lv_form.RegularBooleanField,
        )
        self.assertIsInstance(
            get_field(cell=build_cell(name='birthday'), user=user),
            lv_form.RegularDateField,
        )
        self.assertIsInstance(
            get_field(cell=build_cell(name='address'), user=user),
            lv_form.RegularRelatedField,
        )

    def test_cell_registry_customfield(self):
        cfield = CustomField.objects.create(
            name='A', field_type=CustomField.STR,
            content_type=FakeContact,
        )

        cell = EntityCellCustomField(customfield=cfield)
        registry = lv_search.ListViewSearchFieldRegistry()

        field = registry.get_field(cell=cell, user=self.user)
        self.assertIsInstance(field, lv_form.CustomCharField)

    def test_cell_registry_functionfield01(self):
        funfield = self.PhoneFunctionField()
        cell = EntityCellFunctionField(model=FakeContact, func_field=funfield)
        registry = lv_search.ListViewSearchFieldRegistry(to_register=())

        field = registry.get_field(cell=cell, user=self.user)
        self.assertIsInstance(field, lv_form.ListViewSearchField)

        with self.assertRaises(KeyError):
            registry[EntityCellFunctionField.type_id]  # NOQA

    def test_cell_registry_functionfield02(self):
        "Default data."
        funfield = self.PhoneFunctionField()
        cell = EntityCellFunctionField(model=FakeContact, func_field=funfield)
        registry = lv_search.ListViewSearchFieldRegistry()

        field = registry.get_field(cell=cell, user=self.user)
        self.assertEqual(lv_form.ListViewSearchField, type(field))

    def test_cell_registry_relation01(self):
        cell = EntityCellRelation.build(model=FakeContact, rtype_id=REL_SUB_HAS)
        registry = lv_search.ListViewSearchFieldRegistry(to_register=())

        field = registry.get_field(cell=cell, user=self.user)
        self.assertIsInstance(field, lv_form.ListViewSearchField)

        class MyField(lv_form.RelationField):
            pass

        class Registry:
            def get_field(this, *, cell, user):
                return MyField(cell=cell, user=user)

        registry.register(cell_id=EntityCellRelation.type_id, registry_class=Registry)
        field = registry.get_field(cell=cell, user=self.user)
        self.assertIsInstance(field, MyField)

    def test_cell_registry_relation02(self):
        "Default data."
        registry = lv_search.ListViewSearchFieldRegistry()
        cell = EntityCellRelation.build(model=FakeContact, rtype_id=REL_SUB_HAS)

        field = registry.get_field(cell=cell, user=self.user)
        self.assertIsInstance(field, lv_form.RelationField)

    def test_cell_registry_get_item(self):
        class MyField(lv_form.ListViewSearchField):
            pass

        funfield = self.PhoneFunctionField()
        cell = EntityCellFunctionField(model=FakeContact, func_field=funfield)
        registry = lv_search.ListViewSearchFieldRegistry()

        registry[EntityCellFunctionField.type_id].register(
            ffield=funfield, sfield_builder=MyField,
        )
        self.assertIsInstance(registry.get_field(cell=cell, user=self.user), MyField)

        with self.assertNoException():
            registry[EntityCellRegularField.type_id].builder_4_model_field_type(ForeignKey)

    def test_cell_registry_pretty(self):
        registry = lv_search.ListViewSearchFieldRegistry()

        # NB: just test it don't crash. We could do better...
        with self.assertNoException():
            registry.pretty()
