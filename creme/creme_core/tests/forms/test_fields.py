# -*- coding: utf-8 -*-

from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.forms import BooleanField, ChoiceField, IntegerField
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.forms import widgets as core_widgets
from creme.creme_core.forms.fields import (
    ChoiceOrCharField,
    ColorField,
    CremeUserChoiceField,
    CTypeChoiceField,
    DatePeriodField,
    DateRangeField,
    DurationField,
    EnhancedChoiceIterator,
    EnhancedModelChoiceIterator,
    EnhancedModelMultipleChoiceField,
    EnhancedMultipleChoiceField,
    EntityCTypeChoiceField,
    MultiCTypeChoiceField,
    MultiEntityCTypeChoiceField,
    OptionalChoiceField,
    ReadonlyMessageField,
)
from creme.creme_core.models import (
    CremePropertyType,
    CremeUser,
    Currency,
    FakeContact,
    FakeOrganisation,
    FakeSector,
    RelationType,
)
from creme.creme_core.utils.date_period import (
    DatePeriod,
    DatePeriodRegistry,
    DaysPeriod,
    HoursPeriod,
    MinutesPeriod,
    date_period_registry,
)
from creme.creme_core.utils.date_range import (
    CurrentYearRange,
    CustomRange,
    DateRange,
)

from .base import FieldTestCase


class CremeUserChoiceFieldTestCase(FieldTestCase):
    def test_default(self):
        user = self.login()
        other_user = self.other_user
        staff = CremeUser.objects.create(username='deunan', is_staff=True)

        # Alphabetically-first user (__str__, not username)
        first_user = CremeUser.objects.create_user(
            username='noir', email='chloe@noir.jp',
            first_name='Chloe', last_name='Noir',
            password='uselesspw',
        )
        self.assertGreater(str(user), str(first_user))

        field = CremeUserChoiceField()
        self.assertIsNone(field.empty_label)
        self.assertIsNone(field.initial)
        self.assertIsNone(field.user)

        choices = [*field.choices]
        self.assertEqual(1, len(choices))

        active_group = choices[0]
        self.assertEqual('', active_group[0])

        active_choices = active_group[1]
        user_index = self.assertInChoices(
            value=user.id,
            label=str(user),
            choices=active_choices,
        )
        other_index = self.assertInChoices(
            value=other_user.id,
            label=str(other_user),
            choices=active_choices,
        )
        first_index = self.assertInChoices(
            value=first_user.id,
            label=str(first_user),
            choices=active_choices,
        )

        self.assertInChoices(
            value=staff.id,
            label=str(staff),
            choices=active_choices,
        )

        self.assertGreater(other_index, user_index)
        self.assertGreater(user_index,  first_index)

        # ---
        field.user = user
        self.assertEqual(user,    field.user)
        self.assertEqual(user.id, field.initial)

        # ---
        clean = field.clean
        self.assertEqual(user,       clean(str(user.id)))
        self.assertEqual(other_user, clean(str(other_user.id)))

    def test_queryset(self):
        user = self.login()
        other_user = self.other_user
        staff = CremeUser.objects.create(username='deunan', is_staff=True)

        field = CremeUserChoiceField(queryset=CremeUser.objects.exclude(is_staff=True))

        choices = [*field.choices]
        self.assertEqual(1, len(choices))

        active_group = choices[0]
        self.assertEqual('', active_group[0])

        active_choices = active_group[1]
        self.assertInChoices(value=user.id,       label=str(user),       choices=active_choices)
        self.assertInChoices(value=other_user.id, label=str(other_user), choices=active_choices)
        self.assertNotInChoices(value=staff.id, choices=active_choices)

    def test_initial(self):
        self.login()
        other_id = self.other_user.id

        field = CremeUserChoiceField(initial=other_id)
        self.assertEqual(other_id, field.initial)

    def test_inactive_users(self):
        user = self.login()
        other_user = self.other_user

        create_inactive_user = partial(CremeUser.objects.create, is_active=False)
        inactive1 = create_inactive_user(
            username='deunan', first_name='Deunan', last_name='Knut',
        )
        inactive2 = create_inactive_user(
            username='heca', first_name='Briareos', last_name='Hecatonchire',
        )
        self.assertGreater(inactive2.username, inactive1.username)
        self.assertLess(str(inactive2), str(inactive1))

        field = CremeUserChoiceField()

        choices = [*field.choices]
        self.assertEqual(2, len(choices))

        active_group = choices[0]
        self.assertEqual('', active_group[0])

        active_choices = active_group[1]
        self.assertInChoices(value=user.id,       label=str(user),       choices=active_choices)
        self.assertInChoices(value=other_user.id, label=str(other_user), choices=active_choices)
        self.assertNotInChoices(value=inactive1.id, choices=active_choices)

        inactive_group = choices[1]
        self.assertEqual(_('Inactive users'), inactive_group[0])
        self.assertListEqual(
            [
                (inactive2.id, str(inactive2)),
                (inactive1.id, str(inactive1)),
            ],
            inactive_group[1],
        )

    def test_teams(self):
        user = self.login()
        other_user = self.other_user

        team_name = 'Team#1'
        team = CremeUser.objects.create(username=team_name, is_team=True)
        team.teammates = [user, self.other_user]

        field = CremeUserChoiceField()

        choices = [*field.choices]
        self.assertEqual(2, len(choices))

        active_group = choices[0]
        self.assertEqual('', active_group[0])

        active_choices = active_group[1]
        self.assertInChoices(value=user.id,       label=str(user),       choices=active_choices)
        self.assertInChoices(value=other_user.id, label=str(other_user), choices=active_choices)
        self.assertNotInChoices(value=team.id, choices=active_choices)

        team_group = choices[1]
        self.assertEqual(_('Teams'), team_group[0])
        self.assertListEqual([(team.id, team_name)], team_group[1])


