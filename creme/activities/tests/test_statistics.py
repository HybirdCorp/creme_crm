# -*- coding: utf-8 -*-

from functools import partial

from dateutil.relativedelta import relativedelta
from django.utils.formats import number_format
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.activities.statistics import AveragePerMonthStatistics
from creme.creme_core.tests.base import CremeTestCase

from ..constants import (
    ACTIVITYTYPE_MEETING,
    ACTIVITYTYPE_PHONECALL,
    ACTIVITYTYPE_TASK,
)
from .base import Activity, skipIfCustomActivity


class StatisticsTestCase(CremeTestCase):
    def test_average_per_month01(self):
        "Empty."
        self.assertListEqual(
            [
                _('No meeting since one year'),
                _('No phone call since one year'),
            ],
            AveragePerMonthStatistics(Activity)(),
        )

    @skipIfCustomActivity
    def test_average_per_month02(self):
        "1 meeting per month."
        now_value = now()
        create_activity = partial(
            Activity.objects.create,
            user=self.create_user(),
            type_id=ACTIVITYTYPE_MEETING,
        )

        for i in range(1, 13):
            create_activity(
                title=f'Meeting #{i}', start=now_value - relativedelta(months=i),
            )

        # Should not be counted (too old)
        for i in range(1, 4):
            create_activity(
                title='Task', start=now_value - relativedelta(years=1, months=1),
            )

        self.assertListEqual(
            [
                ngettext(
                    '{count} meeting per month',
                    '{count} meetings per month',
                    1
                ).format(
                    count=number_format(1, decimal_pos=1, use_l10n=True),
                ),
                _('No phone call since one year'),
            ],
            AveragePerMonthStatistics(Activity)()
        )

    @skipIfCustomActivity
    def test_average_per_month03(self):
        "1.5 meeting per month."
        now_value = now()
        create_activity = partial(
            Activity.objects.create,
            user=self.create_user(),
            type_id=ACTIVITYTYPE_MEETING,
        )

        for i in range(1, 13):
            create_activity(
                title=f'Meeting #A-{i}',
                start=now_value - relativedelta(months=i),
            )

        for i in range(1, 7):
            create_activity(
                title=f'Meeting #B-{i}',
                start=now_value - relativedelta(months=i),
            )

        # Should not be counted (not meeting)
        for i in range(1, 4):
            create_activity(
                title=f'Task #{i}',
                start=now_value - relativedelta(months=i),
                type_id=ACTIVITYTYPE_TASK,
            )

        self.assertListEqual(
            [
                ngettext(
                    '{count} meeting per month',
                    '{count} meetings per month',
                    1.5
                ).format(
                    count=number_format(1.5, decimal_pos=1, use_l10n=True),
                ),
                _('No phone call since one year'),
            ],
            AveragePerMonthStatistics(Activity)(),
        )

    @skipIfCustomActivity
    def test_average_per_month04(self):
        "0.5 phone call per month."
        now_value = now()
        create_activity = partial(
            Activity.objects.create,
            user=self.create_user(),
            type_id=ACTIVITYTYPE_PHONECALL,
        )

        create_activity(
            title='Task', start=now_value - relativedelta(months=1),
            type_id=ACTIVITYTYPE_TASK,
        )  # Should not be counted

        for i in range(1, 7):
            create_activity(
                title=f'Phone call#{i}',
                start=now_value - relativedelta(months=i),
            )

        self.assertListEqual(
            [
                _('No meeting since one year'),
                ngettext(
                    '{count} phone call per month',
                    '{count} phone calls per month',
                    0.5
                ).format(
                    count=number_format(0.5, decimal_pos=1, use_l10n=True),
                ),
            ],
            AveragePerMonthStatistics(Activity)(),
        )
