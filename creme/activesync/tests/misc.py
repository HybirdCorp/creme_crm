# -*- coding: utf-8 -*-

try:
    from creme_core.tests.base import CremeTestCase

    from creme_config.models import SettingKey, SettingValue

    from activesync.utils import decode_AS_timezone, is_user_sync_calendars, is_user_sync_contacts
    from activesync.constants import USER_MOBILE_SYNC_ACTIVITIES, USER_MOBILE_SYNC_CONTACTS
except Exception as e:
    print 'Error:', e


class MiscTestCase(CremeTestCase):
    def setUp(self):
        pass

    def test_decode_AS_timezone_europe_paris(self):
        #Europe/Paris GMT+1 - GMT+2
        tz = 'xP///0MARQBUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAoAAAAFAAMAAAAAAAAAAAAAAEMARQBTAFQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAAAAFAAIAAAAAAAAAxP///w=='

        decoded = decode_AS_timezone(tz)

        self.assertEqual({'bias': -60,
                          'daylight_bias': -60,
                          'daylight_day': 5,
                          'daylight_day_of_week': 0,
                          'daylight_hour': 2,
                          'daylight_milliseconds': 0,
                          'daylight_minute': 0,
                          'daylight_month': 3,
                          'daylight_name': 'CES',
                          'daylight_second': 0,
                          'daylight_year': 0,
                          'standard_bias': 0,
                          'standard_day': 5,
                          'standard_day_of_week': 0,
                          'standard_hour': 3,
                          'standard_milliseconds': 0,
                          'standard_minute': 0,
                          'standard_month': 10,
                          'standard_name': 'CET',
                          'standard_second': 0,
                          'standard_year': 0,
                         },
                         decoded
                        )

    def test_decode_AS_timezone_tahiti(self):
        #Tahiti GMT -10
        tz = 'WAIAAFQAQQBIAFQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA== '

        decoded = decode_AS_timezone(tz)

        self.assertEqual({'bias': 600,
                          'daylight_bias': 0,
                          'daylight_day': 0,
                          'daylight_day_of_week': 0,
                          'daylight_hour': 0,
                          'daylight_milliseconds': 0,
                          'daylight_minute': 0,
                          'daylight_month': 0,
                          'daylight_name': '\x00\x00\x00',
                          'daylight_second': 0,
                          'daylight_year': 0,
                          'standard_bias': 0,
                          'standard_day': 0,
                          'standard_day_of_week': 0,
                          'standard_hour': 0,
                          'standard_milliseconds': 0,
                          'standard_minute': 0,
                          'standard_month': 0,
                          'standard_name': 'TAH',
                          'standard_second': 0,
                          'standard_year': 0
                         },
                         decoded
                        )


class UserSettingsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_config', 'activesync')
    #def setUp(self):
        #self.populate('creme_config', 'activesync')

    def test_is_user_sync_calendars01(self):
        self.login()
        self.assertEqual(1, SettingKey.objects.filter(pk=USER_MOBILE_SYNC_ACTIVITIES).count())
        self.assertEqual(0, SettingValue.objects.filter(key=USER_MOBILE_SYNC_ACTIVITIES).count())
        self.assertIs(False, is_user_sync_calendars(self.user))

        SettingValue.objects.create(key=SettingKey.objects.get(pk=USER_MOBILE_SYNC_ACTIVITIES), value_str="True", user=self.user)

        self.assertTrue(is_user_sync_calendars(self.user))

    def test_is_user_sync_contacts01(self):
        self.login()
        self.assertEqual(1, SettingKey.objects.filter(pk=USER_MOBILE_SYNC_CONTACTS).count())
        self.assertEqual(0, SettingValue.objects.filter(key=USER_MOBILE_SYNC_CONTACTS).count())
        self.assertIs(False, is_user_sync_contacts(self.user))

        SettingValue.objects.create(key=SettingKey.objects.get(pk=USER_MOBILE_SYNC_CONTACTS), value_str="True", user=self.user)

        self.assertTrue(is_user_sync_contacts(self.user))
