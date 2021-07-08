# -*- coding: utf-8 -*-

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.core.setting_key import SettingKey, setting_key_registry
from creme.creme_core.models import SettingValue
from creme.creme_core.tests.base import CremeTestCase


# TODO: clean registry in teardDown...
class SettingTestCase(CremeTestCase):
    @staticmethod
    def _build_edit_url(setting_value):
        return reverse('creme_config__edit_setting', args=(setting_value.id,))

    def test_edit_string(self):
        self.login()

        sk = SettingKey(
            id='persons-test_edit_string', description='Page title',
            app_label='persons', type=SettingKey.STRING, hidden=False,
        )
        setting_key_registry.register(sk)

        title = 'May the source be with you'
        sv = SettingValue(key=sk)
        sv.value = title
        sv.save()

        url = self._build_edit_url(sv)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        get_ctxt = response.context.get
        self.assertEqual(_('Edit «{key}»').format(key=sk.description), get_ctxt('title'))
        self.assertEqual(_('Save the modifications'),                  get_ctxt('submit_label'))

        # ---
        title = title.upper()
        self.assertNoFormError(self.client.post(url, data={'value': title}))
        self.assertEqual(title, self.refresh(sv).value)

    def test_edit_int(self):
        self.login()

        sk = SettingKey(
            id='persons-test_edit_int', description='Page size',
            app_label='persons', type=SettingKey.INT,
        )
        setting_key_registry.register(sk)

        size = 156
        sv = SettingValue(key=sk)
        sv.value = size
        sv.save()

        size += 15
        self.assertNoFormError(self.client.post(self._build_edit_url(sv), data={'value': size}))
        self.assertEqual(size, self.refresh(sv).value)

    def test_edit_bool(self):
        self.login()

        sk = SettingKey(
            id='persons-test_edit_bool', description='Display logo ?',
            app_label='persons', type=SettingKey.BOOL,
        )
        setting_key_registry.register(sk)

        sv = SettingValue(key=sk)
        sv.value = True
        sv.save()

        # False -> empty POST
        self.assertNoFormError(self.client.post(self._build_edit_url(sv), data={}))
        self.assertFalse(self.refresh(sv).value)

    def test_edit_hour(self):
        self.login()

        sk = SettingKey(
            id='persons-test_edit_hour', description='Reminder hour',
            app_label='persons', type=SettingKey.HOUR,
        )
        setting_key_registry.register(sk)

        hour = 11
        sv = SettingValue(key=sk)
        sv.value = hour
        sv.save()

        url = self._build_edit_url(sv)
        hour += 1
        self.assertNoFormError(self.client.post(url, data={'value': hour}))
        self.assertEqual(hour, self.refresh(sv).value)

        response = self.assertPOST200(url, data={'value': 24})
        self.assertFormError(
            response, 'form', 'value',
            _('Ensure this value is less than or equal to %(limit_value)s.') % {
                'limit_value': 23,
            },
        )

        response = self.assertPOST200(url, data={'value': -1})
        self.assertFormError(
            response, 'form', 'value',
            _('Ensure this value is greater than or equal to %(limit_value)s.') % {
                'limit_value': 0,
            },
        )

    def test_edit_email(self):
        self.login()

        sk = SettingKey(
            id='persons-test_edit_email', description='Campaign Sender',
            app_label='persons', type=SettingKey.EMAIL,
        )
        setting_key_registry.register(sk)

        email = 'd.knut@eswat.ol'
        sv = SettingValue(key=sk)
        sv.value = email
        sv.save()

        url = self._build_edit_url(sv)

        response = self.assertPOST200(url, data={'value': 42})
        self.assertFormError(
            response, 'form', 'value', _('Enter a valid email address.'),
        )

        email = 'd.knut.knut@eswat.ol'
        self.assertNoFormError(self.client.post(url, data={'value': email}))
        self.assertEqual(email, self.refresh(sv).value)

    def test_edit_hidden01(self):
        "Hidden => not editable (value=True)"
        self.login()

        sk = SettingKey(
            id='persons-test_edit_hidden01', description='Display logo ?',
            app_label='persons', type=SettingKey.BOOL, hidden=True,
        )
        setting_key_registry.register(sk)

        sv = SettingValue(key=sk)
        sv.value = True
        sv.save()
        self.assertGET409(self._build_edit_url(sv))

    def test_edit_hidden02(self):
        "Hidden => not editable (value=False)."
        self.login()

        sk = SettingKey(
            id='persons-test_edit_hidden02', description='Display logo ?',
            app_label='persons', type=SettingKey.BOOL, hidden=True,
        )
        setting_key_registry.register(sk)

        sv = SettingValue(key=sk)
        sv.value = False
        sv.save()
        self.assertGET409(self._build_edit_url(sv))

    def test_edit_blank01(self):
        self.login()

        sk = SettingKey(
            id='persons-test_edit_blank01', description='API key',
            app_label='persons', type=SettingKey.STRING,
            blank=True,
        )
        setting_key_registry.register(sk)

        sv = SettingValue(key=sk)
        sv.value = '123-456-abc'
        sv.save()

        self.assertNoFormError(self.client.post(self._build_edit_url(sv), data={'value': ''}))

        sv = self.refresh(sv)
        self.assertEqual('', sv.value_str)
        self.assertIsNone(sv.value)

    def test_edit_blank02(self):
        self.login()

        sk = SettingKey(
            id='persons-test_edit_blank02', description='API key',
            app_label='persons', type=SettingKey.INT,
            blank=True,
        )
        setting_key_registry.register(sk)

        sv = SettingValue(key=sk)
        sv.value = 12345
        sv.save()

        self.assertNoFormError(self.client.post(self._build_edit_url(sv)))

        sv = self.refresh(sv)
        self.assertEqual('', sv.value_str)
        self.assertIsNone(sv.value)

        # ---
        self.assertNoFormError(self.client.post(self._build_edit_url(sv), data={'value': ''}))

        sv = self.refresh(sv)
        self.assertEqual('', sv.value_str)
        self.assertIsNone(sv.value)

    def test_edit_app_perm01(self):
        self.login(is_superuser=False, admin_4_apps=['creme_core'])

        sk = SettingKey(
            id='creme_core-test_edit_app_perm01', description='Page title',
            app_label='creme_core', type=SettingKey.STRING, hidden=False,
        )
        setting_key_registry.register(sk)

        sv = SettingValue(key=sk)
        sv.value = 'May the source be with you'
        sv.save()
        self.assertGET200(self._build_edit_url(sv))

    def test_edit_app_perm02(self):
        "No app perm => error."
        self.login(is_superuser=False)

        sk = SettingKey(
            id='creme_core-test_edit_app_perm02', description='Page title',
            app_label='creme_core', type=SettingKey.STRING, hidden=False,
        )
        setting_key_registry.register(sk)

        sv = SettingValue(key=sk)
        sv.value = 'May the source be with you'
        sv.save()
        self.assertGET403(self._build_edit_url(sv))
