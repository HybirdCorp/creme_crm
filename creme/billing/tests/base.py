# -*- coding: utf-8 -*-

try:
    from datetime import date
    from decimal import Decimal
    from functools import partial

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.utils.translation import ugettext as _

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.views.list_view_import import CSVImportBaseTestCaseMixin
    from creme.creme_core.models import (RelationType, Currency, Vat, SettingValue,
            CremePropertyType, CremeProperty, BlockDetailviewLocation)
    from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME

    from creme.persons.models import Contact, Organisation, Address

    from creme.products.models import Product, Service, Category, SubCategory

    from ..blocks import persons_statistics_block
    from ..constants import *
    from ..models import *
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class _BillingTestCaseMixin(object):
    def login(self, is_superuser=True, allowed_apps=None, *args, **kwargs):
        super(_BillingTestCaseMixin, self).login(is_superuser, allowed_apps=allowed_apps or ['billing'], *args, **kwargs)

    def assertAddressContentEqual(self, address1, address2): #TODO: move in persons ??
        self.assertIsInstance(address1, Address)
        self.assertIsInstance(address2, Address)

        for f in ('name', 'address', 'po_box', 'zipcode', 'city', 'department', 'state', 'country'):
            self.assertEqual(getattr(address1, f), getattr(address2, f))

    def genericfield_format_entity(self, entity):
        return '{"ctype":"%s", "entity":"%s"}' % (entity.entity_type_id, entity.id)

    def create_invoice(self, name, source, target, currency=None, discount=Decimal(), user=None):
        user = user or self.user
        currency = currency or Currency.objects.all()[0]
        response = self.client.post('/billing/invoice/add', follow=True,
                                    data={'user':            user.pk,
                                          'name':            name,
                                          'issuing_date':    '2010-9-7',
                                          'expiration_date': '2010-10-13',
                                          'status':          1,
                                          'currency':        currency.id,
                                          'discount':        discount,
                                          'source':          source.id,
                                          'target':          self.genericfield_format_entity(target),
                                         }
                                   )
        self.assertNoFormError(response)
        invoice = self.get_object_or_fail(Invoice, name=name)
        self.assertRedirects(response, invoice.get_absolute_url())

        return invoice

    def create_orgas(self):
        create_orga = partial(Organisation.objects.create, user=self.user)
        return create_orga(name='Source Orga'), create_orga(name='Target Orga')

    def create_invoice_n_orgas(self, name, user=None, discount=Decimal(), currency=None):
        source, target = self.create_orgas()
        invoice = self.create_invoice(name, source, target, user=self.user,
                                      discount=discount, currency=currency,
                                     )

        return invoice, source, target

    def create_quote(self, name, source, target, currency=None, status=None):
        status = status or QuoteStatus.objects.all()[0]
        currency = currency or Currency.objects.all()[0]
        response = self.client.post('/billing/quote/add', follow=True,
                                    data={'user':            self.user.pk,
                                          'name':            name,
                                          'issuing_date':    '2011-3-15',
                                          'expiration_date': '2012-4-22',
                                          'status':          status.id,
                                          'currency':        currency.id,
                                          'discount':        Decimal(),
                                          'source':          source.id,
                                          'target':          self.genericfield_format_entity(target),
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
        return Service.objects.create(user=self.user, name=u"Mushroom hunting",
                                      unit_price=Decimal("6"),
                                      category=cat, sub_category=subcat
                                     )

    def assertDeleteStatusOK(self, status, short_name):
        self.assertPOST200('/creme_config/billing/%s/delete' % short_name, data={'id': status.pk})
        self.assertFalse(status.__class__.objects.filter(pk=status.pk).exists())

    def assertDeleteStatusKO(self, status, short_name, doc):
        self.assertPOST404('/creme_config/billing/%s/delete' % short_name, data={'id': status.pk})
        self.assertTrue(status.__class__.objects.filter(pk=status.pk).exists())

        doc = self.get_object_or_fail(doc.__class__, pk=doc.pk)
        self.assertEqual(status, doc.status)

    def _set_managed(self, orga):
        ptype = self.get_object_or_fail(CremePropertyType, id=PROP_IS_MANAGED_BY_CREME)
        CremeProperty.objects.create(type=ptype, creme_entity=orga)


class _BillingTestCase(_BillingTestCaseMixin, CremeTestCase, CSVImportBaseTestCaseMixin):
#class _BillingTestCase(CremeTestCase, _BillingTestCaseMixin, CSVImportBaseTestCaseMixin):
    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        #cls.populate('creme_core', 'creme_config', 'billing')
        cls.populate('creme_config', 'billing')
        cls.autodiscover()

    def _aux_test_csv_import(self, model, status_model):
        count = model.objects.count()
        create_orga = partial(Organisation.objects.create, user=self.user)
        create_contact = partial(Contact.objects.create, user=self.user)

        #sources -------------------------------------------------------------
        source1 = create_orga(name='Nerv')

        source2_name = 'Seele'
        self.assertFalse(Organisation.objects.filter(name=source2_name))

        #targets -------------------------------------------------------------
        target1 = create_orga(name='Acme')
        #TODO: factorise
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

        #---------------------------------------------------------------------

        lines_count = 4
        names   = ['Billdoc #%04i' % i for i in xrange(1, lines_count + 1)]
        numbers = ['B%04i' % i for i in xrange(1, lines_count + 1)]
        issuing_dates = [date(year=2013, month=6 + i, day=24 + i)
                            for i in xrange(lines_count)
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
                #has_header

                'user': self.user.id,

                'name_colselect': 1,
                'number_colselect': 2,

                'issuing_date_colselect': 3,
                'expiration_date_colselect': 0,

                'status_colselect': 0,
                'status_defval':    def_status.pk,

                'discount_colselect': 0,
                'discount_defval':    0,

                'currency_colselect': 0,
                'currency_defval':    def_currency.pk,

                'acceptation_date_colselect':    0,

                'comment_colselect':         0,
                'additional_info_colselect': 0,
                'payment_terms_colselect':   0,
                'payment_type_colselect':    0,

                #'property_types',
                #'fixed_relations',
                #'dyn_relations',
               }
        response = self.assertPOST200(url, data=data)
        self.assertFormError(response, 'form', 'source', [_(u'Enter a valid value.')])

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
        self.assertFormError(response, 'form', 'source', [_(u'This field is required.')])

        response = self.client.post(url,
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
            #self.assertIsNone(billing_doc.payment_type) #only in invoice... TODO lambda ??

        #billing_doc1
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

        #billing_doc2
        billing_doc2 = billing_docs[1]
        imp_source2 = billing_doc2.get_source()
        self.assertIsNotNone(imp_source2)
        source2 = self.get_object_or_fail(Organisation, name=source2_name)
        self.assertEqual(imp_source2.get_real_entity(), source2)

        imp_target2 = billing_doc2.get_target()
        self.assertIsNotNone(imp_target2)
        target2 = self.get_object_or_fail(Organisation, name=target2_name)
        self.assertEqual(imp_target2.get_real_entity(), target2)

        #billing_doc3
        imp_target3 = billing_docs[2].get_target()
        self.assertIsNotNone(imp_target3)
        self.assertEqual(target3, imp_target3.get_real_entity())

        #billing_doc4
        imp_target4 = billing_docs[3].get_target()
        self.assertIsNotNone(imp_target4)
        target4 = self.get_object_or_fail(Contact, last_name=target4_last_name)
        self.assertEqual(imp_target4.get_real_entity(), target4)


class AppTestCase(_BillingTestCase, CremeTestCase):
    def test_populate(self):
        billing_classes = [Invoice, Quote, SalesOrder, CreditNote, TemplateBase]
        lines_clases = [Line, ProductLine, ServiceLine]
        self.get_relationtype_or_fail(REL_SUB_BILL_ISSUED,       billing_classes, [Organisation])
        self.get_relationtype_or_fail(REL_SUB_BILL_RECEIVED,     billing_classes, [Organisation, Contact])
        self.get_relationtype_or_fail(REL_SUB_HAS_LINE,          billing_classes, lines_clases)
        self.get_relationtype_or_fail(REL_SUB_LINE_RELATED_ITEM, lines_clases,    [Product, Service])

        self.assertEqual(1, SalesOrderStatus.objects.filter(pk=1).count())
        self.assertEqual(2, InvoiceStatus.objects.filter(pk__in=(1, 2)).count())
        self.assertEqual(1, CreditNoteStatus.objects.filter(pk=1).count())

        #self.assertEqual(5, Vat.objects.count()) #in creme_core populate...
        self.assertTrue(Vat.objects.exists()) #in creme_core populate...

        #contribution to activities
        from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT

        rtype = self.get_object_or_fail(RelationType, pk=REL_SUB_ACTIVITY_SUBJECT)
        get_ct = ContentType.objects.get_for_model
        ct_ids = [get_ct(m).id for m in (Invoice, Quote, SalesOrder)]
        self.assertEqual(len(ct_ids), rtype.subject_ctypes.filter(id__in=ct_ids).count())
        self.assertTrue(rtype.subject_ctypes.filter(id=get_ct(Contact).id).exists())
        self.assertEqual(len(ct_ids), rtype.symmetric_type.object_ctypes.filter(id__in=ct_ids).count())

    def test_portal(self):
        self.login()
        self.assertGET200('/billing/')

    def test_algoconfig(self):
        self.login()

        orga = Organisation.objects.create(user=self.user, name='NERV')

        self.assertFalse(ConfigBillingAlgo.objects.filter(organisation=orga))
        self.assertFalse(SimpleBillingAlgo.objects.filter(organisation=orga))

        self._set_managed(orga)

        algoconfs = ConfigBillingAlgo.objects.filter(organisation=orga)
        self.assertEqual(['SIMPLE_ALGO'] * 3, [algoconf.name_algo for algoconf in algoconfs])
        self.assertEqual({Quote, Invoice, SalesOrder},
                         {algoconf.ct.model_class() for algoconf in algoconfs}
                        )

        simpleconfs = SimpleBillingAlgo.objects.filter(organisation=orga)
        self.assertEqual([0] * 3, [simpleconf.last_number for simpleconf in simpleconfs])
        self.assertEqual({Quote, Invoice, SalesOrder},
                         {simpleconf.ct.model_class() for simpleconf in simpleconfs}
                        )

    def _get_setting_value(self):
        return self.get_object_or_fail(SettingValue, key_id=DISPLAY_PAYMENT_INFO_ONLY_CREME_ORGA)

    def test_block_orga01(self):
        self.login()

        sv = self._get_setting_value()
        self.assertIs(True, sv.value)

        orga = Organisation.objects.create(user=self.user, name='NERV')

        response = self.assertGET200(orga.get_absolute_url())
        payment_info_tlpt = 'billing/templatetags/block_payment_information.html'
        self.assertTemplateNotUsed(response, payment_info_tlpt)
        self.assertTemplateUsed(response, 'billing/templatetags/block_received_invoices.html')
        self.assertTemplateUsed(response, 'billing/templatetags/block_received_billing_document.html')

        sv.value = False
        sv.save()

        response = self.assertGET200(orga.get_absolute_url())
        self.assertTemplateUsed(response, payment_info_tlpt)

    def test_block_orga02(self):
        "Managed organisation"
        self.login()

        orga = Organisation.objects.create(user=self.user, name='NERV')
        self._set_managed(orga)

        response = self.assertGET200(orga.get_absolute_url())
        payment_info_tlpt = 'billing/templatetags/block_payment_information.html'
        self.assertTemplateUsed(response, payment_info_tlpt)
        self.assertTemplateUsed(response, 'billing/templatetags/block_received_invoices.html')
        self.assertTemplateUsed(response, 'billing/templatetags/block_received_billing_document.html')

        sv = self._get_setting_value()
        sv.value = False
        sv.save()

        response = self.assertGET200(orga.get_absolute_url())
        self.assertTemplateUsed(response, payment_info_tlpt)

    def test_block_orga03(self):
        "Statistics"
        self.login()

        orga = Organisation.objects.create(user=self.user, name='NERV')

        BlockDetailviewLocation.create(block_id=persons_statistics_block.id_, order=1000,
                                        zone=BlockDetailviewLocation.LEFT, model=Organisation,
                                       )

        response = self.assertGET200(orga.get_absolute_url())
        self.assertTemplateUsed(response, 'billing/templatetags/block_persons_statistics.html')
        self.assertContains(response, 'id="%s"' % persons_statistics_block.id_)
