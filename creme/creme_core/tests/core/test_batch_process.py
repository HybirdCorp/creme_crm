from django.db import models
from django.utils.translation import gettext as _

from creme.creme_core.core.batch_process import (
    BatchAction,
    batch_operator_manager,
)
from creme.creme_core.models import FakeContact

from ..base import CremeTestCase


class BatchOperatorTestCase(CremeTestCase):
    def test_upper(self):
        op = batch_operator_manager.get(models.CharField, 'upper')
        self.assertFalse(op.need_arg)
        self.assertEqual('GALLY', op('gally'))

    def test_lower(self):
        op = batch_operator_manager.get(models.CharField, 'lower')
        self.assertFalse(op.need_arg)
        self.assertEqual('gally', op('GALLY'))

    def test_title(self):
        op = batch_operator_manager.get(models.CharField, 'title')
        self.assertFalse(op.need_arg)
        self.assertEqual('Gally', op('gally'))

    def test_prefix(self):
        op = batch_operator_manager.get(models.CharField, 'prefix')
        self.assertTrue(op.need_arg)
        self.assertEqual('My Gally', op('Gally', 'My '))

    def test_suffix(self):
        op = batch_operator_manager.get(models.CharField, 'suffix')
        self.assertTrue(op.need_arg)
        self.assertEqual('Gally my love', op('Gally', ' my love'))

    def test_remove_substring(self):
        op = batch_operator_manager.get(models.CharField, 'rm_substr')
        self.assertTrue(op.need_arg)
        fieldval = 'Gally the battle angel'
        self.assertEqual('Gally the angel', op(fieldval, 'battle '))
        self.assertEqual(fieldval, op(fieldval, 'evil '))

    def test_remove_start(self):
        op = batch_operator_manager.get(models.CharField, 'rm_start')
        self.assertTrue(op.need_arg)
        self.assertEqual('Gally', op('GGGally', 2))
        self.assertEqual('',      op('Gally',   op.cast('10')))

    def test_remove_end(self):
        op = batch_operator_manager.get(models.CharField, 'rm_end')
        self.assertTrue(op.need_arg)
        self.assertEqual('Gally', op('Gallyyy', 2))
        self.assertEqual('',      op('Gally',   op.cast('10')))

    def test_add_int(self):
        op = batch_operator_manager.get(models.IntegerField, 'add_int')
        self.assertEqual(3, op(1, 2))
        self.assertEqual(5, op(4, op.cast('1')))

    def test_substract_int(self):
        op = batch_operator_manager.get(models.IntegerField, 'sub_int')
        self.assertEqual(1, op(3, 2))
        self.assertEqual(3, op(4, op.cast('1')))

    def test_multiply_int(self):
        op = batch_operator_manager.get(models.IntegerField, 'mul_int')
        self.assertEqual(6, op(3, 2))
        self.assertEqual(8, op(2, op.cast('4')))

    def test_divide_int(self):
        op = batch_operator_manager.get(models.IntegerField, 'div_int')
        self.assertEqual(3, op(6, 2))
        self.assertEqual(2, op(9, op.cast('4')))

    def test_operators01(self):
        ops = [
            (op_name, str(op))
            for op_name, op in batch_operator_manager.operators(models.CharField)
        ]
        self.assertInChoices(value='upper', label=_('To upper case'), choices=ops)
        self.assertInChoices(value='lower', label=_('To lower case'), choices=ops)
        self.assertNotInChoices(value='add_int', choices=ops)

    def test_operators02(self):
        ops = [
            (op_name, str(op))
            for op_name, op in batch_operator_manager.operators(models.IntegerField)
        ]
        self.assertInChoices(value='add_int', label=_('Add'), choices=ops)
        self.assertNotInChoices(value='prefix', choices=ops)

    def test_operators03(self):
        ops = [(op_name, str(op)) for op_name, op in batch_operator_manager.operators()]
        self.assertInChoices(value='mul_int', label=_('Multiply'), choices=ops)
        self.assertInChoices(value='suffix',  label=_('Suffix'),   choices=ops)


class BatchActionTestCase(CremeTestCase):
    def test_changed01(self):
        baction = BatchAction(FakeContact, 'first_name', 'upper', value='')
        haruhi = FakeContact(first_name='Haruhi', last_name='Suzumiya')
        self.assertTrue(baction(haruhi))
        self.assertEqual('HARUHI', haruhi.first_name)

    def test_changed02(self):
        baction = BatchAction(FakeContact, 'last_name', 'rm_substr', value='Foobar')
        first_name = 'Haruhi'
        last_name = 'Suzumiya'
        haruhi = FakeContact(first_name=first_name, last_name=last_name)
        self.assertFalse(baction(haruhi))
        self.assertEqual(last_name,  haruhi.last_name)
        self.assertEqual(first_name, haruhi.first_name)

    def test_cast(self):
        baction = BatchAction(FakeContact, 'last_name', 'rm_start', value='3')
        haruhi = FakeContact(first_name='Haruhi', last_name='Suzumiya')
        baction(haruhi)
        self.assertEqual('umiya', haruhi.last_name)

    def test_null_field(self):
        baction = BatchAction(FakeContact, 'first_name', 'upper', value='')
        haruhi = FakeContact(first_name=None, last_name='Suzumiya')
        self.assertFalse(baction(haruhi))
        self.assertIsNone(haruhi.first_name)

    def test_operand_error(self):
        with self.assertRaises(BatchAction.ValueError) as cm:
            BatchAction(FakeContact, 'last_name', 'rm_start', value='three')  # Not int

        self.assertEqual(
            _('{operator}: {message}.').format(
                operator=_('Remove the start (N characters)'),
                message=_('enter a whole number'),
            ),
            str(cm.exception)
        )

        with self.assertRaises(BatchAction.ValueError) as cm:
            BatchAction(FakeContact, 'last_name', 'rm_end', value='-3')  # Not positive

        self.assertEqual(
            _('{operator}: {message}.').format(
                operator=_('Remove the end (N characters)'),
                message=_('enter a positive number'),
            ),
            str(cm.exception)
        )

    def test_unicode01(self):
        baction = BatchAction(FakeContact, 'first_name', 'upper', value='')
        self.assertEqual(
            _('{field} ➔ {operator}').format(
                field=_('First name'),
                operator=_('To upper case'),
            ),
            str(baction)
        )

    def test_unicode02(self):
        "With argument"
        value = 'Foobarbaz'
        baction = BatchAction(FakeContact, 'last_name', 'rm_substr', value=value)
        self.assertEqual(
            _('{field} ➔ {operator}: «{value}»').format(
                field=_('Last name'),
                operator=_('Remove a sub-string'),
                value=value,
            ),
            str(baction)
        )
