from creme.creme_core.core.sandbox import (
    SandboxType,
    SandboxTypeRegistry,
    sandbox_type_registry,
)
from creme.creme_core.models import Sandbox

from ..base import CremeTestCase


class SandboxTestCase(CremeTestCase):
    def test_registry01(self):
        name = 'Test sandbox #1'

        class TestSandboxType1(SandboxType):
            id = SandboxType.generate_id('creme_core', 'test1')
            verbose_name = name

        sandbox_type_registry.register(TestSandboxType1)  # TODO: unregister in tearDown ?

        sandbox = Sandbox(type_id=TestSandboxType1.id)

        st_type = sandbox.type
        self.assertIsInstance(st_type, TestSandboxType1)
        self.assertEqual(name, st_type.verbose_name)

    def test_registry02(self):
        registry = SandboxTypeRegistry()

        st_id = SandboxType.generate_id('creme_core', 'test2')

        class TestSandboxType2_2(SandboxType):
            id = st_id
            verbose_name = 'Test sandbox #2'

        class TestSandboxType2_3(SandboxType):
            id = st_id
            verbose_name = 'Test sandbox #3'

        registry.register(TestSandboxType2_2)

        with self.assertRaises(SandboxTypeRegistry.Error) as cm:
            registry.register(TestSandboxType2_3)

        self.assertEqual(
            f'Duplicated sandbox type id: {TestSandboxType2_3.id}',
            str(cm.exception),
        )

        sandbox1 = Sandbox(type=TestSandboxType2_2)
        self.assertIsInstance(registry.get(sandbox1), TestSandboxType2_2)

        class TestSandboxType2_4(SandboxType):  # Not registered
            id = SandboxType.generate_id('creme_core', 'unknown')
            verbose_name = 'Test sandbox #4'

        sandbox2 = Sandbox(type_id=TestSandboxType2_4.id)

        with self.assertLogs(level='CRITICAL') as logs_manager:
            sb_type = registry.get(sandbox2)

        self.assertIsNone(sb_type)
        self.assertListEqual(
            logs_manager.output,
            [
                f'CRITICAL:creme.creme_core.core.sandbox:Unknown SandboxType: '
                f'{TestSandboxType2_4.id}',
            ],
        )

    def test_registry03(self):
        "Empty ID."
        class TestSandboxType(SandboxType):
            # id = SandboxType.generate_id('creme_core', 'test')  NOPE
            verbose_name = 'Test sandbox'

        registry = SandboxTypeRegistry()

        with self.assertRaises(SandboxTypeRegistry.Error) as cm:
            registry.register(TestSandboxType)

        self.assertEqual(
            f'SandBox class with empty id: {TestSandboxType}',
            str(cm.exception),
        )

    def test_sandbox_data(self):
        user = self.get_root_user()
        fmt = 'Restricted to "{}"'.format

        class TestSandboxType3(SandboxType):
            id = SandboxType.generate_id('creme_core', 'test3')

            @property
            def verbose_name(self):
                return fmt(self.sandbox.user)

        sandbox_type_registry.register(TestSandboxType3)  # TODO: unregister in tearDown ?

        sandbox = Sandbox(type_id=TestSandboxType3.id, user=user)
        self.assertEqual(fmt(user), sandbox.type.verbose_name)
