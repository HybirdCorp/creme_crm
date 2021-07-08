# -*- coding: utf-8 -*-

from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db.models.query_utils import Q
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.entity_filter import (
    EF_USER,
    _EntityFilterRegistry,
    entity_filter_registries,
    operands,
    operators,
)
from creme.creme_core.models import FakeContact, FakeOrganisation, Language
from creme.creme_core.tests.base import CremeTestCase


class OperatorTestCase(CremeTestCase):
    @staticmethod
    def get_operator(op_id):
        return entity_filter_registries[EF_USER].get_operator(op_id)

    def test_base(self):
        pattern = '{}__foobar'

        class TestOp(operators.ConditionOperator):
            verbose_name = 'Foo'
            key_pattern = pattern

        op = TestOp()
        self.assertEqual((), op.allowed_fieldtypes)
        self.assertIs(op.exclude, False)
        self.assertEqual(pattern, op.key_pattern)
        self.assertIs(op.accept_subpart, True)
        self.assertEqual(TestOp.verbose_name, str(op))

    def test_get_q1(self):
        class ContainsOp(operators.ConditionOperator):
            key_pattern = '{}__contains'

        self.assertQEqual(
            Q(name__contains='Acme'),
            ContainsOp().get_q(
                model=FakeOrganisation,
                field_name='name', values=['Acme'],
            ),
        )

    def test_get_q2(self):
        "Other pattern, several values."
        class EndsOp(operators.ConditionOperator):
            key_pattern = '{}__endswith'

        self.assertQEqual(
            Q(last_name__endswith='foo') | Q(last_name__endswith='bar'),
            EndsOp().get_q(
                model=FakeContact,
                field_name='last_name', values=['foo', 'bar'],
            ),
        )

    def test_validate_field_values01(self):
        "String."
        op = operators.ConditionOperator()
        field = FakeOrganisation._meta.get_field('name')

        values = ['Acme']
        self.assertEqual(
            values,
            op.validate_field_values(field=field, values=[*values]),
        )

    def test_validate_field_values02(self):
        "Integer."
        op = operators.ConditionOperator()
        field = FakeOrganisation._meta.get_field('capital')

        values = ['1000', '3000']
        self.assertEqual(
            values,
            op.validate_field_values(field=field, values=[*values]),
        )

        with self.assertRaises(ValidationError):
            op.validate_field_values(field=field, values=['1000', 'notanint'])

    def test_validate_field_values03(self):
        "Email (sub-part validation)."
        op1 = operators.ConditionOperator()
        field = FakeOrganisation._meta.get_field('email')

        values = ['toto@']
        self.assertEqual(
            values,
            op1.validate_field_values(field=field, values=[*values]),
        )

        class DoNotAcceptSubPartOperator(operators.ConditionOperator):
            accept_subpart = False

        op2 = DoNotAcceptSubPartOperator()
        with self.assertRaises(ValidationError):
            op2.validate_field_values(field=field, values=values)

    def test_validate_field_values04(self):
        "Operand."
        user = self.create_user()
        registry = _EntityFilterRegistry(id=10, verbose_name='Test')

        op = operators.ConditionOperator()
        get_field = FakeOrganisation._meta.get_field

        values = [operands.CurrentUserOperand.type_id]
        self.assertEqual(
            values,
            op.validate_field_values(
                field=get_field('name'),
                values=[*values],
                user=user,
                efilter_registry=registry,
            )
        )

        user_field = get_field('user')
        with self.assertRaises(ValidationError):
            op.validate_field_values(
                field=user_field,
                values=[*values],
                user=user,
                efilter_registry=registry,
            )

        registry.register_operands(operands.CurrentUserOperand)
        self.assertEqual(
            values,
            op.validate_field_values(
                field=get_field('user'),
                values=[*values],
                user=user,
                efilter_registry=registry,
            )
        )

    def test_validate_field_values05(self):
        "ManyToManyField."
        op = operators.ConditionOperator()
        field = FakeContact._meta.get_field('languages')
        lang1, lang2 = Language.objects.all()[:2]

        values = [str(lang1.id), str(lang2.id)]
        self.assertEqual(
            values,
            op.validate_field_values(field=field, values=[*values]),
        )

        with self.assertRaises(ValidationError):
            op.validate_field_values(field=field, values=[*values, 'notanint'])

    def test_equals(self):
        op = self.get_operator(operators.EQUALS)
        self.assertIsInstance(op, operators.EqualsOperator)
        self.assertFalse(op.accept_subpart)
        self.assertIs(op.exclude, False)
        self.assertSetEqual(
            {
                'string',
                'enum', 'enum__null',
                'number', 'number__null',
                'date', 'date__null',
                'boolean', 'boolean__null',
                'fk', 'fk__null',
                'user', 'user__null',
            },
            op.allowed_fieldtypes,
        )
        # TODO: complete

        field = 'Foo'
        self.assertEqual('??', op.description(field_vname=field, values=[]))

        value1 = 26
        fmt = _('«{field}» is {values}').format
        fmt_value = _('«{enum_value}»').format
        self.assertEqual(
            fmt(
                field=field,
                values=fmt_value(enum_value=value1),
            ),
            op.description(field_vname=field, values=[value1]),
        )

        value2 = 28
        self.assertEqual(
            fmt(
                field=field,
                values=_('{first} or {last}').format(
                    first=fmt_value(enum_value=value1),
                    last=fmt_value(enum_value=value2),
                ),
            ),
            op.description(field_vname=field, values=[value1, value2])
        )

        value3 = 42
        self.assertEqual(
            fmt(
                field=field,
                values=_('{first} or {last}').format(
                    first=f'{fmt_value(enum_value=value1)}, '
                          f'{fmt_value(enum_value=value2)}',
                    last=fmt_value(enum_value=value3),
                ),
            ),
            op.description(field_vname=field, values=[value1, value2, value3]),
        )

    def test_equals_get_q(self):
        op = operators.EqualsOperator()
        self.assertQEqual(
            Q(name__exact='Acme'),
            op.get_q(
                model=FakeOrganisation,
                field_name='name',
                values=['Acme'],
            ),
        )
        self.assertQEqual(
            Q(last_name__in=['Spiegel', 'Black']),
            op.get_q(
                model=FakeContact,
                field_name='last_name',
                values=['Spiegel', 'Black'],
            ),
        )
        self.assertQEqual(
            Q(),
            op.get_q(
                model=FakeContact,
                field_name='last_name',
                values=[],  # Should not happen...
            ),
        )

    def test_equals_accept(self):
        op = operators.EqualsOperator()
        self.assertIs(op.accept(field_value='Nerv',  values=['Nerv']),  True)
        self.assertIs(op.accept(field_value='Nerv',  values=['Seele']), False)
        self.assertIs(op.accept(field_value='Seele', values=['Seele']), True)

        # Case sensitivity ---
        with patch('creme.creme_core.core.entity_filter.operators.is_db_equal_case_sensitive',
                   return_value=True) as mock_sensitive:
            accepted_sensitive = op.accept(field_value='Nerv', values=['nErv'])

        mock_sensitive.assert_called_once_with()
        self.assertIs(accepted_sensitive, False)

        with patch('creme.creme_core.core.entity_filter.operators.is_db_equal_case_sensitive',
                   return_value=False) as mock_no_sensitive:
            accepted_no_sensitive = op.accept(field_value='Nerv', values=['nErv'])

        mock_no_sensitive.assert_called_once_with()
        self.assertIs(accepted_no_sensitive, True)

        # Value is a list ---
        self.assertIs(op.accept(field_value='Nerv', values=[['Eva01', 'Nerv']]), True)
        self.assertIs(op.accept(field_value='Nerv', values=[['Eva01', 'Eva02']]), False)

        # Not strings ---
        with patch('creme.creme_core.core.entity_filter.operators.is_db_equal_case_sensitive',
                   return_value=True):
            self.assertIs(op.accept(field_value=1000, values=[1000]), True)
            self.assertIs(op.accept(field_value=500,  values=[1000]), False)
            self.assertIs(op.accept(field_value=500,  values=[500]),  True)

        with patch('creme.creme_core.core.entity_filter.operators.is_db_equal_case_sensitive',
                   return_value=False):
            self.assertIs(op.accept(field_value=1000, values=[1000]), True)
            self.assertIs(op.accept(field_value=500,  values=[1000]), False)
            self.assertIs(op.accept(field_value=500,  values=[500]),  True)

        self.assertIs(op.accept(field_value=None, values=[1]), False)

    def test_equals_not(self):
        op = operators.EqualsNotOperator()
        self.assertIs(op.exclude, True)

        field = 'Foo'
        self.assertEqual('??', op.description(field_vname=field, values=[]))

        value1 = 26
        fmt_value = _('«{enum_value}»').format
        self.assertEqual(
            _('«{field}» is not {values}').format(
                field=field,
                values=fmt_value(enum_value=value1),
            ),
            op.description(field_vname=field, values=[value1])
        )

        value2 = 28
        self.assertEqual(
            _('«{field}» is not {values}').format(
                field=field,
                values=_('{first} or {last}').format(
                    first=fmt_value(enum_value=value1),
                    last=fmt_value(enum_value=value2),
                ),
            ),
            op.description(field_vname=field, values=[value1, value2])
        )

    def test_equals_not_accept(self):
        op = operators.EqualsNotOperator()
        self.assertIs(op.accept(field_value='Nerv', values=['Nerv']),  False)
        self.assertIs(op.accept(field_value='Nerv', values=['Seele']), True)
        self.assertIs(op.accept(field_value='Seele', values=['Seele']), False)

        # Case sensitivity ---
        with patch('creme.creme_core.core.entity_filter.operators.is_db_equal_case_sensitive',
                   return_value=True) as mock_sensitive:
            accepted_sensitive = op.accept(field_value='Nerv', values=['nErv'])

        mock_sensitive.assert_called_once_with()
        self.assertIs(accepted_sensitive, True)

        with patch('creme.creme_core.core.entity_filter.operators.is_db_equal_case_sensitive',
                   return_value=False) as mock_no_sensitive:
            accepted_no_sensitive = op.accept(field_value='Nerv', values=['nErv'])

        mock_no_sensitive.assert_called_once_with()
        self.assertIs(accepted_no_sensitive, False)

        self.assertIs(op.accept(field_value=None, values=[1]), True)

    def test_boolean(self):
        op = operators.BooleanOperatorBase()
        field = FakeContact._meta.get_field('is_a_nerd')

        values1 = [True]
        self.assertEqual(
            values1,
            op.validate_field_values(field=field, values=[*values1])
        )

        values2 = [False]
        self.assertEqual(
            values2,
            op.validate_field_values(field=field, values=[*values2])
        )

        with self.assertRaises(ValidationError):
            op.validate_field_values(field=field, values=['notabool'])

        with self.assertRaises(ValidationError):
            op.validate_field_values(field=field, values=[True, False])

    def test_is_empty(self):
        self.assertIsSubclass(operators.IsEmptyOperator, operators.BooleanOperatorBase)

        op = operators.IsEmptyOperator()
        self.assertFalse(op.accept_subpart)
        self.assertSetEqual(
            {'string', 'fk__null', 'user__null', 'enum__null', 'boolean__null'},
            op.allowed_fieldtypes,
        )
        # TODO: complete

        field = 'Foo'
        self.assertEqual('??', op.description(field_vname=field, values=[]))
        self.assertEqual(
            _('«{field}» is empty').format(field=field),
            op.description(field_vname=field, values=[True]),
        )
        self.assertEqual(
            _('«{field}» is not empty').format(field=field),
            op.description(field_vname=field, values=[False]),
        )

        self.assertEqual(
            _('«{field}» is empty').format(field=field),
            op.description(field_vname=field, values=['True']),  # not Bool
        )

    def test_is_empty_get_q(self):
        op = operators.IsEmptyOperator()
        self.assertQEqual(
            Q(sector__isnull=True),
            op.get_q(
                model=FakeOrganisation,
                field_name='sector',
                values=[True],
            ),
        )
        self.assertQEqual(
            Q(last_name__isnull=True) | Q(last_name=''),
            op.get_q(
                model=FakeContact,
                field_name='last_name',
                values=[True],
            ),
        )

        q3 = Q(last_name__isnull=True) | Q(last_name='')
        q3.negate()
        self.assertQEqual(
            q3,
            op.get_q(
                model=FakeContact,
                field_name='last_name',
                values=[False],
            ),
        )

    def test_is_empty_accept(self):
        op = operators.IsEmptyOperator()
        self.assertIs(op.accept(field_value='',   values=[True]), True)
        self.assertIs(op.accept(field_value=None, values=[True]), True)
        self.assertIs(op.accept(field_value='X',  values=[True]), False)

        self.assertIs(op.accept(field_value='',    values=[False]), False)
        self.assertIs(op.accept(field_value='FOO', values=[False]), True)

    def test_range(self):
        op = operators.RangeOperator()
        self.assertTrue(op.accept_subpart)
        self.assertEqual('{}__range',        op.key_pattern)
        self.assertEqual(('number', 'date'), op.allowed_fieldtypes)
        # TODO: complete

        field = 'Foo'
        self.assertEqual('??', op.description(field_vname=field, values=[]))

        value1 = 25
        self.assertEqual('??', op.description(field_vname=field, values=[value1]))

        value2 = 30
        value3 = 42
        self.assertEqual(
            '??',
            op.description(field_vname=field, values=[value1, value2, value3])
        )

        self.assertEqual(
            _('«{field}» is between «{start}» and «{end}»').format(
                field=field,
                start=value1,
                end=value2,
            ),
            op.description(field_vname=field, values=[value1, value2])
        )

    def test_range_validate_field_values(self):
        op = operators.RangeOperator()
        field = FakeOrganisation._meta.get_field('capital')

        values1 = [1000, 2000]
        self.assertEqual(
            [values1],
            op.validate_field_values(field=field, values=[*values1]),
        )

        with self.assertRaises(ValidationError):
            op.validate_field_values(field=field, values=[1000])

        with self.assertRaises(ValidationError):
            op.validate_field_values(field=field, values=[1000, 2000, 3000])

        with self.assertRaises(ValidationError):
            op.validate_field_values(field=field, values=[1000, 'noanint'])

    def test_range_get_q(self):
        op = operators.RangeOperator()
        self.assertQEqual(
            Q(capital__range=[1000, 10000]),
            op.get_q(
                model=FakeOrganisation,
                field_name='capital',
                values=[[1000, 10000]],
            ),
        )

    def test_range_accept(self):
        op = operators.RangeOperator()
        self.assertIs(op.accept(field_value=1000, values=[[100, 1500]]), True)
        self.assertIs(op.accept(field_value=99,   values=[[100, 1500]]), False)
        self.assertIs(op.accept(field_value=1501, values=[[100, 1500]]), False)
        self.assertIs(op.accept(field_value=1000, values=[[100, 1500]]), True)
        self.assertIs(op.accept(field_value=1500, values=[[100, 1500]]), True)
        self.assertIs(op.accept(field_value=None, values=[[100, 1500]]), False)

    def test_gt(self):
        op = self.get_operator(operators.GT)
        self.assertIsInstance(op, operators.GTOperator)
        self.assertEqual(_('>'), op.verbose_name)
        self.assertIs(op.exclude, False)
        self.assertEqual('{}__gt', op.key_pattern)
        self.assertIs(op.accept_subpart, True)
        self.assertEqual(operators.FIELDTYPES_ORDERABLE, op.allowed_fieldtypes)

        field = 'capital'
        self.assertEqual('??', op.description(field_vname=field, values=[]))

        value1 = 58
        fmt_value = _('«{enum_value}»').format
        self.assertEqual(
            _('«{field}» is greater than {values}').format(
                field=field,
                values=fmt_value(enum_value=value1),
            ),
            op.description(field_vname=field, values=[value1])
        )

        value2 = 75
        self.assertEqual(
            _('«{field}» is greater than {values}').format(
                field=field,
                values=_('{first} or {last}').format(
                    first=fmt_value(enum_value=value1),
                    last=fmt_value(enum_value=value2),
                ),
            ),
            op.description(field_vname=field, values=[value1, value2]),
        )

    def test_gt_accept(self):
        op = operators.GTOperator()
        self.assertIs(op.accept(field_value=1000, values=[100]),  True)
        self.assertIs(op.accept(field_value=1000, values=[999]),  True)
        self.assertIs(op.accept(field_value=1000, values=[1000]), False)

        self.assertIs(op.accept(field_value=99,   values=[100]),  False)
        self.assertIs(op.accept(field_value=None, values=[100]),  False)

    def test_gte(self):
        op = self.get_operator(operators.GTE)
        self.assertIsInstance(op, operators.GTEOperator)
        self.assertEqual(_('≥'), op.verbose_name)
        self.assertIs(op.exclude, False)
        self.assertEqual('{}__gte', op.key_pattern)
        self.assertIs(op.accept_subpart, True)
        self.assertEqual(operators.FIELDTYPES_ORDERABLE, op.allowed_fieldtypes)

        field = 'order'
        value1 = 6
        self.assertEqual(
            _('«{field}» is greater than or equal to {values}').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value1),
            ),
            op.description(field_vname=field, values=[value1]),
        )

    def test_gte_accept(self):
        op = operators.GTEOperator()
        self.assertIs(op.accept(field_value=1000, values=[100]),  True)
        self.assertIs(op.accept(field_value=1000, values=[1000]), True)
        self.assertIs(op.accept(field_value=1000, values=[1001]), False)

        self.assertIs(op.accept(field_value=99,   values=[100]), False)
        self.assertIs(op.accept(field_value=None, values=[100]), False)

    def test_lt(self):
        op = self.get_operator(operators.LT)
        self.assertIsInstance(op, operators.LTOperator)
        self.assertEqual(_('<'), op.verbose_name)
        self.assertIs(op.exclude, False)
        self.assertEqual('{}__lt', op.key_pattern)
        self.assertIs(op.accept_subpart, True)
        self.assertEqual(operators.FIELDTYPES_ORDERABLE, op.allowed_fieldtypes)

        field = 'order'
        value = 8
        self.assertEqual(
            _('«{field}» is less than {values}').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value])
        )

    def test_lt_accept(self):
        op = operators.LTOperator()
        self.assertIs(op.accept(field_value=100, values=[1000]), True)
        self.assertIs(op.accept(field_value=100, values=[101]),  True)
        self.assertIs(op.accept(field_value=100, values=[100]),  False)

        self.assertIs(op.accept(field_value=99, values=[100]), True)
        self.assertIs(op.accept(field_value=None, values=[100]), False)

    def test_lte(self):
        op = self.get_operator(operators.LTE)
        self.assertIsInstance(op, operators.LTEOperator)
        self.assertEqual(_('≤'), op.verbose_name)
        self.assertIs(op.exclude, False)
        self.assertEqual('{}__lte', op.key_pattern)
        self.assertIs(op.accept_subpart, True)
        self.assertEqual(operators.FIELDTYPES_ORDERABLE, op.allowed_fieldtypes)

        field = 'size'
        value = 68
        self.assertEqual(
            _('«{field}» is less than or equal to {values}').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value]),
        )

    def test_lte_accept(self):
        op = operators.LTEOperator()
        self.assertIs(op.accept(field_value=100, values=[1000]), True)
        self.assertIs(op.accept(field_value=100, values=[100]),  True)
        self.assertIs(op.accept(field_value=100, values=[99]),   False)

        self.assertIs(op.accept(field_value=99,   values=[99]), True)
        self.assertIs(op.accept(field_value=None, values=[99]), False)

    def test_iequals(self):
        op = self.get_operator(operators.IEQUALS)
        self.assertIsInstance(op, operators.IEqualsOperator)
        self.assertEqual(_('Equals (case insensitive)'), op.verbose_name)
        self.assertEqual('{}__iexact',                   op.key_pattern)
        self.assertFalse(op.accept_subpart)
        self.assertFalse(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING, op.allowed_fieldtypes)

        field = 'name'
        self.assertEqual('??', op.description(field_vname=field, values=[]))

        value = 'Spike'
        self.assertEqual(
            _('«{field}» is equal to {values} (case insensitive)').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value]),
        )

    def test_iequals_accept(self):
        op = operators.IEqualsOperator()
        self.assertIs(op.accept(field_value='Nerv', values=['Nerv']),  True)
        self.assertIs(op.accept(field_value='Nerv', values=['nerv']),  True)
        self.assertIs(op.accept(field_value='Nerv', values=['Seele']), False)

        self.assertIs(op.accept(field_value='SEELE', values=['Seele']), True)
        self.assertIs(op.accept(field_value=None,    values=['gikari@seele.jp']), False)

    def test_iequals_not(self):
        op = self.get_operator(operators.IEQUALS_NOT)
        self.assertIsInstance(op, operators.IEqualsNotOperator)
        self.assertEqual(_('Does not equal (case insensitive)'), op.verbose_name)
        self.assertEqual('{}__iexact',                           op.key_pattern)
        self.assertFalse(op.accept_subpart)
        self.assertTrue(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING, op.allowed_fieldtypes)

        field = 'first_name'
        value = 'Spike'
        self.assertEqual(
            _('«{field}» is different from {values} (case insensitive)').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value])
        )

    def test_iequals_not_accept(self):
        op = operators.IEqualsNotOperator()
        self.assertIs(op.accept(field_value='Nerv', values=['Nerv']),  False)
        self.assertIs(op.accept(field_value='Nerv', values=['nerv']),  False)
        self.assertIs(op.accept(field_value='Nerv', values=['Seele']), True)

        self.assertIs(op.accept(field_value='SEELE', values=['Seele']), False)

    def test_contains(self):
        op = self.get_operator(operators.CONTAINS)
        self.assertIsInstance(op, operators.ContainsOperator)
        self.assertEqual(_('Contains'), op.verbose_name)
        self.assertEqual('{}__contains', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertFalse(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING, op.allowed_fieldtypes)

        field = 'info'
        value = 'important'
        self.assertEqual(
            _('«{field}» contains {values}').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value]),
        )

    def test_contains_accept(self):
        op = operators.ContainsOperator()
        self.assertIs(op.accept(field_value='Evil corp',         values=['corp']), True)
        self.assertIs(op.accept(field_value='Acme incorporated', values=['corp']), True)

        self.assertIs(op.accept(field_value='Nerv inc.',  values=['corp']), False)
        self.assertIs(op.accept(field_value='Nerv inc.',  values=['inc']),  True)

        self.assertIs(op.accept(field_value='Evil corp', values=['cme', 'vil']),  True)
        self.assertIs(op.accept(field_value='Nerv inc.', values=['cme', 'vil']),  False)

        # Case sensitivity ---
        with patch('creme.creme_core.core.entity_filter.operators.is_db_like_case_sensitive',
                   return_value=True) as mock_sensitive:
            accepted_sensitive = op.accept(field_value='Evil corp', values=['cOR'])

        mock_sensitive.assert_called_once_with()
        self.assertIs(accepted_sensitive, False)

        with patch('creme.creme_core.core.entity_filter.operators.is_db_like_case_sensitive',
                   return_value=False) as mock_no_sensitive:
            accepted_no_sensitive = op.accept(field_value='Evil corp', values=['cOR'])

        mock_no_sensitive.assert_called_once_with()
        self.assertIs(accepted_no_sensitive, True)

        self.assertIs(op.accept(field_value=None, values=['corp']), False)

    def test_contains_not(self):
        op = self.get_operator(operators.CONTAINS_NOT)
        self.assertIsInstance(op, operators.ContainsNotOperator)
        self.assertEqual(_('Does not contain'), op.verbose_name)
        self.assertEqual('{}__contains', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertTrue(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING, op.allowed_fieldtypes)

        field = 'Info'
        value = 'ignore'
        self.assertEqual(
            _('«{field}» does not contain {values}').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value]),
        )

    def test_contains_not_accept(self):
        accept = operators.ContainsNotOperator().accept
        self.assertIs(accept(field_value='Evil corp',        values=['inc']), True)
        self.assertIs(accept(field_value='Acme corporation', values=['inc']), True)
        self.assertIs(accept(field_value='Nerv inc.',        values=['inc']), False)

        self.assertIs(accept(field_value='Evil corp', values=['cme', 'erv']),  True)
        self.assertIs(accept(field_value='Evil corp', values=['cor', 'erv']),  False)
        self.assertIs(accept(field_value='Evil corp', values=['cme', 'vil']), False)

    def test_icontains(self):
        op = self.get_operator(operators.ICONTAINS)
        self.assertIsInstance(op, operators.IContainsOperator)
        self.assertEqual(_('Contains (case insensitive)'), op.verbose_name)
        self.assertEqual('{}__icontains', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertFalse(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING, op.allowed_fieldtypes)

        field = 'Information'
        value = 'IMPORTANT'
        self.assertEqual(
            _('«{field}» contains {values} (case insensitive)').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value]),
        )

    def test_icontains_accept(self):
        op = operators.IContainsOperator()
        self.assertIs(op.accept(field_value='Evil corp', values=['corp']), True)
        self.assertIs(op.accept(field_value='Evil corp', values=['CORP']), True)

        self.assertIs(op.accept(field_value='ACME incorporated', values=['acme']), True)

        self.assertIs(op.accept(field_value=None, values=['acme']), False)

    def test_icontains_not(self):
        op = self.get_operator(operators.ICONTAINS_NOT)
        self.assertIsInstance(op, operators.IContainsNotOperator)
        self.assertEqual(_('Does not contain (case insensitive)'), op.verbose_name)
        self.assertEqual('{}__icontains', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertTrue(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING, op.allowed_fieldtypes)

        field = 'Information'
        value = 'IgNoRe'
        self.assertEqual(
            _('«{field}» does not contain {values} (case insensitive)').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value]),
        )

    def test_icontains_not_accept(self):
        op = operators.IContainsNotOperator()
        self.assertIs(op.accept(field_value='Evil corp', values=['corp']), False)
        self.assertIs(op.accept(field_value='Evil corp', values=['CORP']), False)

        self.assertIs(op.accept(field_value='ACME incorporated', values=['evil']), True)
        self.assertIs(op.accept(field_value='ACME incorporated', values=['EVIL']), True)

    def test_startswith(self):
        op = self.get_operator(operators.STARTSWITH)
        self.assertIsInstance(op, operators.StartsWithOperator)
        self.assertEqual(_('Starts with'), op.verbose_name)
        self.assertEqual('{}__startswith', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertFalse(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING, op.allowed_fieldtypes)

        field = 'Last_name'
        value = 'sire'
        self.assertEqual(
            _('«{field}» starts with {values}').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value]),
        )

    def test_startswith_accept(self):
        accept = operators.StartsWithOperator().accept
        self.assertIs(accept(field_value='Evil corp',    values=['Evil']), True)
        self.assertIs(accept(field_value='Evil company', values=['Evil']), True)

        self.assertIs(accept(field_value='We are not Evil', values=['Evil']),       False)
        self.assertIs(accept(field_value='We are not Evil', values=['Evil', 'We']), True)
        self.assertIs(accept(field_value='We are not Evil', values=['We']),         True)

        # Case sensitivity ---
        with patch('creme.creme_core.core.entity_filter.operators.is_db_like_case_sensitive',
                   return_value=True) as mock_sensitive:
            accepted_sensitive = accept(field_value='Evil corp', values=['EVIL'])

        mock_sensitive.assert_called_once_with()
        self.assertIs(accepted_sensitive, False)

        with patch('creme.creme_core.core.entity_filter.operators.is_db_like_case_sensitive',
                   return_value=False) as mock_no_sensitive:
            accepted_no_sensitive = accept(field_value='Evil corp', values=['EVIL'])

        mock_no_sensitive.assert_called_once_with()
        self.assertIs(accepted_no_sensitive, True)

        self.assertIs(accept(field_value=None, values=['evil']), False)

    def test_startswith_not(self):
        op = self.get_operator(operators.STARTSWITH_NOT)
        self.assertIsInstance(op, operators.StartswithNotOperator)
        self.assertEqual(_('Does not start with'), op.verbose_name)
        self.assertEqual('{}__startswith', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertTrue(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING, op.allowed_fieldtypes)

        field = 'Last_name'
        value = 'sire'
        self.assertEqual(
            _('«{field}» does not start with {values}').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value]),
        )

    def test_startswith_not_accept(self):
        accept = operators.StartswithNotOperator().accept
        self.assertIs(accept(field_value='Evil corp', values=['Evil']), False)
        self.assertIs(accept(field_value='Evil corp', values=['corp']), True)

        self.assertIs(accept(field_value='Evil company', values=['Evil']), False)
        self.assertIs(accept(field_value='Evil company', values=['comp']), True)

    def test_istartswith(self):
        op = self.get_operator(operators.ISTARTSWITH)
        self.assertIsInstance(op, operators.IStartsWithOperator)
        self.assertEqual(_('Starts with (case insensitive)'), op.verbose_name)
        self.assertEqual('{}__istartswith', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertFalse(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING, op.allowed_fieldtypes)

        field = 'Last_name'
        value = 'sire'
        self.assertEqual(
            _('«{field}» starts with {values} (case insensitive)').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value]),
        )

    def test_istartswith_accept(self):
        accept = operators.IStartsWithOperator().accept
        self.assertIs(accept(field_value='Evil corp', values=['Evil']), True)
        self.assertIs(accept(field_value='Evil corp', values=['evil']), True)
        self.assertIs(accept(field_value='Evil corp', values=['corp']), False)

        self.assertIs(accept(field_value='We are not Evil', values=['Evil']), False)
        self.assertIs(accept(field_value=None, values=['evil']), False)

    def test_istartswith_not(self):
        op = self.get_operator(operators.ISTARTSWITH_NOT)
        self.assertIsInstance(op, operators.IStartswithNotOperator)
        self.assertEqual(_('Does not start with (case insensitive)'), op.verbose_name)
        self.assertEqual('{}__istartswith', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertTrue(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING, op.allowed_fieldtypes)

        field = 'Last_name'
        value = 'sire'
        self.assertEqual(
            _('«{field}» does not start with {values} (case insensitive)').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value]),
        )

    def test_istartswith_not_accept(self):
        accept = operators.IStartswithNotOperator().accept
        self.assertIs(accept(field_value='Evil corp', values=['Evil']), False)
        self.assertIs(accept(field_value='Evil corp', values=['evil']), False)
        self.assertIs(accept(field_value='Evil corp', values=['corp']), True)

        self.assertIs(accept(field_value='Evil inc.', values=['Evil']), False)

    def test_endswith(self):
        op = self.get_operator(operators.ENDSWITH)
        self.assertIsInstance(op, operators.EndsWithOperator)
        self.assertEqual(_('Ends with'), op.verbose_name)
        self.assertEqual('{}__endswith', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertFalse(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING, op.allowed_fieldtypes)

        field = 'Last_name'
        value = 'sson'
        self.assertEqual(
            _('«{field}» ends with {values}').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value]),
        )

    def test_endswith_accept(self):
        accept = operators.EndsWithOperator().accept
        self.assertIs(accept(field_value='Evil corp',    values=['corp']), True)
        self.assertIs(accept(field_value='Evil corp',    values=['Evil']), False)
        self.assertIs(accept(field_value='Evil company', values=['corp']), False)

        # Case sensitivity ---
        with patch('creme.creme_core.core.entity_filter.operators.is_db_like_case_sensitive',
                   return_value=True) as mock_sensitive:
            accepted_sensitive = accept(field_value='Evil corp', values=['CORP'])

        mock_sensitive.assert_called_once_with()
        self.assertIs(accepted_sensitive, False)

        with patch('creme.creme_core.core.entity_filter.operators.is_db_like_case_sensitive',
                   return_value=False) as mock_no_sensitive:
            accepted_no_sensitive = accept(field_value='Evil corp', values=['CORP'])

        mock_no_sensitive.assert_called_once_with()
        self.assertIs(accepted_no_sensitive, True)

        self.assertIs(accept(field_value=None, values=['@corp']), False)

    def test_endswith_not(self):
        op = self.get_operator(operators.ENDSWITH_NOT)
        self.assertIsInstance(op, operators.EndsWithNotOperator)
        self.assertEqual(_('Does not end with'), op.verbose_name)
        self.assertEqual('{}__endswith', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertTrue(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING, op.allowed_fieldtypes)

        field = 'Last_name'
        value = 'sson'
        self.assertEqual(
            _('«{field}» does not end with {values}').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value])
        )

    def test_endswith_not_accept(self):
        accept = self.get_operator(operators.ENDSWITH_NOT).accept
        self.assertIs(accept(field_value='Evil corp',    values=['corp']), False)
        self.assertIs(accept(field_value='Evil corp',    values=['Evil']), True)
        self.assertIs(accept(field_value='Evil company', values=['corp']), True)

    def test_iendswith(self):
        op = self.get_operator(operators.IENDSWITH)
        self.assertIsInstance(op, operators.IEndsWithOperator)
        self.assertEqual(_('Ends with (case insensitive)'), op.verbose_name)
        self.assertEqual('{}__iendswith', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertFalse(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING, op.allowed_fieldtypes)

        field = 'Last_name'
        value = 'sSoN'
        self.assertEqual(
            _('«{field}» ends with {values} (case insensitive)').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value]),
        )

    def test_iendswith_accept(self):
        op = operators.IEndsWithOperator()
        self.assertIs(op.accept(field_value='Evil corp', values=['corp']), True)
        self.assertIs(op.accept(field_value='Evil corp', values=['CORP']), True)
        self.assertIs(op.accept(field_value='Evil corp', values=['Evil']), False)
        self.assertIs(op.accept(field_value='Evil INC',  values=['inc']),  True)
        self.assertIs(op.accept(field_value='Evil INC',  values=['corp']), False)

        self.assertIs(op.accept(field_value=None, values=['@corp']), False)

    def test_iendswith_not(self):
        op = self.get_operator(operators.IENDSWITH_NOT)
        self.assertIsInstance(op, operators.IEndsWithNotOperator)
        self.assertEqual(_('Does not end with (case insensitive)'), op.verbose_name)
        self.assertEqual('{}__iendswith', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertTrue(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING, op.allowed_fieldtypes)

        field = 'Last_name'
        value = 'sSoN'
        self.assertEqual(
            _('«{field}» does not end with {values} (case insensitive)').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value]),
        )

    def test_iendswith_not_accept(self):
        accept = operators.IEndsWithNotOperator().accept
        self.assertIs(accept(field_value='Evil corp', values=['corp']), False)
        self.assertIs(accept(field_value='Evil corp', values=['CORP']), False)
        self.assertIs(accept(field_value='Evil corp', values=['Evil']), True)
        self.assertIs(accept(field_value='Evil INC',  values=['inc']),  False)
        self.assertIs(accept(field_value='Evil INC',  values=['corp']), True)