class DatePeriodFieldTestCase(FieldTestCase):
    def test_ok01(self):
        "Days."
        period = DatePeriodField().clean(['days', '3'])
        self.assertIsInstance(period, DatePeriod)

        create_dt = self.create_datetime
        self.assertEqual(
            create_dt(year=2014, month=7, day=5, hour=22, minute=9),
            create_dt(year=2014, month=7, day=2, hour=22, minute=9)
            + period.as_timedelta()
        )

    def test_ok02(self):
        "Minutes."
        period = DatePeriodField().clean(['minutes', '5'])
        self.assertIsInstance(period, DatePeriod)

        create_dt = self.create_datetime
        self.assertEqual(
            create_dt(year=2014, month=7, day=2, hour=22, minute=14),
            create_dt(year=2014, month=7, day=2, hour=22, minute=9)
            + period.as_timedelta()
        )

    def test_required(self):
        clean = DatePeriodField().clean
        self.assertFieldValidationError(DatePeriodField, 'required', clean, ['', ''])
        self.assertFieldValidationError(DatePeriodField, 'required', clean, None)

    def test_not_required(self):
        clean = DatePeriodField(required=False).clean
        self.assertIsNone(clean(['', '']))
        self.assertIsNone(clean(['']))
        self.assertIsNone(clean([]))
        self.assertIsNone(clean(['days', '']))
        self.assertIsNone(clean(['days']))
        self.assertIsNone(clean(['', 2]))

    def test_empty(self):
        self.assertIsNone(DatePeriodField(required=False).clean(None))

    def test_invalid(self):
        clean = DatePeriodField().clean
        self.assertFieldValidationError(
            IntegerField, 'invalid', clean, ['years', 'notint'],
        )

        name = 'unknownperiod'
        self.assertFieldValidationError(
            ChoiceField, 'invalid_choice', clean, [name, '2'],
            message_args={'value': name},
        )

    def test_choices(self):
        choices = [*DatePeriodField().choices]
        self.assertInChoices(
            value=MinutesPeriod.name, label=MinutesPeriod.verbose_name, choices=choices,
        )
        self.assertInChoices(
            value=HoursPeriod.name, label=HoursPeriod.verbose_name, choices=choices,
        )
        self.assertInChoices(
            value=DaysPeriod.name, label=DaysPeriod.verbose_name, choices=choices,
        )

    def test_period_names(self):
        clean = DatePeriodField(period_names=('months',)).clean
        period = clean(['months', '5'])
        self.assertIsInstance(period, DatePeriod)

        name = 'years'
        self.assertFieldValidationError(
            ChoiceField, 'invalid_choice', clean, [name, '2'],
            message_args={'value': name},
        )

    def test_notnull(self):
        with self.assertRaises(ValidationError) as cm:
            DatePeriodField().clean(['days', '0'])

        self.assertListEqual(
            [
                _('Ensure this value is greater than or equal to %(limit_value)s.') % {
                    'limit_value': 1,
                },
            ],
            cm.exception.messages,
        )

    def test_registry_1(self):
        self.assertListEqual(
            [*date_period_registry.choices()],
            [*DatePeriodField().choices],
        )

    def test_registry_2(self):
        registry = DatePeriodRegistry(MinutesPeriod, HoursPeriod)
        self.assertListEqual(
            [*registry.choices()],
            [*DatePeriodField(period_registry=registry).choices]
        )

    def test_registry_3(self):
        registry = DatePeriodRegistry(MinutesPeriod, HoursPeriod)
        field = DatePeriodField()
        field.period_registry = registry
        self.assertListEqual([*registry.choices()], [*field.choices])

    def test_period_names_1(self):
        names = (MinutesPeriod.name, HoursPeriod.name)
        self.assertListEqual(
            [*date_period_registry.choices(choices=names)],
            [*DatePeriodField(period_names=names).choices],
        )

    def test_period_names_2(self):
        field = DatePeriodField()
        field.period_names = names = (MinutesPeriod.name, HoursPeriod.name)
        self.assertListEqual(
            [*date_period_registry.choices(choices=names)],
            [*field.choices],
        )


class DateRangeFieldTestCase(FieldTestCase):
    def test_clean_empty_customized(self):
        clean = DateRangeField().clean
        self.assertFieldValidationError(DateRangeField, 'required', clean, ['', '', ''])
        self.assertFieldValidationError(DateRangeField, 'required', clean, None)

    def test_start_before_end(self):
        self.assertFieldValidationError(
            DateRangeField, 'customized_invalid',
            DateRangeField().clean, ['', '2011-05-16', '2011-05-15'],
        )

    def test_ok01(self):
        drange = DateRangeField().clean(['', '2013-05-29', '2013-06-16'])
        dt = self.create_datetime
        self.assertIsInstance(drange, DateRange)
        self.assertIsInstance(drange, CustomRange)
        self.assertTupleEqual(
            (
                dt(year=2013, month=5, day=29, hour=0,  minute=0,  second=0),
                dt(year=2013, month=6, day=16, hour=23, minute=59, second=59),
            ),
            drange.get_dates(now()),
        )

    def test_ok02(self):
        drange = DateRangeField().clean([CurrentYearRange.name, '', ''])
        dt = self.create_datetime
        self.assertIsInstance(drange, CurrentYearRange)
        self.assertTupleEqual(
            (
                dt(year=2013, month=1, day=1,   hour=0,  minute=0,  second=0),
                dt(year=2013, month=12, day=31, hour=23, minute=59, second=59),
            ),
            drange.get_dates(dt(year=2013, month=5, day=29, hour=11)),
        )

    def test_ok03(self):
        drange = DateRangeField(required=False).clean(['', '', ''])
        self.assertIsNone(drange)


