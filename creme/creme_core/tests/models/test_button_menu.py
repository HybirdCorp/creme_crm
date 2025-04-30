from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from creme.creme_core.buttons import Restrict2SuperusersButton
from creme.creme_core.gui.button_menu import Button, button_registry
from creme.creme_core.models import ButtonMenuItem, FakeContact

from ..base import CremeTestCase


class TestButton(Button):
    id = Button.generate_id('creme_core', 'test_button_menu')
    verbose_name = 'Testing purpose'


class ButtonMenuItemTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        button_registry.register(TestButton)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        button_registry.unregister(TestButton)

    def test_manager_create_if_needed(self):
        content_type = ContentType.objects.get_for_model(FakeContact)
        old_count = ButtonMenuItem.objects.count()

        order = 10
        ButtonMenuItem.objects.create_if_needed(
            model=FakeContact, button=TestButton, order=order,
        )
        self.assertEqual(old_count + 1, ButtonMenuItem.objects.count())

        bmi = self.get_object_or_fail(
            ButtonMenuItem,
            content_type=content_type,
            button_id=TestButton.id,
            superuser=False,
            role=None,
        )
        self.assertEqual(FakeContact,   bmi.content_type.model_class())
        self.assertEqual(TestButton.id, bmi.button_id)
        self.assertEqual(order,         bmi.order)

        bmi = ButtonMenuItem.objects.create_if_needed(
            model=FakeContact, button=TestButton, order=order + 5,
        )
        self.assertEqual(order, bmi.order)
        self.assertEqual(old_count + 1, ButtonMenuItem.objects.count())

    def test_manager_create_if_needed__no_ctype(self):
        "Default config (content_type=None)."
        old_count = ButtonMenuItem.objects.count()
        bmi = ButtonMenuItem.objects.create_if_needed(
            model=None, button=TestButton, order=15,
        )
        self.assertEqual(old_count + 1, ButtonMenuItem.objects.count())
        self.assertIsNone(bmi.content_type)

    def test_manager_create_if_needed__button_id(self):
        "Button ID."
        order = 10
        ButtonMenuItem.objects.create_if_needed(
            model=FakeContact, button=TestButton.id, order=order,
        )
        self.get_object_or_fail(
            ButtonMenuItem,
            content_type=ContentType.objects.get_for_model(FakeContact),
            button_id=TestButton.id,
        )

    def test_manager_create_if_needed__superuser(self):
        ButtonMenuItem.objects.create_if_needed(
            model=FakeContact, button=Restrict2SuperusersButton, order=1,
            role='superuser',
        )
        self.get_object_or_fail(
            ButtonMenuItem,
            content_type=ContentType.objects.get_for_model(FakeContact),
            button_id=Restrict2SuperusersButton.id,
            superuser=True, role=None,
        )

    def test_manager_create_if_needed__role(self):
        role = self.create_role()
        ButtonMenuItem.objects.create_if_needed(
            model=FakeContact, button=Restrict2SuperusersButton, order=1,
            role=role,
        )
        self.get_object_or_fail(
            ButtonMenuItem,
            content_type=ContentType.objects.get_for_model(FakeContact),
            button_id=Restrict2SuperusersButton.id,
            superuser=False, role=role,
        )

    # TODO?
    # def test_eq(self):
    #     ct = ContentType.objects.get_for_model(FakeContact)
    #     button_id = Restrict2SuperusersButton.id
    #     role1 = self.create_role(name='Role #1')
    #     role2 = self.create_role(name='Role #2')
    #
    #     self.assertEqual(
    #         ButtonMenuItem(content_type=None, button_id='', order=1),
    #         ButtonMenuItem(content_type=None, button_id='', order=1),
    #     )
    #     self.assertEqual(
    #         ButtonMenuItem(content_type=ct, button_id=button_id, order=3, role=role1),
    #         ButtonMenuItem(content_type=ct, button_id=button_id, order=3, role=role1),
    #     )
    #
    #     self.assertNotEqual(ButtonMenuItem(button_id='', order=1), 'Not a button')
    #     self.assertNotEqual(
    #         ButtonMenuItem(content_type=ct,   button_id='', order=1),
    #         ButtonMenuItem(content_type=None, button_id='', order=1),
    #     )
    #     self.assertNotEqual(
    #         ButtonMenuItem(content_type=ct, button_id='',        order=1),
    #         ButtonMenuItem(content_type=ct, button_id=button_id, order=1),
    #     )
    #     self.assertNotEqual(
    #         ButtonMenuItem(content_type=ct, button_id=button_id, order=1),
    #         ButtonMenuItem(content_type=ct, button_id=button_id, order=2),
    #     )
    #     self.assertNotEqual(
    #         ButtonMenuItem(content_type=ct, button_id=button_id, order=1),
    #         ButtonMenuItem(content_type=ct, button_id=button_id, order=1, superuser=True),
    #     )
    #     self.assertNotEqual(
    #         ButtonMenuItem(content_type=ct, button_id=button_id, order=1, role=role1),
    #         ButtonMenuItem(content_type=ct, button_id=button_id, order=1, role=role2),
    #     )

    def test_property_button__class(self):
        bmi = ButtonMenuItem(button=TestButton)
        self.assertEqual(TestButton.id, bmi.button_id)
        self.assertIsInstance(bmi.button, TestButton)
        self.assertEqual(TestButton.verbose_name, str(bmi))

    def test_property_button__instance(self):
        bmi = ButtonMenuItem(button=TestButton())
        self.assertEqual(TestButton.id, bmi.button_id)
        self.assertIsInstance(bmi.button, TestButton)
        self.assertEqual(TestButton.verbose_name, str(bmi))

    def test_property_button__invalid(self):
        bmi = ButtonMenuItem()
        self.assertEqual('', bmi.button_id)
        self.assertIsNone(bmi.button)
        self.assertEqual(_('Deprecated button'), str(bmi))

    def test_clone_for_role(self):
        bmi1 = ButtonMenuItem(content_type=None, button_id='', order=1)
        self.assertIs(bmi1.superuser, False)
        self.assertIsNone(bmi1.role, False)

        clone1 = bmi1.clone_for_role(role=None)
        self.assertIsInstance(clone1, ButtonMenuItem)
        self.assertIsNone(clone1.content_type)
        self.assertEqual('', clone1.button_id)
        self.assertEqual(1, clone1.order)
        self.assertIsNone(clone1.role)
        self.assertIs(clone1.superuser, True)

        # ---
        role = self.create_role()
        bmi2 = ButtonMenuItem(
            content_type=ContentType.objects.get_for_model(FakeContact),
            button_id=Restrict2SuperusersButton.id, order=2, role=role,
        )
        clone2 = bmi2.clone_for_role(role=role)
        self.assertEqual(bmi2.content_type, clone2.content_type)
        self.assertEqual(bmi2.button_id, clone2.button_id)
        self.assertEqual(2, clone2.order)
        self.assertIs(clone2.superuser, False)
        self.assertEqual(role, clone2.role)
