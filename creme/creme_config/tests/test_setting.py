# -*- coding: utf-8 -*-

try:
    from django.core.urlresolvers import reverse
    from django.utils.translation import ugettext as _

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.core.setting_key import SettingKey, setting_key_registry
    from creme.creme_core.models import SettingValue
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


# TODO: clean registry in teardDown...
class SettingTestCase(CremeTestCase):
    def _build_edit_url(self, setting_value):
        return reverse('creme_config__edit_setting', args=(setting_value.id,))

    def test_edit_string(self):
        self.login()

        sk = SettingKey(id='persons-test_edit_string', description=u'Page title',
                        app_label='persons', type=SettingKey.STRING, hidden=False,
                       )
        setting_key_registry.register(sk)

        title = 'May the source be with you'
        sv = SettingValue.objects.create(key=sk, user=None, value=title)

        url = self._build_edit_url(sv)
        self.assertGET200(url)

        title = title.upper()
        self.assertNoFormError(self.client.post(url, data={'value': title}))
        self.assertEqual(title, self.refresh(sv).value)

    def test_edit_int(self):
        self.login()

        sk = SettingKey(id='persons-test_edit_int', description=u"Page size",
                        app_label='persons', type=SettingKey.INT,
                       )
        setting_key_registry.register(sk)

        size = 156
        sv = SettingValue.objects.create(key=sk, value=size)

        size += 15
        self.assertNoFormError(self.client.post(self._build_edit_url(sv), data={'value': size}))
        self.assertEqual(size, self.refresh(sv).value)

    def test_edit_bool(self):
        self.login()

        sk = SettingKey(id='persons-test_edit_bool', description=u"Display logo ?",
                        app_label='persons', type=SettingKey.BOOL,
                       )
        setting_key_registry.register(sk)

        sv = SettingValue.objects.create(key=sk, value=True)

        self.assertNoFormError(self.client.post(self._build_edit_url(sv), data={})) #False -> empty POST
        self.assertFalse(self.refresh(sv).value)

    def test_edit_hour(self):
        self.login()

        sk = SettingKey(id='persons-test_edit_hour', description='Reminder hour',
                        app_label='persons', type=SettingKey.HOUR,
                       )
        setting_key_registry.register(sk)

        hour = 11
        sv = SettingValue.objects.create(key=sk, value=hour)

        url = self._build_edit_url(sv)
        hour += 1
        self.assertNoFormError(self.client.post(url, data={'value': hour}))
        self.assertEqual(hour, self.refresh(sv).value)

        response = self.assertPOST200(url, data={'value': 24})
        self.assertFormError(response, 'form', 'value',
                             _(u'Ensure this value is less than or equal to %(limit_value)s.') % {
                                    'limit_value': 23,
                                }
                            )

        response = self.assertPOST200(url, data={'value': -1})
        self.assertFormError(response, 'form', 'value',
                             _(u'Ensure this value is greater than or equal to %(limit_value)s.') % {
                                    'limit_value': 0,
                                }
                            )

    def test_edit_email(self):
        self.login()

        sk = SettingKey(id='persons-test_edit_email', description='Campaign Sender',
                        app_label='persons', type=SettingKey.EMAIL,
                       )
        setting_key_registry.register(sk)

        email = u'd.knut@eswat.ol'
        sv = SettingValue.objects.create(key=sk, value=email)

        url = self._build_edit_url(sv)

        response = self.assertPOST200(url, data={'value': 42})
        self.assertFormError(response, 'form', 'value',
                             _(u'Enter a valid email address.')
                            )

        email = u'd.knut.knut@eswat.ol'
        self.assertNoFormError(self.client.post(url, data={'value': email}))
        self.assertEqual(email, self.refresh(sv).value)

    def test_edit_hidden01(self):
        "Hidden => not editable (value=True)"
        self.login()

        sk = SettingKey(id='persons-test_edit_hidden01', description=u'Display logo ?',
                        app_label='persons', type=SettingKey.BOOL, hidden=True,
                       )
        setting_key_registry.register(sk)

        sv = SettingValue.objects.create(key=sk, value=True)
        self.assertGET404(self._build_edit_url(sv))

    def test_edit_hidden02(self):
        "Hidden => not editable (value=False)"
        self.login()

        sk = SettingKey(id='persons-test_edit_hidden02', description=u'Display logo ?',
                        app_label='persons', type=SettingKey.BOOL, hidden=True,
                       )
        setting_key_registry.register(sk)

        sv = SettingValue.objects.create(key=sk, value=False)
        self.assertGET404(self._build_edit_url(sv))

    def test_edit_blank01(self):
        self.login()

        sk = SettingKey(id='persons-test_edit_blank01', description=u'API key',
                        app_label='persons', type=SettingKey.STRING,
                        blank=True,
                       )
        setting_key_registry.register(sk)

        sv = SettingValue.objects.create(key=sk, value='123-456-abc')

        self.assertNoFormError(self.client.post(self._build_edit_url(sv), data={'value': ''}))

        sv = self.refresh(sv)
        self.assertEqual('', sv.value_str)
        self.assertIsNone(sv.value)

    def test_edit_blank02(self):
        self.login()

        sk = SettingKey(id='persons-test_edit_blank02', description=u'API key',
                        app_label='persons', type=SettingKey.INT,
                        blank=True,
                       )
        setting_key_registry.register(sk)

        sv = SettingValue.objects.create(key=sk, value=12345)

        self.assertNoFormError(self.client.post(self._build_edit_url(sv)))

        sv = self.refresh(sv)
        self.assertEqual('', sv.value_str)
        self.assertIsNone(sv.value)

        # ---
        self.assertNoFormError(self.client.post(self._build_edit_url(sv), data={'value': ''}))

        sv = self.refresh(sv)
        self.assertEqual('', sv.value_str)
        self.assertIsNone(sv.value)