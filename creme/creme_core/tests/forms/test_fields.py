from copy import deepcopy
from datetime import timedelta
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator
from django.forms import (
    BooleanField,
    ChoiceField,
    Field,
    Form,
    HiddenInput,
    IntegerField,
)
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

import creme.creme_core.forms.widgets as core_widgets
from creme.creme_core.forms.fields import (
    ChoiceOrCharField,
    ColorField,
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
    OptionalField,
    OrderedChoiceIterator,
    OrderedMultipleChoiceField,
    PropertyTypesChoiceField,
    ReadonlyMessageField,
    RelativeDatePeriodField,
    UnionField,
)
from creme.creme_core.models import (
    CremePropertyType,
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
    YearsPeriod,
    date_period_registry,
)
from creme.creme_core.utils.date_range import (
    CurrentYearRange,
    CustomRange,
    DateRange,
)

from ..base import CremeTestCase


class DatePeriodFieldTestCase(CremeTestCase):
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
        field = DatePeriodField()
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=['', ''])
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)

    def test_not_required(self):
        clean = DatePeriodField(required=False).clean
        self.assertIsNone(clean(['', '']))
        self.assertIsNone(clean(['']))
        self.assertIsNone(clean([]))
        self.assertIsNone(clean(None))
        self.assertIsNone(clean(['days', '']))
        self.assertIsNone(clean(['days']))
        self.assertIsNone(clean(['', 2]))

    def test_invalid(self):
        field = DatePeriodField()
        self.assertFormfieldError(
            field=field, value=['years', 'notint'],
            messages=_('Enter a whole number.'), codes='invalid',
        )

        name = 'unknownperiod'
        self.assertFormfieldError(
            field=field, value=[name, '2'],
            messages=_(
                'Select a valid choice. %(value)s is not one of the available choices.'
            ) % {'value': name},
            codes='invalid_choice',
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
        field = DatePeriodField(period_names=('months',))
        period = field.clean(['months', '5'])
        self.assertIsInstance(period, DatePeriod)

        name = 'years'
        self.assertFormfieldError(
            field=field, value=[name, '2'],
            messages=_(
                'Select a valid choice. %(value)s is not one of the available choices.'
            ) % {'value': name},
            codes='invalid_choice',
        )

    def test_notnull(self):
        self.assertFormfieldError(
            field=DatePeriodField(),
            value=['days', '0'],
            messages=MinValueValidator.message % {'limit_value': 1},
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


class RelativeDatePeriodFieldTestCase(CremeTestCase):
    def test_relative_date_period(self):
        RPeriod = RelativeDatePeriodField.RelativeDatePeriod

        rperiod1 = RPeriod(sign=1, period=DaysPeriod(1))
        self.assertEqual(1,             rperiod1.sign)
        self.assertEqual(DaysPeriod(1), rperiod1.period)

        rperiod2 = RPeriod(sign=-1, period=HoursPeriod(3))
        self.assertEqual(-1,             rperiod2.sign)
        self.assertEqual(HoursPeriod(3), rperiod2.period)

        self.assertNotEqual(rperiod1, None)
        self.assertNotEqual(rperiod1, rperiod2)
        self.assertNotEqual(RPeriod(sign=-1, period=DaysPeriod(1)), rperiod1)
        self.assertNotEqual(RPeriod(sign=1,  period=DaysPeriod(2)), rperiod1)
        self.assertEqual(RPeriod(sign=1, period=DaysPeriod(1)), rperiod1)

        self.assertRaises(ValueError, RPeriod, sign=2, period=DaysPeriod(1))

    def test_ok01(self):
        "Days + after."
        signed_period = RelativeDatePeriodField().clean(['1', [DaysPeriod.name, '3']])
        self.assertEqual(
            RelativeDatePeriodField.RelativeDatePeriod(sign=1, period=DaysPeriod(3)),
            signed_period,
        )

    def test_ok02(self):
        "Minutes + before."
        signed_period = RelativeDatePeriodField().clean(['-1', [MinutesPeriod.name, '5']])
        self.assertEqual(
            RelativeDatePeriodField.RelativeDatePeriod(sign=-1, period=MinutesPeriod(5)),
            signed_period,
        )

    def test_required(self):
        field = RelativeDatePeriodField()
        pname = DaysPeriod.name
        code = 'required'
        msg = Field.default_error_messages[code]
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=['', ['', '']])
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=None)
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=['', [pname, '2']])
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=['1', [pname, '']])

    def test_not_required(self):
        clean = RelativeDatePeriodField(required=False).clean
        self.assertIsNone(clean(['', ['', '']]))
        self.assertIsNone(clean(['', ['']]))
        self.assertIsNone(clean(['']))
        self.assertIsNone(clean([]))
        self.assertIsNone(clean(None))
        self.assertIsNone(clean(['1', [DaysPeriod.name, '']]))
        self.assertIsNone(clean(['1', ['', '2']]))

    def test_invalid(self):
        field = RelativeDatePeriodField()
        choice_msg = _(
            'Select a valid choice. %(value)s is not one of the available choices.'
        )
        self.assertFormfieldError(
            field=field,
            value=['notint', [YearsPeriod.name, '1']],
            messages=choice_msg % {'value': 'notint'},
            codes='invalid_choice',
        )
        self.assertFormfieldError(
            field=field,
            value=['1', [YearsPeriod.name, 'notint']],
            messages=_('Enter a whole number.'),
            codes='invalid',
        )

        name = 'unknownperiod'
        self.assertFormfieldError(
            field=field,
            value=['-1', [name, '2']],
            messages=choice_msg % {'value': name},
            codes='invalid_choice',
        )

    def test_notnull_period(self):
        self.assertFormfieldError(
            field=RelativeDatePeriodField(),
            value=['-1', [DaysPeriod.name, '0']],
            messages=MinValueValidator.message % {'limit_value': 1},
        )

    def test_period_names_1(self):
        names = (MinutesPeriod.name, HoursPeriod.name)
        field = RelativeDatePeriodField(period_names=names)
        self.assertListEqual([*names], [*field.period_names])

        expected_choices = [*date_period_registry.choices(choices=names)]
        self.assertListEqual(expected_choices, [*field.fields[1].choices])
        self.assertListEqual(expected_choices, [*field.widget.period_choices])
        self.assertListEqual(expected_choices, [*field.period_choices])

    def test_period_names_2(self):
        field = RelativeDatePeriodField()
        field.period_names = names = (MinutesPeriod.name, HoursPeriod.name)
        self.assertListEqual(
            [*date_period_registry.choices(choices=names)],
            [*field.fields[1].choices],
        )

    def test_registry_1(self):
        field = RelativeDatePeriodField()
        self.assertListEqual(
            [*date_period_registry.choices()],
            [*field.fields[1].choices],
        )
        self.assertEqual(date_period_registry, field.period_registry)

    def test_registry_2(self):
        registry = DatePeriodRegistry(MinutesPeriod, HoursPeriod)
        self.assertListEqual(
            [*registry.choices()],
            [*RelativeDatePeriodField(period_registry=registry).fields[1].choices],
        )

    def test_registry_3(self):
        "Property."
        registry = DatePeriodRegistry(MinutesPeriod, HoursPeriod)
        field = RelativeDatePeriodField()
        field.period_registry = registry
        self.assertListEqual([*registry.choices()], [*field.fields[1].choices])

    def test_relative_choices_1(self):
        "Default choices."
        field = RelativeDatePeriodField(period_names=(MinutesPeriod.name,))
        expected_choices = [
            (-1, pgettext('creme_core-date_period', 'Before')),
            (1,  pgettext('creme_core-date_period', 'After')),
        ]
        self.assertListEqual(expected_choices, [*field.fields[0].choices])
        self.assertListEqual(expected_choices, [*field.relative_choices])
        self.assertListEqual(expected_choices, [*field.widget.relative_choices])

    def test_relative_choices_2(self):
        "Property."
        field = RelativeDatePeriodField(period_names=(MinutesPeriod.name,))
        choices = [(-1, 'In the past'), (1, 'In the future')]
        field.relative_choices = choices
        self.assertListEqual(choices, [*field.fields[0].choices])
        self.assertListEqual(choices, [*field.widget.relative_choices])


