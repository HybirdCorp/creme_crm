# -*- coding: utf-8 -*-

from datetime import date, datetime, time, timezone
from decimal import Decimal

from django.utils.translation import gettext, gettext_lazy
from pytz import timezone as get_timezone

from creme.creme_core.utils.serializers import json_encode

from ..base import CremeTestCase


class SerializerTestCase(CremeTestCase):
    def test_encode_decimal(self):
        self.assertEqual('12.47', json_encode(Decimal('12.47')))
        self.assertEqual('5.0', json_encode(Decimal('5')))

    def test_encode_date(self):
        self.assertEqual(
            '"2018-01-12"', json_encode(date(2018, 1, 12))
        )

    def test_encode_time__use_utc(self):
        self.assertEqual(
            '"08:12:25.012"', json_encode(time(8, 12, 25, 12345))
        )

        self.assertEqual(
            '"08:12:25.012Z"',
            json_encode(time(8, 12, 25, 12345, tzinfo=timezone.utc))
        )

        # "normalize" pytz timezone information to get "05:00" and not "04:56"
        # see https://stackoverflow.com/questions/26264897/time-zone-field-in-isoformat
        tzinfo = get_timezone('US/Eastern').localize(
            datetime(2018, 1, 12, 8, 12, 25, 12345),
        ).tzinfo

        self.assertEqual(
            '"13:12:25.012Z"',
            json_encode(time(8, 12, 25, 12345, tzinfo=tzinfo))
        )

        # "normalize" pytz timezone information to get "08:00" and not "08:06"
        # see https://stackoverflow.com/questions/26264897/time-zone-field-in-isoformat
        tzinfo = get_timezone('Asia/Shanghai').localize(
            datetime(2018, 1, 12, 8, 12, 25, 12345),
        ).tzinfo

        self.assertEqual(
            '"00:12:25.012Z"',
            json_encode(time(8, 12, 25, 12345, tzinfo=tzinfo))
        )

    def test_encode_time(self):
        self.assertEqual(
            '"08:12:25.012"',
            json_encode(time(8, 12, 25, 12345), use_utc=False)
        )

        self.assertEqual(
            '"08:12:25.012Z"',
            json_encode(time(8, 12, 25, 12345, tzinfo=timezone.utc), use_utc=False)
        )

        # "normalize" pytz timezone information to get "05:00" and not "04:56"
        # see https://stackoverflow.com/questions/26264897/time-zone-field-in-isoformat
        tzinfo = get_timezone('US/Eastern').localize(
            datetime(2018, 1, 12, 8, 12, 25, 12345),
        ).tzinfo

        self.assertEqual(
            '"08:12:25.012-05:00"',
            json_encode(time(8, 12, 25, 12345, tzinfo=tzinfo), use_utc=False)
        )

        # "normalize" pytz timezone information to get "08:00" and not "08:06"
        # see https://stackoverflow.com/questions/26264897/time-zone-field-in-isoformat
        tzinfo = get_timezone('Asia/Shanghai').localize(
            datetime(2018, 1, 12, 8, 12, 25, 12345),
        ).tzinfo

        self.assertEqual(
            '"08:12:25.012+08:00"',
            json_encode(time(8, 12, 25, 12345, tzinfo=tzinfo), use_utc=False)
        )

    def test_encode_datetime__use_utc(self):
        self.assertEqual(
            '"2018-01-12T08:12:25.012"',
            json_encode(datetime(2018, 1, 12, 8, 12, 25, 12345))
        )

        self.assertEqual(
            '"2018-01-12T08:12:25.012Z"',
            json_encode(datetime(2018, 1, 12, 8, 12, 25, 12345, tzinfo=timezone.utc))
        )

        self.assertEqual(
            '"2018-01-12T13:12:25.012Z"',
            json_encode(get_timezone('US/Eastern').localize(
                datetime(2018, 1, 12, 8, 12, 25, 12345))
            ),
        )

        self.assertEqual(
            '"2018-01-12T00:12:25.012Z"',
            json_encode(get_timezone('Asia/Shanghai').localize(
                datetime(2018, 1, 12, 8, 12, 25, 12345))
            ),
        )

    def test_encode_datetime(self):
        self.assertEqual(
            '"2018-01-12T08:12:25.012"',
            json_encode(datetime(2018, 1, 12, 8, 12, 25, 12345), use_utc=False),
        )

        self.assertEqual(
            '"2018-01-12T08:12:25.012Z"',
            json_encode(
                datetime(2018, 1, 12, 8, 12, 25, 12345, tzinfo=timezone.utc),
                use_utc=False,
            ),
        )

        self.assertEqual(
            '"2018-01-12T08:12:25.012-05:00"',
            json_encode(
                get_timezone('US/Eastern').localize(
                    datetime(2018, 1, 12, 8, 12, 25, 12345)
                ),
                use_utc=False,
            ),
        )

        self.assertEqual(
            '"2018-01-12T08:12:25.012+08:00"',
            json_encode(
                get_timezone('Asia/Shanghai').localize(
                    datetime(2018, 1, 12, 8, 12, 25, 12345)
                ),
                use_utc=False,
            ),
        )

    def test_encode_lazy(self):
        self.assertEqual(
            '"{}"'.format(gettext('User')),
            json_encode(gettext_lazy('User')),
        )

    def test_encode_generator(self):
        self.assertEqual('[0,1,2]', json_encode(x for x in range(3)))
        self.assertEqual('[2,4,6]', json_encode(x * 2 for x in [1, 2, 3]))

    def test_encode_none(self):
        self.assertEqual('null', json_encode(None))
        # TODO: uncomment when order is guaranteed (Python 3.8?)
        # self.assertEqual('{"a":null,"b":12}', json_encode({'a': None, 'b': 12}))
        self.assertEqual('{"a":null}', json_encode({'a': None}))
