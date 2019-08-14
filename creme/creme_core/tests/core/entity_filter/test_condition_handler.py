# -*- coding: utf-8 -*-

try:
    from datetime import date
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    from django.db.models.query_utils import Q
    from django.utils.timezone import now
    # from django.utils.translation import gettext as _

    from creme.creme_core.core.entity_filter import operators
    from creme.creme_core.core.entity_filter.condition_handler import (
        FilterConditionHandler,
        RegularFieldConditionHandler, DateRegularFieldConditionHandler,
        CustomFieldConditionHandler, DateCustomFieldConditionHandler,
        PropertyConditionHandler, RelationConditionHandler,
        SubFilterConditionHandler, RelationSubFilterConditionHandler,
    )
    from creme.creme_core.models import (
        RelationType, Relation, CremeProperty, CremePropertyType, CustomField,
        EntityFilter, EntityFilterCondition,
        FakeContact, FakeOrganisation, FakeFolder, FakeDocument,
    )
    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.utils.date_range import date_range_registry
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


# TODO: query_for_related_conditions()
# TODO: query_for_parent_conditions()
class FilterConditionHandlerTestCase(CremeTestCase):
    def test_regularfield_init(self):
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

        self.assertQEqual(
            Q(name__icontains=value),
            handler.get_q(user=None)
        )
        # TODO: test other operators

    def test_regularfield_error(self):
        "<error> property."
        handler1 = RegularFieldConditionHandler(
            model=FakeOrganisation,
            field_name='invalid',
            operator_id=operators.ICONTAINS,
            values=['Corp'],
        )
        self.assertEqual("FakeOrganisation has no field named 'invalid'",
                         handler1.error
                        )

        # ---
        handler2 = RegularFieldConditionHandler(
            model=FakeOrganisation,
            field_name='name',
            operator_id=1234,  # <=
            values=['Corp'],
        )
        self.assertEqual("Operator ID '1234' is invalid",
                         handler2.error
                        )

    def test_regularfield_build01(self):
        fname = 'name'
        operator_id = operators.ICONTAINS
        value = 'Corp'
        handler = RegularFieldConditionHandler.build(
            model=FakeOrganisation,
            name=fname,
            data={'operator': operator_id, 'values': [value]}
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

    def test_regularfield_condition01(self):
        "Build condition."
        self.assertEqual(5, RegularFieldConditionHandler.type_id)

        fname = 'last_name'
        operator_id =  operators.EQUALS
        value = 'Ikari'
        condition = RegularFieldConditionHandler.build_condition(
            model=FakeContact,
            operator_id=operators.EQUALS,
            field_name=fname, values=[value],
        )
        self.assertIsInstance(condition, EntityFilterCondition)
        self.assertIsNone(condition.pk)
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(fname, condition.name)
        self.assertDictEqual({'operator': operator_id, 'values': [value]},
                             condition.decoded_value
                            )

        handler = RegularFieldConditionHandler.build(
            model=FakeContact,
            name=condition.name,
            data=condition.decoded_value,
        )
        self.assertIsInstance(handler, RegularFieldConditionHandler)
        self.assertEqual(FakeContact, handler.model)
        self.assertIsNone(handler.subfilter_id)
        self.assertIs(handler.subfilter, False)
        self.assertEqual(fname,       handler._field_name)
        self.assertEqual(operator_id, handler._operator_id)
        self.assertEqual([value],     handler._values)

    def test_regularfield_condition02(self):
        "Build condition + errors."
        # ValueError = EntityFilterCondition.ValueError
        ValueError = FilterConditionHandler.ValueError
        # build_4_field = EntityFilterCondition.build_4_field
        build_4_field = RegularFieldConditionHandler.build_condition

        self.assertRaises(
            ValueError, build_4_field,
            # model=FakeContact, operator=EntityFilterCondition.CONTAINS, name='unknown_field', values=['Misato'],
            model=FakeContact, field_name='unknown_field',
            operator_id=operators.CONTAINS, values=['Misato'],
        )
        self.assertRaises(
            ValueError, build_4_field,
            # model=FakeOrganisation, operator=EntityFilterCondition.GT, name='capital', values=['Not an integer']
            model=FakeOrganisation, field_name='capital',
            operator_id=operators.GT, values=['Not an integer'],
        )
        self.assertRaises(
            ValueError, build_4_field,
            # NB: ISEMPTY => boolean
            # model=FakeContact, operator=EntityFilterCondition.ISEMPTY, name='description', values=['Not a boolean'],
            model=FakeContact, field_name='description',
            operator_id=operators.ISEMPTY, values=['Not a boolean'],
        )
        self.assertRaises(
            ValueError, build_4_field,
            # NB: only one boolean is expected
            # model=FakeContact, operator=EntityFilterCondition.ISEMPTY, name='description', values=[True, True],
            model=FakeContact, field_name='description',
            operator_id=operators.ISEMPTY, values=[True, True],
        )
        self.assertRaises(
            ValueError, build_4_field,
            # model=FakeContact, operator=EntityFilterCondition.STARTSWITH, name='civility__unknown', values=['Mist']
            model=FakeContact, field_name='civility__unknown',
            operator_id=operators.STARTSWITH, values=['Mist'],
        )
        self.assertRaises(
            ValueError, build_4_field,
            model=FakeOrganisation, field_name='capital',
            operator_id=operators.RANGE, values=[5000],
        )
        self.assertRaises(
            ValueError, build_4_field,
            # model=FakeOrganisation, operator=EntityFilterCondition.RANGE, name='capital', values=[5000, 50000, 100000]
            model=FakeOrganisation, field_name='capital',
            operator_id=operators.RANGE, values=[5000, 50000, 100000],
        )
        self.assertRaises(
            ValueError, build_4_field,
            # model=FakeOrganisation, operator=EntityFilterCondition.RANGE, name='capital', values=['not an integer', 500000]
            model=FakeOrganisation, field_name='capital',
            operator_id=operators.RANGE, values=['not an integer', 500000],
        )
        self.assertRaises(
            ValueError, build_4_field,
            # model=FakeOrganisation, operator=EntityFilterCondition.RANGE, name='capital', values=[500000, 'not an integer']
            model=FakeOrganisation, field_name='capital',
            operator_id=operators.RANGE, values=[500000, 'not an integer'],
        )

    def test_regularfield_condition03(self):
        "Email + sub-part validation."
        build = partial(RegularFieldConditionHandler.build_condition,
                        model=FakeOrganisation, field_name='email',
                        )

        # Problem a part of a email address is not a valid email address
        with self.assertRaises(FilterConditionHandler.ValueError) as cm:
            build(operator_id=operators.EQUALS, values=['misato'])
        # self.assertEqual(_('Enter a valid email address.'), cm.exception.args[0])  TODO: ?
        self.assertEqual("['Enter a valid email address.']", cm.exception.args[0])

        # ---
        with self.assertNoException():
            build(operator_id=operators.ISTARTSWITH, values=['misato'])

        with self.assertNoException():
            build(operator_id=operators.RANGE, values=['misato', 'yui'])

        with self.assertNoException():
            build(operator_id=operators.EQUALS, values=['misato@nerv.jp'])

    def test_regularfield_condition04(self):
        "Credentials for entity FK."
        user = self.login()
        other_user = self.other_user

        create_folder = FakeFolder.objects.create
        folder       = create_folder(title='Folder 01', user=user)
        other_folder = create_folder(title='Folder 02', user=other_user)

        # build_4_field = partial(EntityFilterCondition.build_4_field,
        build_4_field = partial(RegularFieldConditionHandler.build_condition,
                                model=FakeDocument,
                                # operator=EntityFilterCondition.EQUALS,
                                operator_id=operators.EQUALS,
                                # name='linked_folder',
                                field_name='linked_folder',
                                )

        # user can link Document on "Folder 01" (owner=user)
        self.assertNoException(lambda: build_4_field(values=[str(folder.id)], user=user))
        # user can link Document on "Folder 02" (owner=other_user)
        self.assertNoException(lambda: build_4_field(values=[str(other_folder.id)], user=user))

        # other_user cannot link (not authenticated)
        # with self.assertRaises(EntityFilterCondition.ValueError):
        with self.assertRaises(FilterConditionHandler.ValueError):
            build_4_field(values=[str(folder.id)], user=other_user)

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

        self.assertQEqual(
            Q(**date_range_registry.get_range(name=range_name)
                                   .get_q_dict(field=fname, now=now())
             ),
            handler.get_q(user=None)
        )

    def test_dateregularfield_error(self):
        "<error> property."
        handler1 = DateRegularFieldConditionHandler(
            model=FakeOrganisation,
            field_name='unknown',
            date_range='previous_year',
        )
        self.assertEqual("FakeOrganisation has no field named 'unknown'",
                         handler1.error
                        )

        handler2 = DateRegularFieldConditionHandler(
            model=FakeOrganisation,
            field_name='sector',
            date_range='previous_year',
        )
        self.assertEqual("'sector' is not a date field",
                         handler2.error
                        )

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
        self.assertEqual(fname,       handler._field_name)
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
        self.assertEqual(DateRegularFieldConditionHandler.type_id, condition1.type)
        self.assertEqual(fname1, condition1.name)
        self.assertDictEqual({'start': {'day': 1, 'month': 1, 'year': 2000}},
                             condition1.decoded_value
                            )

        handler1 = DateRegularFieldConditionHandler.build(
            model=FakeContact,
            name=condition1.name,
            data=condition1.decoded_value,
        )
        self.assertIsInstance(handler1, DateRegularFieldConditionHandler)
        self.assertEqual(FakeContact, handler1.model)
        self.assertIsNone(handler1.subfilter_id)
        self.assertIs(handler1.subfilter, False)
        self.assertEqual(fname1, handler1._field_name)
        self.assertIsNone(handler1._range_name)
        self.assertIsNone(handler1._end)
        self.assertEqual(self.create_datetime(year=2000, month=1, day=1),
                         handler1._start
                        )

        # LTE ---
        condition2 = DateRegularFieldConditionHandler.build_condition(
            model=FakeOrganisation, field_name='created',
            end=date(year=1999, month=12, day=31),
        )
        self.assertEqual('created', condition2.name)
        self.assertDictEqual({'end': {'day': 31, 'month': 12, 'year': 1999}},
                             condition2.decoded_value
                            )

        handler2 = DateRegularFieldConditionHandler.build(
            model=FakeOrganisation,
            name=condition2.name,
            data=condition2.decoded_value,
        )
        self.assertEqual(FakeOrganisation, handler2.model)
        self.assertIsNone(handler2._range_name)
        self.assertIsNone(handler2._start)
        self.assertEqual(self.create_datetime(year=1999, month=12, day=31),
                         handler2._end
                        )

        # RANGE ---
        condition3 = DateRegularFieldConditionHandler.build_condition(
            model=FakeContact, field_name='birthday',
            start=date(year=2001, month=1, day=1),
            end=date(year=2001, month=12, day=1),
        )
        self.assertDictEqual({'start': {'day': 1, 'month': 1,  'year': 2001},
                              'end':   {'day': 1, 'month': 12, 'year': 2001},
                             },
                             condition3.decoded_value
                            )

        # YESTERDAY ---
        range_name = 'yesterday'
        condition4 = DateRegularFieldConditionHandler.build_condition(
            model=FakeContact, field_name='birthday', date_range=range_name,
        )
        self.assertDictEqual({'name': range_name}, condition4.decoded_value)

        handler4 = DateRegularFieldConditionHandler.build(
            model=FakeContact,
            name=condition4.name,
            data=condition4.decoded_value,
        )
        self.assertEqual(range_name, handler4._range_name)
        self.assertIsNone(handler4._start)
        self.assertIsNone(handler4._end)

    def test_dateregularfield_condition02(self):
        "Build condition + errors."
        # ValueError = EntityFilterCondition.ValueError
        ValueError = FilterConditionHandler.ValueError
        # build_cond = EntityFilterCondition.build_4_date
        build_cond = DateRegularFieldConditionHandler.build_condition

        self.assertRaises(
            ValueError, build_cond,
            # model=FakeContact, name='unknown_field', start=date(year=2001, month=1, day=1)
            model=FakeContact, field_name='unknown_field', start=date(year=2001, month=1, day=1)
        )
        self.assertRaises(
            ValueError, build_cond,
            # model=FakeContact, name='first_name', start=date(year=2001, month=1, day=1)  # Not a date
            model=FakeContact, field_name='first_name', start=date(year=2001, month=1, day=1)  # Not a date
        )
        self.assertRaises(
            ValueError, build_cond,
            # model=FakeContact, name='birthday',  # No date given
            model=FakeContact, field_name='birthday',  # No date given
        )
        self.assertRaises(
            ValueError, build_cond,
            # model=FakeContact, name='birthday', date_range='unknown_range',
            model=FakeContact, field_name='birthday', date_range='unknown_range',
        )

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

        self.assertQEqual(
            Q(pk__in=FakeOrganisation.objects.none()),
            handler.get_q(user=None)
        )

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
        self.assertEqual("Operator ID '1234' is invalid",
                         handler1.error
                        )

        # ---
        handler2 = CustomFieldConditionHandler(
            model=FakeOrganisation,
            custom_field=custom_field.id,
            operator_id=operators.EQUALS,
            values=['True'],
            related_name='invalid',  # <===
        )
        self.assertEqual("related_name 'invalid' is invalid",
                         handler2.error
                        )

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
                'value': [value],
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

    def test_customfield_condition01(self):
        "Build condition."
        custom_field = CustomField.objects.create(
            name='Size (cm)', field_type=CustomField.INT,
            content_type=FakeContact,
        )

        operator_id = operators.LTE
        value = 155
        rname = 'customfieldinteger'
        condition = CustomFieldConditionHandler.build_condition(
            custom_field=custom_field,
            operator_id=operator_id,
            values=[value],
        )
        self.assertIsInstance(condition, EntityFilterCondition)
        self.assertIsNone(condition.pk)
        self.assertEqual(CustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(custom_field.id), condition.name)
        self.assertDictEqual(
            {'operator': operator_id,
             'value': [str(value)],
             'rname': rname,
            },
            condition.decoded_value
         )

        handler = CustomFieldConditionHandler.build(
            model=FakeContact,
            name=condition.name,
            data=condition.decoded_value,
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
        "Build condition + errors."
        create_cf = partial(CustomField.objects.create, content_type=FakeContact)
        cf_int = create_cf(name='size (cm)', field_type=CustomField.INT)

        # ValueError = EntityFilterCondition.ValueError
        ValueError = FilterConditionHandler.ValueError
        # build_cond = EntityFilterCondition.build_4_customfield
        build_cond = CustomFieldConditionHandler.build_condition

        self.assertRaises(
            ValueError, build_cond,
            # custom_field=cf_int, operator=1216, value=155,  # Invalid operator
            custom_field=cf_int, operator_id=1216, values=155,  # Invalid operator
        )
        self.assertRaises(
            ValueError, build_cond,
            # custom_field=cf_int, operator=EntityFilterCondition.CONTAINS, value='not an int',
            custom_field=cf_int, operator_id=operators.CONTAINS, values='not an int',
        )

        cf_date = create_cf(name='Day', field_type=CustomField.DATETIME)
        self.assertRaises(
            ValueError, build_cond,
            # custom_field=cf_date, operator=EntityFilterCondition.EQUALS, value=2011,  # DATE
            custom_field=cf_date, operator_id=operators.EQUALS, values=2011,  # DATE
        )

        cf_bool = create_cf(name='Cute ?', field_type=CustomField.BOOL)
        self.assertRaises(
            ValueError, build_cond,
            # custom_field=cf_bool, operator=EntityFilterCondition.CONTAINS, value=True,  # Bad operator
            custom_field=cf_bool, operator_id=operators.CONTAINS, values=True,  # Bad operator
        )

    def test_customfield_condition03(self):
        "BOOL => unsupported operator."
        custom_field = CustomField.objects.create(
            name='cute ??',
            content_type=FakeContact,
            field_type=CustomField.BOOL,
        )

        # with self.assertRaises(EntityFilterCondition.ValueError) as err:
        #     EntityFilterCondition.build_4_customfield(custom_field=custom_field,
        #                                               operator=EntityFilterCondition.GT,
        #                                               value=[True],
        #                                              )
        with self.assertRaises(FilterConditionHandler.ValueError) as err:
            CustomFieldConditionHandler.build_condition(custom_field=custom_field,
                                                        operator_id=operators.GT,
                                                        values=[True],
                                                       )

        self.assertEqual(
            str(err.exception),
            'CustomFieldConditionHandler.build_condition(): '
            'BOOL type is only compatible with EQUALS, EQUALS_NOT and ISEMPTY operators'
        )

    def test_customfield_get_q(self):
        "get_q() not empty."
        user = self.login()

        custom_field = CustomField.objects.create(
            name='Is a ship?', field_type=CustomField.BOOL,
            content_type=FakeOrganisation,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop = create_orga(name='Bebop')
        create_orga(name='Swordfish')
        dragons = create_orga(name='Red Dragons')

        klass = custom_field.get_value_class()

        def set_cfvalue(entity, value):
            klass(custom_field=custom_field, entity=entity).set_value_n_save(value)

        set_cfvalue(bebop,   True)
        set_cfvalue(dragons, False)

        handler = CustomFieldConditionHandler(
            model=FakeOrganisation,
            custom_field=custom_field.id,
            operator_id=operators.EQUALS,
            values=['True'],
            related_name='customfieldboolean',
        )
        self.assertQEqual(
            # NB: the nested QuerySet is not compared by the query, but by its result...
            Q(pk__in=FakeOrganisation.objects.filter(id=bebop.id).values_list('id', flat=True)),
            handler.get_q(user=None)
        )

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

        self.assertQEqual(
            Q(pk__in=FakeOrganisation.objects.none()),
            handler.get_q(user=None)
        )

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

    def test_datecustomfield_error(self):
        "<error> property."
        handler = DateCustomFieldConditionHandler(
            model=FakeOrganisation,
            custom_field=12,
            date_range='yesterday',
            related_name='invalid',  # <===
        )
        self.assertEqual("related_name 'invalid' is invalid",
                         handler.error
                        )

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

    def test_datecustomfield_condition01(self):
        "Build condition."
        custom_field = CustomField.objects.create(
            name='First fight',
            content_type=FakeContact,
            field_type=CustomField.DATETIME,
        )

        rname = 'customfielddatetime'
        condition = DateCustomFieldConditionHandler.build_condition(
            custom_field=custom_field, start=date(year=2015, month=4, day=1),
        )
        self.assertIsInstance(condition, EntityFilterCondition)
        self.assertIsNone(condition.pk)
        self.assertEqual(DateCustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(custom_field.id), condition.name)
        self.assertDictEqual(
            {'rname': rname,
             'start': {'day': 1, 'month': 4, 'year': 2015},
            },
            condition.decoded_value
        )

        handler = DateCustomFieldConditionHandler.build(
            model=FakeContact,
            name=condition.name,
            data=condition.decoded_value,
        )
        self.assertIsInstance(handler, DateCustomFieldConditionHandler)
        self.assertEqual(FakeContact, handler.model)
        self.assertIsNone(handler.subfilter_id)
        self.assertIs(handler.subfilter, False)
        self.assertEqual(custom_field.id, handler._custom_field_id)
        self.assertEqual(rname,           handler._related_name)
        self.assertIsNone(handler._range_name)
        self.assertIsNone(handler._end)
        self.assertEqual(self.create_datetime(year=2015, month=4, day=1),
                         handler._start
                        )

    def test_datecustomfield_condition02(self):
        "Build condition + errors."
        # ValueError = EntityFilterCondition.ValueError
        ValueError = FilterConditionHandler.ValueError
        # build_cond = EntityFilterCondition.build_4_datecustomfield
        build_cond = DateCustomFieldConditionHandler.build_condition

        create_cf = partial(CustomField.objects.create, content_type=FakeContact)
        custom_field1 = create_cf(name='First flight', field_type=CustomField.INT)  # Not a DATE
        self.assertRaises(ValueError, build_cond,
                          custom_field=custom_field1, date_range='in_future',
                         )

        custom_field2 = create_cf(name='Day', field_type=CustomField.DATETIME)
        self.assertRaises(ValueError, build_cond,
                          custom_field=custom_field2,  # No date is given
                         )
        self.assertRaises(ValueError, build_cond,
                          custom_field=custom_field2, date_range='unknown_range',
                         )

    def test_datecustomfield_get_q(self):
        "get_q() not empty."
        user = self.login()

        custom_field = CustomField.objects.create(
            name='First fight', field_type=CustomField.DATETIME,
            content_type=FakeOrganisation,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop = create_orga(name='Bebop')
        create_orga(name='Swordfish')
        dragons = create_orga(name='Red Dragons')

        klass = custom_field.get_value_class()

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

    def test_relation_init01(self):
        rtype_id = 'creme_core-subject_loves'
        handler1 = RelationConditionHandler(
            model=FakeOrganisation,
            rtype=rtype_id,
            exclude=False,
        )

        self.assertEqual(FakeOrganisation, handler1.model)
        self.assertIsNone(handler1.subfilter_id)
        self.assertIs(handler1.subfilter, False)
        self.assertEqual(rtype_id, handler1._rtype_id)
        self.assertIs(handler1._exclude, False)
        self.assertIsNone(handler1._ct_id)
        self.assertIsNone(handler1._entity_id)

        self.assertIsNone(handler1.error)

        self.assertQEqual(
            Q(pk__in=Relation.objects.none()),
            handler1.get_q(user=None)
        )

        # ---
        ctype_id = ContentType.objects.get_for_model(FakeContact).id
        handler2 = RelationConditionHandler(
            model=FakeOrganisation,
            rtype=rtype_id,
            ctype=ctype_id,
            exclude=True,
        )

        self.assertIs(handler2._exclude, True)
        self.assertEqual(ctype_id, handler2._ct_id)

        # ---
        entity_id = 64
        handler3 = RelationConditionHandler(
            model=FakeOrganisation,
            rtype=rtype_id,
            entity=entity_id,
        )

        self.assertIs(handler3._exclude, False)
        self.assertEqual(entity_id, handler3._entity_id)

    def test_relation_init02(self):
        "Pass an instance of RelationType."
        rtype = RelationType.create(('test-subject_love', 'Is loving'),
                                    ('test-object_love',  'Is loved by')
                                   )[0]

        handler = RelationConditionHandler(
            model=FakeContact,
            rtype=rtype,
        )

        self.assertEqual(FakeContact, handler.model)
        self.assertEqual(rtype.id, handler._rtype_id)

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

    def test_relation_init04(self):
        "Pass an instance of CremeEntity."
        user = self.login()
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

    def test_relation_condition(self):
        "Build condition."
        user = self.login()

        loves, loved = RelationType.create(('test-subject_love', 'Is loving'),
                                           ('test-object_love',  'Is loved by')
                                          )

        build_cond = partial(RelationConditionHandler.build_condition, model=FakeContact)
        condition1 = build_cond(rtype=loves, has=True)
        self.assertIsInstance(condition1, EntityFilterCondition)
        self.assertIsNone(condition1.pk)
        self.assertEqual(RelationConditionHandler.type_id, condition1.type)
        self.assertEqual(loves.id, condition1.name)
        self.assertDictEqual({'has': True},
                             condition1.decoded_value
                            )

        handler1 = RelationConditionHandler.build(
            model=FakeContact,
            name=condition1.name,
            data=condition1.decoded_value,
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
        condition2 = build_cond(rtype=loved, has=False)
        self.assertEqual(loved.id, condition2.name)
        self.assertDictEqual({'has': False},
                             condition2.decoded_value
                            )

        handler2 = RelationConditionHandler.build(
            model=FakeContact,
            name=condition2.name,
            data=condition2.decoded_value,
        )
        self.assertIs(handler2._exclude, True)

        # ---
        ct = ContentType.objects.get_for_model(FakeContact)
        condition3 = build_cond(rtype=loves, ct=ct)
        self.assertEqual(loves.id, condition3.name)
        self.assertDictEqual({'has': True, 'ct_id': ct.id},
                             condition3.decoded_value
                            )

        handler3 = RelationConditionHandler.build(
            model=FakeContact,
            name=condition3.name,
            data=condition3.decoded_value,
        )
        self.assertEqual(ct.id, handler3._ct_id)

        # ---
        # NB: "ct" should not be used
        orga = FakeOrganisation.objects.create(user=user, name='Nerv')
        condition4 = build_cond(rtype=loves, ct=ct, entity=orga)
        self.assertEqual(loves.id, condition4.name)
        self.assertDictEqual({'has': True, 'entity_id': orga.id},
                             condition4.decoded_value
                            )

        handler4 = RelationConditionHandler.build(
            model=FakeContact,
            name=condition4.name,
            data=condition4.decoded_value,
        )
        self.assertIsNone(handler4._ct_id)
        self.assertEqual(orga.id, handler4._entity_id)

    def test_relation_get_q(self):
        "get_q() not empty."
        user = self.login()

        loves, loved = RelationType.create(('test-subject_love', 'Is loving'),
                                           ('test-object_love',  'Is loved by')
                                          )

        create_contact = partial(FakeContact.objects.create, user=user)
        shinji = create_contact(last_name='Ikari',     first_name='Shinji')
        rei    = create_contact(last_name='Ayanami',   first_name='Rei')
        asuka  = create_contact(last_name='Langley',   first_name='Asuka')
        misato = create_contact(last_name='Katsuragi', first_name='Misato')

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        create_rel = partial(Relation.objects.create, user=user)
        rel1 = create_rel(subject_entity=shinji, type=loves, object_entity=rei)
        rel2 = create_rel(subject_entity=asuka,  type=loves, object_entity=shinji)
        rel3 = create_rel(subject_entity=misato, type=loves, object_entity=nerv)

        handler1 = RelationConditionHandler(model=FakeContact,
                                            rtype=loves.id,
                                            exclude=False,
                                           )
        self.assertQEqual(
            Q(pk__in=Relation.objects
                             .filter(id__in=[rel1.id, rel2.id, rel3.id])
                             .values_list('subject_entity_id', flat=True)
             ),
            handler1.get_q(user=None)
        )

        # Exclude ---
        handler2 = RelationConditionHandler(model=FakeContact,
                                            rtype=loves.id,
                                            exclude=True,
                                           )
        self.assertQEqual(
            ~Q(pk__in=Relation.objects
                             .filter(id__in=[rel1.id, rel2.id, rel3.id])
                             .values_list('subject_entity_id', flat=True)
              ),
            handler2.get_q(user=None)
        )

        # CT ---
        handler3 = RelationConditionHandler(
            model=FakeContact,
            rtype=loves.id,
            ctype=ContentType.objects.get_for_model(FakeContact),
        )
        self.assertQEqual(
            Q(pk__in=Relation.objects
                             .filter(id__in=[rel1.id, rel2.id])
                             .values_list('subject_entity_id', flat=True)
             ),
            handler3.get_q(user=None)
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
                             .values_list('subject_entity_id', flat=True)
             ),
            handler4.get_q(user=None)
        )

    def test_subfilter_init01(self):
        sub_efilter = EntityFilter.create(
            pk='test-filter01', name='Filter01', model=FakeOrganisation, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation, field_name='name',
                    operator_id=operators.EQUALS, values=['Bebop'],
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
            __ = handler.subfilter

        self.assertIsNone(handler.error)

        self.assertQEqual(Q(name__exact='Bebop'),
                          handler.get_q(user=None)
                         )

        # --
        with self.assertRaises(TypeError):
            SubFilterConditionHandler(
                # model=FakeOrganisation,  # No model passed
                subfilter=sub_efilter.id,
            )

    def test_subfilter_init02(self):
        "Pass EntityFilter instance."
        sub_efilter = EntityFilter.create(
            pk='test-filter01', name='Filter01', model=FakeOrganisation, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation, field_name='name',
                    operator_id=operators.EQUALS, values=['Bebop'],
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

    def test_subfilter_condition(self):
        "Build condition."
        sub_efilter = EntityFilter.create(
            pk='test-filter01', name='Filter01', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='last_name',
                    operator_id=operators.EQUALS, values=['Spiegel'],
                ),
            ],
        )

        condition = SubFilterConditionHandler.build_condition(
            sub_efilter
        )
        self.assertIsInstance(condition, EntityFilterCondition)
        self.assertIsNone(condition.pk)
        self.assertEqual(SubFilterConditionHandler.type_id, condition.type)
        self.assertEqual(sub_efilter.id,                    condition.name)
        self.assertEqual('',                                condition.value)

        handler = SubFilterConditionHandler.build(
            model=FakeContact,
            name=condition.name,
            data=condition.decoded_value,
        )
        self.assertIsInstance(handler, SubFilterConditionHandler)
        self.assertEqual(FakeContact, handler.model)
        self.assertEqual(sub_efilter.id, handler.subfilter_id)
        self.assertEqual(sub_efilter.id, handler._subfilter_id)
        self.assertEqual(sub_efilter, handler.subfilter)

    def test_relation_subfilter_init01(self):
        sub_efilter = EntityFilter.create(
            pk='test-filter01', name='Filter01', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='last_name',
                    operator_id=operators.EQUALS, values=['Spiegel'],
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
            __ = handler.subfilter

        self.assertIsNone(handler.error)

        self.assertQEqual(
            Q(pk__in=Relation.objects.none()),
            handler.get_q(user=None)
        )

    def test_relation_subfilter_init02(self):
        "Pass an EntityFilter instance."
        sub_efilter = EntityFilter.create(
            pk='test-filter01', name='Filter01', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='last_name',
                    operator_id=operators.EQUALS, values=['Spiegel'],
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
        rtype = RelationType.create(('test-subject_love', 'Is loving'),
                                    ('test-object_love',  'Is loved by')
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

    def test_relation_subfilter_condition(self):
        "Build condition."
        loves, loved = RelationType.create(('test-subject_love', 'Is loving'),
                                           ('test-object_love',  'Is loved by')
                                          )

        def build_filter(pk):
            return EntityFilter.create(
                pk=pk, name='Filter Rei', model=FakeContact, is_custom=True,
                conditions=[
                    RegularFieldConditionHandler.build_condition(
                        model=FakeContact, field_name='last_name',
                        operator_id=operators.STARTSWITH, values=['Ayanami'],
                    ),
                ],
            )

        sub_efilter1 = build_filter('test-filter01')

        condition1 = RelationSubFilterConditionHandler.build_condition(
            model=FakeContact, rtype=loves, has=True, subfilter=sub_efilter1,
        )
        self.assertIsInstance(condition1, EntityFilterCondition)
        self.assertIsNone(condition1.pk)
        self.assertEqual(RelationSubFilterConditionHandler.type_id, condition1.type)
        self.assertEqual(loves.id, condition1.name)
        self.assertDictEqual({'filter_id': sub_efilter1.id, 'has': True},
                             condition1.decoded_value
                            )

        handler1 = RelationSubFilterConditionHandler.build(
            model=FakeContact,
            name=condition1.name,
            data=condition1.decoded_value,
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
        self.assertDictEqual({'filter_id': sub_efilter2.id, 'has': False},
                             condition2.decoded_value
                            )

        handler2 = RelationSubFilterConditionHandler.build(
            model=FakeContact,
            name=condition2.name,
            data=condition2.decoded_value,
        )
        self.assertIsInstance(handler2, RelationSubFilterConditionHandler)
        self.assertEqual(FakeContact,  handler2.model)
        self.assertEqual(sub_efilter2, handler2.subfilter)
        self.assertEqual(loved.id,     handler2._rtype_id)
        self.assertIs(handler2._exclude, True)

    def test_relation_subfilter_get_q(self):
        "get_q() not empty."
        user = self.login()

        loves, loved = RelationType.create(('test-subject_love', 'Is loving'),
                                           ('test-object_love',  'Is loved by')
                                          )

        create_contact = partial(FakeContact.objects.create, user=user)
        shinji = create_contact(last_name='Ikari',     first_name='Shinji')
        yui    = create_contact(last_name='Ikari',     first_name='Yui')
        rei    = create_contact(last_name='Ayanami',   first_name='Rei')
        asuka  = create_contact(last_name='Langley',   first_name='Asuka')
        misato = create_contact(last_name='Katsuragi', first_name='Misato')

        create_rel = partial(Relation.objects.create, user=user)
        rel1 = create_rel(subject_entity=shinji, type=loves, object_entity=yui)
        rel2 = create_rel(subject_entity=asuka,  type=loves, object_entity=shinji)
        ___  = create_rel(subject_entity=rei,    type=loves, object_entity=misato)

        sub_filter = EntityFilter.create(
            pk='test-filter01', name='Filter Ikari', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='last_name',
                    operator_id=operators.STARTSWITH, values=['Ikari'],
                ),
            ],
        )

        handler1 = RelationSubFilterConditionHandler(
            model=FakeOrganisation,
            subfilter=sub_filter.id,
            rtype=loves.id,
        )
        self.assertQEqual(
            Q(pk__in=Relation.objects
                             .filter(id__in=[rel1.id, rel2.id])
                             .values_list('subject_entity_id', flat=True)
             ),
            handler1.get_q(user=None)
        )

        # Exclude ---
        handler2 = RelationSubFilterConditionHandler(
            model=FakeOrganisation,
            subfilter=sub_filter.id,
            rtype=loves.id,
            exclude=True,
        )
        self.assertQEqual(
            ~Q(pk__in=Relation.objects
                              .filter(id__in=[rel1.id, rel2.id])
                              .values_list('subject_entity_id', flat=True)
              ),
            handler2.get_q(user=None)
        )

    def test_property_init01(self):
        ptype_id = 'creme_core-is_cool'
        handler = PropertyConditionHandler(
            model=FakeOrganisation,
            ptype=ptype_id,
            exclude=False,
        )

        self.assertEqual(FakeOrganisation, handler.model)
        self.assertIsNone(handler.subfilter_id)
        self.assertIs(handler.subfilter, False)
        self.assertEqual(ptype_id, handler._ptype_id)
        self.assertIs(handler._exclude, False)

        self.assertIsNone(handler.error)

        self.assertQEqual(
            Q(pk__in=CremeProperty.objects.none()),
            handler.get_q(user=None)
        )

    def test_property_init02(self):
        "Pass a CremePropertyType instance."
        ptype = CremePropertyType.create(str_pk='test-prop_kawaii', text='Kawaii')

        handler = PropertyConditionHandler(
            model=FakeContact,
            ptype=ptype,
            exclude=True,
        )

        self.assertEqual(FakeContact, handler.model)
        self.assertEqual(ptype.id, handler._ptype_id)
        self.assertIs(handler._exclude, True)

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

    def test_property_condition(self):
        "Build condition."
        ptype1 = CremePropertyType.create(str_pk='test-prop_kawaii', text='Kawaii')

        condition1 = PropertyConditionHandler.build_condition(
            model=FakeContact, ptype=ptype1, has=True,
        )
        self.assertIsInstance(condition1, EntityFilterCondition)
        self.assertIsNone(condition1.pk)
        self.assertEqual(PropertyConditionHandler.type_id, condition1.type)
        self.assertEqual(ptype1.id,                        condition1.name)
        self.assertEqual(True,                             condition1.decoded_value)

        handler1 = PropertyConditionHandler.build(
            model=FakeContact,
            name=condition1.name,
            data=condition1.decoded_value,
        )
        self.assertIsInstance(handler1, PropertyConditionHandler)
        self.assertEqual(FakeContact, handler1.model)
        self.assertIsNone(handler1.subfilter_id)
        self.assertIs(handler1.subfilter, False)
        self.assertEqual(ptype1.id, handler1._ptype_id)
        self.assertIs(handler1._exclude, False)

        # ---
        ptype2 = CremePropertyType.create(str_pk='test-prop_cute', text='Cute')
        condition2 = PropertyConditionHandler.build_condition(
            model=FakeContact, ptype=ptype2, has=False,
        )
        self.assertEqual(ptype2.id, condition2.name)
        self.assertIs(condition2.decoded_value, False)

        handler2 = PropertyConditionHandler.build(
            model=FakeContact,
            name=condition2.name,
            data=condition2.decoded_value,
        )
        self.assertEqual(ptype2.id, handler2._ptype_id)
        self.assertIs(handler2._exclude, True)

    def test_property_get_q(self):
        "get_q() not empty."
        user = self.login()

        create_ptype = CremePropertyType.create
        cute  = create_ptype(str_pk='test-prop_cute', text='Cute')
        pilot = create_ptype(str_pk='test-prop_pilot',  text='Pilot')

        create_contact = partial(FakeContact.objects.create, user=user)
        shinji = create_contact(last_name='Ikari',     first_name='Shinji')
        rei    = create_contact(last_name='Ayanami',   first_name='Rei')
        ___    = create_contact(last_name='Langley',   first_name='Asuka')
        misato = create_contact(last_name='Katsuragi', first_name='Misato')

        create_prop = CremeProperty.objects.create
        prop1 = create_prop(creme_entity=rei,    type=cute)
        ___   = create_prop(creme_entity=rei,    type=pilot)
        prop3 = create_prop(creme_entity=misato, type=cute)
        ___   = create_prop(creme_entity=shinji, type=pilot)

        handler1 = PropertyConditionHandler(
            model=FakeOrganisation,
            ptype=cute.id,
        )
        self.assertQEqual(
            Q(pk__in=CremeProperty.objects
                                  .filter(id__in=[prop1.id, prop3.id])
                                  .values_list('creme_entity_id', flat=True)
             ),
            handler1.get_q(user=None)
        )

        # Exclude ---
        handler2 = PropertyConditionHandler(
            model=FakeOrganisation,
            ptype=cute.id,
            exclude=True,
        )
        self.assertQEqual(
            ~Q(pk__in=CremeProperty.objects
                                   .filter(id__in=[prop1.id, prop3.id])
                                   .values_list('creme_entity_id', flat=True)
              ),
            handler2.get_q(user=None)
        )

    def test_operand_currentuser(self):
        # efilter = EntityFilter.create('test-filter01', 'Spike & Faye', FakeContact, is_custom=True)

        with self.assertNoException():
            RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator_id=operators.EQUALS,
                field_name='user',
                values=['__currentuser__'],
            )

        with self.assertNoException():
            # efilter.set_conditions([
            #     EntityFilterCondition.build_4_field(
            #         model=FakeContact,
            #         operator=EntityFilterCondition.EQUALS,
            #         name='last_name',
            #         values=['__currentuser__'],
            #     ),
            # ])
            RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator_id=operators.EQUALS,
                # OK it's a CharField, you could search "__currentuser__" if you want...
                field_name='last_name',
                values=['__currentuser__'],
            )

        # with self.assertRaises(EntityFilterCondition.ValueError):
        with self.assertRaises(FilterConditionHandler.ValueError):
            # efilter.set_conditions([
            #     EntityFilterCondition.build_4_field(
            #         model=FakeContact,
            #         operator=EntityFilterCondition.EQUALS,
            #         name='birthday',
            #         values=['__currentuser__'],
            #     ),
            # ])
            RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator_id=operators.EQUALS,
                field_name='birthday',   # <= DateField -> KO
                values=['__currentuser__'],
            )

        with self.assertRaises(FilterConditionHandler.ValueError):
            RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator_id=operators.EQUALS,
                field_name='sector',   # <= ForeignKey but not related to User
                values=['__currentuser__'],
            )
