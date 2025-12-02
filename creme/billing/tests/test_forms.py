from decimal import Decimal

from django.utils.formats import number_format
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.billing.forms.mass_import import (
    TotalsExtractorField,
    TotalWithoutVatExtractor,
    TotalWithVatExtractor,
    VatExtractor,
)
from creme.billing.tests.base import ProductLine
from creme.creme_core.models import Vat
from creme.creme_core.tests.base import CremeTestCase

MODE_NO_TOTAL = '1'
MODE_COMPUTE_TOTAL_VAT = '2'
MODE_COMPUTE_TOTAL_NO_VAT = '3'
MODE_COMPUTE_VAT = '4'


class TotalsExtractorFieldTestCase(CremeTestCase):
    choices = [(0, 'No column'), (1, 'Column #1'), (2, 'Column #2')]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = cls.create_user()

    def test_extractor__total_with_vat(self):
        extractor = TotalWithVatExtractor(total_no_vat_index=1, vat_index=2)
        self.assertEqual(0, extractor._total_no_vat_index)
        self.assertEqual(1, extractor._vat_index)

        vat = Vat.objects.get_or_create(value=Decimal('10.0'))[0]

        with self.assertNoException():
            pline, errors = extractor.extract_value(
                user=self.user,
                line=[number_format('100.0'), number_format(vat.value)],
            )

        self.assertEqual([], errors)

        self.assertIsInstance(pline, ProductLine)
        self.assertIsNone(pline.pk)
        self.assertEqual(self.user,         pline.user)
        self.assertEqual(_('N/A (import)'), pline.on_the_fly_item)
        self.assertEqual(Decimal('1'),      pline.quantity)
        self.assertEqual(Decimal('0'),      pline.discount)
        self.assertEqual(ProductLine.Discount.PERCENT, pline.discount_unit)
        self.assertEqual(Decimal('100.0'),  pline.unit_price)
        self.assertEqual(vat,               pline.vat_value)

    def test_extractor__total_with_vat__errors(self):
        extractor = TotalWithVatExtractor(
            total_no_vat_index=1, vat_index=2, create_vat=True,
        )

        # Empty VAT ---
        with self.assertNoException():
            pline1, errors1 = extractor.extract_value(
                user=self.user,
                line=[number_format('100.0'), ''],
            )
        self.assertIsNone(pline1)
        self.assertListEqual(
            [_('The VAT value is invalid: {}').format(_('This field is required.'))],
            errors1,
        )

        # Invalid VAT ---
        with self.assertNoException():
            pline2, errors2 = extractor.extract_value(
                user=self.user,
                line=[number_format('100.0'), 'Nan'],
            )
        self.assertIsNone(pline2)
        self.assertListEqual(
            [_('The VAT value is invalid: {}').format(_('Enter a number.'))],
            errors2,
        )

        # Empty Total ---
        with self.assertNoException():
            pline3, errors3 = extractor.extract_value(
                user=self.user,
                line=['', number_format('10.0')],
            )
        self.assertIsNone(pline3)
        self.assertListEqual(
            [_('The total without VAT is invalid: {}').format(_('This field is required.'))],
            errors3,
        )

        # Invalid Total ---
        with self.assertNoException():
            pline4, errors4 = extractor.extract_value(
                user=self.user,
                line=['Nan', number_format('15.0')],
            )
        self.assertIsNone(pline4)
        self.assertListEqual(
            [_('The total without VAT is invalid: {}').format(_('Enter a number.'))],
            errors4,
        )

    def test_extractor__total_without_vat(self):
        extractor = TotalWithoutVatExtractor(total_vat_index=1, vat_index=2)
        self.assertEqual(0, extractor._total_vat_index)
        self.assertEqual(1, extractor._vat_index)

        vat = Vat.objects.get_or_create(value=Decimal('10.5'))[0]

        with self.assertNoException():
            pline, errors = extractor.extract_value(
                user=self.user,
                line=[number_format('221.0'), number_format(vat.value)],
            )

        self.assertEqual([], errors)

        self.assertIsInstance(pline, ProductLine)
        self.assertIsNone(pline.pk)
        self.assertEqual(self.user,         pline.user)
        self.assertEqual(_('N/A (import)'), pline.on_the_fly_item)
        self.assertEqual(Decimal('1'),      pline.quantity)
        self.assertEqual(Decimal('0'),      pline.discount)
        self.assertEqual(ProductLine.Discount.PERCENT, pline.discount_unit)
        self.assertEqual(Decimal('200.0'),  pline.unit_price)
        self.assertEqual(vat,               pline.vat_value)

    def test_extractor__total_without_vat__errors(self):
        extractor = TotalWithoutVatExtractor(
            total_vat_index=1, vat_index=2, create_vat=True,
        )

        # Empty VAT ---
        with self.assertNoException():
            pline1, errors1 = extractor.extract_value(
                user=self.user,
                line=[number_format('100.0'), ''],
            )
        self.assertIsNone(pline1)
        self.assertListEqual(
            [_('The VAT value is invalid: {}').format(_('This field is required.'))],
            errors1,
        )

        # Invalid VAT ---
        with self.assertNoException():
            pline2, errors2 = extractor.extract_value(
                user=self.user,
                line=[number_format('100.0'), 'Nan'],
            )
        self.assertIsNone(pline2)
        self.assertListEqual(
            [_('The VAT value is invalid: {}').format(_('Enter a number.'))],
            errors2,
        )

        # Empty Total ---
        with self.assertNoException():
            pline3, errors3 = extractor.extract_value(
                user=self.user,
                line=['', number_format('10.0')],
            )
        self.assertIsNone(pline3)
        self.assertListEqual(
            [_('The total with VAT is invalid: {}').format(_('This field is required.'))],
            errors3,
        )

        # Invalid Total ---
        with self.assertNoException():
            pline4, errors4 = extractor.extract_value(
                user=self.user,
                line=['Nan', number_format('15.0')],
            )
        self.assertIsNone(pline4)
        self.assertListEqual(
            [_('The total with VAT is invalid: {}').format(_('Enter a number.'))],
            errors4,
        )

    def test_extractor__vat(self):
        extractor = VatExtractor(total_no_vat_index=1, total_vat_index=2)
        self.assertEqual(0, extractor._total_no_vat_index)
        self.assertEqual(1, extractor._total_vat_index)

        vat = Vat.objects.get_or_create(value=Decimal('10'))[0]

        with self.assertNoException():
            pline, errors = extractor.extract_value(
                user=self.user,
                line=[number_format('300.0'), number_format('330.0')],
            )

        self.assertEqual([], errors)

        self.assertIsInstance(pline, ProductLine)
        self.assertIsNone(pline.pk)
        self.assertEqual(self.user,         pline.user)
        self.assertEqual(_('N/A (import)'), pline.on_the_fly_item)
        self.assertEqual(Decimal('1'),      pline.quantity)
        self.assertEqual(Decimal('0'),      pline.discount)
        self.assertEqual(ProductLine.Discount.PERCENT, pline.discount_unit)
        self.assertEqual(Decimal('300.0'),  pline.unit_price)
        self.assertEqual(vat,               pline.vat_value)

    def test_extractor__vat__errors(self):
        extractor = VatExtractor(total_no_vat_index=1, total_vat_index=2)

        # Invalid Total without VAT ---
        with self.assertNoException():
            pline1, errors1 = extractor.extract_value(
                user=self.user,
                line=['Nan', number_format('15.0')],
            )
        self.assertIsNone(pline1)
        self.assertListEqual(
            [_('The total without VAT is invalid: {}').format(_('Enter a number.'))],
            errors1,
        )

        # Invalid Total with VAT ---
        with self.assertNoException():
            pline2, errors2 = extractor.extract_value(
                user=self.user,
                line=[number_format('15.0'), 'Nan'],
            )
        self.assertIsNone(pline2)
        self.assertListEqual(
            [_('The total with VAT is invalid: {}').format(_('Enter a number.'))],
            errors2,
        )

    def test_extractor__total_with_vat__vat_creation(self):
        extractor = TotalWithVatExtractor(
            total_no_vat_index=1, vat_index=2,
            create_vat=True,
        )
        self.assertTrue(extractor.create_vat)

        vat = '10.0'
        self.assertFalse(Vat.objects.filter(value=Decimal(vat)).exists())

        with self.assertNoException():
            pline, errors = extractor.extract_value(
                user=self.user,
                line=[number_format('100.0'), number_format(vat)],
            )

        self.assertEqual([], errors)
        self.assertEqual(Decimal('100.0'), pline.unit_price)

        vat_obj = self.get_object_or_fail(Vat, value=Decimal(vat))
        self.assertEqual(vat_obj, pline.vat_value)

    def test_extractor__total_with_vat__vat_creation__forbidden(self):
        extractor = TotalWithVatExtractor(total_no_vat_index=1, vat_index=2)
        self.assertFalse(extractor.create_vat)

        vat = '10.0'
        self.assertFalse(Vat.objects.filter(value=Decimal(vat)).exists())

        with self.assertNoException():
            pline, errors = extractor.extract_value(
                user=self.user,
                line=[number_format('100.0'), number_format(vat)],
            )

        self.assertIsNone(pline)
        self.assertEqual(
            [
                _('The VAT with value «{}» does not exist and cannot be created').format(
                    number_format(vat),
                ),
            ],
            errors,
        )
        self.assertFalse(Vat.objects.filter(value=Decimal(vat)).exists())

    def test_extractor__total_without_vat__vat_creation(self):
        extractor = TotalWithoutVatExtractor(
            total_vat_index=1, vat_index=2,
            create_vat=True,
        )
        self.assertTrue(extractor.create_vat)

        vat = '10.0'
        self.assertFalse(Vat.objects.filter(value=Decimal(vat)).exists())

        with self.assertNoException():
            pline, errors = extractor.extract_value(
                user=self.user,
                line=[number_format('110.0'), number_format(vat)],
            )

        self.assertEqual([], errors)
        self.assertEqual(Decimal('100.0'), pline.unit_price)

        vat_obj = self.get_object_or_fail(Vat, value=Decimal(vat))
        self.assertEqual(vat_obj, pline.vat_value)

    def test_extractor__total_without_vat__vat_creation__forbidden(self):
        extractor = TotalWithoutVatExtractor(total_vat_index=1, vat_index=2)
        self.assertFalse(extractor.create_vat)

        vat = '10.0'
        self.assertFalse(Vat.objects.filter(value=Decimal(vat)).exists())

        with self.assertNoException():
            pline, errors = extractor.extract_value(
                user=self.user,
                line=[number_format('110.0'), number_format(vat)],
            )

        self.assertIsNone(pline)
        self.assertEqual(
            [
                _('The VAT with value «{}» does not exist and cannot be created').format(
                    number_format(vat),
                ),
            ],
            errors,
        )
        self.assertFalse(Vat.objects.filter(value=Decimal(vat)).exists())

    def test_extractor__vat__vat_creation(self):
        extractor = VatExtractor(
            total_no_vat_index=1, total_vat_index=2,
            create_vat=True,
        )
        self.assertTrue(extractor.create_vat)

        vat = '10.0'
        self.assertFalse(Vat.objects.filter(value=Decimal(vat)).exists())

        with self.assertNoException():
            pline, errors = extractor.extract_value(
                user=self.user,
                line=[number_format('100.0'), number_format('110.0')],
            )

        self.assertEqual([], errors)
        self.assertEqual(Decimal('100.0'), pline.unit_price)

        vat_obj = self.get_object_or_fail(Vat, value=Decimal(vat))
        self.assertEqual(vat_obj, pline.vat_value)

    def test_extractor__vat__vat_creation__forbidden(self):
        extractor = VatExtractor(total_no_vat_index=1, total_vat_index=2)
        self.assertFalse(extractor.create_vat)

        vat = '10.0'
        self.assertFalse(Vat.objects.filter(value=Decimal(vat)).exists())

        with self.assertNoException():
            pline, errors = extractor.extract_value(
                user=self.user,
                line=[number_format('100.0'), number_format('110.00')],
            )

        self.assertIsNone(pline)
        self.assertEqual(
            [
                _('The VAT with value «{}» does not exist and cannot be created').format(
                    number_format(vat),
                ),
            ],
            errors,
        )
        self.assertFalse(Vat.objects.filter(value=Decimal(vat)).exists())

    def test_field__no_total(self):
        field = TotalsExtractorField(choices=self.choices)
        self.assertIsNone(field.clean({'mode': MODE_NO_TOTAL}))

    def test_field__total_no_vat_n_vat(self):
        field1 = TotalsExtractorField(choices=self.choices)

        with self.assertNoException():
            extractor1 = field1.clean({
                'mode': MODE_COMPUTE_TOTAL_VAT,
                'total_no_vat_column_index': 1,
                'vat_column_index': 2,
            })

        self.assertIsInstance(extractor1, TotalWithVatExtractor)
        self.assertEqual(0, extractor1._total_no_vat_index)
        self.assertEqual(1, extractor1._vat_index)

        # Other indexes ---
        field2 = TotalsExtractorField(choices=self.choices)
        extractor2 = field2.clean({
            'mode': MODE_COMPUTE_TOTAL_VAT,
            'total_no_vat_column_index': 2,
            'vat_column_index': 1,
        })
        self.assertEqual(1, extractor2._total_no_vat_index)
        self.assertEqual(0, extractor2._vat_index)

    def test_field__total_vat_n_vat(self):
        field1 = TotalsExtractorField(choices=self.choices)

        with self.assertNoException():
            extractor1 = field1.clean({
                'mode': MODE_COMPUTE_TOTAL_NO_VAT,
                'total_vat_column_index': 1,
                'vat_column_index': 2,
            })

        self.assertIsInstance(extractor1, TotalWithoutVatExtractor)
        self.assertEqual(0, extractor1._total_vat_index)
        self.assertEqual(1, extractor1._vat_index)

        # Other indexes ---
        field2 = TotalsExtractorField(choices=self.choices)
        extractor2 = field2.clean({
            'mode': MODE_COMPUTE_TOTAL_NO_VAT,
            'total_vat_column_index': 2,
            'vat_column_index': 1,
        })
        self.assertEqual(1, extractor2._total_vat_index)
        self.assertEqual(0, extractor2._vat_index)

    def test_field__totals(self):
        field1 = TotalsExtractorField(choices=self.choices)

        with self.assertNoException():
            extractor1 = field1.clean({
                'mode': MODE_COMPUTE_VAT,
                'total_vat_column_index': 1,
                'total_no_vat_column_index': 2,
            })

        self.assertIsInstance(extractor1, VatExtractor)
        self.assertEqual(0, extractor1._total_vat_index)
        self.assertEqual(1, extractor1._total_no_vat_index)

        # Other indexes ---
        field2 = TotalsExtractorField(choices=self.choices)
        extractor2 = field2.clean({
            'mode': MODE_COMPUTE_VAT,
            'total_vat_column_index': 2,
            'total_no_vat_column_index': 1,
        })
        self.assertEqual(1, extractor2._total_vat_index)
        self.assertEqual(0, extractor2._total_no_vat_index)

    def test_field__invalid_mode(self):
        field = TotalsExtractorField(choices=self.choices)

        self.assertFormfieldError(
            field=field, messages='Invalid mode',
            value={
                'mode': '6',
                'total_vat_column_index': 1,
                'total_no_vat_column_index': 2,
            },
        )
        self.assertFormfieldError(
            field=field, messages='Invalid value for mode',
            value={
                'mode': 'nan',
                'total_vat_column_index': 1,
                'total_no_vat_column_index': 2,
            },
        )
        self.assertFormfieldError(
            field=field, messages='Mode is required',
            value={
                # 'mode': '2',
                'total_vat_column_index': 1,
                'total_no_vat_column_index': 2,
            },
        )

    def test_field__invalid_index(self):
        field = TotalsExtractorField(choices=self.choices)
        self.assertFormfieldError(
            field=field,
            value={
                'mode': MODE_COMPUTE_VAT,
                'total_vat_column_index': 'nan',
                'total_no_vat_column_index': 2,
            },
            messages='Index "total_vat_column_index" should be an integer',
        )
        self.assertFormfieldError(
            field=field,
            value={
                'mode': MODE_COMPUTE_VAT,
                # 'total_vat_column_index': 1,
                'total_no_vat_column_index': 2,
            },
            messages='Index "total_vat_column_index" is required',
        )
        self.assertFormfieldError(
            field=field,
            value={
                'mode': MODE_COMPUTE_VAT,
                'total_vat_column_index': 12,
                'total_no_vat_column_index': 2,
            },
            messages='Invalid index',
        )

    def test_field__required_choices(self):
        field = TotalsExtractorField(choices=self.choices)
        msg_fmt = _('You have to select a column for «%(field)s».')
        self.assertFormfieldError(
            field=field,
            value={
                'mode': MODE_COMPUTE_TOTAL_VAT,
                'total_no_vat_column_index': '0',
                'vat_column_index': 2,
            },
            messages=msg_fmt % {'field': _('Total without VAT')},
        )
        self.assertFormfieldError(
            field=field,
            value={
                'mode': MODE_COMPUTE_TOTAL_VAT,
                'total_no_vat_column_index': 1,
                'vat_column_index': '0',
            },
            messages=msg_fmt % {'field': _('VAT')},
        )
        self.assertFormfieldError(
            field=field,
            value={
                'mode': MODE_COMPUTE_TOTAL_NO_VAT,
                'total_vat_column_index': '0',
                'vat_column_index': 2,
            },
            messages=msg_fmt % {'field': _('Total with VAT')},
        )

    def test_field__empty_not_required(self):
        field = TotalsExtractorField(choices=self.choices, required=False)

        with self.assertNoException():
            extractor = field.clean({})

        self.assertIsNone(extractor)

    @parameterized.expand([
        (MODE_COMPUTE_TOTAL_VAT,    'total_no_vat_column_index', 'vat_column_index'),
        (MODE_COMPUTE_TOTAL_NO_VAT, 'total_vat_column_index',    'vat_column_index'),
        (MODE_COMPUTE_VAT,          'total_no_vat_column_index', 'total_vat_column_index'),
    ])
    def test_field__vat_creation(self, mode, index1, index2):
        field = TotalsExtractorField(choices=self.choices)
        self.assertIs(field.can_create_vat, False)
        beware = _('Beware: you are not allowed to create new VAT values')
        self.assertEqual(beware, str(field.help_text))

        field.user = self.user
        self.assertIs(field.can_create_vat, True)
        self.assertEqual('', field.help_text)

        data = {
            'mode': mode,
            index1: 1,
            index2: 2,
        }

        with self.assertNoException():
            extractor1 = field.clean(data)

        self.assertTrue(extractor1.create_vat)

        # ---
        role = self.create_role(
            allowed_apps=['creme_core'],
            admin_4_apps=['persons'],  # creme_core
        )

        field.user = self.build_user(index=1, role=role)
        self.assertIs(field.can_create_vat, False)
        self.assertEqual(beware, str(field.help_text))

        with self.assertNoException():
            extractor2 = field.clean(data)

        self.assertFalse(extractor2.create_vat)
