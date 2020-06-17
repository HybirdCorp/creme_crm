# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse
    from django.utils.translation import gettext as _

    from creme.creme_core.gui.button_menu import Button, button_registry
    from creme.creme_core.models import (
        ButtonMenuItem,
        FakeContact, FakeOrganisation,
    )
    from creme.creme_core.tests.base import CremeTestCase
except Exception as e:
    print(f'Error in <{__name__}>: {e}')


class ButtonMenuConfigTestCase(CremeTestCase):
    WIZARD_URL = reverse('creme_config__add_buttons_to_ctype')
    DEL_URL = reverse('creme_config__delete_ctype_buttons')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.contact_ct = ct = ContentType.objects.get_for_model(FakeContact)
        contact_conf = ButtonMenuItem.objects.filter(content_type=ct)
        cls._buttonconf_backup = [*contact_conf]
        contact_conf.delete()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        ButtonMenuItem.objects.bulk_create(cls._buttonconf_backup)

    def setUp(self):
        super().setUp()
        self.login()

    def test_portal(self):
        response = self.assertGET200(reverse('creme_config__buttons'))
        self.assertTemplateUsed(response, 'creme_config/button_menu_portal.html')
        self.assertEqual(reverse('creme_core__reload_bricks'),
                         response.context.get('bricks_reload_url')
                        )

    def test_wizard(self):
        class TestButton(Button):
            id_          = Button.generate_id('creme_config', 'test_wizard')
            verbose_name = 'Testing purpose'

        button_registry.register(TestButton)

        ct = self.contact_ct
        url = self.WIZARD_URL
        response = self.assertGET200(url)

        with self.assertNoException():
            ctypes = response.context['form'].fields['ctype'].ctypes

        self.assertIn(ct, ctypes)

        step_key = 'button_menu_wizard-current_step'
        response = self.assertPOST200(
            url,
            data={
                step_key: '0',
                '0-ctype': ct.id,
            },
        )

        with self.assertNoException():
            choices = response.context['form'].fields['button_ids'].choices

        button_index = self.assertInChoices(
            value=TestButton.id_,
            label=TestButton.verbose_name,
            choices=choices,
        )

        response = self.client.post(
            url,
            data={
                step_key: '1',
                f'1-button_ids_check_{button_index}': 'on',
                f'1-button_ids_value_{button_index}': TestButton.id_,
                f'1-button_ids_order_{button_index}': 1,
            },
        )
        self.assertNoFormError(response)
        self.assertListEqual(
            [(TestButton.id_, 1000)],
            [*ButtonMenuItem.objects
                            .filter(content_type=ct)
                            .values_list('button_id', 'order')
            ]
        )

    def test_edit01(self):
        "Edit empty configuration => error."
        ct = self.contact_ct
        self.assertGET404(reverse('creme_config__edit_ctype_buttons', args=(ct.id,)))

    def test_edit02(self):
        "Edit the default configuration."
        class TestButton(Button):
            id_          = Button.generate_id('creme_config', 'test_edit02')
            verbose_name = 'Testing purpose'

        button_registry.register(TestButton)

        url = reverse('creme_config__edit_ctype_buttons', args=(0,))
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(_('Edit default configuration'), context.get('title'))
        self.assertEqual(_('Save the modifications'),     context.get('submit_label'))

        with self.assertNoException():
            choices = context['form'].fields['button_ids'].choices

        button_index = self.assertInChoices(
            value=TestButton.id_,
            label=TestButton.verbose_name,
            choices=choices,
        )

        response = self.client.post(
            url,
            data={
                f'button_ids_check_{button_index}': 'on',
                f'button_ids_value_{button_index}': TestButton.id_,
                f'button_ids_order_{button_index}': 1,
            },
        )
        self.assertNoFormError(response)
        self.assertListEqual(
            [(TestButton.id_, 1)],
            [*ButtonMenuItem.objects.filter(content_type=None)
                                    .values_list('button_id', 'order')
            ]
        )

    def test_edit03(self):
        ct = self.contact_ct

        class TestButton01(Button):
            id_          = Button.generate_id('creme_config', 'test_edit03_1')
            verbose_name = 'Test button #1'

        class TestButton02(Button):
            id_          = Button.generate_id('creme_config', 'test_edit03_2')
            verbose_name = 'Test button #2'

            def get_ctypes(self):
                return [FakeContact, FakeOrganisation]

        class TestButton03(Button):
            id_          = Button.generate_id('creme_config', 'test_edit03_3')
            verbose_name = 'Test button #3'

            def get_ctypes(self):
                return [FakeOrganisation]  # No Contact

        button_registry.register(TestButton01, TestButton02, TestButton03)

        ButtonMenuItem.objects.create(content_type=ct, order=1)

        url = reverse('creme_config__edit_ctype_buttons', args=(ct.id,))
        context = self.assertGET200(url).context
        self.assertEqual(
            _('Edit configuration for «{model}»').format(model=ct),
            context.get('title')
        )

        with self.assertNoException():
            choices = context['form'].fields['button_ids'].choices

        button01_index = self.assertInChoices(
            value=TestButton01.id_,
            label=TestButton01.verbose_name,
            choices=choices,
        )
        button02_index = self.assertInChoices(
            value=TestButton02.id_,
            label=TestButton02.verbose_name,
            choices=choices,
        )

        # NB: Button03 is incompatible with Contact
        self.assertNotInChoices(value=TestButton03.id_, choices=choices)

        response = self.client.post(
            url,
            data={
                f'button_ids_check_{button01_index}': 'on',
                f'button_ids_value_{button01_index}': TestButton01.id_,
                f'button_ids_order_{button01_index}': 1,

                f'button_ids_check_{button02_index}': 'on',
                f'button_ids_value_{button02_index}': TestButton02.id_,
                f'button_ids_order_{button02_index}': 2,
            },
        )
        self.assertNoFormError(response)
        self.assertListEqual(
            [(TestButton01.id_, 1000), (TestButton02.id_, 1001)],
            [*ButtonMenuItem.objects.filter(content_type=ct)
                                    .order_by('order')
                                    .values_list('button_id', 'order')
            ]
        )

    def test_delete01(self):
        "Can not delete default configuration."
        url = self.DEL_URL
        bmi = ButtonMenuItem.objects.create(content_type=None, button_id='', order=1)
        self.assertPOST404(url)
        self.assertPOST200(url, data={'id': 0})
        self.assertStillExists(bmi)

    def test_delete_detailview02(self):
        ct = self.contact_ct
        ButtonMenuItem.objects.create(content_type=ct, order=1)

        self.assertPOST200(self.DEL_URL, data={'id': ct.id})
        self.assertFalse(ButtonMenuItem.objects.filter(content_type=ct))
