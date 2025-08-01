from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    EF_REGULAR,
    EntityFilterRegistry,
    EntityFilterSuperRegistry,
    entity_filter_registries,
    operands,
    operators,
)
from creme.creme_core.core.entity_filter.condition_handler import (
    DateRegularFieldConditionHandler,
    FilterConditionHandler,
    RegularFieldConditionHandler,
)
from creme.creme_core.models import EntityFilter, FakeContact
from creme.creme_core.tests.base import CremeTestCase


class EntityFilterRegistryTestCase(CremeTestCase):
    def test_constants(self):
        with self.assertNoException():
            from creme.creme_core.core.entity_filter import (
                EF_CREDENTIALS,
                EF_REGULAR,
            )

        self.assertEqual('creme_core-regular', EF_REGULAR)
        self.assertEqual('creme_core-credentials', EF_CREDENTIALS)

    def test_handlers01(self):
        name = 'Common'
        registry = EntityFilterRegistry(id='creme_core-default', verbose_name=name)
        self.assertEqual(name, registry.verbose_name)

        cls1 = RegularFieldConditionHandler

        with self.assertLogs(level='WARNING') as logs_manager:
            none_handler = registry.get_handler(
                type_id=cls1.type_id, model=FakeContact, name='foo', data={},
            )

        self.assertIsNone(none_handler)
        self.assertListEqual(
            [
                f'WARNING:creme.creme_core.core.entity_filter:'
                f'EntityFilterRegistry.get_handler(): '
                f'no handler class with type_id="{cls1.type_id}" found.',
            ],
            logs_manager.output,
        )

        cls2 = DateRegularFieldConditionHandler
        registry.register_condition_handlers(cls1, cls2)
        handler1 = registry.get_handler(
            type_id=cls1.type_id,
            model=FakeContact, name='first_name',
            data={'operator': operators.ICONTAINS, 'values': ['Ikari']},
        )
        self.assertIsInstance(handler1, cls1)

        handler2 = registry.get_handler(
            type_id=cls2.type_id,
            model=FakeContact, name='created', data={'name': 'yesterday'},
        )
        self.assertIsInstance(handler2, cls2)

        # assertListEqual => order must be kept
        self.assertListEqual([cls1, cls2], [*registry.handler_classes])

    def test_handlers02(self):
        "ID collision."
        registry = EntityFilterRegistry(id='creme_core-default', verbose_name='Test')

        cls1 = RegularFieldConditionHandler

        class TestHandler(FilterConditionHandler):
            type_id = cls1.type_id

        registry.register_condition_handlers(cls1)

        with self.assertRaises(EntityFilterRegistry.RegistrationError):
            registry.register_condition_handlers(TestHandler)

    def test_handlers03(self):
        "get_handler() + invalid data."
        registry = EntityFilterRegistry(
            id='creme_core-default', verbose_name='Test',
        ).register_condition_handlers(RegularFieldConditionHandler)

        handler = registry.get_handler(
            type_id=RegularFieldConditionHandler.type_id,
            model=FakeContact, name='first_name',
            data={'values': ['Ikari']},  # No 'operator'
        )
        self.assertIsNone(handler)

    def test_operands01(self):
        registry = EntityFilterRegistry(id='creme_core-default', verbose_name='Test')

        cls1 = operands.CurrentUserOperand
        self.assertIsNone(registry.get_operand(type_id=cls1.type_id, user=None))

        class TestOperand(operands.ConditionDynamicOperand):
            type_id = 'test'

        registry.register_operands(cls1, TestOperand)
        operand1 = registry.get_operand(type_id=cls1.type_id, user=None)
        self.assertIsInstance(operand1, cls1)
        self.assertIsNone(operand1.user)

        operand2 = registry.get_operand(type_id=TestOperand.type_id, user=None)
        self.assertIsInstance(operand2, TestOperand)

        self.assertSetEqual({cls1, TestOperand}, {type(op) for op in registry.operands(user=None)})

    def test_operands02(self):
        "ID collision."
        registry = EntityFilterRegistry(id='creme_core-default', verbose_name='Test')

        cls1 = operands.CurrentUserOperand

        class TestOperand(operands.ConditionDynamicOperand):
            type_id = cls1.type_id

        registry.register_operands(cls1)

        with self.assertRaises(EntityFilterRegistry.RegistrationError):
            registry.register_operands(TestOperand)

    def test_operator01(self):
        registry = EntityFilterRegistry(id='creme_core-default', verbose_name='Test')

        cls1 = operators.EqualsOperator
        self.assertIsNone(registry.get_operator(type_id=cls1.type_id))

        cls2 = operators.IsEmptyOperator
        registry.register_operators(cls1, cls2)
        operator1 = registry.get_operator(type_id=cls1.type_id)
        self.assertIsInstance(operator1, cls1)

        operator2 = registry.get_operator(type_id=cls2.type_id)
        self.assertIsInstance(operator2, cls2)

        self.assertSetEqual({cls1, cls2}, {type(op) for op in registry.operators})

    def test_operators02(self):
        "ID collision."
        registry = EntityFilterRegistry(id='creme_core-default', verbose_name='Test')

        class TestOperator(operators.EqualsOperator):
            pass

        registry.register_operators(operators.EqualsOperator)

        with self.assertRaises(EntityFilterRegistry.RegistrationError):
            registry.register_operators(TestOperator)

    def test_tag01(self):
        registry = EntityFilterRegistry(id='creme_core-default', verbose_name='Test')
        self.assertEqual('', registry.tag)

        registry.tag = 'test'
        self.assertEqual('test', registry.tag)

        # ---
        self.assertEqual('', entity_filter_registries[EF_REGULAR].tag)
        self.assertEqual('', entity_filter_registries[EF_CREDENTIALS].tag)

    def test_tag02(self):
        registry = EntityFilterRegistry(
            id='creme_core-default', verbose_name='Test', tag='test',
        )
        self.assertEqual('test', registry.tag)

    def test_id_length(self):
        length = 36
        self.assertEqual(length, EntityFilter._meta.get_field('filter_type').max_length)

        rid = 'a_app-a_very_very_very_very_long_name'
        self.assertEqual(length + 1, len(rid))

        with self.assertRaises(ValueError) as cm:
            EntityFilterRegistry(id=rid, verbose_name='Test01')

        self.assertEqual(
            f'The "id" cannot be longer than {length}',
            str(cm.exception),
        )


