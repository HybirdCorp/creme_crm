# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _

    from creme.creme_core.tests.base import CremeTestCase

    from ..models import SettingKey, SettingValue
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('SettingTestCase',)


class SettingTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config')

    def _buil_edit_url(self, setting_value):
        return '/creme_config/settings/edit/%s' % setting_value.id

    def test_model_string(self):
        sk = SettingKey.objects.create(pk='persons-title', description=u"Page title",
                                       app_label=None, type=SettingKey.STRING,
                                       hidden=False,
                                      )
        title = 'May the source be with you'
        sv = SettingValue.objects.create(key=sk, user=None, value=title)

        self.assertEqual(title, self.refresh(sv).value)

    def test_model_int(self):
        sk = SettingKey.objects.create(pk='persons-page_size', description=u"Page size",
                                       app_label='persons', type=SettingKey.INT,
                                      )
        self.assertFalse(sk.hidden)

        size = 156
        sv = SettingValue.objects.create(key=sk, user=None, value=size)

        sv = self.refresh(sv)
        self.assertEqual(size, sv.value)
        self.assertEqual(size, sv.as_html)

    def test_model_bool(self):
        self.login()

        sk = SettingKey.objects.create(pk='persons-display_logo',
                                       description=u"Display logo ?",
                                       type=SettingKey.BOOL,
                                      )
        sv = SettingValue.objects.create(key=sk, user=self.user, value=True)

        sv = self.refresh(sv)
        self.assertIs(sv.value, True)
        #self.assertEqual(_('Yes'), sv.as_html)
        self.assertEqual('<input type="checkbox" checked disabled/>%s' % _('Yes'), sv.as_html)

        sv.value = False
        sv.save()

        sv = self.refresh(sv)
        self.assertIs(sv.value, False)
        #self.assertEqual(_('No'), sv.as_html)
        self.assertEqual('<input type="checkbox" disabled/>%s' % _('No'), sv.as_html)

    def test_model_hour(self):
        self.login()

        sk = SettingKey.objects.create(pk='persons-reminder_hour',
                                       description='Reminder hour',
                                       type=SettingKey.HOUR,
                                      )
        hour = 9
        sv = SettingValue.objects.create(key=sk, user=self.user, value=hour)

        sv = self.refresh(sv)
        self.assertEqual(hour, sv.value)
        self.assertEqual(_('%sh') % hour, sv.as_html)

    def test_edit_string(self):
        self.login()

        sk = SettingKey.objects.create(pk='persons-title', description=u"Page title",
                                       app_label='persons', type=SettingKey.STRING,
                                       hidden=False,
                                      )
        title = 'May the source be with you'
        sv = SettingValue.objects.create(key=sk, user=None, value=title)

        url = self._buil_edit_url(sv)
        self.assertGET200(url)

        title = title.upper()
        self.assertNoFormError(self.client.post(url, data={'value': title}))
        self.assertEqual(title, self.refresh(sv).value)

    def test_edit_int(self):
        self.login()

        sk = SettingKey.objects.create(pk='persons-size', description=u"Page size",
                                       app_label='persons', type=SettingKey.INT,
                                      )
        size = 156
        sv = SettingValue.objects.create(key=sk, user=None, value=size)

        size += 15
        self.assertNoFormError(self.client.post(self._buil_edit_url(sv), data={'value': size}))
        self.assertEqual(size, self.refresh(sv).value)

    def test_edit_bool(self):
        self.login()

        sk = SettingKey.objects.create(pk='persons-display_logo',
                                       description=u"Display logo ?",
                                       app_label='persons', type=SettingKey.BOOL,
                                      )
        sv = SettingValue.objects.create(key=sk, user=None, value=True)

        self.assertNoFormError(self.client.post(self._buil_edit_url(sv), data={})) #False -> empty POST
        self.assertFalse(self.refresh(sv).value)

    def test_edit_hour(self):
        self.login()

        sk = SettingKey.objects.create(pk='persons-reminder_hour',
                                       description='Reminder hour',
                                       app_label='persons', type=SettingKey.HOUR,
                                      )
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

        sk = SettingKey.objects.create(pk='persons-display_logo',
                                       description=u"Display logo ?",
                                       app_label='persons', type=SettingKey.BOOL,
                                       hidden=True,
                                      )
        sv = SettingValue.objects.create(key=sk, user=None, value=True)
        self.assertGET404(self._buil_edit_url(sv))

    def test_edit_hidden02(self):
        "Hidden => not editable  (value=False)"
        self.login()

        sk = SettingKey.objects.create(pk='persons-display_logo',
                                       description=u"Display logo ?",
                                       app_label='persons', type=SettingKey.BOOL,
                                       hidden=False,
                                      )
        sv = SettingValue.objects.create(key=sk, user=self.user, value=True)
        self.assertGET404(self._buil_edit_url(sv))

    def test_create_value_if_needed(self):
        self.login()

        sk = SettingKey.objects.create(pk='persons-size', description=u"Page size",
                                       app_label='persons', type=SettingKey.INT,
                                      )

        self.assertFalse(SettingValue.objects.filter(key=sk))

        size = 156
        sv = SettingValue.create_if_needed(key=sk, user=None, value=size)
        self.assertIsInstance(sv, SettingValue)
        self.assertIsNone(sv.user)
        self.assertEqual(size, sv.value)

        with self.assertNoException():
            self.refresh(sv)

        sv = SettingValue.create_if_needed(key=sk, user=None, value=size + 1)
        self.assertEqual(size, sv.value) #not new size
