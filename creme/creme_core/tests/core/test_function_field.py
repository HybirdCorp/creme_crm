# -*- coding: utf-8 -*-

try:
    from ..base import CremeTestCase

    from creme.creme_core.core.function_field import FunctionField, _FunctionFieldRegistry  # FunctionFieldsManager
except Exception as e:
    print(f'Error in <{__name__}>: {e}')


class FunctionFieldsTestCase(CremeTestCase):
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

        registry.register(
            Klass1, TestFunctionField11, TestFunctionField12, TestFunctionField13,
        ).register(
            Klass2, TestFunctionField2,
        )
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
            name         = TestFunctionField1.name  # <==
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
