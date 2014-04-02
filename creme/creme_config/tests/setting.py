# -*- coding: utf-8 -*-

try:
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

    def test_model01(self):
        sk = SettingKey.objects.create(pk='persons-title', description=u"Page title",
                                       app_label=None, type=SettingKey.STRING,
                                       hidden=False,
                                      )
        title = 'May the source be with you'
        sv = SettingValue.objects.create(key=sk, user=None, value=title)

        self.assertEqual(title, self.refresh(sv).value)

    def test_model02(self):
        sk = SettingKey.objects.create(pk='persons-page_size', description=u"Page size",
                                       app_label='persons', type=SettingKey.INT
                                      )
        self.assertFalse(sk.hidden)

        size = 156
        sv = SettingValue.objects.create(key=sk, user=None, value=size)
        self.assertEqual(size, self.refresh(sv).value)

    def test_model03(self):
        self.login()

        sk = SettingKey.objects.create(pk='persons-display_logo',
                                       description=u"Display logo ?",
                                       type=SettingKey.BOOL
                                      )
        sv = SettingValue.objects.create(key=sk, user=self.user, value=True)
        self.assertIs(self.refresh(sv).value, True)

        sv.value = False
        sv.save()
        self.assertIs(self.refresh(sv).value, False)

    def test_edit01(self):
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

    def test_edit02(self):
        self.login()

        sk = SettingKey.objects.create(pk='persons-size', description=u"Page size",
                                       app_label='persons', type=SettingKey.INT,
                                       hidden=False,
                                      )
        size = 156
        sv = SettingValue.objects.create(key=sk, user=None, value=size)

        size += 15
        self.assertNoFormError(self.client.post(self._buil_edit_url(sv), data={'value': size}))
        self.assertEqual(size, self.refresh(sv).value)

    def test_edit03(self):
        self.login()

        sk = SettingKey.objects.create(pk='persons-display_logo',
                                       description=u"Display logo ?",
                                       app_label='persons', type=SettingKey.BOOL,
                                       hidden=False,
                                      )
        sv = SettingValue.objects.create(key=sk, user=None, value=True)

        self.assertNoFormError(self.client.post(self._buil_edit_url(sv), data={})) #False -> empty POST
        self.assertFalse(self.refresh(sv).value)

    def test_edit04(self):
        "Hidden => not editable"
        self.login()

        sk = SettingKey.objects.create(pk='persons-display_logo',
                                       description=u"Display logo ?",
                                       app_label='persons', type=SettingKey.BOOL,
                                       hidden=True,
                                      )
        sv = SettingValue.objects.create(key=sk, user=None, value=True)
        self.assertGET404(self._buil_edit_url(sv))

    def test_edit05(self):
        "Hidden => not editable"
        self.login()

        sk = SettingKey.objects.create(pk='persons-display_logo',
                                       description=u"Display logo ?",
                                       app_label='persons', type=SettingKey.BOOL,
                                       hidden=False,
                                      )
        sv = SettingValue.objects.create(key=sk, user=self.user, value=True)
        self.assertGET404(self._buil_edit_url(sv))
