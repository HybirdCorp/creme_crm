# -*- coding: utf-8 -*-

try:
    from datetime import datetime, date
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _

    from creme.creme_core.utils.date_range import date_range_registry
    from creme.creme_core.tests.base import CremeTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('DateRangeTestCase',)


class DateRangeTestCase(CremeTestCase):
    def test_future(self):
        date_range = date_range_registry.get_range('in_future')
        self.assertIsNotNone(date_range)
        self.assertEqual(_(u"In the future"), unicode(date_range.verbose_name))

        now_value = now()
        self.assertEqual({'birthday__gte': now_value},
                         date_range.get_q_dict(field='birthday', now=now_value)
                        )

    def test_past(self):
        now_value = now()
        date_range = date_range_registry.get_range(name='in_past')
        self.assertIsNotNone(date_range)
        self.assertEqual({'created__lte': now_value},
                         date_range.get_q_dict(field='created', now=now_value)
                        )

    def test_custom_start01(self):
        now_value = date(year=2011, month=6, day=1)
        date_range = date_range_registry.get_range(start=now_value)
        self.assertIsNotNone(date_range)
        self.assertEqual({'created__gte': datetime(year=2011, month=6, day=1, hour=0, minute=0, second=0)},
                         date_range.get_q_dict(field='created', now=now())
                        )

    def test_custom_start02(self):
        now_value = datetime(year=2011, month=6, day=1, hour=12, minute=36, second=12)
        date_range = date_range_registry.get_range(start=now_value)
        self.assertIsNotNone(date_range)
        self.assertEqual({'created__gte': datetime(year=2011, month=6, day=1, hour=12, minute=36, second=12)},
                         date_range.get_q_dict(field='created', now=now())
                        )

    def test_custom_end01(self):
        now_value = date(year=2012, month=7, day=15)
        date_range = date_range_registry.get_range(end=now_value)
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__lte': datetime(year=2012, month=7, day=15, hour=23, minute=59, second=59)},
                         date_range.get_q_dict(field='modified', now=now())
                        )

    def test_custom_end02(self):
        now_value = datetime(year=2012, month=7, day=15, hour=10, minute=21, second=50)
        date_range = date_range_registry.get_range(end=now_value)
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__lte': datetime(year=2012, month=7, day=15, hour=10, minute=21, second=50)},
                         date_range.get_q_dict(field='modified', now=now())
                        )

    def test_custom_range01(self):
        today    = date(year=2011, month=8, day=2)
        tomorrow = date(year=2011, month=8, day=3)
        date_range = date_range_registry.get_range(start=today, end=tomorrow)
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2011, month=8, day=2, hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=8, day=3, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=now())
                        )

    def test_previous_year(self):
        today = datetime(year=2011, month=4, day=24)
        date_range = date_range_registry.get_range(name='previous_year')
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2010, month=1,  day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2010, month=12, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=today)
                        )

    def test_current_year(self):
        today = datetime(year=2011, month=4, day=24)
        date_range = date_range_registry.get_range(name='current_year')
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2011, month=1,  day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=12, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=today)
                        )

    def test_next_year(self):
        today = datetime(year=2011, month=4, day=24)
        date_range = date_range_registry.get_range(name='next_year')
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2012, month=1,  day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2012, month=12, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=today)
                        )

    def test_previous_month01(self):
        today = datetime(year=2011, month=4, day=24)
        date_range = date_range_registry.get_range(name='previous_month')
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2011, month=3, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=3, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=today)
                        )

    def test_previous_month02(self):
        today = datetime(year=2011, month=3, day=12)
        self.assertEqual({'modified__range': (datetime(year=2011, month=2, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=2, day=28, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='previous_month')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_previous_month03(self):
        today = datetime(year=2011, month=1, day=12)
        self.assertEqual({'modified__range': (datetime(year=2010, month=12, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2010, month=12, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='previous_month')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_current_month01(self):
        today = datetime(year=2011, month=1, day=15)
        date_range = date_range_registry.get_range(name='current_month')
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2011, month=1, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=1, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=today)
                        )

    def test_current_month02(self):
        today = datetime(year=2011, month=2, day=15)
        self.assertEqual({'modified__range': (datetime(year=2011, month=2, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=2, day=28, hour=23, minute=59, second=59) #<--28
                                             )
                         },
                         date_range_registry.get_range(name='current_month')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_current_month03(self):
        today = datetime(year=2012, month=2, day=15)
        self.assertEqual({'modified__range': (datetime(year=2012, month=2, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2012, month=2, day=29, hour=23, minute=59, second=59) #<--29
                                             )
                         },
                         date_range_registry.get_range(name='current_month')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_next_month01(self):
        today = datetime(year=2011, month=10, day=20)
        date_range = date_range_registry.get_range(name='next_month')
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2011, month=11, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=11, day=30, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=today)
                        )

    def test_next_month02(self):
        today = datetime(year=2011, month=11, day=21)
        self.assertEqual({'modified__range': (datetime(year=2011, month=12, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=12, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='next_month')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_next_month03(self):
        today = datetime(year=2011, month=12, day=23)
        self.assertEqual({'modified__range': (datetime(year=2012, month=1, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2012, month=1, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='next_month')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_previous_quarter01(self):
        today = datetime(year=2011, month=4, day=24)
        date_range = date_range_registry.get_range(name='previous_quarter')
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2011, month=1, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=3, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=today)
                        )

    def test_previous_quarter02(self):
        today = datetime(year=2011, month=6, day=12)
        self.assertEqual({'modified__range': (datetime(year=2011, month=1, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=3, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='previous_quarter')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_previous_quarter03(self):
        today = datetime(year=2011, month=2, day=8)
        self.assertEqual({'modified__range': (datetime(year=2010, month=10, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2010, month=12, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='previous_quarter')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_current_quarter01(self):
        today = datetime(year=2011, month=7, day=21)
        date_range = date_range_registry.get_range(name='current_quarter')
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2011, month=7, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=9, day=30, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=today)
                        )

    def test_next_quarter01(self):
        today = datetime(year=2011, month=4, day=21)
        date_range = date_range_registry.get_range(name='next_quarter')
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2011, month=7, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=9, day=30, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=today)
                        )

    def test_next_quarter02(self):
        today = datetime(year=2011, month=12, day=3)
        self.assertEqual({'modified__range': (datetime(year=2012, month=1, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2012, month=3, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='next_quarter')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_yesterday01(self):
        today = datetime(year=2011, month=6, day=1, hour=14, minute=14, second=37)
        self.assertEqual({'modified__range': (datetime(year=2011, month=5, day=31, hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=5, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='yesterday')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_yesterday02(self):
        today = datetime(year=2011, month=6, day=2, hour=14, minute=14, second=37)
        self.assertEqual({'modified__range': (datetime(year=2011, month=6, day=1, hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=6, day=1, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='yesterday')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_today(self):
        today = datetime(year=2011, month=6, day=1, hour=14, minute=14, second=37)
        self.assertEqual({'modified__range': (datetime(year=2011, month=6, day=1, hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=6, day=1, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='today')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_tomorrow01(self):
        today = datetime(year=2011, month=6, day=1, hour=14, minute=14, second=37)
        self.assertEqual({'modified__range': (datetime(year=2011, month=6, day=2, hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=6, day=2, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='tomorrow')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_tomorrow02(self):
        today = datetime(year=2011, month=6, day=30, hour=14, minute=14, second=37)
        self.assertEqual({'modified__range': (datetime(year=2011, month=7, day=1, hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=7, day=1, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='tomorrow')\
                                            .get_q_dict(field='modified', now=today)
                        )

