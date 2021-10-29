# -*- coding: utf-8 -*-

# from json import loads as json_load
# from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_config.bricks import FieldsConfigsBrick
from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.gui.fields_config import fields_config_registry
from creme.creme_core.models import (
    CremeEntity,
    FakeContact,
    FakeOrganisation,
    FieldsConfig,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_models import FakeActivity, FakeSector
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.translation import plural


class FieldsConfigTestCase(BrickTestCaseMixin, CremeTestCase):
    WIZARD_URL = reverse('creme_config__create_fields_config')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.ct = ContentType.objects.get_for_model(FakeContact)

    @staticmethod
    def _build_edit_url(fconf):
        return reverse('creme_config__edit_fields_config', args=(fconf.pk,))

    def _create_fconf(self, model=None):
        return FieldsConfig.objects.create(content_type=model or self.ct, descriptions=())

    @staticmethod
    def _configure_all_models():
        used_ct_ids = {*FieldsConfig.objects.values_list('content_type', flat=True)}
        FieldsConfig.objects.bulk_create([
            FieldsConfig(content_type=ct, descriptions=())
            for ct in map(
                ContentType.objects.get_for_model,
                # filter(FieldsConfig.objects.is_model_valid, apps.get_models())
                fields_config_registry.models
            )
            if ct.id not in used_ct_ids
        ])

    def test_portal01(self):
        self.login()

        self._create_fconf()

        response = self.assertGET200(reverse('creme_config__fields'))
        self.assertTemplateUsed(response, 'creme_config/portals/fields-config.html')

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), FieldsConfigsBrick.id_,
        )

        count = FieldsConfig.objects.count()
        msg = (
            _('{count} Configured types of resource')
            if plural(count) else
            _('{count} Configured type of resource')
        )
        self.assertEqual(
            msg.format(count=count),
            self.get_brick_title(brick_node),
        )
        self.assertBrickHeaderHasButton(
            self.get_brick_header_buttons(brick_node),
            url=self.WIZARD_URL, label=_('New fields configuration'),
        )

    def test_portal02(self):
        "All CTypes are already configured."
        self._configure_all_models()
        self.login()

        response = self.assertGET200(reverse('creme_config__fields'))
        self.assertNotContains(response, self.WIZARD_URL)

    def test_portal_errors(self):
        self.login()

        self._create_fconf(FakeSector)

        response = self.assertGET200(reverse('creme_config__fields'))

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), FieldsConfigsBrick.id_,
        )

        error_node = self.get_html_node_or_fail(brick_node, './/ul[@class="errorlist"]/li')
        self.assertEqual(
            _(
                'This type of resource cannot be configured ; '
                'please contact your administrator.'
            ),
            error_node.text,
        )

    def test_edit01(self):
        self.login()

        get_field = FakeContact._meta.get_field
        model_phone_field = get_field('phone')
        self.assertTrue(model_phone_field.get_tag('optional'))
        self.assertTrue(model_phone_field.get_tag(FieldTag.OPTIONAL))
        self.assertTrue(model_phone_field.blank)

        self.assertTrue(get_field('birthday').get_tag(FieldTag.OPTIONAL))

        model_last_name_field = get_field('last_name')
        self.assertFalse(model_last_name_field.get_tag('optional'))
        self.assertFalse(model_last_name_field.get_tag(FieldTag.OPTIONAL))
        self.assertFalse(model_last_name_field.blank)

        model_email_field = get_field('email')
        self.assertFalse(model_email_field.get_tag(FieldTag.OPTIONAL))
        self.assertTrue(model_email_field.blank)

        self.assertTrue(get_field('image').get_tag(FieldTag.OPTIONAL))

        # --------
        fconf = self._create_fconf()

        url = self._build_edit_url(fconf)
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')

        context = response1.context
        self.assertEqual(_('Edit «{object}»').format(object=fconf), context.get('title'))

        with self.assertNoException():
            # choices = context['form'].fields['hidden'].choices
            fields1 = context['form'].fields

            phone_f1 = fields1['phone']
            phone_f_choices = phone_f1.choices

            email_f = fields1['email']
            email_f_choices = email_f.choices

        # self.assertInChoices(value='phone', label=_('Phone number'), choices=choices)
        # self.assertInChoices(value='birthday', label=_('Birthday'), choices=choices)
        # self.assertNotInChoices(value='last_name', choices=choices)
        # self.assertInChoices(value='image', label=_('Photograph'), choices=choices)
        # self.assertNotInChoices(value='image__description', choices=choices)

        self.assertEqual(_('Phone number'), phone_f1.label)
        self.assertInChoices(value='',         label='---',         choices=phone_f_choices)
        self.assertInChoices(value='hidden',   label=_('Hidden'),   choices=phone_f_choices)
        self.assertInChoices(value='required', label=_('Required'), choices=phone_f_choices)

        self.assertEqual(_('Email address'), email_f.label)
        self.assertInChoices(value='',         label='---',         choices=email_f_choices)
        self.assertInChoices(value='required', label=_('Required'), choices=email_f_choices)
        self.assertNotInChoices(value='hidden', choices=email_f_choices)

        self.assertNotIn('last_name', fields1)
        self.assertNotIn('cremeentity_ptr', fields1)
        self.assertNotIn('id', fields1)

        # TODO: assertSorted
        labels = [
            elt.text
            for elt in self.get_html_tree(response1.content).findall('.//label')
        ]
        self.assertListEqual(sorted(labels), labels)

        # ---
        # response2 = self.client.post(url, data={'hidden': ['phone', 'birthday']})
        response2 = self.client.post(
            url,
            data={
                'phone': 'required',
                'birthday': 'hidden',
            },
        )
        self.assertNoFormError(response2)

        # fconf = self.refresh(fconf)
        # self.assertListEqual(
        #     [['phone', {'hidden': True}], ['birthday', {'hidden': True}]],
        #     json_load(fconf.raw_descriptions),
        # )
        self.assertListEqual(
            [('birthday', {'hidden': True}), ('phone', {'required': True})],
            self.refresh(fconf).descriptions,
        )

        # test initial ------
        response3 = self.assertGET200(url)

        with self.assertNoException():
            # hidden_f = response3.context['form'].fields['hidden']
            fields3 = response3.context['form'].fields
            email_f3 = fields3['email']
            phone_f3 = fields3['phone']
            birthday_f3 = fields3['birthday']

        # self.assertCountEqual(['phone', 'birthday'], hidden_f.initial)
        self.assertEqual('',         email_f3.initial)
        self.assertEqual('required', phone_f3.initial)
        self.assertEqual('hidden',   birthday_f3.initial)

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

    def test_edit03(self):
        "Model not registered."
        self.login()

        self.assertFalse(fields_config_registry.is_model_registered(FakeActivity))

        fconf = FieldsConfig.objects.create(content_type=FakeActivity, descriptions=())
        self.assertGET409(self._build_edit_url(fconf))

    def test_delete(self):
        self.login()
        fconf = self._create_fconf()

        self.assertPOST200(reverse('creme_config__delete_fields_config'), data={'id': fconf.pk})
        self.assertDoesNotExist(fconf)

    def test_wizard_model_step(self):
        self.login()

        contact_ct = self.ct
        self.assertFalse(FieldsConfig.objects.filter(content_type=contact_ct).exists())

        ctxt1 = self.assertGET200(self.WIZARD_URL).context
        self.assertEqual(_('Create a fields configuration'), ctxt1.get('title'))

        with self.assertNoException():
            ctypes = ctxt1['form'].fields['ctype'].ctypes

        self.assertIn(contact_ct, ctypes)

        get_ct = ContentType.objects.get_for_model
        self.assertIn(get_ct(FakeOrganisation), ctypes)
        self.assertNotIn(get_ct(CremeEntity), ctypes)

        response2 = self.client.post(
            self.WIZARD_URL,
            data={
                'fields_config_wizard-current_step': '0',
                '0-ctype': contact_ct.pk,
            },
        )
        self.assertNoFormError(response2)

        # last step is not submitted so nothing yet in database
        self.assertFalse(FieldsConfig.objects.filter(content_type=contact_ct))

    def test_wizard_model_step_invalid(self):
        self.login()

        ctype = self.ct
        self.assertFalse(FieldsConfig.objects.filter(content_type=ctype).exists())

        response1 = self.assertGET200(self.WIZARD_URL)
        self.assertIn(ctype, response1.context['form'].fields['ctype'].ctypes)

        response2 = self.client.post(
            self.WIZARD_URL,
            data={
                'fields_config_wizard-current_step': '0',
                '0-ctype': 'unknown',
            },
        )
        self.assertFormError(
            response2, 'form', 'ctype',
            _('Select a valid choice. That choice is not one of the available choices.'),
        )
        self.assertFalse(FieldsConfig.objects.filter(content_type=ctype).exists())

    def test_wizard_config_step(self):
        self.login()

        ctype = self.ct
        self.assertFalse(FieldsConfig.objects.filter(content_type=ctype))

        ctxt1 = self.assertGET200(self.WIZARD_URL).context
        self.assertIn(ctype, ctxt1['form'].fields['ctype'].ctypes)

        response2 = self.assertPOST200(
            self.WIZARD_URL,
            data={
                'fields_config_wizard-current_step': '0',
                '0-ctype': ctype.pk,
            },
        )

        ctxt2 = response2.context
        self.assertEqual(
            _('Create a fields configuration for «{model}»').format(model=ctype),
            ctxt2.get('title'),
        )

        with self.assertNoException():
            # choices = ctxt2['form'].fields['hidden'].choices
            choices = ctxt2['form'].fields['phone'].choices

        # self.assertInChoices(value='phone',    label=_('Phone number'), choices=choices)
        # self.assertInChoices(value='birthday', label=_('Birthday'),     choices=choices)
        self.assertInChoices(value='hidden',   label=_('Hidden'),   choices=choices)
        self.assertInChoices(value='required', label=_('Required'), choices=choices)

        self.assertFalse(FieldsConfig.objects.filter(content_type=ctype))

        response3 = self.client.post(
            self.WIZARD_URL,
            data={
                'fields_config_wizard-current_step': '1',
                # '1-hidden': ['phone', 'birthday'],
                '1-phone': 'required',
                '1-birthday': 'hidden',
            },
        )
        self.assertNoFormError(response3)

        config = self.get_object_or_fail(FieldsConfig, content_type=ctype)
        # self.assertListEqual(
        #     [
        #         ('phone', {'hidden': True}),
        #         ('birthday', {'hidden': True}),
        #     ],
        #     config.descriptions,
        # )
        self.assertListEqual(
            [
                ('birthday', {'hidden': True}),
                ('phone', {'required': True}),
            ],
            config.descriptions,
        )

    def test_wizard_go_back(self):
        self.login()

        ctype = self.ct
        self.assertFalse(FieldsConfig.objects.filter(content_type=ctype))

        response1 = self.assertGET200(self.WIZARD_URL)
        self.assertIn(ctype, response1.context['form'].fields['ctype'].ctypes)

        self.assertPOST200(
            self.WIZARD_URL,
            data={
                'fields_config_wizard-current_step': '0',
                '0-ctype': ctype.pk,
            },
        )

        # return to first step
        response2 = self.assertPOST200(
            self.WIZARD_URL,
            data={
                'fields_config_wizard-current_step': '1',
                'wizard_goto_step': '0',
                '1-hidden': ['phone', 'last_name'],
            },
        )
        self.assertNoFormError(response2)
        self.assertIn(ctype, response2.context['form'].fields['ctype'].ctypes)

    def test_wizard_409(self):
        "All CTypes are already configured."
        self._configure_all_models()
        self.login()
        self.assertGET409(self.WIZARD_URL)

    def test_wizard_403(self):
        "Perm is 'creme_core.can_admin'."
        self.login(is_superuser=False, allowed_apps=('creme_core',))
        self.assertGET403(self.WIZARD_URL)
