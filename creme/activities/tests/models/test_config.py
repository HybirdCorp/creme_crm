from django.utils.translation import gettext as _

from creme.activities.models import CalendarConfigItem
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.tests.base import CremeTestCase


class CalendarConfigItemManagerTestCase(CremeTestCase):
    def test_missing_default(self):
        CalendarConfigItem.objects.all().delete()

        with self.assertRaises(ConflictError) as cm1:
            CalendarConfigItem.objects.get_default()

        self.assertEqual(
            str(cm1.exception),
            _('The default configuration for calendar is not populated.'),
        )

        # ---
        user = self.create_user(role=self.get_regular_role())

        with self.assertRaises(ConflictError) as cm2:
            CalendarConfigItem.objects.for_user(user)

        self.assertEqual(
            str(cm2.exception),
            _('The default configuration for calendar is not populated.'),
        )

    def test_default(self):
        CalendarConfigItem.objects.all().delete()

        week_default = CalendarConfigItem.objects.create(
            superuser=False, role=None, view='week',
        )
        default = CalendarConfigItem.objects.get_default()
        self.assertEqual(default.pk, week_default.pk)
        self.assertDictEqual(week_default.as_dict(), default.as_dict())

    def test_for_user(self):
        role = self.get_regular_role()
        user = self.create_user(role=role)
        other_user = self.create_user(username='other', role=self.create_role(name='Other role'))
        super_user = self.get_root_user()

        default_dict = CalendarConfigItem.objects.get_default().as_dict()
        self.assertDictEqual(
            default_dict, CalendarConfigItem.objects.for_user(user).as_dict(),
        )
        self.assertDictEqual(
            default_dict, CalendarConfigItem.objects.for_user(other_user).as_dict(),
        )
        self.assertDictEqual(
            default_dict, CalendarConfigItem.objects.for_user(super_user).as_dict(),
        )

        def _create_if_needed(role, superuser, **kwargs):
            return CalendarConfigItem.objects.get_or_create(
                role=role, superuser=superuser, defaults=kwargs,
            )[0]

        # ---
        role_dict = _create_if_needed(
            role=role, superuser=False, view='week', week_days=(1, 2, 4, 5),
        ).as_dict()
        self.assertDictEqual(
            role_dict, CalendarConfigItem.objects.for_user(user).as_dict(),
        )
        self.assertDictEqual(
            default_dict, CalendarConfigItem.objects.for_user(other_user).as_dict(),
        )
        self.assertDictEqual(
            default_dict, CalendarConfigItem.objects.for_user(super_user).as_dict(),
        )

        # ---
        superuser_config = _create_if_needed(role=None, superuser=True, view='week')
        self.assertDictEqual(
            role_dict, CalendarConfigItem.objects.for_user(user).as_dict(),
        )
        self.assertDictEqual(
            default_dict, CalendarConfigItem.objects.for_user(other_user).as_dict()
        )
        self.assertDictEqual(
            superuser_config.as_dict(),
            CalendarConfigItem.objects.for_user(super_user).as_dict(),
        )


class CalendarConfigItemTestCase(CremeTestCase):
    def test_as_dict(self):
        self.assertDictEqual(
            {
                'view': 'month',
                'view_day_start': '00:00',
                'view_day_end': '24:00',
                'week_days': [1, 2, 3, 4, 5, 6],
                'week_start': 1,
                'day_start': '08:00',
                'day_end': '18:00',
                'slot_duration': '00:15:00',
                'allow_event_move': True,
                'allow_keep_state': False,
                'extra_data': {},
            },
            CalendarConfigItem().as_dict(),
        )
