import zoneinfo
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.utils.timezone import override as override_tz
from django.utils.translation import gettext as _

from creme.creme_core.core.value_maker import (
    BooleanMaker,
    DateMaker,
    DateTimeMaker,
    DecimalMaker,
    IntegerMaker,
    NoneMaker,
    StringMaker,
)
from creme.creme_core.forms.value_maker import (
    BooleanMakerField,
    DateMakerField,
    DateTimeMakerField,
    DecimalMakerField,
    IntegerMakerField,
    StringMakerField,
)

from ..base import CremeTestCase


class IntegerMakerFieldTestCase(CremeTestCase):
    def test_clean(self):
        self.assertEqual(IntegerMaker(42), IntegerMakerField().clean('42'))

    def test_clean__empty__required(self):
        field = IntegerMakerField(required=True)
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, value=None, messages=msg, codes='required')
        self.assertFormfieldError(field=field, value='',   messages=msg, codes='required')

    def test_clean__empty__not_required(self):
        field = IntegerMakerField(required=False)
        self.assertIsInstance(field.clean(''), NoneMaker)

    def test_clean__invalid_data(self):
        self.assertFormfieldError(
            field=IntegerMakerField(),
            value='not_int',
            messages=_('Enter a whole number.'), codes='invalid',
        )

    def test_prepare_value(self):
        field = IntegerMakerField()
        value = 26
        self.assertEqual(value, field.prepare_value(IntegerMaker(value)))
        self.assertIsNone(field.prepare_value(NoneMaker()))


class BooleanMakerFieldTestCase(CremeTestCase):
    def test_clean(self):
        self.assertEqual(BooleanMaker(True), BooleanMakerField().clean('on'))

    def test_clean__empty(self):
        self.assertEqual(BooleanMaker(False), BooleanMakerField().clean(''))

    def test_prepare_value(self):
        field = BooleanMakerField()
        self.assertEqual(True, field.prepare_value(BooleanMaker(True)))
        self.assertIsNone(field.prepare_value(NoneMaker()))


class DecimalMakerFieldTestCase(CremeTestCase):
    def test_clean(self):
        field = DecimalMakerField()
        str_value = '3.14'
        self.assertEqual(DecimalMaker(str_value), field.clean(str_value))

    def test_clean__empty__required(self):
        field = DecimalMakerField(required=True)
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, value=None, messages=msg, codes='required')
        self.assertFormfieldError(field=field, value='',   messages=msg, codes='required')

    def test_clean__empty__not_required(self):
        self.assertIsInstance(DecimalMakerField(required=False).clean(''), NoneMaker)

    def test_clean__invalid_data(self):
        self.assertFormfieldError(
            field=DecimalMakerField(),
            value='not_decimal',
            messages=_('Enter a number.'), codes='invalid',
        )

    def test_clean__nan(self):
        self.assertFormfieldError(
            field=DecimalMakerField(),
            value='nan',
            messages=_('Enter a number.'), codes='invalid',
        )

    def test_validators(self):
        message = 'Too small'

        def too_small(value):
            if value < Decimal('0.2'):
                raise ValidationError(message)

        field = DecimalMakerField(validators=[too_small])
        self.assertIsInstance(field.clean('1.00'), DecimalMaker)
        self.assertFormfieldError(field=field, value='0.1', messages=message)

    def test_prepare_value(self):
        field = DecimalMakerField()
        str_value = '13.37'
        value = Decimal(str_value)
        self.assertEqual(value, field.prepare_value(DecimalMaker(str_value)))

        # ---
        self.assertIsNone(field.prepare_value(NoneMaker()))


class StringMakerFieldTestCase(CremeTestCase):
    def test_clean(self):
        value = 'Hi'
        self.assertEqual(StringMaker(value), StringMakerField().clean(value))

    def test_clean__empty__not_required(self):
        field = StringMakerField(required=False)
        self.assertIsInstance(field.clean(''), NoneMaker)

    def test_clean__empty__required(self):
        field = StringMakerField(required=True)
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, value=None, messages=msg, codes='required')
        self.assertFormfieldError(field=field, value='',   messages=msg, codes='required')

    def test_prepare_value(self):
        field = StringMakerField()
        value = 'Hi Barbie'
        self.assertEqual(value, field.prepare_value(StringMaker(value)))

        # ---
        self.assertIsNone(field.prepare_value(NoneMaker()))