class DateRangeFieldTestCase(CremeTestCase):
    def test_clean_empty_customized(self):
        field = DateRangeField()
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=['', '', ''])
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)

    def test_start_before_end(self):
        date_value = self.formfield_value_date
        self.assertFormfieldError(
            field=DateRangeField(),
            value=['', date_value(2011, 5, 16), date_value(2011, 5, 15)],
            messages=_('Start date has to be before end date.'),
            codes='customized_invalid',
        )

    def test_ok(self):
        date_value = self.formfield_value_date
        drange = DateRangeField().clean(['', date_value(2013, 5, 29), date_value(2013, 6, 16)])
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

    def test_ok_special_range(self):
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

    def test_ok_empty(self):
        drange = DateRangeField(required=False).clean(['', '', ''])
        self.assertIsNone(drange)


class ColorFieldTestCase(CremeTestCase):
    def test_empty01(self):
        field = ColorField()
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=[])

    def test_length01(self):
        field = ColorField()
        msg = _('Enter a valid value (e.g. DF8177).')
        self.assertFormfieldError(field=field, value='1',     messages=msg, codes='invalid')
        self.assertFormfieldError(field=field, value='12',    messages=msg, codes='invalid')
        self.assertFormfieldError(field=field, value='123',   messages=msg, codes='invalid')
        self.assertFormfieldError(field=field, value='1234',  messages=msg, codes='invalid')
        self.assertFormfieldError(field=field, value='12345', messages=msg, codes='invalid')

    def test_invalid_value01(self):
        field = ColorField()
        msg = _('Enter a valid value (e.g. DF8177).')
        self.assertFormfieldError(field=field, messages=msg, codes='invalid', value='GGGGGG')
        self.assertFormfieldError(field=field, messages=msg, codes='invalid', value='------')

    def test_ok01(self):
        clean = ColorField().clean
        self.assertEqual('AAAAAA', clean('AAAAAA'))
        self.assertEqual('AAAAAA', clean('#AAAAAA'))
        self.assertEqual('AAAAAA', clean('aaaaaa'))
        self.assertEqual('AAAAAA', clean('#aaaaaa'))
        self.assertEqual('123456', clean('123456'))
        self.assertEqual('123ABC', clean('123ABC'))
        self.assertEqual('123ABC', clean('123abc'))

    def test_render(self):
        label = 'My color'
        color = '123abc'

        class ColorForm(Form):
            color = ColorField(label=label)

        form = ColorForm(data={'color': color})

        self.assertHTMLEqual(
            f'<p>'
            f'<label for="id_color">{label}{_(":")}</label>'
            f'<input type="color" name="color" value="#{color}" required id="id_color">'
            f'</p>',
            form.as_p(),
        )

    def test_render_empty(self):
        label = 'Color'

        class ColorForm(Form):
            color = ColorField(label=label)

        form = ColorForm()

        self.assertHTMLEqual(
            f'<p>'
            f'<label for="id_color">{label}{_(":")}</label>'
            f'<input type="color" name="color" required id="id_color">'
            f'</p>',
            form.as_p(),
        )


