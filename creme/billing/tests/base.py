from datetime import date
from decimal import Decimal
from functools import partial
from unittest import skipIf

from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.formats import number_format
from django.utils.translation import gettext as _

from creme import billing
from creme.creme_core.models import Currency, Vat
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views import base
from creme.persons import (
    get_address_model,
    get_contact_model,
    get_organisation_model,
)
from creme.products import get_product_model, get_service_model
from creme.products.models import Category, SubCategory

from ..constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED
from ..models import (
    CreditNoteStatus,
    InvoiceStatus,
    NumberGeneratorItem,
    QuoteStatus,
    SalesOrderStatus,
)

skip_cnote_tests    = billing.credit_note_model_is_custom()
skip_invoice_tests  = billing.invoice_model_is_custom()
skip_quote_tests    = billing.quote_model_is_custom()
skip_order_tests    = billing.sales_order_model_is_custom()
skip_template_tests = billing.template_base_model_is_custom()
skip_pline_tests    = billing.product_line_model_is_custom()
skip_sline_tests    = billing.service_line_model_is_custom()

CreditNote   = billing.get_credit_note_model()
Invoice      = billing.get_invoice_model()
Quote        = billing.get_quote_model()
SalesOrder   = billing.get_sales_order_model()
TemplateBase = billing.get_template_base_model()

ProductLine = billing.get_product_line_model()
ServiceLine = billing.get_service_line_model()

Address = get_address_model()
Contact = get_contact_model()
Organisation = get_organisation_model()

Product = get_product_model()
Service = get_service_model()


def skipIfCustomCreditNote(test_func):
    return skipIf(skip_cnote_tests, 'Custom CreditNote model in use')(test_func)


def skipIfCustomInvoice(test_func):
    return skipIf(skip_invoice_tests, 'Custom Invoice model in use')(test_func)


def skipIfCustomQuote(test_func):
    return skipIf(skip_quote_tests, 'Custom Quote model in use')(test_func)


def skipIfCustomSalesOrder(test_func):
    return skipIf(skip_order_tests, 'Custom SalesOrder model in use')(test_func)


def skipIfCustomTemplateBase(test_func):
    return skipIf(skip_template_tests, 'Custom TemplateBase model in use')(test_func)


def skipIfCustomProductLine(test_func):
    return skipIf(skip_pline_tests, 'Custom ProductLine model in use')(test_func)


def skipIfCustomServiceLine(test_func):
    return skipIf(skip_sline_tests, 'Custom ServiceLine model in use')(test_func)