class ColorFieldTestCase(FieldTestCase):
    def test_empty01(self):
        clean = ColorField().clean
        self.assertFieldValidationError(ColorField, 'required', clean, None)
        self.assertFieldValidationError(ColorField, 'required', clean, '')
        self.assertFieldValidationError(ColorField, 'required', clean, [])

    def test_length01(self):
        clean = ColorField().clean
        self.assertFieldRaises(ValidationError, clean, '1')
        self.assertFieldRaises(ValidationError, clean, '12')
        self.assertFieldRaises(ValidationError, clean, '123')
        self.assertFieldRaises(ValidationError, clean, '1234')
        self.assertFieldRaises(ValidationError, clean, '12345')

    def test_invalid_value01(self):
        clean = ColorField().clean
        self.assertFieldValidationError(ColorField, 'invalid', clean, 'GGGGGG')
        self.assertFieldValidationError(ColorField, 'invalid', clean, '------')

    def test_ok01(self):
        clean = ColorField().clean
        self.assertEqual('AAAAAA', clean('AAAAAA'))
        self.assertEqual('AAAAAA', clean('aaaaaa'))
        self.assertEqual('123456', clean('123456'))
        self.assertEqual('123ABC', clean('123ABC'))
        self.assertEqual('123ABC', clean('123abc'))


class DurationFieldTestCase(FieldTestCase):
    def test_empty01(self):
        clean = DurationField().clean
        self.assertFieldValidationError(DurationField, 'required', clean, None)
        self.assertFieldValidationError(DurationField, 'required', clean, '')
        self.assertFieldValidationError(DurationField, 'required', clean, [])

    def test_invalid01(self):
        self.assertFieldValidationError(
            DurationField, 'invalid', DurationField().clean, ['a', 'b', 'c'],
        )

    def test_positive01(self):
        self.assertFieldValidationError(
            DurationField, 'min_value', DurationField().clean,
            ['-1', '-1', '-1'], message_args={'limit_value': 0},
        )

    def test_ok01(self):
        clean = DurationField().clean
        self.assertEqual('10:2:0', clean(['10', '2', '0']))
        self.assertEqual('10:2:0', clean([10, 2, 0]))


class OptionalChoiceFieldTestCase(FieldTestCase):
    _team = ['Naruto', 'Sakura', 'Sasuke', 'Kakashi']

    def test_sub_fields(self):
        choices = [*enumerate(self._team, start=1)]
        field = OptionalChoiceField(choices=choices)

        sub_fields = field.fields
        self.assertIsInstance(sub_fields, tuple)
        self.assertEqual(2, len(sub_fields))

        sub_field1 = sub_fields[0]
        self.assertIsInstance(sub_field1, BooleanField)
        self.assertFalse(sub_field1.required)
        self.assertFalse(sub_field1.disabled)

        sub_field2 = sub_fields[1]
        self.assertIsInstance(sub_field2, ChoiceField)
        self.assertListEqual(choices, sub_field2.choices)
        self.assertTrue(sub_field2.required)
        self.assertFalse(sub_field2.disabled)

    def test_ok_choice(self):
        field = OptionalChoiceField(choices=enumerate(self._team, start=1))
        self.assertEqual((True, '1'), field.clean([True, 1]))

    def test_not_required(self):
        field = OptionalChoiceField(
            choices=enumerate(self._team, start=1), required=False,
        )
        expected = (False, None)
        self.assertEqual(expected, field.clean([False, '']))
        self.assertEqual(expected, field.clean([False, 1]))
        self.assertEqual(expected, field.clean([False, None]))
        self.assertEqual(expected, field.clean([False]))
        self.assertEqual(expected, field.clean([]))

    def test_required(self):
        clean = OptionalChoiceField(
            choices=enumerate(self._team, start=1), required=True,
        ).clean

        expected = (False, None)
        self.assertEqual(expected, clean([False, None]))
        self.assertEqual(expected, clean([False]))
        self.assertEqual(expected, clean([]))

        self.assertFieldValidationError(
            OptionalChoiceField, 'subfield_required', clean, [True, None],
        )
        self.assertFieldValidationError(
            OptionalChoiceField, 'subfield_required', clean, [True],
        )

    def test_invalid(self):
        field = OptionalChoiceField(choices=enumerate(self._team, start=1))

        with self.assertRaises(ValidationError) as cm:
            field.clean([False, 'invalid'])

        self.assertListEqual(
            [
                _('Select a valid choice. %(value)s is not one of the available choices.') % {
                    'value': 'invalid',
                },
            ],
            cm.exception.messages,
        )

    def test_disabled(self):
        field = OptionalChoiceField(choices=enumerate(self._team, start=1), disabled=True)
        self.assertTrue(field.disabled)

        sub_fields = field.fields
        self.assertTrue(sub_fields[0].disabled)
        self.assertTrue(sub_fields[1].disabled)

        # ---
        field.disabled = False
        self.assertFalse(field.disabled)
        self.assertFalse(field.fields[0].disabled)


