# -*- coding: utf-8 -*-

try:
    from creme_core.tests.base import CremeTestCase

    from creme_config.models import SettingKey, SettingValue
except Exception, e:
    print 'Error:', e


__all__ = ('SettingTestCase',)


class SettingTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config')

    def test_model01(self):
        sk = SettingKey.objects.create(pk='persons-title', description=u"Page title",
                                       app_label=None, type=SettingKey.STRING,
                                       hidden=False,
                                      )
        title = 'May the source be with you'
        sv = SettingValue.objects.create(key=sk, user=None, value=title)

        self.assertEqual(title, SettingValue.objects.get(pk=sv.pk).value)

    def test_model02(self):
        sk = SettingKey.objects.create(pk='persons-page_size', description=u"Page size",
                                       app_label='persons', type=SettingKey.INT
                                      )
        self.assertFalse(sk.hidden)

        size = 156
        sv = SettingValue.objects.create(key=sk, user=None, value=size)
        self.assertEqual(size, SettingValue.objects.get(pk=sv.pk).value)

    def test_model03(self):
        self.login()

        sk = SettingKey.objects.create(pk='persons-display_logo', description=u"Display logo ?",
                                       type=SettingKey.BOOL
                                      )
        sv = SettingValue.objects.create(key=sk, user=self.user, value=True)
        self.assert_(SettingValue.objects.get(pk=sv.pk).value is True)

        sv.value = False
        sv.save()
        self.assert_(SettingValue.objects.get(pk=sv.pk).value is False)

    def test_edit01(self):
        self.login()

        sk = SettingKey.objects.create(pk='persons-title', description=u"Page title",
                                       app_label='persons', type=SettingKey.STRING,
                                       hidden=False,
                                      )
        title = 'May the source be with you'
        sv = SettingValue.objects.create(key=sk, user=None, value=title)

        url = '/creme_config/setting/edit/%s' % sv.id
        self.assertEqual(200, self.client.get(url).status_code)

        title = title.upper()
        response = self.client.post(url, data={'value': title})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        sv = SettingValue.objects.get(pk=sv.pk) #refresh
        self.assertEqual(title, sv.value)

    def test_edit02(self):
        self.login()

        sk = SettingKey.objects.create(pk='persons-size', description=u"Page size",
                                       app_label='persons', type=SettingKey.INT,
                                       hidden=False,
                                      )
        size = 156
        sv = SettingValue.objects.create(key=sk, user=None, value=size)

        size += 15
        response = self.client.post('/creme_config/setting/edit/%s' % sv.id, data={'value': size})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertEqual(size, SettingValue.objects.get(pk=sv.pk).value)

    def test_edit03(self):
        self.login()

        sk = SettingKey.objects.create(pk='persons-display_logo', description=u"Display logo ?",
                                       app_label='persons', type=SettingKey.BOOL,
                                       hidden=False,
                                      )
        sv = SettingValue.objects.create(key=sk, user=None, value=True)

        response = self.client.post('/creme_config/setting/edit/%s' % sv.id, data={}) #False -> empty POST
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertFalse(SettingValue.objects.get(pk=sv.pk).value)

    def test_edit04(self): #hidden => not editable
        self.login()

        sk = SettingKey.objects.create(pk='persons-display_logo', description=u"Display logo ?",
                                       app_label='persons', type=SettingKey.BOOL,
                                       hidden=True,
                                      )
        sv = SettingValue.objects.create(key=sk, user=None, value=True)
        self.assertEqual(404, self.client.get('/creme_config/setting/edit/%s' % sv.id).status_code)

    def test_edit05(self): #hidden => not editable
        self.login()

        sk = SettingKey.objects.create(pk='persons-display_logo', description=u"Display logo ?",
                                       app_label='persons', type=SettingKey.BOOL,
                                       hidden=False,
                                      )
        sv = SettingValue.objects.create(key=sk, user=self.user, value=True)
        self.assertEqual(404, self.client.get('/creme_config/setting/edit/%s' % sv.id).status_code)
