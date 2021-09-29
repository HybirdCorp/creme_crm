# -*- coding: utf-8 -*-

from dateutil.rrule import (
    DAILY,
    HOURLY,
    MINUTELY,
    MONTHLY,
    WEEKLY,
    YEARLY,
    rrule,
)
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core.utils.date_period import (
    DatePeriodRegistry,
    DaysPeriod,
    HoursPeriod,
    MinutesPeriod,
    MonthsPeriod,
    WeeksPeriod,
    YearsPeriod,
    date_period_registry,
)

from ..base import CremeTestCase


class DatePeriodTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.registry = DatePeriodRegistry(
            MinutesPeriod,
            HoursPeriod,
            DaysPeriod,
            WeeksPeriod,
            MonthsPeriod,
            YearsPeriod,
        )

    @staticmethod
    def _get_comparable_data(rrule):
        rrule__dict__ = rrule.__dict__
        rrule__dict__.pop('_bysecond')
        rrule__dict__.pop('_dtstart')
        rrule__dict__.pop('_timeset')
        return rrule__dict__

    def assertRRuleEqual(self, rrule1, rrule2):
        self.assertEqual(
            self._get_comparable_data(rrule1),
            self._get_comparable_data(rrule2),
        )

    def test_registry01(self):
        "Register in __init__()."
        registry = DatePeriodRegistry(MinutesPeriod, HoursPeriod)

        period1 = registry.get_period(MinutesPeriod.name, 1)
        self.assertIsInstance(period1, MinutesPeriod)

        period2 = registry.get_period(HoursPeriod.name, 1)
        self.assertIsInstance(period2, HoursPeriod)

        self.assertIsNone(registry.get_period('invalid', 1))

    def test_registry02(self):
        "register() method."
        registry = DatePeriodRegistry()
        registry.register(DaysPeriod, WeeksPeriod)

        period = registry.get_period(DaysPeriod.name, 1)
        self.assertIsInstance(period, DaysPeriod)

        self.assertIsNone(registry.get_period(MinutesPeriod.name, 1))

    def test_registry03(self):
        "Duplicates."
        registry = DatePeriodRegistry()

        with self.assertRaises(registry.RegistrationError):
            registry.register(DaysPeriod, WeeksPeriod, DaysPeriod)

    def test_hours(self):
        get = self.registry.get_period
        every_hour = get('hours', 1)
        rrule_every_hour = rrule(HOURLY, interval=1)
        self.assertIsNotNone(every_hour)
        self.assertEqual(_('Hour(s)'), str(every_hour.verbose_name))
        self.assertEqual(
            ngettext('{number} hour', '{number} hours', 1).format(number=1),
            str(every_hour),
        )
        self.assertDictEqual(
            {'type': 'hours', 'value': 1}, every_hour.as_dict(),
        )
        self.assertRRuleEqual(rrule_every_hour, every_hour.as_rrule())

        create_dt = self.create_datetime
        now_value = create_dt(year=2014, month=6, day=26, hour=22, minute=38)
        self.assertEqual(
            create_dt(year=2014, month=6, day=26, hour=23, minute=38),
            now_value + every_hour.as_timedelta(),
        )

        every_3hours = get('hours', 3)
        rrule_every_3hours = rrule(HOURLY, interval=3)
        self.assertDictEqual(
            {'type': 'hours', 'value': 3}, every_3hours.as_dict(),
        )
        self.assertEqual(
            create_dt(year=2014, month=6, day=27, hour=1, minute=38),
            now_value + every_3hours.as_timedelta(),
        )
        self.assertEqual(
            ngettext('{number} hour', '{number} hours', 3).format(number=3),
            str(every_3hours),
        )
        self.assertRRuleEqual(rrule_every_3hours, every_3hours.as_rrule())

    def test_minutes(self):
        get = self.registry.get_period
        every_3minutes = get('minutes', 3)
        rrule_every_3minutes = rrule(MINUTELY, interval=3)
        self.assertIsNotNone(every_3minutes)
        self.assertDictEqual(
            {'type': 'minutes', 'value': 3}, every_3minutes.as_dict(),
        )
        self.assertEqual(
            ngettext('{number} minute', '{number} minutes', 3).format(number=3),
            str(every_3minutes),
        )

        create_dt = self.create_datetime
        self.assertEqual(
            create_dt(year=2014, month=6, day=27, hour=18, minute=25),
            create_dt(year=2014, month=6, day=27, hour=18, minute=22)
            + every_3minutes.as_timedelta(),
        )
        self.assertRRuleEqual(rrule_every_3minutes, every_3minutes.as_rrule())

    def test_days(self):
        get = self.registry.get_period
        every_day = get('days', 1)
        rrule_every_day = rrule(DAILY, interval=1)
        self.assertIsNotNone(every_day)
        self.assertDictEqual({'type': 'days', 'value': 1}, every_day.as_dict())
        self.assertEqual(
            ngettext('{number} day', '{number} days', 1).format(number=1),
            str(every_day),
        )

        create_dt = self.create_datetime
        now_value = create_dt(year=2014, month=6, day=27, hour=18, minute=22)
        self.assertEqual(
            create_dt(year=2014, month=6, day=28, hour=18, minute=22),
            now_value + every_day.as_timedelta(),
        )
        self.assertRRuleEqual(rrule_every_day, every_day.as_rrule())

        every_5days = get('days', 5)
        rrule_every_5days = rrule(DAILY, interval=5)
        self.assertEqual(
            create_dt(year=2014, month=7, day=2, hour=18, minute=22),
            now_value + every_5days.as_timedelta(),
        )
        self.assertEqual(
            ngettext('{number} day', '{number} days', 5).format(number=5),
            str(every_5days),
        )
        self.assertRRuleEqual(rrule_every_5days, every_5days.as_rrule())

    def test_years(self):
        get = self.registry.get_period
        every_year = get('years', 1)
        rrule_every_year = rrule(YEARLY, interval=1)
        self.assertIsNotNone(every_year)
        self.assertDictEqual({'type': 'years', 'value': 1}, every_year.as_dict())
        self.assertEqual(
            ngettext('{number} year', '{number} years', 1).format(number=1),
            str(every_year),
        )
        self.assertRRuleEqual(rrule_every_year, every_year.as_rrule())

        create_dt = self.create_datetime
        self.assertEqual(
            create_dt(year=2015, month=6, day=27, hour=18, minute=22),
            create_dt(year=2014, month=6, day=27, hour=18, minute=22)
            + every_year.as_timedelta(),
        )

        # Beware with leap years (as 2000)
        self.assertEqual(
            create_dt(year=2002, month=1, day=1, hour=14, minute=23),
            create_dt(year=2000, month=1, day=1, hour=14, minute=23)
            + get('years', 2).as_timedelta(),
        )

        # 29 february
        every_3years = get('years', 3)
        rrule_every_3years = rrule(YEARLY, interval=3)
        self.assertEqual(
            create_dt(year=2003, month=2, day=28, hour=14, minute=23),
            create_dt(year=2000, month=2, day=29, hour=14, minute=23)
            + every_3years.as_timedelta(),
        )
        self.assertRRuleEqual(rrule_every_3years, every_3years.as_rrule())

    def test_months(self):
        get = self.registry.get_period
        every_month = get('months', 1)
        rrule_every_month = rrule(MONTHLY, interval=1)
        self.assertIsNotNone(every_month)
        self.assertDictEqual({'type': 'months', 'value': 1}, every_month.as_dict())
        self.assertEqual(
            ngettext('{number} month', '{number} months', 1).format(number=1),
            str(every_month),
        )

        create_dt = self.create_datetime
        now_value = create_dt(year=2014, month=6, day=27, hour=18, minute=22)
        self.assertEqual(
            create_dt(year=2014, month=7, day=27, hour=18, minute=22),
            now_value + every_month.as_timedelta(),
        )
        self.assertRRuleEqual(rrule_every_month, every_month.as_rrule())

        # TODO
        # #self.assertEqual(create_dt(year=2014, month=10, day=27, hour=18, minute=22),
        # self.assertEqual(create_dt(year=2014, month=10, day=27, hour=17, minute=22),
        #                  now_value + get('months', 4).as_timedelta()
        #                 )

    def test_weeks(self):
        get = self.registry.get_period
        every_week = get('weeks', 1)
        rrule_every_week = rrule(WEEKLY, interval=1)
        self.assertIsNotNone(every_week)
        self.assertDictEqual({'type': 'weeks', 'value': 1}, every_week.as_dict())
        self.assertEqual(
            ngettext('{number} week', '{number} weeks', 1).format(number=1),
            str(every_week),
        )

        create_dt = self.create_datetime
        self.assertEqual(
            create_dt(year=2014, month=7, day=4, hour=18, minute=22),
            create_dt(year=2014, month=6, day=27, hour=18, minute=22)
            + every_week.as_timedelta(),
        )
        self.assertRRuleEqual(rrule_every_week, every_week.as_rrule())

    def test_deserialize(self):
        get = self.registry.deserialize
        period = get({'type': 'months', 'value': 2})
        self.assertIsInstance(period, MonthsPeriod)

        create_dt = self.create_datetime
        now_value = create_dt(year=2014, month=7, day=2, hour=17, minute=31)
        self.assertEqual(
            create_dt(year=2014, month=9, day=2, hour=17, minute=31),
            now_value + period.as_timedelta(),
        )
        self.assertEqual(
            create_dt(year=2014, month=7, day=5, hour=17, minute=31),
            now_value + get({'type': 'days', 'value': 3}).as_timedelta(),
        )

    def test_choices01(self):
        choices = [*self.registry.choices()]
        self.assertEqual(len(choices), 6)
        self.assertEqual(('minutes', _('Minute(s)')), choices[0])

    def test_choices02(self):
        "Global registry."
        choices = [*date_period_registry.choices()]
        self.assertEqual(len(choices), 6)

    def test_eq(self):
        self.assertNotEqual(MinutesPeriod(value=1), HoursPeriod(value=2))
        self.assertEqual(MinutesPeriod(value=1), MinutesPeriod(value=1))
        self.assertEqual(MinutesPeriod(value=60), HoursPeriod(value=1))

        self.assertNotEqual(MinutesPeriod(value=60), None)

        with self.assertNoException():
            r = bool(MinutesPeriod(value=60) == 'whatever')
        self.assertFalse(r)

        with self.assertNoException():
            r = bool(MinutesPeriod(value=60) != HoursPeriod(value=1))
        self.assertFalse(r)

        with self.assertNoException():
            r = bool('foo' == MinutesPeriod(value=1))
        self.assertFalse(r)