class DurationFieldTestCase(CremeTestCase):
    def test_ok(self):
        clean = DurationField().clean
        self.assertEqual(timedelta(hours=10, minutes=2, seconds=0),  clean(['10', '2', '0']))
        self.assertEqual(timedelta(hours=8, minutes=12, seconds=25), clean([8, 12, 25]))

    def test_empty_required(self):
        field = DurationField()
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=[])
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=['', '', ''])

    def test_empty_not_required(self):
        clean = DurationField(required=False).clean
        empty = timedelta()
        self.assertEqual(empty, clean(None))
        self.assertEqual(empty, clean(''))
        self.assertEqual(empty, clean([]))
        self.assertEqual(empty, clean(['', '', '']))

    def test_invalid(self):
        self.assertFormfieldError(
            field=DurationField(),
            value=['a', 'b', 'c'],
            messages=_('Enter a whole number.'),
            codes='invalid',
        )

    def test_positive(self):
        self.assertFormfieldError(
            field=DurationField(),
            value=['-1', '-1', '-1'],
            messages=_(
                'Ensure this value is greater than or equal to %(limit_value)s.'
            ) % {'limit_value': 0},
            codes='min_value',
        )


class OptionalFieldTestCase(CremeTestCase):
    def test_option01(self):
        opt1 = OptionalField.Option(is_set=True, data=1)
        self.assertIs(opt1.is_set, True)
        self.assertEqual(1, opt1.data)
        self.assertTrue(opt1)

        opt2 = OptionalField.Option(is_set=False, data=None)
        self.assertIs(opt2.is_set, False)
        self.assertIsNone(opt2.data)
        self.assertTrue(opt2)

        self.assertEqual(opt1, OptionalField.Option(is_set=True, data=1))
        self.assertNotEqual(opt1, OptionalField.Option(is_set=False, data=None))
        self.assertNotEqual(opt1, OptionalField.Option(is_set=True,  data=2))

    def test_option02(self):
        opt1 = OptionalField.Option(is_set=False)
        self.assertFalse(opt1.is_set)
        self.assertIsNone(opt1.data)

        with self.assertRaises(ValueError):
            OptionalField.Option(is_set=False, data=1)