class ChoiceOrCharFieldTestCase(FieldTestCase):
    _team = ['Naruto', 'Sakura', 'Sasuke', 'Kakashi']

    def test_empty_required(self):
        clean = ChoiceOrCharField(choices=enumerate(self._team, start=1)).clean
        self.assertFieldValidationError(ChoiceOrCharField, 'required', clean, None)
        self.assertFieldValidationError(ChoiceOrCharField, 'required', clean, '')
        self.assertFieldValidationError(ChoiceOrCharField, 'required', clean, [])

    def test_empty_other(self):
        field = ChoiceOrCharField(choices=enumerate(self._team, start=1))
        self.assertFieldValidationError(ChoiceOrCharField, 'invalid_other', field.clean, [0, ''])

    def test_ok_choice(self):
        field = ChoiceOrCharField(choices=enumerate(self._team, start=1))
        self.assertEqual((1, 'Naruto'), field.clean([1, '']))

    def test_ok_other(self):
        field = ChoiceOrCharField(choices=enumerate(self._team, start=1))

        with self.assertNoException():
            choices = field.choices

        self.assertInChoices(value=0, label=_('Other'), choices=choices)

        other = 'Shikamaru'
        self.assertEqual((0, other), field.clean([0, other]))

    def test_empty_ok(self):
        field = ChoiceOrCharField(
            choices=enumerate(self._team, start=1),
            required=False,
        )

        with self.assertNoException():
            cleaned = field.clean(['', ''])

        self.assertEqual((None, None), cleaned)

    # TODO: set 'Other' label


