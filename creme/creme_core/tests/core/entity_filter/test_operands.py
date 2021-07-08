# -*- coding: utf-8 -*-

from django.core.exceptions import ValidationError

from creme.creme_core.core.entity_filter import (
    EF_USER,
    entity_filter_registries,
    operands,
)
from creme.creme_core.models import CremeUser, FakeContact
from creme.creme_core.tests.base import CremeTestCase


class OperandTestCase(CremeTestCase):
    def test_current_user01(self):
        "Registered."
        operand = entity_filter_registries[EF_USER].get_operand(
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
        user = CremeUser.objects.create(
            username='kirika', email='kirika@noir.jp',
            first_name='Kirika', last_name='Yumura',
        )

        operand = operands.CurrentUserOperand(user=user)
        self.assertEqual(user, operand.user)
        self.assertEqual(user.id, operand.resolve())

    def test_current_user04(self):
        "Resolve with team."
        create_user = CremeUser.objects.create
        user = create_user(
            username='kirika', email='kirika@noir.jp',
            first_name='Kirika', last_name='Yumura',
        )
        team = create_user(username='Noir', is_team=True)
        team.teammates = [user]

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
