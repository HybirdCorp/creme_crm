from django import forms
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
        self.login_as_root()

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
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')

        ctxt1 = response1.context
        self.assertEqual(_('Edit «{key}»').format(key=sk.description), ctxt1.get('title'))
        self.assertEqual(_('Save the modifications'),                  ctxt1.get('submit_label'))

        with self.assertNoException():
            value_f1 = ctxt1['form'].fields['value']

        self.assertIsInstance(value_f1, forms.CharField)
        self.assertIsInstance(value_f1.widget, forms.Textarea)
        self.assertEqual(title, value_f1.initial)

        # ---
        title = title.upper()
        self.assertNoFormError(self.client.post(url, data={'value': title}))
        self.assertEqual(title, self.refresh(sv).value)

    def test_edit_int(self):
        self.login_as_root()

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
        self.login_as_root()

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
        self.login_as_root()

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

        response1 = self.assertPOST200(url, data={'value': 24})
        self.assertFormError(
            response1.context['form'],
            field='value',
            errors=_('Ensure this value is less than or equal to %(limit_value)s.') % {
                'limit_value': 23,
            },
        )

        # ---
        response2 = self.assertPOST200(url, data={'value': -1})
        self.assertFormError(
            response2.context['form'],
            field='value',
            errors=_('Ensure this value is greater than or equal to %(limit_value)s.') % {
                'limit_value': 0,
            },
        )

    def test_edit_email(self):
        self.login_as_root()

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
            self.get_form_or_fail(response),
            field='value', errors=_('Enter a valid email address.'),
        )

        email = 'd.knut.knut@eswat.ol'
        self.assertNoFormError(self.client.post(url, data={'value': email}))
        self.assertEqual(email, self.refresh(sv).value)

    def test_edit_hidden01(self):
        "Hidden => not editable (value=True)"
        self.login_as_root()

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
        self.login_as_root()

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
        self.login_as_root()

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
        self.assertEqual('', sv.json_value)
        self.assertEqual('', sv.value)

    def test_edit_blank02(self):
        self.login_as_root()

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
        self.assertIsNone(sv.json_value)
        self.assertIsNone(sv.value)

        # ---
        self.assertNoFormError(self.client.post(self._build_edit_url(sv), data={'value': ''}))

        sv = self.refresh(sv)
        self.assertIsNone(sv.json_value)
        self.assertIsNone(sv.value)

    def test_edit_app_perm01(self):
        self.login_as_standard(admin_4_apps=['creme_core'])

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
        self.login_as_standard()

        sk = SettingKey(
            id='creme_core-test_edit_app_perm02', description='Page title',
            app_label='creme_core', type=SettingKey.STRING, hidden=False,
        )
        setting_key_registry.register(sk)

        sv = SettingValue(key=sk)
        sv.value = 'May the source be with you'
        sv.save()
        self.assertGET403(self._build_edit_url(sv))
