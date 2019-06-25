# -*- coding: utf-8 -*-

skip_cnote_tests    = False
skip_invoice_tests  = False
skip_quote_tests    = False
skip_order_tests    = False
skip_template_tests = False
skip_pline_tests    = False
skip_sline_tests    = False

try:
    from datetime import date
    from decimal import Decimal
    from functools import partial
    from unittest import skipIf

    from django.conf import settings
    from django.urls import reverse
    from django.utils.translation import gettext as _

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.views.base import MassImportBaseTestCaseMixin
    from creme.creme_core.models import Relation, Currency

    from creme.persons import get_address_model, get_contact_model, get_organisation_model

    from creme.products import get_product_model, get_service_model
    from creme.products.models import Category, SubCategory

    from creme import billing
    from ..constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED
    from ..models import QuoteStatus

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
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


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
    def login(self, is_superuser=True, allowed_apps=None, *args, **kwargs):
        return super().login(is_superuser,
                             allowed_apps=allowed_apps or ['billing'],
                             *args, **kwargs
                            )

    def assertAddressContentEqual(self, address1, address2):  # TODO: move in persons ??
        self.assertIsInstance(address1, Address)
        self.assertIsInstance(address2, Address)

        for f in ('name', 'address', 'po_box', 'zipcode', 'city', 'department', 'state', 'country'):
            self.assertEqual(getattr(address1, f), getattr(address2, f))

    def create_invoice(self, name, source, target, currency=None, discount=Decimal(), user=None):
        user = user or self.user
        currency = currency or Currency.objects.all()[0]
        response = self.client.post(reverse('billing__create_invoice'), follow=True,
                                    data={'user':            user.pk,
                                          'name':            name,
                                          'issuing_date':    '2010-9-7',
                                          'expiration_date': '2010-10-13',
                                          'status':          1,
                                          'currency':        currency.id,
                                          'discount':        discount,
                                          'source':          source.id,
                                          'target':          self.formfield_value_generic_entity(target),
                                         }
                                   )
        self.assertNoFormError(response)
        invoice = self.get_object_or_fail(Invoice, name=name)
        self.assertRedirects(response, invoice.get_absolute_url())

        return invoice

    def create_orgas(self, user=None):
        create_orga = partial(Organisation.objects.create, user=user or self.user)
        return create_orga(name='Source Orga'), create_orga(name='Target Orga')

    def create_invoice_n_orgas(self, name, user=None, discount=Decimal(), currency=None):
        source, target = self.create_orgas()
        invoice = self.create_invoice(name, source, target, user=user,
                                      discount=discount, currency=currency,
                                     )

        return invoice, source, target

    def create_quote(self, name, source, target, currency=None, status=None):
        status = status or QuoteStatus.objects.all()[0]
        currency = currency or Currency.objects.all()[0]
        response = self.client.post(reverse('billing__create_quote'), follow=True,
                                    data={'user':            self.user.pk,
                                          'name':            name,
                                          'issuing_date':    '2011-3-15',
                                          'expiration_date': '2012-4-22',
                                          'status':          status.id,
                                          'currency':        currency.id,
                                          'discount':        Decimal(),
                                          'source':          source.id,
                                          'target':          self.formfield_value_generic_entity(target),
                                         }
                                   )
        self.assertNoFormError(response)

        quote = self.get_object_or_fail(Quote, name=name)
        self.assertRedirects(response, quote.get_absolute_url())

        return quote

    def create_quote_n_orgas(self, name, currency=None, status=None):
        source, target = self.create_orgas()
        quote = self.create_quote(name, source, target, currency, status)

        return quote, source, target

    def create_cat_n_subcat(self):
        cat    = Category.objects.create(name='Cat', description='DESCRIPTION1')
        subcat = SubCategory.objects.create(name='SubCat', description='DESCRIPTION2', category=cat)

        return cat, subcat

    def create_product(self, name='Red eye', unit_price=None):
        cat, subcat = self.create_cat_n_subcat()
        return Product.objects.create(user=self.user, name=name, code='465',
                                      unit_price=unit_price or Decimal('1.0'),
                                      description='Drug',
                                      category=cat, sub_category=subcat
                                     )

    def create_service(self):
        cat, subcat = self.create_cat_n_subcat()
        return Service.objects.create(user=self.user, name='Mushroom hunting',
                                      unit_price=Decimal('6'),
                                      category=cat, sub_category=subcat
                                     )

    def create_salesorder(self, name, source, target, currency=None, status=None):  # TODO inline (used once)
        currency = currency or Currency.objects.all()[0]
        response = self.client.post(reverse('billing__create_order'), follow=True,
                                    data={'user':            self.user.pk,
                                          'name':            name,
                                          'issuing_date':    '2012-1-5',
                                          'expiration_date': '2012-2-15',
                                          'status':          status.id if status else 1,
                                          'currency':        currency.id,
                                          'discount':        Decimal(),
                                          'source':          source.id,
                                          'target':          self.formfield_value_generic_entity(target),
                                         }
                                   )
        self.assertNoFormError(response)

        return self.get_object_or_fail(SalesOrder, name=name)

    def create_salesorder_n_orgas(self, name, currency=None, status=None):
        source, target = self.create_orgas()
        order = self.create_salesorder(name, source, target, currency, status)

        return order, source, target

    def assertDeleteStatusOK(self, status, short_name):
        # self.assertPOST200(reverse('creme_config__delete_instance', args=('billing', short_name)),
        #                    data={'id': status.pk}
        #                   )
        # self.assertDoesNotExist(status)
        response = self.client.post(reverse('creme_config__delete_instance',
                                            args=('billing', short_name, status.id)
                                           ),
                                   )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(type(status)).job
        job.type.execute(job)
        self.assertDoesNotExist(status)

    def assertDeleteStatusKO(self, status, short_name, doc):
        # self.assertPOST404(reverse('creme_config__delete_instance', args=('billing', short_name)),
        #                    data={'id': status.pk}
        #                   )
        # self.assertStillExists(status)
        # doc = self.get_object_or_fail(doc.__class__, pk=doc.pk)
        # self.assertEqual(status, doc.status)
        response = self.assertPOST200(reverse('creme_config__delete_instance',
                                              args=('billing', short_name, status.id)
                                             ),
                                     )
        self.assertFormError(
            response, 'form',
            'replace_billing__{}_status'.format(type(doc).__name__.lower()),
            _('Deletion is not possible.')
        )

        doc = self.assertStillExists(doc)
        self.assertEqual(status, doc.status)

    def _set_managed(self, orga, managed=True):
        orga.is_managed = managed
        orga.save()


