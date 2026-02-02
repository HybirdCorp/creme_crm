from datetime import date
from decimal import Decimal
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.utils.formats import number_format
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED
from creme.billing.forms.mass_import import (
    TotalsExtractorField,
    TotalWithoutVatExtractor,
    TotalWithVatExtractor,
    VatExtractor,
)
from creme.billing.models import (
    InvoiceStatus,
    NumberGeneratorItem,
    QuoteStatus,
    SalesOrderStatus,
)
from creme.billing.setting_keys import emitter_edition_key
from creme.creme_core.models import Currency, SettingValue, Vat
from creme.creme_core.tests.views.base import MassImportBaseTestCaseMixin
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)

from ..base import (
    Address,
    Contact,
    Invoice,
    Organisation,
    ProductLine,
    Quote,
    SalesOrder,
    _BillingTestCase,
    skipIfCustomInvoice,
    skipIfCustomQuote,
    skipIfCustomSalesOrder,
)

MODE_NO_TOTAL = '1'
MODE_COMPUTE_TOTAL_VAT = '2'
MODE_COMPUTE_TOTAL_NO_VAT = '3'
MODE_COMPUTE_VAT = '4'


class TotalsExtractorFieldTestCase(_BillingTestCase):
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


@skipIfCustomOrganisation
class _BaseMassImportTestCase(MassImportBaseTestCaseMixin, _BillingTestCase):
    @override_settings(SOFTWARE_LABEL='My CRM')
    def _aux_test_csv_import_no_total(self, *, user, model, status_model,
                                      update=False,
                                      # number_help_text=True,
                                      creation_number_help_text=True,
                                      ):
        count = model.objects.count()
        create_orga = partial(Organisation.objects.create, user=user)
        create_contact = partial(Contact.objects.create, user=user)

        # Sources --------------------------------------------------------------
        source1 = create_orga(name='Nerv')

        source2_name = 'Seele'
        self.assertFalse(Organisation.objects.filter(name=source2_name))

        # Targets --------------------------------------------------------------
        target1 = create_orga(name='Acme')
        # TODO: factorise
        create_addr = partial(Address.objects.create, owner=target1)
        target1.shipping_address = create_addr(
            name='ShippingAddr', address='Temple of fire',
            po_box='6565', zipcode='789', city='Konoha',
            department='dep1', state='Stuff', country='Land of Fire',
        )
        target1.billing_address = create_addr(
            name='BillingAddr', address='Temple of sand',
            po_box='8778', zipcode='123', city='Suna',
            department='dep2', state='Foo', country='Land of Sand',
        )
        target1.save()

        target2_name = 'NHK'
        self.assertFalse(Organisation.objects.filter(name=target2_name))

        target3 = create_contact(last_name='Ayanami', first_name='Rei')

        target4_last_name = 'Katsuragi'
        self.assertFalse(Contact.objects.filter(last_name=target4_last_name))

        # ----------------------------------------------------------------------

        lines_count = 4
        names = [f'Billdoc #{i:04}' for i in range(1, lines_count + 1)]
        numbers = [f'B{i:04}' for i in range(1, lines_count + 1)]
        issuing_dates = [
            date(year=2013, month=6 + i, day=24 + i)
            for i in range(lines_count)
        ]

        lines = [
            (
                names[0], numbers[0],
                self.formfield_value_date(issuing_dates[0]),
                source1.name, target1.name, '',
            ),
            (
                names[1], numbers[1],
                self.formfield_value_date(issuing_dates[1]),
                source2_name, target2_name, '',
            ),
            (
                names[2], numbers[2],
                self.formfield_value_date(issuing_dates[2]),
                source2_name, '', target3.last_name,
            ),
            (
                names[3], numbers[3],
                self.formfield_value_date(issuing_dates[3]),
                source2_name, '', target4_last_name,
            ),
        ]

        doc = self._build_csv_doc(lines, user=user)
        url = self._build_import_url(model)

        # STEP 1 ---
        self.assertGET200(url)

        response1 = self.client.post(
            url,
            data={
                'step': 0,
                'document': doc.id,
                # has_header
            }
        )
        self.assertNoFormError(response1)

        with self.assertNoException():
            number_f = response1.context['form'].fields['number']

        # if number_help_text:
        #     self.assertEqual(
        #         _(
        #             'If you chose an organisation managed by {software} as source organisation, '
        #             'a number will be automatically generated for created «{models}».'
        #         ).format(software='My CRM', models=model._meta.verbose_name_plural),
        #         number_f.help_text,
        #     )
        # else:
        #     self.assertFalse(number_f.help_text)
        help_start = _(
            'If you chose an organisation managed by {software} as source organisation, '
            'a number will be automatically generated for created «{models}».'
        ).format(software='My CRM', models=model._meta.verbose_name_plural)
        if creation_number_help_text:
            self.assertStartsWith(number_f.help_text, help_start)
        else:
            if number_f.help_text.startswith(help_start):
                self.failureException(
                    f'The string {number_f.help_text!r} starts with {help_start!r}'
                )

        # STEP 2 ---
        def_status = status_model.objects.all()[0]
        def_currency = Currency.objects.all()[0]
        data = {
            'step':     1,
            'document': doc.id,
            # has_header

            'user': user.id,
            'key_fields': ['name'] if update else [],

            'name_colselect':   1,
            'number_colselect': 2,

            'issuing_date_colselect':    3,
            'expiration_date_colselect': 0,

            'status_colselect': 0,
            'status_defval':    def_status.pk,

            'discount_colselect': 0,
            'discount_defval':    '0',

            'currency_colselect': 0,
            'currency_defval':    def_currency.pk,

            'acceptation_date_colselect': 0,

            'comment_colselect':         0,
            'additional_info_colselect': 0,
            'payment_terms_colselect':   0,
            'payment_type_colselect':    0,

            'description_colselect':         0,
            'buyers_order_number_colselect': 0,  # Invoice only...

            'totals_mode': '1',  # No totals

            # 'property_types',
            # 'fixed_relations',
            # 'dyn_relations',
        }
        response2 = self.assertPOST200(url, data=data)
        self.assertFormError(
            response2.context['form'],
            field='source', errors=_('Enter a valid value.'),
        )

        response3 = self.assertPOST200(
            url,
            data={
                **data,
                'source_persons_organisation_colselect': 0,
                'source_persons_organisation_create':    True,

                'target_persons_organisation_colselect': 0,
                'target_persons_organisation_create':    True,

                'target_persons_contact_colselect': 0,
                'target_persons_contact_create':    True,
            },
        )
        self.assertFormError(
            response3.context['form'],
            field='source', errors=_('This field is required.'),
        )

        response4 = self.client.post(
            url, follow=True,
            data={
                **data,
                'source_persons_organisation_colselect': 4,
                'source_persons_organisation_create':    True,

                'target_persons_organisation_colselect': 5,
                'target_persons_organisation_create':    True,

                'target_persons_contact_colselect': 6,
                'target_persons_contact_create':    True,
            },
        )
        self.assertNoFormError(response4)

        self._execute_job(response4)
        self.assertEqual(count + len(lines), model.objects.count())

        billing_docs = []

        for i, l in enumerate(lines):
            billing_doc = self.get_object_or_fail(model, name=names[i])
            billing_docs.append(billing_doc)

            self.assertEqual(user,             billing_doc.user)
            self.assertEqual(numbers[i],       billing_doc.number)
            self.assertEqual(issuing_dates[i], billing_doc.issuing_date)
            self.assertIsNone(billing_doc.expiration_date)
            self.assertEqual(def_status,     billing_doc.status)
            self.assertEqual(Decimal('0.0'), billing_doc.discount)
            self.assertEqual(def_currency,   billing_doc.currency)
            self.assertEqual('',             billing_doc.comment)
            self.assertIsNone(billing_doc.additional_info)
            self.assertIsNone(billing_doc.payment_terms)
            # self.assertIsNone(billing_doc.payment_type) #only in invoice... TODO lambda ??

            self.assertEqual(Decimal('0.0'), billing_doc.total_vat)
            self.assertEqual(Decimal('0.0'), billing_doc.total_no_vat)
            self.assertFalse([*billing_doc.iter_all_lines()])

        # Billing_doc1
        billing_doc1 = billing_docs[0]
        imp_source1 = billing_doc1.source
        self.assertIsNotNone(imp_source1)
        self.assertEqual(source1, imp_source1.get_real_entity())

        imp_target1 = billing_doc1.target
        self.assertIsNotNone(imp_target1)
        self.assertEqual(target1, imp_target1.get_real_entity())

        shipping_address = billing_doc1.shipping_address
        self.assertAddressContentEqual(target1.shipping_address, shipping_address)
        self.assertEqual(billing_doc1, shipping_address.owner)

        billing_address = billing_doc1.billing_address
        self.assertAddressContentEqual(target1.billing_address, billing_address)
        self.assertEqual(billing_doc1, billing_address.owner)

        # Billing_doc2
        billing_doc2 = billing_docs[1]
        imp_source2 = billing_doc2.source
        self.assertIsNotNone(imp_source2)
        source2 = self.get_object_or_fail(Organisation, name=source2_name)
        self.assertEqual(imp_source2.get_real_entity(), source2)

        imp_target2 = billing_doc2.target
        self.assertIsNotNone(imp_target2)
        target2 = self.get_object_or_fail(Organisation, name=target2_name)
        self.assertEqual(imp_target2.get_real_entity(), target2)

        # Billing_doc3
        imp_target3 = billing_docs[2].target
        self.assertIsNotNone(imp_target3)
        self.assertEqual(target3, imp_target3.get_real_entity())

        # Billing_doc4
        imp_target4 = billing_docs[3].target
        self.assertIsNotNone(imp_target4)
        target4 = self.get_object_or_fail(Contact, last_name=target4_last_name)
        self.assertEqual(imp_target4.get_real_entity(), target4)

    def _aux_test_csv_import_total_no_vat_n_vat(self, *, user, model, status_model):
        count = model.objects.count()

        create_orga = partial(Organisation.objects.create, user=user)
        src = create_orga(name='Nerv')
        tgt = create_orga(name='Acme')

        vat1 = 15
        vat_obj1 = Vat.objects.get_or_create(value=vat1)[0]
        vat2 = '12.5'
        self.assertFalse(Vat.objects.filter(value=vat2).exists())
        vat_count = Vat.objects.count()

        total_no_vat1 = 100
        total_no_vat2 = '200.5'

        lines = [
            ('Bill #1', src.name, tgt.name, number_format(total_no_vat1), number_format(vat1)),
            ('Bill #2', src.name, tgt.name, number_format(total_no_vat2), number_format(vat2)),
            ('Bill #3', src.name, tgt.name, '300',                        'nan'),
        ]
        doc = self._build_csv_doc(lines, user=user)
        response = self.client.post(
            self._build_import_url(model),
            follow=True,
            data={
                'step':     1,
                'document': doc.id,
                # has_header

                'user': user.id,
                # 'key_fields': ['name'] if update else [],

                'name_colselect':   1,
                'number_colselect': 0,

                'issuing_date_colselect':    0,
                'expiration_date_colselect': 0,

                'status_colselect': 0,
                'status_defval':    status_model.objects.all()[0].pk,

                'discount_colselect': 0,
                'discount_defval':    '0',

                'currency_colselect': 0,
                'currency_defval':    Currency.objects.all()[0].pk,

                'acceptation_date_colselect': 0,

                'comment_colselect':         0,
                'additional_info_colselect': 0,
                'payment_terms_colselect':   0,
                'payment_type_colselect':    0,

                'description_colselect':         0,
                'buyers_order_number_colselect': 0,  # Invoice only...

                'source_persons_organisation_colselect': 2,
                'target_persons_organisation_colselect': 3,
                'target_persons_contact_colselect': 0,

                'totals_mode': '2',  # Compute total with VAT
                'totals_total_no_vat_colselect': 4,
                'totals_vat_colselect': 5,

                # 'property_types',
                # 'fixed_relations',
                # 'dyn_relations',
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertEqual(count + len(lines), model.objects.count())

        billing_doc1 = self.get_object_or_fail(model, name=lines[0][0])
        self.assertEqual(Decimal('0.0'),         billing_doc1.discount)
        self.assertEqual(Decimal(total_no_vat1), billing_doc1.total_no_vat)
        self.assertEqual(Decimal('115.00'),      billing_doc1.total_vat)

        line1 = self.get_alone_element(billing_doc1.iter_all_lines())
        self.assertIsInstance(line1, ProductLine)
        self.assertEqual(_('N/A (import)'), line1.on_the_fly_item)
        self.assertFalse(line1.comment)
        self.assertEqual(1, line1.quantity)
        self.assertEqual(total_no_vat1, line1.unit_price)
        self.assertFalse(line1.unit)
        self.assertEqual(0, line1.discount)
        self.assertEqual(ProductLine.Discount.PERCENT, line1.discount_unit)
        self.assertEqual(vat_obj1, line1.vat_value)

        billing_doc2 = self.get_object_or_fail(model, name=lines[1][0])
        self.assertEqual(Decimal(total_no_vat2), billing_doc2.total_no_vat)
        self.assertEqual(Decimal('225.56'),      billing_doc2.total_vat)

        self.assertEqual(vat_count + 1, Vat.objects.count())
        line2 = self.get_alone_element(billing_doc2.iter_all_lines())
        self.assertEqual(Decimal(total_no_vat2), line2.unit_price)
        self.assertEqual(Decimal(vat2),          line2.vat_value.value)

        billing_doc3 = self.get_object_or_fail(model, name=lines[2][0])
        self.assertEqual(Decimal('0'), billing_doc3.total_no_vat)
        self.assertEqual(Decimal('0'), billing_doc3.total_vat)
        self.assertFalse([*billing_doc3.iter_all_lines()])

        results = self._get_job_results(job)
        self.assertEqual(len(lines), len(results))

        jr_error3 = self.get_alone_element(r for r in results if r.entity_id == billing_doc3.id)
        self.assertListEqual(
            [_('The VAT value is invalid: {}').format(_('Enter a number.'))],
            jr_error3.messages,
        )

    def _aux_test_csv_import_update(self, *, user, model, status_model,
                                    target_billing_address=True,
                                    # override_billing_addr=False,
                                    # override_shipping_addr=False,
                                    ):
        create_orga = partial(Organisation.objects.create, user=user)

        source1 = create_orga(name='Nerv')
        self._set_managed(source1)  # Edition is allowed
        source2 = create_orga(name='Seele')

        item = self.get_object_or_fail(
            NumberGeneratorItem,
            numbered_type=ContentType.objects.get_for_model(model),
            organisation=source1,
        )
        self.assertTrue(item.is_edition_allowed)

        target1 = create_orga(name='Acme1')
        target2 = create_orga(name='Acme2')

        def_status = status_model.objects.all()[0]
        bdoc = model.objects.create(
            user=user, name='Billdoc #1', status=def_status,
            source=source1,
            target=target1,
        )

        create_addr = Address.objects.create
        if target_billing_address:
            target2.billing_address = b_addr1 = create_addr(
                owner=target2,
                name='BillingAddr1', address='Temple of sand', city='Suna',
            )
        else:
            b_addr1 = Address(address=_('Billing address'))

        target2.shipping_address = s_addr1 = create_addr(
            owner=target2,
            name='ShippingAddr1', address='Temple of fire', city='Konoha',
        )
        target2.save()

        bdoc.billing_address = b_addr2 = create_addr(
            owner=bdoc,
            name='BillingAddr22', address='Temple of rain', city='Kiri',
        )
        bdoc.shipping_address = s_addr2 = create_addr(
            owner=bdoc,
            name='ShippingAddr2', address='Temple of lightning', city='Kumo',
        )
        bdoc.save()

        # addr_count = Address.objects.count()

        number = 'B0001'
        doc = self._build_csv_doc(
            [(bdoc.name, number, source2.name, target2.name)],
            user=user,
        )
        response = self.client.post(
            self._build_import_url(model), follow=True,
            data={
                'step':     1,
                'document': doc.id,

                'user': user.id,
                'key_fields': ['name'],

                'name_colselect':   1,
                'number_colselect': 2,

                'issuing_date_colselect':    0,
                'expiration_date_colselect': 0,

                'status_colselect': 0,
                'status_defval':    def_status.pk,

                'discount_colselect': 0,
                'discount_defval':    '0',

                'currency_colselect': 0,
                'currency_defval':    Currency.objects.first().pk,

                'acceptation_date_colselect': 0,

                'comment_colselect':         0,
                'additional_info_colselect': 0,
                'payment_terms_colselect':   0,
                'payment_type_colselect':    0,

                'description_colselect':         0,
                'buyers_order_number_colselect': 0,

                'source_persons_organisation_colselect': 3,
                'source_persons_organisation_create':    True,
                'target_persons_organisation_colselect': 4,
                'target_persons_organisation_create':    True,
                'target_persons_contact_colselect':      0,
                # 'target_persons_contact_create':         True,

                # 'override_billing_addr':  'on' if override_billing_addr else '',
                # 'override_shipping_addr': 'on' if override_shipping_addr else '',
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)
        bdoc = self.refresh(bdoc)
        self.assertEqual(number, bdoc.number)

        self.assertHaveRelation(subject=bdoc, type=REL_SUB_BILL_ISSUED, object=source2)
        self.assertHaveNoRelation(subject=bdoc, type=REL_SUB_BILL_ISSUED, object=source1)

        self.assertHaveRelation(subject=bdoc, type=REL_SUB_BILL_RECEIVED, object=target2)
        self.assertHaveNoRelation(subject=bdoc, type=REL_SUB_BILL_RECEIVED, object=target1)

        b_addr = bdoc.billing_address
        self.assertIsNotNone(b_addr)
        self.assertEqual(bdoc, b_addr.owner)

        s_addr = bdoc.shipping_address
        self.assertIsNotNone(s_addr)
        self.assertEqual(bdoc, s_addr.owner)

        # if target_billing_address:
        #     expected_b_addr = b_addr1 if override_billing_addr else b_addr2
        #     self.assertEqual(expected_b_addr.address, b_addr.address)
        #     self.assertEqual(expected_b_addr.city,    b_addr.city)
        # else:
        #     self.assertEqual(b_addr2, b_addr)  # No change
        self.assertEqual(b_addr1.address, b_addr.address)
        self.assertEqual(b_addr1.city,    b_addr.city)

        # expected_s_addr = s_addr1 if override_shipping_addr else s_addr2
        # self.assertEqual(expected_s_addr.address, s_addr.address)
        # self.assertEqual(expected_s_addr.city,    s_addr.city)
        self.assertEqual(s_addr1.address, s_addr.address)
        self.assertEqual(s_addr1.city,    s_addr.city)

        # No new Address should be created
        # self.assertEqual(addr_count, Address.objects.count())
        self.assertDoesNotExist(b_addr2)
        self.assertDoesNotExist(s_addr2)

    # model, status_model,
    def _aux_test_csv_import_update__emitter_edition(self, *, user, model,
                                                     emitter_edition_ok=True,
                                                     ):
        create_orga = partial(Organisation.objects.create, user=user)
        src1 = create_orga(name='SRC-1')
        src2 = create_orga(name='SRC-2')
        tgt = create_orga(name='TGT')

        create_bdoc = partial(model.objects.create, user=user, source=src1, target=tgt)
        bdoc1 = create_bdoc(name='Bill #001')
        bdoc2 = create_bdoc(name='Bill #002', number='#122')
        bdoc3 = create_bdoc(name='Bill #003', number='#123')

        count = model.objects.count()

        description = 'Imported from CSV'
        lines = [
            (bdoc1.name, src2.name, tgt.name, description),  # No number => OK
            (bdoc2.name, src1.name, tgt.name, description),  # No emitter change => OK
            (bdoc3.name, src2.name, tgt.name, description),  # => Error is some cases
        ]
        doc = self._build_csv_doc(lines, user=user)
        response = self.client.post(
            self._build_import_url(model),
            follow=True,
            data={
                'step':     1,
                'document': doc.id,

                'user': user.id,
                'key_fields': ['name'],

                'name_colselect':   1,
                'number_colselect': 0,

                'issuing_date_colselect':    0,
                'expiration_date_colselect': 0,

                'status_colselect': 0,
                'status_defval':    bdoc1.status_id,

                'discount_colselect': 0,
                'discount_defval':    '0',

                'currency_colselect': 0,
                'currency_defval':    bdoc1.currency_id,

                'acceptation_date_colselect': 0,

                'comment_colselect':         0,
                'additional_info_colselect': 0,
                'payment_terms_colselect':   0,
                'payment_type_colselect':    0,

                'description_colselect':         4,
                'buyers_order_number_colselect': 0,  # Invoice only

                'source_persons_organisation_colselect': 2,
                'target_persons_organisation_colselect': 3,
                'target_persons_contact_colselect': 0,

                'totals_mode': '1',
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertEqual(count, model.objects.count())

        bdoc1 = self.refresh(bdoc1)
        self.assertEqual(description, bdoc1.description)
        self.assertEqual(src2,        bdoc1.source)

        self.assertEqual(description, self.refresh(bdoc2).description)

        j_results = self._get_job_results(job)
        self.assertEqual(len(lines), len(j_results))

        j_result1 = j_results[0]
        self.assertEqual(bdoc1.id, j_result1.entity_id)
        self.assertFalse(j_result1.messages)

        j_result2 = j_results[1]
        self.assertEqual(bdoc2.id, j_result2.entity_id)
        self.assertFalse(j_result2.messages)

        bdoc3 = self.refresh(bdoc3)
        j_result3 = j_results[2]
        if emitter_edition_ok:
            self.assertEqual(description, bdoc3.description)
            self.assertEqual(src2,        bdoc3.source)

            self.assertEqual(bdoc3.id, j_result3.entity_id)
            self.assertFalse(j_result3.messages)
        else:
            self.assertFalse(bdoc3.description)
            self.assertEqual(src1, bdoc3.source)  # No change

            # self.assertEqual(bdoc2.id, j_result3.entity_id) TODO?
            self.assertIsNone(j_result3.entity_id)
            self.assertListEqual(
                [_('Your configuration forbids you to edit the source Organisation')],
                j_result3.messages,
            )


@skipIfCustomInvoice
class MassImportInvoiceTestCase(_BaseMassImportTestCase):
    @skipIfCustomAddress
    def test_no_total(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_no_total(
            user=user, model=Invoice, status_model=InvoiceStatus,
            # number_help_text=False,
            creation_number_help_text=False,
        )

    def test_total_no_vat_n_vat(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_total_no_vat_n_vat(
            user=user, model=Invoice, status_model=InvoiceStatus,
        )

    @skipIfCustomAddress
    def test_update__target_has_address(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_update(
            user=user,
            model=Invoice, status_model=InvoiceStatus,
            target_billing_address=True,
        )

    @skipIfCustomAddress
    def test_update__target_has_no_address(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_update(
            user=user,
            model=Invoice, status_model=InvoiceStatus,
            target_billing_address=False,
        )

    @skipIfCustomAddress
    def test_update_total__no_total(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_no_total(
            user=user,
            model=Invoice, status_model=InvoiceStatus,
            update=True,
            creation_number_help_text=False,
        )

    def test_update_total__error(self):
        user = self.login_as_root_and_get()
        doc = self._build_csv_doc([('Bill #1', 'Nerv', 'Acme', '300', '15')], user=user)
        response = self.assertPOST200(
            self._build_import_url(Invoice),
            follow=True,
            data={
                'step':     1,
                'document': doc.id,
                # has_header

                'user': user.id,
                'key_fields': ['name'],

                'name_colselect':   1,
                'number_colselect': 0,

                'issuing_date_colselect':    0,
                'expiration_date_colselect': 0,

                'status_colselect': 0,
                'status_defval':    InvoiceStatus.objects.all()[0].pk,

                'discount_colselect': 0,
                'discount_defval':    '0',

                'currency_colselect': 0,
                'currency_defval':    Currency.objects.all()[0].pk,

                'acceptation_date_colselect': 0,

                'comment_colselect':         0,
                'additional_info_colselect': 0,
                'payment_terms_colselect':   0,
                'payment_type_colselect':    0,

                'description_colselect':         0,
                'buyers_order_number_colselect': 0,  # Invoice only...

                'source_persons_organisation_colselect': 2,
                'target_persons_organisation_colselect': 3,
                'target_persons_contact_colselect': 0,

                'totals_mode': '2',  # Compute total with VAT
                'totals_total_no_vat_colselect': 4,
                'totals_vat_colselect': 5,

                # 'property_types',
                # 'fixed_relations',
                # 'dyn_relations',
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='totals',
            errors=_('You cannot compute totals in update mode.'),
        )

    def test_emitter_edition(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_update__emitter_edition(
            user=user, model=Invoice, emitter_edition_ok=False,
        )

    def test_emitter_edition__error(self):
        SettingValue.objects.set_4_key(emitter_edition_key, True)

        user = self.login_as_root_and_get()
        self._aux_test_csv_import_update__emitter_edition(
            user=user, model=Invoice, emitter_edition_ok=True,
        )


@skipIfCustomQuote
class MassImportQuoteTestCase(_BaseMassImportTestCase):
    @skipIfCustomAddress
    def test_no_total(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_no_total(user=user, model=Quote, status_model=QuoteStatus)

    def test_no_total__managed_emitter(self):
        "Source is managed + edition is allowed."
        user = self.login_as_root_and_get()

        count = Quote.objects.count()
        create_orga = partial(Organisation.objects.create, user=user)

        source = create_orga(name='Nerv')
        self._set_managed(source)

        target1 = create_orga(name='Acme')
        target2 = create_orga(name='NHK')

        lines_count = 2
        names = [f'Billdoc #{i:04}' for i in range(1, lines_count + 1)]
        # NB: probably not a good idea to mix generated & mixed numbers...
        numbers = [
            '',  # A number should be generated
            'Q0002',  # Should be used
        ]
        lines = [
            (names[0], numbers[0], source.name, target1.name),
            (names[1], numbers[1], source.name, target2.name),
        ]

        doc = self._build_csv_doc(lines, user=user)
        url = self._build_import_url(Quote)
        self.assertGET200(url)

        def_status = QuoteStatus.objects.all()[0]
        def_currency = Currency.objects.all()[0]
        response = self.client.post(
            url,
            follow=True,
            data={
                'step':     1,
                'document': doc.id,
                # has_header

                'user': user.id,
                'key_fields': [],

                'name_colselect':   1,
                'number_colselect': 2,

                'issuing_date_colselect':    0,
                'expiration_date_colselect': 0,

                'status_colselect': 0,
                'status_defval':    def_status.pk,

                'discount_colselect': 0,
                'discount_defval':    '0',

                'currency_colselect': 0,
                'currency_defval':    def_currency.pk,

                'acceptation_date_colselect': 0,

                'comment_colselect':         0,
                'additional_info_colselect': 0,
                'payment_terms_colselect':   0,
                'payment_type_colselect':    0,

                'description_colselect':         0,
                'buyers_order_number_colselect': 0,  # Invoice only...

                'source_persons_organisation_colselect': 3,
                'source_persons_organisation_create':    False,

                'target_persons_organisation_colselect': 4,
                'target_persons_organisation_create':    False,

                'target_persons_contact_colselect': 0,
                'target_persons_contact_create':    False,

                # 'property_types',
                # 'fixed_relations',
                # 'dyn_relations',
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)
        self.assertEqual(count + len(lines), Quote.objects.count())

        quote1 = self.get_object_or_fail(Quote, name=names[0])
        self.assertEqual(source, quote1.source)
        self.assertEqual(target1, quote1.target)
        number1 = quote1.number
        self.assertStartsWith(number1, _('QUO') + '-')

        quote2 = self.get_object_or_fail(Quote, name=names[1])
        self.assertEqual(source, quote2.source)
        self.assertEqual(target2, quote2.target)
        number2 = quote2.number
        self.assertEqual(numbers[1], quote2.number)
        self.assertNotEqual(number1, number2)

    def test_total_no_vat_n_vat(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_total_no_vat_n_vat(
            user=user, model=Quote, status_model=QuoteStatus,
        )

    def test_number_not_editable(self):
        "Source is managed + edition is forbidden."
        user = self.login_as_root_and_get()
        count = Quote.objects.count()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        item = self.get_object_or_fail(
            NumberGeneratorItem,
            numbered_type=ContentType.objects.get_for_model(Quote),
            organisation=source,
        )
        item.is_edition_allowed = False
        item.save()

        names = ['Quote #001', 'Quote #002']
        numbers = [
            '',  # A number should be generated
            'Q0002',  # Causes an error
        ]
        lines = [
            (names[0], numbers[0], source.name, target.name),
            (names[1], numbers[1], source.name, target.name),
        ]

        doc = self._build_csv_doc(lines, user=user)
        response = self.client.post(
            self._build_import_url(Quote),
            follow=True,
            data={
                'step':     1,
                'document': doc.id,
                # has_header

                'user': user.id,
                'key_fields': [],

                'name_colselect':   1,
                'number_colselect': 2,

                'issuing_date_colselect':    0,
                'expiration_date_colselect': 0,

                'status_colselect': 0,
                'status_defval':    QuoteStatus.objects.default().pk,

                'discount_colselect': 0,
                'discount_defval':    '0',

                'currency_colselect': 0,
                'currency_defval':    Currency.objects.first().pk,

                'acceptation_date_colselect': 0,

                'comment_colselect':         0,
                'additional_info_colselect': 0,
                'payment_terms_colselect':   0,
                'payment_type_colselect':    0,

                'description_colselect':         0,
                'buyers_order_number_colselect': 0,  # Invoice only...

                'source_persons_organisation_colselect': 3,
                'source_persons_organisation_create':    False,

                'target_persons_organisation_colselect': 4,
                'target_persons_organisation_create':    False,

                'target_persons_contact_colselect': 0,
                'target_persons_contact_create':    False,
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertEqual(count + 1, Quote.objects.count())

        quote1 = self.get_object_or_fail(Quote, name=names[0])
        self.assertStartsWith(quote1.number, _('QUO') + '-')

        j_results = self._get_job_results(job)
        self.assertEqual(2, len(j_results))
        self.assertIsNone(j_results[0].messages)

        j_error = j_results[1]
        self.assertIsNone(j_error.entity)
        self.assertListEqual(
            [_('The number is set as not editable by the configuration.')],
            j_error.messages,
        )

    def test_number_not_editable__update_mode(self):
        "Source is managed + edition is forbidden (update mode)."
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        item = self.get_object_or_fail(
            NumberGeneratorItem,
            numbered_type=ContentType.objects.get_for_model(Quote),
            organisation=source,
        )
        item.is_edition_allowed = False
        item.save()

        def_status = QuoteStatus.objects.default()
        create_quote = partial(
            Quote.objects.create,
            user=user, status=def_status, source=source, target=target,
        )
        quote1 = create_quote(name='Quote #001')
        quote2 = create_quote(name='Quote #002')
        self.assertTrue(quote1.number)

        number2 = quote2.number
        self.assertTrue(number2)

        old_count = Quote.objects.count()
        desc = 'Imported from CSV'
        doc = self._build_csv_doc(
            [
                (quote1.name, quote1.number, source.name, target.name, desc),
                (quote2.name, 'Q#25',        source.name, target.name, desc),
            ],
            user=user,
        )
        response = self.client.post(
            self._build_import_url(Quote),
            follow=True,
            data={
                'step':     1,
                'document': doc.id,
                # has_header

                'user': user.id,
                'key_fields': ['name'],

                'name_colselect':   1,
                'number_colselect': 2,

                'issuing_date_colselect':    0,
                'expiration_date_colselect': 0,

                'status_colselect': 0,
                'status_defval':    QuoteStatus.objects.default().pk,

                'discount_colselect': 0,
                'discount_defval':    '0',

                'currency_colselect': 0,
                'currency_defval':    Currency.objects.first().pk,

                'acceptation_date_colselect': 0,

                'comment_colselect':         0,
                'additional_info_colselect': 0,
                'payment_terms_colselect':   0,
                'payment_type_colselect':    0,

                'description_colselect':         5,
                'buyers_order_number_colselect': 0,  # Invoice only...

                'source_persons_organisation_colselect': 3,
                'source_persons_organisation_create':    False,

                'target_persons_organisation_colselect': 4,
                'target_persons_organisation_create':    False,

                'target_persons_contact_colselect': 0,
                'target_persons_contact_create':    False,
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertEqual(old_count, Quote.objects.count())

        quote1 = self.refresh(quote1)
        self.assertEqual(desc, quote1.description)

        quote2 = self.refresh(quote2)
        self.assertEqual(number2, quote2.number)

        j_results = self._get_job_results(job)
        self.assertEqual(2, len(j_results))
        self.assertIsNone(j_results[0].messages)

        j_error = j_results[1]
        self.assertIsNone(j_error.entity)
        self.assertListEqual(
            [_('The number is set as not editable by the configuration.')],
            j_error.messages,
        )

    def test_emitter_edition(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_update__emitter_edition(
            user=user, model=Quote, emitter_edition_ok=True,
        )


@skipIfCustomAddress
@skipIfCustomSalesOrder
class MassImportSalesOrderTestCase(_BaseMassImportTestCase):
    def test_no_total(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_no_total(
            user=user, model=SalesOrder, status_model=SalesOrderStatus,
        )

    def test_update(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_update(
            user=user, model=SalesOrder, status_model=SalesOrderStatus,
        )
