# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.core.exceptions import ValidationError
    from django.contrib.contenttypes.models import ContentType
    from django.forms import IntegerField, ChoiceField
    from django.utils.timezone import now
    from django.utils.translation import gettext as _

    from .base import FieldTestCase

    from creme.creme_core.forms.fields import (DatePeriodField, DateRangeField,
            DurationField, ColorField, ChoiceOrCharField,
            OptionalChoiceField,
            CTypeChoiceField, EntityCTypeChoiceField,
            MultiCTypeChoiceField, MultiEntityCTypeChoiceField,
            ForcedModelMultipleChoiceField)
    from creme.creme_core.forms.widgets import UnorderedMultipleChoiceWidget
    from creme.creme_core.models import (RelationType, CremePropertyType, Currency,
            FakeContact, FakeOrganisation, FakeSector)
    from creme.creme_core.utils.date_period import (DatePeriod, MinutesPeriod, HoursPeriod, DaysPeriod,
            DatePeriodRegistry, date_period_registry)
    from creme.creme_core.utils.date_range import DateRange, CustomRange, CurrentYearRange
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class DatePeriodFieldTestCase(FieldTestCase):
    def test_ok01(self):
        "Days"
        period = DatePeriodField().clean(['days', '3'])
        self.assertIsInstance(period, DatePeriod)

        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2014, month=7, day=5, hour=22, minute=9),
                         create_dt(year=2014, month=7, day=2, hour=22, minute=9)
                         + period.as_timedelta()
                        )

    def test_ok02(self):
        "Minutes"
        period = DatePeriodField().clean(['minutes', '5'])
        self.assertIsInstance(period, DatePeriod)

        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2014, month=7, day=2, hour=22, minute=14),
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
        self.assertFieldValidationError(IntegerField, 'invalid', clean, ['years', 'notint'])

        name = 'unknownperiod'
        self.assertFieldValidationError(ChoiceField, 'invalid_choice', clean,
                                        [name, '2'], message_args={'value': name},
                                       )

    def test_choices(self):
        choices = list(DatePeriodField().choices)
        self.assertIn((MinutesPeriod.name, MinutesPeriod.verbose_name), choices)
        self.assertIn((HoursPeriod.name,   HoursPeriod.verbose_name),   choices)
        self.assertIn((DaysPeriod.name,    DaysPeriod.verbose_name),    choices)

    def test_period_names(self):
        clean = DatePeriodField(period_names=('months',)).clean
        period = clean(['months', '5'])
        self.assertIsInstance(period, DatePeriod)

        name = 'years'
        self.assertFieldValidationError(ChoiceField, 'invalid_choice', clean,
                                        [name, '2'], message_args={'value': name},
                                       )

    def test_notnull(self):
        with self.assertRaises(ValidationError) as cm:
            DatePeriodField().clean(['days', '0'])

        self.assertEqual([_('Ensure this value is greater than or equal to %(limit_value)s.') % {
                                'limit_value': 1
                            },
                         ],
                         cm.exception.messages
                        )

    def test_registry_1(self):
        self.assertEqual(list(date_period_registry.choices()), list(DatePeriodField().choices))

    def test_registry_2(self):
        registry = DatePeriodRegistry(MinutesPeriod, HoursPeriod)
        self.assertEqual(list(registry.choices()), list(DatePeriodField(period_registry=registry).choices))

    def test_registry_3(self):
        registry = DatePeriodRegistry(MinutesPeriod, HoursPeriod)
        field = DatePeriodField()
        field.period_registry = registry
        self.assertEqual(list(registry.choices()), list(field.choices))

    def test_period_names_1(self):
        names = (MinutesPeriod.name, HoursPeriod.name)
        self.assertEqual(list(date_period_registry.choices(choices=names)),
                         list(DatePeriodField(period_names=names).choices)
                        )

    def test_period_names_2(self):
        field = DatePeriodField()
        field.period_names = names = (MinutesPeriod.name, HoursPeriod.name)
        self.assertEqual(list(date_period_registry.choices(choices=names)), list(field.choices))


