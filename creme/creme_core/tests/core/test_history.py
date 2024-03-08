from functools import partial

from creme.creme_core.core.history import do_toggle_history, toggle_history
from creme.creme_core.models import FakeContact, HistoryLine, Language
from creme.creme_core.models.history import TYPE_CREATION, is_history_enabled

from ..base import CremeTestCase


class HistoryTestCase(CremeTestCase):
    def test_do_toggle_history(self):
        create_contact = partial(FakeContact.objects.create, user=self.get_root_user())
        fry = self.refresh(create_contact(first_name='Phillip', last_name='Fry'))
        self.assertIs(is_history_enabled(), True)

        count = HistoryLine.objects.count()

        # ---
        do_toggle_history(enabled=False)
        amy = self.refresh(create_contact(first_name='Amy', last_name='Wong'))
        amy.phone = '123'
        amy.save()

        fry.languages.set([*Language.objects.all()[:2]])
        fry.delete()

        self.assertEqual(count, HistoryLine.objects.count())
        self.assertIs(is_history_enabled(), False)

        # ---
        do_toggle_history(enabled=True)
        amy = self.refresh(amy)
        amy.phone = '456'
        amy.save()
        self.assertEqual(count + 1, HistoryLine.objects.count())
        self.assertIs(is_history_enabled(), True)

    def test_toggle_history__context(self):
        create_contact = partial(FakeContact.objects.create, user=self.get_root_user())
        fry = self.refresh(create_contact(first_name='Phillip', last_name='Fry'))
        self.assertIs(is_history_enabled(), True)

        count = HistoryLine.objects.count()

        # ---
        with toggle_history(enabled=False):
            amy = self.refresh(create_contact(first_name='Amy', last_name='Wong'))
            amy.phone = '123'
            amy.save()

            fry.languages.set([*Language.objects.all()[:2]])
            fry.delete()
            self.assertIs(is_history_enabled(), False)

        self.assertEqual(count, HistoryLine.objects.count())
        self.assertIs(is_history_enabled(), True)

        # ---
        amy = self.refresh(amy)
        amy.phone = '456'
        amy.save()
        self.assertEqual(count + 1, HistoryLine.objects.count())

    def test_toggle_history__decorator(self):
        user = self.get_root_user()
        count = HistoryLine.objects.count()
        self.assertIs(is_history_enabled(), True)

        @toggle_history(enabled=False)
        def perform():
            FakeContact.objects.create(user=user, first_name='Amy', last_name='Wong')
            self.assertIs(is_history_enabled(), False)

        perform()
        self.assertEqual(count, HistoryLine.objects.count())
        self.assertIs(is_history_enabled(), True)

    def test_toggle_history__context_exception(self):
        user = self.get_root_user()
        count = HistoryLine.objects.count()

        with self.assertRaises(ValueError):
            with toggle_history(enabled=False):
                FakeContact.objects.create(user=user, first_name='Amy', last_name='Wong')
                raise ValueError('I should not be captured by context manager')

        self.assertEqual(count, HistoryLine.objects.count())
        self.assertIs(is_history_enabled(), True)

    def test_toggle_history__nested_contexts(self):
        create_contact = partial(FakeContact.objects.create, user=self.get_root_user())
        count = HistoryLine.objects.count()

        with toggle_history(enabled=False):
            with toggle_history(enabled=False):
                create_contact(first_name='Amy', last_name='Wong')
                self.assertIs(is_history_enabled(), False)

            with toggle_history(enabled=True):
                fry = create_contact(first_name='Phillip', last_name='Fry')
                self.assertIs(is_history_enabled(), True)

            create_contact(first_name='Leela', last_name='Turanga')
            self.assertIs(is_history_enabled(), False)

        self.assertEqual(count + 1, HistoryLine.objects.count())
        self.assertIs(is_history_enabled(), True)

        hline = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(TYPE_CREATION, hline.type)
        self.assertEqual(fry.id, hline.entity.id)
