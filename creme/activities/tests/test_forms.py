from copy import deepcopy
from datetime import date, time

from django.db.models.expressions import Q
from django.forms import Field
from django.test.utils import override_settings
from django.utils.translation import gettext as _

from creme.activities.forms.fields import ActivitySubTypeField
from creme.activities.models.activity import Activity
from creme.creme_core.forms.enumerable import NO_LIMIT
from creme.creme_core.forms.widgets import Label
from creme.creme_core.tests.base import CremeTestCase

from .. import constants
from ..forms.fields import (
    DateWithOptionalTimeField,
    ParticipatingUsersField,
    UserParticipationField,
)
from ..models import ActivitySubType, ActivityType, Calendar
from .base import _ActivitiesTestCase


class ActivitySubTypeFieldTestCase(_ActivitiesTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.atype = ActivityType.objects.create(
            name='Meeting',
            default_day_duration=0,
            default_hour_duration='01:00:00',
        )
        cls.subtype = ActivitySubType.objects.create(
            name='Rendez-vous', type=cls.atype,
        )

    def test_choices(self):
        field = ActivitySubTypeField()
        self.assertEqual(Activity._meta.get_field('sub_type'), field.enum.field)
        self.assertEqual(NO_LIMIT, field.limit)
        self.assertCountEqual(
            [
                ('', field.empty_label, None),
                *((c.pk, str(c), str(c.type)) for c in ActivitySubType.objects.all()),
            ],
            [(c.value, c.label, c.group) for c in field.choices],
        )

    def test_limit_choices_to(self):
        field = ActivitySubTypeField(
            model=Activity, field_name='sub_type',
            limit_choices_to=Q(type__uuid=constants.UUID_TYPE_UNAVAILABILITY)
        )

        self.assertEqual(field.limit, NO_LIMIT)
        self.assertCountEqual(
            [
                ('', field.empty_label, None),
                *(
                    (c.pk, str(c), str(c.type))
                    for c in ActivitySubType.objects.filter(
                        type__uuid=constants.UUID_TYPE_UNAVAILABILITY,
                    )
                ),
            ],
            [(c.value, c.label, c.group) for c in field.choices],
        )

    def test_deepcopy(self):
        field = ActivitySubTypeField(
            model=Activity, field_name='sub_type',
            limit_choices_to=Q(type__uuid=constants.UUID_TYPE_UNAVAILABILITY)
        )

        field_copy = deepcopy(field)

        self.assertEqual(field_copy.limit, NO_LIMIT)
        self.assertEqual(
            field_copy.limit_choices_to,
            Q(type__uuid=constants.UUID_TYPE_UNAVAILABILITY)
        )

        self.assertListEqual(
            [(c.value, c.label, c.group) for c in field_copy.choices],
            [(c.value, c.label, c.group) for c in field.choices]
        )

    def test_clean(self):
        field = ActivitySubTypeField()
        self.assertEqual(self.subtype, field.clean(self.subtype.pk))
        self.assertFormfieldError(
            field=field, value=None,
            messages=_('This field is required.'),
            codes='required',
        )

    def test_clean__not_required(self):
        field = ActivitySubTypeField(required=False)
        self.assertIsNone(field.clean(None))

    def test_clean__limit_choices_to(self):
        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_UNAVAILABILITY)
        field = ActivitySubTypeField(limit_choices_to=Q(type_id=sub_type.type_id))
        self.assertEqual(
            sub_type,
            field.clean(sub_type.id),
        )
        self.assertFormfieldError(
            field=field,
            value=self._get_sub_type(constants.UUID_SUBTYPE_MEETING_MEETING).id,
            messages=_(
                'Select a valid choice. That choice is not one of the available choices.'
            ),
            codes='invalid_choice',
        )


class DateWithOptionalTimeFieldTestCase(CremeTestCase):
    def test_result(self):
        DWOT = DateWithOptionalTimeField.DateWithOptionalTime
        o1 = DWOT(date=date(year=2023, month=6, day=22), time=time(hour=12, minute=43))
        self.assertEqual(date(year=2023, month=6, day=22), o1.date)
        self.assertEqual(time(hour=12, minute=43),         o1.time)

        o2 = DWOT(date=date(year=2024, month=7, day=15), time=time(hour=16, minute=12))
        self.assertEqual(date(year=2024, month=7, day=15), o2.date)
        self.assertEqual(time(hour=16, minute=12),         o2.time)

        self.assertIsNone(DWOT(date=date(year=2023, month=1, day=1)).time)

        self.assertEqual(
            DWOT(date=date(year=2023, month=6, day=22), time=time(hour=12, minute=43)),
            o1,
        )
        self.assertNotEqual(
            DWOT(date=date(year=2023, month=6, day=23), time=time(hour=12, minute=43)),
            o1,
        )
        self.assertNotEqual(
            DWOT(date=date(year=2023, month=6, day=22), time=time(hour=12, minute=44)),
            o1,
        )
        self.assertNotEqual(DWOT(date=date(year=2023, month=6, day=22)), o1)

    def test_clean_complete(self):
        field = DateWithOptionalTimeField()

        self.assertEqual(
            field.DateWithOptionalTime(
                date=date(year=2020, month=12, day=8),
                time=time(hour=18, minute=44),
            ),
            field.clean([self.formfield_value_date(2020, 12, 8), '18:44:00']),
        )

    def test_clean_empty_required(self):
        field = DateWithOptionalTimeField(required=True)
        code = 'required'
        msg = Field.default_error_messages[code]
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=[])

    def test_clean_empty_not_required(self):
        field = DateWithOptionalTimeField(required=False)
        self.assertIsNone(field.clean([]))
        self.assertIsNone(field.clean(['']))
        self.assertIsNone(field.clean(['', '']))

    def test_clean_only_date(self):
        field = DateWithOptionalTimeField()
        self.assertEqual(
            field.DateWithOptionalTime(date=date(year=2020, month=11, day=9)),
            field.clean([self.formfield_value_date(2020, 11, 9)]),
        )

    def test_required_property01(self):
        field = DateWithOptionalTimeField()
        field.required = False

        with self.assertNoException():
            res = field.clean([])

        self.assertIsNone(res)

    def test_required_property02(self):
        field = DateWithOptionalTimeField(required=False)
        field.required = True

        self.assertFormfieldError(
            field=field, value=[], codes='required', messages=_('This field is required.'),
        )

        with self.assertNoException():
            res = field.clean([self.formfield_value_date(2020, 11, 9)])

        self.assertEqual(
            field.DateWithOptionalTime(date=date(year=2020, month=11, day=9)),
            res,
        )