class DateRangeFieldTestCase(FieldTestCase):
    def test_clean_empty_customized(self):
        clean = DateRangeField().clean
        self.assertFieldValidationError(DateRangeField, 'required', clean, ['', '', ''])
        self.assertFieldValidationError(DateRangeField, 'required', clean, None)

    def test_start_before_end(self):
        self.assertFieldValidationError(DateRangeField, 'customized_invalid',
                                        DateRangeField().clean, ['', '2011-05-16', '2011-05-15']
                                       )

    def test_ok01(self):
        drange = DateRangeField().clean(['', '2013-05-29', '2013-06-16'])
        dt = self.create_datetime
        self.assertIsInstance(drange, DateRange)
        self.assertIsInstance(drange, CustomRange)
        self.assertEqual((dt(year=2013, month=5, day=29, hour=0,  minute=0,  second=0),
                          dt(year=2013, month=6, day=16, hour=23, minute=59, second=59),
                         ),
                         drange.get_dates(now())
                        )

    def test_ok02(self):
        drange = DateRangeField().clean([CurrentYearRange.name, '', ''])
        dt = self.create_datetime
        self.assertIsInstance(drange, CurrentYearRange)
        self.assertEqual((dt(year=2013, month=1, day=1,   hour=0,  minute=0,  second=0),
                          dt(year=2013, month=12, day=31, hour=23, minute=59, second=59),
                         ),
                         drange.get_dates(dt(year=2013, month=5, day=29, hour=11))
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
        self.assertFieldValidationError(DurationField, 'invalid', DurationField().clean, ['a', 'b', 'c'])

    def test_positive01(self):
        self.assertFieldValidationError(DurationField, 'min_value', DurationField().clean,
                                        ['-1', '-1', '-1'], message_args={'limit_value': 0}
                                       )

    def test_ok01(self):
        clean = DurationField().clean
        self.assertEqual('10:2:0', clean(['10', '2', '0']))
        self.assertEqual('10:2:0', clean([10, 2, 0]))


class OptionalChoiceFieldTestCase(FieldTestCase):
    _team = ['Naruto', 'Sakura', 'Sasuke', 'Kakashi']

    def test_ok_choice(self):
        field = OptionalChoiceField(choices=enumerate(self._team, start=1))
        self.assertEqual((True, '1'), field.clean([True, 1]))

    def test_not_required(self):
        field = OptionalChoiceField(choices=enumerate(self._team, start=1), required=False)
        expected = (False, None)
        self.assertEqual(expected, field.clean([False, '']))
        self.assertEqual(expected, field.clean([False, 1]))
        self.assertEqual(expected, field.clean([False, None]))
        self.assertEqual(expected, field.clean([False]))
        self.assertEqual(expected, field.clean([]))

    def test_required(self):
        clean = OptionalChoiceField(choices=enumerate(self._team, start=1), required=True).clean

        expected = (False, None)
        self.assertEqual(expected, clean([False, None]))
        self.assertEqual(expected, clean([False]))
        self.assertEqual(expected, clean([]))

        self.assertFieldValidationError(OptionalChoiceField, 'subfield_required', clean, [True, None])
        self.assertFieldValidationError(OptionalChoiceField, 'subfield_required', clean, [True])

    def test_invalid(self):
        field = OptionalChoiceField(choices=enumerate(self._team, start=1))

        with self.assertRaises(ValidationError) as cm:
            field.clean([False, 'invalid'])

        self.assertEqual([_('Select a valid choice. %(value)s is not one of the available choices.') % {
                                'value': 'invalid',
                            },
                         ],
                         cm.exception.messages
                        )


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

        self.assertIn((0, _('Other')), choices)

        other = 'Shikamaru'
        self.assertEqual((0, other), field.clean([0, other]))

    def test_empty_ok(self):
        field = ChoiceOrCharField(choices=enumerate(self._team, start=1), required=False)

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

        self.assertEqual(sorted([(ct1.pk, str(ct1)),
                                 (ct2.pk, str(ct2)),
                                ], key=lambda ct: ct[1]),
                         list(field.widget.choices)
                        )

        self.assertEqual(ct1, clean(ct1.id))
        self.assertEqual(ct2, clean(ct2.id))
        self.assertFieldValidationError(CTypeChoiceField, 'required', clean, '')

    def test_not_required(self):
        ct1 = self.ct1
        ct2 = self.ct2
        field = CTypeChoiceField(ctypes=[ct1, ct2], required=False)
        clean = field.clean

        self.assertEqual([('', field.empty_label)] +
                         sorted([(ct1.pk, str(ct1)),
                                 (ct2.pk, str(ct2)),
                                ], key=lambda ct: ct[1]),
                         list(field.widget.choices)
                        )

        self.assertEqual(ct1, clean(ct1.id))
        self.assertEqual(ct2, clean(ct2.id))
        self.assertEqual(None, clean(''))

    def test_invalid(self):
        clean = CTypeChoiceField(ctypes=[self.ct1, self.ct2]).clean
        self.assertFieldValidationError(CTypeChoiceField, 'invalid_choice',
                                        clean, self.ct3.id,
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
        self.assertFieldValidationError(EntityCTypeChoiceField, 'invalid_choice',
                                        EntityCTypeChoiceField().clean, self.ct3.id,
                                       )

    def test_ctypes01(self):
        "Constructor"
        ct1 = self.ct1

        with self.assertNumQueries(0):
            field = EntityCTypeChoiceField(ctypes=[ct1])

        clean = field.clean
        self.assertEqual(ct1, clean(ct1.id))
        self.assertFieldValidationError(EntityCTypeChoiceField,
                                        'invalid_choice', clean, self.ct2.id,
                                       )

    def test_ctypes02(self):
        "Setter"
        ct1 = self.ct1
        field = EntityCTypeChoiceField()
        field.ctypes = [ct1]

        clean = field.clean
        self.assertEqual(ct1, clean(ct1.id))
        self.assertFieldValidationError(EntityCTypeChoiceField,
                                        'invalid_choice', clean, self.ct2.id,
                                       )

    def test_ctypes03(self):
        "All accepted"
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

        self.assertEqual(sorted([(ct1.pk, str(ct1)),
                                 (ct2.pk, str(ct2)),
                                ], key=lambda ct: ct[1]),
                         [(choice.value, label) for choice, label in field.widget.choices])

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

        self.assertEqual(sorted([(ct1.pk, str(ct1)),
                                 (ct2.pk, str(ct2)),
                                ], key=lambda ct: ct[1]),
                         [(choice.value, label) for choice, label in field.widget.choices])

        self.assertEqual([ct1], clean([ct1.id]))
        self.assertEqual([ct2], clean([ct2.id]))
        self.assertEqual([],    clean(''))
        self.assertEqual([],    clean([]))

    def test_invalid(self):
        ct1 = self.ct1
        clean = MultiCTypeChoiceField(ctypes=[ct1, self.ct2]).clean
        self.assertFieldValidationError(MultiCTypeChoiceField, 'invalid_choice',
                                        clean, [ct1.id, self.ct3.id],
                                       )
        self.assertFieldValidationError(MultiCTypeChoiceField, 'invalid_choice',
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

        self.assertEqual([ct1], clean([ct1.id]))
        self.assertEqual([ct2], clean([ct2.id]))
        self.assertEqual([],    clean(''))
        self.assertEqual([],    clean([]))

    def test_invalid(self):
        clean = MultiEntityCTypeChoiceField().clean
        self.assertFieldValidationError(MultiEntityCTypeChoiceField, 'invalid_choice',
                                        clean, [self.ct1.id, self.ct3.id],
                                       )
        self.assertFieldValidationError(MultiEntityCTypeChoiceField, 'invalid_choice',
                                        clean, ['not an int'],
                                       )

    def test_ctypes(self):
        ct1 = self.ct1
        clean = MultiEntityCTypeChoiceField(ctypes=[ct1]).clean
        self.assertEqual([ct1], clean([ct1.id]))
        self.assertFieldValidationError(MultiEntityCTypeChoiceField,
                                        'invalid_choice', clean, [self.ct2.id],
                                       )


class ForcedModelMultipleChoiceFieldTestCase(FieldTestCase):
    def assertFoundChoice(self, pk, label, choices):
        for choice in choices:
            if choice[0].value == pk:
                if choice[1] != label:
                    self.fail('Choice with pk="{pk}" found with '
                              'label "{found}" != "{label}"'.format(
                        pk=pk,
                        found=choice[1],
                        label=label,
                    ))

                return choice

        self.fail('Choice with pk="{}" not found'.format(pk))

    def test_required(self):
        field = ForcedModelMultipleChoiceField(queryset=FakeSector.objects.all())
        self.assertTrue(field.required)
        self.assertIsInstance(field.widget, UnorderedMultipleChoiceWidget)
        self.assertSetEqual(set(), field.initial)

        sectors = list(FakeSector.objects.all())
        self.assertGreaterEqual(len(sectors), 3)

        sector1 = sectors[0]
        sector2 = sectors[1]
        sector3 = sectors[2]

        choices = list(field.choices)
        choice1 = self.assertFoundChoice(sector1.id, sector1.title, choices)
        self.assertFalse(choice1[0].readonly)

        self.assertFoundChoice(sector2.id, sector2.title, choices)

        clean = field.clean
        self.assertSetEqual({sector1, sector3}, set(clean([sector1.id, sector3.id])))
        self.assertSetEqual({sector1, sector3}, set(clean([str(sector1.id), str(sector3.id)])))

        # NB: we need a 0-argument constructor
        field_builder = partial(ForcedModelMultipleChoiceField, queryset=FakeSector.objects.all())
        self.assertFieldValidationError(field_builder, 'required', clean, '')
        self.assertFieldValidationError(field_builder, 'required', clean, [])
        self.assertFieldValidationError(field_builder, 'required', clean, None)

    def test_not_required(self):
        field = ForcedModelMultipleChoiceField(queryset=FakeSector.objects.all(), required=False)

        sector = FakeSector.objects.first()
        self.assertIsNotNone(sector)

        clean = field.clean
        self.assertEqual([sector], list(clean([sector.id])))
        self.assertFalse([], clean(''))
        self.assertFalse([], clean([]))

    def test_invalid(self):
        field_builder = partial(ForcedModelMultipleChoiceField, queryset=FakeSector.objects.all())
        field = field_builder()

        invalid_pk = 1024
        self.assertFalse(FakeSector.objects.filter(pk=invalid_pk))

        self.assertFieldValidationError(field_builder, 'invalid_choice',
                                        field.clean, [str(invalid_pk)],
                                        message_args={'value': invalid_pk},
                                       )

    def test_forced_values01(self):
        field_builder = partial(ForcedModelMultipleChoiceField,
                                queryset=FakeSector.objects.all(),
                                required=False,
                               )
        field1 = field_builder()
        self.assertEqual(frozenset(), field1.forced_values)
        self.assertFalse(field1.initial)

        sectors = list(FakeSector.objects.all())
        self.assertGreaterEqual(len(sectors), 3)

        sector1, sector2, sector3 = sectors[:3]

        field1.forced_values = [sector1.id, sector3.id]
        self.assertEqual(frozenset([sector1.id, sector3.id]), field1.forced_values)
        self.assertSetEqual({sector1.id, sector3.id}, field1.initial)

        # --
        choices = list(field1.choices)
        choice1 = self.assertFoundChoice(sector1.id, sector1.title, choices)
        self.assertTrue(choice1[0].readonly)

        choice2 = self.assertFoundChoice(sector2.id, sector2.title, choices)
        self.assertFalse(choice2[0].readonly)

        # --
        field2 = field_builder(forced_values=[sector2.id])
        self.assertEqual(frozenset([sector2.id]), field2.forced_values)

        clean = field2.clean
        expected = {sector1, sector2}
        self.assertSetEqual(expected, set(clean([sector1.id, sector2.id])))
        self.assertSetEqual(expected, set(clean([sector1.id])))

    def test_forced_values02(self):
        "Use <to_field_name>."
        field_builder = partial(ForcedModelMultipleChoiceField,
                                queryset=FakeSector.objects.all(),
                                required=False,
                                to_field_name='title',
                               )
        sectors = list(FakeSector.objects.all())
        self.assertGreaterEqual(len(sectors), 3)

        sector1, sector2, sector3 = sectors[:3]

        field = field_builder(forced_values=[sector2.title])

        clean = field.clean
        expected = {sector1, sector2}
        self.assertSetEqual(expected, set(clean([sector1.title, sector2.title])))
        self.assertSetEqual(expected, set(clean([sector1.title])))

        # --
        choices = list(field.choices)
        choice1 = self.assertFoundChoice(sector1.title, sector1.title, choices)
        self.assertFalse(choice1[0].readonly)

        choice2 = self.assertFoundChoice(sector2.title, sector2.title, choices)
        self.assertTrue(choice2[0].readonly)

    def test_initial(self):
        field = ForcedModelMultipleChoiceField(queryset=FakeSector.objects.all())
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
        field = ForcedModelMultipleChoiceField(queryset=FakeSector.objects.all())
        sector1, sector2 = FakeSector.objects.all()[:2]
        widget = field.widget
        field.forced_values = [sector1.id]

        choices = list(widget.choices)
        choice1 = self.assertFoundChoice(sector1.id, sector1.title, choices)
        self.assertTrue(choice1[0].readonly)

        choice2 = self.assertFoundChoice(sector2.id, sector2.title, choices)
        self.assertFalse(choice2[0].readonly)