class OptionalChoiceFieldTestCase(CremeTestCase):
    _team = ['Naruto', 'Sakura', 'Sasuke', 'Kakashi']

    def test_sub_fields(self):
        choices = [*enumerate(self._team, start=1)]
        field = OptionalChoiceField(choices=choices)
        self.assertFalse(field.required)

        sub_fields = field.fields
        self.assertIsTuple(sub_fields, length=2)

        sub_field1 = sub_fields[0]
        self.assertIsInstance(sub_field1, BooleanField)
        self.assertFalse(sub_field1.required)
        self.assertFalse(sub_field1.disabled)

        sub_field2 = sub_fields[1]
        self.assertIsInstance(sub_field2, ChoiceField)
        self.assertListEqual(choices, sub_field2.choices)
        self.assertFalse(sub_field2.required)
        self.assertFalse(sub_field2.disabled)

    def test_ok_choice(self):
        field = OptionalChoiceField(choices=enumerate(self._team, start=1))
        self.assertEqual(
            OptionalChoiceField.Option(is_set=True, data='1'),
            field.clean([True, 1]),
        )

    def test_not_required(self):
        field = OptionalChoiceField(
            choices=enumerate(self._team, start=1), required=False,
        )
        expected = OptionalChoiceField.Option(is_set=False, data=None)
        self.assertEqual(expected, field.clean([False, '']))
        self.assertEqual(expected, field.clean(['', '']))
        self.assertEqual(expected, field.clean([False, 1]))
        self.assertEqual(expected, field.clean([False, None]))
        self.assertEqual(expected, field.clean([False]))
        self.assertEqual(expected, field.clean([]))

        self.assertFormfieldError(
            field=field, value=['on', None],
            messages=_('Enter a value if you check the box.'),
            codes='subfield_required',
        )

    def test_required(self):
        field = OptionalChoiceField(
            choices=enumerate(self._team, start=1), required=True,
        )

        expected = OptionalChoiceField.Option(is_set=False, data=None)
        self.assertEqual(expected, field.clean([False, None]))
        self.assertEqual(expected, field.clean(['', None]))
        self.assertEqual(expected, field.clean([False]))
        self.assertEqual(expected, field.clean([]))

        msg = _('Enter a value if you check the box.')
        code = 'subfield_required'
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=[True, None])
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=['on', None])
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=[True])

    def test_invalid(self):
        self.assertFormfieldError(
            field=OptionalChoiceField(choices=enumerate(self._team, start=1)),
            value=[False, 'invalid'],
            messages=_(
                "Select a valid choice. %(value)s is not one of the available choices."
            ) % {'value': 'invalid'},
            codes='invalid_choice',
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


class TestUnionField(UnionField):
    CHOICE = 'type_choice'
    INT    = 'type_int'

    def __init__(self, sub_required=True, **kwargs):
        kwargs['fields_choices'] = (
            (
                self.CHOICE,
                ChoiceField(
                    label='Fixed choices',
                    choices=[('s', 'Small'), ('m', 'Medium'), ('b', 'Big')],
                    required=sub_required,
                )
            ),
            (self.INT, IntegerField(label='Free size', required=sub_required)),
        )

        super().__init__(**kwargs)


class UnionFieldTestCase(CremeTestCase):
    def test_fields_choices(self):
        field = TestUnionField()

        field_choices = [*field.fields_choices]
        self.assertEqual(2, len(field_choices))

        choice1 = field_choices[0]
        self.assertIsTuple(choice1, length=2)
        self.assertEqual('type_choice', choice1[0])
        sub_field1 = choice1[1]
        self.assertIsInstance(sub_field1, ChoiceField)
        self.assertEqual('Fixed choices', sub_field1.label)
        self.assertFalse(sub_field1.disabled)

        choice2 = field_choices[1]
        self.assertIsTuple(choice2, length=2)
        self.assertEqual('type_int', choice2[0])
        sub_field2 = choice2[1]
        self.assertIsInstance(sub_field2, IntegerField)
        self.assertEqual('Free size', sub_field2.label)
        self.assertFalse(sub_field2.disabled)

    def test_ok01(self):
        "All filled => keep only selected alternative."
        sub_values = {
            TestUnionField.CHOICE: 'm',
            TestUnionField.INT: '12',
        }
        clean = TestUnionField().clean
        self.assertTupleEqual(
            (TestUnionField.CHOICE, 'm'),
            clean((TestUnionField.CHOICE, sub_values)),
        )
        self.assertTupleEqual(
            (TestUnionField.INT, 12),
            clean((TestUnionField.INT, sub_values)),
        )

    def test_ok02(self):
        "Partially filled."
        self.assertTupleEqual(
            (TestUnionField.CHOICE, 'b'),
            TestUnionField().clean(
                (TestUnionField.CHOICE, {TestUnionField.CHOICE: 'b'})
            ),
        )

    def test_not_required(self):
        clean = TestUnionField(required=False).clean
        self.assertIsNone(clean(None))
        self.assertIsNone(clean(()))
        self.assertIsNone(clean(('', {})))

    def test_required__subfields_required(self):
        field = TestUnionField()
        self.assertTrue(field.required)

        field_choices = [*field.fields_choices]
        self.assertTrue(field_choices[0][1].required)
        self.assertTrue(field_choices[1][1].required)

        code = 'required'
        msg = Field.default_error_messages[code]
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=None)
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=('', {}))
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=(None, {}))
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=('invalid', {}))

    def test_required__subfields_not_required(self):
        field = TestUnionField(sub_required=False)
        self.assertTrue(field.required)

        field_choices = [*field.fields_choices]
        self.assertFalse(field_choices[0][1].required)
        self.assertFalse(field_choices[1][1].required)

        code = 'required'
        msg = Field.default_error_messages[code]
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=None)
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=('', {}))
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=(None, {}))
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=('invalid', {}))

        sub_values = {TestUnionField.CHOICE: '', TestUnionField.INT: ''}
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value=(TestUnionField.CHOICE, sub_values),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value=(TestUnionField.INT, sub_values),
        )

    def test_invalid(self):
        field = TestUnionField()
        self.assertFormfieldError(
            field=field,
            value=(TestUnionField.CHOICE, {TestUnionField.CHOICE: 'z'}),
            messages=ChoiceField.default_error_messages['invalid_choice'] % {'value': 'z'},
            codes='invalid_choice',
        )
        self.assertFormfieldError(
            field=field,
            value=(TestUnionField.INT, {TestUnionField.INT: 'notint'}),
            messages=IntegerField.default_error_messages['invalid'],
            codes='invalid',
        )
        self.assertFormfieldError(
            field=field,
            value=(TestUnionField.INT, {}),
            messages='No sub-data related to your choice.',
            codes='invalid',
        )

    def test_widget1(self):
        "Required."
        field = TestUnionField()
        self.assertEqual(_('Empty'), field.empty_label)

        widgets_choices = [*field.widget.widgets_choices]
        self.assertEqual(2, len(widgets_choices))

        choice1 = widgets_choices[0]
        self.assertIsTuple(choice1, length=3)
        self.assertEqual(TestUnionField.CHOICE, choice1[0])
        self.assertEqual('Fixed choices',             choice1[1])
        self.assertIsInstance(choice1[2], ChoiceField.widget)

        choice2 = widgets_choices[1]
        self.assertEqual(TestUnionField.INT, choice2[0])
        self.assertIsInstance(choice2[2], IntegerField.widget)

    def test_widget2(self):
        "Not required."
        empty_label = 'No size'
        field = TestUnionField(required=False, empty_label=empty_label)
        self.assertEqual(empty_label, field.empty_label)

        widgets_choices = [*field.widget.widgets_choices]
        self.assertEqual(3, len(widgets_choices))

        choice1 = widgets_choices[0]
        self.assertEqual('', choice1[0])
        self.assertEqual(empty_label, choice1[1])
        self.assertIsInstance(choice1[2], HiddenInput)

        self.assertEqual(TestUnionField.CHOICE, widgets_choices[1][0])
        self.assertEqual(TestUnionField.INT, widgets_choices[2][0])

    def test_deepcopy(self):
        field1 = TestUnionField()
        field2 = deepcopy(field1)

        field1.required = False
        self.assertEqual(3, len([*field1.widget.widgets_choices]))
        self.assertEqual(2, len([*field2.widget.widgets_choices]))

    def test_disabled(self):
        field = TestUnionField(disabled=True)
        self.assertTrue(field.disabled)

        field_choices1 = [*field.fields_choices]

        sub_field11 = field_choices1[0][1]
        self.assertIsInstance(sub_field11, ChoiceField)
        self.assertEqual('Fixed choices', sub_field11.label)
        self.assertTrue(sub_field11.disabled)

        sub_field12 = field_choices1[1][1]
        self.assertIsInstance(sub_field12, IntegerField)
        self.assertTrue(sub_field12.disabled)

        # Property
        field.disabled = False
        field_choices2 = [*field.fields_choices]

        self.assertFalse(field_choices2[0][1].disabled)
        self.assertFalse(field_choices2[1][1].disabled)


