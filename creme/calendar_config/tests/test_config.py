from datetime import time

from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.calendar_config.bricks import CalendarConfigItemsBrick
from creme.calendar_config.models import CalendarConfigItem
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin


class CalendarConfigItemTestCase(BrickTestCaseMixin, CremeTestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.role = cls.create_role()

    def create_if_needed(self, *, role, superuser, **kwargs):
        return CalendarConfigItem.objects.get_or_create(
            role=role,
            superuser=superuser,
            defaults=kwargs,
        )[0]

    def for_superuser(self):
        return CalendarConfigItem.objects.filter(
            Q(role__isnull=True, superuser=True),
        ).first()

    def test_as_dict(self):
        self.assertDictEqual(CalendarConfigItem().as_dict(), {
            "view": "month",
            "week_days": [1, 2, 3, 4, 5, 6],
            "week_start": 1,
            "day_start": "08:00",
            "day_end": "18:00",
            "slot_duration": "00:15:00",
            "allow_event_move": True,
            "extra_data": {},
        })

    def test_missing_default(self):
        CalendarConfigItem.objects.all().delete()

        with self.assertRaises(ConflictError) as e:
            CalendarConfigItem.objects.get_default()

        self.assertEqual(
            str(e.exception),
            _("The default configuration for calendar is not populated.")
        )

        with self.assertRaises(ConflictError) as e:
            CalendarConfigItem.objects.for_user(self.login_as_standard())

        self.assertEqual(
            str(e.exception),
            _("The default configuration for calendar is not populated.")
        )

    def test_default(self):
        CalendarConfigItem.objects.all().delete()

        week_default = CalendarConfigItem.objects.create(
            superuser=False, role=None, view="week"
        )

        default = CalendarConfigItem.objects.get_default()

        self.assertEqual(default.pk, week_default.pk)
        self.assertDictEqual(week_default.as_dict(), default.as_dict())

    def test_for_user(self):
        user = self.create_user(role=self.role)
        other_user = self.create_user(username='other', role=self.create_role(name='other'))
        super_user = self.get_root_user()

        default_config = CalendarConfigItem.objects.get_default()

        self.assertEqual(
            default_config.as_dict(),
            CalendarConfigItem.objects.for_user(user).as_dict()
        )
        self.assertEqual(
            default_config.as_dict(),
            CalendarConfigItem.objects.for_user(other_user).as_dict()
        )
        self.assertEqual(
            default_config.as_dict(),
            CalendarConfigItem.objects.for_user(super_user).as_dict()
        )

        role_config = self.create_if_needed(
            role=self.role, superuser=False, view="week", week_days=(1, 2, 4, 5),
        )

        self.assertEqual(
            role_config.as_dict(),
            CalendarConfigItem.objects.for_user(user).as_dict()
        )
        self.assertEqual(
            default_config.as_dict(),
            CalendarConfigItem.objects.for_user(other_user).as_dict()
        )
        self.assertEqual(
            default_config.as_dict(),
            CalendarConfigItem.objects.for_user(super_user).as_dict()
        )

        superuser_config = self.create_if_needed(role=None, superuser=True, view='week')

        self.assertEqual(
            role_config.as_dict(),
            CalendarConfigItem.objects.for_user(user).as_dict()
        )
        self.assertEqual(
            default_config.as_dict(),
            CalendarConfigItem.objects.for_user(other_user).as_dict()
        )
        self.assertEqual(
            superuser_config.as_dict(),
            CalendarConfigItem.objects.for_user(super_user).as_dict()
        )

    def test_config_portal(self):
        self.login_as_root()

        response = self.assertGET200(
            reverse('creme_config__app_portal', args=('activities',))
        )
        self.get_brick_node(
            self.get_html_tree(response.content), brick=CalendarConfigItemsBrick,
        )

    def test_config_create__not_allowed(self):
        self.login_as_standard()
        self.assertGET403(
            reverse('calendar_config__add_calendar_settings')
        )

    def test_config_create__role_choices(self):
        self.login_as_root()

        url = reverse('calendar_config__add_calendar_settings')
        other_role = self.create_role(name='other')
        response = self.assertGET200(url)

        role_field = response.context['form'].fields['role']
        self.assertListEqual([
            ('', f'*{_("Superuser")}*'),
            (self.role.pk, str(self.role)),
            (other_role.pk, str(other_role)),
        ], [c for c in role_field.choices])

        self.create_if_needed(role=None, superuser=True)

        response = self.assertGET200(url)
        role_field = response.context['form'].fields['role']
        self.assertListEqual([
            (self.role.pk, str(self.role)),
            (other_role.pk, str(other_role)),
        ], [c for c in role_field.choices])

        self.create_if_needed(role=self.role, superuser=False)

        response = self.assertGET200(url)
        role_field = response.context['form'].fields['role']
        self.assertListEqual([
            (other_role.pk, str(other_role)),
        ], [c for c in role_field.choices])

        self.create_if_needed(role=other_role, superuser=False)

        response = self.assertGET200(url)
        role_field = response.context['form'].fields['role']
        self.assertListEqual([], [c for c in role_field.choices])

    def test_config_create__clone_default(self):
        self.login_as_root()

        default = CalendarConfigItem.objects.get_default()
        url = reverse('calendar_config__add_calendar_settings')

        response = self.assertGET200(url)
        self.assertEqual(response.context['form'].instance.as_dict(), default.as_dict())

        # Now customize the default configuration
        new_default = self.create_if_needed(
            role=None, superuser=False, view="week", week_days=(1, 2, 4, 5)
        )

        response = self.assertGET200(url)
        self.assertEqual(response.context['form'].instance.as_dict(), new_default.as_dict())

    def test_config_create_superuser(self):
        self.login_as_root()

        default = CalendarConfigItem.objects.get_default()

        self.assertIsNone(self.for_superuser())

        url = reverse('calendar_config__add_calendar_settings')
        response = self.assertGET200(url)

        role_field = response.context['form'].fields['role']
        self.assertListEqual([
            ('', f'*{_("Superuser")}*'),
            (self.role.pk, str(self.role)),
        ], [c for c in role_field.choices])

        response = self.assertPOST200(url, data={
            **default.as_dict(),
            "role": "",
            "view": "week",
            "week_days": (1, 2, 3, 4),
            "week_start": "2",
            "slot_duration": time(0, 30, 0),
            "day_start": "07:00:00",
            "day_end": "19:00:00",
        })

        self.assertNoFormError(response)

        superuser_config = self.for_superuser()
        self.assertDictEqual({
            **default.as_dict(),
            "view": "week",
            "week_days": [1, 2, 3, 4],
            "week_start": 2,
            "slot_duration": "00:30:00",
            "day_start": "07:00",
            "day_end": "19:00",
        }, superuser_config.as_dict())

    def test_config_create_for_role(self):
        self.login_as_root()

        default = CalendarConfigItem.objects.get_default()

        url = reverse('calendar_config__add_calendar_settings')
        response = self.assertGET200(url)

        role_field = response.context['form'].fields['role']
        self.assertListEqual([
            ('', f'*{_("Superuser")}*'),
            (self.role.pk, str(self.role)),
        ], [c for c in role_field.choices])

        response = self.assertPOST200(url, data={
            **default.as_dict(),
            "role": self.role.pk,
            "view": "week",
            "week_days": (1, 2, 3, 4),
            "week_start": "2",
            "slot_duration": time(0, 30, 0),
            "day_start": "07:00:00",
            "day_end": "19:00:00",
        })

        self.assertNoFormError(response)

        config = self.get_object_or_fail(CalendarConfigItem, role=self.role.pk)
        self.assertDictEqual({
            **default.as_dict(),
            "view": "week",
            "week_days": [1, 2, 3, 4],
            "week_start": 2,
            "slot_duration": "00:30:00",
            "day_start": "07:00",
            "day_end": "19:00",
        }, config.as_dict())

    def test_config_edit__not_allowed(self):
        self.login_as_standard()

        default = CalendarConfigItem.objects.get_default()

        self.assertGET403(
            reverse('calendar_config__edit_calendar_settings', args=(default.pk,))
        )

    def test_config_edit(self):
        self.login_as_root()

        default = CalendarConfigItem.objects.get_default()
        role_config = self.create_if_needed(
            role=self.role, superuser=False, view="week", week_days=(1, 2, 4, 5)
        )

        url = reverse('calendar_config__edit_calendar_settings', args=(role_config.pk,))
        self.assertGET200(url)

        response = self.assertPOST200(url, data={
            **default.as_dict(),
            "view": "week",
            "week_days": (1, 2, 3, 4),
            "week_start": "2",
            "slot_duration": time(0, 30, 0),
            "day_start": "07:00:00",
            "day_end": "19:00:00",
        })

        self.assertNoFormError(response)

        role_config = self.get_object_or_fail(CalendarConfigItem, pk=role_config.pk)
        self.assertDictEqual({
            **default.as_dict(),
            "view": "week",
            "week_days": [1, 2, 3, 4],
            "week_start": 2,
            "slot_duration": "00:30:00",
            "day_start": "07:00",
            "day_end": "19:00",
        }, role_config.as_dict())

    def test_config_delete__not_allowed(self):
        self.login_as_standard()

        config = self.create_if_needed(
            role=self.role, superuser=False, view="week", week_days=(1, 2, 4, 5)
        )

        self.assertPOST403(reverse('calendar_config__delete_calendar_settings'), data={
            "id": config.pk
        })

    def test_config_delete(self):
        self.login_as_root()

        config = self.create_if_needed(
            role=self.role, superuser=False, view="week", week_days=(1, 2, 4, 5)
        )

        url = reverse('calendar_config__delete_calendar_settings')
        self.assertPOST200(url, data={
            "id": config.pk
        })

        self.assertDoesNotExist(config)

    def test_config_delete__default(self):
        self.login_as_root()

        config = CalendarConfigItem.objects.get_default()

        url = reverse('calendar_config__delete_calendar_settings')
        self.assertPOST409(url, data={
            "id": config.pk
        })

        self.assertStillExists(config)

    def test_calendar_override(self):
        user = self.login_as_standard(
            allowed_apps=['persons', 'activities'],
        )

        config = self.create_if_needed(
            role=user.role, superuser=False, view="week", week_days=(1, 2, 4, 5)
        )

        url = reverse('activities__calendar')
        response = self.assertGET200(url)

        self.assertDictEqual(
            response.context['calendar_settings'],
            config.as_dict()
        )
