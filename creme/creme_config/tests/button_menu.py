# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.models import ButtonMenuItem
    from creme.creme_core.gui.button_menu import Button, button_registry
    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons.models import Contact, Organisation
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('ButtonMenuConfigTestCase',)


class ButtonMenuConfigTestCase(CremeTestCase):
    ADD_URL = '/creme_config/button_menu/add/'
    DEL_URL = '/creme_config/button_menu/delete'

    @classmethod
    def setUpClass(cls):
        ButtonMenuItem.objects.all().delete()
        cls.populate('creme_core', 'creme_config')

    def setUp(self):
        self.login()

    def test_portal(self):
        self.assertGET200('/creme_config/button_menu/portal/')

    def test_add_detailview(self):
        ct = ContentType.objects.get_for_model(Contact)
        self.assertFalse(ButtonMenuItem.objects.filter(content_type=ct))

        url = self.ADD_URL
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(url, data={'ctype': ct.id}))

        self.assertEqual([('', 1)],
                         [(bmi.button_id, bmi.order) for bmi in ButtonMenuItem.objects.filter(content_type=ct)]
                        )

        response = self.client.get(url)

        with self.assertNoException():
            ctypes = response.context['form'].fields['ctype'].ctypes

        self.assertNotIn(ct, ctypes)

    def _find_field_index(self, formfield, button_id):
        for i, (f_button_id, f_button_vname) in enumerate(formfield.choices):
            if f_button_id == button_id:
                return i

        self.fail('No "%s" in field' % button_id)

    def test_edit01(self):
        ct = ContentType.objects.get_for_model(Contact)
        self.assertGET404('/creme_config/button_menu/edit/%s' % ct.id)

    def test_edit02(self):
        class TestButton(Button):
            id_          = Button.generate_id('creme_config', 'test_edit02')
            verbose_name = u'Testing purpose'


        button = TestButton()
        button_registry.register(button)

        url = '/creme_config/button_menu/edit/0'
        response = self.assertGET200(url)

        with self.assertNoException():
            button_ids = response.context['form'].fields['button_ids']

        button_index = self._find_field_index(button_ids, button.id_)

        response = self.client.post(url,
                                    data={'button_ids_check_%s' % button_index: 'on',
                                          'button_ids_value_%s' % button_index: button.id_,
                                          'button_ids_order_%s' % button_index: 1,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual([(button.id_, 1)],
                         [(bmi.button_id, bmi.order) for bmi in ButtonMenuItem.objects.filter(content_type=None)]
                        )

    def test_edit03(self):
        ct = ContentType.objects.get_for_model(Contact)

        class TestButton01(Button):
            id_          = Button.generate_id('creme_config', 'test_edit03_1')
            verbose_name = u'Testing purpose'


        class TestButton02(Button):
            id_          = Button.generate_id('creme_config', 'test_edit03_2')
            verbose_name = u'Testing purpose'

            def get_ctypes(self):
                return [Contact, Organisation]


        class TestButton03(Button):
            id_          = Button.generate_id('creme_config', 'test_edit03_3')
            verbose_name = u'Testing purpose'

            def get_ctypes(self):
                return [Organisation] #no Contact


        button01 = TestButton01()
        button02 = TestButton02()
        button03 = TestButton03()
        button_registry.register(button01, button02, button03)

        self.client.post(self.ADD_URL, data={'ctype': ct.id})
        self.assertEqual(1, ButtonMenuItem.objects.filter(content_type=ct).count())

        url = '/creme_config/button_menu/edit/%s' % ct.id
        response = self.assertGET200(url)

        with self.assertNoException():
            button_ids = response.context['form'].fields['button_ids']

        button01_index = self._find_field_index(button_ids, button01.id_)
        button02_index = self._find_field_index(button_ids, button02.id_)

        for i, (f_button_id, f_button_vname) in enumerate(button_ids.choices):
            if f_button_id == button03.id_:
                self.fail('Button03 is incompatible with Contact')

        response = self.client.post(url,
                                    data={'button_ids_check_%s' % button01_index: 'on',
                                          'button_ids_value_%s' % button01_index: button01.id_,
                                          'button_ids_order_%s' % button01_index: 1,

                                          'button_ids_check_%s' % button02_index: 'on',
                                          'button_ids_value_%s' % button02_index: button02.id_,
                                          'button_ids_order_%s' % button02_index: 2,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual([(button01.id_, 1000), (button02.id_, 1001)],
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
        self.get_object_or_fail(ButtonMenuItem, pk=bmi.pk) #still exists

    def test_delete_detailview02(self):
        ct = ContentType.objects.get_for_model(Contact)
        self.client.post(self.ADD_URL, data={'ctype': ct.id})
        self.get_object_or_fail(ButtonMenuItem, content_type=ct)

        self.assertPOST200(self.DEL_URL, data={'id': ct.id})
        self.assertFalse(ButtonMenuItem.objects.filter(content_type=ct))
