# -*- coding: utf-8 -*-

try:
    from datetime import datetime

    from django.core.exceptions import ValidationError
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _

    from creme.creme_core.forms.fields import (DateRangeField, ColorField,
                                             DurationField, ChoiceOrCharField)
    from creme.creme_core.utils.date_range import DateRange, CustomRange, CurrentYearRange
    from .base import FieldTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('DateRangeFieldTestCase', 'ColorFieldTestCase',
           'DurationFieldTestCase', 'ChoiceOrCharFieldTestCase',
          )


class DateRangeFieldTestCase(FieldTestCase):
    def test_clean_empty_customized(self):
        clean = DateRangeField().clean
        self.assertFieldValidationError(DateRangeField, 'customized_empty', clean, [u"", u"", u""])
        self.assertFieldValidationError(DateRangeField, 'customized_empty', clean, None)

    def test_start_before_end(self):
        self.assertFieldValidationError(DateRangeField, 'customized_invalid',
                                        DateRangeField().clean, [u"", u"2011-05-16", u"2011-05-15"]
                                       )

    def test_ok01(self):
        drange = DateRangeField().clean(['', '2013-05-29', '2013-06-16'])
        self.assertIsInstance(drange, DateRange)
        self.assertIsInstance(drange, CustomRange)
        self.assertEqual((datetime(year=2013, month=5, day=29, hour=0,  minute=0,  second=0),
                          datetime(year=2013, month=6, day=16, hour=23, minute=59, second=59),
                         ),
                         drange.get_dates(now())
                        )

    def test_ok02(self):
        drange = DateRangeField().clean([CurrentYearRange.name, '', ''])
        self.assertIsInstance(drange, CurrentYearRange)
        self.assertEqual((datetime(year=2013, month=1, day=1,   hour=0,  minute=0,  second=0),
                          datetime(year=2013, month=12, day=31, hour=23, minute=59, second=59),
                         ),
                         drange.get_dates(datetime(year=2013, month=5, day=29, hour=11))
                        )


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
        self.assertFieldValidationError(DurationField, 'invalid', DurationField().clean, [u'a', u'b', u'c'])

    def test_positive01(self):
        self.assertFieldValidationError(DurationField, 'min_value', DurationField().clean,
                                        [u'-1', u'-1', u'-1'], message_args={'limit_value': 0}
                                       )

    def test_ok01(self):
        clean = DurationField().clean
        self.assertEqual('10:2:0', clean([u'10', u'2', u'0']))
        self.assertEqual('10:2:0', clean([10, 2, 0]))


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

    #TODO: set 'Other' label
