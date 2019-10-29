# -*- coding: utf-8 -*-

try:
    from ..base import CremeTestCase

    from creme.creme_core.core.reminder import Reminder, ReminderRegistry
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class ReminderTestCase(CremeTestCase):
    def test_empty(self):
        registry = ReminderRegistry()

        self.assertFalse([*registry])
        # self.assertFalse(list(registry.itervalues()))

    def test_register(self):
        registry = ReminderRegistry()

        class TestReminder1(Reminder):
            id = Reminder.generate_id('creme_core', 'ReminderTestCase_test_register_1')

        class TestReminder2(Reminder):
            id = Reminder.generate_id('creme_core', 'ReminderTestCase_test_register_2')

        registry.register(TestReminder1)
        registry.register(TestReminder2)

        self.assertEqual({TestReminder1, TestReminder2},
                         {r.__class__ for r in registry}
                        )
        # self.assertEqual({TestReminder1, TestReminder2},
        #                  {r.__class__ for r in registry.itervalues()}
        #                 )

        # --
        registry.unregister(TestReminder1)
        self.assertEqual([TestReminder2],
                         [r.__class__ for r in registry]
                        )

        with self.assertRaises(registry.RegistrationError):
            registry.unregister(TestReminder1)

    def test_register_error(self):
        registry = ReminderRegistry()

        class TestReminder1(Reminder):
            id = Reminder.generate_id('creme_core', 'ReminderTestCase_test_register_error')

        class TestReminder2(Reminder):
            id = TestReminder1.id  # < ===

        registry.register(TestReminder1)

        with self.assertRaises(registry.RegistrationError):
            registry.register(TestReminder2)
