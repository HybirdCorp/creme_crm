from datetime import date, time

from django.utils.translation import gettext as _

from creme.activities.forms.bulk_update import ActivityRangeField
from creme.activities.forms.fields import DateWithOptionalTimeField
from creme.creme_core.tests.base import CremeTestCase


class ActivityRangeFieldTestCase(CremeTestCase):
    def test_range(self):
        DWOT = DateWithOptionalTimeField.DateWithOptionalTime

        def build_range(**kwargs):
            return ActivityRangeField.Range(**{
                'start': DWOT(date=date(year=2023, month=6, day=22), time=time(hour=14, minute=0)),
                'end': DWOT(date=date(year=2023, month=6, day=22), time=time(hour=16, minute=30)),
                'all_day': False,
                'busy': True,
                **kwargs
            })

        act_range = build_range()
        self.assertEqual(
            DWOT(date=date(year=2023, month=6, day=22), time=time(hour=14, minute=0)),
            act_range.start,
        )
        self.assertEqual(
            DWOT(date=date(year=2023, month=6, day=22), time=time(hour=16, minute=30)),
            act_range.end,
        )
        self.assertIs(act_range.all_day, False)
        self.assertIs(act_range.busy, True)

        self.assertEqual(build_range(), act_range)
        self.assertNotEqual(None, act_range)
        self.assertNotEqual(build_range(all_day=True), act_range)
        self.assertNotEqual(build_range(busy=False),   act_range)
        self.assertNotEqual(build_range(start=None),   act_range)

    def test_clean__empty__required(self):
        field = ActivityRangeField(required=True)
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=[])

    def test_clean__empty__not_required(self):
        field = ActivityRangeField(required=False)
        self.assertIsNone(field.clean([]))
        self.assertIsNone(field.clean(['']))
        self.assertIsNone(field.clean(['', '']))

    def test_clean__complete(self):
        field = ActivityRangeField()

        DWOT = DateWithOptionalTimeField.DateWithOptionalTime
        self.assertEqual(
            field.Range(
                start=DWOT(date=date(year=2022, month=10, day=20), time=time(hour=18, minute=30)),
                end=DWOT(date=date(year=2022, month=10, day=21), time=time(hour=12, minute=00)),
                all_day=False,
                busy=True,
            ),
            field.clean([
                [self.formfield_value_date(2022, 10, 20), '18:30:00'],
                [self.formfield_value_date(2022, 10, 21), '12:00:00'],
                '',
                'on',
            ]),
        )

    def test_clean__partial_datetime(self):
        field = ActivityRangeField()

        DWOT = DateWithOptionalTimeField.DateWithOptionalTime
        self.assertEqual(
            field.Range(
                start=DWOT(date=date(year=2023, month=3, day=15), time=time(hour=14, minute=45)),
                end=DWOT(date=date(year=2023, month=3, day=16)),
                all_day=True,
                busy=False,
            ),
            field.clean([
                [self.formfield_value_date(2023, 3, 15), '14:45:00'],
                [self.formfield_value_date(2023, 3, 16)],
                'on',
                '',
            ]),
        )

    def test_clean__partial__not_required(self):
        field = ActivityRangeField(required=False)
        DWOT = DateWithOptionalTimeField.DateWithOptionalTime
        self.assertEqual(
            field.Range(
                start=DWOT(date=date(year=2023, month=3, day=15), time=time(hour=14, minute=45)),
                end=None,
                all_day=False,
                busy=False,
            ),
            field.clean([
                [self.formfield_value_date(2023, 3, 15), '14:45:00'],
                ['', ''],
                '',
                '',
            ]),
        )
        self.assertEqual(
            field.Range(
                start=None,
                end=DWOT(date=date(year=2023, month=3, day=16)),
                all_day=False,
                busy=False,
            ),
            field.clean([
                ['', ''],
                [self.formfield_value_date(2023, 3, 16), ''],
                '',
                '',
            ]),
        )