class ChoiceOrCharFieldTestCase(CremeTestCase):
    _team = ['Naruto', 'Sakura', 'Sasuke', 'Kakashi']

    def test_empty_required(self):
        field = ChoiceOrCharField(choices=enumerate(self._team, start=1))
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=[])

    def test_empty_other(self):
        field = ChoiceOrCharField(choices=enumerate(self._team, start=1))
        self.assertFormfieldError(
            field=field, value=[0, ''],
            messages=_('Enter a value for "Other" choice.'),
            codes='invalid_other',
        )

    def test_ok_choice(self):
        field = ChoiceOrCharField(choices=enumerate(self._team, start=1))
        self.assertTupleEqual((1, 'Naruto'), field.clean([1, '']))

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


class _CTypeChoiceFieldTestCase(CremeTestCase):
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
        self.assertFormfieldError(
            field=field, messages=_('This field is required.'), codes='required', value='',
        )

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
        self.assertFormfieldError(
            field=CTypeChoiceField(ctypes=[self.ct1, self.ct2]),
            value=self.ct3.id,
            messages=_(
                'Select a valid choice. That choice is not one of the available choices.'
            ),
            codes='invalid_choice',
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


class _EntityCTypeChoiceFieldTestCase(CremeTestCase):
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
        field = EntityCTypeChoiceField()
        self.assertEqual(ct1, field.clean(ct1.id))
        self.assertEqual(ct2, field.clean(ct2.id))
        self.assertFormfieldError(
            field=field, value='',
            messages=_('This field is required.'), codes='required',
        )

    def test_not_required(self):
        ct1 = self.ct1
        ct2 = self.ct2
        clean = EntityCTypeChoiceField(required=False).clean
        self.assertEqual(ct1, clean(ct1.id))
        self.assertEqual(ct2, clean(ct2.id))
        self.assertEqual(None, clean(''))

    def test_invalid(self):
        self.assertFormfieldError(
            field=EntityCTypeChoiceField(),
            value=self.ct3.id,
            messages=_(
                'Select a valid choice. That choice is not one of the available choices.'
            ),
            codes='invalid_choice',
        )

    def test_ctypes01(self):
        "Constructor."
        ct1 = self.ct1

        with self.assertNumQueries(0):
            field = EntityCTypeChoiceField(ctypes=[ct1])

        self.assertEqual(ct1, field.clean(ct1.id))
        self.assertFormfieldError(
            field=field,
            value=self.ct2.id,
            messages=_(
                'Select a valid choice. That choice is not one of the available choices.'
            ),
            codes='invalid_choice',
        )

    def test_ctypes02(self):
        "Setter."
        ct1 = self.ct1
        field = EntityCTypeChoiceField()
        field.ctypes = [ct1]

        self.assertEqual(ct1, field.clean(ct1.id))
        self.assertFormfieldError(
            field=field,
            value=self.ct2.id,
            messages=_(
                'Select a valid choice. That choice is not one of the available choices.'
            ),
            codes='invalid_choice',
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

        self.assertListEqual([ct1], field.clean([ct1.id]))
        self.assertListEqual([ct2], field.clean([ct2.id]))

        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=[])
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)

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
        field = MultiCTypeChoiceField(ctypes=[ct1, self.ct2])
        msg = _(
            'Select a valid choice. That choice is not one of the available choices.'
        )
        self.assertFormfieldError(
            field=field, value=[ct1.id, self.ct3.id], messages=msg, codes='invalid_choice',
        )
        self.assertFormfieldError(
            field=field, value=['not an int'], messages=msg, codes='invalid_choice',
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

        self.assertListEqual([ct1], field.clean([ct1.id]))
        self.assertListEqual([ct2], field.clean([ct2.id]))

        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=[])
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)

    def test_not_required(self):
        ct1 = self.ct1
        ct2 = self.ct2
        clean = MultiEntityCTypeChoiceField(ctypes=[ct1, ct2], required=False).clean

        self.assertListEqual([ct1], clean([ct1.id]))
        self.assertListEqual([ct2], clean([ct2.id]))
        self.assertListEqual([],    clean(''))
        self.assertListEqual([],    clean([]))

    def test_invalid(self):
        field = MultiEntityCTypeChoiceField()
        msg = _(
            'Select a valid choice. That choice is not one of the available choices.'
        )
        self.assertFormfieldError(
            field=field, value=[self.ct1.id, self.ct3.id], messages=msg, codes='invalid_choice',
        )
        self.assertFormfieldError(
            field=field, value=['not an int'], messages=msg, codes='invalid_choice',
        )

    def test_ctypes(self):
        ct1 = self.ct1
        field = MultiEntityCTypeChoiceField(ctypes=[ct1])
        self.assertListEqual([ct1], field.clean([ct1.id]))
        self.assertFormfieldError(
            field=field, value=[self.ct2.id],
            messages=_(
                'Select a valid choice. That choice is not one of the available choices.'
            ),
            codes='invalid_choice',
        )


