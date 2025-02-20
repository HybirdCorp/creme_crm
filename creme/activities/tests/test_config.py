from datetime import time

from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.activities.bricks import CalendarConfigItemsBrick
from creme.activities.models import CalendarConfigItem
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin


class CalendarConfigItemTestCase(BrickTestCaseMixin, CremeTestCase):
    ADD_URL = reverse('activities__add_calendar_settings')
    DELETE_URL = reverse('activities__delete_calendar_settings')

    @staticmethod
    def _build_edit_url(item):
        return reverse('activities__edit_calendar_settings', args=(item.id,))

    def create_if_needed(self, *, role, superuser, **kwargs):
        return CalendarConfigItem.objects.get_or_create(
            role=role, superuser=superuser, defaults=kwargs,
        )[0]

    def for_superuser(self):
        return CalendarConfigItem.objects.filter(
            role__isnull=True, superuser=True,
        ).first()

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

        # ---
        role_dict = self.create_if_needed(
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
        superuser_config = self.create_if_needed(role=None, superuser=True, view='week')
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

    def test_config_portal(self):
        self.login_as_root()

        response = self.assertGET200(
            reverse('creme_config__app_portal', args=('activities',)),
        )
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=CalendarConfigItemsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=1,
            title='{count} Configured calendar view',
            plural_title='{count} Configured calendar views',
        )

    def test_config_create__not_allowed(self):
        self.login_as_standard()
        self.assertGET403(self.ADD_URL)

    def test_config_create__role_choices(self):
        self.login_as_root()
        role1 = self.get_regular_role()
        role2 = self.create_role(name='Other')

        url = self.ADD_URL
        response1 = self.assertGET200(url)

        with self.assertNoException():
            role_choices1 = response1.context['form'].fields['role'].choices

        self.assertInChoices(
            value='', label=f'*{_("Superuser")}*', choices=role_choices1,
        )
        self.assertInChoices(
            value=role1.id, label=role1.name, choices=role_choices1,
        )
        self.assertInChoices(
            value=role2.id, label=role2.name, choices=role_choices1,
        )

        # ---
        self.create_if_needed(role=None, superuser=True)

        role_choices2 = self.assertGET200(url).context['form'].fields['role'].choices
        self.assertInChoices(
            value=role1.id, label=role1.name, choices=role_choices2,
        )
        self.assertInChoices(
            value=role2.id, label=role2.name, choices=role_choices2,
        )
        self.assertNotInChoices(value='', choices=role_choices2)

        # ---
        self.create_if_needed(role=role1, superuser=False)

        role_choices3 = self.assertGET200(url).context['form'].fields['role'].choices
        self.assertInChoices(
            value=role2.id, label=role2.name, choices=role_choices3,
        )
        self.assertNotInChoices(value=role1.id, choices=role_choices3)
        self.assertNotInChoices(value='',       choices=role_choices3)

        # ---
        self.create_if_needed(role=role2, superuser=False)
        self.assertFalse(
            [*self.assertGET200(url).context['form'].fields['role'].choices],
        )

    def test_config_create__clone_default(self):
        self.login_as_root()

        default = CalendarConfigItem.objects.get_default()
        url = self.ADD_URL
        self.assertDictEqual(
            default.as_dict(),
            self.assertGET200(url).context['form'].instance.as_dict(),
        )

        # Now customize the default configuration ---
        new_default = self.create_if_needed(
            role=None, superuser=False, view='week', week_days=(1, 2, 4, 5),
        )
        self.assertDictEqual(
            new_default.as_dict(),
            self.assertGET200(url).context['form'].instance.as_dict(),
        )

    @parameterized.expand([
        (
            {
                'view_day_start': '00:00:00',
                'view_day_end': '00:00:00',
            }, {
                'day_start': time(8, 0, 0),
                'day_end': time(18, 0, 0),
                'view_day_start': time(0, 0, 0),
                'view_day_end': time(0, 0, 0),
            }
        ),
        (
            {
                'day_start': '7:00:00',
                'day_end': '19:00:00',
                'view_day_start': '00:00:00',
                'view_day_end': '00:00:00',
            }, {
                'day_start': time(7, 0, 0),
                'day_end': time(19, 0, 0),
                'view_day_start': time(0, 0, 0),
                'view_day_end': time(0, 0, 0),
            }
        ),
        (
            {
                'view_day_start': '7:00:00',
                'view_day_end': '19:00:00',
            }, {
                'day_start': time(8, 0, 0),
                'day_end': time(18, 0, 0),
                'view_day_start': time(7, 0, 0),
                'view_day_end': time(19, 0, 0),
            }
        ),
        (
            {
                'view_day_start': '8:00:00',
                'view_day_end': '18:00:00',
            }, {
                'day_start': time(8, 0, 0),
                'day_end': time(18, 0, 0),
                'view_day_start': time(8, 0, 0),
                'view_day_end': time(18, 0, 0),
            }
        ),
    ])
    def test_config_create__day_range(self, options, expected):
        self.login_as_root()

        default = CalendarConfigItem.objects.get_default()

        response = self.client.post(
            self.ADD_URL,
            data={
                **default.as_dict(),
                'role': '',
                'view': 'week',
                'week_days': (1, 2, 3, 4),
                'week_start': '2',
                'slot_duration': time(0, 30, 0),
                **options,
            },
        )

        self.assertNoFormError(response)

        config = CalendarConfigItem.objects.exclude(pk=default.pk).get()
        self.assertEqual(config.day_start, expected['day_start'])
        self.assertEqual(config.day_end, expected['day_end'])
        self.assertEqual(config.view_day_start, expected['view_day_start'])
        self.assertEqual(config.view_day_end, expected['view_day_end'])

    @parameterized.expand([
        (
            {
                'day_start': '19:00:00',
                'day_end': '07:00:00',
            }, [
                _('Day start ({start}) must be before end ({end}).').format(
                    start=date_format(time(19, 0, 0), 'TIME_FORMAT'),
                    end=date_format(time(7, 0, 0), 'TIME_FORMAT'),
                )
            ]
        ),
        (
            {
                'view_day_start': '19:00:00',
                'view_day_end': '07:00:00',
            }, [
                _('Visible start ({start}) must be before end ({end}).').format(
                    start=date_format(time(19, 0, 0), 'TIME_FORMAT'),
                    end=date_format(time(7, 0, 0), 'TIME_FORMAT'),
                )
            ]
        ),
        (
            {
                'view_day_start': '07:00:00',
                'view_day_end': '07:00:00',
            }, [
                _('Visible start ({start}) must be before end ({end}).').format(
                    start=date_format(time(7, 0, 0), 'TIME_FORMAT'),
                    end=date_format(time(7, 0, 0), 'TIME_FORMAT'),
                )
            ]
        ),
        (
            {
                'day_start': '07:00:00',
                'day_end': '19:00:00',
                'view_day_start': '10:00:00',
                'view_day_end': '15:00:00',
            }, [
                _(
                    'The visible range of the day ({start} − {end}) should contains '
                    'the working hours ({day_start} − {day_end}) or some events will '
                    'not be displayed'
                ).format(
                    start=date_format(time(10, 0, 0), 'TIME_FORMAT'),
                    end=date_format(time(15, 0, 0), 'TIME_FORMAT'),
                    day_start=date_format(time(7, 0, 0), 'TIME_FORMAT'),
                    day_end=date_format(time(19, 0, 0), 'TIME_FORMAT'),
                )
            ]
        ),
        (
            {
                'day_start': '07:00:00',
                'day_end': '19:00:00',
                'view_day_start': '7:00:00',
                'view_day_end': '15:00:00',
            }, [
                _(
                    'The visible range of the day ({start} − {end}) should contains '
                    'the working hours ({day_start} − {day_end}) or some events will '
                    'not be displayed'
                ).format(
                    start=date_format(time(7, 0, 0), 'TIME_FORMAT'),
                    end=date_format(time(15, 0, 0), 'TIME_FORMAT'),
                    day_start=date_format(time(7, 0, 0), 'TIME_FORMAT'),
                    day_end=date_format(time(19, 0, 0), 'TIME_FORMAT'),
                )
            ]
        ),
    ])
    def test_config_create__day_range_errors(self, options, expected):
        self.login_as_root()

        default = CalendarConfigItem.objects.get_default()

        response = self.client.post(
            self.ADD_URL,
            data={
                **default.as_dict(),
                'role': '',
                'view': 'week',
                'week_days': (1, 2, 3, 4),
                'week_start': '2',
                'slot_duration': time(0, 30, 0),
                **options,
            },
        )

        self.assertFormError(response.context['form'], None, expected)

    def test_config_create_superuser(self):
        self.login_as_root()
        role = self.get_regular_role()

        default = CalendarConfigItem.objects.get_default()
        self.assertIsNone(self.for_superuser())

        url = self.ADD_URL
        role_choices = self.assertGET200(url).context['form'].fields['role'].choices
        self.assertEqual(2, len(role_choices))
        self.assertInChoices(
            value='', label=f'*{_("Superuser")}*', choices=role_choices,
        )
        self.assertInChoices(value=role.id, label=role.name, choices=role_choices)

        # ---
        self.assertNoFormError(self.client.post(
            url,
            data={
                **default.as_dict(),
                'role': '',
                'view': 'week',
                'view_day_start': '00:00:00',
                'view_day_end': '00:00:00',
                'week_days': (1, 2, 3, 4),
                'week_start': '2',
                'slot_duration': time(0, 30, 0),
                'day_start': '07:00:00',
                'day_end': '19:00:00',
            },
        ))

        superuser_config = self.for_superuser()
        self.assertDictEqual(
            {
                **default.as_dict(),
                'view': 'week',
                'view_day_start': '00:00',
                'view_day_end': '24:00',
                'week_days': [1, 2, 3, 4],
                'week_start': 2,
                'slot_duration': '00:30:00',
                'day_start': '07:00',
                'day_end': '19:00',
            },
            superuser_config.as_dict(),
        )

    def test_config_create_for_role(self):
        self.login_as_root()
        role = self.get_regular_role()
        default = CalendarConfigItem.objects.get_default()

        url = self.ADD_URL
        role_field = self.assertGET200(url).context['form'].fields['role']
        self.assertListEqual(
            [('', f'*{_("Superuser")}*'), (role.id, str(role))],
            [*role_field.choices],
        )

        # ---
        self.assertNoFormError(self.client.post(
            url,
            data={
                **default.as_dict(),
                'role': role.id,
                'view': 'week',
                'view_day_start': '05:00:00',
                'view_day_end': '20:00:00',
                'week_days': (1, 2, 3, 4),
                'week_start': '2',
                'slot_duration': time(0, 30, 0),
                'day_start': '07:00:00',
                'day_end': '19:00:00',
            },
        ))

        config = self.get_object_or_fail(CalendarConfigItem, role=role.id)
        self.assertDictEqual(
            {
                **default.as_dict(),
                'view': 'week',
                'view_day_start': '05:00',
                'view_day_end': '20:00',
                'week_days': [1, 2, 3, 4],
                'week_start': 2,
                'slot_duration': '00:30:00',
                'day_start': '07:00',
                'day_end': '19:00',
            },
            config.as_dict(),
        )

    def test_config_edit__not_allowed(self):
        self.login_as_standard()

        default = CalendarConfigItem.objects.get_default()
        self.assertGET403(self._build_edit_url(default))

    def test_config_edit(self):
        self.login_as_root()

        default = CalendarConfigItem.objects.get_default()
        role_config = self.create_if_needed(
            role=self.get_regular_role(), superuser=False,
            view='week', week_days=(1, 2, 4, 5),
        )

        url = self._build_edit_url(role_config)
        self.assertGET200(url)

        # ---
        self.assertNoFormError(self.client.post(
            url,
            data={
                **default.as_dict(),
                'view': 'week',
                'view_day_start': '00:00:00',
                'view_day_end': '00:00:00',
                'week_days': (1, 2, 3, 4),
                'week_start': '2',
                'slot_duration': time(0, 30, 0),
                'day_start': '07:00:00',
                'day_end': '19:00:00',
            },
        ))

        role_config = self.get_object_or_fail(CalendarConfigItem, pk=role_config.pk)
        self.assertDictEqual(
            {
                **default.as_dict(),
                'view': 'week',
                'view_day_start': '00:00',
                'view_day_end': '24:00',
                'week_days': [1, 2, 3, 4],
                'week_start': 2,
                'slot_duration': '00:30:00',
                'day_start': '07:00',
                'day_end': '19:00',
            },
            role_config.as_dict(),
        )

    def test_config_edit__errors(self):
        self.login_as_root()

        default = CalendarConfigItem.objects.get_default()
        role_config = self.create_if_needed(
            role=self.get_regular_role(), superuser=False,
            view='week', week_days=(1, 2, 4, 5),
        )

        response = self.client.post(
            self._build_edit_url(role_config),
            data={
                **default.as_dict(),
                'role': '',
                'view': 'week',
                'week_days': (1, 2, 3, 4),
                'week_start': '2',
                'slot_duration': time(0, 30, 0),
                'day_start': '19:00:00',
                'day_end': '07:00:00',
                'view_day_start': '19:00:00',
                'view_day_end': '07:00:00',
            },
        )

        self.assertFormError(response.context['form'], None, [
            _('Day start ({start}) must be before end ({end}).').format(
                start=date_format(time(19, 0, 0), 'TIME_FORMAT'),
                end=date_format(time(7, 0, 0), 'TIME_FORMAT'),
            )
        ])

        response = self.client.post(
            self._build_edit_url(role_config),
            data={
                **default.as_dict(),
                'role': '',
                'view': 'week',
                'week_days': (1, 2, 3, 4),
                'week_start': '2',
                'slot_duration': time(0, 30, 0),
                'day_start': '07:00:00',
                'day_end': '19:00:00',
                'view_day_start': '19:00:00',
                'view_day_end': '07:00:00',
            },
        )

        self.assertFormError(response.context['form'], None, [
            _('Visible start ({start}) must be before end ({end}).').format(
                start=date_format(time(19, 0, 0), 'TIME_FORMAT'),
                end=date_format(time(7, 0, 0), 'TIME_FORMAT'),
            )
        ])

    def test_config_delete__not_allowed(self):
        self.login_as_standard()

        config = self.create_if_needed(
            role=self.get_regular_role(), superuser=False,
            view='week', week_days=(1, 2, 4, 5),
        )
        self.assertPOST403(self.DELETE_URL, data={'id': config.id})

    def test_config_delete(self):
        self.login_as_root()

        config = self.create_if_needed(
            role=self.get_regular_role(), superuser=False,
            view='week', week_days=(1, 2, 4, 5),
        )
        self.assertPOST200(self.DELETE_URL, data={'id': config.id})
        self.assertDoesNotExist(config)

    def test_config_delete__default(self):
        self.login_as_root()

        config = CalendarConfigItem.objects.get_default()
        self.assertPOST409(self.DELETE_URL, data={'id': config.id})
        self.assertStillExists(config)
