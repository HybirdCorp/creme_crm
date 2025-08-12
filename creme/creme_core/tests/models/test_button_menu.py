from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from creme.creme_core.buttons import Restrict2SuperusersButton
from creme.creme_core.gui.button_menu import Button, button_registry
from creme.creme_core.models import ButtonMenuItem, FakeContact, FakeSector
from creme.creme_core.models.button_menu import ButtonMenuItemProxy

from ..base import CremeTestCase


class TestButton(Button):
    id = Button.generate_id('creme_core', 'test_button_menu')
    verbose_name = 'Testing purpose'


class _ButtonMenuItemTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        button_registry.register(TestButton)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        button_registry.unregister(TestButton)


class ButtonMenuItemManagerTestCase(_ButtonMenuItemTestCase):
    def test_create_if_needed(self):
        content_type = ContentType.objects.get_for_model(FakeContact)
        old_count = ButtonMenuItem.objects.count()

        order = 10
        ButtonMenuItem.objects.create_if_needed(
            model=FakeContact, button=TestButton, order=order,
        )
        self.assertEqual(old_count + 1, ButtonMenuItem.objects.count())

        bmi1 = self.get_object_or_fail(
            ButtonMenuItem,
            content_type=content_type,
            button_id=TestButton.id,
            superuser=False,
            role=None,
        )
        self.assertEqual(order, bmi1.order)

        bmi2 = ButtonMenuItem.objects.create_if_needed(
            model=FakeContact, button=TestButton, order=order + 5,
        )
        self.assertEqual(bmi1.id, bmi2.id)
        self.assertEqual(order, bmi2.order)
        self.assertEqual(old_count + 1, ButtonMenuItem.objects.count())

    def test_create_if_needed__no_ctype(self):
        "Default config (content_type=None)."
        old_count = ButtonMenuItem.objects.count()
        bmi = ButtonMenuItem.objects.create_if_needed(
            model=None, button=TestButton, order=15,
        )
        self.assertEqual(old_count + 1, ButtonMenuItem.objects.count())
        self.assertIsNone(bmi.content_type)

    def test_create_if_needed__button_id(self):
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

    def test_create_if_needed__superuser(self):
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

    def test_create_if_needed__role(self):
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

    def test_proxy(self):
        old_count = ButtonMenuItem.objects.count()

        order1 = 10
        proxy1 = ButtonMenuItem.objects.proxy(
            model=FakeContact, button=TestButton, order=order1,
        )
        self.assertEqual(FakeContact,     proxy1.model)
        self.assertEqual(FakeContact,     proxy1.content_type.model_class())
        self.assertEqual(TestButton,      proxy1.button)
        self.assertEqual(TestButton.id,   proxy1.button_id)
        self.assertEqual(order1,           proxy1.order)
        self.assertIsNone(proxy1.role)
        self.assertFalse(proxy1.superuser)

        bmi1, created1 = proxy1.get_or_create()
        self.assertIs(created1, True)
        self.assertIsInstance(bmi1, ButtonMenuItem)
        self.assertTrue(bmi1.pk)
        self.assertEqual(old_count + 1, ButtonMenuItem.objects.count())

        refreshed_bmi1 = self.get_object_or_fail(
            ButtonMenuItem,
            content_type=ContentType.objects.get_for_model(FakeContact),
            button_id=TestButton.id,
            superuser=False,
            role=None,
        )
        self.assertEqual(order1, refreshed_bmi1.order)

        # ---
        bmi1_again, created_again = proxy1.get_or_create()
        self.assertIs(created_again, False)
        self.assertEqual(refreshed_bmi1.id, bmi1_again.id)

        # ---
        order2 = 5
        proxy2 = ButtonMenuItem.objects.proxy(button=TestButton, order=order2)
        self.assertIsNone(proxy2.model)
        self.assertIsNone(proxy2.content_type)
        self.assertEqual(TestButton, proxy2.button)
        self.assertEqual(order2,     proxy2.order)

        bmi2, created2 = proxy2.get_or_create()
        self.assertIs(created2, True)
        self.assertTrue(bmi1_again.pk)
        self.assertEqual(old_count + 2, ButtonMenuItem.objects.count())
        self.assertIsNone(bmi2.content_type)
        self.assertEqual(TestButton, bmi2.button)
        self.assertEqual(order2,     bmi2.order)

    def test_proxy__superuser(self):
        proxy1 = ButtonMenuItem.objects.proxy(
            model=FakeContact, button=Restrict2SuperusersButton, order=1,
            role='superuser',
        )
        self.assertIsNone(proxy1.role)
        self.assertIs(proxy1.superuser, True)

        bmi1, created1 = proxy1.get_or_create()
        self.assertIs(created1, True)
        self.assertIsInstance(bmi1, ButtonMenuItem)
        self.get_object_or_fail(
            ButtonMenuItem,
            content_type=ContentType.objects.get_for_model(FakeContact),
            button_id=Restrict2SuperusersButton.id,
            superuser=True, role=None,
        )

        # ---
        _, created_again = proxy1.get_or_create()
        self.assertFalse(created_again)

        # ---
        _, created2 = ButtonMenuItem.objects.proxy(
            model=FakeContact, button=Restrict2SuperusersButton, order=1,
        ).get_or_create()
        self.assertTrue(created2)

    def test_proxy__role(self):
        role1 = self.get_regular_role()
        proxy1 = ButtonMenuItem.objects.proxy(
            model=FakeContact, button=TestButton, order=1,
            role=str(role1.uuid),  # TODO: accept UUIDs?
        )
        self.assertFalse(proxy1.superuser)
        self.assertEqual(role1, proxy1.role)

        bmi1, created1 = proxy1.get_or_create()
        self.assertIs(created1, True)
        self.get_object_or_fail(
            ButtonMenuItem,
            content_type=ContentType.objects.get_for_model(FakeContact),
            button_id=TestButton.id,
            superuser=False, role=role1,
        )

        # Get if it already exists ---
        _, created_again = proxy1.get_or_create()
        self.assertFalse(created_again)

        # Create if different role ---
        proxy2 = ButtonMenuItem.objects.proxy(
            model=FakeContact, button=TestButton, order=1,
        )
        _, created2 = proxy2.get_or_create()
        self.assertTrue(created2)

        # Role setter (UserRole instance) ---
        role2 = self.create_role(name='Lite')
        proxy2.role = role2
        self.assertEqual(role2, proxy2.role)

        # Role setter (UUID instance) ---
        proxy2.role = role1.uuid
        self.assertEqual(role1, proxy2.role)

    def test_proxy__order(self):
        proxy = ButtonMenuItem.objects.proxy(button=TestButton, order=1)
        order = 10
        proxy.order = order
        self.assertEqual(order, proxy.order)

    def test_proxy__buttons(self):
        proxy = ButtonMenuItem.objects.proxy(button=Restrict2SuperusersButton, order=1)
        proxy.button = TestButton
        self.assertEqual(TestButton, proxy.button)

    def test_proxy__helper_errors(self):
        proxy = ButtonMenuItem.objects.proxy(button=TestButton, order=1)
        with self.assertRaises(AttributeError):
            proxy.save  # NOQA

        with self.assertRaises(ValueError):
            ButtonMenuItem.objects.proxy(
                button=TestButton, order=1,
                model=FakeSector,  # <===
            )

        with self.assertRaises(ValueError):
            ButtonMenuItem.objects.proxy(
                button=TestButton, order=1,
                role=FakeSector,  # <===
            )

        with self.assertRaises(ValueError):
            ButtonMenuItem.objects.proxy(
                button=TestButton, order=1,
                role='not-uuid',  # <===
            )

    def test_proxy__errors(self):
        with self.assertRaises(ValueError) as cm:
            ButtonMenuItemProxy(
                instance=ButtonMenuItem(content_type=FakeContact),  # <
                model=None, role=None,
            )
        self.assertIn(
            'The field "content_type" of the ButtonMenuItem must not be set',
            str(cm.exception),
        )

        with self.assertRaises(ValueError) as cm:
            ButtonMenuItemProxy(
                instance=ButtonMenuItem(
                    button_id=TestButton.id, order=1,
                    role=self.get_regular_role(),  # <==
                ),
                model=None, role=None,
            )
        self.assertIn(
            'The field "role" of the ButtonMenuItem must not be set',
            str(cm.exception),
        )

        with self.assertRaises(ValueError) as cm:
            ButtonMenuItemProxy(
                instance=ButtonMenuItem(
                    button_id=TestButton.id, order=1,
                    superuser=True,  # <==
                ),
                model=None, role=None,
            )
        self.assertIn(
            'The field "superuser" of the ButtonMenuItem must not be set',
            str(cm.exception),
        )

        bmi = ButtonMenuItem.objects.create(button_id=TestButton.id, order=1)
        with self.assertRaises(ValueError) as cm:
            ButtonMenuItemProxy(instance=bmi, model=None, role=None)
        self.assertIn(
            'The field "pk" of the ButtonMenuItem must not be set',
            str(cm.exception),
        )


class ButtonMenuItemTestCase(_ButtonMenuItemTestCase):
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