class _CTypeChoiceFieldTestCase(FieldTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        get_ct = ContentType.objects.get_for_model
        cls.ct1 = get_ct(RelationType)
        cls.ct2 = get_ct(CremePropertyType)
        cls.ct3 = get_ct(Currency)


class CTypeChoiceFieldTestCase(_CTypeChoiceFieldTestCase):
    def test_required(self):
        ct1 = self.ct1
        ct2 = self.ct2
        field = CTypeChoiceField(ctypes=[ct1, ct2])
        clean = field.clean

        self.assertListEqual(
            sorted(
                [
                    (ct1.pk, str(ct1)),
                    (ct2.pk, str(ct2)),
                ],
                key=lambda ct: ct[1],
            ),
            [*field.widget.choices],
        )

        self.assertEqual(ct1, clean(ct1.id))
        self.assertEqual(ct2, clean(ct2.id))
        self.assertFieldValidationError(CTypeChoiceField, 'required', clean, '')

    def test_not_required(self):
        ct1 = self.ct1
        ct2 = self.ct2
        field = CTypeChoiceField(ctypes=[ct1, ct2], required=False)
        clean = field.clean

        self.assertListEqual(
            [
                ('', field.empty_label),
                *sorted(
                    [(ct1.pk, str(ct1)), (ct2.pk, str(ct2))],
                    key=lambda ct: ct[1],
                ),
            ],
            [*field.widget.choices],
        )

        self.assertEqual(ct1, clean(ct1.id))
        self.assertEqual(ct2, clean(ct2.id))
        self.assertEqual(None, clean(''))

    def test_invalid(self):
        clean = CTypeChoiceField(ctypes=[self.ct1, self.ct2]).clean
        self.assertFieldValidationError(
            CTypeChoiceField, 'invalid_choice', clean, self.ct3.id,
        )

    def test_prepare_value(self):
        ct1 = self.ct1
        ct2 = self.ct2
        prepare_value = CTypeChoiceField(ctypes=[ct1, ct2]).prepare_value
        self.assertIsNone(prepare_value(None))

        self.assertEqual(ct1.id, prepare_value(ct1.id))
        self.assertEqual(ct2.id, prepare_value(ct2.id))

        self.assertEqual(ct1.id, prepare_value(ct1))
        self.assertEqual(ct2.id, prepare_value(ct2))


class _EntityCTypeChoiceFieldTestCase(FieldTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        get_ct = ContentType.objects.get_for_model
        cls.ct1 = get_ct(FakeContact)
        cls.ct2 = get_ct(FakeOrganisation)
        cls.ct3 = get_ct(Currency)


class EntityCTypeChoiceFieldTestCase(_EntityCTypeChoiceFieldTestCase):
    def test_required(self):
        ct1 = self.ct1
        ct2 = self.ct2
        clean = EntityCTypeChoiceField().clean
        self.assertEqual(ct1, clean(ct1.id))
        self.assertEqual(ct2, clean(ct2.id))
        self.assertFieldValidationError(EntityCTypeChoiceField, 'required', clean, '')

    def test_not_required(self):
        ct1 = self.ct1
        ct2 = self.ct2
        clean = EntityCTypeChoiceField(required=False).clean
        self.assertEqual(ct1, clean(ct1.id))
        self.assertEqual(ct2, clean(ct2.id))
        self.assertEqual(None, clean(''))

    def test_invalid(self):
        self.assertFieldValidationError(
            EntityCTypeChoiceField, 'invalid_choice',
            EntityCTypeChoiceField().clean, self.ct3.id,
        )

    def test_ctypes01(self):
        "Constructor."
        ct1 = self.ct1

        with self.assertNumQueries(0):
            field = EntityCTypeChoiceField(ctypes=[ct1])

        clean = field.clean
        self.assertEqual(ct1, clean(ct1.id))
        self.assertFieldValidationError(
            EntityCTypeChoiceField, 'invalid_choice', clean, self.ct2.id,
        )

    def test_ctypes02(self):
        "Setter."
        ct1 = self.ct1
        field = EntityCTypeChoiceField()
        field.ctypes = [ct1]

        clean = field.clean
        self.assertEqual(ct1, clean(ct1.id))
        self.assertFieldValidationError(
            EntityCTypeChoiceField, 'invalid_choice', clean, self.ct2.id,
        )

    def test_ctypes03(self):
        "All accepted."
        ContentType.objects.clear_cache()

        with self.assertNumQueries(0):
            field = EntityCTypeChoiceField()

        ct1 = self.ct1
        self.assertEqual(ct1, field.clean(ct1.id))


class MultiCTypeChoiceFieldTestCase(_CTypeChoiceFieldTestCase):
    def test_required(self):
        ct1 = self.ct1
        ct2 = self.ct2
        field = MultiCTypeChoiceField(ctypes=[ct1, ct2])
        clean = field.clean

        self.assertEqual(
            sorted(
                [
                    (ct1.pk, str(ct1)),
                    (ct2.pk, str(ct2)),
                ],
                key=lambda ct: ct[1],
            ),
            [(choice.value, label) for choice, label in field.widget.choices],
        )

        self.assertEqual([ct1], clean([ct1.id]))
        self.assertEqual([ct2], clean([ct2.id]))
        self.assertFieldValidationError(MultiCTypeChoiceField, 'required', clean, '')
        self.assertFieldValidationError(MultiCTypeChoiceField, 'required', clean, [])
        self.assertFieldValidationError(MultiCTypeChoiceField, 'required', clean, None)

    def test_not_required(self):
        ct1 = self.ct1
        ct2 = self.ct2
        field = MultiCTypeChoiceField(ctypes=[ct1, ct2], required=False)
        clean = field.clean

        self.assertListEqual(
            sorted(
                [(ct1.pk, str(ct1)), (ct2.pk, str(ct2))],
                key=lambda ct: ct[1],
            ),
            [(choice.value, label) for choice, label in field.widget.choices],
        )

        self.assertListEqual([ct1], clean([ct1.id]))
        self.assertListEqual([ct2], clean([ct2.id]))
        self.assertListEqual([],    clean(''))
        self.assertListEqual([],    clean([]))

    def test_invalid(self):
        ct1 = self.ct1
        clean = MultiCTypeChoiceField(ctypes=[ct1, self.ct2]).clean
        self.assertFieldValidationError(
            MultiCTypeChoiceField, 'invalid_choice',
            clean, [ct1.id, self.ct3.id],
        )
        self.assertFieldValidationError(
            MultiCTypeChoiceField, 'invalid_choice',
            clean, ['not an int'],
        )

    def test_prepare_value(self):
        ct1 = self.ct1
        ct2 = self.ct2
        prepare_value = MultiCTypeChoiceField(ctypes=[ct1, ct2]).prepare_value
        self.assertIsNone(prepare_value(None))

        # TODO ?
        # self.assertEqual(ct1.id, prepare_value(ct1.id))
        # self.assertEqual(ct2.id, prepare_value(ct2.id))

        self.assertEqual([ct1.id, ct2.id], prepare_value([ct1.id, ct2.id]))
        self.assertEqual([ct1.id, ct2.id], prepare_value([ct1, ct2]))


class MultiEntityCTypeChoiceFieldTestCase(_EntityCTypeChoiceFieldTestCase):
    def test_required(self):
        ct1 = self.ct1
        ct2 = self.ct2

        ContentType.objects.clear_cache()

        with self.assertNumQueries(0):
            field = MultiEntityCTypeChoiceField()

        clean = field.clean
        self.assertEqual([ct1], clean([ct1.id]))
        self.assertEqual([ct2], clean([ct2.id]))
        self.assertFieldValidationError(MultiEntityCTypeChoiceField, 'required', clean, '')
        self.assertFieldValidationError(MultiEntityCTypeChoiceField, 'required', clean, [])
        self.assertFieldValidationError(MultiEntityCTypeChoiceField, 'required', clean, None)

    def test_not_required(self):
        ct1 = self.ct1
        ct2 = self.ct2
        clean = MultiEntityCTypeChoiceField(ctypes=[ct1, ct2], required=False).clean

        self.assertListEqual([ct1], clean([ct1.id]))
        self.assertListEqual([ct2], clean([ct2.id]))
        self.assertListEqual([],    clean(''))
        self.assertListEqual([],    clean([]))

    def test_invalid(self):
        clean = MultiEntityCTypeChoiceField().clean
        self.assertFieldValidationError(
            MultiEntityCTypeChoiceField, 'invalid_choice',
            clean, [self.ct1.id, self.ct3.id],
        )
        self.assertFieldValidationError(
            MultiEntityCTypeChoiceField, 'invalid_choice',
            clean, ['not an int'],
        )

    def test_ctypes(self):
        ct1 = self.ct1
        clean = MultiEntityCTypeChoiceField(ctypes=[ct1]).clean
        self.assertEqual([ct1], clean([ct1.id]))
        self.assertFieldValidationError(
            MultiEntityCTypeChoiceField,
            'invalid_choice', clean, [self.ct2.id],
        )


class EnhancedMultipleChoiceFieldTestCase(FieldTestCase):
    def test_required(self):
        choices = [
            (1, 'Sword'),
            (2, 'Axes'),
            (3, 'Spear'),
        ]
        field = EnhancedMultipleChoiceField(choices=choices)
        self.assertTrue(field.required)
        self.assertIsInstance(field.widget, core_widgets.UnorderedMultipleChoiceWidget)
        self.assertSetEqual(set(), field.initial)

        clean = field.clean
        self.assertSetEqual({'1', '3'}, {*clean([1, 3])})
        self.assertSetEqual({'1', '3'}, {*clean(['1', '3'])})

        # NB: we need a 0-argument constructor
        field_builder = partial(EnhancedMultipleChoiceField, choices=choices)
        self.assertFieldValidationError(field_builder, 'required', clean, '')
        self.assertFieldValidationError(field_builder, 'required', clean, [])
        self.assertFieldValidationError(field_builder, 'required', clean, None)

    def test_not_required(self):
        field = EnhancedMultipleChoiceField(
            choices=[
                (1, 'Sword'),
                (2, 'Axes'),
                (3, 'Spear'),
            ],
            required=False,
        )

        clean = field.clean
        self.assertListEqual(['2'], [*clean(['2'])])
        self.assertFalse([], clean(''))
        self.assertFalse([], clean([]))

    def test_invalid(self):
        choices = [
            (1, 'Sword'),
            (2, 'Axes'),
            (3, 'Spear'),
        ]
        field_builder = partial(EnhancedMultipleChoiceField, choices=choices)
        field = field_builder()

        self.assertFieldValidationError(
            field_builder, 'invalid_choice', field.clean, [str(4)],
            message_args={'value': 4},
        )

    def test_choices01(self):
        "From tuples."
        field = EnhancedMultipleChoiceField(
            choices=[
                (1, 'Sword'),
                (2, 'Axes'),
                (3, 'Spear'),
            ],
        )

        choices = [*field.choices]
        choice1 = choices[0]
        id1, label1 = choice1
        self.assertEqual('Sword', label1)
        self.assertEqual(1,       id1.value)
        self.assertEqual('',      id1.help)
        self.assertFalse(id1.readonly)

        choice2 = choices[1]
        id2, label2 = choice2
        self.assertEqual('Axes', label2)
        self.assertEqual(2,      id2.value)

        wchoice = [*field.widget.choices][0]
        self.assertEqual('Sword', wchoice[1])
        self.assertEqual(1,       wchoice[0].value)

        self.assertFalse(field.forced_values)

    def test_choices02(self):
        "Callable."
        def _choices():
            return [
                (1, 'Sword'),
                (2, 'Axes'),
                (3, 'Spear'),
            ]

        field = EnhancedMultipleChoiceField(choices=_choices)

        choices = [*field.choices]
        choice1 = choices[0]
        id1, label1 = choice1
        self.assertEqual('Sword', label1)
        self.assertEqual(1,       id1.value)
        self.assertEqual('',      id1.help)

        choice2 = choices[1]
        id2, label2 = choice2
        self.assertEqual('Axes', label2)
        self.assertEqual(2,      id2.value)

        wchoice = [*field.widget.choices][0]
        self.assertEqual('Sword', wchoice[1])
        self.assertEqual(1,       wchoice[0].value)

    def test_choices03(self):
        """From dict."""
        help_text = 'Stronger than word'
        field = EnhancedMultipleChoiceField(
            choices=[
                {'value': 1, 'label': 'Sword'},
                {'value': 2, 'label': 'Axes', 'help': help_text},
                {'value': 3, 'label': 'Spear', 'disabled': True},
            ],
        )

        choices = [*field.choices]
        choice1 = choices[0]
        id1, label1 = choice1
        self.assertEqual('Sword', label1)
        self.assertEqual(1,  id1.value)
        self.assertEqual('', id1.help)
        self.assertIs(id1.disabled, False)

        choice2 = choices[1]
        id2, label2 = choice2
        self.assertEqual('Axes', label2)
        self.assertEqual(2, id2.value)
        self.assertEqual(help_text, id2.help)

        id3, label3 = choices[2]
        self.assertEqual('Spear', label3)
        self.assertEqual(3, id3.value)
        self.assertIs(id3.disabled, True)

        wchoice2 = [*field.widget.choices][1]
        self.assertEqual('Axes', wchoice2[1])
        wid2 = wchoice2[0]
        self.assertEqual(2, wid2.value)
        self.assertEqual(help_text, wid2.help)

    def test_choices04(self):
        """Dict + callable."""
        help_text = 'Stronger than word'

        def _choices():
            return [
                {'value': 1, 'label': 'Sword'},
                {'value': 2, 'label': 'Axes', 'help': help_text},
                {'value': 3, 'label': 'Spear'},
            ]

        field = EnhancedMultipleChoiceField(choices=_choices)

        choices = [*field.choices]
        choice1 = choices[0]
        id1, label1 = choice1
        self.assertEqual('Sword', label1)
        self.assertEqual(1,       id1.value)
        self.assertEqual('',      id1.help)
        self.assertEqual(False,   id1.readonly)

        choice2 = choices[1]
        id2, label2 = choice2
        self.assertEqual('Axes',    label2)
        self.assertEqual(2,         id2.value)
        self.assertEqual(help_text, id2.help)

        wchoice2 = [*field.widget.choices][1]
        self.assertEqual('Axes', wchoice2[1])
        wid2 = wchoice2[0]
        self.assertEqual(2,    wid2.value)
        self.assertEqual(help_text, wid2.help)

    def test_forced_values01(self):
        "Tuple choices."
        field_builder = partial(
            EnhancedMultipleChoiceField,
            choices=[
                (1, 'Sword'),
                (2, 'Axes'),
                (3, 'Spear'),
            ],
            required=False,
        )
        field1 = field_builder()
        self.assertEqual(frozenset(), field1.forced_values)
        self.assertFalse(field1.initial)
        wchoices1 = iter(field1.choices)
        old_wchoices1 = iter(field1.widget.choices)

        field1.forced_values = [1, 3]
        self.assertEqual(frozenset([1, 3]), field1.forced_values)  # TODO: '1', '3' ???
        self.assertSetEqual({1, 3}, field1.initial)

        self.assertFalse(next(wchoices1)[0].readonly)

        # --
        choices1 = [*field1.choices]
        choice1 = choices1[0]
        id1, label1 = choice1
        self.assertEqual('Sword', label1)
        self.assertEqual(1,       id1.value)
        self.assertEqual('',      id1.help)
        self.assertTrue(id1.readonly)

        self.assertFalse(choices1[1][0].readonly)
        self.assertTrue(choices1[2][0].readonly)

        self.assertFalse(next(old_wchoices1)[0].readonly)
        self.assertTrue(next(iter(field1.widget.choices))[0].readonly)

        # --
        field2 = field_builder(forced_values=[2])
        self.assertEqual(frozenset([2]), field2.forced_values)
        self.assertSetEqual({2}, field2.initial)

        clean = field2.clean
        expected = ['1', '2']
        self.assertCountEqual(expected, clean(['1', '2']))
        self.assertCountEqual(expected, clean(['1']))

    def test_forced_values02(self):
        "Dict + callable."
        def _choices():
            return [
                {'value': 1, 'label': 'Sword'},
                {'value': 2, 'label': 'Axes'},
                {'value': 3, 'label': 'Spear'},
                {'value': 4, 'label': 'Bow'},
            ]

        field = EnhancedMultipleChoiceField(choices=_choices)

        field.forced_values = [2, 3]
        self.assertEqual(frozenset([2, 3]), field.forced_values)
        self.assertSetEqual({2, 3}, field.initial)

        choices = [*field.choices]
        self.assertFalse(choices[0][0].readonly)
        self.assertTrue(choices[1][0].readonly)

        self.assertCountEqual(['1', '2', '3'], field.clean(['1', '2']))

    def test_initial(self):
        field = EnhancedMultipleChoiceField(choices=[
            (1, 'Sword'),
            (2, 'Axes'),
            (3, 'Spear'),
        ])

        field.initial = [2, 1]
        self.assertSetEqual({1, 2}, field.initial)

        field.initial = None
        self.assertFalse(field.initial)

        field.forced_values = [1]
        field.initial = [2]
        self.assertSetEqual({1, 2}, field.initial)

    def test_iterator(self):
        class CustomIterator(EnhancedChoiceIterator):
            def __iter__(self):
                for x in self.choices:
                    label = x[1]

                    yield (
                        self.choice_cls(
                            value=x[0],
                            help=f'The "{label}" weapon',
                        ),
                        label,
                    )

        field = EnhancedMultipleChoiceField(
            choices=[(1, 'Sword'), (2, 'Axes')],
            iterator=CustomIterator,
        )

        choice = [*field.choices][0]
        self.assertEqual('The "Sword" weapon', choice[0].help)


class EnhancedModelMultipleChoiceFieldTestCase(FieldTestCase):
    def assertFoundChoice(self, pk, label, choices):
        for choice in choices:
            id_obj = choice[0]

            if id_obj.value == pk:
                if choice[1] != label:
                    self.fail(
                        f'Choice with pk="{pk}" found with '
                        f'label "{choice[1]}" != "{label}"'
                    )

                return id_obj

        self.fail(f'Choice with pk="{pk}" not found')

    def test_required(self):
        field = EnhancedModelMultipleChoiceField(queryset=FakeSector.objects.all())
        self.assertTrue(field.required)
        self.assertIsInstance(field.widget, core_widgets.UnorderedMultipleChoiceWidget)
        self.assertSetEqual(set(), field.initial)

        sectors = [*FakeSector.objects.all()]
        self.assertGreaterEqual(len(sectors), 3)

        sector1 = sectors[0]
        sector2 = sectors[1]
        sector3 = sectors[2]

        choices = [*field.choices]
        choice1 = self.assertFoundChoice(sector1.id, sector1.title, choices)
        self.assertFalse(choice1.readonly)
        self.assertFalse(choice1.help)

        self.assertFoundChoice(sector2.id, sector2.title, choices)

        clean = field.clean
        self.assertSetEqual({sector1, sector3}, {*clean([sector1.id, sector3.id])})
        self.assertSetEqual({sector1, sector3}, {*clean([str(sector1.id), str(sector3.id)])})

        # NB: we need a 0-argument constructor
        field_builder = partial(
            EnhancedModelMultipleChoiceField, queryset=FakeSector.objects.all(),
        )
        self.assertFieldValidationError(field_builder, 'required', clean, '')
        self.assertFieldValidationError(field_builder, 'required', clean, [])
        self.assertFieldValidationError(field_builder, 'required', clean, None)

    def test_not_required(self):
        field = EnhancedModelMultipleChoiceField(
            queryset=FakeSector.objects.all(), required=False,
        )

        sector = FakeSector.objects.first()
        self.assertIsNotNone(sector)

        clean = field.clean
        self.assertListEqual([sector], [*clean([sector.id])])
        self.assertFalse(clean(''))
        self.assertFalse(clean([]))

    def test_invalid(self):
        field_builder = partial(
            EnhancedModelMultipleChoiceField, queryset=FakeSector.objects.all(),
        )
        field = field_builder()

        invalid_pk = self.UNUSED_PK
        self.assertFalse(FakeSector.objects.filter(pk=invalid_pk))

        self.assertFieldValidationError(
            field_builder, 'invalid_choice', field.clean, [str(invalid_pk)],
            message_args={'value': invalid_pk},
        )

    def test_forced_values01(self):
        field_builder = partial(
            EnhancedModelMultipleChoiceField,
            queryset=FakeSector.objects.all(),
            required=False,
        )
        field1 = field_builder()
        self.assertEqual(frozenset(), field1.forced_values)
        self.assertFalse(field1.initial)

        sectors = [*FakeSector.objects.all()]
        self.assertGreaterEqual(len(sectors), 3)

        sector1, sector2, sector3 = sectors[:3]

        field1.forced_values = [sector1.id, sector3.id]
        self.assertEqual(frozenset([sector1.id, sector3.id]), field1.forced_values)
        self.assertSetEqual({sector1.id, sector3.id}, field1.initial)

        # --
        choices = [*field1.choices]
        choice1 = self.assertFoundChoice(sector1.id, sector1.title, choices)
        self.assertTrue(choice1.readonly)

        choice2 = self.assertFoundChoice(sector2.id, sector2.title, choices)
        self.assertFalse(choice2.readonly)

        # --
        field2 = field_builder(forced_values=[sector2.id])
        self.assertEqual(frozenset([sector2.id]), field2.forced_values)

        clean = field2.clean
        expected = {sector1, sector2}
        self.assertSetEqual(expected, {*clean([sector1.id, sector2.id])})
        self.assertSetEqual(expected, {*clean([sector1.id])})

    def test_forced_values02(self):
        "Use <to_field_name>."
        field_builder = partial(
            EnhancedModelMultipleChoiceField,
            queryset=FakeSector.objects.all(),
            required=False,
            to_field_name='title',
        )
        sectors = [*FakeSector.objects.all()]
        self.assertGreaterEqual(len(sectors), 3)

        sector1, sector2, sector3 = sectors[:3]

        field = field_builder(forced_values=[sector2.title])

        clean = field.clean
        expected = {sector1, sector2}
        self.assertSetEqual(expected, {*clean([sector1.title, sector2.title])})
        self.assertSetEqual(expected, {*clean([sector1.title])})

        # --
        choices = [*field.choices]
        choice1 = self.assertFoundChoice(sector1.title, sector1.title, choices)
        self.assertFalse(choice1.readonly)

        choice2 = self.assertFoundChoice(sector2.title, sector2.title, choices)
        self.assertTrue(choice2.readonly)

    def test_initial(self):
        field = EnhancedModelMultipleChoiceField(queryset=FakeSector.objects.all())
        sector1, sector2 = FakeSector.objects.all()[:2]

        field.initial = [sector2.id, sector1.id]
        self.assertSetEqual({sector2.id, sector1.id}, field.initial)

        field.initial = [sector1.id]
        self.assertSetEqual({sector1.id}, field.initial)

        field.initial = None
        self.assertFalse(field.initial)

        field.forced_values = [sector1.id]
        field.initial = [sector2.id]
        self.assertSetEqual({sector2.id, sector1.id}, field.initial)
        self.assertEqual(frozenset([sector1.id]), field.forced_values)

    def test_widget_choices(self):
        field = EnhancedModelMultipleChoiceField(queryset=FakeSector.objects.all())
        sector1, sector2 = FakeSector.objects.all()[:2]
        widget = field.widget
        field.forced_values = [sector1.id]

        choices = [*widget.choices]
        choice1 = self.assertFoundChoice(sector1.id, sector1.title, choices)
        self.assertTrue(choice1.readonly)

        choice2 = self.assertFoundChoice(sector2.id, sector2.title, choices)
        self.assertFalse(choice2.readonly)

    def test_iterator(self):
        class CustomIterator(EnhancedModelChoiceIterator):
            def help(self, obj):
                return f'The "{obj}" sector'

        field = EnhancedModelMultipleChoiceField(
            queryset=FakeSector.objects.all(),
            iterator=CustomIterator,
        )

        sector = FakeSector.objects.first()

        choices = [*field.choices]
        choice = self.assertFoundChoice(sector.id, sector.title, choices)
        self.assertEqual(f'The "{sector}" sector', choice.help)


class ReadonlyMessageFieldTestCase(FieldTestCase):
    def test_clean(self):
        label = 'Beware !'
        msg = 'This stuff is not available'
        field = ReadonlyMessageField(label=label, initial=msg)
        self.assertEqual(label, field.label)
        self.assertEqual(msg, field.initial)
        self.assertFalse(field.required)
        self.assertIsInstance(field.widget, core_widgets.Label)

        self.assertIsNone(field.clean(''))
        self.assertIsNone(field.clean('ignore me'))

    def test_clean_return_value(self):
        return_value = 'NO VALUE'
        field = ReadonlyMessageField(
            label='Beware !', initial='Blabla', return_value=return_value,
        )

        self.assertEqual(return_value, field.clean(''))
        self.assertEqual(return_value, field.clean('ignore me'))

    def test_widget(self):
        class MyLabel(core_widgets.Label):
            pass

        field = ReadonlyMessageField(
            label='Beware !', initial='This stuff is not available',
            widget=MyLabel,
        )
        self.assertIsInstance(field.widget, MyLabel)

    def test_initial(self):
        field = ReadonlyMessageField(label='Beware !')
        self.assertEqual('', field.initial)

        msg = 'This stuff is not available'
        field.initial = msg
        self.assertEqual(msg, field.initial)
