# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.core.setting_key import SettingKey, setting_key_registry
    from creme.creme_core.models import SettingValue
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('SettingTestCase',)


#TODO: clean registry in teardDown....
class SettingTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config')

    def _buil_edit_url(self, setting_value):
        return '/creme_config/settings/edit/%s' % setting_value.id

    def test_edit_string(self):
        self.login()

        #sk = SettingKey.objects.create(pk='persons-title', description=u"Page title",
                                       #app_label='persons', type=SettingKey.STRING,
                                       #hidden=False,
                                      #)
        sk = SettingKey(id='persons-test_edit_string', description=u"Page title",
                        app_label='persons', type=SettingKey.STRING, hidden=False,
                       )
        setting_key_registry.register(sk)

        title = 'May the source be with you'
        sv = SettingValue.objects.create(key=sk, user=None, value=title)

        url = self._buil_edit_url(sv)
        self.assertGET200(url)

        title = title.upper()
        self.assertNoFormError(self.client.post(url, data={'value': title}))
        self.assertEqual(title, self.refresh(sv).value)

    def test_edit_int(self):
        self.login()

        #sk = SettingKey.objects.create(pk='persons-size', description=u"Page size",
                                       #app_label='persons', type=SettingKey.INT,
                                      #)
        sk = SettingKey(id='persons-test_edit_int', description=u"Page size",
                        app_label='persons', type=SettingKey.INT,
                       )
        setting_key_registry.register(sk)

        size = 156
        sv = SettingValue.objects.create(key=sk, user=None, value=size)

        size += 15
        self.assertNoFormError(self.client.post(self._buil_edit_url(sv), data={'value': size}))
        self.assertEqual(size, self.refresh(sv).value)

    def test_edit_bool(self):
        self.login()

        #sk = SettingKey.objects.create(pk='persons-display_logo',
                                       #description=u"Display logo ?",
                                       #app_label='persons', type=SettingKey.BOOL,
                                      #)
        sk = SettingKey(id='persons-test_edit_bool', description=u"Display logo ?",
                        app_label='persons', type=SettingKey.BOOL,
                       )
        setting_key_registry.register(sk)

        sv = SettingValue.objects.create(key=sk, user=None, value=True)

        self.assertNoFormError(self.client.post(self._buil_edit_url(sv), data={})) #False -> empty POST
        self.assertFalse(self.refresh(sv).value)

    def test_edit_hour(self):
        self.login()

        #sk = SettingKey.objects.create(pk='persons-reminder_hour',
                                       #description='Reminder hour',
                                       #app_label='persons', type=SettingKey.HOUR,
                                      #)
        sk = SettingKey(id='persons-test_edit_hour', description='Reminder hour',
                        app_label='persons', type=SettingKey.HOUR,
                       )
        setting_key_registry.register(sk)

        hour = 11
        sv = SettingValue.objects.create(key=sk, user=None, value=hour)

        url = self._buil_edit_url(sv)
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

    def test_edit_hidden01(self):
        "Hidden => not editable (value=True)"
        self.login()

        #sk = SettingKey.objects.create(pk='persons-display_logo',
                                       #description=u"Display logo ?",
                                       #app_label='persons', type=SettingKey.BOOL,
                                       #hidden=True,
                                      #)
        sk = SettingKey(id='persons-test_edit_hidden01', description=u"Display logo ?",
                        app_label='persons', type=SettingKey.BOOL, hidden=True,
                       )
        setting_key_registry.register(sk)

        sv = SettingValue.objects.create(key=sk, user=None, value=True)
        self.assertGET404(self._buil_edit_url(sv))

    def test_edit_hidden02(self):
        "Hidden => not editable (value=False)"
        self.login()

        #sk = SettingKey.objects.create(pk='persons-display_logo',
                                       #description=u"Display logo ?",
                                       #app_label='persons', type=SettingKey.BOOL,
                                       #hidden=False,
                                      #)
        sk = SettingKey(id='persons-test_edit_hidden02', description=u"Display logo ?",
                        app_label='persons', type=SettingKey.BOOL, hidden=False,
                       )
        setting_key_registry.register(sk)

        sv = SettingValue.objects.create(key=sk, user=self.user, value=True)
        self.assertGET404(self._buil_edit_url(sv))
