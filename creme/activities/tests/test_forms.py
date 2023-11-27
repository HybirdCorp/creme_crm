# from json import dumps as json_dump
from copy import deepcopy
from datetime import date, time

from django.core.exceptions import ValidationError
from django.db.models.expressions import Q
from django.test.utils import override_settings
from django.utils.translation import gettext as _

from creme.activities.forms.fields import ActivitySubTypeField
from creme.activities.models.activity import Activity
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.forms.enumerable import NO_LIMIT
from creme.creme_core.models import SetCredentials
from creme.creme_core.tests.forms.base import FieldTestCase

from .. import constants
# from ..forms.fields import ActivityTypeField
from ..forms.fields import (
    DateWithOptionalTimeField,
    ParticipatingUsersField,
    UserParticipationField,
)
from ..models import ActivitySubType, ActivityType, Calendar

# class ActivityTypeFieldTestCase(FieldTestCase):
#     @classmethod
#     def setUpClass(cls):
#         super().setUpClass()
#
#         cls.atype = ActivityType.objects.create(
#             id='meeting', name='Meeting',
#             default_day_duration=0,
#             default_hour_duration='01:00:00',
#         )
#         cls.subtype = ActivitySubType.objects.create(
#             id='rendezvous', name='Rendez-vous', type=cls.atype,
#         )
#
#     @staticmethod
#     def _build_value(act_type_id, subtype_id=None):
#         return json_dump(
#             {'type': act_type_id, 'sub_type': subtype_id},
#             separators=(',', ':'),
#         )
#
#     def test_format_object(self):
#         atype = self.atype
#         subtype = self.subtype
#         from_python = ActivityTypeField(
#             types=ActivityType.objects.filter(pk=atype.id),
#         ).from_python
#         args = (atype.id, subtype.id)
#         self.assertEqual(self._build_value(*args), from_python(args))
#         self.assertEqual(self._build_value(*args), from_python(subtype))
#
#     def test_clean_empty_required(self):
#         clean = ActivityTypeField(required=True).clean
#         self.assertFieldValidationError(ActivityTypeField, 'required', clean, None)
#         self.assertFieldValidationError(ActivityTypeField, 'required', clean, '{}')
#
#     def test_clean_empty_not_required(self):
#         clean = ActivityTypeField(required=False).clean
#
#         with self.assertNoException():
#             value = clean(None)
#
#         self.assertIsNone(value)
#
#         with self.assertNoException():
#             value = clean('{}')
#
#         self.assertIsNone(value)
#
#     def test_clean_invalid_json(self):
#         clean = ActivityTypeField(required=False).clean
#         self.assertFieldValidationError(
#             ActivityTypeField, 'invalidformat', clean,
#             '{"type":"12", "sub_type":"1"',
#         )
#
#     def test_clean_invalid_data_type(self):
#         clean = ActivityTypeField(required=False).clean
#         self.assertFieldValidationError(
#             ActivityTypeField, 'invalidtype', clean, '"this is a string"',
#         )
#         self.assertFieldValidationError(
#             ActivityTypeField, 'invalidtype', clean, '12',
#         )
#
#     def test_clean_unknown_type(self):
#         "Data injections."
#         atype1 = self.atype
#         atype2 = ActivityType.objects.create(
#             id='phonecall', name='phone Call',
#             default_day_duration=0,
#             default_hour_duration=1,
#         )
#         subtype2 = ActivitySubType.objects.create(
#             id='incoming', name='Incoming', type=atype2,
#         )
#
#         clean = ActivityTypeField(types=ActivityType.objects.filter(pk=atype1.id)).clean
#         self.assertFieldValidationError(
#             ActivityTypeField, 'typenotallowed', clean,
#             self._build_value('unknown', self.subtype.id),
#         )
#         self.assertFieldValidationError(
#             ActivityTypeField, 'subtyperequired', clean,
#             self._build_value(atype1.id, 'unknown'),
#         )
#         self.assertFieldValidationError(
#             ActivityTypeField, 'typenotallowed', clean,
#             self._build_value(atype2.id, subtype2.id),
#         )
#         self.assertFieldValidationError(
#             ActivityTypeField, 'subtyperequired', clean,
#             self._build_value(atype1.id, subtype2.id),
#         )
#
#     def test_clean01(self):
#         atype = self.atype
#         subtype = self.subtype
#
#         with self.assertNumQueries(0):
#             field = ActivityTypeField(types=ActivityType.objects.filter(pk=atype.id))
#
#         self.assertTupleEqual(
#             (atype, subtype),
#             field.clean(self._build_value(atype.id, subtype.id)),
#         )
#
#     def test_clean02(self):
#         "Use 'types' setter."
#         atype = self.atype
#         subtype = self.subtype
#         field = ActivityTypeField()
#         field.types = ActivityType.objects.filter(pk=atype.id)
#         self.assertTupleEqual(
#             (atype, subtype),
#             field.clean(self._build_value(atype.id, subtype.id)),
#         )
#
#     def test_clean03(self):
#         "Not required."
#         atype = self.atype
#         field = ActivityTypeField(
#             types=ActivityType.objects.filter(pk=atype.id),
#             required=False,
#         )
#         self.assertFieldValidationError(
#             ActivityTypeField, 'subtyperequired', field.clean,
#             self._build_value(atype.id),
#         )
#
#     def test_clean04(self):
#         "No related ActivitySubType."
#         atype2 = ActivityType.objects.create(
#             id='custom', name='Custom',
#             default_day_duration=0,
#             default_hour_duration=1,
#         )
#         field = ActivityTypeField(
#             types=ActivityType.objects.filter(pk__in=[self.atype.id, atype2.id]),
#         )
#         self.assertFieldValidationError(
#             ActivityTypeField, 'subtyperequired', field.clean,
#             self._build_value(atype2.id),
#         )


