# -*- coding: utf-8 -*-

try:
    from creme_core.core.function_field import FunctionField, FunctionFieldsManager
    from creme_core.tests.base import CremeTestCase
except Exception as e:
    print 'Error:', e


__all__ = ('FunctionFieldsTestCase',)


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