class _BillingTestCaseMixin:
    SOURCE_KEY = 'cform_extra-billing_source'
    TARGET_KEY = 'cform_extra-billing_target'

    def assertAddressContentEqual(self, address1, address2):  # TODO: move in persons ??
        self.assertIsInstance(address1, Address)
        self.assertIsInstance(address2, Address)

        for f in (
            'name', 'address', 'po_box', 'zipcode', 'city', 'department', 'state', 'country',
        ):
            self.assertEqual(getattr(address1, f), getattr(address2, f))

    def create_credit_note(self, *, user, name, source, target, currency=None,
                           discount=Decimal(), status=None):
        status = status or CreditNoteStatus.objects.all()[0]
        currency = currency or Currency.objects.all()[0]
        response = self.client.post(
            reverse('billing__create_cnote'), follow=True,
            data={
                'user':   user.id,
                'name':   name,
                'status': status.id,

                'issuing_date':    self.formfield_value_date(2010,  9,  7),
                'expiration_date': self.formfield_value_date(2010, 10, 13),

                'currency': currency.id,
                'discount': discount,

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        )
        self.assertNoFormError(response)

        credit_note = self.get_object_or_fail(CreditNote, name=name)
        self.assertRedirects(response, credit_note.get_absolute_url())

        return credit_note

    def create_credit_note_n_orgas(self, *, user, name, status=None, **kwargs):
        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source Orga')
        target = create_orga(name='Target Orga')

        credit_note = self.create_credit_note(
            name=name, source=source, target=target, user=user, status=status,
            **kwargs
        )

        return credit_note, source, target

    def create_invoice(self, *, user, name, source, target,
                       currency=None,
                       status=None,
                       discount=Decimal(),
                       issuing_date=date(year=2010, month=9, day=7),
                       **kwargs):
        currency = currency or Currency.objects.all()[0]
        status = status or InvoiceStatus.objects.default()
        response = self.client.post(
            reverse('billing__create_invoice'),
            follow=True,
            data={
                'user':   user.pk,
                'name':   name,
                'status': status.id,

                # 'issuing_date':    self.formfield_value_date(2010,  9,  7),
                'issuing_date':    self.formfield_value_date(issuing_date) if issuing_date else '',
                'expiration_date': self.formfield_value_date(2010, 10, 13),

                'currency': currency.id,
                'discount': discount,

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),

                **kwargs
            },
        )
        self.assertNoFormError(response)

        invoice = self.get_object_or_fail(Invoice, name=name)
        self.assertRedirects(response, invoice.get_absolute_url())

        return invoice

    def create_orgas(self, user, index=1):
        create_orga = partial(Organisation.objects.create, user=user)

        return (
            create_orga(name=f'Source #{index}'),
            create_orga(name=f'Target #{index}'),
        )

    def create_invoice_n_orgas(self,
                               *, user, name,
                               discount=Decimal(), currency=None, status=None,
                               **kwargs):
        source, target = self.create_orgas(user=user)
        invoice = self.create_invoice(
            name=name, source=source, target=target,
            user=user, discount=discount, currency=currency, status=status,
            **kwargs
        )

        return invoice, source, target

    def create_quote(self, *, user, name, source, target, currency=None, status=None, **kwargs):
        status = status or QuoteStatus.objects.all()[0]
        currency = currency or Currency.objects.all()[0]
        response = self.client.post(
            reverse('billing__create_quote'), follow=True,
            data={
                'user':   user.pk,
                'name':   name,
                'status': status.id,

                'issuing_date':    self.formfield_value_date(2011, 3, 15),
                'expiration_date': self.formfield_value_date(2012, 4, 22),

                'currency': currency.id,
                'discount': Decimal(),

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),

                **kwargs
            },
        )
        self.assertNoFormError(response)

        quote = self.get_object_or_fail(Quote, name=name)
        self.assertRedirects(response, quote.get_absolute_url())

        return quote

    def create_quote_n_orgas(self, *, user, name, currency=None, status=None, **kwargs):
        source, target = self.create_orgas(user=user)
        quote = self.create_quote(
            user=user, name=name,
            source=source, target=target,
            currency=currency, status=status,
            **kwargs
        )

        return quote, source, target

    def create_cat_n_subcat(self):
        cat = Category.objects.create(name='Cat', description='DESCRIPTION1')
        subcat = SubCategory.objects.create(
            name='SubCat', description='DESCRIPTION2', category=cat,
        )

        return cat, subcat

    def create_product(self, *, user, name='Red eye', unit_price=None):
        cat, subcat = self.create_cat_n_subcat()

        return Product.objects.create(
            user=user, name=name, code='465',
            unit_price=unit_price or Decimal('1.0'),
            description='Drug',
            category=cat, sub_category=subcat,
        )

    def create_service(self, user):
        cat, subcat = self.create_cat_n_subcat()

        return Service.objects.create(
            user=user, name='Mushroom hunting',
            unit_price=Decimal('6'),
            category=cat, sub_category=subcat,
        )

    def create_salesorder(self, *, user, name, source, target, currency=None, status=None):
        currency = currency or Currency.objects.all()[0]
        response = self.client.post(
            reverse('billing__create_order'), follow=True,
            data={
                'user':    user.pk,
                'name':    name,
                'status': status.id if status else SalesOrderStatus.objects.first().id,

                'issuing_date':    self.formfield_value_date(2012, 1, 5),
                'expiration_date': self.formfield_value_date(2012, 2, 15),

                'currency': currency.id,
                'discount': Decimal(),

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        )
        self.assertNoFormError(response)

        return self.get_object_or_fail(SalesOrder, name=name)

    def create_salesorder_n_orgas(self, *, user, name, currency=None, status=None):
        source, target = self.create_orgas(user=user)
        order = self.create_salesorder(
            user=user, name=name, source=source, target=target, currency=currency, status=status,
        )

        return order, source, target

    def assertDeleteStatusOK(self, *, status2del, short_name, new_status, doc):
        response = self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('billing', short_name, status2del.id),
            ),
            data={
                f'replace_billing__{type(doc).__name__.lower()}_status': new_status.id,
            },
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(type(status2del)).job
        job.type.execute(job)
        self.assertDoesNotExist(status2del)

        doc = self.assertStillExists(doc)
        self.assertEqual(new_status, doc.status)

    def _set_managed(self, orga, managed=True):
        orga.is_managed = managed
        orga.save()

        return orga


@override_settings(ENTITIES_DELETION_ALLOWED=True)  # TODO: in CremeTestCase?
class _BillingTestCase(_BillingTestCaseMixin,
                       base.ButtonTestCaseMixin,
                       base.MassImportBaseTestCaseMixin,
                       CremeTestCase):
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

    def assertConvertButtons(self, html_tree, expected):
        found = []

        for button_node in self.iter_button_nodes(
            self.get_instance_buttons_node(html_tree),
        ):
            if button_node.tag == 'a':
                texts = [stripped for txt in button_node.itertext() if (stripped := txt.strip())]
                if len(texts) == 2:
                    found.append({
                        'label': texts[0],
                        'json_data': texts[1],
                        'disabled': ('is-disabled' in button_node.attrib.get('class').split()),
                    })
            else:
                found.append({
                    'label': self.get_alone_element(
                        filter(None, (txt.strip() for txt in button_node.itertext()))
                    ),
                    'disabled': True,
                })

        for item in expected:
            label = item['title']

            for f in found:
                if f['label'] == label:
                    self.assertEqual(item['disabled'], f['disabled'])

                    if 'type' in item:
                        btype = item['type']
                        self.assertIn(f'"type": "{btype}"', f['json_data'])

                    break
            else:
                self.fail(f'The conversion button with title="{label}" has not been found.')

    def _convert(self, status_code, src, dest_type, is_ajax=False):
        http_header = {}

        if is_ajax:
            http_header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        return self.assertPOST(
            status_code, reverse('billing__convert', args=(src.id,)),
            data={'type': dest_type}, follow=True, **http_header
        )
