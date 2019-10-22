# -*- coding: utf-8 -*-

try:
    from json import loads as json_load

    from django.apps import apps
    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse
    from django.utils.translation import gettext as _

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.models import (
        CremeEntity,
        FieldsConfig,
        FakeContact, FakeOrganisation,
    )
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class FieldsConfigTestCase(CremeTestCase):
    WIZARD_URL = reverse('creme_config__create_fields_config')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.ct = ContentType.objects.get_for_model(FakeContact)

    def _build_edit_url(self, fconf):
        return reverse('creme_config__edit_fields_config', args=(fconf.pk,))

    def _create_fconf(self):
        return FieldsConfig.objects.create(content_type=self.ct, descriptions=())

    def _configure_all_models(self):
        used_ct_ids = {*FieldsConfig.objects.values_list('content_type', flat=True)}
        FieldsConfig.objects.bulk_create([
            FieldsConfig(content_type=ct, descriptions=())
                for ct in map(ContentType.objects.get_for_model,
                              filter(FieldsConfig.is_model_valid, apps.get_models())
                             )
                    if ct.id not in used_ct_ids
        ])

    def test_portal01(self):
        self.login()

        response = self.assertGET200(reverse('creme_config__fields'))
        self.assertTemplateUsed(response, 'creme_config/fields_config_portal.html')
        self.assertContains(response, self.WIZARD_URL)

    def test_portal02(self):
        "All CTypes are already configured."
        self._configure_all_models()
        self.login()

        response = self.assertGET200(reverse('creme_config__fields'))
        self.assertNotContains(response, self.WIZARD_URL)

    def test_edit01(self):
        self.login()

        get_field = FakeContact._meta.get_field
        self.assertTrue(get_field('phone').get_tag('optional'))
        self.assertTrue(get_field('birthday').get_tag('optional'))
        self.assertFalse(get_field('last_name').get_tag('optional'))
        self.assertTrue(get_field('image').get_tag('optional'))

        # --------
        fconf = self._create_fconf()

        url = self._build_edit_url(fconf)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(_('Edit «{object}»').format(object=fconf), context.get('title'))

        with self.assertNoException():
            choices = context['form'].fields['hidden'].choices
            choices_keys = {k for k, v in choices}

        self.assertIn('phone',    choices_keys)
        self.assertIn('birthday', choices_keys)
        self.assertNotIn('last_name', choices_keys)
        self.assertIn('image', choices_keys)
        self.assertNotIn('image__description', choices_keys)

        # ---
        response = self.client.post(url, data={'hidden': ['phone', 'birthday']})
        self.assertNoFormError(response)

        fconf = self.refresh(fconf)
        self.assertEqual([['phone', {'hidden': True}], ['birthday', {'hidden': True}]],
                         json_load(fconf.raw_descriptions)
                        )  # TODO: meh

        # test initial ------
        response = self.assertGET200(url)

        with self.assertNoException():
            hidden_f = response.context['form'].fields['hidden']

        self.assertCountEqual(['phone', 'birthday'], hidden_f.initial)

    def test_edit02(self):
        "Not super-user."
        self.login(is_superuser=False)

        fconf = self._create_fconf()
        url = self._build_edit_url(fconf)
        self.assertGET403(url)

        # ---
        role = self.role
        role.admin_4_apps = ['creme_core']
        role.save()
        self.assertGET200(url)

    def test_delete(self):
        self.login()
        fconf = self._create_fconf()

        self.assertPOST200(reverse('creme_config__delete_fields_config'), data={'id': fconf.pk})
        self.assertDoesNotExist(fconf)

    def test_wizard_model_step(self):
        self.login()

        contact_ct = self.ct
        self.assertFalse(FieldsConfig.objects.filter(content_type=contact_ct).exists())

        response = self.assertGET200(self.WIZARD_URL)

        with self.assertNoException():
            ctypes = response.context['form'].fields['ctype'].ctypes

        self.assertIn(contact_ct, ctypes)

        get_ct = ContentType.objects.get_for_model
        self.assertIn(get_ct(FakeOrganisation), ctypes)
        self.assertNotIn(get_ct(CremeEntity), ctypes)

        response = self.client.post(self.WIZARD_URL,
                                    # {'field_config_wizard-current_step': '0',
                                    {'fields_config_wizard-current_step': '0',
                                     '0-ctype': contact_ct.pk,
                                    },
                                   )
        self.assertNoFormError(response)

        # last step is not submitted so nothing yet in database
        self.assertFalse(FieldsConfig.objects.filter(content_type=contact_ct).exists())

    def test_wizard_model_step_invalid(self):
        self.login()

        ctype = self.ct
        self.assertFalse(FieldsConfig.objects.filter(content_type=ctype).exists())

        response = self.assertGET200(self.WIZARD_URL)
        self.assertIn(ctype, response.context['form'].fields['ctype'].ctypes)

        response = self.client.post(self.WIZARD_URL,
                                    # {'field_config_wizard-current_step': '0',
                                    {'fields_config_wizard-current_step': '0',
                                     '0-ctype': 'unknown',
                                    },
                                   )
        self.assertFormError(
            response, 'form', 'ctype',
            _('Select a valid choice. That choice is not one of the available choices.')
        )
        self.assertFalse(FieldsConfig.objects.filter(content_type=ctype).exists())

    def test_wizard_config_step(self):
        self.login()

        ctype = self.ct
        self.assertFalse(FieldsConfig.objects.filter(content_type=ctype).exists())

        response = self.assertGET200(self.WIZARD_URL)
        self.assertIn(ctype, response.context['form'].fields['ctype'].ctypes)

        response = self.assertPOST200(self.WIZARD_URL,
                                      # {'field_config_wizard-current_step': '0',
                                      {'fields_config_wizard-current_step': '0',
                                       '0-ctype': ctype.pk,
                                      },
                                     )

        ctype_fieldnames = {e[0] for e in response.context['form'].fields['hidden'].choices}
        self.assertIn('phone', ctype_fieldnames)
        self.assertIn('birthday', ctype_fieldnames)

        self.assertFalse(FieldsConfig.objects.filter(content_type=ctype).exists())

        response = self.client.post(self.WIZARD_URL,
                                    # {'field_config_wizard-current_step': '1',
                                    {'fields_config_wizard-current_step': '1',
                                     '1-hidden': ['phone', 'birthday'],
                                    },
                                   )
        self.assertNoFormError(response)

        config = FieldsConfig.objects.get(content_type=ctype)
        self.assertListEqual(config.descriptions,
                             [('phone', {'hidden': True}),
                              ('birthday', {'hidden': True})
                             ],
                            )

    def test_wizard_go_back(self):
        self.login()

        ctype = self.ct
        self.assertFalse(FieldsConfig.objects.filter(content_type=ctype).exists())

        response = self.assertGET200(self.WIZARD_URL)
        self.assertIn(ctype, response.context['form'].fields['ctype'].ctypes)

        self.assertPOST200(self.WIZARD_URL,
                           # {'field_config_wizard-current_step': '0',
                           {'fields_config_wizard-current_step': '0',
                            '0-ctype': ctype.pk,
                           },
                          )

        # return to first step
        response = self.assertPOST200(self.WIZARD_URL,
                                      # {'field_config_wizard-current_step': '1',
                                      {'fields_config_wizard-current_step': '1',
                                       'wizard_goto_step': '0',
                                       '1-hidden': ['phone', 'last_name'],
                                      },
                                     )
        self.assertNoFormError(response)
        self.assertIn(ctype, response.context['form'].fields['ctype'].ctypes)

    def test_wizard_409(self):
        "All CTypes are already configured."
        self._configure_all_models()
        self.login()
        self.assertGET409(self.WIZARD_URL)

    def test_wizard_403(self):
        "Perm is 'creme_core.can_admin'."
        self.login(is_superuser=False, allowed_apps=('creme_core',))
        self.assertGET403(self.WIZARD_URL)