class EntityFilterSuperRegistryTestCase(CremeTestCase):
    def test_main(self):
        rid1 = 'creme_core-normal'
        rid2 = 'creme_core-system'
        rid3 = 'documents-specific'
        registry01 = EntityFilterRegistry(id=rid1, verbose_name='Test01')
        registry02 = EntityFilterRegistry(id=rid2, verbose_name='Test02')
        registry03 = EntityFilterRegistry(id=rid3, verbose_name='Test03')

        registries = EntityFilterSuperRegistry().register(
            registry01, registry02, registry03,
        )
        self.assertIs(registry01, registries[rid1])
        self.assertIs(registry02, registries[rid2])

        with self.assertRaises(KeyError):
            registries['creme_core-unkknown']  # NOQA

        self.assertListEqual(
            [registry01, registry02, registry03],
            [*registries],
        )

        # ---
        registries.unregister(rid1, rid3)
        self.assertListEqual([registry02], [*registries])

        with self.assertRaises(registries.UnRegistrationError) as cm:
            registries.unregister(rid1)

        self.assertEqual(
            f'Invalid registry ID "{rid1}" (already unregistered?)',
            str(cm.exception),
        )

    def test_id_collision(self):
        rid = 'creme_core-listview'
        registry01 = EntityFilterRegistry(id=rid, verbose_name='Test01')
        registry02 = EntityFilterRegistry(id=rid, verbose_name='Test02')
        registries = EntityFilterSuperRegistry()\

        with self.assertRaises(EntityFilterSuperRegistry.RegistrationError):
            registries.register(
                registry01, registry02,
            )
