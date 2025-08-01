from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.gui.button_menu import Button, button_registry
from creme.creme_core.models import (
    ButtonMenuItem,
    FakeContact,
    FakeInvoiceLine,
    FakeOrganisation,
)
from creme.creme_core.tests.base import CremeTestCase


class TestButton1(Button):
    id = Button.generate_id('creme_config', 'test_buttonconfig_1')
    verbose_name = 'Test button #1'


class TestButton2(Button):
    id = Button.generate_id('creme_config', 'test_buttonconfig_2')
    verbose_name = 'Test button #2'


class TestButton3(Button):
    id = Button.generate_id('creme_config', 'test_buttonconfig_3')
    verbose_name = 'Test button #3'


class TestButton4(Button):
    id = Button.generate_id('creme_config', 'test_buttonconfig_4')
    verbose_name = 'Test button #4'

    def get_ctypes(self):
        return [FakeContact, FakeOrganisation]


class TestButton5(Button):
    id = Button.generate_id('creme_config', 'test_buttonconfig_5')
    verbose_name = 'Test button #5'

    def get_ctypes(self):
        return [FakeOrganisation]  # No Contact


class ButtonMenuConfigTestCase(CremeTestCase):
    DEL_URL = reverse('creme_config__delete_buttons')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.contact_ct = ct = ContentType.objects.get_for_model(FakeContact)
        contact_conf = ButtonMenuItem.objects.filter(content_type=ct)
        cls._buttonconf_backup = [*contact_conf]
        contact_conf.delete()

        button_registry.register(
            TestButton1, TestButton2, TestButton3, TestButton4, TestButton5
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        ButtonMenuItem.objects.bulk_create(cls._buttonconf_backup)
        button_registry.unregister(
            TestButton1, TestButton2, TestButton3, TestButton4, TestButton5,
        )

    def _login_as_core_admin(self):
        return self.login_as_standard(admin_4_apps=['creme_core'])

    def test_portal(self):
        self._login_as_core_admin()

        response = self.assertGET200(reverse('creme_config__buttons'))
        self.assertTemplateUsed(response, 'creme_config/portals/button-menu.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

    def test_add__base(self):
        self.login_as_root()

        ct = self.contact_ct
        url = reverse('creme_config__add_base_buttons')
        ctxt1 = self.assertGET200(url).context
        self.assertEqual(_('New buttons base configuration'), ctxt1.get('title'))

        with self.assertNoException():
            ctypes = ctxt1['form'].fields['ctype'].ctypes

        self.assertIn(ct, ctypes)
        # FakeInvoiceLine is registered in brick_registry as invalid (cannot have a detail-view)
        self.assertNotIn(ContentType.objects.get_for_model(FakeInvoiceLine), ctypes)

        # ---
        step_key = 'button_menu_base_creation_wizard-current_step'
        response2 = self.assertPOST200(
            url,
            data={
                step_key: '0',
                '0-ctype': ct.id,
            },
        )

        ctxt2 = response2.context
        self.assertEqual(
            _('New buttons configuration for «{model}»').format(model=ct),
            ctxt2.get('title'),
        )

        with self.assertNoException():
            choices = ctxt2['form'].fields['button_ids'].choices

        self.assertInChoices(value=TestButton1.id, label=TestButton1(), choices=choices)
        self.assertInChoices(value=TestButton2.id, label=TestButton2(), choices=choices)
        self.assertInChoices(value=TestButton3.id, label=TestButton3(), choices=choices)
        self.assertInChoices(value=TestButton4.id, label=TestButton4(), choices=choices)
        self.assertNotInChoices(value=TestButton5.id, choices=choices)

        # --
        response3 = self.client.post(
            url,
            data={
                step_key: '1',
                '1-button_ids': [TestButton1.id],
            },
        )
        self.assertNoFormError(response3)
        self.assertListEqual(
            [(TestButton1.id, 1000)],
            [
                *ButtonMenuItem.objects
                               .filter(content_type=ct, superuser=False, role=None)
                               .values_list('button_id', 'order'),
            ],
        )

    def test_add__role(self):
        user = self._login_as_core_admin()
        role = user.role
        url = reverse('creme_config__add_role_buttons', args=(role.id,))

        # GET (error) ---
        self.assertGET409(url)

        # GET ---
        create_bmi = ButtonMenuItem.objects.create
        create_bmi(button_id='', order=1, role=role)
        create_bmi(button=TestButton1, order=1, role=role, content_type=FakeOrganisation)

        step0_get_ctxt = self.assertGET200(url).context
        self.assertEqual(
            _('New buttons configuration for role «{role}»').format(role=role),
            step0_get_ctxt.get('title'),
        )

        with self.assertNoException():
            ctypes = step0_get_ctxt['form'].fields['ctype'].ctypes

        ct = self.contact_ct
        self.assertIn(ct, ctypes)

        get_ct = ContentType.objects.get_for_model
        self.assertNotIn(get_ct(FakeOrganisation), ctypes)  # Already exists
        # FakeInvoiceLine is registered in brick_registry as invalid (cannot have a detail-view)
        self.assertNotIn(get_ct(FakeInvoiceLine), ctypes)

        # POST1 ---
        step_key = 'button_menu_role_creation_wizard-current_step'
        step0_post_response = self.assertPOST200(
            url,
            data={
                step_key: '0',
                '0-ctype': ct.id,
            },
        )

        step0_post_ctxt = step0_post_response.context
        self.assertEqual(
            _('New buttons configuration for «{model}»').format(model=ct),
            step0_post_ctxt.get('title'),
        )

        with self.assertNoException():
            choices = step0_post_ctxt['form'].fields['button_ids'].choices

        self.assertInChoices(value=TestButton1.id, label=TestButton1(), choices=choices)
        self.assertInChoices(value=TestButton2.id, label=TestButton2(), choices=choices)
        self.assertInChoices(value=TestButton3.id, label=TestButton3(), choices=choices)
        self.assertInChoices(value=TestButton4.id, label=TestButton4(), choices=choices)
        self.assertNotInChoices(value=TestButton5.id, choices=choices)

        # POST 2 ---
        self.assertNoFormError(self.client.post(
            url,
            data={
                step_key: '1',
                '1-button_ids': [TestButton1.id],
            },
        ))

        def _buttons_info(ctype):
            return [
                *ButtonMenuItem.objects.filter(
                    content_type=ctype, superuser=False, role=role,
                ).values_list('button_id', 'order'),
            ]

        self.assertListEqual([(TestButton1.id, 1000)], _buttons_info(ctype=ct))
        self.assertListEqual([('', 1)],               _buttons_info(ctype=None))

    def test_add__superuser(self):
        self.login_as_root()

        url = reverse('creme_config__add_superuser_buttons')

        # GET (error) ---
        self.assertGET409(url)

        # GET ---
        create_bmi = partial(ButtonMenuItem.objects.create, superuser=True, order=1)
        create_bmi(button_id='')
        create_bmi(button=TestButton5, content_type=FakeOrganisation)

        step0_get_ctxt = self.assertGET200(url).context
        self.assertEqual(
            _('New buttons configuration for superusers'),
            step0_get_ctxt.get('title'),
        )

        with self.assertNoException():
            ctypes = step0_get_ctxt['form'].fields['ctype'].ctypes

        ct = self.contact_ct
        self.assertIn(ct, ctypes)

        get_ct = ContentType.objects.get_for_model
        self.assertNotIn(get_ct(FakeOrganisation), ctypes)  # Already exists
        # FakeInvoiceLine is registered in brick_registry as invalid (cannot have a detail-view)
        self.assertNotIn(get_ct(FakeInvoiceLine), ctypes)

        # ---
        step_key = 'button_menu_superuser_creation_wizard-current_step'
        step0_post_response = self.assertPOST200(
            url,
            data={
                step_key: '0',
                '0-ctype': ct.id,
            },
        )

        step0_post_ctxt = step0_post_response.context
        self.assertEqual(
            _('New buttons configuration for «{model}»').format(model=ct),
            step0_post_ctxt.get('title'),
        )

        with self.assertNoException():
            choices = step0_post_ctxt['form'].fields['button_ids'].choices

        self.assertInChoices(value=TestButton1.id, label=TestButton1(), choices=choices)
        self.assertInChoices(value=TestButton2.id, label=TestButton2(), choices=choices)
        self.assertInChoices(value=TestButton3.id, label=TestButton3(), choices=choices)
        self.assertInChoices(value=TestButton4.id, label=TestButton4(), choices=choices)
        self.assertNotInChoices(value=TestButton5.id, choices=choices)

        # --
        self.assertNoFormError(self.client.post(
            url,
            data={
                step_key: '1',
                '1-button_ids': [TestButton1.id],
            },
        ))

        def _buttons_info(ctype):
            return [
                *ButtonMenuItem.objects.filter(
                    content_type=ctype, superuser=True, role=None,
                ).values_list('button_id', 'order'),
            ]

        self.assertListEqual([(TestButton1.id, 1000)], _buttons_info(ctype=ct))
        self.assertListEqual([('', 1)],               _buttons_info(ctype=None))

    def test_add__perms(self):
        self.login_as_standard()
        self.assertGET403(reverse('creme_config__add_base_buttons'))
        self.assertGET403(reverse('creme_config__add_superuser_buttons'))

    def test_edit__base__not_existing(self):
        "Edit Content type without configuration => error."
        self.login_as_root()

        ct = self.contact_ct
        self.assertGET404(reverse('creme_config__edit_base_buttons', args=(ct.id,)))

    def test_edit__base__default(self):
        self.login_as_root()

        url = reverse('creme_config__edit_base_buttons', args=(0,))

        # GET ---
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')

        context1 = response1.context
        self.assertEqual(_('Edit default base configuration'), context1.get('title'))
        self.assertEqual(_('Save the modifications'),          context1.get('submit_label'))

        with self.assertNoException():
            buttons_f1 = context1['form'].fields['button_ids']
            choices = buttons_f1.choices

        self.assertInChoices(value=TestButton1.id, label=TestButton1(), choices=choices)
        self.assertInChoices(value=TestButton2.id, label=TestButton2(), choices=choices)
        self.assertInChoices(value=TestButton3.id, label=TestButton3(), choices=choices)
        self.assertNotInChoices(value=TestButton4.id, choices=choices)
        self.assertNotInChoices(value=TestButton5.id, choices=choices)

        self.assertIsInstance(buttons_f1.initial, list)
        self.assertIn('', buttons_f1.initial)

        # POST ---
        response2 = self.client.post(url, data={'button_ids': TestButton1.id})
        self.assertNoFormError(response2)
        self.assertListEqual(
            [(TestButton1.id, 1)],
            [
                *ButtonMenuItem.objects.filter(
                    content_type=None, superuser=False, role=None,
                ).values_list('button_id', 'order'),
            ],
        )

        # GET again (to test initial) ---
        response3 = self.assertGET200(url)

        with self.assertNoException():
            buttons_f3 = response3.context['form'].fields['button_ids']

        self.assertEqual([TestButton1.id], buttons_f3.initial)

    def test_edit__base__for_model(self):
        self.login_as_root()

        ct = self.contact_ct

        ButtonMenuItem.objects.create(
            content_type=FakeContact, button=TestButton4, order=1,
        )

        url = reverse('creme_config__edit_base_buttons', args=(ct.id,))
        context = self.assertGET200(url).context
        self.assertEqual(
            _('Edit base configuration for «{model}»').format(model=ct),
            context.get('title'),
        )

        with self.assertNoException():
            choices = context['form'].fields['button_ids'].choices

        self.assertInChoices(
            value=TestButton1.id,
            label=button_registry.get_button(TestButton1.id),
            choices=choices,
        )
        self.assertInChoices(
            value=TestButton4.id,
            label=button_registry.get_button(TestButton4.id),
            choices=choices,
        )

        # NB: Button03 is incompatible with Contact
        self.assertNotInChoices(value=TestButton5.id, choices=choices)

        self.assertNoFormError(self.client.post(
            url, data={'button_ids': [TestButton1.id, TestButton4.id]},
        ))
        self.assertListEqual(
            [(TestButton1.id, 1000), (TestButton4.id, 1001)],
            [
                *ButtonMenuItem.objects
                               .filter(content_type=ct, superuser=False, role=None)
                               .values_list('button_id', 'order'),
            ],
        )

    def test_edit__base__set_empty(self):
        self.login_as_root()

        ct = self.contact_ct

        ButtonMenuItem.objects.create(
            content_type=FakeContact, button=TestButton1, order=1,
        )

        self.assertNoFormError(self.client.post(
            reverse('creme_config__edit_base_buttons', args=(ct.id,)),
            data={'button_ids': []},
        ))
        self.assertListEqual(
            [('', 1)],
            [
                *ButtonMenuItem.objects
                               .filter(content_type=ct, superuser=False, role=None)
                               .values_list('button_id', 'order'),
            ],
        )

    def test_edit__role__not_existing(self):
        "Edit role without configuration => error."
        self.login_as_root()

        role = self.create_role()
        self.assertGET404(reverse('creme_config__edit_role_buttons', args=(role.id, 0)))
        self.assertGET404(
            reverse('creme_config__edit_role_buttons', args=(role.id, self.contact_ct.id))
        )

    def test_edit__role__default(self):
        user = self._login_as_core_admin()
        role = user.role
        url = reverse('creme_config__edit_role_buttons', args=(role.id, 0))

        create_bmi = ButtonMenuItem.objects.create
        create_bmi(button=TestButton1, order=1, role=role)
        create_bmi(button=TestButton2, order=2, role=role)
        create_bmi(button=TestButton4, order=1, role=role, content_type=FakeContact)
        create_bmi(button=TestButton5, order=1, superuser=True, content_type=FakeContact)

        # GET ---
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')

        context1 = response1.context
        self.assertEqual(
            _('Edit default configuration of role «{role}»').format(role=role),
            context1.get('title'),
        )
        self.assertEqual(_('Save the modifications'), context1.get('submit_label'))

        with self.assertNoException():
            buttons_f = context1['form'].fields['button_ids']
            choices = buttons_f.choices

        self.assertInChoices(value=TestButton1.id, label=TestButton1(), choices=choices)
        self.assertInChoices(value=TestButton2.id, label=TestButton2(), choices=choices)
        self.assertInChoices(value=TestButton3.id, label=TestButton3(), choices=choices)
        self.assertNotInChoices(value=TestButton4.id, choices=choices)
        self.assertNotInChoices(value=TestButton5.id, choices=choices)

        self.assertListEqual([TestButton1.id, TestButton2.id], buttons_f.initial)

        # POST ---
        response2 = self.client.post(url, data={'button_ids': [TestButton2.id, TestButton3.id]})
        self.assertNoFormError(response2)

        def button_info(**kwargs):
            return [*ButtonMenuItem.objects.filter(**kwargs).values_list('button_id', 'order')]

        self.assertListEqual(
            [(TestButton2.id, 1), (TestButton3.id, 2)],
            button_info(content_type=None, superuser=False, role=role),
        )
        self.assertListEqual(
            [(TestButton4.id, 1)],
            button_info(content_type=self.contact_ct, superuser=False, role=role),
        )
        self.assertListEqual(
            [(TestButton5.id, 1)],
            button_info(content_type=self.contact_ct, superuser=True, role=None),
        )

    def test_edit__role__for_model(self):
        self.login_as_root()

        role = self.create_role()
        ct = self.contact_ct

        create_bmi = ButtonMenuItem.objects.create
        create_bmi(button=TestButton3, order=2)
        create_bmi(button=TestButton1, order=1, role=role)
        create_bmi(button=TestButton2, order=101, content_type=ct)
        create_bmi(button=TestButton3, order=102, content_type=ct)
        # NB: order should be something 1001 in normal cases
        create_bmi(button=TestButton2, order=101, role=role, content_type=ct)
        create_bmi(button=TestButton3, order=102, role=role, content_type=ct)
        create_bmi(button=TestButton2, order=101, superuser=True, content_type=ct)
        create_bmi(button=TestButton4, order=102, superuser=True, content_type=ct)

        url = reverse('creme_config__edit_role_buttons', args=(role.id, ct.id,))

        # GET ---
        context = self.assertGET200(url).context
        self.assertEqual(
            _('Edit configuration of role «{role}» for «{model}»').format(
                role=role, model=ct,
            ),
            context.get('title'),
        )

        with self.assertNoException():
            buttons_f = context['form'].fields['button_ids']
            choices = buttons_f.choices

        self.assertNotInChoices(value=TestButton1.id, choices=choices)  # Already in default conf
        self.assertInChoices(value=TestButton2.id, label=TestButton2(), choices=choices)
        self.assertInChoices(value=TestButton3.id, label=TestButton3(), choices=choices)
        self.assertInChoices(value=TestButton4.id, label=TestButton4(), choices=choices)
        self.assertNotInChoices(value=TestButton5.id, choices=choices)  # Not compatible

        self.assertListEqual([TestButton2.id, TestButton3.id], buttons_f.initial)

        # POST ---
        self.assertNoFormError(self.client.post(
            url, data={'button_ids': [TestButton4.id, TestButton2.id]},
        ))

        def buttons_info(role):
            return [*ButtonMenuItem.objects.filter(
                content_type=ct, superuser=False, role=role,
            ).values_list('button_id', 'order')]

        self.assertListEqual(
            [(TestButton4.id, 1000), (TestButton2.id, 1001)],
            buttons_info(role=role),
        )
        self.assertListEqual(
            [(TestButton2.id, 101), (TestButton3.id, 102)],
            buttons_info(role=None),
        )

    def test_edit__role__set_default_empty(self):
        self.login_as_root()
        role = self.create_role()

        ButtonMenuItem.objects.create(button=TestButton1, order=1, role=role)
        self.assertNoFormError(self.client.post(
            reverse('creme_config__edit_role_buttons', args=(role.id, 0)),
            data={'button_ids': []},
        ))
        self.assertListEqual(
            [('', 1)],
            [
                *ButtonMenuItem.objects
                               .filter(content_type=None, superuser=False, role=role)
                               .values_list('button_id', 'order'),
            ],
        )

    def test_edit__role__set_model_empty(self):
        self.login_as_root()
        role = self.create_role()

        ct = self.contact_ct
        create_bmi = partial(ButtonMenuItem.objects.create, content_type=ct)
        create_bmi(button=TestButton1, order=1)
        create_bmi(button=TestButton2, order=1, role=role)

        self.assertNoFormError(self.client.post(
            reverse('creme_config__edit_role_buttons', args=(role.id, ct.id,)),
            data={'button_ids': []},
        ))

        def buttons_info(role):
            return [*ButtonMenuItem.objects.filter(
                content_type=ct, superuser=False, role=role,
            ).values_list('button_id', 'order')]

        self.assertListEqual([('',             1)], buttons_info(role=role))
        self.assertListEqual([(TestButton1.id, 1)], buttons_info(role=None))

    def test_edit__superuser__not_existing(self):
        "Edit superuser without configuration => error."
        self.login_as_root()

        self.assertGET404(reverse('creme_config__edit_superuser_buttons', args=(0,)))
        self.assertGET404(
            reverse('creme_config__edit_superuser_buttons', args=(self.contact_ct.id,))
        )

    def test_edit__superuser__default(self):
        self.login_as_root()

        ct = self.contact_ct
        role = self.create_role()
        url = reverse('creme_config__edit_superuser_buttons', args=(0,))

        create_bmi = ButtonMenuItem.objects.create
        create_bmi(button=TestButton1, order=1, superuser=True)
        create_bmi(button=TestButton2, order=2, superuser=True)
        create_bmi(button=TestButton4, order=1, superuser=True, content_type=ct)
        create_bmi(button=TestButton5, order=1, role=role, content_type=ct)

        # GET ---
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')

        context1 = response1.context
        self.assertEqual(_('Edit default configuration of superusers'), context1.get('title'))
        self.assertEqual(_('Save the modifications'), context1.get('submit_label'))

        with self.assertNoException():
            buttons_f = context1['form'].fields['button_ids']
            choices = buttons_f.choices

        self.assertInChoices(value=TestButton1.id, label=TestButton1(), choices=choices)
        self.assertInChoices(value=TestButton2.id, label=TestButton2(), choices=choices)
        self.assertInChoices(value=TestButton3.id, label=TestButton3(), choices=choices)
        self.assertNotInChoices(value=TestButton4.id, choices=choices)
        self.assertNotInChoices(value=TestButton5.id, choices=choices)

        self.assertListEqual([TestButton1.id, TestButton2.id], buttons_f.initial)

        # POST ---
        response2 = self.client.post(
            url, data={'button_ids': [TestButton2.id, TestButton3.id]},
        )
        self.assertNoFormError(response2)

        def button_info(**kwargs):
            return [*ButtonMenuItem.objects.filter(**kwargs).values_list('button_id', 'order')]

        self.assertListEqual(
            [(TestButton2.id, 1), (TestButton3.id, 2)],
            button_info(content_type=None, superuser=True, role=None),
        )
        self.assertListEqual(
            [(TestButton4.id, 1)],
            button_info(content_type=ct, superuser=True, role=None),
        )
        self.assertListEqual(
            [(TestButton5.id, 1)],
            button_info(content_type=ct, superuser=False, role=role),
        )

    def test_edit__superuser__for_model(self):
        self.login_as_root()

        role = self.create_role()
        ct = self.contact_ct

        create_bmi = ButtonMenuItem.objects.create
        create_bmi(button=TestButton3, order=1)
        create_bmi(button=TestButton2, order=101, content_type=ct)
        create_bmi(button=TestButton3, order=102, content_type=ct)
        create_bmi(button=TestButton1, order=1, superuser=True)
        # NB: order should be something 1001 in normal cases
        create_bmi(button=TestButton2, order=101, superuser=True, content_type=ct)
        create_bmi(button=TestButton3, order=102, superuser=True, content_type=ct)
        create_bmi(button=TestButton2, order=101, role=role, content_type=ct)
        create_bmi(button=TestButton4, order=102, role=role, content_type=ct)

        url = reverse('creme_config__edit_superuser_buttons', args=(ct.id,))

        # GET ---
        context = self.assertGET200(url).context
        self.assertEqual(
            _('Edit configuration of superusers for «{model}»').format(model=ct),
            context.get('title'),
        )

        with self.assertNoException():
            buttons_f = context['form'].fields['button_ids']
            choices = buttons_f.choices

        self.assertNotInChoices(value=TestButton1.id, choices=choices)  # Already in default conf
        self.assertInChoices(value=TestButton2.id, label=TestButton2(), choices=choices)
        self.assertInChoices(value=TestButton3.id, label=TestButton3(), choices=choices)
        self.assertInChoices(value=TestButton4.id, label=TestButton4(), choices=choices)
        self.assertNotInChoices(value=TestButton5.id, choices=choices)  # Not compatible

        self.assertListEqual([TestButton2.id, TestButton3.id], buttons_f.initial)

        # POST ---
        self.assertNoFormError(self.client.post(
            url, data={'button_ids': [TestButton4.id, TestButton2.id]},
        ))

        def buttons_info(superuser):
            return [*ButtonMenuItem.objects.filter(
                content_type=ct, superuser=superuser, role=None,
            ).values_list('button_id', 'order')]

        self.assertListEqual(
            [(TestButton4.id, 1000), (TestButton2.id, 1001)],
            buttons_info(superuser=True),
        )
        self.assertListEqual(
            [(TestButton2.id, 101), (TestButton3.id, 102)],
            buttons_info(superuser=False),
        )

    def test_edit__superuser__set_default_empty(self):
        self.login_as_root()

        ButtonMenuItem.objects.create(button=TestButton1, order=1, superuser=True)
        self.assertNoFormError(self.client.post(
            reverse('creme_config__edit_superuser_buttons', args=(0,)),
            data={'button_ids': []},
        ))
        self.assertListEqual(
            [('', 1)],
            [
                *ButtonMenuItem.objects
                               .filter(content_type=None, superuser=True, role=None)
                               .values_list('button_id', 'order'),
            ],
        )

    def test_edit__superuser__set_model_empty(self):
        self.login_as_root()
        ct = self.contact_ct
        create_bmi = partial(ButtonMenuItem.objects.create, content_type=ct)
        create_bmi(button=TestButton1, order=1)
        create_bmi(button=TestButton2, order=1, superuser=True)

        self.assertNoFormError(self.client.post(
            reverse('creme_config__edit_superuser_buttons', args=(ct.id,)),
            data={'button_ids': []},
        ))

        def buttons_info(superuser):
            return [*ButtonMenuItem.objects.filter(
                content_type=self.contact_ct, superuser=superuser, role=None,
            ).values_list('button_id', 'order')]

        self.assertListEqual([('',             1)], buttons_info(superuser=True))
        self.assertListEqual([(TestButton1.id, 1)], buttons_info(superuser=False))

    def test_edit__perms(self):
        user = self.login_as_standard()

        ct = self.contact_ct
        self.assertGET403(reverse('creme_config__edit_base_buttons', args=(ct.id,)))
        self.assertGET403(reverse('creme_config__edit_superuser_buttons', args=(0,)))
        self.assertGET403(reverse('creme_config__edit_role_buttons', args=(user.role.id, 0)))

    def test_delete__base__default(self):
        "Can not delete base default configuration."
        self.login_as_root()

        url = self.DEL_URL
        bmi = ButtonMenuItem.objects.create(content_type=None, button_id='', order=1)
        self.assertPOST404(url)
        # self.assertPOST200(url, data={'id': 0})
        self.assertStillExists(bmi)

    def test_delete__base__for_model(self):
        self.login_as_root()

        ct = self.contact_ct

        create_bmi = partial(ButtonMenuItem.objects.create, order=1)
        bmi1 = create_bmi(button=TestButton1)
        bmi2 = create_bmi(button=TestButton1, content_type=ct)
        bmi3 = create_bmi(button=TestButton1, superuser=True)
        bmi4 = create_bmi(button=TestButton1, superuser=True, content_type=ct)
        bmi5 = create_bmi(button=TestButton1, role=self.create_role(), content_type=ct)

        # self.assertPOST200(self.DEL_URL, data={'id': ct.id})
        self.assertPOST200(self.DEL_URL, data={'ctype': ct.id})
        self.assertDoesNotExist(bmi2)
        self.assertStillExists(bmi1)
        self.assertStillExists(bmi3)
        self.assertStillExists(bmi4)
        self.assertStillExists(bmi5)

        self.assertPOST404(self.DEL_URL, data={'ctype': 'notanint'})

    def test_delete__role(self):
        user = self._login_as_core_admin()
        role = user.role

        create_bmi = partial(ButtonMenuItem.objects.create, order=1)
        bmi1 = create_bmi(button_id='',       role=role)
        bmi2 = create_bmi(button=TestButton1, role=role, content_type=self.contact_ct)
        bmi3 = create_bmi(button=TestButton1, superuser=True)
        bmi4 = create_bmi(button=TestButton1)

        self.assertPOST200(self.DEL_URL, data={'role': role.id})
        self.assertDoesNotExist(bmi1)
        self.assertDoesNotExist(bmi2)
        self.assertStillExists(bmi3)
        self.assertStillExists(bmi4)

        self.assertPOST404(self.DEL_URL, data={'role': 'not_an_int'})

    def test_delete__role__for_model(self):
        self.login_as_root()

        role = self.create_role()
        ct = self.contact_ct

        create_bmi = partial(ButtonMenuItem.objects.create, order=1)
        bmi1 = create_bmi(button_id='',       role=role)
        bmi2 = create_bmi(button=TestButton1, role=role, content_type=ct)
        bmi3 = create_bmi(button=TestButton1, superuser=True)
        bmi4 = create_bmi(button=TestButton1)

        self.assertPOST200(self.DEL_URL, data={'role': role.id, 'ctype': ct.id})
        self.assertDoesNotExist(bmi2)
        self.assertStillExists(bmi1)
        self.assertStillExists(bmi3)
        self.assertStillExists(bmi4)

    def test_delete__superuser(self):
        self.login_as_root()

        role = self.create_role()

        create_bmi = partial(ButtonMenuItem.objects.create, order=1)
        bmi1 = create_bmi(button=TestButton1, superuser=True)
        bmi2 = create_bmi(button=TestButton1, superuser=True, content_type=FakeContact)
        bmi3 = create_bmi(button_id='', role=role)
        bmi4 = create_bmi(button=TestButton1,)

        self.assertPOST200(self.DEL_URL, data={'role': 'superuser'})
        self.assertDoesNotExist(bmi1)
        self.assertDoesNotExist(bmi2)
        self.assertStillExists(bmi3)
        self.assertStillExists(bmi4)

    def test_delete__superuser__for_model(self):
        self.login_as_root()

        role = self.create_role()
        ct = self.contact_ct

        create_bmi = partial(ButtonMenuItem.objects.create, order=1)
        bmi1 = create_bmi(button_id='',       superuser=True)
        bmi2 = create_bmi(button=TestButton1, superuser=True, content_type=ct)
        bmi3 = create_bmi(button=TestButton1, role=role,      content_type=ct)
        bmi4 = create_bmi(button=TestButton1,                 content_type=ct)

        self.assertPOST200(
            self.DEL_URL,
            data={'role': 'superuser', 'ctype': ct.id},
        )
        self.assertDoesNotExist(bmi2)
        self.assertStillExists(bmi1)
        self.assertStillExists(bmi3)
        self.assertStillExists(bmi4)

    def test_delete__perms(self):
        user = self.login_as_standard()

        ct = self.contact_ct
        url = self.DEL_URL
        self.assertPOST403(url, data={'ctype': ct.id})
        self.assertPOST403(url, data={'role': 'superuser', 'ctype': ct.id})
        self.assertPOST403(url, data={'role': user.role.id, 'ctype': ct.id})

    def test_clone__default(self):
        self.login_as_root()

        existing = ButtonMenuItem.objects.all()
        self.assertFalse([bmi.button_id for bmi in existing if bmi.superuser])
        self.assertFalse([bmi.button_id for bmi in existing if bmi.role])

        role1 = self.create_role(name='Role #1')
        role2 = self.create_role(name='Role #2')
        role3 = self.create_role(name='Role #3')

        create_bmi = ButtonMenuItem.objects.create
        create_bmi(button=TestButton1, order=1, superuser=True)
        create_bmi(button=TestButton4, order=2, role=role3)

        # GET ---
        url = reverse('creme_config__clone_base_buttons')
        context1 = self.assertGET200(url).context
        self.assertEqual(_('Clone the base configuration'), context1.get('title'))
        self.assertEqual(_('Clone'),                        context1.get('submit_label'))

        with self.assertNoException():
            target_f = context1['form'].fields['target']
            choices = target_f.choices

        self.assertTrue(target_f.required)
        self.assertInChoices(value=role1.id, label=str(role1), choices=choices)
        self.assertInChoices(value=role2.id, label=str(role2), choices=choices)
        self.assertNotInChoices(value='', choices=choices)
        self.assertNotInChoices(value=role3.id, choices=choices)

        # POST ---
        self.assertNoFormError(self.client.post(url, data={'target': role1.id}))
        self.assertCountEqual(
            [(bmi.button_id, bmi.order, bmi.content_type_id) for bmi in existing],
            [
                *ButtonMenuItem.objects
                               .filter(superuser=False, role=role1)
                               .values_list('button_id', 'order', 'content_type'),
            ],
        )

    def test_clone__role_to_role(self):
        self.login_as_root()

        role1 = self.create_role(name='Role #1')
        role2 = self.create_role(name='Role #2')

        url = reverse('creme_config__clone_role_buttons', args=(role1.id,))

        # GET (error) ---
        self.assertContains(
            self.client.get(url),
            text=_('This role has no button configuration.'),
            status_code=409,
            html=True,
        )

        # GET ---
        ct = ContentType.objects.get_for_model(FakeOrganisation)
        create_bmi = ButtonMenuItem.objects.create
        create_bmi(button=TestButton1, order=1, role=role1)
        create_bmi(content_type=ct, button=TestButton4, order=1, role=role1)
        create_bmi(content_type=ct, button=TestButton5, order=2, role=role1)

        response2 = self.assertGET200(url)
        self.assertEqual(
            _('Clone the configuration of «{role}»').format(role=role1),
            response2.context.get('title'),
        )

        with self.assertNoException():
            choices = response2.context['form'].fields['target'].choices

        self.assertInChoices(value=role2.id, label=str(role2), choices=choices)
        self.assertInChoices(value='', label='*{}*'.format(_('Superuser')), choices=choices)
        self.assertNotInChoices(value=role1.id, choices=choices)

        # POST ---
        self.assertNoFormError(self.client.post(url, data={'target': role2.id}))

        self.assertCountEqual(
            [
                {'button_id': TestButton1.id, 'order': 1, 'content_type': None},
                {'button_id': TestButton4.id, 'order': 1, 'content_type': ct.id},
                {'button_id': TestButton5.id, 'order': 2, 'content_type': ct.id},
            ],
            [
                *ButtonMenuItem.objects
                               .filter(superuser=False, role=role2)
                               .values('button_id', 'order', 'content_type'),
            ],
        )

    def test_clone__role_to_superuser(self):
        user = self._login_as_core_admin()
        role = user.role
        ct = ContentType.objects.get_for_model(FakeOrganisation)

        create_bmi = ButtonMenuItem.objects.create
        create_bmi(button=TestButton1, order=1, role=role)
        create_bmi(button=TestButton4, order=1, role=role, content_type=ct)
        create_bmi(button=TestButton5, order=2, role=role, content_type=ct)

        self.assertNoFormError(self.client.post(
            reverse('creme_config__clone_role_buttons', args=(role.id,)),
            data={'target': ''},
        ))
        self.assertCountEqual(
            [
                {'button_id': TestButton1.id, 'order': 1, 'content_type': None},
                {'button_id': TestButton4.id, 'order': 1, 'content_type': ct.id},
                {'button_id': TestButton5.id, 'order': 2, 'content_type': ct.id},
            ],
            [
                *ButtonMenuItem.objects
                               .filter(superuser=True, role=None)
                               .values('button_id', 'order', 'content_type'),
            ],
        )

    def test_clone__superuser(self):
        self.login_as_root()
        role = self.create_role(name='Role')
        ct = ContentType.objects.get_for_model(FakeOrganisation)

        # GET (error) ---
        url = reverse('creme_config__clone_superuser_buttons')
        self.assertContains(
            self.client.get(url),
            text=_('Superusers have no button configuration.'),
            status_code=409,
            html=True,
        )

        # GET ---
        create_bmi = partial(ButtonMenuItem.objects.create, superuser=True)
        create_bmi(button=TestButton1, order=1)
        create_bmi(button=TestButton4, order=1, content_type=ct)
        create_bmi(button=TestButton5, order=2, content_type=ct)

        response1 = self.assertGET200(url)
        self.assertEqual(
            _('Clone the configuration of superusers'),
            response1.context.get('title'),
        )

        # POST ---
        self.assertNoFormError(self.client.post(url, data={'target': role.id}))

        self.maxDiff = None
        self.assertCountEqual(
            [
                {'button_id': TestButton1.id, 'order': 1, 'content_type': None},
                {'button_id': TestButton4.id, 'order': 1, 'content_type': ct.id},
                {'button_id': TestButton5.id, 'order': 2, 'content_type': ct.id},
            ],
            [
                *ButtonMenuItem.objects
                               .filter(superuser=False, role=role)
                               .values('button_id', 'order', 'content_type'),
            ],
        )

    def test_clone__perms(self):
        user = self.login_as_standard()

        self.assertPOST403(reverse('creme_config__clone_base_buttons'))
        self.assertPOST403(reverse('creme_config__clone_superuser_buttons'))
        self.assertPOST403(reverse('creme_config__clone_role_buttons', args=(user.role.id,)))