class _BillingTestCase(_BillingTestCaseMixin, CremeTestCase, MassImportBaseTestCaseMixin):
    def _aux_test_csv_import(self, model, status_model, update=False):
        count = model.objects.count()
        create_orga = partial(Organisation.objects.create, user=self.user)
        create_contact = partial(Contact.objects.create, user=self.user)

        # Sources --------------------------------------------------------------
        source1 = create_orga(name='Nerv')

        source2_name = 'Seele'
        self.assertFalse(Organisation.objects.filter(name=source2_name))

        # Targets --------------------------------------------------------------
        target1 = create_orga(name='Acme')
        # TODO: factorise
        create_addr = partial(Address.objects.create, owner=target1)
        target1.shipping_address = create_addr(name='ShippingAddr', address='Temple of fire',
                                               po_box='6565', zipcode='789', city='Konoha',
                                               department='dep1', state='Stuff', country='Land of Fire'
                                              )
        target1.billing_address  = create_addr(name='BillingAddr', address='Temple of sand',
                                               po_box='8778', zipcode='123', city='Suna',
                                               department='dep2', state='Foo', country='Land of Sand'
                                              )
        target1.save()

        target2_name = 'NHK'
        self.assertFalse(Organisation.objects.filter(name=target2_name))

        target3 = create_contact(last_name='Ayanami', first_name='Rei')

        target4_last_name = 'Katsuragi'
        self.assertFalse(Contact.objects.filter(last_name=target4_last_name))

        # ----------------------------------------------------------------------

        lines_count = 4
        names   = ['Billdoc #%04i' % i for i in range(1, lines_count + 1)]
        numbers = ['B%04i' % i for i in range(1, lines_count + 1)]
        issuing_dates = [date(year=2013, month=6 + i, day=24 + i)
                            for i in range(lines_count)
                        ]

        date_fmt = settings.DATE_INPUT_FORMATS[0]
        lines = [(names[0], numbers[0], issuing_dates[0].strftime(date_fmt), source1.name, target1.name, ''),
                 (names[1], numbers[1], issuing_dates[1].strftime(date_fmt), source2_name, target2_name, ''),
                 (names[2], numbers[2], issuing_dates[2].strftime(date_fmt), source2_name, '',           target3.last_name),
                 (names[3], numbers[3], issuing_dates[3].strftime(date_fmt), source2_name, '',           target4_last_name),
                ]

        doc = self._build_csv_doc(lines)
        url = self._build_import_url(model)
        self.assertGET200(url)

        def_status = status_model.objects.all()[0]
        def_currency = Currency.objects.all()[0]
        data = {'step':     1,
                'document': doc.id,
                # has_header

                'user': self.user.id,
                'key_fields': ['name'] if update else [],

                'name_colselect': 1,
                'number_colselect': 2,

                'issuing_date_colselect': 3,
                'expiration_date_colselect': 0,

                'status_colselect': 0,
                'status_defval':    def_status.pk,

                'discount_colselect': 0,
                'discount_defval':    '0',

                'currency_colselect': 0,
                'currency_defval':    def_currency.pk,

                'acceptation_date_colselect':    0,

                'comment_colselect':         0,
                'additional_info_colselect': 0,
                'payment_terms_colselect':   0,
                'payment_type_colselect':    0,

                'description_colselect': 0,

                # 'property_types',
                # 'fixed_relations',
                # 'dyn_relations',
               }
        response = self.assertPOST200(url, data=data)
        self.assertFormError(response, 'form', 'source', _('Enter a valid value.'))

        response = self.assertPOST200(url,
                                      data=dict(data,
                                                source_persons_organisation_colselect=0,
                                                source_persons_organisation_create=True,
                                                target_persons_organisation_colselect=0,
                                                target_persons_organisation_create=True,
                                                target_persons_contact_colselect=0,
                                                target_persons_contact_create=True,
                                               )
                                     )
        self.assertFormError(response, 'form', 'source', _('This field is required.'))

        response = self.client.post(url, follow=True,
                                    data=dict(data,
                                              source_persons_organisation_colselect=4,
                                              source_persons_organisation_create=True,
                                              target_persons_organisation_colselect=5,
                                              target_persons_organisation_create=True,
                                              target_persons_contact_colselect=6,
                                              target_persons_contact_create=True,
                                             )
                                   )
        self.assertNoFormError(response)

        self._execute_job(response)
        self.assertEqual(count + len(lines), model.objects.count())

        billing_docs = []

        for i, l in enumerate(lines):
            billing_doc = self.get_object_or_fail(model, name=names[i])
            billing_docs.append(billing_doc)

            self.assertEqual(self.user,        billing_doc.user)
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

        # Billing_doc1
        billing_doc1 = billing_docs[0]
        imp_source1 = billing_doc1.get_source()
        self.assertIsNotNone(imp_source1)
        self.assertEqual(source1, imp_source1.get_real_entity())

        imp_target1 = billing_doc1.get_target()
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
        imp_source2 = billing_doc2.get_source()
        self.assertIsNotNone(imp_source2)
        source2 = self.get_object_or_fail(Organisation, name=source2_name)
        self.assertEqual(imp_source2.get_real_entity(), source2)

        imp_target2 = billing_doc2.get_target()
        self.assertIsNotNone(imp_target2)
        target2 = self.get_object_or_fail(Organisation, name=target2_name)
        self.assertEqual(imp_target2.get_real_entity(), target2)

        # Billing_doc3
        imp_target3 = billing_docs[2].get_target()
        self.assertIsNotNone(imp_target3)
        self.assertEqual(target3, imp_target3.get_real_entity())

        # Billing_doc4
        imp_target4 = billing_docs[3].get_target()
        self.assertIsNotNone(imp_target4)
        target4 = self.get_object_or_fail(Contact, last_name=target4_last_name)
        self.assertEqual(imp_target4.get_real_entity(), target4)

    def _aux_test_csv_import_update(self, model, status_model,
                                    target_billing_address=True,
                                    override_billing_addr=False, override_shipping_addr=False,
                                   ):
        user = self.user
        create_orga = partial(Organisation.objects.create, user=user)

        source1 = create_orga(name='Nerv')
        source2 = create_orga(name='Seele')

        target1 = create_orga(name='Acme1')
        target2 = create_orga(name='Acme2')

        def_status = status_model.objects.all()[0]
        bdoc = model.objects.create(user=user, name='Billdoc #1', status=def_status)

        # TODO: copy the API of Opportunities
        create_rel = partial(Relation.objects.create, subject_entity=bdoc, user=user)
        create_rel(type_id=REL_SUB_BILL_ISSUED,   object_entity=source1)
        create_rel(type_id=REL_SUB_BILL_RECEIVED, object_entity=target1)

        create_addr = Address.objects.create
        if target_billing_address:
            target2.billing_address  = b_addr1 = create_addr(owner=target2, name='BillingAddr1',
                                                             address='Temple of sand', city='Suna',
                                                            )
        target2.shipping_address = s_addr1 = create_addr(owner=target2, name='ShippingAddr1',
                                                        address='Temple of fire', city='Konoha',
                                                       )
        target2.save()

        bdoc.billing_address  = b_addr2 = create_addr(owner=bdoc, name='BillingAddr22',
                                                      address='Temple of rain', city='Kiri',
                                                     )
        bdoc.shipping_address = s_addr2 = create_addr(owner=bdoc, name='ShippingAddr2',
                                                      address='Temple of ligthning', city='Kumo',
                                                     )
        bdoc.save()

        addr_count = Address.objects.count()

        number = 'B0001'
        doc = self._build_csv_doc([(bdoc.name, number, source2.name, target2.name)])
        response = self.client.post(self._build_import_url(model), follow=True,
                                    data={'step':     1,
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
                                          'currency_defval':    Currency.objects.all()[0].pk,

                                          'acceptation_date_colselect': 0,

                                          'comment_colselect':         0,
                                          'additional_info_colselect': 0,
                                          'payment_terms_colselect':   0,
                                          'payment_type_colselect':    0,

                                          'description_colselect': 0,

                                          'source_persons_organisation_colselect': 3,
                                          'source_persons_organisation_create':    True,
                                          'target_persons_organisation_colselect': 4,
                                          'target_persons_organisation_create':    True,
                                          'target_persons_contact_colselect':      0,
                                          # 'target_persons_contact_create':         True,

                                          'override_billing_addr':  'on' if override_billing_addr else '',
                                          'override_shipping_addr': 'on' if override_shipping_addr else '',
                                         }
                                   )
        self.assertNoFormError(response)

        self._execute_job(response)
        bdoc = self.refresh(bdoc)
        self.assertEqual(number, bdoc.number)

        self.assertRelationCount(1, bdoc, REL_SUB_BILL_ISSUED, source2)
        self.assertRelationCount(0, bdoc, REL_SUB_BILL_ISSUED, source1)

        self.assertRelationCount(1, bdoc, REL_SUB_BILL_RECEIVED, target2)
        self.assertRelationCount(0, bdoc, REL_SUB_BILL_RECEIVED, target1)

        b_addr = bdoc.billing_address
        self.assertIsNotNone(b_addr)
        self.assertEqual(bdoc, b_addr.owner)

        s_addr = bdoc.shipping_address
        self.assertIsNotNone(s_addr)
        self.assertEqual(bdoc, s_addr.owner)

        if target_billing_address:
            expected_b_addr = b_addr1 if override_billing_addr else b_addr2
            self.assertEqual(expected_b_addr.address, b_addr.address)
            self.assertEqual(expected_b_addr.city,    b_addr.city)
        else:
            self.assertEqual(b_addr2, b_addr)  # No change

        expected_s_addr = s_addr1 if override_shipping_addr else s_addr2
        self.assertEqual(expected_s_addr.address, s_addr.address)
        self.assertEqual(expected_s_addr.city,    s_addr.city)

        self.assertEqual(addr_count, Address.objects.count())  # No new Address should be created
