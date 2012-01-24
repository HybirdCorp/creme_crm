# -*- coding: utf-8 -*-

try:
    from creme_core.core.function_field import FunctionField, FunctionFieldsManager
    from creme_core.core.batch_process import OPERATOR_MAP, BatchAction
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact
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


class _BatchTestCase(CremeTestCase):
    def get_operator_or_die(self, op_id):
        operator = OPERATOR_MAP.get(op_id)
        if operator is None:
            self.fail('The operator %s can not be found' % op_id)

        return operator


class BatchOperatorTestCase(_BatchTestCase):
    def test_upper(self):
        op = self.get_operator_or_die('upper')
        self.assertFalse(op.need_arg)
        self.assertEqual('GALLY', op('gally'))

    def test_lower(self):
        op = self.get_operator_or_die('lower')
        self.assertFalse(op.need_arg)
        self.assertEqual('gally', op('GALLY'))

    def test_title(self):
        op = self.get_operator_or_die('title')
        self.assertFalse(op.need_arg)
        self.assertEqual('Gally', op('gally'))

    def test_prefix(self):
        op = self.get_operator_or_die('prefix')
        self.assertTrue(op.need_arg)
        self.assertEqual('My Gally', op('Gally', 'My '))

    def test_suffix(self):
        op = self.get_operator_or_die('suffix')
        self.assertTrue(op.need_arg)
        self.assertEqual('Gally my love', op('Gally', ' my love'))

    def test_remove_substring(self):
        op = self.get_operator_or_die('rm_substr')
        self.assertTrue(op.need_arg)
        fieldval = 'Gally the battle angel'
        self.assertEqual('Gally the angel', op(fieldval, 'battle '))
        self.assertEqual(fieldval, op(fieldval, 'evil '))

    #def test_remove_start(self):
        #op = self.get_operator_or_die('rm_start')
        #self.assertTrue(op.need_arg)
        #self.assertEqual('Gally', op('GGGally', 2))


class BatchActionTestCase(_BatchTestCase):
    def test_changed01(self):
        baction = BatchAction('first_name', self.get_operator_or_die('upper'), value='')
        haruhi = Contact(first_name='Haruhi', last_name='Suzumiya')
        self.assertTrue(baction(haruhi))
        self.assertEqual('HARUHI', haruhi.first_name)

    def test_changed02(self):
        baction = BatchAction('last_name', self.get_operator_or_die('rm_substr'), value='Foobar')
        haruhi = Contact(first_name='Haruhi', last_name='Suzumiya')
        self.assertFalse(baction(haruhi))
        self.assertEqual('Suzumiya', haruhi.last_name)
