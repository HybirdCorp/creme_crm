# -*- coding: utf-8 -*-

try:
    from decimal import Decimal
    from functools import partial

    from creme_core.tests.base import CremeTestCase
    from creme_core.models import Currency, CremePropertyType, CremeProperty
    from creme_core.constants import PROP_IS_MANAGED_BY_CREME

    from persons.models import Contact, Organisation

    from products.models import Product, Service, Category, SubCategory

    from billing.models import *
    from billing.constants import *
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class _BillingTestCase(object):
    def login(self, is_superuser=True, allowed_apps=None, *args, **kwargs):
        super(_BillingTestCase, self).login(is_superuser, allowed_apps=allowed_apps or ['billing'], *args, **kwargs)

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'billing')

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

    def create_invoice_n_orgas(self, name, user=None, discount=Decimal(), currency=None):
        user = user or self.user
        create = partial(Organisation.objects.create, user=user)
        source = create(name='Source Orga')
        target = create(name='Target Orga')

        invoice = self.create_invoice(name, source, target, user=user, discount=discount, currency=currency)

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
        create = partial(Organisation.objects.create, user=self.user)
        source = create(name='Source Orga')
        target = create(name='Target Orga')

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

        self.assertEqual(4, Vat.objects.count())

    def test_portal(self):
        self.login()
        self.assertGET200('/billing/')

    def test_algoconfig(self):
        self.login()

        orga = Organisation.objects.create(user=self.user, name='NERV')

        self.assertFalse(ConfigBillingAlgo.objects.filter(organisation=orga))
        self.assertFalse(SimpleBillingAlgo.objects.filter(organisation=orga))

        ptype = self.get_object_or_fail(CremePropertyType, id=PROP_IS_MANAGED_BY_CREME)
        CremeProperty.objects.create(type=ptype, creme_entity=orga)

        algoconfs = ConfigBillingAlgo.objects.filter(organisation=orga)
        self.assertEqual(['SIMPLE_ALGO'] * 3, [algoconf.name_algo for algoconf in algoconfs])
        self.assertEqual(set([Quote, Invoice, SalesOrder]),
                         set(algoconf.ct.model_class() for algoconf in algoconfs)
                        )

        simpleconfs = SimpleBillingAlgo.objects.filter(organisation=orga)
        self.assertEqual([0] * 3, [simpleconf.last_number for simpleconf in simpleconfs])
        self.assertEqual(set([Quote, Invoice, SalesOrder]),
                         set(simpleconf.ct.model_class() for simpleconf in simpleconfs)
                        )


class VatTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        Vat.objects.all().delete()

    def test_create01(self):
        create_vat = Vat.objects.create
        vat01 = create_vat(value=Decimal('5.0'), is_default=True, is_custom=False)

        vat01 = self.refresh(vat01)
        self.assertEqual(Decimal('5.0'), vat01.value)
        self.assertTrue(vat01.is_default)
        self.assertFalse(vat01.is_custom)

        vat02 = create_vat(value=Decimal('6.0'), is_default=False, is_custom=True)
        vat02 = self.refresh(vat02)
        self.assertEqual(Decimal('6.0'), vat02.value)
        self.assertFalse(vat02.is_default)
        self.assertTrue(vat02.is_custom)

        self.assertEqual(vat01, Vat.get_default_vat())

    def test_create02(self):
        vat = Vat.objects.create(value=Decimal('5.0'), is_default=False, is_custom=False)
        self.assertTrue(self.refresh(vat).is_default)

    def test_create03(self):
        create_vat = partial(Vat.objects.create, is_default=True, is_custom=False)
        vat01 = create_vat(value=Decimal('5.0'))
        vat02 = create_vat(value=Decimal('7.0'))
        self.assertFalse(self.refresh(vat01).is_default)
        self.assertTrue(self.refresh(vat02).is_default)
        self.assertEqual(vat02, Vat.get_default_vat())

    def test_edit01(self):
        create_vat = partial(Vat.objects.create, is_custom=False)
        vat01 = create_vat(value=Decimal('5.0'), is_default=False)
        vat02 = create_vat(value=Decimal('7.0'), is_default=True)

        vat01.is_default = True
        vat01.save()

        self.assertTrue(self.refresh(vat01).is_default)
        self.assertFalse(self.refresh(vat02).is_default)

    def test_edit02(self):
        create_vat = partial(Vat.objects.create, is_custom=False)
        vat01 = create_vat(value=Decimal('5.0'), is_default=False)
        vat02 = create_vat(value=Decimal('7.0'), is_default=True)

        vat02.is_default = False
        vat02.save()

        self.assertFalse(self.refresh(vat01).is_default)
        self.assertTrue(self.refresh(vat02).is_default)

    def test_delete(self):
        create_vat = partial(Vat.objects.create, is_custom=False)
        vat01 = Vat.objects.create(value=Decimal('5.0'), is_default=False)
        vat02 = Vat.objects.create(value=Decimal('7.0'), is_default=True)

        vat02.delete()

        self.assertTrue(self.refresh(vat01).is_default)
