# -*- coding: utf-8 -*-

try:
    from creme_core.tests.base import CremeTestCase

    from creme_config.models import SettingValue, SettingKey

    from activesync.constants import *
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class UserSettingsTestCase(CremeTestCase):
    def setUp(self): #setUpClass ??
        self.populate('creme_config', 'activesync')

    def test_user_settings01(self):
        self.login()

        url = '/activesync/user_settings'
        self.assertGET200(url)

        as_sk = [USER_MOBILE_SYNC_SERVER_URL, USER_MOBILE_SYNC_SERVER_DOMAIN, USER_MOBILE_SYNC_SERVER_SSL,
                 USER_MOBILE_SYNC_SERVER_LOGIN, USER_MOBILE_SYNC_SERVER_PWD, USER_MOBILE_SYNC_ACTIVITIES,
                 USER_MOBILE_SYNC_CONTACTS
                ]

        self.assertEqual(len(as_sk), SettingKey.objects.filter(pk__in=as_sk).count())
        self.assertEqual(0, SettingValue.objects.filter(key__in=as_sk).count())

        response = self.client.post(url, data={'user':           self.user,
                                               'url':            'http://cremecrm.com/as',
                                               'domain':         'creme',
                                               'ssl':            '1',
                                               'login':          'fulbert',
                                               'password':       'fulbert_pwd',
                                               'sync_calendars': '0',
                                               'sync_contacts':  '0',
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(len(as_sk), SettingValue.objects.filter(key__in=as_sk).count())

        self.assertEqual('http://cremecrm.com/as', SettingValue.objects.get(key=USER_MOBILE_SYNC_SERVER_URL).value)
        self.assertEqual('creme', SettingValue.objects.get(key=USER_MOBILE_SYNC_SERVER_DOMAIN).value)
        self.assertTrue(SettingValue.objects.get(key=USER_MOBILE_SYNC_SERVER_SSL).value)
        self.assertEqual('fulbert', SettingValue.objects.get(key=USER_MOBILE_SYNC_SERVER_LOGIN).value)
        self.assertFalse(SettingValue.objects.get(key=USER_MOBILE_SYNC_ACTIVITIES).value)
        self.assertFalse(SettingValue.objects.get(key=USER_MOBILE_SYNC_CONTACTS).value)
