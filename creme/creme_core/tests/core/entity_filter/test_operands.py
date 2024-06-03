from django.core.exceptions import ValidationError

from creme.creme_core.core.entity_filter import (
    EF_REGULAR,
    entity_filter_registries,
    operands,
)
from creme.creme_core.models import FakeContact
from creme.creme_core.tests.base import CremeTestCase


class OperandTestCase(CremeTestCase):
    def test_current_user01(self):
        "Registered."
        operand = entity_filter_registries[EF_REGULAR].get_operand(
            type_id=operands.CurrentUserOperand.type_id,
            user=None,
        )
        self.assertIsInstance(operand, operands.CurrentUserOperand)
        self.assertIsNone(operand.user)

    def test_current_user02(self):
        "Resolve with None."
        operand = operands.CurrentUserOperand(user=None)
        self.assertIsNone(operand.user)
        self.assertIsNone(operand.resolve())

    def test_current_user03(self):
        "Resolve with no team."
        user = self.create_user()

        operand = operands.CurrentUserOperand(user=user)
        self.assertEqual(user, operand.user)
        self.assertEqual(user.id, operand.resolve())

    def test_current_user04(self):
        "Resolve with team."
        user = self.create_user(0)
        team = self.create_team('Noir', user)

        operand = operands.CurrentUserOperand(user=user)
        self.assertEqual(user, operand.user)
        self.assertCountEqual([user.id, team.id], operand.resolve())

    def test_current_user05(self):
        "Validate."
        operand = operands.CurrentUserOperand(user=None)

        get_field = FakeContact._meta.get_field
        field1 = get_field('first_name')
        self.assertIsNone(operand.validate(field=field1, value='foo'))
        self.assertIsNone(operand.validate(field=field1, value=operand.type_id))

        with self.assertRaises(ValidationError):
            operand.validate(field=get_field('sector'), value=operand.type_id)

        self.assertIsNone(
            operand.validate(field=get_field('user'), value=operand.type_id),
        )
