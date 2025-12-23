from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from creme.creme_core.forms.custom_field import (
    BooleanMakerField,
    DateMakerField,
    DecimalMakerField,
    IntegerMakerField,
    StringMakerField,
)
from creme.creme_core.gui.custom_field import (
    BooleanMaker,
    DateMaker,
    DecimalMaker,
    IntegerMaker,
    NoneMaker,
    StringMaker,
)

from ..base import CremeTestCase


class IntegerMakerFieldTestCase(CremeTestCase):
    def test_clean(self):
        field = IntegerMakerField()
        maker = field.clean('42')
        self.assertIsInstance(maker, IntegerMaker)
        self.assertEqual(42, maker.make())

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


class BooleanMakerFieldTestCase(CremeTestCase):
    def test_clean(self):
        maker = BooleanMakerField().clean('on')
        self.assertIsInstance(maker, BooleanMaker)
        self.assertEqual(True, maker.make())

    def test_clean__empty(self):
        maker = BooleanMakerField().clean('')
        self.assertIsInstance(maker, BooleanMaker)
        self.assertEqual(False, maker.make())


class DecimalMakerFieldTestCase(CremeTestCase):
    def test_clean(self):
        field = DecimalMakerField()

        str_value = '3.14'
        maker = field.clean(str_value)
        self.assertIsInstance(maker, DecimalMaker)
        self.assertEqual(Decimal(str_value), maker.make())

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


class StringMakerFieldTestCase(CremeTestCase):
    def test_clean(self):
        value = 'Hi'
        field = StringMakerField()
        maker = field.clean(value)
        self.assertIsInstance(maker, StringMaker)
        self.assertEqual(value, maker.make())

    def test_clean__empty__not_required(self):
        field = StringMakerField(required=False)
        self.assertIsInstance(field.clean(''), NoneMaker)

    def test_clean__empty__required(self):
        field = StringMakerField(required=True)
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, value=None, messages=msg, codes='required')
        self.assertFormfieldError(field=field, value='',   messages=msg, codes='required')


class DateMakerFieldTestCase(CremeTestCase):
    def test_clean__not_required(self):
        field = DateMakerField(required=False)

        FIXED = DateMakerField.FIXED
        TODAY = DateMakerField.TODAY
        value = date(2026, 2, 14)
        sub_values = {
            FIXED: self.formfield_value_date(value),
            TODAY: '',
        }

        # Fixed date ---
        maker1 = field.clean((FIXED, sub_values))
        self.assertIsInstance(maker1, DateMaker)
        self.assertEqual(value, maker1.make())

        # Now operator ---
        maker2 = field.clean((TODAY, sub_values))
        self.assertIsInstance(maker2, DateMaker)
        self.assertEqual(date.today(), maker2.make())

        # Empty ---
        self.assertIsInstance(field.clean(('', sub_values)), NoneMaker)
        self.assertIsInstance(field.clean(''), NoneMaker)

    def test_clean__required(self):
        field = DateMakerField()
        self.assertTrue(field.required)

        FIXED = DateMakerField.FIXED
        TODAY = DateMakerField.TODAY
        value = date(2027, 3, 15)
        sub_values = {
            FIXED: self.formfield_value_date(value),
            TODAY: '',
        }

        # Fixed date ---
        maker1 = field.clean((FIXED, sub_values))
        self.assertIsInstance(maker1, DateMaker)
        self.assertEqual(value, maker1.make())

        # Now operator ---
        maker2 = field.clean((TODAY, sub_values))
        self.assertIsInstance(maker2, DateMaker)
        self.assertEqual(date.today(), maker2.make())

        # None ---
        self.assertFormfieldError(
            field=field, value='',
            messages=_('This field is required.'), codes='required',
        )
