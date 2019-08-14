# -*- coding: utf-8 -*-

try:
    from creme.creme_core.core.entity_filter import operators
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

        # TODO: get_q
        # TODO: validate_field_values

    # TODO: def test_equals(self):
    # TODO: def test_is_empty(self):
    # TODO: def test_range(self):
