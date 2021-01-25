# -*- coding: utf-8 -*-

from django.contrib.contenttypes.models import ContentType

from creme.creme_core.gui.button_menu import Button
from creme.creme_core.models import ButtonMenuItem

from ..base import CremeTestCase
from ..fake_models import FakeContact


class ButtonMenuItemTestCase(CremeTestCase):
    # def test_create_if_needed(self):
    #     pk = 'creme_core-test_button'
    #     old_count = ButtonMenuItem.objects.count()
    #
    #     class TestButton(Button):
    #         id_ = Button.generate_id('creme_core', 'test_create_if_needed')
    #         verbose_name = 'Testing purpose'
    #
    #     order = 10
    #     ButtonMenuItem.create_if_needed(pk, FakeContact, TestButton, order)
    #     self.assertEqual(old_count + 1, ButtonMenuItem.objects.count())
    #
    #     bmi = self.get_object_or_fail(
    #         ButtonMenuItem,
    #         content_type=ContentType.objects.get_for_model(FakeContact),
    #         button_id=TestButton.id_,
    #     )
    #     self.assertEqual(order, bmi.order)
    #
    #     bmi = ButtonMenuItem.create_if_needed(pk, FakeContact, TestButton, order + 5)
    #     self.assertEqual(order, bmi.order)
    #     self.assertEqual(old_count + 1, ButtonMenuItem.objects.count())

    def test_manager_create_if_needed01(self):
        content_type = ContentType.objects.get_for_model(FakeContact)
        old_count = ButtonMenuItem.objects.count()

        class TestButton(Button):
            id_ = Button.generate_id('creme_core', 'test_manager_create_if_needed01')
            verbose_name = 'Testing purpose'

        order = 10
        ButtonMenuItem.objects.create_if_needed(
            model=FakeContact, button=TestButton, order=order,
        )
        self.assertEqual(old_count + 1, ButtonMenuItem.objects.count())

        bmi = self.get_object_or_fail(
            ButtonMenuItem,
            content_type=content_type,
            button_id=TestButton.id_,
        )
        self.assertEqual(FakeContact,    bmi.content_type.model_class())
        self.assertEqual(TestButton.id_, bmi.button_id)
        self.assertEqual(order,          bmi.order)

        bmi = ButtonMenuItem.objects.create_if_needed(
            model=FakeContact, button=TestButton, order=order + 5,
        )
        self.assertEqual(order, bmi.order)
        self.assertEqual(old_count + 1, ButtonMenuItem.objects.count())

    def test_manager_create_if_needed02(self):
        "Default config (content_type=None)."
        class TestButton(Button):
            id_ = Button.generate_id('creme_core', 'test_manager_create_if_needed02')
            verbose_name = 'Testing purpose'

        old_count = ButtonMenuItem.objects.count()
        bmi = ButtonMenuItem.objects.create_if_needed(
            model=None, button=TestButton, order=15,
        )
        self.assertEqual(old_count + 1, ButtonMenuItem.objects.count())
        self.assertIsNone(bmi.content_type)

    def test_manager_create_if_needed03(self):
        "Button ID."
        class TestButton(Button):
            id_ = Button.generate_id('creme_core', 'test_manager_create_if_needed03')
            verbose_name = 'Testing purpose'

        order = 10
        ButtonMenuItem.objects.create_if_needed(
            model=FakeContact, button=TestButton.id_, order=order,
        )
        self.get_object_or_fail(
            ButtonMenuItem,
            content_type=ContentType.objects.get_for_model(FakeContact),
            button_id=TestButton.id_,
        )
