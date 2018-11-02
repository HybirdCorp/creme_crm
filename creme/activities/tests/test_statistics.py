# -*- coding: utf-8 -*-

try:
    from functools import partial

    from dateutil.relativedelta import relativedelta

    from django.utils.formats import number_format
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _, ungettext

    from creme.creme_core.tests.base import CremeTestCase

    from creme.activities.statistics import AveragePerMonthStatistics

    from .base import Activity, skipIfCustomActivity
    from ..constants import ACTIVITYTYPE_MEETING, ACTIVITYTYPE_PHONECALL, ACTIVITYTYPE_TASK
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class StatisticsTestCase(CremeTestCase):
    def test_average_per_month01(self):
        "Empty"
        self.login()
        self.assertEqual(
            [_('No meeting since one year'),
             _('No phone call since one year'),
            ],
            AveragePerMonthStatistics(Activity)()
        )

    @skipIfCustomActivity
    def test_average_per_month02(self):
        "1 meeting per month"
        user = self.login()

        now_value = now()
        create_activity = partial(Activity.objects.create, user=user, type_id=ACTIVITYTYPE_MEETING)

        for i in range(1, 13):
            create_activity(title='Meeting #{}'.format(i), start=now_value - relativedelta(months=i))

        # Should not be counted (too old)
        for i in range(1, 4):
            create_activity(title='Task', start=now_value - relativedelta(year=1, months=1))

        self.assertEqual(
            [ungettext('%(count)s meeting per month', '%(count)s meetings per month', 1) % {
                    'count': number_format(1, decimal_pos=1, use_l10n=True),
                },
             _('No phone call since one year'),
            ],
            AveragePerMonthStatistics(Activity)()
        )

    @skipIfCustomActivity
    def test_average_per_month03(self):
        "1.5 meeting per month"
        user = self.login()

        now_value = now()
        create_activity = partial(Activity.objects.create, user=user, type_id=ACTIVITYTYPE_MEETING)

        for i in range(1, 13):
            create_activity(title='Meeting #A-{}'.format(i),
                            start=now_value - relativedelta(months=i),
                           )

        for i in range(1, 7):
            create_activity(title='Meeting #B-{}'.format(i),
                            start=now_value - relativedelta(months=i),
                           )

        # Should not be counted (not meeting)
        for i in range(1, 4):
            create_activity(title='Task #{}'.format(i),
                            start=now_value - relativedelta(months=i),
                            type_id=ACTIVITYTYPE_TASK,
                           )

        self.assertEqual(
            [ungettext('%(count)s meeting per month', '%(count)s meetings per month', 1.5) % {
                    'count': number_format(1.5, decimal_pos=1, use_l10n=True),
                },
             _('No phone call since one year'),
            ],
            AveragePerMonthStatistics(Activity)()
        )

    @skipIfCustomActivity
    def test_average_per_month04(self):
        "0.5 phone call per month"
        user = self.login()

        now_value = now()
        create_activity = partial(Activity.objects.create, user=user, type_id=ACTIVITYTYPE_PHONECALL)

        create_activity(title='Task', start=now_value - relativedelta(months=1),
                        type_id=ACTIVITYTYPE_TASK,
                       )  # Should not be counted

        for i in range(1, 7):
            create_activity(title='Phone call#{}'.format(i),
                            start=now_value - relativedelta(months=i),
                           )

        self.assertEqual(
            [_('No meeting since one year'),
             ungettext('%(count)s phone call per month', '%(count)s phone calls per month', 0.5) % {
                    'count': number_format(0.5, decimal_pos=1, use_l10n=True),
                },
            ],
            AveragePerMonthStatistics(Activity)()
        )
