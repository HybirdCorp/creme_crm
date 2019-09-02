# -*- coding: utf-8 -*-

try:
    from datetime import date

    from django.db.models.query_utils import Q
    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.core.entity_filter import operators
    from creme.creme_core.models import FakeOrganisation, FakeContact
    from creme.creme_core.tests.base import CremeTestCase
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class OperatorTestCase(CremeTestCase):
    def test_base(self):
        name = 'Foo'
        pattern = '{}__foobar'
        op = operators.ConditionOperator(name=name, key_pattern=pattern)
        self.assertEqual(name, op.name)
        self.assertEqual((), op.allowed_fieldtypes)
        self.assertIs(op.exclude, False)
        self.assertEqual(pattern, op.key_pattern)
        self.assertIs(op.accept_subpart, True)
        self.assertEqual(name, str(op))

    def test_get_q1(self):
        op = operators.ConditionOperator(name='Contains', key_pattern='{}__contains')
        self.assertQEqual(
            Q(name__contains='Acme'),
            op.get_q(model=FakeOrganisation, field_name='name', values=['Acme'])
        )

    def test_get_q2(self):
        "Other pattern, several values."
        op = operators.ConditionOperator(name='Ends with', key_pattern='{}__endswith')
        self.assertQEqual(
            Q(last_name__endswith='foo') | Q(last_name__endswith='bar'),
            op.get_q(model=FakeContact,
                     field_name='last_name', values=['foo', 'bar'],
                    )
        )

    def test_equals(self):
        op = operators.EqualsOperator(name='Equals')
        self.assertFalse(op.accept_subpart)
        self.assertIs(op.exclude, False)
        self.assertSetEqual({
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
            fmt(field=field,
                values=fmt_value(enum_value=value1),
               ),
            op.description(field_vname=field, values=[value1])
        )

        value2 = 28
        self.assertEqual(
            fmt(field=field,
                values=_('{first} or {last}').format(
                    first=fmt_value(enum_value=value1),
                    last=fmt_value(enum_value=value2),
                ),
               ),
            op.description(field_vname=field, values=[value1, value2])
        )

        value3 = 42
        self.assertEqual(
            fmt(field=field,
                values=_('{first} or {last}').format(
                    first='{}, {}'.format(
                        fmt_value(enum_value=value1),
                        fmt_value(enum_value=value2),
                    ),
                    last=fmt_value(enum_value=value3),
                ),
               ),
            op.description(field_vname=field, values=[value1, value2, value3])
        )

    def test_equals_get_q(self):
        op = operators.EqualsOperator(name='Equals')
        self.assertQEqual(
            Q(name__exact='Acme') | Q(name__exact='Akme'),
            op.get_q(model=FakeOrganisation,
                     field_name='name',
                     values=['Acme', 'Akme'],
                    )
        )
        self.assertQEqual(
            Q(last_name__in=['Spiegel', 'Black']),
            op.get_q(model=FakeContact,
                     field_name='last_name',
                     values=[['Spiegel', 'Black']],
                    )
        )

    def test_equals_not(self):
        op = operators.EqualsOperator(name='Equals', exclude=True)
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
                values=_('{first} or «{last}»').format(
                    first=fmt_value(enum_value=value1),
                    last=value2,
                ),
             ),
            op.description(field_vname=field, values=[value1, value2])
        )

    def test_is_empty(self):
        op = operators.IsEmptyOperator(name='Is empty')
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
            op.description(field_vname=field, values=[True])
        )
        self.assertEqual(
            _('«{field}» is not empty').format(field=field),
            op.description(field_vname=field, values=[False])
        )

        self.assertEqual(
            _('«{field}» is empty').format(field=field),
            op.description(field_vname=field, values=['True'])  # not Bool
        )

    def test_is_empty_get_q(self):
        op = operators.IsEmptyOperator(name='Is empty')
        self.assertQEqual(
            Q(sector__isnull=True),
            op.get_q(model=FakeOrganisation,
                     field_name='sector',
                     values=[True],
                    )
        )
        self.assertQEqual(
            Q(last_name__isnull=True) | Q(last_name=''),
            op.get_q(model=FakeContact,
                     field_name='last_name',
                     values=[True],
                    )
        )

        q3 = Q(last_name__isnull=True) | Q(last_name='')
        q3.negate()
        self.assertQEqual(
            q3,
            op.get_q(model=FakeContact,
                     field_name='last_name',
                     values=[False],
                    )
        )

    def test_range(self):
        op = operators.RangeOperator(name='Range')
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

    def test_range_get_q(self):
        op = operators.RangeOperator(name='Range')
        self.assertQEqual(
            Q(capital__range=[1000, 10000]),
            op.get_q(model=FakeOrganisation,
                     field_name='capital',
                     values=[[1000, 10000]],
                    )
        )

    def test_gt(self):
        op = operators.OPERATORS[operators.GT]
        self.assertEqual(_('>'), op.name)
        self.assertIs(op.exclude, False)
        self.assertEqual('{}__gt', op.key_pattern)
        self.assertIs(op.accept_subpart, True)
        self.assertEqual(operators.FIELDTYPES_ORDERABLE,
                         op.allowed_fieldtypes
                        )

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
                values=_('{first} or «{last}»').format(
                    first=fmt_value(enum_value=value1),
                    last=value2,
                ),
            ),
            op.description(field_vname=field, values=[value1, value2])
        )

    def test_gte(self):
        op = operators.OPERATORS[operators.GTE]
        # self.assertEqual(_('>='), op.name)
        self.assertEqual(_('≥'), op.name)
        self.assertIs(op.exclude, False)
        self.assertEqual('{}__gte', op.key_pattern)
        self.assertIs(op.accept_subpart, True)
        self.assertEqual(operators.FIELDTYPES_ORDERABLE,
                         op.allowed_fieldtypes
                        )

        field = 'order'
        value1 = 6
        self.assertEqual(
            _('«{field}» is greater or equal to {values}').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value1),
            ),
            op.description(field_vname=field, values=[value1])
        )

    def test_lt(self):
        op = operators.OPERATORS[operators.LT]
        self.assertEqual(_('<'), op.name)
        self.assertIs(op.exclude, False)
        self.assertEqual('{}__lt', op.key_pattern)
        self.assertIs(op.accept_subpart, True)
        self.assertEqual(operators.FIELDTYPES_ORDERABLE,
                         op.allowed_fieldtypes
                        )

        field = 'order'
        value = 8
        self.assertEqual(
            _('«{field}» is lesser than {values}').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value])
        )

    def test_lte(self):
        op = operators.OPERATORS[operators.LTE]
        # self.assertEqual(_('<='), op.name)
        self.assertEqual(_('≤'), op.name)
        self.assertIs(op.exclude, False)
        self.assertEqual('{}__lte', op.key_pattern)
        self.assertIs(op.accept_subpart, True)
        self.assertEqual(operators.FIELDTYPES_ORDERABLE,
                         op.allowed_fieldtypes
                        )

        field = 'size'
        value = 68
        self.assertEqual(
            _('«{field}» is lesser or equal to {values}').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value])
        )

    def test_iequals(self):
        op = operators.OPERATORS[operators.IEQUALS]
        self.assertEqual(_('Equals (case insensitive)'), op.name)
        self.assertEqual('{}__iexact',                   op.key_pattern)
        self.assertFalse(op.accept_subpart)
        self.assertFalse(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING,
                         op.allowed_fieldtypes
                        )

        field = 'name'
        self.assertEqual('??', op.description(field_vname=field, values=[]))

        value = 'Spike'
        self.assertEqual(
            _('«{field}» is equal to {values} (case insensitive)').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value])
        )

    def test_iequals_not(self):
        op = operators.OPERATORS[operators.IEQUALS_NOT]
        self.assertEqual(_('Does not equal (case insensitive)'), op.name)
        self.assertEqual('{}__iexact',                           op.key_pattern)
        self.assertFalse(op.accept_subpart)
        self.assertTrue(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING,
                         op.allowed_fieldtypes
                        )

        field = 'first_name'
        value = 'Spike'
        self.assertEqual(
            _('«{field}» is different from {values} (case insensitive)').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value])
        )

    def test_contains(self):
        op = operators.OPERATORS[operators.CONTAINS]
        self.assertEqual(_('Contains'), op.name)
        self.assertEqual('{}__contains', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertFalse(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING,
                         op.allowed_fieldtypes
                        )

        field = 'info'
        value = 'important'
        self.assertEqual(
            _('«{field}» contains {values}').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value])
        )

    def test_contains_not(self):
        op = operators.OPERATORS[operators.CONTAINS_NOT]
        self.assertEqual(_('Does not contain'), op.name)
        self.assertEqual('{}__contains', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertTrue(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING,
                         op.allowed_fieldtypes
                        )

        field = 'Info'
        value = 'ignore'
        self.assertEqual(
            _('«{field}» does not contain {values}').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value])
        )

    def test_icontains(self):
        op = operators.OPERATORS[operators.ICONTAINS]
        self.assertEqual(_('Contains (case insensitive)'), op.name)
        self.assertEqual('{}__icontains', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertFalse(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING,
                         op.allowed_fieldtypes
                        )

        field = 'Information'
        value = 'IMPORTANT'
        self.assertEqual(
            _('«{field}» contains {values} (case insensitive)').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value])
        )

    def test_icontains_not(self):
        op = operators.OPERATORS[operators.ICONTAINS_NOT]
        self.assertEqual(_('Does not contain (case insensitive)'), op.name)
        self.assertEqual('{}__icontains', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertTrue(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING,
                         op.allowed_fieldtypes
                        )

        field = 'Information'
        value = 'IgNoRe'
        self.assertEqual(
            _('«{field}» does not contain {values} (case insensitive)').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value])
        )

    def test_startswith(self):
        op = operators.OPERATORS[operators.STARTSWITH]
        self.assertEqual(_('Starts with'), op.name)
        self.assertEqual('{}__startswith', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertFalse(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING,
                         op.allowed_fieldtypes
                        )

        field = 'Last_name'
        value = 'sire'
        self.assertEqual(
            _('«{field}» starts with {values}').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value])
        )

    def test_startswith_not(self):
        op = operators.OPERATORS[operators.STARTSWITH_NOT]
        self.assertEqual(_('Does not start with'), op.name)
        self.assertEqual('{}__startswith', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertTrue(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING,
                         op.allowed_fieldtypes
                        )

        field = 'Last_name'
        value = 'sire'
        self.assertEqual(
            _('«{field}» does not start with {values}').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value])
        )

    def test_istartswith(self):
        op = operators.OPERATORS[operators.ISTARTSWITH]
        self.assertEqual(_('Starts with (case insensitive)'), op.name)
        self.assertEqual('{}__istartswith', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertFalse(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING,
                         op.allowed_fieldtypes
                        )

        field = 'Last_name'
        value = 'sire'
        self.assertEqual(
            _('«{field}» starts with {values} (case insensitive)').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value])
        )

    def test_istartswith_not(self):
        op = operators.OPERATORS[operators.ISTARTSWITH_NOT]
        self.assertEqual(_('Does not start with (case insensitive)'), op.name)
        self.assertEqual('{}__istartswith', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertTrue(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING,
                         op.allowed_fieldtypes
                        )

        field = 'Last_name'
        value = 'sire'
        self.assertEqual(
            _('«{field}» does not start with {values} (case insensitive)').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value])
        )

    def test_endswith(self):
        op = operators.OPERATORS[operators.ENDSWITH]
        self.assertEqual(_('Ends with'), op.name)
        self.assertEqual('{}__endswith', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertFalse(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING,
                         op.allowed_fieldtypes
                        )

        field = 'Last_name'
        value = 'sson'
        self.assertEqual(
            _('«{field}» ends with {values}').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value])
        )

    def test_endswith_not(self):
        op = operators.OPERATORS[operators.ENDSWITH_NOT]
        self.assertEqual(_('Does not end with'), op.name)
        self.assertEqual('{}__endswith', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertTrue(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING,
                         op.allowed_fieldtypes
                        )

        field = 'Last_name'
        value = 'sson'
        self.assertEqual(
            _('«{field}» does not end with {values}').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value])
        )

    def test_iendswith(self):
        op = operators.OPERATORS[operators.IENDSWITH]
        self.assertEqual(_('Ends with (case insensitive)'), op.name)
        self.assertEqual('{}__iendswith', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertFalse(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING,
                         op.allowed_fieldtypes
                        )

        field = 'Last_name'
        value = 'sSoN'
        self.assertEqual(
            _('«{field}» ends with {values} (case insensitive)').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value])
        )

    def test_iendswith_not(self):
        op = operators.OPERATORS[operators.IENDSWITH_NOT]
        self.assertEqual(_('Does not end with (case insensitive)'), op.name)
        self.assertEqual('{}__iendswith', op.key_pattern)
        self.assertTrue(op.accept_subpart)
        self.assertTrue(op.exclude)
        self.assertEqual(operators.FIELDTYPES_STRING,
                         op.allowed_fieldtypes
                        )

        field = 'Last_name'
        value = 'sSoN'
        self.assertEqual(
            _('«{field}» does not end with {values} (case insensitive)').format(
                field=field,
                values=_('«{enum_value}»').format(enum_value=value),
            ),
            op.description(field_vname=field, values=[value])
        )

    # TODO: validate_field_values x N
