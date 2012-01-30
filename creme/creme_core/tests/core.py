# -*- coding: utf-8 -*-

try:
    from django.db import models
    from django.utils.translation import ugettext as _

    from creme_core.core.function_field import FunctionField, FunctionFieldsManager
    from creme_core.core.batch_process import batch_operator_manager, BatchAction
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact, Organisation
except Exception as e:
    print 'Error:', e


__all__ = ('FunctionFieldsTestCase', 'BatchOperatorTestCase', 'BatchActionTestCase')


class FunctionFieldsTestCase(CremeTestCase):
    def test_manager01(self): #constructor with no args, add() & get() methods
        ffm = FunctionFieldsManager()
        self.assertEqual([], list(ffm))

        fname01 = "name01"
        fname02 = "name02"

        class TestFunctionField01(FunctionField):
            name         = fname01
            verbose_name = "Verbose name 01"

        class TestFunctionField02(FunctionField):
            name         = fname02
            verbose_name = "Verbose name 02"

        ff01 = TestFunctionField01()
        ff02 = TestFunctionField02()

        self.assertIsNone(ffm.get(fname01))

        ffm.add(ff01, ff02)
        self.assertIs(ff01, ffm.get(fname01))
        self.assertIs(ff02, ffm.get(fname02))
        self.assertEqual([ff01, ff02], sorted(ffm, key=lambda ff: ff.name))

    def test_manager02(self): #constructor with args
        fname01 = "name01"
        fname02 = "name02"

        class TestFunctionField01(FunctionField):
            name         = fname01
            verbose_name = "Verbose name 01"

        class TestFunctionField02(FunctionField):
            name         = fname02
            verbose_name = "Verbose name 02"

        ff01 = TestFunctionField01()
        ff02 = TestFunctionField02()

        ffm = FunctionFieldsManager(ff01, ff02)
        self.assertIs(ff01, ffm.get(fname01))
        self.assertIs(ff02, ffm.get(fname02))
        self.assertEqual([ff01, ff02], sorted(ffm, key=lambda ff: ff.name))

    def test_manager03(self): #new() method
        fname01 = "name01"
        fname02 = "name02"

        class TestFunctionField01(FunctionField):
            name         = fname01
            verbose_name = "Verbose name 01"

        class TestFunctionField02(FunctionField):
            name         = fname02
            verbose_name = "Verbose name 02"

        ff01 = TestFunctionField01()
        ff02 = TestFunctionField02()

        ffm01 = FunctionFieldsManager(ff01)
        ffm02 = ffm01.new(ff02)

        self.assertIs(ff01, ffm01.get(fname01))
        self.assertIsNone(ffm01.get(fname02))
        self.assertEqual([ff01], list(ffm01))

        self.assertIs(ff01, ffm02.get(fname01))
        self.assertIs(ff02, ffm02.get(fname02))
        self.assertEqual([ff01, ff02], sorted(ffm02, key=lambda ff: ff.name))

    def test_manager04(self): #new() method + add() on "base instance"
        fname01 = "name01"
        fname02 = "name02"

        class TestFunctionField01(FunctionField):
            name         = fname01
            verbose_name = "Verbose name 01"

        class TestFunctionField02(FunctionField):
            name         = fname02
            verbose_name = "Verbose name 02"

        ff01 = TestFunctionField01()
        ff02 = TestFunctionField02()

        ffm01 = FunctionFieldsManager()
        ffm02 = ffm01.new(ff02)

        ffm01.add(ff01) # <== added after new()

        self.assertIs(ff01, ffm01.get(fname01))
        self.assertIsNone(ffm01.get(fname02))
        self.assertEqual([ff01], list(ffm01))

        self.assertIs(ff02, ffm02.get(fname02))
        self.assertIs(ff01, ffm02.get(fname01)) # ok ?
        self.assertEqual([ff01, ff02], sorted(ffm02, key=lambda ff: ff.name))


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
        ops = set((op_name, unicode(op)) for op_name, op in batch_operator_manager.operators(models.CharField))
        self.assertIn(('upper', _('To upper case')), ops)
        self.assertIn(('lower', _('To lower case')), ops)
        self.assertNotIn('add_int', (e[0] for e in ops))

    def test_operators02(self):
        ops = set((op_name, unicode(op)) for op_name, op in batch_operator_manager.operators(models.IntegerField))
        self.assertIn(('add_int', _('Add')), ops)
        self.assertNotIn('prefix', (e[0] for e in ops))

    def test_operators03(self):
        ops = set((op_name, unicode(op)) for op_name, op in batch_operator_manager.operators())
        self.assertIn(('mul_int', _('Multiply')), ops)
        self.assertIn(('suffix',  _('Suffix')), ops)


class BatchActionTestCase(CremeTestCase):
    def test_changed01(self):
        baction = BatchAction(Contact, 'first_name', 'upper', value='')
        haruhi = Contact(first_name='Haruhi', last_name='Suzumiya')
        self.assertTrue(baction(haruhi))
        self.assertEqual('HARUHI', haruhi.first_name)

    def test_changed02(self):
        baction = BatchAction(Organisation, 'name', 'rm_substr', value='Foobar')
        name = 'SOS no Dan'
        sos = Organisation(name=name)
        self.assertFalse(baction(sos))
        self.assertEqual(name, sos.name)

    def test_cast(self):
        baction = BatchAction(Contact, 'last_name', 'rm_start', value='3')
        haruhi = Contact(first_name='Haruhi', last_name='Suzumiya')
        baction(haruhi)
        self.assertEqual('umiya', haruhi.last_name)

    def test_operand_error(self):
        with self.assertRaises(BatchAction.ValueError) as cm:
            BatchAction(Contact, 'last_name', 'rm_start', value='three') #not int

        self.assertEqual(_('%(operator)s : %(message)s.') % {
                                'operator': _('Remove the start (N characters)'),
                                'message':  _('enter a whole number'),
                            },
                         unicode(cm.exception)
                        )

        with self.assertRaises(BatchAction.ValueError) as cm:
            BatchAction(Contact, 'last_name', 'rm_end', value='-3') #not positive

        self.assertEqual(_('%(operator)s : %(message)s.') % {
                                'operator': _('Remove the end (N characters)'),
                                'message':  _('enter a positive number'),
                            },
                         unicode(cm.exception)
                        )
