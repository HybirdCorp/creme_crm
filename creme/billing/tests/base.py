from datetime import date
from decimal import Decimal
from functools import partial
from unittest import skipIf

from django.test.utils import override_settings
from django.urls import reverse

from creme import billing
from creme.creme_core.models import Currency
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views import base
from creme.persons import (
    get_address_model,
    get_contact_model,
    get_organisation_model,
)
from creme.products import get_product_model, get_service_model
from creme.products.models import Category, SubCategory

from ..models import (
    CreditNoteStatus,
    InvoiceStatus,
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
        self.assertNoFormError(self.client.post(
            reverse('billing__create_order'),
            follow=True,
            data={
                'user': user.pk,
                'name': name,
                'status': status.id if status else SalesOrderStatus.objects.first().id,

                'issuing_date':    self.formfield_value_date(2012, 1, 5),
                'expiration_date': self.formfield_value_date(2012, 2, 15),

                'currency': currency.id if currency else Currency.objects.first().id,
                'discount': Decimal(),

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        ))

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
                       CremeTestCase):
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
