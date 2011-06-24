# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
from decimal import Decimal
from django.db.models.deletion import ProtectedError
from django.db.models.query_utils import Q

from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, Relation, CremePropertyType, CremeProperty, SetCredentials
from creme_core.constants import PROP_IS_MANAGED_BY_CREME, REL_SUB_RELATED_TO
from creme_core.models.entity import CremeEntity
from creme_core.tests.base import CremeTestCase

from persons.models import Contact, Organisation, Address

from products.models import Product, Service, Category, SubCategory

from billing.models import *
from billing.constants import *


class BillingTestCase(CremeTestCase):
    def login(self, is_superuser=True, allowed_apps=None):
        super(BillingTestCase, self).login(is_superuser, allowed_apps=allowed_apps or ['billing'])

    def setUp(self):
        self.populate('creme_core', 'billing')

    def test_populate(self):
        self.assertEqual(1, RelationType.objects.filter(pk=REL_SUB_BILL_ISSUED).count())
        self.assertEqual(1, RelationType.objects.filter(pk=REL_OBJ_BILL_ISSUED).count())
        self.assertEqual(1, RelationType.objects.filter(pk=REL_SUB_BILL_RECEIVED).count())
        self.assertEqual(1, RelationType.objects.filter(pk=REL_OBJ_BILL_RECEIVED).count())
        self.assertEqual(1, RelationType.objects.filter(pk=REL_SUB_HAS_LINE).count())
        self.assertEqual(1, RelationType.objects.filter(pk=REL_OBJ_HAS_LINE).count())
        self.assertEqual(1, RelationType.objects.filter(pk=REL_SUB_LINE_RELATED_ITEM).count())
        self.assertEqual(1, RelationType.objects.filter(pk=REL_OBJ_LINE_RELATED_ITEM).count())

        self.assertEqual(1, SalesOrderStatus.objects.filter(pk=1).count())
        self.assertEqual(2, InvoiceStatus.objects.filter(pk__in=(1, 2)).count())
        self.assertEqual(1, CreditNoteStatus.objects.filter(pk=1).count())

        self.assertEqual(1, CremePropertyType.objects.filter(pk=PROP_IS_MANAGED_BY_CREME).count())

    def test_portal(self):
        self.login()
        self.assertEqual(self.client.get('/billing/').status_code, 200)

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
        self.assertNoFormError(response)
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

        self.assertEqual(self.client.get('/billing/invoice/add').status_code, 200)

        name = 'Invoice001'
        source = Organisation.objects.create(user=self.user, name='Source Orga')
        target = Organisation.objects.create(user=self.user, name='Target Orga')

        self.failIf(target.billing_address)
        self.failIf(target.shipping_address)

        invoice = self.create_invoice(name, source, target)
        self.assertEqual(1, invoice.status_id)

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

    def test_invoice_createview03(self): #creds errors with Organisation
        self.login(is_superuser=False)

        role = self.user.role
        create_sc = SetCredentials.objects.create
        create_sc(role=role,
                  value=SetCredentials.CRED_VIEW | SetCredentials.CRED_CHANGE | SetCredentials.CRED_DELETE | SetCredentials.CRED_UNLINK, #no CRED_LINK
                  set_type=SetCredentials.ESET_ALL
                 )
        create_sc(role=role,
                  value=SetCredentials.CRED_VIEW | SetCredentials.CRED_CHANGE | SetCredentials.CRED_DELETE | SetCredentials.CRED_LINK | SetCredentials.CRED_UNLINK,
                  set_type=SetCredentials.ESET_OWN
                 )
        role.creatable_ctypes = [ContentType.objects.get_for_model(Invoice)]

        source = Organisation.objects.create(user=self.other_user, name='Source Orga')
        self.failIf(source.can_link(self.user))

        target = Organisation.objects.create(user=self.other_user, name='Target Orga')
        self.failIf(target.can_link(self.user))

        response = self.client.get('/billing/invoice/add', follow=True)
        try:
            form = response.context['form']
        except Exception, e:
            self.fail(str(e))

        self.assert_('source' in form.fields, 'Bad form ?!')

        response = self.client.post('/billing/invoice/add', follow=True,
                            data={
                                    'user':            self.user.pk,
                                    'name':            'Invoice001',
                                    'issuing_date':    '2011-9-7',
                                    'expiration_date': '2011-10-13',
                                    'status':          1,
                                    'source':          source.id,
                                    'target':          self.genericfield_format_entity(target),
                                    }
                           )
        self.assertEqual(200, response.status_code)

        try:
            errors = response.context['form'].errors
        except Exception, e:
            self.fail(str(e))

        self.assert_(errors)
        self.assert_('source' in errors)
        self.assert_('target' in errors)

    def test_invoice_listview(self):
        self.login()

        create = Organisation.objects.create
        source = create(user=self.user, name='Source Orga')
        target = create(user=self.user, name='Target Orga')

        self.create_invoice('invoice 01', source, target)
        self.create_invoice('invoice 02', source, target)

        self.assertEqual(200, self.client.get('/billing/invoices').status_code)

    def test_invoice_editview01(self):
        self.login()

        #Test when not all relation with organisations exist
        invoice = Invoice.objects.create(user=self.user, name='invoice01',
                                         expiration_date=date(year=2010, month=12, day=31),
                                         status_id=1, number='INV0001')

        self.assertEqual(200, self.client.get('/billing/invoice/edit/%s' % invoice.id).status_code)

    def test_invoice_editview02(self):
        self.login()

        #Test when not all relation with organisations exist
        invoice = Invoice.objects.create(user=self.user, name='invoice01',
                                         expiration_date=date(year=2010, month=12, day=31),
                                         status_id=1, number='INV0001')

        self.assertEqual(200, self.client.get('/billing/invoice/edit/%s' % invoice.id).status_code)

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

        url = '/billing/invoice/edit/%s' % invoice.id
        self.assertEqual(200, self.client.get(url).status_code)

        name += '_edited'

        create_orga = Organisation.objects.create
        source = create_orga(user=self.user, name='Source Orga 2')
        target = create_orga(user=self.user, name='Target Orga 2')

        response = self.client.post(url, follow=True,
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

    def test_invoice_add_product_lines01(self):
        self.login()

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        url = '/billing/%s/product_line/add' % invoice.id
        self.assertEqual(200, self.client.get(url).status_code)

        unit_price = Decimal('1.0')
        cat     = Category.objects.create(name='Cat', description='DESCRIPTION')
        subcat  = SubCategory.objects.create(name='Cat', description='DESCRIPTION', category=cat)
        product = Product.objects.create(user=self.user, name='Red eye', code='465',
                                         unit_price=unit_price, description='Drug',
                                         category=cat, sub_category=subcat)

        response = self.client.post(url,
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
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        lines = invoice.product_lines
        self.assertEqual(1, len(lines))

        line = lines[0]
        self.assertEqual(product.id, line.related_item.id)
        self.assertEqual(unit_price, line.unit_price)

        self.assertEqual(unit_price, invoice.get_total())
        self.assertEqual(unit_price, invoice.get_total_with_tax())

    def test_invoice_add_product_lines02(self): #on-the-fly
        self.login()

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        url = '/billing/%s/product_line/add_on_the_fly' % invoice.id
        self.assertEqual(200, self.client.get(url).status_code)

        unit_price = Decimal('1.0')
        name = 'Awesomo'
        response = self.client.post(url,
                                    data={
                                            'user':            self.user.pk,
                                            'on_the_fly_item': name,
                                            'comment':         'no comment !',
                                            'quantity':        1,
                                            'unit_price':      unit_price,
                                            'discount':        Decimal(),
                                            'vat':             Decimal(),
                                            'credit':          Decimal(),
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        lines = invoice.product_lines
        self.assertEqual(1, len(lines))
        self.assertEqual(name, lines[0].on_the_fly_item)

        self.assertEqual(unit_price, invoice.get_total())
        self.assertEqual(unit_price, invoice.get_total_with_tax())

    def test_invoice_add_product_lines03(self): #on-the-fly + product creation
        self.login()

        self.failIf(Product.objects.count())

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        unit_price = Decimal('1.0')
        name    = 'Awesomo'
        cat     = Category.objects.create(name='Cat', description='DESCRIPTION')
        subcat  = SubCategory.objects.create(name='Cat', description='DESCRIPTION', category=cat)
        response = self.client.post('/billing/%s/product_line/add_on_the_fly' % invoice.id,
                                    data={
                                            'user':                self.user.pk,
                                            'on_the_fly_item':     name,
                                            'comment':             'no comment !',
                                            'quantity':            1,
                                            'unit_price':          unit_price,
                                            'discount':            Decimal(),
                                            'vat':                 Decimal(),
                                            'credit':              Decimal(),
                                            'has_to_register_as':  'on',
                                            'sub_category': """{"category":%s, "subcategory":%s}""" % (cat.id, subcat.id)
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            product = Product.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(cat.id,     product.category_id)
        self.assertEqual(subcat.id,  product.sub_category_id)
        self.assertEqual(unit_price, product.unit_price)

        lines = invoice.product_lines
        self.assertEqual(1, len(lines))

        line = lines[0]
        self.failIf(line.on_the_fly_item)
        self.assertEqual(product.id, line.related_item.id)

    def test_invoice_add_product_lines04(self): #on-the-fly + product creation + no creation creds
        self.login(is_superuser=False)

        user = self.user
        role = user.role

        role.allowed_apps = ['persons', 'billing']
        role.save()

        SetCredentials.objects.create(role=role,
                                      value=SetCredentials.CRED_VIEW   | SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | SetCredentials.CRED_LINK | SetCredentials.CRED_UNLINK,
                                      set_type=SetCredentials.ESET_OWN)

        get_ct = ContentType.objects.get_for_model
        role.creatable_ctypes = [get_ct(Invoice), get_ct(Contact), get_ct(Organisation)] #not 'Product'

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        cat    = Category.objects.create(name='Cat', description='DESCRIPTION')
        subcat = SubCategory.objects.create(name='Cat', description='DESCRIPTION', category=cat)
        response = self.client.post('/billing/%s/product_line/add_on_the_fly' % invoice.id,
                                    data={
                                            'user':                self.user.pk,
                                            'on_the_fly_item':     'Awesomo',
                                            'comment':             'no comment !',
                                            'quantity':            1,
                                            'unit_price':          Decimal('1.0'),
                                            'discount':            Decimal(),
                                            'vat':                 Decimal(),
                                            'credit':              Decimal(),
                                            'has_to_register_as':  'on',
                                            'category':            cat.id,
                                            'sub_category':        subcat.id,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'has_to_register_as', [_(u'You are not allowed to create Products')])
        self.failIf(invoice.product_lines)
        self.failIf(Product.objects.count())

    def test_invoice_delete_product_line01(self):
        self.login()
        invoice  = self.create_invoice_n_orgas('Invoice001')[0]

        self.failIf(len(invoice.product_lines))

        product_line = ProductLine.objects.create(user=self.user)
        product_line.related_document = invoice

        response = self.client.post('/creme_core/entity/delete/%s' % product_line.id, data={}, follow=True)

        self.assertEqual(200, response.status_code)
        self.failIf(len(invoice.product_lines))
        self.failIf(ProductLine.objects.count())

    def test_invoice_delete_product_line02(self):
        self.login()
        invoice  = self.create_invoice_n_orgas('Invoice001')[0]

        self.failIf(len(invoice.product_lines))

        product_line = ProductLine.objects.create(user=self.user)

        response = self.client.post('/creme_core/entity/delete/%s' % product_line.id, data={}, follow=True)

        self.assertEqual(403, response.status_code)

    def test_invoice_edit_product_lines01(self):
#        self.populate('creme_core', 'persons')
        self.login()

        name = 'Stuff'
        unit_price = Decimal('42.0')
        quantity = 1
        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        line = ProductLine.objects.create(on_the_fly_item=name, quantity=quantity,
                                          unit_price=unit_price, is_paid=False, user=self.user,
                                         )
        line.related_document = invoice

        url = '/billing/productline/%s/edit' % line.id
        self.assertEqual(200, self.client.get(url).status_code)

        name += '_edited'
        unit_price += Decimal('1.0')
        quantity *= 2
        response = self.client.post(url, data={
                                                'user':            self.user.pk,
                                                'on_the_fly_item': name,
                                                'comment':         'no comment !',
                                                'quantity':        quantity,
                                                'unit_price':      unit_price,
                                                'discount':        Decimal(),
                                                'vat':             Decimal(),
                                                'credit':          Decimal(),
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        line = ProductLine.objects.get(pk=line.id) #refresh
        self.assertEqual(name,       line.on_the_fly_item)
        self.assertEqual(unit_price, line.unit_price)
        self.assertEqual(quantity,   line.quantity)

    def test_invoice_add_service_lines01(self):
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        url = '/billing/%s/service_line/add' % invoice.id
        self.assertEqual(200, self.client.get(url).status_code)

        self.failIf(invoice.service_lines)

        unit_price = Decimal('1.33')
        cat     = Category.objects.create(name='Cat', description='DESCRIPTION')
        sub_cat = SubCategory.objects.create(name='Sub Cat', description='DESCRIPTION', category=cat)

        service = Service.objects.create(user=self.user, name='Mushroom hunting', reference='465',
                                         unit_price=unit_price, description='Wooot', countable=False,
                                         category=cat, sub_category=sub_cat)

        response = self.client.post(url,
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
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        invoice = Invoice.objects.get(pk=invoice.id) #refresh (line cache)
        self.assertEqual(1,               len(invoice.service_lines))
        self.assertEqual(Decimal('2.66'), invoice.get_total()) # 2 * 1.33
        self.assertEqual(Decimal('3.19'), invoice.get_total_with_tax()) #2.66 * 1.196 == 3.18136

    def test_invoice_add_service_lines02(self): #on-the-fly
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        url = '/billing/%s/service_line/add_on_the_fly' % invoice.id
        self.assertEqual(200, self.client.get(url).status_code)

        unit_price = Decimal('1.33')
        name = 'Car wash'
        response = self.client.post(url, data={
                                                'user':            self.user.pk,
                                                'on_the_fly_item': name,
                                                'comment':         'no comment !',
                                                'quantity':        2,
                                                'unit_price':      unit_price,
                                                'discount':        Decimal(),
                                                'vat':             Decimal('19.6'),
                                                'credit':          Decimal(),
                                             }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        invoice = Invoice.objects.get(pk=invoice.id) #refresh (line cache)
        lines = invoice.service_lines
        self.assertEqual(1, len(lines))
        self.assertEqual(name, lines[0].on_the_fly_item)

    def test_invoice_add_service_lines03(self): #on-the-fly + Service creation
        self.login()

        self.failIf(Service.objects.count())

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        unit_price = Decimal('1.33')
        name = 'Car wash'
        cat     = Category.objects.create(name='Cat', description='DESCRIPTION')
        subcat  = SubCategory.objects.create(name='Cat', description='DESCRIPTION', category=cat)

        response = self.client.post('/billing/%s/service_line/add_on_the_fly' % invoice.id,
                                    data={
                                            'user':               self.user.pk,
                                            'on_the_fly_item':    name,
                                            'comment':            'no comment !',
                                            'quantity':           2,
                                            'unit_price':         unit_price,
                                            'discount':           Decimal(),
                                            'vat':                Decimal('19.6'),
                                            'credit':             Decimal(),
                                            'has_to_register_as': 'on',
                                            'sub_category': """{"category":%s, "subcategory":%s}""" % (cat.id, subcat.id)
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            service = Service.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(cat.id,     service.category_id)
        self.assertEqual(subcat.id,  service.sub_category_id)
        self.assertEqual(unit_price, service.unit_price)

        invoice = Invoice.objects.get(pk=invoice.id) #refresh (line cache)
        lines = invoice.service_lines
        self.assertEqual(1, len(lines))

        line = lines[0]
        self.failIf(line.on_the_fly_item)
        self.assertEqual(service.id, line.related_item.id)

    def test_invoice_add_service_lines04(self): #on-the-fly + service creation + no creation creds
        self.login(is_superuser=False)

        user = self.user
        role = user.role

        role.allowed_apps = ['persons', 'billing']
        role.save()

        SetCredentials.objects.create(role=role,
                                      value=SetCredentials.CRED_VIEW   | SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | SetCredentials.CRED_LINK | SetCredentials.CRED_UNLINK,
                                      set_type=SetCredentials.ESET_OWN)

        get_ct = ContentType.objects.get_for_model
        role.creatable_ctypes = [get_ct(Invoice), get_ct(Contact), get_ct(Organisation)] #not 'Service'

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        cat     = Category.objects.create(name='Cat', description='DESCRIPTION')
        subcat  = SubCategory.objects.create(name='Cat', description='DESCRIPTION', category=cat)
        response = self.client.post('/billing/%s/service_line/add_on_the_fly' % invoice.id,
                                    data={
                                            'user':               self.user.pk,
                                            'on_the_fly_item':    'Car wash',
                                            'comment':            'no comment !',
                                            'quantity':           2,
                                            'unit_price':         Decimal('1.33'),
                                            'discount':           Decimal(),
                                            'vat':                Decimal('19.6'),
                                            'credit':             Decimal(),
                                            'has_to_register_as': 'on',
                                            'sub_category': """{"category":%s, "subcategory":%s}""" % (cat.id, subcat.id)
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'has_to_register_as', [_(u'You are not allowed to create Services')])
        self.failIf(invoice.service_lines)
        self.failIf(Service.objects.count())

    def test_invoice_edit_service_lines01(self):
        self.login()

        name = 'Stuff'
        unit_price = Decimal('42.0')
        quantity = 1
        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        line = ServiceLine.objects.create(on_the_fly_item=name, quantity=quantity,
                                          unit_price=unit_price, is_paid=False, user=self.user,
                                         )
        line.related_document = invoice

        url = '/billing/serviceline/%s/edit' % line.id
        self.assertEqual(200, self.client.get(url).status_code)

        name += '_edited'
        unit_price += Decimal('1.0')
        quantity *= 2
        response = self.client.post(url, data={
                                                'user':            self.user.pk,
                                                'on_the_fly_item': name,
                                                'comment':         'no comment !',
                                                'quantity':        quantity,
                                                'unit_price':      unit_price,
                                                'discount':        Decimal(),
                                                'vat':             Decimal(),
                                                'credit':          Decimal(),
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        line = ServiceLine.objects.get(pk=line.id) #refresh
        self.assertEqual(name,       line.on_the_fly_item)
        self.assertEqual(unit_price, line.unit_price)
        self.assertEqual(quantity,   line.quantity)

    def test_generate_number01(self):
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        self.failIf(invoice.number)
        self.assertEqual(1, invoice.status_id)
        issuing_date = invoice.issuing_date
        self.assert_(issuing_date)

        url = '/billing/invoice/generate_number/%s' % invoice.id
        self.assertEqual(404, self.client.get(url, follow=True).status_code)

        self.assertEqual(200, self.client.post(url, follow=True).status_code)
        invoice = Invoice.objects.get(pk=invoice.id)
        number    = invoice.number
        status_id = invoice.status_id
        self.assert_(number)
        self.assertEqual(2,            status_id)
        self.assertEqual(issuing_date, invoice.issuing_date)

        #already generated
        self.assertEqual(404, self.client.post(url, follow=True).status_code)
        invoice = Invoice.objects.get(pk=invoice.id)
        self.assertEqual(number,    invoice.number)
        self.assertEqual(status_id, invoice.status_id)

    def test_generate_number02(self):
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        invoice.issuing_date = None
        invoice.save()

        self.assertEqual(200, self.client.post('/billing/invoice/generate_number/%s' % invoice.id, follow=True).status_code)
        invoice = Invoice.objects.get(pk=invoice.id)
        self.assert_(invoice.issuing_date)
        self.assertEqual(date.today(), invoice.issuing_date) #NB this test can fail if run at midnight...

    def create_quote(self, name, source, target):
        response = self.client.post('/billing/quote/add', follow=True,
                                    data={
                                            'user':            self.user.pk,
                                            'name':            name,
                                            'issuing_date':    '2011-3-15',
                                            'expiration_date': '2012-4-22',
                                            'status':          1,
                                            'source':          source.id,
                                            'target':          self.genericfield_format_entity(target),
                                            }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertEqual(1,   len(response.redirect_chain))

        try:
            quote = Quote.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        self.assert_(response.redirect_chain[0][0].endswith('/billing/quote/%s' % quote.id))

        return quote

    def create_quote_n_orgas(self, name):
        create = Organisation.objects.create
        source = create(user=self.user, name='Source Orga')
        target = create(user=self.user, name='Target Orga')

        quote = self.create_quote(name, source, target)

        return quote, source, target

    def test_quote_createview01(self):
        self.login()

        quote, source, target = self.create_quote_n_orgas('My Quote')

        exp_date = quote.expiration_date
        self.assertEqual(2012, exp_date.year)
        self.assertEqual(4,    exp_date.month)
        self.assertEqual(22,   exp_date.day)

        rel_filter = Relation.objects.filter
        self.assertEqual(1, rel_filter(subject_entity=quote, type=REL_SUB_BILL_ISSUED,   object_entity=source).count())
        self.assertEqual(1, rel_filter(subject_entity=quote, type=REL_SUB_BILL_RECEIVED, object_entity=target).count())

    def test_convert01(self):
        self.login()

        quote, source, target = self.create_quote_n_orgas('My Quote')
        self.failIf(Invoice.objects.count())

        response = self.client.post('/billing/%s/convert/' % quote.id,
                                    data={'type': 'invoice'}, follow=True
                                   )
        self.assertEqual(200, response.status_code)

        invoices = Invoice.objects.all()
        self.assertEqual(1, len(invoices))

        invoice = invoices[0]
        self.assertEqual(quote.issuing_date,    invoice.issuing_date)
        self.assertEqual(quote.expiration_date, invoice.expiration_date)
        self.assertEqual(quote.discount,        invoice.discount)
        self.assertEqual(quote.total_vat,       invoice.total_vat)
        self.assertEqual(quote.total_no_vat,    invoice.total_no_vat)

        rel_filter = Relation.objects.filter
        self.assertEqual(1, rel_filter(subject_entity=invoice, type=REL_SUB_BILL_ISSUED,   object_entity=source).count())
        self.assertEqual(1, rel_filter(subject_entity=invoice, type=REL_SUB_BILL_RECEIVED, object_entity=target).count())

    def test_convert02(self): #SalesOrder + not superuser
        self.login(is_superuser=False, allowed_apps=['billing', 'persons'])

        get_ct = ContentType.objects.get_for_model
        self.role.creatable_ctypes = [get_ct(Quote), get_ct(SalesOrder)]
        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_VIEW | SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | \
                                            SetCredentials.CRED_LINK | SetCredentials.CRED_UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        quote = self.create_quote_n_orgas('My Quote')[0]

        response = self.client.post('/billing/%s/convert/' % quote.id, data={'type': 'sales_order'}, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, Invoice.objects.count())
        self.assertEqual(1, SalesOrder.objects.count())

    def test_convert03(self): #creds (creation) errors
        self.login(is_superuser=False, allowed_apps=['billing', 'persons'])

        get_ct = ContentType.objects.get_for_model
        self.role.creatable_ctypes = [get_ct(Quote)] #not get_ct(Invoice)
        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_VIEW | SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | \
                                            SetCredentials.CRED_LINK | SetCredentials.CRED_UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        quote = self.create_quote_n_orgas('My Quote')[0]
        self.assertEqual(403, self.client.post('/billing/%s/convert/' % quote.id, data={'type': 'invoice'}).status_code)
        self.assertEqual(0, Invoice.objects.count())

    def test_convert04(self): #creds (view) errors
        self.login(is_superuser=False, allowed_apps=['billing', 'persons'])

        get_ct = ContentType.objects.get_for_model
        self.role.creatable_ctypes = [get_ct(Quote), get_ct(Invoice)]
        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_VIEW | SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | \
                                            SetCredentials.CRED_LINK | SetCredentials.CRED_UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        quote = Quote.objects.create(user=self.other_user, name='My Quote',
                                     issuing_date=datetime.now(),
                                     expiration_date=datetime.now() + timedelta(days=10),
                                     status=QuoteStatus.objects.all()[0],
                                     )
        self.failIf(quote.can_view(self.user))

        self.assertEqual(403, self.client.post('/billing/%s/convert/' % quote.id, data={'type': 'invoice'}).status_code)
        self.assertEqual(0, Invoice.objects.count())

    def test_convert05(self):#Quote to Invoice with lines
        self.login()
        self.populate('products')

        quote, source, target = self.create_quote_n_orgas('My Quote')

        product_line_otf = ProductLine.objects.create(user=self.user, on_the_fly_item="otf1", unit_price=Decimal("1"))
        product_line_otf.related_document = quote

        product_line     = ProductLine.objects.create(user=self.user, unit_price=Decimal("2"))
        product = Product.objects.create(user=self.user, code=1, unit_price=Decimal("3"), category=Category.objects.all()[0], sub_category=SubCategory.objects.all()[0], name=u"Product 1")
        product_line.related_document = quote
        product_line.related_item     = product

        service_line_otf = ServiceLine.objects.create(user=self.user, on_the_fly_item="otf2", unit_price=Decimal("4"))
        service_line_otf.related_document = quote

        service_line = ServiceLine.objects.create(user=self.user, unit_price=Decimal("5"))
        service = Service.objects.create(user=self.user, unit_price=Decimal("6"), category=Category.objects.all()[0], sub_category=SubCategory.objects.all()[0], name=u"Service 1")
        service_line.related_document = quote
        service_line.related_item     = service

        quote.save()#To set total_vat...

        quote_property = CremeProperty.objects.create(creme_entity=quote, type=CremePropertyType.objects.all()[0])

        self.assertEqual(2, quote.get_lines(ServiceLine).count())
        self.assertEqual(2, quote.get_lines(ProductLine).count())

        self.failIf(Invoice.objects.count())

        response = self.client.post('/billing/%s/convert/' % quote.id,
                                    data={'type': 'invoice'}, follow=True
                                   )
        self.assertEqual(200, response.status_code)

        invoices = Invoice.objects.all()
        self.assertEqual(1, len(invoices))

        invoice = invoices[0]

        self.assertEqual(2, invoice.get_lines(ServiceLine).count())
        self.assertEqual(2, invoice.get_lines(ProductLine).count())

        q_otf_item = Q(on_the_fly_item=None)

        invoice_service_line     = invoice.get_lines(ServiceLine).get(q_otf_item)#Should be with the related_item
        invoice_service_line_otf = invoice.get_lines(ServiceLine).get(~q_otf_item)

        self.assertEqual(service_line.related_item,     invoice_service_line.related_item)
        self.assertEqual(service_line_otf.related_item, invoice_service_line_otf.related_item)

        invoice_product_line     = invoice.get_lines(ProductLine).get(q_otf_item)#Should be with the related_item
        invoice_product_line_otf = invoice.get_lines(ProductLine).get(~q_otf_item)

        self.assertEqual(product_line.related_item,     invoice_product_line.related_item)
        self.assertEqual(product_line_otf.related_item, invoice_product_line_otf.related_item)

        self.assertEqual(quote.issuing_date,    invoice.issuing_date)
        self.assertEqual(quote.expiration_date, invoice.expiration_date)
        self.assertEqual(quote.discount,        invoice.discount)
        self.assertEqual(quote.total_no_vat,    invoice.total_no_vat)
        self.assertEqual(quote.total_vat,       invoice.total_vat)

        rel_filter = Relation.objects.filter
        self.assertEqual(1, rel_filter(subject_entity=invoice, type=REL_SUB_BILL_ISSUED,   object_entity=source).count())
        self.assertEqual(1, rel_filter(subject_entity=invoice, type=REL_SUB_BILL_RECEIVED, object_entity=target).count())

        self.assertEqual(1, invoice.properties.count())
        self.assertEqual(quote_property.type, invoice.properties.all()[0].type)


    def test_add_payment_info01(self):
        self.login()

        organisation = Organisation.objects.create(user=self.user, name=u"Nintendo")
        url = '/billing/payment_information/add/%s' % organisation.id
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url,
                                    data={
                                            'user':            self.user.pk,
                                            'name':            "RIB of %s" % organisation,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        self.assertEqual(1, PaymentInformation.objects.count())

        pi = PaymentInformation.objects.all()[0]

        self.assertEqual(True,         pi.is_default)
        self.assertEqual(organisation, pi.organisation)

    def test_add_payment_info02(self):
        self.login()

        organisation = Organisation.objects.create(user=self.user, name=u"Nintendo")
        first_pi = PaymentInformation.objects.create(organisation=organisation, name="RIB 1", is_default=True)

        url = '/billing/payment_information/add/%s' % organisation.id
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url,
                                    data={
                                            'user':            self.user.pk,
                                            'name':            "RIB of %s" % organisation,
                                            'is_default':      True,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        self.assertEqual(2, PaymentInformation.objects.count())

        second_pi = PaymentInformation.objects.exclude(pk=first_pi.pk)[0]

        self.assertEqual(True, second_pi.is_default)

        second_pi.delete()

        self.assertEqual(True, first_pi.is_default)

    def test_edit_payment_info01(self):
        self.login()

        organisation = Organisation.objects.create(user=self.user, name=u"Nintendo")
        pi = PaymentInformation.objects.create(organisation=organisation, name="RIB 1")

        url = '/billing/payment_information/edit/%s' % pi.id
        self.assertEqual(200, self.client.get(url).status_code)

        rib_key = "00"
        name    = "RIB of %s" % organisation
        bic     = "pen ?"

        response = self.client.post(url,
                                    data={
                                            'user':            self.user.pk,
                                            'name':            name,
                                            'rib_key':         rib_key,
                                            'bic':             bic,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        pi = PaymentInformation.objects.get(pk=pi.pk) #Refresh

        self.assertEqual(True,    pi.is_default)
        self.assertEqual(name,    pi.name)
        self.assertEqual(rib_key, pi.rib_key)
        self.assertEqual(bic,     pi.bic)

    def test_edit_payment_info02(self):
        self.login()

        organisation = Organisation.objects.create(user=self.user, name=u"Nintendo")
        pi  = PaymentInformation.objects.create(organisation=organisation, name="RIB 1", is_default=True)
        pi2 = PaymentInformation.objects.create(organisation=organisation, name="RIB 2", is_default=False)

        url = '/billing/payment_information/edit/%s' % pi2.id
        self.assertEqual(200, self.client.get(url).status_code)

        rib_key = "00"
        name    = "RIB of %s" % organisation
        bic     = "pen ?"

        response = self.client.post(url,
                                    data={
                                            'user':            self.user.pk,
                                            'name':            name,
                                            'rib_key':         rib_key,
                                            'bic':             bic,
                                            'is_default':      True
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        pi  = PaymentInformation.objects.get(pk=pi.pk) #Refresh
        pi2 = PaymentInformation.objects.get(pk=pi2.pk) #Refresh

        self.assertEqual(False,    pi.is_default)
        self.assertEqual(True,     pi2.is_default)

        self.assertEqual(name,    pi2.name)
        self.assertEqual(rib_key, pi2.rib_key)
        self.assertEqual(bic,     pi2.bic)

        pi2.delete()

        pi = PaymentInformation.objects.get(pk=pi.pk) #Refresh

        self.assertEqual(True, pi.is_default)


    def test_payment_info_set_default_in_invoice01(self):
        self.login()

        invoice, sony_source, nintendo_target = self.create_invoice_n_orgas('Playstations')
        pi_sony = PaymentInformation.objects.create(organisation=sony_source, name="RIB sony")

        self.assertEqual(200, self.client.get('/billing/payment_information/set_default/%s/%s' % (pi_sony.id, invoice.id)).status_code)


    def test_payment_info_set_default_in_invoice02(self):
        self.login()

        sega = Organisation.objects.create(user=self.user, name=u"Sega")
        invoice, sony_source, nintendo_target = self.create_invoice_n_orgas('Playstations')

        pi_nintendo  = PaymentInformation.objects.create(organisation=nintendo_target, name="RIB nintendo")
        pi_sony      = PaymentInformation.objects.create(organisation=sony_source,     name="RIB sony")
        pi_sega      = PaymentInformation.objects.create(organisation=sega,            name="RIB sega")

        self.assertEqual(404, self.client.get('/billing/payment_information/set_default/%s/%s' % (pi_nintendo.id, invoice.id)).status_code)
        self.assertEqual(404, self.client.get('/billing/payment_information/set_default/%s/%s' % (pi_sega.id, invoice.id)).status_code)
        self.assertEqual(200, self.client.get('/billing/payment_information/set_default/%s/%s' % (pi_sony.id, invoice.id)).status_code)

    def test_payment_info_set_null_in_invoice01(self):
        self.login()

        sega = Organisation.objects.create(user=self.user, name=u"Sega")
        invoice, sony_source, nintendo_target = self.create_invoice_n_orgas('Playstations')

        pi_sony = PaymentInformation.objects.create(organisation=sony_source, name="RIB sony")
        self.assertEqual(200, self.client.get('/billing/payment_information/set_default/%s/%s' % (pi_sony.id, invoice.id)).status_code)

        response = self.client.post('/billing/invoice/edit/%s' % invoice.id, follow=True,
                                    data={
                                            'user':            self.user.pk,
                                            'name':            'Dreamcast',
                                            'issuing_date':    '2010-9-7',
                                            'expiration_date': '2010-10-13',
                                            'status':          1,
                                            'source':          sega.id,
                                            'target':          self.genericfield_format_entity(nintendo_target),
                                         }
                                   )

        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        invoice = Invoice.objects.get(pk=invoice.pk)#Refresh

        self.assertEqual(None, invoice.payment_info)


    def test_create_invoice_from_a_detailview01(self):
        self.login()

        name = 'Invoice001'

        source = Organisation.objects.create(user=self.user, name='Source Orga')
        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=source)

        target = Organisation.objects.create(user=self.user, name='Target Orga')

        url = '/billing/invoice/add/%s' % target.id

        response = self.client.get(url)

        self.assertEqual(source.id, response.context['form']['source'].field.initial)
#        self.assertEqual(target.id, response.context['form']['target'].field.initial) #Why doesn't work ?

        self.assertEqual(200, response.status_code)

        response = self.client.post(url, follow=True,
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
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            invoice = Invoice.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(target, invoice.get_target().get_real_entity())

    def test_product_lines_property01(self):
        self.login()
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')
        self.assertEqual(None, invoice._productlines_cache)
        self.assertEqual(0,    len(invoice.product_lines))

        product_line = ProductLine.objects.create(user=self.user)

        relation=Relation.objects.create(subject_entity=invoice, object_entity=product_line, type_id=REL_SUB_HAS_LINE, user=self.user)

        self.assertEqual(1,                          len(invoice.product_lines))
        self.assertEqual(product_line,               invoice.product_lines[0])
        self.assertEqual(set(invoice.product_lines), set(invoice._productlines_cache))

        relation.delete()
        product_line.delete() #NB: The right way should be to delete only the ProductLine but with CanNotBeDeleted...

        self.assertEqual(None, invoice._productlines_cache)
        self.assertEqual(0,    len(invoice.product_lines))

    def test_product_lines_property02(self):
        self.login()
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')
        self.assertEqual(None, invoice._productlines_cache)
        self.assertEqual(0,    len(invoice.product_lines))

        product_line = ProductLine.objects.create(user=self.user)
        service_line = ServiceLine.objects.create(user=self.user)

        pl_rel=Relation.objects.create(subject_entity=invoice, object_entity=product_line, type_id=REL_SUB_HAS_LINE, user=self.user)
        sl_rel=Relation.objects.create(subject_entity=invoice, object_entity=service_line, type_id=REL_SUB_HAS_LINE, user=self.user)

        self.assertEqual(1,            len(invoice.product_lines))
        self.assertEqual(product_line, invoice.product_lines[0])

    def test_service_lines_property01(self):
        self.login()
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')
        self.assertEqual(None, invoice._servicelines_cache)
        self.assertEqual(0,    len(invoice.service_lines))

        service_line = ServiceLine.objects.create(user=self.user)

        relation=Relation.objects.create(subject_entity=invoice, object_entity=service_line, type_id=REL_SUB_HAS_LINE, user=self.user)

        self.assertEqual(1,                          len(invoice.service_lines))
        self.assertEqual(service_line,               invoice.service_lines[0])
        self.assertEqual(set(invoice.service_lines), set(invoice._servicelines_cache))

        relation.delete()
        service_line.delete() #NB: The right way should be to delete only the ProductLine but with CanNotBeDeleted...

        self.assertEqual(None, invoice._servicelines_cache)
        self.assertEqual(0,    len(invoice.service_lines))

    def test_service_lines_property02(self):
        self.login()
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')
        self.assertEqual(None, invoice._servicelines_cache)
        self.assertEqual(0,    len(invoice.service_lines))

        product_line = ProductLine.objects.create(user=self.user)
        service_line = ServiceLine.objects.create(user=self.user)

        pl_rel=Relation.objects.create(subject_entity=invoice, object_entity=product_line, type_id=REL_SUB_HAS_LINE, user=self.user)
        sl_rel=Relation.objects.create(subject_entity=invoice, object_entity=service_line, type_id=REL_SUB_HAS_LINE, user=self.user)

        self.assertEqual(1,            len(invoice.service_lines))
        self.assertEqual(service_line, invoice.service_lines[0])

    def test_get_lines01(self):
        self.login()
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')

        self.assertEqual(0, len(invoice.get_lines(Line)))

        product_line = ProductLine.objects.create(user=self.user)
        service_line = ServiceLine.objects.create(user=self.user)

        pl_rel=Relation.objects.create(subject_entity=invoice, object_entity=product_line, type_id=REL_SUB_HAS_LINE, user=self.user)
        sl_rel=Relation.objects.create(subject_entity=invoice, object_entity=service_line, type_id=REL_SUB_HAS_LINE, user=self.user)

        self.assertEqual(2, len(invoice.get_lines(Line)))
        self.assertEqual(set([product_line.id, service_line.id]), set(invoice.get_lines(Line).values_list('pk', flat=True)))

        self.assertEqual(1, len(invoice.get_lines(ProductLine)))
        self.assertEqual(1, len(invoice.get_lines(ServiceLine)))

    def test_total_vat01(self):
        self.login()
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')

        product_line = ProductLine.objects.create(user=self.user, quantity=3, unit_price=Decimal("5"))
        service_line = ServiceLine.objects.create(user=self.user, quantity=9, unit_price=Decimal("10"))

        self.assertEqual(0, invoice.get_total_with_tax())

        pl_rel=Relation.objects.create(subject_entity=invoice, object_entity=product_line, type_id=REL_SUB_HAS_LINE, user=self.user)

        self.assertEqual(product_line.get_price_inclusive_of_tax(), invoice.get_total_with_tax())

        sl_rel=Relation.objects.create(subject_entity=invoice, object_entity=service_line, type_id=REL_SUB_HAS_LINE, user=self.user)

        self.assertEqual(product_line.get_price_inclusive_of_tax() + service_line.get_price_inclusive_of_tax(), invoice.get_total_with_tax())

    def test_line_related_document01(self):
        self.login()
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')

        product_line = ProductLine.objects.create(user=self.user)
        pl_rel=Relation.objects.create(subject_entity=invoice, object_entity=product_line, type_id=REL_SUB_HAS_LINE, user=self.user)

        self.assertEqual(invoice.pk, product_line.related_document.id)

        #Tries for testing there is only one relation created between product_line and invoice
        pl_rel2=Relation.objects.create(subject_entity=invoice, object_entity=product_line, type_id=REL_SUB_HAS_LINE, user=self.user)
        pl_rel3=Relation.objects.create(subject_entity=invoice, object_entity=product_line, type_id=REL_SUB_HAS_LINE, user=self.user)

        self.assertEqual(1, Relation.objects.filter(subject_entity=invoice, object_entity=product_line, type=REL_SUB_HAS_LINE).count())

    def test_line_related_document02(self):
        self.login()
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')

        product_line = ProductLine.objects.create(user=self.user)

        self.assertEqual(None, product_line.related_document)
        self.assertEqual(0, Relation.objects.filter(subject_entity=invoice, object_entity=product_line, type=REL_SUB_HAS_LINE).count())

        product_line.related_document = invoice

        self.assertEqual(invoice, product_line.related_document)
        self.assertEqual(1, Relation.objects.filter(subject_entity=invoice, object_entity=product_line, type=REL_SUB_HAS_LINE).count())

    def test_line_related_item01(self):
        self.login()
        self.populate('products')

        import creme_core
        creme_core.autodiscover()#To connect signals

        product = Product.objects.create(user=self.user, code=1, unit_price=Decimal("1"), category=Category.objects.all()[0], sub_category=SubCategory.objects.all()[0])

        product_line = ProductLine.objects.create(user=self.user)

        self.assertEqual(None, product_line.related_item)

        pl_rel=Relation.objects.create(object_entity=product, subject_entity=product_line, type_id=REL_SUB_LINE_RELATED_ITEM, user=self.user)

        self.assertEqual(product.pk, product_line.related_item.id)

        #Tries for testing there is only one relation created between product_line and product
        pl_rel2=Relation.objects.create(object_entity=product, subject_entity=product_line, type_id=REL_SUB_LINE_RELATED_ITEM, user=self.user)
        pl_rel3=Relation.objects.create(object_entity=product, subject_entity=product_line, type_id=REL_SUB_LINE_RELATED_ITEM, user=self.user)

        self.assertEqual(1, Relation.objects.filter(object_entity=product, subject_entity=product_line, type=REL_SUB_LINE_RELATED_ITEM).count())

    def test_line_related_item02(self):
        self.login()
        self.populate('products')

        import creme_core
        creme_core.autodiscover()#To connect signals

        product = Product.objects.create(user=self.user, code=1, unit_price=Decimal("1"), category=Category.objects.all()[0], sub_category=SubCategory.objects.all()[0])

        product_line = ProductLine.objects.create(user=self.user)

        self.assertEqual(None, product_line.related_item)
        self.assertEqual(0, Relation.objects.filter(object_entity=product, subject_entity=product_line, type=REL_SUB_LINE_RELATED_ITEM).count())

        product_line.related_item = product
        self.assertEqual(product, product_line.related_item)
        self.assertEqual(1, Relation.objects.filter(object_entity=product, subject_entity=product_line, type=REL_SUB_LINE_RELATED_ITEM).count())

    def test_product_line_clone01(self):
        self.login()
        self.populate('products')

        import creme_core
        creme_core.autodiscover()#To connect signals

        product = Product.objects.create(user=self.user, code=1, unit_price=Decimal("1"), category=Category.objects.all()[0], sub_category=SubCategory.objects.all()[0], name=u"Product 1")
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')

        product2 = Product.objects.create(user=self.user, code=1, unit_price=Decimal("1"), category=Category.objects.all()[0], sub_category=SubCategory.objects.all()[0], name=u"Product 2")
        invoice2, source2, target2 = self.create_invoice_n_orgas('Invoice002')

        product_line = ProductLine.objects.create(user=self.user)
        product_line.related_document = invoice
        product_line.related_item     = product

        product_line2 = product_line.clone()
        product_line2.related_document = invoice2
        product_line2.related_item     = product2

        product_line2 = ProductLine.objects.get(pk=product_line2.id)#Refresh
        self.assertEqual(invoice2, product_line2.related_document)
        self.assertEqual(product2, product_line2.related_item)

        self.assertEqual(set([product_line2.pk]), set(Relation.objects.filter(type=REL_SUB_HAS_LINE, subject_entity=invoice2).values_list('object_entity', flat=True)))
        self.assertEqual(set([product_line2.pk]), set(Relation.objects.filter(type=REL_SUB_LINE_RELATED_ITEM, object_entity=product2).values_list('subject_entity', flat=True)))

    def test_service_line_clone01(self):
        self.login()
        self.populate('products')

        import creme_core
        creme_core.autodiscover()#To connect signals

        service = Service.objects.create(user=self.user, unit_price=Decimal("1"), category=Category.objects.all()[0], sub_category=SubCategory.objects.all()[0], name=u"Service 1")
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')

        service2 = Service.objects.create(user=self.user, unit_price=Decimal("1"), category=Category.objects.all()[0], sub_category=SubCategory.objects.all()[0], name=u"Service 2")
        invoice2, source2, target2 = self.create_invoice_n_orgas('Invoice002')

        service_line = ServiceLine.objects.create(user=self.user)
        service_line.related_document = invoice
        service_line.related_item     = service

        service_line2 = service_line.clone()
        service_line2.related_document = invoice2
        service_line2.related_item     = service2

        service_line2 = ServiceLine.objects.get(pk=service_line2.id)#Refresh
        self.assertEqual(invoice2, service_line2.related_document)
        self.assertEqual(service2, service_line2.related_item)
        self.assertNotEqual(service_line, service_line2)

        self.assertEqual(set([service_line2.pk]), set(Relation.objects.filter(type=REL_SUB_HAS_LINE, subject_entity=invoice2).values_list('object_entity', flat=True)))
        self.assertEqual(set([service_line2.pk]), set(Relation.objects.filter(type=REL_SUB_LINE_RELATED_ITEM, object_entity=service2).values_list('subject_entity', flat=True)))

    def test_invoice_clone_with_lines01(self):
        self.login()
        self.populate('products')
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')

        service = Service.objects.create(user=self.user, unit_price=Decimal("1"), category=Category.objects.all()[0], sub_category=SubCategory.objects.all()[0], name=u"Service 1")

        service_line = ServiceLine.objects.create(user=self.user)
        service_line.related_document = invoice
        service_line.related_item     = service

        service_line_otf = ServiceLine.objects.create(user=self.user, on_the_fly_item="otf service")
        service_line_otf.related_document = invoice

        product = Product.objects.create(user=self.user, code=1, unit_price=Decimal("1"), category=Category.objects.all()[0], sub_category=SubCategory.objects.all()[0], name=u"Product 1")

        product_line = ProductLine.objects.create(user=self.user)
        product_line.related_document = invoice
        product_line.related_item     = product

        product_line_otf = ProductLine.objects.create(user=self.user, on_the_fly_item="otf product")
        product_line_otf.related_document = invoice

        cloned = invoice.clone()
        cloned = Invoice.objects.get(pk=cloned.pk)

        self.assertNotEqual(invoice, cloned)#Not the same pk
        self.assertEqual(invoice.get_source(), cloned.get_source())
        self.assertEqual(invoice.get_target(), cloned.get_target())

        invoice.invalidate_cache()#just in case
        cloned.invalidate_cache()#just in case

        self.assert_(invoice.service_lines)
        self.assert_(invoice.product_lines)

        self.assertEqual(len(invoice.service_lines), len(cloned.service_lines))
        self.assertEqual(len(invoice.product_lines), len(cloned.product_lines))

        self.assertNotEqual(set([p.pk for p in invoice.service_lines]), set([p.pk for p in cloned.service_lines]))
        self.assertNotEqual(set([p.pk for p in invoice.product_lines]), set([p.pk for p in cloned.product_lines]))

#        rel_filter = Relation.objects.filter
#        self.assertEqual(1, rel_filter(subject_entity=invoice, type=REL_SUB_BILL_ISSUED,   object_entity=source).count())

    def test_delete01(self):
        self.login()
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')

        service_line = ServiceLine.objects.create(user=self.user)
        service_line.related_document = invoice

        invoice.delete()
        self.assertFalse(Invoice.objects.filter(pk=invoice.pk))
        self.assertFalse(ServiceLine.objects.filter(pk=service_line.pk))

        try:
            Organisation.objects.get(pk=source.pk)
            Organisation.objects.get(pk=target.pk)
        except Organisation.DoesNotExist, e:
            self.fail(e)

    def test_delete02(self):#Can't be deleted
        self.login()
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')

        service_line = ServiceLine.objects.create(user=self.user)
        service_line.related_document = invoice

        ce = CremeEntity.objects.create(user=self.user)

        Relation.objects.create(subject_entity=invoice, object_entity=ce, type_id=REL_SUB_RELATED_TO, user=self.user)

        self.assertRaises(ProtectedError, invoice.delete)

        try:
            Invoice.objects.get(pk=invoice.pk)
            Organisation.objects.get(pk=source.pk)
            Organisation.objects.get(pk=target.pk)
            ServiceLine.objects.get(pk=service_line.pk)
            CremeEntity.objects.get(pk=ce.id)
        except Exception, e:
            #Works with Postgres with autocommit option enabled in settings
            self.fail("Exception:%s. Maybe the db doesn't support transaction ?" % e)

#TODO: add tests for other billing document (Quote, SalesOrder, CreditNote), clone on all of this (with Lines)