class EnhancedMultipleChoiceFieldTestCase(CremeTestCase):
    def test_required(self):
        field = EnhancedMultipleChoiceField(
            choices=[(1, 'Sword'), (2, 'Axes'), (3, 'Spear')],
        )
        self.assertTrue(field.required)
        self.assertIsInstance(field.widget, core_widgets.UnorderedMultipleChoiceWidget)
        # self.assertSetEqual(set(), field.initial)
        self.assertIsNone(field.initial)

        clean = field.clean
        self.assertCountEqual(['1', '3'], clean([1, 3]))
        self.assertCountEqual(['1', '3'], clean(['1', '3']))

        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=[])
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)

    def test_not_required(self):
        field = EnhancedMultipleChoiceField(
            choices=[(1, 'Sword'), (2, 'Axes'), (3, 'Spear')],
            required=False,
        )

        clean = field.clean
        self.assertListEqual(['2'], [*clean(['2'])])
        self.assertListEqual([], clean(''))
        self.assertListEqual([], clean([]))

    def test_invalid(self):
        field = EnhancedMultipleChoiceField(
            choices=[(1, 'Sword'), (2, 'Axes'), (3, 'Spear')],
        )
        value = 4
        self.assertFormfieldError(
            field=field,
            value=[str(value)],
            messages=_(
                'Select a valid choice. %(value)s is not one of the available choices.'
            ) % {'value': value},
            codes='invalid_choice',
        )

    def test_choices__from_tuples(self):
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

    def test_choices__callable(self):
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

    def test_choices__from_dict(self):
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

    def test_choices__dict_callable(self):
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

    def test_forced_values__tuples(self):
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
        # self.assertFalse(field1.initial)
        wchoices1 = iter(field1.choices)
        old_wchoices1 = iter(field1.widget.choices)

        field1.forced_values = [1, 3]
        self.assertEqual(frozenset([1, 3]), field1.forced_values)  # TODO: '1', '3' ???
        # self.assertSetEqual({1, 3}, field1.initial)
        self.assertSetEqual({1, 3}, field1.prepare_value(None))
        self.assertSetEqual({1, 3}, field1.prepare_value([]))
        self.assertSetEqual({1, 2, 3}, field1.prepare_value([2]))

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
        # self.assertSetEqual({2}, field2.initial)
        self.assertSetEqual({2}, field2.prepare_value([]))

        clean = field2.clean
        expected = ['1', '2']
        self.assertCountEqual(expected, clean(['1', '2']))
        self.assertCountEqual(expected, clean(['1']))

    def test_forced_values__dict_callable(self):
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
        # self.assertSetEqual({2, 3}, field.initial)
        self.assertSetEqual({2, 3}, field.prepare_value([]))

        choices = [*field.choices]
        self.assertFalse(choices[0][0].readonly)
        self.assertTrue(choices[1][0].readonly)

        self.assertCountEqual(['1', '2', '3'], field.clean(['1', '2']))

    # def test_initial(self):
    #     field = EnhancedMultipleChoiceField(choices=[
    #         (1, 'Sword'),
    #         (2, 'Axes'),
    #         (3, 'Spear'),
    #     ])
    #
    #     field.initial = [2, 1]
    #     self.assertSetEqual({1, 2}, field.initial)
    #
    #     field.initial = None
    #     self.assertFalse(field.initial)
    #
    #     field.forced_values = [1]
    #     field.initial = [2]
    #     self.assertSetEqual({1, 2}, field.initial)

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


