from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.utils.translation import gettext as _

from creme.creme_core.gui.button_menu import Button, ButtonRegistry
from creme.creme_core.models import FakeContact, FakeOrganisation

from ..base import CremeTestCase


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
        # self.assertIs(button.ok_4_display(entity=c), True)
        self.assertIs(button.is_displayed(entity=c, request=request), True)

        # ctxt = button.get_context(entity=c, request=request)
        # self.assertIsDict(ctxt, length=4)
        # self.assertEqual('',                                     ctxt.get('description'))
        # self.assertEqual('creme_core/buttons/place-holder.html', ctxt.get('template_name'))
        # self.assertEqual('BUTTON',                               ctxt.get('verbose_name'))
        #
        # is_allowed_func = ctxt.get('is_allowed')
        # self.assertTrue(callable(is_allowed_func))
        #
        # with self.assertLogs(level='CRITICAL'):
        #     is_allowed = is_allowed_func()
        # self.assertIs(is_allowed, True)
        self.assertDictEqual(
            {
                'description': '',
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
        msg = _('You are not allowed to access to the app: {}').format(_('Core'))
        button1 = TestButton01()

        # ctxt = button1.get_context(entity=c, request=request)
        #
        # with self.assertRaises(PermissionDenied) as cm1:
        #     button1.check_permissions(entity=c, request=request)
        # self.assertEqual(msg, str(cm1.exception))
        #
        # self.assertIsDict(ctxt, length=5)
        # self.assertEqual(TestButton01.description,   ctxt.get('description'))
        # self.assertEqual(TestButton01.template_name, ctxt.get('template_name'))
        # self.assertEqual(TestButton01.verbose_name,  ctxt.get('verbose_name'))
        # self.assertEqual(msg,                        ctxt.get('permission_error'))
        #
        # is_allowed_func = ctxt.get('is_allowed')
        # self.assertTrue(callable(is_allowed_func))
        #
        # with self.assertLogs(level='CRITICAL'):
        #     is_allowed = is_allowed_func()
        # self.assertIs(is_allowed, False)
        self.assertDictEqual(
            {
                'description': TestButton01.description,
                'template_name': TestButton01.template_name,
                'verbose_name': TestButton01.verbose_name,
                'permission_error': msg,
            },
            button1.get_context(entity=c, request=request),
        )

        with self.assertNoException():
            TestButton02().check_permissions(entity=c, request=request)

        with self.assertRaises(PermissionDenied) as cm3:
            TestButton03().check_permissions(entity=c, request=request)
        self.assertEqual(msg, str(cm3.exception))

        with self.assertNoException():
            TestButton04().check_permissions(entity=c, request=request)

    def test_registry(self):
        class TestButton1(Button):
            id = Button.generate_id('creme_core', 'test_button_registry_1')

        class TestButton2(Button):
            id = Button.generate_id('creme_core', 'test_button_registry_2')

            # def ok_4_display(self, entity):
            def is_displayed(this, *, entity, request):
                return False

        class TestButton3(Button):
            id = Button.generate_id('creme_core', 'test_button_registry_3')

        class TestButton4(Button):
            id = Button.generate_id('creme_core', 'test_button_registry_4')

        registry = ButtonRegistry()

        with self.assertNoLogs():
            registry.register(TestButton1, TestButton2, TestButton3, TestButton4)

        class DuplicatedTestButton(Button):
            id = TestButton1.id

        with self.assertRaises(ButtonRegistry.RegistrationError):
            registry.register(DuplicatedTestButton)

        get = registry.get_button
        self.assertIsInstance(get(TestButton1.id), TestButton1)
        self.assertIsInstance(get(TestButton2.id), TestButton2)
        self.assertIsNone(get(Button.generate_id('creme_core', 'test_button_registry_invalid')))

        c = FakeContact(first_name='Casca', last_name='Mylove')
        buttons = [
            # *registry.get_buttons(
            #     [
            #         TestButton3.id,
            #         TestButton2.id,  # No because ok_4_display() returns False
            #         'test_button_registry_invalid',
            #         TestButton1.id,
            #     ],
            #     entity=c,
            # ),
            *registry.get_buttons(
                button_ids=[
                    TestButton3.id,
                    TestButton2.id,  # No because ok_4_display() returns False
                    'test_button_registry_invalid',
                    TestButton1.id,
                ],
                entity=c,
                request=self.build_request(),
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

        # ---
        class ProblematicTestButton(Button):
            id = Button.generate_id('creme_core', 'test_problematic')

            def ok_4_display(self, entity):
                return False

        with self.assertLogs(level='CRITICAL'):
            registry.register(ProblematicTestButton)

    def test_registry__duplicated_id(self):
        class TestButton1(Button):
            id = Button.generate_id('creme_core', 'test_button_registry_1')

        class TestButton2(TestButton1):
            # id = Button.generate_id('creme_core', 'test_button_registry_2') NOPE
            pass

        registry = ButtonRegistry()

        with self.assertRaises(ButtonRegistry.RegistrationError) as cm:
            registry.register(TestButton1, TestButton2)

        self.assertEqual(
            f"Duplicated button's ID (or button registered twice): {TestButton1.id}",
            str(cm.exception)
        )

    def test_registry__empty_id(self):
        class TestButton(Button):
            # id = Button.generate_id('creme_core', 'test_button_registry') # NOPE
            pass

        registry = ButtonRegistry()

        with self.assertRaises(ButtonRegistry.RegistrationError) as cm:
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

        button1 = TestButton01()
        with self.assertNoException():
            button1.check_permissions(**super_ctxt)
            button1.check_permissions(**basic_ctxt)

        # Other app ---
        class TestButton02(Button):
            id = Button.generate_id('creme_core', 'test_button_registry04_02')
            permissions = 'documents'

        button2 = TestButton02()
        with self.assertNoException():
            button2.check_permissions(**super_ctxt)

        with self.assertRaises(PermissionDenied) as cm2:
            button2.check_permissions(**basic_ctxt)
        self.assertEqual(
            _('You are not allowed to access to the app: {}').format(_('Documents')),
            str(cm2.exception),
        )

        # Creation permission ---
        class TestButton03(Button):
            id = Button.generate_id('creme_core', 'test_button_registry04_03')
            permissions = 'creme_core.add_fakecontact'

        class TestButton04(Button):
            id = Button.generate_id('creme_core', 'test_button_registry04_04')
            permissions = 'creme_core.add_fakeorganisation'

        with self.assertNoException():
            TestButton03().check_permissions(**basic_ctxt)

        with self.assertRaises(PermissionDenied) as cm4:
            TestButton04().check_permissions(**basic_ctxt)
        self.assertEqual(
            _('You are not allowed to create: {}').format('Test Organisation'),
            str(cm4.exception),
        )

        # Several permissions ---
        class TestButton05(Button):
            id = Button.generate_id('creme_core', 'test_button_registry04_05')
            permissions = ['persons', 'creme_core.add_fakecontact']

        class TestButton06(Button):
            id = Button.generate_id('creme_core', 'test_button_registry04_06')
            permissions = ['persons', 'creme_core.add_fakeorganisation']

        with self.assertNoException():
            TestButton05().check_permissions(**basic_ctxt)

        with self.assertRaises(PermissionDenied) as cm6:
            TestButton06().check_permissions(**basic_ctxt)
        self.assertEqual(
            _('You are not allowed to create: {}').format('Test Organisation'),
            str(cm6.exception),
        )

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

        registry = ButtonRegistry().register(TestButton1, TestButton2, TestButton3)

        c = FakeContact.objects.create(
            user=user, first_name='Musubi', last_name='Susono',
        )

        with self.assertLogs(level='WARNING') as logs_manager:
            buttons = [
                # *registry.get_buttons(
                #     [
                #         TestButton3.id,  # No because ctype is not allowed
                #         TestButton2.id,
                #         TestButton1.id,
                #     ],
                #     entity=c,
                # ),
                *registry.get_buttons(
                    button_ids=[
                        TestButton3.id,  # No because ctype is not allowed
                        TestButton2.id,
                        TestButton1.id,
                    ],
                    entity=c,
                    request=self.build_request(user=user),
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

        registry = ButtonRegistry().register(TestButton1, TestButton2, TestButton3)

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

    def test_registry_mandatory_buttons(self):
        class TestButton1(Button):
            id = Button.generate_id('creme_core', 'test_mandatory_button_1')

        class TestButton2(Button):
            id = Button.generate_id('creme_core', 'test_mandatory_button_2')

        class TestButton3(Button):
            id = Button.generate_id('creme_core', 'test_mandatory_button_3')

            def get_ctypes(this):
                return [FakeOrganisation, FakeContact]

        class TestButton4(Button):
            id = Button.generate_id('creme_core', 'test_mandatory_button_4')

            def get_ctypes(this):
                return [FakeOrganisation]

        registry = ButtonRegistry().register_mandatory(
            button_class=TestButton1,
        ).register_mandatory(
            button_class=TestButton2, priority=8,
        ).register_mandatory(
            button_class=TestButton3, priority=10,
        ).register_mandatory(
            button_class=TestButton4, priority=5,
        )

        def assertButtonsEqual(expected_classes, buttons):
            self.assertEqual(len(expected_classes), len(buttons))
            for button_cls, button in zip(expected_classes, buttons):
                self.assertIsInstance(button, button_cls)

        request = self.build_request()
        assertButtonsEqual(
            [TestButton1, TestButton2, TestButton3],
            # [*registry.mandatory_buttons(entity=FakeContact())],
            [*registry.mandatory_buttons(entity=FakeContact(), request=request)],
        )
        assertButtonsEqual(
            [TestButton1, TestButton4, TestButton2, TestButton3],
            # [*registry.mandatory_buttons(entity=FakeOrganisation())],
            [*registry.mandatory_buttons(entity=FakeOrganisation(), request=request)],
        )

        self.assertIsNone(registry.get_button(TestButton2.id))
        # TODO?
        # self.assertIsInstance(
        #     registry.get_mandatory_button(button_id=TestButton2.id, model=FakeOrganisation),
        #     TestButton2,
        # )
        assertButtonsEqual(
            [TestButton1, TestButton4, TestButton3],
            # [*registry.get_buttons(
            #     entity=FakeOrganisation(),
            #     id_list=[TestButton1.id, TestButton4.id, TestButton3.id],
            # )],
            [*registry.get_buttons(
                entity=FakeOrganisation(),
                button_ids=[TestButton1.id, TestButton4.id, TestButton3.id],
                request=request,
            )],
        )
        assertButtonsEqual(
            [TestButton1, TestButton3],  # TestButton4 is ignored
            # [*registry.get_buttons(
            #     entity=FakeContact(),
            #     id_list=[TestButton1.id, TestButton4.id, TestButton3.id],
            # )],
            [*registry.get_buttons(
                entity=FakeContact(),
                button_ids=[TestButton1.id, TestButton4.id, TestButton3.id],
                request=request,
            )],
        )

        # Unregistering (Button with no related model) ---
        registry.unregister_mandatory(TestButton2)
        assertButtonsEqual(
            [TestButton1, TestButton3],
            # [*registry.mandatory_buttons(entity=FakeContact())],
            [*registry.mandatory_buttons(entity=FakeContact(), request=request)],
        )
        assertButtonsEqual(
            [TestButton1, TestButton4, TestButton3],
            # [*registry.mandatory_buttons(entity=FakeOrganisation())],
            [*registry.mandatory_buttons(entity=FakeOrganisation(), request=request)],
        )

        # Unregistering (Button with related model) ---
        registry.unregister_mandatory(TestButton3)
        assertButtonsEqual(
            # [TestButton1], [*registry.mandatory_buttons(entity=FakeContact())],
            [TestButton1], [*registry.mandatory_buttons(entity=FakeContact(), request=request)],
        )
        assertButtonsEqual(
            [TestButton1, TestButton4],
            # [*registry.mandatory_buttons(entity=FakeOrganisation())],
            [*registry.mandatory_buttons(entity=FakeOrganisation(), request=request)],
        )

    def test_registry_mandatory_buttons__empty_id(self):
        class TestButton(Button):
            # id = ...
            pass

        registry = ButtonRegistry()

        with self.assertRaises(ButtonRegistry.RegistrationError):
            registry.register_mandatory(button_class=TestButton)

    def test_registry_mandatory_buttons__duplicated_id1(self):
        class TestButton1(Button):
            id = Button.generate_id('creme_core', 'test_button_registry_1')

        class TestButton2(Button):
            # id = Button.generate_id('creme_core', 'test_button_registry_2')
            id = TestButton1.id  # <===

        registry = ButtonRegistry().register_mandatory(button_class=TestButton1)

        with self.assertRaises(ButtonRegistry.RegistrationError):
            registry.register_mandatory(button_class=TestButton2)

    def test_registry_mandatory_buttons__duplicated_id2(self):
        class TestButton1(Button):
            id = Button.generate_id('creme_core', 'test_button_registry_1')

            def get_ctypes(this):
                return [FakeContact]

        class TestButton2(Button):
            # id = Button.generate_id('creme_core', 'test_button_registry_3')
            id = TestButton1.id  # <===

            def get_ctypes(this):
                return [FakeOrganisation, FakeContact]

        registry = ButtonRegistry().register_mandatory(button_class=TestButton1)

        with self.assertRaises(ButtonRegistry.RegistrationError):
            registry.register_mandatory(button_class=TestButton2)

    def test_registry_unregister_mandatory_errors(self):
        class TestButton1(Button):
            # id = ''
            pass

        class TestButton2(Button):
            id = Button.generate_id('creme_core', 'test_button_registry_2')

        registry = ButtonRegistry().register_mandatory(button_class=TestButton2)

        with self.assertRaises(ButtonRegistry.UnRegistrationError) as cm1:
            registry.unregister_mandatory(button_class=TestButton1)

        self.assertStartsWith(str(cm1.exception), 'Button class with empty ID:')

        # ---
        registry.unregister_mandatory(button_class=TestButton2)

        with self.assertRaises(ButtonRegistry.UnRegistrationError) as cm2:
            registry.unregister_mandatory(button_class=TestButton2)

        self.assertStartsWith(
            str(cm2.exception),
            'Button class with invalid ID (already unregistered?): ',
        )

    def test_registry_mandatory_buttons__ok_for_display(self):
        class TestButton(Button):
            id = Button.generate_id('creme_core', 'test_mandatory_button')

            # def ok_4_display(this, entity):
            def is_displayed(self, *, entity, request):
                return False

        with self.assertNoLogs():
            registry = ButtonRegistry().register_mandatory(TestButton)

        self.assertFalse(
            # [*registry.mandatory_buttons(entity=FakeOrganisation())],
            [*registry.mandatory_buttons(
                entity=FakeOrganisation(), request=self.build_request(),
            )],
        )

        # ---
        class ProblematicTestButton(Button):
            id = Button.generate_id('creme_core', 'test_problematic')

            def ok_4_display(this, entity):
                return False

        with self.assertLogs(level='CRITICAL'):
            registry.register_mandatory(ProblematicTestButton)
