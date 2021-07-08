# -*- coding: utf-8 -*-

from datetime import date, datetime

from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.utils import date_range


class DateRangeTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.registry = date_range.DateRangeRegistry(
            date_range.PreviousYearRange(),
            date_range.CurrentYearRange(),
            date_range.NextYearRange(),

            date_range.PreviousQuarterRange(),
            date_range.CurrentQuarterRange(),
            date_range.NextQuarterRange(),

            date_range.PreviousMonthRange(),
            date_range.CurrentMonthRange(),
            date_range.NextMonthRange(),

            date_range.YesterdayRange(),
            date_range.TodayRange(),
            date_range.TomorrowRange(),

            date_range.FutureRange(),
            date_range.PastRange(),

            date_range.EmptyRange(),
            date_range.NotEmptyRange(),
        )

    def test_registry01(self):
        "Register in __init__()."
        prev_range = date_range.PreviousYearRange()
        curr_range = date_range.CurrentYearRange()

        registry = date_range.DateRangeRegistry(prev_range, curr_range)

        self.assertIs(prev_range, registry.get_range(prev_range.name))
        self.assertIs(curr_range, registry.get_range(curr_range.name))
        self.assertIsNone(registry.get_range())

    def test_registry02(self):
        "register() method."
        prev_range = date_range.PreviousYearRange()
        curr_range = date_range.CurrentYearRange()

        registry = date_range.DateRangeRegistry()
        registry.register(prev_range, curr_range)

        self.assertIs(prev_range, registry.get_range(prev_range.name))
        self.assertIs(curr_range, registry.get_range(curr_range.name))
        self.assertIsNone(registry.get_range())

    def test_registry03(self):
        "Duplicates."
        prev_range1 = date_range.PreviousYearRange()
        prev_range2 = date_range.PreviousYearRange()
        curr_range = date_range.CurrentYearRange()

        registry = date_range.DateRangeRegistry()

        with self.assertRaises(registry.RegistrationError):
            registry.register(prev_range1, curr_range, prev_range2)

    def test_choices01(self):
        choices = [*self.registry.choices()]
        self.assertEqual(14, len(choices))

        choice0 = choices[0]
        self.assertIsInstance(choice0, tuple)
        self.assertEqual(2, len(choice0))

        PreviousYearRange = date_range.PreviousYearRange
        self.assertEqual(PreviousYearRange.name, choice0[0])
        self.assertIsInstance(choice0[1], PreviousYearRange)

        names = {choice[0] for choice in choices}
        self.assertEqual(14, len(names))
        self.assertIn(date_range.CurrentMonthRange.name, names)
        self.assertNotIn(date_range.EmptyRange.name,     names)
        self.assertNotIn(date_range.NotEmptyRange.name,  names)

    def test_choices02(self):
        "Global registry."
        choices = [*date_range.date_range_registry.choices()]
        self.assertEqual(14, len(choices))

    def test_future(self):
        date_range = self.registry.get_range('in_future')
        self.assertIsNotNone(date_range)
        self.assertEqual(_('In the future'), str(date_range.verbose_name))

        now_value = now()
        self.assertDictEqual(
            {'birthday__gte': now_value},
            date_range.get_q_dict(field='birthday', now=now_value),
        )

    def test_past(self):
        now_value = now()
        date_range = self.registry.get_range(name='in_past')
        self.assertIsNotNone(date_range)
        self.assertDictEqual(
            {'created__lte': now_value},
            date_range.get_q_dict(field='created', now=now_value),
        )

    def test_custom_start01(self):
        now_value = date(year=2011, month=6, day=1)
        date_range = self.registry.get_range(start=now_value)
        self.assertIsNotNone(date_range)
        self.assertDictEqual(
            {
                'created__gte': self.create_datetime(
                    year=2011, month=6, day=1, hour=0, minute=0, second=0,
                ),
            },
            date_range.get_q_dict(field='created', now=now()),
        )

    def test_custom_start02(self):
        dt = self.create_datetime
        now_value = dt(year=2011, month=6, day=1, hour=12, minute=36, second=12)
        date_range = self.registry.get_range(start=now_value)
        self.assertIsNotNone(date_range)
        self.assertDictEqual(
            {
                'created__gte': dt(
                    year=2011, month=6, day=1, hour=12, minute=36, second=12,
                ),
            },
            date_range.get_q_dict(field='created', now=now()),
        )

    def test_custom_end01(self):
        now_value = date(year=2012, month=7, day=15)
        date_range = self.registry.get_range(end=now_value)
        self.assertIsNotNone(date_range)
        self.assertDictEqual(
            {
                'modified__lte': self.create_datetime(
                    year=2012, month=7, day=15, hour=23, minute=59, second=59,
                ),
            },
            date_range.get_q_dict(field='modified', now=now()),
        )

    def test_custom_end02(self):
        dt = self.create_datetime
        now_value = dt(year=2012, month=7, day=15, hour=10, minute=21, second=50)
        date_range = self.registry.get_range(end=now_value)
        self.assertIsNotNone(date_range)
        self.assertDictEqual(
            {
                'modified__lte': dt(
                    year=2012, month=7, day=15, hour=10, minute=21, second=50,
                ),
            },
            date_range.get_q_dict(field='modified', now=now())
        )

    def test_custom_range01(self):
        today    = date(year=2011, month=8, day=2)
        tomorrow = date(year=2011, month=8, day=3)
        date_range = self.registry.get_range(start=today, end=tomorrow)
        self.assertIsNotNone(date_range)

        dt = self.create_datetime
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2011, month=8, day=2, hour=0,  minute=0,  second=0),
                    dt(year=2011, month=8, day=3, hour=23, minute=59, second=59),
                ),
            },
            date_range.get_q_dict(field='modified', now=now()),
        )

    def test_previous_year(self):
        dt = self.create_datetime
        today = dt(year=2011, month=4, day=24)
        date_range = self.registry.get_range(name='previous_year')
        self.assertIsNotNone(date_range)
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2010, month=1,  day=1,  hour=0,  minute=0,  second=0),
                    dt(year=2010, month=12, day=31, hour=23, minute=59, second=59)
                ),
            },
            date_range.get_q_dict(field='modified', now=today),
        )

    def test_current_year(self):
        dt = self.create_datetime
        today = dt(year=2011, month=4, day=24)
        date_range = self.registry.get_range(name='current_year')
        self.assertIsNotNone(date_range)
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2011, month=1,  day=1,  hour=0,  minute=0,  second=0),
                    dt(year=2011, month=12, day=31, hour=23, minute=59, second=59)
                ),
            },
            date_range.get_q_dict(field='modified', now=today),
        )

    def test_next_year(self):
        dt = self.create_datetime
        today = dt(year=2011, month=4, day=24)
        date_range = self.registry.get_range(name='next_year')
        self.assertIsNotNone(date_range)
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2012, month=1,  day=1,  hour=0,  minute=0,  second=0),
                    dt(year=2012, month=12, day=31, hour=23, minute=59, second=59)
                ),
            },
            date_range.get_q_dict(field='modified', now=today),
        )

    def test_previous_month01(self):
        now_value = datetime(year=2011, month=4, day=24, hour=12, minute=27, second=59)
        date_range = self.registry.get_range(name='previous_month')
        self.assertIsNotNone(date_range)
        self.assertEqual(
            {
                'modified__range': (
                    datetime(year=2011, month=3, day=1,  hour=0,  minute=0,  second=0),
                    datetime(year=2011, month=3, day=31, hour=23, minute=59, second=59)
                ),
            },
            date_range.get_q_dict(field='modified', now=now_value),
        )

    def test_previous_month02(self):
        today = datetime(year=2011, month=3, day=12)
        self.assertDictEqual(
            {
                'modified__range': (
                    datetime(year=2011, month=2, day=1,  hour=0,  minute=0,  second=0),
                    datetime(year=2011, month=2, day=28, hour=23, minute=59, second=59),
                ),
            },
            self.registry
                .get_range(name='previous_month')
                .get_q_dict(field='modified', now=today),
        )

    def test_previous_month03(self):
        today = datetime(year=2011, month=1, day=12)
        self.assertDictEqual(
            {
                'modified__range': (
                    datetime(year=2010, month=12, day=1,  hour=0,  minute=0,  second=0),
                    datetime(year=2010, month=12, day=31, hour=23, minute=59, second=59),
                ),
            },
            self.registry
                .get_range(name='previous_month')
                .get_q_dict(field='modified', now=today),
        )

    def test_current_month01(self):
        today = datetime(year=2011, month=1, day=15)
        date_range = self.registry.get_range(name='current_month')
        self.assertIsNotNone(date_range)
        self.assertDictEqual(
            {
                'modified__range': (
                    datetime(year=2011, month=1, day=1,  hour=0,  minute=0,  second=0),
                    datetime(year=2011, month=1, day=31, hour=23, minute=59, second=59),
                ),
            },
            date_range.get_q_dict(field='modified', now=today)
        )

    def test_current_month02(self):
        today = datetime(year=2011, month=2, day=15)
        self.assertDictEqual(
            {
                'modified__range': (
                    datetime(year=2011, month=2, day=1,  hour=0,  minute=0,  second=0),
                    datetime(year=2011, month=2, day=28, hour=23, minute=59, second=59),  # <--28
                ),
            },
            self.registry
                .get_range(name='current_month')
                .get_q_dict(field='modified', now=today),
        )

    def test_current_month03(self):
        today = datetime(year=2012, month=2, day=15)
        self.assertDictEqual(
            {
                'modified__range': (
                    datetime(year=2012, month=2, day=1,  hour=0,  minute=0,  second=0),
                    datetime(year=2012, month=2, day=29, hour=23, minute=59, second=59),  # <--29
                )
            },
            self.registry
                .get_range(name='current_month')
                .get_q_dict(field='modified', now=today),
        )

    def test_next_month01(self):
        today = datetime(year=2011, month=10, day=20)
        date_range = self.registry.get_range(name='next_month')
        self.assertIsNotNone(date_range)
        self.assertDictEqual(
            {
                'modified__range': (
                    datetime(year=2011, month=11, day=1,  hour=0,  minute=0,  second=0),
                    datetime(year=2011, month=11, day=30, hour=23, minute=59, second=59),
                )
            },
            date_range.get_q_dict(field='modified', now=today),
        )

    def test_next_month02(self):
        today = datetime(year=2011, month=11, day=21)
        self.assertDictEqual(
            {
                'modified__range': (
                    datetime(year=2011, month=12, day=1,  hour=0,  minute=0,  second=0),
                    datetime(year=2011, month=12, day=31, hour=23, minute=59, second=59),
                )
            },
            self.registry
                .get_range(name='next_month')
                .get_q_dict(field='modified', now=today),
        )

    def test_next_month03(self):
        today = datetime(year=2011, month=12, day=23)
        self.assertDictEqual(
            {
                'modified__range': (
                    datetime(year=2012, month=1, day=1,  hour=0,  minute=0,  second=0),
                    datetime(year=2012, month=1, day=31, hour=23, minute=59, second=59),
                ),
            },
            self.registry
                .get_range(name='next_month')
                .get_q_dict(field='modified', now=today),
        )

    def test_previous_quarter01(self):
        today = datetime(year=2011, month=4, day=24)
        date_range = self.registry.get_range(name='previous_quarter')
        self.assertIsNotNone(date_range)

        dt = self.create_datetime
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2011, month=1, day=1,  hour=0,  minute=0,  second=0),
                    dt(year=2011, month=3, day=31, hour=23, minute=59, second=59)
                ),
            },
            date_range.get_q_dict(field='modified', now=today),
        )

    def test_previous_quarter02(self):
        today = datetime(year=2011, month=6, day=12)
        dt = self.create_datetime
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2011, month=1, day=1,  hour=0,  minute=0,  second=0),
                    dt(year=2011, month=3, day=31, hour=23, minute=59, second=59),
                )
            },
            self.registry
                .get_range(name='previous_quarter')
                .get_q_dict(field='modified', now=today),
        )

    def test_previous_quarter03(self):
        today = datetime(year=2011, month=2, day=8)
        dt = self.create_datetime
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2010, month=10, day=1,  hour=0,  minute=0,  second=0),
                    dt(year=2010, month=12, day=31, hour=23, minute=59, second=59),
                )
            },
            self.registry
                .get_range(name='previous_quarter')
                .get_q_dict(field='modified', now=today),
        )

    def test_current_quarter01(self):
        today = datetime(year=2011, month=7, day=21)
        date_range = self.registry.get_range(name='current_quarter')
        self.assertIsNotNone(date_range)

        dt = self.create_datetime
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2011, month=7, day=1,  hour=0,  minute=0,  second=0),
                    dt(year=2011, month=9, day=30, hour=23, minute=59, second=59),
                )
            },
            date_range.get_q_dict(field='modified', now=today),
        )

    def test_next_quarter01(self):
        today = datetime(year=2011, month=4, day=21)
        date_range = self.registry.get_range(name='next_quarter')
        self.assertIsNotNone(date_range)

        dt = self.create_datetime
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2011, month=7, day=1,  hour=0,  minute=0,  second=0),
                    dt(year=2011, month=9, day=30, hour=23, minute=59, second=59),
                ),
            },
            date_range.get_q_dict(field='modified', now=today),
        )

    def test_next_quarter02(self):
        today = datetime(year=2011, month=12, day=3)
        dt = self.create_datetime
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2012, month=1, day=1,  hour=0,  minute=0,  second=0),
                    dt(year=2012, month=3, day=31, hour=23, minute=59, second=59),
                ),
            },
            self.registry
                .get_range(name='next_quarter')
                .get_q_dict(field='modified', now=today),
        )

    def test_yesterday01(self):
        today = datetime(year=2011, month=6, day=1, hour=14, minute=14, second=37)
        self.assertDictEqual(
            {
                'modified__range': (
                    datetime(year=2011, month=5, day=31, hour=0,  minute=0,  second=0),
                    datetime(year=2011, month=5, day=31, hour=23, minute=59, second=59),
                ),
            },
            self.registry
                .get_range(name='yesterday')
                .get_q_dict(field='modified', now=today)
        )

    def test_yesterday02(self):
        today = datetime(year=2011, month=6, day=2, hour=14, minute=14, second=37)
        self.assertDictEqual(
            {
                'modified__range': (
                    datetime(year=2011, month=6, day=1, hour=0,  minute=0,  second=0),
                    datetime(year=2011, month=6, day=1, hour=23, minute=59, second=59),
                ),
            },
            self.registry
                .get_range(name='yesterday')
                .get_q_dict(field='modified', now=today),
        )

    def test_today(self):
        today = datetime(year=2011, month=6, day=1, hour=14, minute=14, second=37)
        self.assertDictEqual(
            {
                'modified__range': (
                    datetime(year=2011, month=6, day=1, hour=0,  minute=0,  second=0),
                    datetime(year=2011, month=6, day=1, hour=23, minute=59, second=59),
                ),
            },
            self.registry
                .get_range(name='today')
                .get_q_dict(field='modified', now=today),
        )

    def test_tomorrow01(self):
        today = datetime(year=2011, month=6, day=1, hour=14, minute=14, second=37)
        self.assertDictEqual(
            {
                'modified__range': (
                    datetime(year=2011, month=6, day=2, hour=0,  minute=0,  second=0),
                    datetime(year=2011, month=6, day=2, hour=23, minute=59, second=59),
                ),
            },
            self.registry
                .get_range(name='tomorrow')
                .get_q_dict(field='modified', now=today),
        )

    def test_tomorrow02(self):
        today = datetime(year=2011, month=6, day=30, hour=14, minute=14, second=37)
        self.assertDictEqual(
            {
                'modified__range': (
                    datetime(year=2011, month=7, day=1, hour=0,  minute=0,  second=0),
                    datetime(year=2011, month=7, day=1, hour=23, minute=59, second=59),
                ),
            },
            self.registry
                .get_range(name='tomorrow')
                .get_q_dict(field='modified', now=today),
        )

    def test_empty(self):
        date_range = self.registry.get_range(name='empty')
        self.assertIsNotNone(date_range)
        self.assertDictEqual(
            {'created__isnull': True},
            date_range.get_q_dict(field='created', now=now()),
        )

    def test_not_empty(self):
        date_range = self.registry.get_range(name='not_empty')
        self.assertIsNotNone(date_range)
        self.assertDictEqual(
            {'created__isnull': False},
            date_range.get_q_dict(field='created', now=now()),
        )
