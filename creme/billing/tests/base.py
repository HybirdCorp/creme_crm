# -*- coding: utf-8 -*-

try:
    from decimal import Decimal

    from creme_core.models import Relation, Currency
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact, Organisation

    from products.models import Product, Service, Category, SubCategory

    from billing.models import *
    from billing.constants import *
except Exception as e:
    print 'Error:', e


class _BillingTestCase(object):
    def login(self, is_superuser=True, allowed_apps=None, *args, **kwargs):
        super(_BillingTestCase, self).login(is_superuser, allowed_apps=allowed_apps or ['billing'], *args, **kwargs)

    def setUp(self):
        self.populate('creme_core', 'creme_config', 'billing')

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
        self.assertEqual(200, response.status_code)
        self.assertEqual(1,   len(response.redirect_chain))

        invoice = self.get_object_or_fail(Invoice, name=name)
        self.assertTrue(response.redirect_chain[0][0].endswith('/billing/invoice/%s' % invoice.id))

        return invoice

    def create_invoice_n_orgas(self, name, user=None, discount=Decimal()):
        user = user or self.user
        create = Organisation.objects.create
        source = create(user=user, name='Source Orga')
        target = create(user=user, name='Target Orga')

        invoice = self.create_invoice(name, source, target, user=user, discount=discount)

        return invoice, source, target

    def create_quote(self, name, source, target, currency=None):
        currency = currency or Currency.objects.all()[0]
        response = self.client.post('/billing/quote/add', follow=True,
                                    data={'user':            self.user.pk,
                                          'name':            name,
                                          'issuing_date':    '2011-3-15',
                                          'expiration_date': '2012-4-22',
                                          'status':          1,
                                          'currency':        currency.id,
                                          'discount':        Decimal(),
                                          'source':          source.id,
                                          'target':          self.genericfield_format_entity(target),
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertEqual(1,   len(response.redirect_chain))

        quote = self.get_object_or_fail(Quote, name=name)
        self.assertTrue(response.redirect_chain[0][0].endswith('/billing/quote/%s' % quote.id))

        return quote

    def create_quote_n_orgas(self, name):
        create = Organisation.objects.create
        source = create(user=self.user, name='Source Orga')
        target = create(user=self.user, name='Target Orga')

        quote = self.create_quote(name, source, target)

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
        self.assertEqual(200, self.client.get('/billing/').status_code)


class VatTestCase(CremeTestCase):
    def test_create01(self):
        vat01 = Vat.objects.create(value=Decimal('5.0'), is_default=True, is_custom=False)

        vat01 = self.refresh(vat01)
        self.assertEqual(Decimal('5.0'), vat01.value)
        self.assertTrue(vat01.is_default)
        self.assertFalse(vat01.is_custom)

        vat02 = Vat.objects.create(value=Decimal('6.0'), is_default=False, is_custom=True)
        vat02 = self.refresh(vat02)
        self.assertEqual(Decimal('6.0'), vat02.value)
        self.assertFalse(vat02.is_default)
        self.assertTrue(vat02.is_custom)

        self.assertEqual(vat01, Vat.get_default_vat())

    def test_create02(self):
        vat = Vat.objects.create(value=Decimal('5.0'), is_default=False, is_custom=False)
        self.assertTrue(self.refresh(vat).is_default)

    def test_create03(self):
        vat01 = Vat.objects.create(value=Decimal('5.0'), is_default=True, is_custom=False)
        vat02 = Vat.objects.create(value=Decimal('7.0'), is_default=True, is_custom=False)
        self.assertFalse(self.refresh(vat01).is_default)
        self.assertTrue(self.refresh(vat02).is_default)
        self.assertEqual(vat02, Vat.get_default_vat())

    def test_edit01(self):
        vat01 = Vat.objects.create(value=Decimal('5.0'), is_default=False, is_custom=False)
        vat02 = Vat.objects.create(value=Decimal('7.0'), is_default=True, is_custom=False)

        vat01.is_default = True
        vat01.save()

        self.assertTrue(self.refresh(vat01).is_default)
        self.assertFalse(self.refresh(vat02).is_default)

    def test_edit02(self):
        vat01 = Vat.objects.create(value=Decimal('5.0'), is_default=False, is_custom=False)
        vat02 = Vat.objects.create(value=Decimal('7.0'), is_default=True, is_custom=False)

        vat02.is_default = False
        vat02.save()

        self.assertFalse(self.refresh(vat01).is_default)
        self.assertTrue(self.refresh(vat02).is_default)

    def test_delete(self):
        vat01 = Vat.objects.create(value=Decimal('5.0'), is_default=False, is_custom=False)
        vat02 = Vat.objects.create(value=Decimal('7.0'), is_default=True, is_custom=False)

        vat02.delete()

        self.assertTrue(self.refresh(vat01).is_default)
