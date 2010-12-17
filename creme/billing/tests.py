# -*- coding: utf-8 -*-

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User

from creme_core.models import RelationType, Relation, CremePropertyType, CremeProperty
from creme_core.management.commands.creme_populate import Command as PopulateCommand
from creme_core.constants import PROP_IS_MANAGED_BY_CREME

from persons.models import Organisation, Address

from products.models import *

from billing.models import *
from billing.constants import *


class BillingTestCase(TestCase):
    def login(self):
        if not self.user:
            user = User.objects.create(username='Ryoga')
            user.set_password(self.password)
            user.is_superuser = True
            user.save()
            self.user = user

        logged = self.client.login(username=self.user.username, password=self.password)
        self.assert_(logged, 'Not logged in')

    def setUp(self):
        PopulateCommand().handle(application=['creme_core', 'billing'])
        self.password = 'test'
        self.user = None

    def test_populate(self):
        self.assertEqual(1, RelationType.objects.filter(pk=REL_SUB_BILL_ISSUED).count())
        self.assertEqual(1, RelationType.objects.filter(pk=REL_OBJ_BILL_ISSUED).count())
        self.assertEqual(1, RelationType.objects.filter(pk=REL_SUB_BILL_RECEIVED).count())
        self.assertEqual(1, RelationType.objects.filter(pk=REL_OBJ_BILL_RECEIVED).count())

        self.assertEqual(1, SalesOrderStatus.objects.filter(pk=1).count())
        self.assertEqual(2, InvoiceStatus.objects.filter(pk__in=(1, 2)).count())
        self.assertEqual(1, CreditNoteStatus.objects.filter(pk=1).count())

        self.assertEqual(1, CremePropertyType.objects.filter(pk=PROP_IS_MANAGED_BY_CREME).count())

    def genericfield_format_entity(self, entity):
        return '{"ctype":"%s", "entity":"%s"}' % (entity.entity_type_id, entity.id)

    def create_invoice(self, name, source, target):
        response = self.client.post('/billing/invoice/add', follow=True,
                                    data={
                                            'user':            self.user.pk,
                                            'name':            name,
                                            'issuing_date':    '2010-9-7',
                                            'expiration_date': '2010-10-13',
                                            'status':          1,
                                            'source':          source.id,
                                            'target':          self.genericfield_format_entity(target),
                                            }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1,   len(response.redirect_chain))

        try:
            invoice = Invoice.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        self.assert_(response.redirect_chain[0][0].endswith('/billing/invoice/%s' % invoice.id))

        return invoice

    def test_invoice_createview01(self):
        self.login()

        response = self.client.get('/billing/invoice/add')
        self.assertEqual(response.status_code, 200)

        name = 'Invoice001'
        source = Organisation.objects.create(user=self.user, name='Source Orga')
        target = Organisation.objects.create(user=self.user, name='Target Orga')

        self.failIf(target.billing_address)
        self.failIf(target.shipping_address)

        invoice = self.create_invoice(name, source, target)

        self.assertEqual(1,    invoice.status_id)

        exp_date = invoice.expiration_date
        self.assertEqual(2010, exp_date.year)
        self.assertEqual(10,   exp_date.month)
        self.assertEqual(13,   exp_date.day)

        rel_filter = Relation.objects.filter
        self.assertEqual(1, rel_filter(subject_entity=invoice, type=REL_SUB_BILL_ISSUED,   object_entity=source).count())
        self.assertEqual(1, rel_filter(subject_entity=invoice, type=REL_SUB_BILL_RECEIVED, object_entity=target).count())

        self.assertEqual(source.id, invoice.get_source().id)
        self.assertEqual(target.id, invoice.get_target().id)

        target = Organisation.objects.get(pk=target.id)
        b_addr = target.billing_address
        s_addr = target.shipping_address
        self.assert_(b_addr)
        self.assert_(s_addr)
        self.assertEqual(b_addr.id, invoice.billing_address_id)
        self.assertEqual(s_addr.id, invoice.shipping_address_id)

    def test_invoice_createview02(self):
        self.login()

        name = 'Invoice001'

        source = Organisation.objects.create(user=self.user, name='Source Orga')
        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=source)

        target = Organisation.objects.create(user=self.user, name='Target Orga')
        target.shipping_address = Address.objects.create(name='ShippingAddr', owner=target)
        target.billing_address  = Address.objects.create(name='BillingAddr',  owner=target)
        target.save()

        response = self.client.get('/billing/invoice/add')
        self.assertEqual(source.id, response.context['form']['source'].field.initial)

        invoice = self.create_invoice(name, source, target)

        self.assertEqual(target.billing_address.id,  invoice.billing_address_id)
        self.assertEqual(target.shipping_address.id, invoice.shipping_address_id)

        url = invoice.get_absolute_url()
        self.assertEqual('/billing/invoice/%s' % invoice.id, url)
        self.assertEqual(200, self.client.get(url).status_code)

    def test_invoice_editview01(self):
        self.login()

        #Test when not all relation with organisations exist
        invoice = Invoice.objects.create(user=self.user, name='invoice01',
                                         expiration_date=date(year=2010, month=12, day=31),
                                         status_id=1, number='INV0001')

        response = self.client.get('/billing/invoice/edit/%s' % invoice.id)
        self.assertEqual(200, response.status_code)

    def test_invoice_editview02(self):
        self.login()

        #Test when not all relation with organisations exist
        invoice = Invoice.objects.create(user=self.user, name='invoice01',
                                         expiration_date=date(year=2010, month=12, day=31),
                                         status_id=1, number='INV0001')

        response = self.client.get('/billing/invoice/edit/%s' % invoice.id)
        self.assertEqual(200, response.status_code)

    def create_invoice_n_orgas(self, name):
        create = Organisation.objects.create
        source = create(user=self.user, name='Source Orga')
        target = create(user=self.user, name='Target Orga')

        invoice = self.create_invoice(name, source, target)

        return invoice, source, target

    def test_invoice_editview03(self):
        self.login()

        name = 'Invoice001'
        invoice, source, target = self.create_invoice_n_orgas(name)

        response = self.client.get('/billing/invoice/edit/%s' % invoice.id)
        self.assertEqual(200, response.status_code)

        name += '_edited'

        create_orga = Organisation.objects.create
        source = create_orga(user=self.user, name='Source Orga 2')
        target = create_orga(user=self.user, name='Target Orga 2')

        response = self.client.post('/billing/invoice/edit/%s' % invoice.id, follow=True,
                                    data={
                                            'user':            self.user.pk,
                                            'name':            name,
                                            'issuing_date':    '2010-9-7',
                                            'expiration_date': '2011-11-14',
                                            'status':          1,
                                            'source':          source.id,
                                            'target':          self.genericfield_format_entity(target),
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1,   len(response.redirect_chain))
        self.assert_(response.redirect_chain[0][0].endswith('/billing/invoice/%s' % invoice.id))

        invoice = Invoice.objects.get(pk=invoice.id) #refresh object
        self.assertEqual(name, invoice.name)
        self.assertEqual(source.id, invoice.get_source().id)
        self.assertEqual(target.id, invoice.get_target().id)
        rel_filter = Relation.objects.filter
        self.assertEqual(1, rel_filter(subject_entity=source, type=REL_OBJ_BILL_ISSUED,   object_entity=invoice).count())
        self.assertEqual(1, rel_filter(subject_entity=target, type=REL_OBJ_BILL_RECEIVED, object_entity=invoice).count())

        exp_date = invoice.expiration_date
        self.assertEqual(2011, exp_date.year)
        self.assertEqual(11,   exp_date.month)
        self.assertEqual(14,   exp_date.day)

    def test_invoice_addlines01(self): #product line
        self.login()

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        response = self.client.get('/billing/%s/product_line/add' % invoice.id)
        self.assertEqual(200, response.status_code)

        unit_price = Decimal('1.0')
        cat     = Category.objects.create(name='Cat', description='DESCRIPTION')
        subcat  = SubCategory.objects.create(name='Cat', description='DESCRIPTION', category=cat)
        product = Product.objects.create(user=self.user, name='Red eye', code='465',
                                         unit_price=unit_price, description='Drug',
                                         category=cat, sub_category=subcat)

        response = self.client.post('/billing/%s/product_line/add' % invoice.id,
                                    data={
                                            'user':         self.user.pk,
                                            'related_item': product.id,
                                            'comment':      'no comment !',
                                            'quantity':     1,
                                            'unit_price':   unit_price,
                                            'discount':     Decimal(),
                                            'vat':          Decimal(),
                                            'credit':       Decimal(),
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.failIf(response.context['form'].errors)

        self.assertEqual(1, len(invoice.get_product_lines()))
        self.assertEqual(unit_price, invoice.get_total())
        self.assertEqual(unit_price, invoice.get_total_with_tax())

    def test_invoice_addlines02(self): #service line
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        response = self.client.get('/billing/%s/service_line/add' % invoice.id)
        self.assertEqual(200, response.status_code)

        self.failIf(invoice.get_service_lines())

        unit_price = Decimal('1.33')
        cat     = ServiceCategory.objects.create(name='Cat', description='DESCRIPTION')
        service = Service.objects.create(user=self.user, name='Mushroom hunting', reference='465',
                                         unit_price=unit_price, description='Wooot', countable=False,
                                         category=cat)

        response = self.client.post('/billing/%s/service_line/add' % invoice.id,
                                    data={
                                            'user':         self.user.pk,
                                            'related_item': service.id,
                                            'comment':      'no comment !',
                                            'quantity':     2,
                                            'unit_price':   unit_price,
                                            'discount':     Decimal(),
                                            'vat':          Decimal('19.6'),
                                            'credit':       Decimal(),
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.failIf(response.context['form'].errors)

        invoice = Invoice.objects.get(pk=invoice.id) #refresh (line cache)
        self.assertEqual(1, len(invoice.get_service_lines()))
        self.assertEqual(Decimal('2.66'), invoice.get_total()) # 2 * 1.33
        self.assertEqual(Decimal('3.19'), invoice.get_total_with_tax()) #2.66 * 1.196 == 3.18136

    def test_generate_number01(self):
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        self.failIf(invoice.number)
        self.assertEqual(1, invoice.status_id)
        issuing_date = invoice.issuing_date
        self.assert_(issuing_date)

        response = self.client.get('/billing/invoice/generate_number/%s' % invoice.id, follow=True)
        self.assertEqual(404, response.status_code)

        response = self.client.post('/billing/invoice/generate_number/%s' % invoice.id, follow=True)
        self.assertEqual(200, response.status_code)

        invoice = Invoice.objects.get(pk=invoice.id)
        number    = invoice.number
        status_id = invoice.status_id
        self.assert_(number)
        self.assertEqual(2, status_id)
        self.assertEqual(issuing_date, invoice.issuing_date)

        #already generated
        response = self.client.post('/billing/invoice/generate_number/%s' % invoice.id, follow=True)
        self.assertEqual(404, response.status_code)

        invoice = Invoice.objects.get(pk=invoice.id)
        self.assertEqual(number,    invoice.number)
        self.assertEqual(status_id, invoice.status_id)

    def test_generate_number02(self):
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        invoice.issuing_date = None
        invoice.save()

        response = self.client.post('/billing/invoice/generate_number/%s' % invoice.id, follow=True)
        self.assertEqual(200, response.status_code)

        invoice = Invoice.objects.get(pk=invoice.id)
        self.assert_(invoice.issuing_date)
        self.assertEqual(date.today(), invoice.issuing_date) #NB this test can fail if run at midnight...

    #TODO: add product/service on-the fly line
#TODO: add tests for other billing document (Quote, SalesOrder, CreditNote)