class DateMakerFieldTestCase(CremeTestCase):
    def test_clean__not_required(self):
        field = DateMakerField(required=False)

        FIXED = DateMakerField.FIXED
        TODAY = DateMakerField.TODAY
        date_obj = date(2026, 2, 14)
        sub_values = {FIXED: self.formfield_value_date(date_obj), TODAY: ''}

        # Fixed date ---
        self.assertEqual(
            DateMaker.from_date(date_obj), field.clean((FIXED, sub_values)),
        )

        # Now operator ---
        self.assertEqual(
            DateMaker.from_operator('today'), field.clean((TODAY, sub_values)),
        )

        # Empty ---
        self.assertIsInstance(field.clean(('', sub_values)), NoneMaker)
        self.assertIsInstance(field.clean(''), NoneMaker)

    def test_clean__required(self):
        field = DateMakerField()
        self.assertTrue(field.required)

        FIXED = DateMakerField.FIXED
        TODAY = DateMakerField.TODAY
        date_obj = date(2027, 3, 15)
        sub_values = {FIXED: self.formfield_value_date(date_obj), TODAY: ''}

        # Fixed date ---
        self.assertEqual(
            DateMaker.from_date(date_obj), field.clean((FIXED, sub_values)),
        )

        # Now operator ---
        self.assertEqual(
            DateMaker.from_operator('today'), field.clean((TODAY, sub_values)),
        )

        # None ---
        self.assertFormfieldError(
            field=field, value='',
            messages=_('This field is required.'), codes='required',
        )

    def test_prepare_value(self):
        field = DateMakerField()

        # ---
        FIXED = DateTimeMakerField.FIXED
        date_obj = date(year=2028, month=6, day=15)
        self.assertTupleEqual(
            (FIXED, {FIXED: (date_obj)}),
            field.prepare_value(DateMaker.from_date(date_obj))
        )

        # ---
        TODAY = DateMakerField.TODAY
        self.assertTupleEqual(
            (TODAY, {TODAY: 'today'}),
            field.prepare_value(DateMaker.from_operator('today'))
        )

        # ---
        self.assertIsNone(field.prepare_value(NoneMaker()))


class DateTimeMakerFieldTestCase(CremeTestCase):
    def test_clean__not_required(self):
        field = DateTimeMakerField(required=False)

        FIXED = DateTimeMakerField.FIXED
        NOW = DateTimeMakerField.NOW
        dt = self.create_datetime(year=2026, month=5, day=28, hour=13)
        sub_values = {FIXED: self.formfield_value_datetime(dt), NOW: ''}

        # Fixed datetime ---
        self.assertEqual(
            DateTimeMaker.from_datetime(dt), field.clean((FIXED, sub_values)),
        )

        # Now operator ---
        self.assertEqual(
            DateTimeMaker.from_operator('now'), field.clean((NOW, sub_values)),
        )

        # Empty ---
        self.assertIsInstance(field.clean(('', sub_values)), NoneMaker)
        self.assertIsInstance(field.clean(''), NoneMaker)

    def test_clean__required(self):
        field = DateTimeMakerField()
        self.assertTrue(field.required)

        FIXED = DateTimeMakerField.FIXED
        NOW = DateTimeMakerField.NOW
        dt = self.create_datetime(year=2028, month=6, day=15, hour=12)
        sub_values = {FIXED: self.formfield_value_datetime(dt), NOW: ''}

        # Fixed date ---
        maker1 = field.clean((FIXED, sub_values))
        self.assertIsInstance(maker1, DateTimeMaker)
        self.assertEqual(dt, maker1.make())

        # Now operator ---
        maker2 = field.clean((NOW, sub_values))
        self.assertIsInstance(maker2, DateTimeMaker)
        self.assertDatetimesAlmostEqual(now(), maker2.make())

        # None ---
        self.assertFormfieldError(
            field=field, value='',
            messages=_('This field is required.'), codes='required',
        )

    @override_tz('Europe/Paris')
    def test_prepare_value(self):
        field = DateTimeMakerField()

        # ---
        FIXED = DateTimeMakerField.FIXED
        dt = self.create_datetime(year=2028, month=6, day=15, hour=12, utc=True)
        prep = field.prepare_value(DateTimeMaker.from_datetime(dt))
        self.assertTupleEqual((FIXED, {FIXED: dt}), prep)
        self.assertEqual(zoneinfo.ZoneInfo('Europe/Paris'), prep[1][FIXED].tzinfo)

        # ---
        NOW = DateTimeMakerField.NOW
        self.assertTupleEqual(
            (NOW, {NOW: 'now'}),
            field.prepare_value(DateTimeMaker.from_operator('now')),
        )

        # ---
        self.assertIsNone(field.prepare_value(NoneMaker()))