class ActivitySubTypeFieldTestCase(FieldTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.atype = ActivityType.objects.create(
            id='meeting', name='Meeting',
            default_day_duration=0,
            default_hour_duration='01:00:00',
        )
        cls.subtype = ActivitySubType.objects.create(
            id='rendezvous', name='Rendez-vous', type=cls.atype,
        )

    def test_choices(self):
        field = ActivitySubTypeField()
        self.assertEqual(Activity._meta.get_field('sub_type'), field.enum.field)
        self.assertEqual(NO_LIMIT, field.limit)
        self.assertListEqual(
            sorted([
                ('', field.empty_label, None),
                *(
                    (c.pk, str(c), str(c.type))
                    for c in ActivitySubType.objects.all()
                ),
            ]),
            sorted((c.value, c.label, c.group) for c in field.choices),
        )

    def test_limit_choices_to(self):
        field = ActivitySubTypeField(
            model=Activity, field_name='sub_type',
            limit_choices_to=Q(type_id=constants.ACTIVITYTYPE_INDISPO)
        )

        self.assertEqual(field.limit, NO_LIMIT)
        self.assertListEqual(
            sorted([
                ('', field.empty_label, None),
                *(
                    (c.pk, str(c), str(c.type))
                    for c in ActivitySubType.objects.filter(
                        type_id=constants.ACTIVITYTYPE_INDISPO,
                    )
                ),
            ]),
            sorted((c.value, c.label, c.group) for c in field.choices),
        )

    def test_deepcopy(self):
        field = ActivitySubTypeField(
            model=Activity, field_name='sub_type',
            limit_choices_to=Q(type_id=constants.ACTIVITYTYPE_INDISPO)
        )

        field_copy = deepcopy(field)

        self.assertEqual(field_copy.limit, NO_LIMIT)
        self.assertEqual(
            field_copy.limit_choices_to,
            Q(type_id=constants.ACTIVITYTYPE_INDISPO)
        )

        self.assertListEqual(
            [(c.value, c.label, c.group) for c in field_copy.choices],
            [(c.value, c.label, c.group) for c in field.choices]
        )

    def test_clean(self):
        field = ActivitySubTypeField()

        self.assertEqual(self.subtype, field.clean(self.subtype.pk))
        with self.assertRaises(ValidationError):
            field.clean(None)

    def test_clean__not_required(self):
        field = ActivitySubTypeField(required=False)
        self.assertIsNone(field.clean(None))

    def test_clean__limit_choices_to(self):
        field = ActivitySubTypeField(
            limit_choices_to=Q(type_id=constants.ACTIVITYTYPE_INDISPO),
        )

        self.assertEqual(
            ActivitySubType.objects.get(pk=constants.ACTIVITYSUBTYPE_UNAVAILABILITY),
            field.clean(constants.ACTIVITYSUBTYPE_UNAVAILABILITY),
        )

        with self.assertRaises(ValidationError):
            field.clean(constants.ACTIVITYSUBTYPE_MEETING_MEETING)


class DateWithOptionalTimeFieldTestCase(FieldTestCase):
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

        # self.assertTupleEqual(
        #     (date(year=2020, month=12, day=8), time(hour=18, minute=44)),
        #     field.clean([self.formfield_value_date(2020, 12, 8), '18:44:00']),
        # )
        self.assertEqual(
            field.DateWithOptionalTime(
                date=date(year=2020, month=12, day=8),
                time=time(hour=18, minute=44),
            ),
            field.clean([self.formfield_value_date(2020, 12, 8), '18:44:00']),
        )

    def test_clean_empty_required(self):
        clean = DateWithOptionalTimeField(required=True).clean
        self.assertFieldValidationError(DateWithOptionalTimeField, 'required', clean, None)
        self.assertFieldValidationError(DateWithOptionalTimeField, 'required', clean, [])

    def test_clean_empty_not_required(self):
        field = DateWithOptionalTimeField(required=False)
        # self.assertTupleEqual((None, None), field.clean([]))
        self.assertIsNone(field.clean([]))
        self.assertIsNone(field.clean(['']))
        self.assertIsNone(field.clean(['', '']))

    def test_clean_only_date(self):
        field = DateWithOptionalTimeField()
        # self.assertTupleEqual(
        #     (date(year=2020, month=11, day=9), None),
        #     field.clean([self.formfield_value_date(2020, 11, 9)]),
        # )
        self.assertEqual(
            field.DateWithOptionalTime(date=date(year=2020, month=11, day=9)),
            field.clean([self.formfield_value_date(2020, 11, 9)]),
        )

    def test_required_property01(self):
        field = DateWithOptionalTimeField()
        field.required = False

        with self.assertNoException():
            res = field.clean([])

        # self.assertTupleEqual((None, None), res)
        self.assertIsNone(res)

    def test_required_property02(self):
        field = DateWithOptionalTimeField(required=False)
        field.required = True

        self.assertFieldValidationError(
            DateWithOptionalTimeField, 'required', field.clean, [],
        )

        with self.assertNoException():
            res = field.clean([self.formfield_value_date(2020, 11, 9)])

        # self.assertTupleEqual((date(year=2020, month=11, day=9), None), res)
        self.assertEqual(
            field.DateWithOptionalTime(date=date(year=2020, month=11, day=9)),
            res,
        )


class UserParticipationFieldTestCase(FieldTestCase):
    def test_clean_empty(self):
        user = self.get_root_user()
        field = UserParticipationField(user=user, required=False)
        # self.assertTupleEqual((False, None), field.clean([]))
        self.assertEqual(
            UserParticipationField.Option(is_set=False),
            field.clean([]),
        )

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_clean(self):
        # user = self.login(is_superuser=False, allowed_apps=('persons', 'activities'))
        user = self.login_as_standard(allowed_apps=('persons', 'activities'))

        SetCredentials.objects.create(
            role=user.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_ALL,
            ctype=type(user.linked_contact),
        )

        create_cal = Calendar.objects.create
        cal11 = create_cal(user=user, is_default=True,  name='Cal #11')
        cal12 = create_cal(user=user, is_default=False, name='Cal #12')
        cal2 = create_cal(
            # user=self.other_user, is_default=True, name='Cal #2', is_public=True,
            user=self.get_root_user(), is_default=True, name='Cal #2', is_public=True,
        )

        clean = UserParticipationField(user=user).clean
        Option = UserParticipationField.Option
        # self.assertTupleEqual((True, cal11), clean([True, cal11.id]))
        self.assertEqual(Option(is_set=True, data=cal11), clean([True, cal11.id]))
        # self.assertTupleEqual((True, cal12), clean([True, cal12.id]))
        self.assertEqual(Option(is_set=True, data=cal12), clean([True, cal12.id]))

        # ---
        with self.assertRaises(ValidationError) as cm:
            clean([True, cal2.id])

        self.assertEqual(
            [_('Select a valid choice. That choice is not one of the available choices.')],
            cm.exception.messages,
        )

        # ---
        self.assertFieldValidationError(
            UserParticipationField, 'subfield_required', clean, ['on', None],
        )

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_not_linkable(self):
        # user = self.login(is_superuser=False, allowed_apps=('persons', 'activities'))
        user = self.login_as_standard(allowed_apps=('persons', 'activities'))

        SetCredentials.objects.create(
            role=user.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_ALL,
        )

        cal = Calendar.objects.create(user=user, is_default=True, name='Cal #11')
        field = UserParticipationField(user=user)

        with self.assertRaises(ValidationError) as cm:
            field.clean([True, cal.id])

        self.assertEqual(
            [_('You are not allowed to link this entity: {}').format(user.linked_contact)],
            cm.exception.messages,
        )


class ParticipatingUsersFieldTestCase(FieldTestCase):
    def test_clean_empty(self):
        user = self.get_root_user()
        field = ParticipatingUsersField(user=user, required=False)
        self.assertFalse(field.clean([]))
        self.assertFalse(field.clean(None))

    def test_clean(self):
        # user = self.login(is_superuser=False, allowed_apps=('persons', 'activities'))
        user = self.login_as_standard(allowed_apps=('persons', 'activities'))

        SetCredentials.objects.create(
            role=user.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_ALL,
            ctype=type(user.linked_contact),
        )

        # other_user = self.other_user
        other_user = self.get_root_user()
        staff_user = self.create_user(index=2, is_staff=True)

        clean = ParticipatingUsersField(user=user).clean

        self.assertCountEqual(
            [user.linked_contact, other_user.linked_contact],
            clean([user.id, other_user.id]),
        )

        self.assertFieldValidationError(
            ParticipatingUsersField, 'invalid_choice', clean,
            [user.id, staff_user.id],
            message_args={'value': staff_user.id},
        )

    def test_clean_teamate(self):
        user1 = self.login_as_root_and_get()
        user2 = self.create_user(0)
        user3 = self.create_user(1)
        user4 = self.create_user(2)
        team = self.create_team('Samurais', user3, user4)

        field = ParticipatingUsersField(user=user1)
        self.assertCountEqual(
            [u.linked_contact for u in (user2, user3, user4)],
            field.clean([user2.id, team.id]),
        )

    def test_not_linkable(self):
        # user = self.login(is_superuser=False, allowed_apps=('persons', 'activities'))
        user = self.login_as_standard(allowed_apps=('persons', 'activities'))

        SetCredentials.objects.create(
            role=user.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_ALL,
        )

        field = ParticipatingUsersField(user=user)

        with self.assertRaises(ValidationError) as cm:
            field.clean([user.id])

        self.assertEqual(
            [_('Some entities are not linkable: {}').format(user.linked_contact)],
            cm.exception.messages,
        )