class _EnhancedModelMultipleChoiceFieldMixin:
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


class EnhancedModelMultipleChoiceFieldTestCase(_EnhancedModelMultipleChoiceFieldMixin,
                                               CremeTestCase):
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
        # self.assertSetEqual(set(), field.initial)
        self.assertIsNone(field.initial)

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
        expected = [sector1, sector3]
        self.assertCountEqual(expected, clean([sector1.id, sector3.id]))
        self.assertCountEqual(expected, clean([str(sector1.id), str(sector3.id)]))

        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=[])
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)

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
        field = EnhancedModelMultipleChoiceField(queryset=FakeSector.objects.all())

        invalid_pk = self.UNUSED_PK
        self.assertFalse(FakeSector.objects.filter(pk=invalid_pk))

        self.assertFormfieldError(
            field=field, value=[str(invalid_pk)],
            messages=_(
                'Select a valid choice. %(value)s is not one of the available choices.'
            ) % {'value': invalid_pk},
            codes='invalid_choice',
        )

    def test_forced_values(self):
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
        # self.assertSetEqual({sector1.id, sector3.id}, field1.initial)
        self.assertIsNone(field1.prepare_value(None))
        self.assertCountEqual([sector1.id, sector3.id], field1.prepare_value([]))
        self.assertCountEqual(
            [sector1.id, sector2.id, sector3.id], field1.prepare_value([sector2.id]),
        )

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
        expected = [sector1, sector2]
        self.assertCountEqual(expected, clean([sector1.id, sector2.id]))
        self.assertCountEqual(expected, clean([sector1.id]))

    def test_forced_values__to_field_name(self):
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
        expected = [sector1, sector2]
        self.assertCountEqual(expected, clean([sector1.title, sector2.title]))
        self.assertCountEqual(expected, clean([sector1.title]))

        # --
        choices = [*field.choices]
        choice1 = self.assertFoundChoice(sector1.title, sector1.title, choices)
        self.assertFalse(choice1.readonly)

        choice2 = self.assertFoundChoice(sector2.title, sector2.title, choices)
        self.assertTrue(choice2.readonly)

    # def test_initial(self):
    #     field = EnhancedModelMultipleChoiceField(queryset=FakeSector.objects.all())
    #     sector1, sector2 = FakeSector.objects.all()[:2]
    #
    #     field.initial = [sector2.id, sector1.id]
    #     self.assertSetEqual({sector2.id, sector1.id}, field.initial)
    #
    #     field.initial = [sector1.id]
    #     self.assertSetEqual({sector1.id}, field.initial)
    #
    #     field.initial = None
    #     self.assertFalse(field.initial)
    #
    #     field.forced_values = [sector1.id]
    #     field.initial = [sector2.id]
    #     self.assertSetEqual({sector2.id, sector1.id}, field.initial)
    #     self.assertEqual(frozenset([sector1.id]), field.forced_values)

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


class PropertyTypesChoiceFieldTestCase(_EnhancedModelMultipleChoiceFieldMixin,
                                       CremeTestCase):
    def test_default(self):
        field = PropertyTypesChoiceField()
        self.assertEqual(_('Properties'), field.label)
        self.assertTrue(field.required)
        self.assertFalse([*field.queryset])

    def test_required(self):
        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Hot')
        ptype2 = create_ptype(text='Cold')

        label = 'Types to add'
        field = PropertyTypesChoiceField(
            label=label,
            queryset=CremePropertyType.objects.all(),
        )
        self.assertEqual(label, field.label)
        self.assertTrue(field.required)

        ptypes = [*field.queryset]
        self.assertIn(ptype1, ptypes)
        self.assertIn(ptype2, ptypes)

        choices = [(choice.value, label) for choice, label in field.widget.choices]
        self.assertInChoices(value=ptype1.id, label=ptype1.text, choices=choices)
        self.assertInChoices(value=ptype2.id, label=ptype2.text, choices=choices)

        clean = field.clean
        self.assertCountEqual([ptype1], clean([ptype1.id]))
        self.assertCountEqual([ptype2], clean([ptype2.id]))
        self.assertCountEqual([ptype1, ptype2], clean([ptype1.id, ptype2.id]))

        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=[])
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)

    def test_not_required(self):
        ptype = CremePropertyType.objects.create(text='Hot')
        field = PropertyTypesChoiceField(
            queryset=CremePropertyType.objects.all(),
            required=False,
        )
        self.assertFalse(field.required)

        clean = field.clean
        self.assertCountEqual([ptype], clean([ptype.id]))
        self.assertFalse(clean(''))
        self.assertFalse(clean([]))

    def test_forced_values(self):
        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Hot')
        ptype2 = create_ptype(text='Cold')

        field = PropertyTypesChoiceField(queryset=CremePropertyType.objects.all())
        self.assertEqual(frozenset(), field.forced_values)
        self.assertFalse(field.initial)

        field.forced_values = [ptype2.id]
        self.assertEqual(frozenset([ptype2.id]), field.forced_values)
        # self.assertSetEqual({ptype2.id}, field.initial)
        self.assertListEqual([ptype2.id],             field.prepare_value([]))
        self.assertCountEqual([ptype1.id, ptype2.id], field.prepare_value([ptype1.id]))

        # --
        choices = [*field.choices]
        choice1 = self.assertFoundChoice(ptype1.id, ptype1.text, choices)
        self.assertFalse(choice1.readonly)

        choice2 = self.assertFoundChoice(ptype2.id, ptype2.text, choices)
        self.assertTrue(choice2.readonly)