class UserParticipationFieldTestCase(CremeTestCase):
    def test_clean_empty(self):
        user = self.get_root_user()
        field = UserParticipationField(user=user, required=False)
        self.assertEqual(
            UserParticipationField.Option(is_set=False),
            field.clean([]),
        )

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_clean(self):
        user = self.create_user(
            role=self.create_role(allowed_apps=('persons', 'activities')),
        )
        self.add_credentials(user.role, all=['VIEW', 'LINK'], model=type(user.linked_contact))

        create_cal = Calendar.objects.create
        cal11 = create_cal(user=user, is_default=True,  name='Cal #11')
        cal12 = create_cal(user=user, is_default=False, name='Cal #12')
        cal2 = create_cal(
            user=self.get_root_user(), is_default=True, name='Cal #2', is_public=True,
        )

        field = UserParticipationField(user=user)
        Option = UserParticipationField.Option
        self.assertEqual(Option(is_set=True, data=cal11), field.clean([True, cal11.id]))
        self.assertEqual(Option(is_set=True, data=cal12), field.clean([True, cal12.id]))

        # ---
        self.assertFormfieldError(
            field=field,
            value=[True, cal2.id],
            codes='invalid_choice',
            messages=_(
                'Select a valid choice. That choice is not one of the available choices.'
            ),
        )

        # ---
        self.assertFormfieldError(
            field=field, value=['on', None],
            messages=_('Enter a value if you check the box.'),
            codes='subfield_required',
        )

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_not_linkable(self):
        role = self.create_role(allowed_apps=('persons', 'activities'))
        self.add_credentials(role, all=['VIEW'])

        user = self.create_user(role=role)

        cal = Calendar.objects.create(user=user, is_default=True, name='Cal #11')
        self.assertFormfieldError(
            field=UserParticipationField(user=user),
            value=[True, cal.id],
            messages=_('You are not allowed to link this entity: {}').format(user.linked_contact),
        )

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_is_staff(self):
        user = self.create_user(is_staff=True)

        cal = Calendar.objects.get_default_calendar(user)

        field = UserParticipationField(user=user)
        widget = field.widget
        self.assertIsInstance(widget, Label)
        self.assertEqual(
            _('You cannot participate as staff user'),
            widget.empty_label,
        )

        Option = UserParticipationField.Option
        opt = Option(is_set=False, data=None)
        self.assertEqual(opt, field.clean([False, None]))
        self.assertEqual(opt, field.clean([True, cal.id]))


class ParticipatingUsersFieldTestCase(CremeTestCase):
    def test_clean_empty(self):
        user = self.get_root_user()
        field = ParticipatingUsersField(user=user, required=False)
        # self.assertFalse(field.clean([]))
        empty = {'contacts': [], 'calendars': []}
        self.assertDictEqual(empty, field.clean([]))
        # self.assertFalse(field.clean(None))
        self.assertDictEqual(empty, field.clean(None))

    def test_clean(self):
        user = self.login_as_standard(allowed_apps=('persons', 'activities'))
        self.add_credentials(user.role, all=['VIEW', 'LINK'], model=type(user.linked_contact))

        other_user = self.get_root_user()
        staff_user = self.create_user(index=2, is_staff=True)

        field = ParticipatingUsersField(user=user)
        cleaned = field.clean([user.id, other_user.id])
        self.assertIsDict(cleaned, length=2)
        self.assertCountEqual(
            [user.linked_contact, other_user.linked_contact],
            cleaned.get('contacts'),
        )
        self.assertCountEqual(
            [Calendar.objects.get_default_calendar(u) for u in (user, other_user)],
            cleaned.get('calendars'),
        )

        self.assertFormfieldError(
            field=field,
            value=[user.id, staff_user.id],
            codes='invalid_choice',
            messages=_(
                'Select a valid choice. %(value)s is not one of the available choices.'
            ) % {'value': staff_user.id},
        )

    def test_clean_teammate(self):
        user1 = self.login_as_root_and_get()
        user2 = self.create_user(0)
        user3 = self.create_user(1)
        user4 = self.create_user(2)
        team = self.create_team('Samurais', user3, user4)

        field = ParticipatingUsersField(user=user1)
        cleaned = field.clean([user2.id, team.id])
        self.assertCountEqual(
            [u.linked_contact for u in (user2, user3, user4)],
            cleaned.get('contacts'),
        )
        get_default_calendar = Calendar.objects.get_default_calendar
        self.assertCountEqual(
            [get_default_calendar(u) for u in (user2, user3, user4, team)],
            cleaned.get('calendars'),
        )

    def test_not_linkable(self):
        user = self.login_as_standard(allowed_apps=('persons', 'activities'))
        self.add_credentials(user.role, all=['VIEW'])
        self.assertFormfieldError(
            field=ParticipatingUsersField(user=user),
            value=[user.id],
            messages=_('Some entities are not linkable: {}').format(user.linked_contact),
        )
