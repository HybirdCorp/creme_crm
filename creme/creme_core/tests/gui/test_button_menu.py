from django.test import RequestFactory

from creme.creme_core.gui.button_menu import Button, ButtonsRegistry
from creme.creme_core.models import FakeContact

from ..base import CremeTestCase
from ..fake_models import FakeOrganisation


class ButtonMenuTestCase(CremeTestCase):
    def test_button(self):
        user = self.get_root_user()

        class TestButton(Button):
            id = Button.generate_id('creme_core', 'test_button')

        class FakeRequest:
            def __init__(this, user):
                this.user = user

        c = FakeContact(first_name='Casca', last_name='Mylove')
        request = FakeRequest(user=user)

        button = TestButton()
        self.assertIs(button.is_allowed(entity=c, request=request), True)
        self.assertIs(button.ok_4_display(entity=c), True)
        self.assertDictEqual(
            {
                'description': '',
                'is_allowed': True,
                'template_name': 'creme_core/buttons/place-holder.html',
                'verbose_name': 'BUTTON',
            },
            button.get_context(entity=c, request=request),
        )

    def test_button__permissions(self):
        role = self.create_role(name='Role#1', allowed_apps=['documents', 'persons'])
        user = self.create_user(role=role)

        class TestButton01(Button):
            id = Button.generate_id('creme_core', 'test_button_1')
            verbose_name = 'My test button'
            description = 'Very useful button'
            template_name = 'creme_core/tests/unit/buttons/test_ttag_creme_menu.html'
            permissions = 'creme_core'

        class TestButton02(TestButton01):
            id = Button.generate_id('creme_core', 'test_button_2')
            permissions = 'documents'

        class TestButton03(TestButton01):
            id = Button.generate_id('creme_core', 'test_button_3')
            permissions = ['creme_core', 'documents']

        class TestButton04(TestButton01):
            id = Button.generate_id('creme_core', 'test_button_4')
            permissions = ['persons', 'documents']

        class FakeRequest:
            def __init__(this, user):
                this.user = user

        c = FakeContact(first_name='Casca', last_name='Mylove')

        request = FakeRequest(user=user)
        button1 = TestButton01()
        self.assertIs(button1.is_allowed(entity=c, request=request), False)
        self.assertDictEqual(
            {
                'description': TestButton01.description,
                'is_allowed': False,
                'template_name': TestButton01.template_name,
                'verbose_name': TestButton01.verbose_name,
            },
            button1.get_context(entity=c, request=request),
        )

        self.assertIs(TestButton02().is_allowed(entity=c, request=request), True)
        self.assertIs(TestButton03().is_allowed(entity=c, request=request), False)
        self.assertIs(TestButton04().is_allowed(entity=c, request=request), True)

    def test_registry(self):
        class TestButton1(Button):
            id = Button.generate_id('creme_core', 'test_button_registry_1')

        class TestButton2(Button):
            id = Button.generate_id('creme_core', 'test_button_registry_2')

            def ok_4_display(self, entity):
                return False

        class TestButton3(Button):
            id = Button.generate_id('creme_core', 'test_button_registry_3')

        class TestButton4(Button):
            id = Button.generate_id('creme_core', 'test_button_registry_4')

        registry = ButtonsRegistry()
        registry.register(TestButton1, TestButton2, TestButton3, TestButton4)

        class DuplicatedTestButton(Button):
            id = TestButton1.id

        with self.assertRaises(ButtonsRegistry.RegistrationError):
            registry.register(DuplicatedTestButton)

        get = registry.get_button
        self.assertIsInstance(get(TestButton1.id), TestButton1)
        self.assertIsInstance(get(TestButton2.id), TestButton2)
        self.assertIsNone(get(Button.generate_id('creme_core', 'test_button_registry_invalid')))

        c = FakeContact(first_name='Casca', last_name='Mylove')
        buttons = [
            *registry.get_buttons(
                [
                    TestButton3.id,
                    TestButton2.id,  # No because ok_4_display() returns False
                    'test_button_registry_invalid',
                    TestButton1.id,
                ],
                entity=c,
            ),
        ]
        self.assertIsList(buttons, length=2)
        self.assertIsInstance(buttons[0], TestButton3)
        self.assertIsInstance(buttons[1], TestButton1)

        all_button_items = [*registry]
        self.assertEqual(4, len(all_button_items))

        button_item = all_button_items[0]
        self.assertIsInstance(button_item[1], Button)
        self.assertEqual(button_item[0], button_item[1].id)

    def test_registry__duplicated_id(self):
        class TestButton1(Button):
            id = Button.generate_id('creme_core', 'test_button_registry_1')

        class TestButton2(TestButton1):
            # id = Button.generate_id('creme_core', 'test_button_registry_2') NOPE
            pass

        registry = ButtonsRegistry()

        with self.assertRaises(ButtonsRegistry.RegistrationError) as cm:
            registry.register(TestButton1, TestButton2)

        self.assertEqual(
            f"Duplicated button's ID (or button registered twice): {TestButton1.id}",
            str(cm.exception)
        )

    def test_registry__empty_id(self):
        class TestButton(Button):
            # id = Button.generate_id('creme_core', 'test_button_registry') # NOPE
            pass

        registry = ButtonsRegistry()

        with self.assertRaises(ButtonsRegistry.RegistrationError) as cm:
            registry.register(TestButton)

        self.assertEqual(
            f'Button class with empty ID: {TestButton}',
            str(cm.exception),
        )

    def test_registry__permissions(self):
        basic_user = self.login_as_standard(
            allowed_apps=['creme_core', 'persons'],
            creatable_models=[FakeContact],
        )

        class TestButton01(Button):
            id = Button.generate_id('creme_core', 'test_button_registry04_01')
            permissions = 'creme_core'

        entity = FakeContact.objects.create(
            user=basic_user, first_name='Musubi', last_name='Susono',
        )

        factory = RequestFactory()
        url = entity.get_absolute_url()

        def create_request(user):
            request = factory.get(url)
            request.user = user
            return request

        basic_ctxt = {'request': create_request(basic_user),           'entity': entity}
        super_ctxt = {'request': create_request(self.get_root_user()), 'entity': entity}

        is_allowed1 = TestButton01().is_allowed
        self.assertIs(is_allowed1(**super_ctxt), True)
        self.assertIs(is_allowed1(**basic_ctxt), True)

        # Other app ---
        class TestButton02(Button):
            id = Button.generate_id('creme_core', 'test_button_registry04_02')
            permissions = 'documents'

        is_allowed2 = TestButton02().is_allowed
        self.assertIs(is_allowed2(**super_ctxt), True)
        self.assertIs(is_allowed2(**basic_ctxt), False)

        # Creation permission ---
        class TestButton03(Button):
            id = Button.generate_id('creme_core', 'test_button_registry04_03')
            permissions = 'creme_core.add_fakecontact'

        class TestButton04(Button):
            id = Button.generate_id('creme_core', 'test_button_registry04_04')
            permissions = 'creme_core.add_fakeorganisation'

        self.assertTrue(TestButton03().is_allowed(**basic_ctxt))
        self.assertFalse(TestButton04().is_allowed(**basic_ctxt))

        # Several permissions ---
        class TestButton05(Button):
            id = Button.generate_id('creme_core', 'test_button_registry04_05')
            permissions = ['persons', 'creme_core.add_fakecontact']

        class TestButton06(Button):
            id = Button.generate_id('creme_core', 'test_button_registry04_06')
            permissions = ['persons', 'creme_core.add_fakeorganisation']

        self.assertTrue(TestButton05().is_allowed(**basic_ctxt))
        self.assertFalse(TestButton06().is_allowed(**basic_ctxt))

    def test_registry__allowed_ctypes(self):
        user = self.get_root_user()

        class TestButton1(Button):
            id = Button.generate_id('creme_core', 'test_button_registry1')

        class TestButton2(Button):
            id = Button.generate_id('creme_core', 'test_button_registry2')

            def get_ctypes(this):
                return [FakeOrganisation, FakeContact]

        class TestButton3(Button):
            id = Button.generate_id('creme_core', 'test_button_registry3')

            def get_ctypes(this):
                return [FakeOrganisation]

        registry = ButtonsRegistry().register(TestButton1, TestButton2, TestButton3)

        c = FakeContact.objects.create(
            user=user, first_name='Musubi', last_name='Susono',
        )

        with self.assertLogs(level='WARNING') as logs_manager:
            buttons = [
                *registry.get_buttons(
                    [
                        TestButton3.id,  # No because ctype is not allowed
                        TestButton2.id,
                        TestButton1.id,
                    ],
                    entity=c,
                ),
            ]

        self.assertIsList(buttons, length=2)
        self.assertIsInstance(buttons[0], TestButton2)
        self.assertIsInstance(buttons[1], TestButton1)

        self.assertIn(
            f'WARNING:creme.creme_core.gui.button_menu:'
            f'This button cannot be displayed on this content type '
            f'(you have a config problem): {TestButton3.id}',
            logs_manager.output,
        )

    def test_registry_unregister(self):
        class TestButton1(Button):
            id = Button.generate_id('creme_core', 'test_button_registry_1')

        class TestButton2(Button):
            id = Button.generate_id('creme_core', 'test_button_registry_2')

        class TestButton3(Button):
            id = Button.generate_id('creme_core', 'test_button_registry_3')

        registry = ButtonsRegistry().register(TestButton1, TestButton2, TestButton3)

        registry.unregister(TestButton1, TestButton3)
        get = registry.get_button
        self.assertIsNone(get(TestButton1.id))
        self.assertIsNone(get(TestButton3.id))
        self.assertIsInstance(get(TestButton2.id), TestButton2)

        # ---
        class TestButton4(Button):
            pass

        with self.assertRaises(registry.UnRegistrationError) as cm1:
            registry.unregister(TestButton4)
        self.assertEqual(
            f'Button class with empty ID: {TestButton4}',
            str(cm1.exception),
        )

        # ---
        with self.assertRaises(registry.UnRegistrationError) as cm2:
            registry.unregister(TestButton2, TestButton1)
        self.assertEqual(
            f'Button class with invalid ID (already unregistered?): {TestButton1}',
            str(cm2.exception),
        )
