from functools import partial

from dateutil.relativedelta import relativedelta
from django.utils.formats import number_format
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.activities.statistics import AveragePerMonthStatistics

from .. import constants
from .base import Activity, _ActivitiesTestCase, skipIfCustomActivity


class StatisticsTestCase(_ActivitiesTestCase):
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
        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER)
        create_activity = partial(
            Activity.objects.create,
            user=self.get_root_user(), type_id=sub_type.type_id, sub_type=sub_type,
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
                ).format(count=number_format(1, decimal_pos=1)),
                _('No phone call since one year'),
            ],
            AveragePerMonthStatistics(Activity)()
        )

    @skipIfCustomActivity
    def test_average_per_month03(self):
        "1.5 meeting per month."
        now_value = now()
        sub_type1 = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER)
        create_activity = partial(
            Activity.objects.create,
            user=self.get_root_user(),
            type_id=sub_type1.type_id, sub_type=sub_type1,
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
        task_type = self._get_type(constants.UUID_TYPE_TASK)
        task_stype = task_type.activitysubtype_set.first()
        for i in range(1, 4):
            create_activity(
                title=f'Task #{i}',
                start=now_value - relativedelta(months=i),
                type_id=task_type.id,
                sub_type=task_stype,
            )

        self.assertListEqual(
            [
                ngettext(
                    '{count} meeting per month',
                    '{count} meetings per month',
                    # 1.5
                    2
                ).format(count=number_format(1.5, decimal_pos=1)),
                _('No phone call since one year'),
            ],
            AveragePerMonthStatistics(Activity)(),
        )

    @skipIfCustomActivity
    def test_average_per_month04(self):
        "0.5 phone call per month."
        now_value = now()
        create_activity = partial(Activity.objects.create, user=self.get_root_user())

        atype = self._get_type(constants.UUID_TYPE_TASK)
        create_activity(
            title='Task', start=now_value - relativedelta(months=1),
            type=atype, sub_type=atype.activitysubtype_set.first(),
        )  # Should not be counted

        sub_types = [
            self._get_sub_type(uid) for uid in (
                constants.UUID_SUBTYPE_PHONECALL_INCOMING,
                constants.UUID_SUBTYPE_PHONECALL_OUTGOING,
                constants.UUID_SUBTYPE_PHONECALL_CONFERENCE,
                constants.UUID_SUBTYPE_PHONECALL_FAILED,
            )
        ]
        for i in range(1, 7):
            sub_type = sub_types[i % len(sub_types)]
            create_activity(
                title=f'Phone call#{i}',
                start=now_value - relativedelta(months=i),
                type_id=sub_type.type_id, sub_type=sub_type,
            )

        self.assertListEqual(
            [
                _('No meeting since one year'),
                ngettext(
                    '{count} phone call per month',
                    '{count} phone calls per month',
                    0
                ).format(count=number_format(0.5, decimal_pos=1)),
            ],
            AveragePerMonthStatistics(Activity)(),
        )
