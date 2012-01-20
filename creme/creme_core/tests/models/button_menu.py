# -*- coding: utf-8 -*-

try:
    from creme_core.models import ButtonMenuItem
    from creme_core.gui.button_menu import Button
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact
except Exception as e:
    print 'Error:', e


__all__ = ('ButtonMenuItemTestCase', )


class ButtonMenuItemTestCase(CremeTestCase):
    def test_create_if_needed01(self):
        pk = 'creme_core-test_button'
        self.assertFalse(ButtonMenuItem.objects.filter(pk=pk))

        class TestButton(Button):
            id_          = Button.generate_id('creme_core', 'test_create_if_needed01')
            verbose_name = u'Testing purpose'

        button = TestButton()

        order = 10
        ButtonMenuItem.create_if_needed(pk, Contact, button, order)
        bmi = self.get_object_or_fail(ButtonMenuItem, pk=pk)

        self.assertEqual(Contact,    bmi.content_type.model_class())
        self.assertEqual(button.id_, bmi.button_id)
        self.assertEqual(order,      bmi.order)

        old_count = ButtonMenuItem.objects.count()
        bmi = ButtonMenuItem.create_if_needed(pk, Contact, button, order + 5)
        self.assertEqual(order,     bmi.order)
        self.assertEqual(old_count, ButtonMenuItem.objects.count())

    def test_create_if_needed02(self):
        class TestButton(Button):
            id_          = Button.generate_id('creme_core', 'test_create_if_needed02')
            verbose_name = u'Testing purpose'

        button = TestButton()

        old_count = ButtonMenuItem.objects.count()
        bmi = ButtonMenuItem.create_if_needed('creme_core-test_button', None, button, 15)
        self.assertEqual(old_count + 1, ButtonMenuItem.objects.count())
        self.assertIsNone(bmi.content_type)
