# -*- coding: utf-8 -*-

from creme.creme_core.core.reminder import Reminder, ReminderRegistry

from ..base import CremeTestCase


class ReminderTestCase(CremeTestCase):
    def test_empty(self):
        registry = ReminderRegistry()

        self.assertFalse([*registry])

    def test_register(self):
        registry = ReminderRegistry()

        class TestReminder1(Reminder):
            id = Reminder.generate_id('creme_core', 'ReminderTestCase_test_register_1')

        class TestReminder2(Reminder):
            id = Reminder.generate_id('creme_core', 'ReminderTestCase_test_register_2')

        registry.register(TestReminder1)
        registry.register(TestReminder2)

        self.assertSetEqual(
            {TestReminder1, TestReminder2},
            {r.__class__ for r in registry},
        )

        # --
        registry.unregister(TestReminder1)
        self.assertListEqual(
            [TestReminder2],
            [r.__class__ for r in registry],
        )

        with self.assertRaises(registry.RegistrationError):
            registry.unregister(TestReminder1)

    def test_register_error01(self):
        "Duplicated ID."
        registry = ReminderRegistry()

        class TestReminder1(Reminder):
            id = Reminder.generate_id('creme_core', 'ReminderTestCase_test_register_error01')

        class TestReminder2(Reminder):
            id = TestReminder1.id  # < ===

        registry.register(TestReminder1)

        with self.assertRaises(registry.RegistrationError) as cm:
            registry.register(TestReminder2)

        self.assertEqual(
            f"Duplicated reminder's id or reminder registered twice: {TestReminder1.id}",
            str(cm.exception),
        )

    def test_register_error02(self):
        "Empty ID."
        registry = ReminderRegistry()

        class TestReminder(Reminder):
            # id = Reminder.generate_id('creme_core', 'ReminderTestCase_test') NOPE
            pass

        with self.assertRaises(registry.RegistrationError) as cm:
            registry.register(TestReminder)

        self.assertEqual(
            f"Reminder class with empty id: {TestReminder}",
            str(cm.exception),
        )
