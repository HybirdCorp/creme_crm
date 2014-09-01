# -*- coding: utf-8 -*-

try:
    from creme.creme_core.tests.base import CremeTestCase

    from ..utils import decode_AS_timezone
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


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
