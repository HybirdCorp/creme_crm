from django.utils.translation import gettext as _

from creme.creme_core.core.reminder import Reminder, ReminderRegistry
from creme.creme_core.creme_jobs.reminder import _ReminderType
from creme.creme_core.models import FakeIngredient, FakeTodo, Job

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

        with self.assertRaises(registry.UnRegistrationError) as cm:
            registry.unregister(TestReminder1)

        self.assertEqual(
            f"Invalid reminder {TestReminder1} (already unregistered?)",
            str(cm.exception),
        )

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

    def test_job01(self):
        reminder_type = _ReminderType()
        reminder_type.reminder_registry = ReminderRegistry()

        job = self.get_object_or_fail(Job, type_id=reminder_type.id)

        self.assertListEqual(
            [_('None of your apps uses reminders')],
            reminder_type.get_description(job),
        )

    def test_job02(self):
        class TestReminder1(Reminder):
            id = Reminder.generate_id('creme_core', 'ReminderTestCase_test_job02_1')
            model = FakeTodo

        class TestReminder2(Reminder):
            id = Reminder.generate_id('creme_core', 'ReminderTestCase_test_job02_2')
            model = FakeIngredient

        reminder_type = _ReminderType()
        reminder_type.reminder_registry = registry = ReminderRegistry()

        registry.register(TestReminder1).register(TestReminder2)

        job = self.get_object_or_fail(Job, type_id=reminder_type.id)

        fmt = _('Execute reminders for «{model}»').format
        self.assertListEqual(
            [fmt(model='Test Todos'), fmt(model='Test Ingredients')],
            reminder_type.get_description(job),
        )
