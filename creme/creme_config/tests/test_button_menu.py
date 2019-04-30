# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse
    from django.utils.translation import gettext as _

    from creme.creme_core.models import ButtonMenuItem, FakeContact, FakeOrganisation
    from creme.creme_core.gui.button_menu import Button, button_registry
    from creme.creme_core.tests.base import CremeTestCase
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class ButtonMenuConfigTestCase(CremeTestCase):
    # ADD_URL = reverse('creme_config__add_buttons_to_ctype_legacy')
    WIZARD_URL = reverse('creme_config__add_buttons_to_ctype')
    DEL_URL = reverse('creme_config__delete_ctype_buttons')

    @classmethod
    def setUpClass(cls):
        # super(ButtonMenuConfigTestCase, cls).setUpClass()
        super().setUpClass()

        cls.contact_ct = ct = ContentType.objects.get_for_model(FakeContact)
        contact_conf = ButtonMenuItem.objects.filter(content_type=ct)
        cls._buttonconf_backup = list(contact_conf)
        contact_conf.delete()

    @classmethod
    def tearDownClass(cls):
        # super(ButtonMenuConfigTestCase, cls).tearDownClass()
        super().tearDownClass()

        ButtonMenuItem.objects.bulk_create(cls._buttonconf_backup)

    def setUp(self):
        self.login()

    def test_portal(self):
        response = self.assertGET200(reverse('creme_config__buttons'))
        self.assertTemplateUsed(response, 'creme_config/button_menu_portal.html')
        self.assertEqual(reverse('creme_core__reload_bricks'),
                         response.context.get('bricks_reload_url')
                        )

    # def test_add_detailview(self):
    #     ct = self.contact_ct
    #
    #     url = self.ADD_URL
    #     self.assertGET200(url)
    #
    #     self.assertNoFormError(self.client.post(url, data={'ctype': ct.id}))
    #
    #     self.assertEqual([('', 1)],
    #                      [(bmi.button_id, bmi.order) for bmi in ButtonMenuItem.objects.filter(content_type=ct)]
    #                     )
    #
    #     response = self.client.get(url)
    #
    #     with self.assertNoException():
    #         ctypes = response.context['form'].fields['ctype'].ctypes
    #
    #     self.assertNotIn(ct, ctypes)

    def _find_field_index(self, formfield, button_id):
        for i, (f_button_id, f_button_vname) in enumerate(formfield.choices):
            if f_button_id == button_id:
                return i

        self.fail('No "{}" in button IDs'.format(button_id))

    def test_wizard(self):
        class TestButton(Button):
            id_          = Button.generate_id('creme_config', 'test_wizard')
            verbose_name = 'Testing purpose'

        # button = TestButton()
        # button_registry.register(button)
        button_registry.register(TestButton)

        ct = self.contact_ct
        url = self.WIZARD_URL
        response = self.assertGET200(url)

        with self.assertNoException():
            ctypes = response.context['form'].fields['ctype'].ctypes

        self.assertIn(ct, ctypes)

        step_key = 'button_menu_wizard-current_step'
        response = self.assertPOST200(url, data={step_key: '0',
                                                 '0-ctype': ct.id,
                                                },
                                     )

        with self.assertNoException():
            button_ids = response.context['form'].fields['button_ids']

        # button_index = self._find_field_index(button_ids, button.id_)
        button_index = self._find_field_index(button_ids, TestButton.id_)

        response = self.client.post(url,
                                    data={
                                        step_key: '1',
                                        '1-button_ids_check_{}'.format(button_index): 'on',
                                        # '1-button_ids_value_%s' % button_index: button.id_,
                                        '1-button_ids_value_{}'.format(button_index): TestButton.id_,
                                        '1-button_ids_order_{}'.format(button_index): 1,
                                    },
                                   )
        self.assertNoFormError(response)
        # self.assertEqual([(button.id_, 1000)],
        self.assertEqual([(TestButton.id_, 1000)],
                         [(bmi.button_id, bmi.order) for bmi in ButtonMenuItem.objects.filter(content_type=ct)]
                        )

    def test_edit01(self):
        "Edit empty configuration => error"
        ct = self.contact_ct
        self.assertGET404(reverse('creme_config__edit_ctype_buttons', args=(ct.id,)))

    def test_edit02(self):
        "Edit the default configuration"
        class TestButton(Button):
            id_          = Button.generate_id('creme_config', 'test_edit02')
            verbose_name = 'Testing purpose'


        # button = TestButton()
        # button_registry.register(button)
        button_registry.register(TestButton)

        url = reverse('creme_config__edit_ctype_buttons', args=(0,))
        response = self.assertGET200(url)
        # self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit_popup.html')
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(_('Edit default configuration'), context.get('title'))
        self.assertEqual(_('Save the modifications'),     context.get('submit_label'))

        with self.assertNoException():
            button_ids = context['form'].fields['button_ids']

        # button_index = self._find_field_index(button_ids, button.id_)
        button_index = self._find_field_index(button_ids, TestButton.id_)

        response = self.client.post(url,
                                    data={'button_ids_check_{}'.format(button_index): 'on',
                                          # 'button_ids_value_%s' % button_index: button.id_,
                                          'button_ids_value_{}'.format(button_index): TestButton.id_,
                                          'button_ids_order_{}'.format(button_index): 1,
                                         }
                                   )
        self.assertNoFormError(response)
        # self.assertEqual([(button.id_, 1)],
        self.assertEqual([(TestButton.id_, 1)],
                         [(bmi.button_id, bmi.order) for bmi in ButtonMenuItem.objects.filter(content_type=None)]
                        )

    def test_edit03(self):
        ct = self.contact_ct

        class TestButton01(Button):
            id_          = Button.generate_id('creme_config', 'test_edit03_1')
            verbose_name = 'Testing purpose'


        class TestButton02(Button):
            id_          = Button.generate_id('creme_config', 'test_edit03_2')
            verbose_name = 'Testing purpose'

            def get_ctypes(self):
                return [FakeContact, FakeOrganisation]


        class TestButton03(Button):
            id_          = Button.generate_id('creme_config', 'test_edit03_3')
            verbose_name = 'Testing purpose'

            def get_ctypes(self):
                return [FakeOrganisation]  # No Contact


        # button01 = TestButton01()
        # button02 = TestButton02()
        # button03 = TestButton03()
        # button_registry.register(button01, button02, button03)
        button_registry.register(TestButton01, TestButton02, TestButton03)

        # self.client.post(self.ADD_URL, data={'ctype': ct.id})
        # self.assertEqual(1, ButtonMenuItem.objects.filter(content_type=ct).count())
        ButtonMenuItem.objects.create(content_type=ct, order=1)

        url = reverse('creme_config__edit_ctype_buttons', args=(ct.id,))
        context = self.assertGET200(url).context
        self.assertEqual(_('Edit configuration for «{model}»').format(model=ct),
                         context.get('title')
                        )

        with self.assertNoException():
            button_ids = context['form'].fields['button_ids']

        # button01_index = self._find_field_index(button_ids, button01.id_)
        # button02_index = self._find_field_index(button_ids, button02.id_)
        button01_index = self._find_field_index(button_ids, TestButton01.id_)
        button02_index = self._find_field_index(button_ids, TestButton02.id_)

        for i, (f_button_id, f_button_vname) in enumerate(button_ids.choices):
            # if f_button_id == button03.id_:
            if f_button_id == TestButton03.id_:
                self.fail('Button03 is incompatible with Contact')

        response = self.client.post(url,
                                    data={'button_ids_check_{}'.format(button01_index): 'on',
                                          # 'button_ids_value_%s' % button01_index: button01.id_,
                                          'button_ids_value_{}'.format(button01_index): TestButton01.id_,
                                          'button_ids_order_{}'.format(button01_index): 1,

                                          'button_ids_check_{}'.format(button02_index): 'on',
                                          # 'button_ids_value_%s' % button02_index: button02.id_,
                                          'button_ids_value_{}'.format(button02_index): TestButton02.id_,
                                          'button_ids_order_{}'.format(button02_index): 2,
                                         }
                                   )
        self.assertNoFormError(response)
        # self.assertEqual([(button01.id_, 1000), (button02.id_, 1001)],
        self.assertEqual([(TestButton01.id_, 1000), (TestButton02.id_, 1001)],
                         [(bmi.button_id, bmi.order)
                            for bmi in ButtonMenuItem.objects.filter(content_type=ct)
                                                             .order_by('order')
                         ]
                        )

    def test_delete01(self):
        "Can not delete default conf"
        url = self.DEL_URL
        bmi = ButtonMenuItem.objects.create(content_type=None, button_id='', order=1)
        self.assertPOST404(url)
        self.assertPOST200(url, data={'id': 0})
        self.assertStillExists(bmi)

    def test_delete_detailview02(self):
        ct = self.contact_ct
        # self.client.post(self.ADD_URL, data={'ctype': ct.id})
        # self.get_object_or_fail(ButtonMenuItem, content_type=ct)
        ButtonMenuItem.objects.create(content_type=ct, order=1)

        self.assertPOST200(self.DEL_URL, data={'id': ct.id})
        self.assertFalse(ButtonMenuItem.objects.filter(content_type=ct))
