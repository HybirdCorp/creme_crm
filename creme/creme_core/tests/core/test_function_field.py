# -*- coding: utf-8 -*-

try:
    from ..base import CremeTestCase

    from creme.creme_core.core.function_field import FunctionField, _FunctionFieldRegistry  # FunctionFieldsManager
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class FunctionFieldsTestCase(CremeTestCase):
    # def test_manager01(self):
    #     "Constructor with no args, add() & get() methods"
    #     ffm = FunctionFieldsManager()
    #     self.assertFalse(list(ffm))
    #
    #     fname01 = 'name01'
    #     fname02 = 'name02'
    #
    #     class TestFunctionField01(FunctionField):
    #         name         = fname01
    #         verbose_name = 'Verbose name 01'
    #
    #     class TestFunctionField02(FunctionField):
    #         name         = fname02
    #         verbose_name = 'Verbose name 02'
    #
    #     ff01 = TestFunctionField01()
    #     ff02 = TestFunctionField02()
    #
    #     self.assertIsNone(ffm.get(fname01))
    #
    #     ffm.add(ff01, ff02)
    #     self.assertIs(ff01, ffm.get(fname01))
    #     self.assertIs(ff02, ffm.get(fname02))
    #     self.assertEqual([ff01, ff02], sorted(ffm, key=lambda ff: ff.name))

    # def test_manager02(self):
    #     "Constructor with args"
    #     fname01 = 'name01'
    #     fname02 = 'name02'
    #
    #     class TestFunctionField01(FunctionField):
    #         name         = fname01
    #         verbose_name = 'Verbose name 01'
    #
    #     class TestFunctionField02(FunctionField):
    #         name         = fname02
    #         verbose_name = "Verbose name 02"
    #
    #     ff01 = TestFunctionField01()
    #     ff02 = TestFunctionField02()
    #
    #     ffm = FunctionFieldsManager(ff01, ff02)
    #     self.assertIs(ff01, ffm.get(fname01))
    #     self.assertIs(ff02, ffm.get(fname02))
    #     self.assertEqual([ff01, ff02], sorted(ffm, key=lambda ff: ff.name))

    # def test_manager03(self):
    #     "new() method"
    #     fname01 = 'name01'
    #     fname02 = 'name02'
    #
    #     class TestFunctionField01(FunctionField):
    #         name         = fname01
    #         verbose_name = 'Verbose name 01'
    #
    #     class TestFunctionField02(FunctionField):
    #         name         = fname02
    #         verbose_name = 'Verbose name 02'
    #
    #     ff01 = TestFunctionField01()
    #     ff02 = TestFunctionField02()
    #
    #     ffm01 = FunctionFieldsManager(ff01)
    #     ffm02 = ffm01.new(ff02)
    #
    #     self.assertIs(ff01, ffm01.get(fname01))
    #     self.assertIsNone(ffm01.get(fname02))
    #     self.assertEqual([ff01], list(ffm01))
    #
    #     self.assertIs(ff01, ffm02.get(fname01))
    #     self.assertIs(ff02, ffm02.get(fname02))
    #     self.assertEqual([ff01, ff02], sorted(ffm02, key=lambda ff: ff.name))

    # def test_manager04(self):
    #     "new() method + add() on 'base instance'"
    #     fname01 = 'name01'
    #     fname02 = 'name02'
    #
    #     class TestFunctionField01(FunctionField):
    #         name         = fname01
    #         verbose_name = 'Verbose name 01'
    #
    #     class TestFunctionField02(FunctionField):
    #         name         = fname02
    #         verbose_name = 'Verbose name 02'
    #
    #     ff01 = TestFunctionField01()
    #     ff02 = TestFunctionField02()
    #
    #     ffm01 = FunctionFieldsManager()
    #     ffm02 = ffm01.new(ff02)
    #
    #     ffm01.add(ff01)  # <== added after new()
    #
    #     self.assertIs(ff01, ffm01.get(fname01))
    #     self.assertIsNone(ffm01.get(fname02))
    #     self.assertEqual([ff01], list(ffm01))
    #
    #     self.assertIs(ff02, ffm02.get(fname02))
    #     self.assertIs(ff01, ffm02.get(fname01)) # ok ?
    #     self.assertEqual([ff01, ff02], sorted(ffm02, key=lambda ff: ff.name))

    def test_registry01(self):
        class Klass1: pass
        class Klass2(Klass1): pass

        registry = _FunctionFieldRegistry()

        fname11 = 'name11'
        fname12 = 'name12'
        fname13 = 'name13'
        fname2  = 'name2'

        class TestFunctionField11(FunctionField):
            name         = fname11
            verbose_name = 'Verbose name 11'

        class TestFunctionField12(FunctionField):
            name         = fname12
            verbose_name = 'Verbose name 12'

        class TestFunctionField13(FunctionField):
            name         = fname13
            verbose_name = 'Verbose name 13'

        class TestFunctionField2(FunctionField):
            name         = fname2
            verbose_name = 'Verbose name 2'

        registry.register(Klass1, TestFunctionField11, TestFunctionField12, TestFunctionField13)
        registry.register(Klass2, TestFunctionField2)
        self.assertIsInstance(registry.get(Klass1, fname11), TestFunctionField11)
        self.assertIsInstance(registry.get(Klass1, fname12), TestFunctionField12)
        self.assertIsInstance(registry.get(Klass1, fname13), TestFunctionField13)
        self.assertIsNone(registry.get(Klass1, 'unknown'))
        self.assertIsNone(registry.get(Klass1, fname2))

        self.assertIsInstance(registry.get(Klass2, fname11), TestFunctionField11)
        self.assertIsInstance(registry.get(Klass2, fname12), TestFunctionField12)
        self.assertIsInstance(registry.get(Klass2, fname2),  TestFunctionField2)

        self.assertIsNone(registry.get(Klass1, fname2))

        # Function fields
        self.assertEqual({TestFunctionField11, TestFunctionField12, TestFunctionField13},
                         {ff.__class__ for ff in registry.fields(Klass1)}
                        )
        self.assertEqual({TestFunctionField11, TestFunctionField12, TestFunctionField13, TestFunctionField2},
                         {ff.__class__ for ff in registry.fields(Klass2)}
                        )

        # Unregister -----
        registry.unregister(Klass1, TestFunctionField11, TestFunctionField12)
        self.assertIsNone(registry.get(Klass1, fname11))
        self.assertIsNone(registry.get(Klass1, fname12))
        self.assertIsInstance(registry.get(Klass1, fname13), TestFunctionField13)

        self.assertIsNone(registry.get(Klass2, fname11))

    def test_registry02(self):
        "Duplicates error."
        class Klass: pass

        registry = _FunctionFieldRegistry()

        class TestFunctionField1(FunctionField):
            name         = 'name1'
            verbose_name = 'Verbose name 1'

        class TestFunctionField2(FunctionField):
            name         = TestFunctionField1.name # <==
            verbose_name = 'Verbose name 2'

        registry.register(Klass, TestFunctionField1)

        with self.assertRaises(_FunctionFieldRegistry.RegistrationError):
            registry.register(Klass, TestFunctionField2)

    def test_registry03(self):
        "Overridden field."
        class Klass1: pass
        class Klass2(Klass1): pass

        registry = _FunctionFieldRegistry()

        fname1 = 'name1'
        fname2 = 'name2'

        class TestFunctionField1(FunctionField):
            name         = fname1
            verbose_name = 'Verbose name 1'

        class TestFunctionField2(FunctionField):
            name         = fname2
            verbose_name = 'Verbose name 2'

        class TestFunctionField22(FunctionField):
            name         = TestFunctionField2.name  # <== Override
            verbose_name = 'Verbose name 2'

        registry.register(Klass1, TestFunctionField1, TestFunctionField2)
        registry.register(Klass2, TestFunctionField22)
        self.assertIsInstance(registry.get(Klass2, fname1), TestFunctionField1)
        self.assertIsInstance(registry.get(Klass2, fname2), TestFunctionField22)  # Not TestFunctionField2

        # Function fields
        self.assertEqual({TestFunctionField1, TestFunctionField2},
                         {ff.__class__ for ff in registry.fields(Klass1)}
                        )
        self.assertEqual({TestFunctionField1, TestFunctionField22},
                         {ff.__class__ for ff in registry.fields(Klass2)}
                        )

    def test_registry04(self):
        "Unregister() error."
        class Klass: pass

        registry = _FunctionFieldRegistry()

        class TestFunctionField(FunctionField):
            name         = 'name'
            verbose_name = 'Verbose name'

        with self.assertRaises(_FunctionFieldRegistry.RegistrationError):
            registry.unregister(Klass, TestFunctionField)

    # TODO: test other classes