class OrderedMultipleChoiceFieldTestCase(CremeTestCase):
    def test_required(self):
        field = OrderedMultipleChoiceField(
            choices=[(1, 'Sword'), (2, 'Axes'), (3, 'Spear')],
        )
        self.assertTrue(field.required)
        self.assertIsInstance(field.widget, core_widgets.OrderedMultipleChoiceWidget)
        self.assertIsNone(field.initial)

        self.assertListEqual(['1', '3'], field.clean([1, 3]))
        self.assertListEqual(['1', '3'], field.clean(['1', '3']))

        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=[])
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)

    def test_not_required(self):
        field = OrderedMultipleChoiceField(
            choices=[
                {'value': 1, 'label': 'Sword'},
                {'value': 2, 'label': 'Axes'},
                {'value': 3, 'label': 'Spear'},
            ],
            required=False,
        )
        clean = field.clean
        self.assertListEqual(['2'], clean(['2']))
        self.assertFalse([], clean(''))
        self.assertFalse([], clean([]))

    def test_invalid(self):
        self.assertFormfieldError(
            field=OrderedMultipleChoiceField(
                choices=[(1, 'Sword'), (2, 'Axes'), (3, 'Spear')],
            ),
            value=['4'], codes='invalid_choice',
            messages=_(
                "Select a valid choice. %(value)s is not one of the available choices."
            ) % {'value': 4},
        )

    def test_choices01(self):
        "From tuples."
        field = OrderedMultipleChoiceField(
            choices=[(1, 'Sword'), (2, 'Axes'), (3, 'Spear')],
        )

        choices = [*field.choices]
        choice1 = choices[0]
        value1, label1 = choice1
        self.assertEqual('Sword', label1)
        self.assertEqual(1,  value1.value)
        self.assertEqual('', value1.help)
        self.assertFalse(value1.disabled)

        choice2 = choices[1]
        value2, label2 = choice2
        self.assertEqual('Axes', label2)
        self.assertEqual(2, value2.value)

        wchoice = [*field.widget.choices][0]
        self.assertEqual('Sword', wchoice[1])
        self.assertEqual(1,       wchoice[0].value)

    def test_choices02(self):
        """From dict."""
        help_text = 'Stronger than word'
        field = OrderedMultipleChoiceField(
            choices=[
                {'value': 1, 'label': 'Sword'},
                {'value': 2, 'label': 'Axes', 'help': help_text},
                {'value': 3, 'label': 'Spear', 'disabled': True},
            ],
        )

        choices = [*field.choices]
        choice1 = choices[0]
        value1, label1 = choice1
        self.assertEqual('Sword', label1)
        self.assertEqual(1,  value1.value)
        self.assertEqual('', value1.help)
        self.assertIs(value1.disabled, False)

        choice2 = choices[1]
        value2, label2 = choice2
        self.assertEqual('Axes', label2)
        self.assertEqual(2, value2.value)
        self.assertEqual(help_text, value2.help)

        value3, label3 = choices[2]
        self.assertEqual('Spear', label3)
        self.assertEqual(3, value3.value)
        self.assertIs(value3.disabled, True)

        wchoice2 = [*field.widget.choices][1]
        self.assertEqual('Axes', wchoice2[1])
        wid2 = wchoice2[0]
        self.assertEqual(2, wid2.value)
        self.assertEqual(help_text, wid2.help)

    def test_disabled_values(self):
        "Disabled."
        field = OrderedMultipleChoiceField(
            choices=[
                {'value': 1, 'label': 'Sword'},
                {'value': 2, 'label': 'Axes'},
                {'value': 3, 'label': 'Spear', 'disabled': True},
            ],
            required=False,
        )

        # Disabled choice is initially not selected
        self.assertListEqual(['2', '1'], field.clean(['2', '1']))
        self.assertFormfieldError(
            field=field, value=['3'],
            messages=_(
                "Select a valid choice. %(value)s is not one of the available choices."
            ) % {'value': 3},
            codes='invalid_choice',
        )

        # Disabled choice is initially selected
        field.initial = [1, 3]
        self.assertListEqual(['2', '3'], field.clean(['2', '3']))
        self.assertFormfieldError(
            field=field, value=['2'],
            messages=_('The choice %(value)s is mandatory.') % {'value': 3},
            codes='missing_choice',
        )

    def test_iterator(self):
        class CustomIterator(OrderedChoiceIterator):
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

        field = OrderedMultipleChoiceField(
            choices=[(1, 'Sword'), (2, 'Axes')],
            iterator=CustomIterator,
        )

        choice = [*field.choices][0]
        self.assertEqual('The "Sword" weapon', choice[0].help)


class ReadonlyMessageFieldTestCase(CremeTestCase):
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
