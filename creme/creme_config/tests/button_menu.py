# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import ButtonMenuItem
    from creme_core.gui.button_menu import Button, button_registry
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact, Organisation
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('ButtonMenuConfigTestCase',)


class ButtonMenuConfigTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        ButtonMenuItem.objects.all().delete()
        cls.populate('creme_core', 'creme_config')

    def setUp(self):
        #self.populate('creme_core', 'creme_config')
        self.login()

    def test_portal(self):
        self.assertEqual(200, self.client.get('/creme_config/button_menu/portal/').status_code)

    def test_add_detailview(self):
        ct = ContentType.objects.get_for_model(Contact)
        self.assertFalse(ButtonMenuItem.objects.filter(content_type=ct))

        url = '/creme_config/button_menu/add/'
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={'ct_id': ct.id})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        self.assertEqual([('', 1)],
                         [(bmi.button_id, bmi.order) for bmi in ButtonMenuItem.objects.filter(content_type=ct)]
                        )

        response = self.client.get(url)

        with self.assertNoException():
            choices = response.context['form'].fields['ct_id'].choices

        self.assertNotIn(ct.id, (ct_id for ct_id, ctype in choices))

    def _find_field_index(self, formfield, button_id):
        for i, (f_button_id, f_button_vname) in enumerate(formfield.choices):
            if f_button_id == button_id:
                return i

        self.fail('No "%s" in field' % button_id)

    def test_edit01(self):
        ct = ContentType.objects.get_for_model(Contact)
        self.assertEqual(404, self.client.get('/creme_config/button_menu/edit/%s' % ct.id).status_code)

    def test_edit02(self):
        class TestButton(Button):
            id_          = Button.generate_id('creme_config', 'test_edit02')
            verbose_name = u'Testing purpose'


        button = TestButton()
        button_registry.register(button)

        url = '/creme_config/button_menu/edit/0'
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            button_ids = response.context['form'].fields['button_ids']
        except KeyError as e:
            self.fail(str(e))

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

        self.client.post('/creme_config/button_menu/add/', data={'ct_id': ct.id})
        self.assertEqual(1, ButtonMenuItem.objects.filter(content_type=ct).count())

        url = '/creme_config/button_menu/edit/%s' % ct.id
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            button_ids = response.context['form'].fields['button_ids']
        except KeyError as e:
            self.fail(str(e))

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
                         [(bmi.button_id, bmi.order) for bmi in ButtonMenuItem.objects.filter(content_type=ct).order_by('order')]
                        )

    def test_delete01(self): #can not delete default conf
        url = '/creme_config/button_menu/delete'
        bmi = ButtonMenuItem.objects.create(content_type=None, button_id='', order=1)
        self.assertEqual(404, self.client.post(url).status_code)

        self.assertEqual(200, self.client.post(url, data={'id': 0}).status_code)
        ButtonMenuItem.objects.get(pk=bmi.pk) #still exists

    def test_delete_detailview02(self):
        ct = ContentType.objects.get_for_model(Contact)
        self.client.post('/creme_config/button_menu/add/', data={'ct_id': ct.id})
        self.assertEqual(1, ButtonMenuItem.objects.filter(content_type=ct).count())

        response = self.client.post('/creme_config/button_menu/delete', data={'id': ct.id})
        self.assertEqual(200, response.status_code)
        self.assertFalse(ButtonMenuItem.objects.filter(content_type=ct))
