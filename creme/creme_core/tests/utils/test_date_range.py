from datetime import date, datetime, timedelta
from functools import partial

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

    def test_registry__init(self):
        "Register in __init__()."
        prev_range = date_range.PreviousYearRange()
        curr_range = date_range.CurrentYearRange()

        registry = date_range.DateRangeRegistry(prev_range, curr_range)

        self.assertIs(prev_range, registry.get_range(prev_range.name))
        self.assertIs(curr_range, registry.get_range(curr_range.name))
        self.assertIsNone(registry.get_range())

    def test_registry__register(self):
        "register() method."
        prev_range = date_range.PreviousYearRange()
        curr_range = date_range.CurrentYearRange()

        registry = date_range.DateRangeRegistry()
        registry.register(prev_range, curr_range)

        self.assertIs(prev_range, registry.get_range(prev_range.name))
        self.assertIs(curr_range, registry.get_range(curr_range.name))
        self.assertIsNone(registry.get_range())

    def test_registry__dupliactes(self):
        prev_range1 = date_range.PreviousYearRange()
        prev_range2 = date_range.PreviousYearRange()
        curr_range = date_range.CurrentYearRange()

        registry = date_range.DateRangeRegistry()

        with self.assertRaises(registry.RegistrationError):
            registry.register(prev_range1, curr_range, prev_range2)

    def test_choices(self):
        choices = [*self.registry.choices()]
        self.assertEqual(14, len(choices))

        choice0 = choices[0]
        self.assertIsTuple(choice0, length=2)

        PreviousYearRange = date_range.PreviousYearRange
        self.assertEqual(PreviousYearRange.name, choice0[0])
        self.assertIsInstance(choice0[1], PreviousYearRange)

        names = {choice[0] for choice in choices}
        self.assertEqual(14, len(names))
        self.assertIn(date_range.CurrentMonthRange.name, names)
        self.assertNotIn(date_range.EmptyRange.name,     names)
        self.assertNotIn(date_range.NotEmptyRange.name,  names)

    def test_global_registry(self):
        "Global registry."
        choices = [*date_range.date_range_registry.choices()]
        self.assertEqual(14, len(choices))

    def test_future(self):
        drange = self.registry.get_range('in_future')
        self.assertIsInstance(drange, date_range.FutureRange)
        self.assertEqual(_('In the future'), str(drange.verbose_name))

        now_value = now()
        self.assertDictEqual(
            {'birthday__gte': now_value},
            drange.get_q_dict(field='birthday', now=now_value),
        )

        # accept() ---
        future = now_value + timedelta(days=1)
        self.assertTrue(drange.accept(value=future, now=now_value))
        self.assertTrue(drange.accept(value=future.date(), now=now_value))
        self.assertTrue(drange.accept(value=now_value, now=now_value))
        self.assertFalse(
            drange.accept(value=now_value - timedelta(hours=1), now=now_value),
        )
        self.assertFalse(drange.accept(value=None, now=now_value))

    def test_past(self):
        now_value = now()
        drange = self.registry.get_range(name='in_past')
        self.assertIsInstance(drange, date_range.PastRange)
        self.assertDictEqual(
            {'created__lte': now_value},
            drange.get_q_dict(field='created', now=now_value),
        )

        # accept() ---
        past = now_value - timedelta(days=1)
        self.assertTrue(drange.accept(value=past, now=now_value))
        self.assertTrue(drange.accept(value=past.date(), now=now_value))
        self.assertFalse(drange.accept(value=now_value, now=now_value))
        self.assertFalse(
            drange.accept(value=now_value + timedelta(hours=1), now=now_value),
        )
        self.assertFalse(drange.accept(value=None, now=now_value))

    def test_custom_start__date(self):
        start = date(year=2011, month=6, day=1)
        drange = self.registry.get_range(start=start)
        self.assertIsInstance(drange, date_range.CustomRange)
        self.assertDictEqual(
            {
                'created__gte': self.create_datetime(
                    year=2011, month=6, day=1, hour=0, minute=0, second=0,
                ),
            },
            drange.get_q_dict(field='created', now=now()),
        )

        # accept() ---
        accept = partial(drange.accept, now=now())
        dt = self.create_datetime
        self.assertTrue(accept(value=start))
        self.assertTrue(accept(value=date(year=2012, month=12, day=31)))
        self.assertTrue(accept(value=dt(
            year=start.year, month=start.month, day=start.day, hour=8,
        )))

        self.assertFalse(accept(value=start - timedelta(days=1)))
        self.assertFalse(accept(value=dt(year=start.year, month=5, day=31, hour=8)))
        self.assertFalse(accept(value=None))

    def test_custom_start__datetime(self):
        dt = self.create_datetime
        start = dt(year=2011, month=6, day=1, hour=12, minute=36, second=12)
        drange = self.registry.get_range(start=start)
        self.assertIsInstance(drange, date_range.CustomRange)
        self.assertDictEqual(
            {
                'created__gte': dt(
                    year=2011, month=6, day=1, hour=12, minute=36, second=12,
                ),
            },
            drange.get_q_dict(field='created', now=now()),
        )

        # accept() ---
        accept = partial(drange.accept, now=now())
        self.assertTrue(accept(value=start))
        self.assertTrue(accept(value=start + timedelta(weeks=52)))
        self.assertTrue(accept(value=start.date() + timedelta(weeks=52)))

        self.assertFalse(accept(value=start - timedelta(days=1)))
        self.assertFalse(accept(value=start.date() - timedelta(days=1)))
        self.assertFalse(accept(value=None))

    def test_custom_end__date(self):
        end = date(year=2012, month=7, day=15)
        drange = self.registry.get_range(end=end)
        self.assertIsInstance(drange, date_range.CustomRange)
        self.assertDictEqual(
            {
                'modified__lte': self.create_datetime(
                    year=end.year, month=end.month, day=end.day,
                    hour=23, minute=59, second=59,
                ),
            },
            drange.get_q_dict(field='modified', now=now()),
        )

        # accept() ---
        accept = partial(drange.accept, now=now())
        dt = self.create_datetime
        self.assertTrue(accept(value=end))
        self.assertTrue(accept(value=date(year=end.year - 1, month=end.month, day=end.day)))
        self.assertTrue(accept(value=dt(
            year=end.year, month=end.month, day=end.day, hour=8,
        )))

        self.assertFalse(accept(value=end + timedelta(days=1)))
        self.assertFalse(accept(value=dt(year=end.year, month=end.month, day=end.day + 1)))
        self.assertFalse(accept(value=None))

    def test_custom_end__datetime(self):
        dt = self.create_datetime
        end = dt(year=2012, month=7, day=15, hour=10, minute=21, second=50)
        drange = self.registry.get_range(end=end)
        self.assertIsNotNone(drange)
        self.assertDictEqual(
            {'modified__lte': end},
            drange.get_q_dict(field='modified', now=now())
        )

    def test_custom_range(self):
        start = date(year=2011, month=8, day=2)
        end   = date(year=2011, month=8, day=4)
        drange = self.registry.get_range(start=start, end=end)
        self.assertIsNotNone(drange)

        dt = self.create_datetime
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2011, month=8, day=2, hour=0,  minute=0,  second=0),
                    dt(year=2011, month=8, day=4, hour=23, minute=59, second=59),
                ),
            },
            drange.get_q_dict(field='modified', now=now()),
        )

        # accept() ---
        accept = partial(drange.accept, now=now())
        self.assertTrue(accept(value=start))
        self.assertTrue(accept(value=end))
        self.assertTrue(accept(value=date(year=2011, month=8, day=3)))
        self.assertTrue(accept(value=dt(year=2011, month=8, day=3, hour=8)))

        self.assertFalse(accept(value=end + timedelta(days=1)))
        self.assertFalse(accept(value=start - timedelta(days=1)))
        self.assertFalse(accept(value=dt(year=end.year,   month=end.month,   day=end.day + 1)))
        self.assertFalse(accept(value=dt(year=start.year, month=start.month, day=start.day - 1)))
        self.assertFalse(accept(value=None))

    def test_previous_year(self):
        dt = self.create_datetime
        today = dt(year=2011, month=4, day=24)
        drange = self.registry.get_range(name='previous_year')
        self.assertIsInstance(drange, date_range.PreviousYearRange)
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2010, month=1,  day=1,  hour=0,  minute=0,  second=0),
                    dt(year=2010, month=12, day=31, hour=23, minute=59, second=59)
                ),
            },
            drange.get_q_dict(field='modified', now=today),
        )

        # accept() ---
        prev = dt(year=2010, month=6, day=12)
        self.assertTrue(drange.accept(value=prev, now=today))
        self.assertTrue(drange.accept(value=prev.date(), now=today))
        self.assertFalse(drange.accept(value=dt(year=2012, month=6, day=12), now=today))
        self.assertFalse(drange.accept(value=None, now=today))

    def test_current_year(self):
        dt = self.create_datetime
        today = dt(year=2011, month=4, day=24)
        drange = self.registry.get_range(name='current_year')
        self.assertIsInstance(drange, date_range.CurrentYearRange)
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2011, month=1,  day=1,  hour=0,  minute=0,  second=0),
                    dt(year=2011, month=12, day=31, hour=23, minute=59, second=59)
                ),
            },
            drange.get_q_dict(field='modified', now=today),
        )

        # accept() ---
        current = dt(year=2011, month=6, day=12)
        self.assertTrue(drange.accept(value=current, now=today))
        self.assertTrue(drange.accept(value=current.date(), now=today))
        self.assertFalse(drange.accept(value=dt(year=2010, month=6, day=12), now=today))
        self.assertFalse(drange.accept(value=dt(year=2012, month=6, day=12), now=today))
        self.assertFalse(drange.accept(value=None, now=today))

    def test_next_year(self):
        dt = self.create_datetime
        today = dt(year=2011, month=4, day=24)
        drange = self.registry.get_range(name='next_year')
        self.assertIsInstance(drange, date_range.NextYearRange)
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2012, month=1,  day=1,  hour=0,  minute=0,  second=0),
                    dt(year=2012, month=12, day=31, hour=23, minute=59, second=59)
                ),
            },
            drange.get_q_dict(field='modified', now=today),
        )

        # accept() ---
        nexty = dt(year=2012, month=6, day=12)
        self.assertTrue(drange.accept(value=nexty, now=today))
        self.assertTrue(drange.accept(value=nexty.date(), now=today))
        self.assertFalse(drange.accept(value=dt(year=2010, month=6, day=12), now=today))
        self.assertFalse(drange.accept(value=dt(year=2011, month=6, day=12), now=today))
        self.assertFalse(drange.accept(value=None, now=today))

    def test_previous_month01(self):
        now_value = datetime(year=2011, month=4, day=24, hour=12, minute=27, second=59)
        drange = self.registry.get_range(name='previous_month')
        self.assertIsInstance(drange, date_range.PreviousMonthRange)
        self.assertEqual(
            {
                'modified__range': (
                    datetime(year=2011, month=3, day=1,  hour=0,  minute=0,  second=0),
                    datetime(year=2011, month=3, day=31, hour=23, minute=59, second=59)
                ),
            },
            drange.get_q_dict(field='modified', now=now_value),
        )

        # accept() ---
        prev = datetime(year=2011, month=3, day=12)
        accept = partial(drange.accept, now=now_value)
        self.assertTrue(accept(value=prev))
        self.assertTrue(accept(value=prev.date()))
        self.assertFalse(accept(value=datetime(year=2011, month=6, day=12)))
        self.assertFalse(accept(value=datetime(year=2012, month=3, day=12)))
        self.assertFalse(accept(value=None))

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
        drange = self.registry.get_range(name='current_month')
        self.assertIsInstance(drange, date_range.CurrentMonthRange)
        self.assertDictEqual(
            {
                'modified__range': (
                    datetime(year=2011, month=1, day=1,  hour=0,  minute=0,  second=0),
                    datetime(year=2011, month=1, day=31, hour=23, minute=59, second=59),
                ),
            },
            drange.get_q_dict(field='modified', now=today)
        )

        # accept() ---
        current = datetime(year=2011, month=1, day=12)
        accept = partial(drange.accept, now=today)
        self.assertTrue(accept(value=current))
        self.assertTrue(accept(value=current.date()))
        self.assertFalse(accept(value=datetime(year=2011, month=6, day=12)))
        self.assertFalse(accept(value=datetime(year=2012, month=1, day=12)))
        self.assertFalse(accept(value=None))

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
                ),
            },
            self.registry
                .get_range(name='current_month')
                .get_q_dict(field='modified', now=today),
        )

    def test_next_month01(self):
        today = datetime(year=2011, month=10, day=20)
        drange = self.registry.get_range(name='next_month')
        self.assertIsInstance(drange, date_range.NextMonthRange)
        self.assertDictEqual(
            {
                'modified__range': (
                    datetime(year=2011, month=11, day=1,  hour=0,  minute=0,  second=0),
                    datetime(year=2011, month=11, day=30, hour=23, minute=59, second=59),
                ),
            },
            drange.get_q_dict(field='modified', now=today),
        )

        # accept() ---
        nextm = datetime(year=2011, month=11, day=12)
        accept = partial(drange.accept, now=today)
        self.assertTrue(accept(value=nextm))
        self.assertTrue(accept(value=nextm.date()))
        self.assertFalse(accept(value=datetime(year=2011, month=10, day=12)))
        self.assertFalse(accept(value=datetime(year=2012, month=11, day=12)))
        self.assertFalse(accept(value=None))

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
        dt = self.create_datetime
        today = dt(year=2011, month=4, day=24)
        drange = self.registry.get_range(name='previous_quarter')
        self.assertIsInstance(drange, date_range.PreviousQuarterRange)
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2011, month=1, day=1,  hour=0,  minute=0,  second=0),
                    dt(year=2011, month=3, day=31, hour=23, minute=59, second=59)
                ),
            },
            drange.get_q_dict(field='modified', now=today),
        )

        # accept() ---
        prevq = dt(year=2011, month=2, day=12)
        accept = partial(drange.accept, now=today)
        self.assertTrue(accept(value=prevq))
        self.assertTrue(accept(value=prevq.date()))

        self.assertTrue(accept(value=dt(year=2011, month=1, day=1)))
        self.assertTrue(accept(value=dt(year=2011, month=3, day=31)))

        self.assertFalse(accept(value=dt(year=2011, month=4, day=1)))
        self.assertFalse(accept(value=dt(year=2010, month=12, day=31)))
        self.assertFalse(accept(value=None))

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

    def test_current_quarter(self):
        dt = self.create_datetime
        today = dt(year=2011, month=7, day=21)
        drange = self.registry.get_range(name='current_quarter')
        self.assertIsInstance(drange, date_range.CurrentQuarterRange)
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2011, month=7, day=1,  hour=0,  minute=0,  second=0),
                    dt(year=2011, month=9, day=30, hour=23, minute=59, second=59),
                )
            },
            drange.get_q_dict(field='modified', now=today),
        )

        # accept() ---
        currentq = dt(year=2011, month=8, day=12)
        accept = partial(drange.accept, now=today)
        self.assertTrue(accept(value=currentq))
        self.assertTrue(accept(value=currentq.date()))

        self.assertTrue(accept(value=dt(year=2011, month=7, day=1)))
        self.assertTrue(accept(value=dt(year=2011, month=9, day=30)))

        self.assertFalse(accept(value=dt(year=2011, month=6, day=30)))
        self.assertFalse(accept(value=dt(year=2011, month=10, day=1)))
        self.assertFalse(accept(value=None))

    def test_next_quarter01(self):
        dt = self.create_datetime
        today = dt(year=2011, month=4, day=21)
        drange = self.registry.get_range(name='next_quarter')
        self.assertIsInstance(drange, date_range.NextQuarterRange)
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2011, month=7, day=1,  hour=0,  minute=0,  second=0),
                    dt(year=2011, month=9, day=30, hour=23, minute=59, second=59),
                ),
            },
            drange.get_q_dict(field='modified', now=today),
        )

        # accept() ---
        nextq = dt(year=2011, month=8, day=12)
        accept = partial(drange.accept, now=today)
        self.assertTrue(accept(value=nextq))
        self.assertTrue(accept(value=nextq.date()))

        self.assertTrue(accept(value=dt(year=2011, month=7, day=1)))
        self.assertTrue(accept(value=dt(year=2011, month=9, day=30)))

        self.assertFalse(accept(value=dt(year=2011, month=6, day=30)))
        self.assertFalse(accept(value=dt(year=2011, month=10, day=1)))
        self.assertFalse(accept(value=None))

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
        dt = self.create_datetime
        today = dt(year=2011, month=6, day=1, hour=14, minute=14, second=37)
        drange = self.registry.get_range(name='yesterday')
        self.assertIsInstance(drange, date_range.YesterdayRange)
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2011, month=5, day=31, hour=0,  minute=0,  second=0),
                    dt(year=2011, month=5, day=31, hour=23, minute=59, second=59),
                ),
            },
            drange.get_q_dict(field='modified', now=today)
        )

        # accept() ---
        yesterday = today - timedelta(days=1)
        accept = partial(drange.accept, now=today)
        self.assertTrue(accept(value=yesterday))
        self.assertTrue(accept(value=yesterday.date()))

        self.assertFalse(accept(value=today))
        self.assertFalse(accept(value=today + timedelta(days=1)))
        self.assertFalse(accept(value=None))

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
        dt = self.create_datetime
        today = dt(year=2011, month=6, day=1, hour=14, minute=14, second=37)
        drange = self.registry.get_range(name='today')
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2011, month=6, day=1, hour=0,  minute=0,  second=0),
                    dt(year=2011, month=6, day=1, hour=23, minute=59, second=59),
                ),
            },
            drange.get_q_dict(field='modified', now=today),
        )

        # accept() ---
        accept = partial(drange.accept, now=today)
        self.assertTrue(accept(value=today + timedelta(hours=1)))
        self.assertTrue(accept(value=today.date()))

        self.assertFalse(accept(value=today - timedelta(days=1)))
        self.assertFalse(accept(value=today + timedelta(days=1)))
        self.assertFalse(accept(value=None))

    def test_tomorrow01(self):
        dt = self.create_datetime
        today = dt(year=2011, month=6, day=1, hour=14, minute=14, second=37)
        drange = self.registry.get_range(name='tomorrow')
        self.assertIsInstance(drange, date_range.TomorrowRange)
        self.assertDictEqual(
            {
                'modified__range': (
                    dt(year=2011, month=6, day=2, hour=0,  minute=0,  second=0),
                    dt(year=2011, month=6, day=2, hour=23, minute=59, second=59),
                ),
            },
            drange.get_q_dict(field='modified', now=today),
        )

        # accept() ---
        accept = partial(drange.accept, now=today)
        tomorrow = today + timedelta(days=1)
        self.assertTrue(accept(value=tomorrow))
        self.assertTrue(accept(value=tomorrow.date()))

        self.assertFalse(accept(value=today))
        self.assertFalse(accept(value=today - timedelta(days=1)))
        self.assertFalse(accept(value=None))

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
        today = now()
        drange = self.registry.get_range(name='empty')
        self.assertIsInstance(drange, date_range.EmptyRange)
        self.assertDictEqual(
            {'created__isnull': True},
            drange.get_q_dict(field='created', now=today),
        )

        # accept() ---
        self.assertTrue(drange.accept(value=None, now=today))
        self.assertFalse(drange.accept(value=today, now=today))

    def test_not_empty(self):
        today = now()
        drange = self.registry.get_range(name='not_empty')
        self.assertIsInstance(drange, date_range.NotEmptyRange)
        self.assertDictEqual(
            {'created__isnull': False},
            drange.get_q_dict(field='created', now=today),
        )

        # accept() ---
        self.assertTrue(drange.accept(value=today, now=today))
        self.assertFalse(drange.accept(value=None, now=today))
