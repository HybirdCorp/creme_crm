# -*- coding: utf-8 -*-

try:
    from decimal import Decimal
    from functools import partial
    from json import dumps as json_dump

    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse
    from django.utils.translation import ugettext as _

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import Relation, SetCredentials, Vat, FakeOrganisation

    from creme.persons.models import Contact, Organisation
    from creme.persons.tests.base import skipIfCustomOrganisation

    from creme.products.models import Product, Service, SubCategory
    from creme.products.tests.base import skipIfCustomProduct, skipIfCustomService

    from ..constants import (REL_SUB_HAS_LINE, REL_SUB_LINE_RELATED_ITEM,
            DISCOUNT_PERCENT, DISCOUNT_LINE_AMOUNT, DISCOUNT_ITEM_AMOUNT)
    from .base import (_BillingTestCase, skipIfCustomInvoice,
            skipIfCustomProductLine, skipIfCustomServiceLine,
            Invoice, ProductLine, ServiceLine)
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


@skipIfCustomOrganisation
@skipIfCustomInvoice
class LineTestCase(_BillingTestCase):
    DEL_VAT_URL = reverse('creme_config__delete_instance', args=('creme_core', 'vat_value'))

    def _build_msave_url(self, bdocument):
        return reverse('billing__multi_save_lines', args=(bdocument.id,))

    @skipIfCustomProduct
    def test_add_product_lines(self):
        "Multiple adding"
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001', user=self.other_user)[0]
        url = reverse('billing__create_product_lines', args=(invoice.id,))
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        self.assertEqual(_('Add one or more product to «{entity}»').format(entity=invoice),
                         context.get('title')
                        )
        self.assertEqual(_('Save the lines'), context.get('submit_label'))

        # ---
        self.assertFalse(invoice.get_lines(ServiceLine))

        product1 = self.create_product()
        product2 = self.create_product()
        vat = Vat.objects.get_or_create(value=Decimal('5.5'))[0]
        quantity = 2
        response = self.client.post(url, data={'items': self.formfield_value_multi_creator_entity(product1, product2),
                                               'quantity':       quantity,
                                               'discount_value': Decimal('20'),
                                               'vat':            vat.id,
                                              }
                                   )
        self.assertNoFormError(response)

        invoice = self.refresh(invoice)  # Refresh lines cache
        lines = invoice.get_lines(ProductLine)
        self.assertEqual(2, len(lines))

        line0, line1 = lines
        self.assertEqual(quantity, line0.quantity)
        self.assertEqual(quantity, line1.quantity)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE,          line0)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE,          line1)
        self.assertRelationCount(1, line0,   REL_SUB_LINE_RELATED_ITEM, product1)
        self.assertRelationCount(1, line1,   REL_SUB_LINE_RELATED_ITEM, product2)

        self.assertEqual(Decimal('3.2'),  invoice.total_no_vat)  # 2 * 0.8 + 2 * 0.8
        self.assertEqual(Decimal('3.38'), invoice.total_vat)  # 3.2 * 1.07 = 3.38

        self.assertEqual(invoice.get_absolute_url(), line0.get_absolute_url())

        self.assertEqual(Product, line0.related_item_class())

    def test_addlines_not_superuser(self):
        self.login(is_superuser=False,
                   allowed_apps=['persons', 'billing'],
                   creatable_models=[Invoice],
                  )
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_ALL
                                     )

        invoice = self.create_invoice_n_orgas('Invoice001', user=self.other_user)[0]
        self.assertGET200(reverse('billing__create_product_lines', args=(invoice.id,)))
        self.assertGET200(reverse('billing__create_service_lines', args=(invoice.id,)))

    def test_add_lines_link(self):
        "LINK creds are needed"
        self.login(is_superuser=False,
                   allowed_apps=['persons', 'billing'],
                   creatable_models=[Invoice],
                  )
        create_sc = partial(SetCredentials.objects.create, role=self.role,
                            set_type=SetCredentials.ESET_ALL,
                           )
        create_sc(value=EntityCredentials.VIEW   |
                        EntityCredentials.CHANGE |
                        EntityCredentials.DELETE |
                        EntityCredentials.LINK   |
                        EntityCredentials.UNLINK,
                  ctype=ContentType.objects.get_for_model(Organisation),
        )
        create_sc(value=EntityCredentials.VIEW   |
                        EntityCredentials.CHANGE |
                        EntityCredentials.DELETE |
                        # EntityCredentials.LINK   |
                        EntityCredentials.UNLINK,
                  set_type=SetCredentials.ESET_ALL
        )

        invoice = self.create_invoice_n_orgas('Invoice001', user=self.other_user)[0]
        self.assertGET403(reverse('billing__create_product_lines', args=(invoice.id,)))
        self.assertGET403(reverse('billing__create_service_lines', args=(invoice.id,)))

    def test_addlines_bad_related(self):
        "Related is not a billing entity"
        user = self.login()

        orga = Organisation.objects.create(user=user, name='Acme')
        self.assertGET404(reverse('billing__create_product_lines', args=(orga.id,)))
        self.assertGET404(reverse('billing__create_service_lines', args=(orga.id,)))

    @skipIfCustomProduct
    def test_lines_with_negatives_values(self):
        user = self.login()
        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        quote = self.create_quote_n_orgas('Quote001')[0]
        unit_price = Decimal('-50.0')
        product_name = 'on the fly product'
        create_pline = partial(ProductLine.objects.create, user=user, on_the_fly_item=product_name,
                               unit_price=unit_price, unit=''
                              )
        create_pline(related_document=quote)
        create_pline(related_document=invoice)
        self.assertEqual(Decimal('-50.0'), invoice.total_vat)
        self.assertEqual(Decimal('0'), quote.total_vat)

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_listviews(self):
        self.login()

        invoice1 = self.create_invoice_n_orgas('Invoice001')[0]
        invoice2 = self.create_invoice_n_orgas('Invoice002')[0]

        create_pline = partial(ProductLine.objects.create, user=self.user)
        pline1 = create_pline(related_document=invoice1, on_the_fly_item='FlyP1')
        pline2 = create_pline(related_document=invoice2, on_the_fly_item='FlyP2')

        create_sline = partial(ServiceLine.objects.create, user=self.user)
        sline1 = create_sline(related_document=invoice1, on_the_fly_item='FlyS1')
        sline2 = create_sline(related_document=invoice2, on_the_fly_item='FlyS2')

        # ---------------------------------------------------------------------
        response = self.assertGET200(reverse('billing__list_product_lines'))

        with self.assertNoException():
            # plines_page = response.context['entities']
            plines_page = response.context['page_obj']

        self.assertEqual(2, plines_page.paginator.count)

        self.assertIn(pline1, plines_page.object_list)
        self.assertIn(pline2, plines_page.object_list)

        # ---------------------------------------------------------------------
        response = self.assertGET200(reverse('billing__list_service_lines'))

        with self.assertNoException():
            # slines_page = response.context['entities']
            slines_page = response.context['page_obj']

        self.assertEqual(2, slines_page.paginator.count)

        self.assertIn(sline1, slines_page.object_list)
        self.assertIn(sline2, slines_page.object_list)

    @skipIfCustomProductLine
    def test_delete_product_line01(self):
        self.login()
        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        product_line = ProductLine.objects.create(user=self.user, related_document=invoice,
                                                  on_the_fly_item='Flyyyyy',
                                                 )
        self.assertPOST404(reverse('creme_core__delete_related_to_entity', args=(product_line.entity_type_id,)),
                           data={'id': product_line.id},
                          )
        self.assertPOST200(product_line.get_delete_absolute_url(), follow=True)
        self.assertFalse(self.refresh(invoice).get_lines(ProductLine))
        self.assertFalse(ProductLine.objects.exists())

    @skipIfCustomService
    def test_add_service_lines01(self):
        "Multiple adding"
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001', user=self.other_user)[0]
        url = reverse('billing__create_service_lines', args=(invoice.id,))
        self.assertGET200(url)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        self.assertEqual(_('Add one or more service to «{entity}»').format(entity=invoice),
                         context.get('title')
                        )
        self.assertEqual(_('Save the lines'), context.get('submit_label'))

        # ---
        self.assertFalse(invoice.get_lines(Service))

        service1 = self.create_service()
        service2 = self.create_service()
        vat = Vat.objects.get_or_create(value=Decimal('19.6'))[0]
        quantity = 2
        response = self.client.post(url, data={'items': self.formfield_value_multi_creator_entity(service1, service2),
                                               'quantity':       quantity,
                                               'discount_value': Decimal('10'),
                                               'vat':            vat.id,
                                              }
                                   )
        self.assertNoFormError(response)

        invoice = self.refresh(invoice)  # Refresh lines cache
        lines = invoice.get_lines(ServiceLine)
        self.assertEqual(2, len(lines))

        # lines = invoice.service_lines
        line0 = lines[0]
        line1 = lines[1]
        self.assertEqual(quantity, line0.quantity)
        self.assertEqual(quantity, line1.quantity)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE,          line0)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE,          line1)
        self.assertRelationCount(1, line0,   REL_SUB_LINE_RELATED_ITEM, service1)
        self.assertRelationCount(1, line1,   REL_SUB_LINE_RELATED_ITEM, service2)

        self.assertEqual(Decimal('21.6'),  invoice.total_no_vat)  # 2 * 5.4 + 2 * 5.4
        self.assertEqual(Decimal('25.84'), invoice.total_vat)  # 21.6 * 1.196 = 25.84

        self.assertEqual(Service, line0.related_item_class())

    @skipIfCustomProductLine
    def test_related_document01(self):
        user = self.login()
        invoice = self.create_invoice_n_orgas('Invoice001')[0]

        product_line = ProductLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item='Flyyyyy',
                                                 )
        self.assertEqual(invoice, product_line.related_document)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE, product_line)

    @skipIfCustomProduct
    @skipIfCustomProductLine
    def test_related_item01(self):
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        product = self.create_product()

        product_line = ProductLine.objects.create(user=user, related_document=invoice,
                                                  related_item=product,
                                                 )
        self.assertEqual(product, product_line.related_item)
        self.assertRelationCount(1, product_line, REL_SUB_LINE_RELATED_ITEM, product)

        product_line = self.refresh(product_line)
        with self.assertNumQueries(3):
            p = product_line.related_item

        self.assertEqual(product, p)

    @skipIfCustomProductLine
    def test_related_item02(self):
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        product_line = ProductLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item='Flyyyyy',
                                                 )
        self.assertIsNone(product_line.related_item)

        product_line = self.refresh(product_line)
        with self.assertNumQueries(0):
            p = product_line.related_item

        self.assertIsNone(p)

    @skipIfCustomProductLine
    def test_related_item03(self):
        with self.assertNumQueries(0):
            product_line = ProductLine()
            product = product_line.related_item

        self.assertIsNone(product)

    @skipIfCustomProduct
    @skipIfCustomProductLine
    def test_product_line_clone(self):
        user = self.login()

        product = self.create_product()
        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        invoice2 = self.create_invoice_n_orgas('Invoice002')[0]

        product_line = ProductLine.objects.create(user=user, related_document=invoice,
                                                  related_item=product,
                                                 )
        product_line2 = product_line.clone(invoice2)

        product_line2 = self.refresh(product_line2)
        self.assertEqual(invoice2, product_line2.related_document)
        self.assertEqual(product, product_line2.related_item)

        rel_filter = Relation.objects.filter
        self.assertEqual([product_line2.pk],
                         list(rel_filter(type=REL_SUB_HAS_LINE, subject_entity=invoice2)
                                        .values_list('object_entity', flat=True)
                             )
                        )
        self.assertEqual({product_line.pk, product_line2.pk},
                         set(rel_filter(type=REL_SUB_LINE_RELATED_ITEM, object_entity=product)
                                       .values_list('subject_entity', flat=True)
                            )
                        )

    @skipIfCustomServiceLine
    def test_service_line_clone(self):
        user = self.login()

        service = self.create_service()
        invoice1 = self.create_invoice_n_orgas('Invoice001')[0]
        invoice2 = self.create_invoice_n_orgas('Invoice002')[0]

        service_line1 = ServiceLine.objects.create(user=user, related_document=invoice1,
                                                   related_item=service,
                                                  )

        service_line2 = service_line1.clone(invoice2)
        service_line2 = self.refresh(service_line2)
        self.assertEqual(invoice2, service_line2.related_document)
        self.assertEqual(service, service_line2.related_item)
        self.assertNotEqual(service_line1, service_line2)

        rel_filter = Relation.objects.filter
        self.assertEqual([service_line1.pk], list(rel_filter(type=REL_SUB_HAS_LINE, subject_entity=invoice1).values_list('object_entity', flat=True)))
        self.assertEqual([service_line2.pk], list(rel_filter(type=REL_SUB_HAS_LINE, subject_entity=invoice2).values_list('object_entity', flat=True)))
        self.assertEqual({service_line1.pk, service_line2.pk},
                         set(rel_filter(type=REL_SUB_LINE_RELATED_ITEM, object_entity=service)
                                       .values_list('subject_entity', flat=True)
                            )
                        )

    @skipIfCustomProductLine
    def test_multiple_delete01(self):
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001', discount=0)[0]

        create_line = partial(ProductLine.objects.create, user=user, related_document=invoice)
        ids = tuple(create_line(on_the_fly_item='Fly ' + price,
                                unit_price=Decimal(price)
                               ).id for price in ('10', '20')
                   )

        invoice.save()  # Updates totals

        self.assertEqual(2, len(invoice.get_lines(ProductLine)))
        expected_total = Decimal('30')
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

        self.assertPOST200(reverse('creme_core__delete_entities'), follow=True,
                           data={'ids': '{},{}'.format(*ids)}
                          )
        self.assertFalse(ProductLine.objects.filter(pk__in=ids))

        invoice = self.refresh(invoice)
        self.assertFalse(invoice.get_lines(ProductLine))

        expected_total = Decimal('0')
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

    @skipIfCustomProductLine
    def test_multiple_delete02(self):
        user = self.login(is_superuser=False, allowed_apps=['persons', 'billing'],
                          creatable_models=[Invoice, Organisation]
                         )

        SetCredentials.objects.create(role=self.role,
                                      # Not EntityCredentials.CHANGE
                                      value=EntityCredentials.VIEW | EntityCredentials.DELETE |
                                            EntityCredentials.LINK | EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        invoice = self.create_invoice_n_orgas('Invoice001', discount=0)[0]
        self.assertFalse(user.has_perm_to_change(invoice))

        create_line = partial(ProductLine.objects.create, user=user,
                              related_document=invoice
                             )
        ids = tuple(create_line(on_the_fly_item='Fly ' + price,
                                unit_price=Decimal(price)
                               ).id for price in ('10', '20')
                   )

        self.assertPOST403(reverse('creme_core__delete_entities'), follow=True,
                           data={'ids': '{},{}'.format(*ids)}
                          )
        self.assertEqual(2, ProductLine.objects.filter(pk__in=ids).count())

    def test_delete_vat01(self):
        self.login()

        vat = Vat.objects.create(value=Decimal('5.0'), is_default=True, is_custom=True)
        self.assertPOST200(self.DEL_VAT_URL, data={'id': vat.pk})
        self.assertDoesNotExist(vat)

    @skipIfCustomProductLine
    def test_delete_vat02(self):
        user = self.login()

        vat = Vat.objects.create(value=Decimal('5.0'), is_default=True, is_custom=True)
        invoice = self.create_invoice_n_orgas('Nerv')[0]
        line = ProductLine.objects.create(user=user, related_document=invoice,
                                          on_the_fly_item='Flyyyyy', vat_value=vat,
                                         )

        self.assertPOST404(self.DEL_VAT_URL, data={'id': vat.pk})
        self.assertStillExists(vat)

        self.get_object_or_fail(Invoice, pk=invoice.pk)

        line = self.get_object_or_fail(ProductLine, pk=line.pk)
        self.assertEqual(vat, line.vat_value)

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_mass_import(self):
        self.login()
        self.assertGET404(self._build_import_url(ServiceLine))
        self.assertGET404(self._build_import_url(ProductLine))

    def _build_add2catalog_url(self, line):
        return reverse('billing__add_to_catalog', args=(line.id,))

    def _build_dict_cat_subcat(self, cat, subcat):
        return {'sub_category': json_dump({'category': cat.id, 'subcategory': subcat.id})}

    def test_convert_on_the_fly_line_to_real_item_error(self):
        "Entity is not a line"
        user = self.login()
        self.assertGET404(self._build_add2catalog_url(user.linked_contact))

    @skipIfCustomProductLine
    def test_convert_on_the_fly_line_to_real_item01(self):
        "Convert on the fly product"
        user = self.login()

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        unit_price = Decimal('50.0')
        product_name = 'on the fly product'
        product_line = ProductLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item=product_name,
                                                  unit_price=unit_price, unit='',
                                                 )
        cat, subcat = self.create_cat_n_subcat()

        url = self._build_add2catalog_url(product_line)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        self.assertEqual(_('Add this on the fly item to your catalog'), context.get('title'))
        self.assertEqual(_('Add to the catalog'),                       context.get('submit_label'))

        # ---
        response = self.client.post(url, data=self._build_dict_cat_subcat(cat, subcat))
        self.assertNoFormError(response)
        self.assertTrue(Product.objects.exists())

        self.get_object_or_fail(Product, name=product_name, unit_price=unit_price, user=user)

    @skipIfCustomServiceLine
    def test_convert_on_the_fly_line_to_real_item02(self):
        "Convert on the fly service"
        user = self.login()

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        unit_price = Decimal('50.0')
        service_name = 'on the fly service'
        service_line = ServiceLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item=service_name,
                                                  unit_price=unit_price, unit='',
                                                 )
        cat, subcat = self.create_cat_n_subcat()

        response = self.client.post(self._build_add2catalog_url(service_line),
                                      data=self._build_dict_cat_subcat(cat, subcat))

        self.assertNoFormError(response)
        self.assertTrue(Service.objects.exists())

        self.get_object_or_fail(Service, name=service_name, unit_price=unit_price, user=user)

    @skipIfCustomProductLine
    def test_convert_on_the_fly_line_to_real_item03(self):
        "On-the-fly + product creation + no creation creds"
        user = self.login(is_superuser=False, allowed_apps=['persons', 'billing'],
                          creatable_models=[Invoice, Contact, Organisation],  # Not 'Product'
                         )

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE | EntityCredentials.LINK |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        product_line = ProductLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item='on the fly service',
                                                  unit_price=Decimal('50.0')
                                                 )
        cat, subcat = self.create_cat_n_subcat()
        self.assertPOST403(self._build_add2catalog_url(product_line),
                           data=self._build_dict_cat_subcat(cat, subcat))

        self.assertFalse(Product.objects.exists())

    @skipIfCustomServiceLine
    def test_convert_on_the_fly_line_to_real_item04(self):
        "On-the-fly + service creation + no creation creds"
        user = self.login(is_superuser=False, allowed_apps=['persons', 'billing'],
                          creatable_models=[Invoice, Contact, Organisation],  # Not 'Service'
                         )

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE | EntityCredentials.LINK |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        service_line = ServiceLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item='on the fly service',
                                                  unit_price=Decimal('50.0')
                                                 )
        cat, subcat = self.create_cat_n_subcat()
        self.assertPOST403(self._build_add2catalog_url(service_line),
                           data=self._build_dict_cat_subcat(cat, subcat))

        self.assertFalse(Service.objects.exists())

    @skipIfCustomProductLine
    def test_convert_on_the_fly_line_to_real_item05(self):
        "Already related item product line"
        user = self.login()

        product = self.create_product()
        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        product_line = ProductLine.objects.create(user=user, related_document=invoice,
                                                  related_item=product,
                                                  unit_price=Decimal('50.0')
                                                 )
        cat, subcat = self.create_cat_n_subcat()
        response = self.assertPOST200(self._build_add2catalog_url(product_line),
                                      data=self._build_dict_cat_subcat(cat, subcat))

        self.assertFormError(response, 'form', None,
                             _('You are not allowed to add this item to the catalog because it is not on the fly')
                            )
        self.assertEqual(1, Product.objects.count())

    @skipIfCustomServiceLine
    def test_convert_on_the_fly_line_to_real_item06(self):
        "Already related item service line"
        user = self.login()

        service = self.create_service()
        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        service_line = ServiceLine.objects.create(user=user, related_document=invoice,
                                                  related_item=service,
                                                  unit_price=Decimal('50.0')
                                                 )
        cat, subcat = self.create_cat_n_subcat()
        response = self.assertPOST200(self._build_add2catalog_url(service_line),
                                      data=self._build_dict_cat_subcat(cat, subcat))

        self.assertFormError(response, 'form', None,
                             _('You are not allowed to add this item to the catalog because it is not on the fly')
                            )
        self.assertEqual(1, Service.objects.count())

    @skipIfCustomServiceLine
    def test_multi_save_lines01(self):
        "1 service line updated"
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        service_line = ServiceLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item='on the fly service',
                                                  unit_price=Decimal('50.0')
                                                 )

        name = 'on the fly service updated'
        unit_price = '100.0'
        quantity = '2'
        unit = 'day'
        discount = '20'
        discount_unit = DISCOUNT_PERCENT
        response = self.client.post(self._build_msave_url(invoice),
                                    data={service_line.entity_type_id: json_dump({
                                                        'service_line_formset-TOTAL_FORMS':       1,
                                                        'service_line_formset-INITIAL_FORMS':     1,
                                                        'service_line_formset-MAX_NUM_FORMS':     '',
                                                        'service_line_formset-0-cremeentity_ptr': service_line.id,
                                                        'service_line_formset-0-user':            user.id,
                                                        'service_line_formset-0-on_the_fly_item': name,
                                                        'service_line_formset-0-unit_price':      unit_price,
                                                        'service_line_formset-0-quantity':        quantity,
                                                        'service_line_formset-0-discount':        discount,
                                                        'service_line_formset-0-discount_unit':   discount_unit,
                                                        'service_line_formset-0-vat_value':       Vat.objects.all()[1].id,
                                                        'service_line_formset-0-unit':            unit,
                                                    })
                                           }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(1, ServiceLine.objects.count())

        service_line = self.refresh(service_line)
        self.assertEqual(name,                service_line.on_the_fly_item)
        self.assertEqual(Decimal(unit_price), service_line.unit_price)
        self.assertEqual(Decimal(quantity),   service_line.quantity)
        self.assertEqual(unit,                service_line.unit)
        self.assertEqual(Decimal(discount),   service_line.discount)
        self.assertEqual(discount_unit,       service_line.discount_unit)
        self.assertIs(service_line.total_discount, False)

    @skipIfCustomProductLine
    def test_multi_save_lines02(self):
        "1 product line created on the fly and 1 deleted"
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        product_line = ProductLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item='on the fly service',
                                                  unit_price=Decimal('50.0'),
                                                 )
        name = 'new on the fly product'
        unit_price = '69.0'
        quantity = '2'
        unit = 'month'
        response = self.client.post(
            self._build_msave_url(invoice),
            data={product_line.entity_type_id: json_dump({
                                'product_line_formset-TOTAL_FORMS':       2,
                                'product_line_formset-INITIAL_FORMS':     1,
                                'product_line_formset-MAX_NUM_FORMS':     '',
                                'product_line_formset-0-DELETE':          True,
                                'product_line_formset-0-cremeentity_ptr': product_line.id,
                                'product_line_formset-0-user':            user.id,
                                'product_line_formset-0-on_the_fly_item': 'whatever',
                                'product_line_formset-0-unit_price':      'whatever',
                                'product_line_formset-0-quantity':        'whatever',
                                'product_line_formset-0-discount':        'whatever',
                                'product_line_formset-0-discount_unit':   'whatever',
                                'product_line_formset-0-vat_value':       'whatever',
                                'product_line_formset-0-unit':            'whatever',
                                'product_line_formset-1-user':            user.id,
                                'product_line_formset-1-on_the_fly_item': name,
                                'product_line_formset-1-unit_price':      unit_price,
                                'product_line_formset-1-quantity':        quantity,
                                'product_line_formset-1-discount':        '50.00',
                                'product_line_formset-1-discount_unit':   '1',
                                'product_line_formset-1-vat_value':       Vat.objects.all()[0].id,
                                'product_line_formset-1-unit':            unit,
                            })
                 }
        )
        self.assertNoFormError(response)
        product_lines = ProductLine.objects.all()
        self.assertEqual(1, len(product_lines))

        product_line = product_lines[0]
        self.assertEqual(name,                product_line.on_the_fly_item)
        self.assertEqual(Decimal(unit_price), product_line.unit_price)
        self.assertEqual(Decimal(quantity),   product_line.quantity)
        self.assertEqual(unit,                product_line.unit)

    @skipIfCustomServiceLine
    def test_multi_save_lines03(self):
        "No creds"
        user = self.login(is_superuser=False, allowed_apps=['persons', 'billing'],
                          creatable_models=[Invoice, Contact, Organisation],
                         )

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.DELETE | EntityCredentials.LINK |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        service_line = ServiceLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item='on the fly service',
                                                  unit_price=Decimal('50.0')
                                                 )

        self.assertPOST403(self._build_msave_url(invoice),
                           data={service_line.entity_type_id: json_dump({
                                                'service_line_formset-TOTAL_FORMS':       1,
                                                'service_line_formset-INITIAL_FORMS':     1,
                                                'service_line_formset-MAX_NUM_FORMS':     '',
                                                'service_line_formset-0-cremeentity_ptr': service_line.id,
                                                'service_line_formset-0-user':            user.id,
                                                'service_line_formset-0-on_the_fly_item': 'on the fly service updated',
                                                'service_line_formset-0-unit_price':      '100.0',
                                                'service_line_formset-0-quantity':        '2',
                                                'service_line_formset-0-discount':        '20',
                                                'service_line_formset-0-discount_unit':   '1',
                                                'service_line_formset-0-vat_value':       Vat.objects.all()[0].id,
                                                'service_line_formset-0-unit':            'day',
                                            })
                                }
                           )

    @skipIfCustomServiceLine
    def test_multi_save_lines04(self):
        "Other type of discount: amount per line"
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        service_line = ServiceLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item='on the fly service',
                                                  unit_price=Decimal('50.0')
                                                 )

        discount_unit = DISCOUNT_LINE_AMOUNT
        response = self.client.post(self._build_msave_url(invoice),
                                    data={service_line.entity_type_id: json_dump({
                                                        'service_line_formset-TOTAL_FORMS':       1,
                                                        'service_line_formset-INITIAL_FORMS':     1,
                                                        'service_line_formset-MAX_NUM_FORMS':     '',
                                                        'service_line_formset-0-cremeentity_ptr': service_line.id,
                                                        'service_line_formset-0-user':            user.id,
                                                        'service_line_formset-0-on_the_fly_item': 'on the fly service updated',
                                                        'service_line_formset-0-unit_price':      '100.0',
                                                        'service_line_formset-0-quantity':        '2',
                                                        'service_line_formset-0-discount':        '20',
                                                        'service_line_formset-0-discount_unit':   discount_unit,
                                                        'service_line_formset-0-vat_value':       Vat.objects.all()[1].id,
                                                        'service_line_formset-0-unit':            'day',
                                                    })
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(1, ServiceLine.objects.count())

        service_line = self.refresh(service_line)
        self.assertEqual(discount_unit, service_line.discount_unit)
        self.assertIs(service_line.total_discount, True)

    @skipIfCustomServiceLine
    def test_multi_save_lines05(self):
        "Other type of discount: amount per item"
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        service_line = ServiceLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item='on the fly service',
                                                  unit_price=Decimal('50.0')
                                                 )

        response = self.client.post(self._build_msave_url(invoice),
                                    data={service_line.entity_type_id: json_dump({
                                                'service_line_formset-TOTAL_FORMS':       1,
                                                'service_line_formset-INITIAL_FORMS':     1,
                                                'service_line_formset-MAX_NUM_FORMS':     '',
                                                'service_line_formset-0-cremeentity_ptr': service_line.id,
                                                'service_line_formset-0-user':            user.id,
                                                'service_line_formset-0-on_the_fly_item': 'on the fly service updated',
                                                'service_line_formset-0-unit_price':      '100.0',
                                                'service_line_formset-0-quantity':        '2',
                                                'service_line_formset-0-discount':        '20',
                                                'service_line_formset-0-discount_unit':   DISCOUNT_ITEM_AMOUNT,
                                                'service_line_formset-0-vat_value':       Vat.objects.all()[1].id,
                                                'service_line_formset-0-unit':            'day',
                                            }),
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(1, ServiceLine.objects.count())

        service_line = self.refresh(service_line)
        self.assertEqual(DISCOUNT_LINE_AMOUNT, service_line.discount_unit)
        self.assertIs(service_line.total_discount, False)

    @skipIfCustomServiceLine
    def test_multi_save_lines06(self):
        "1 service line updated with concrete related Service"
        user = self.login()

        sub_cat = SubCategory.objects.all()[0]
        shipping = Service.objects.create(user=user, name='Shipping',
                                          category=sub_cat.category,
                                          sub_category=sub_cat,
                                          unit_price=Decimal('60.0'),
                                         )

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        line = ServiceLine.objects.create(user=user, related_document=invoice,
                                          related_item=shipping,
                                          unit_price=Decimal('50.0'),
                                          vat_value=Vat.objects.all()[0],
                                         )

        response = self.client.post(self._build_msave_url(invoice),
                                    data={line.entity_type_id: json_dump({
                                                'service_line_formset-TOTAL_FORMS':       1,
                                                'service_line_formset-INITIAL_FORMS':     1,
                                                'service_line_formset-MAX_NUM_FORMS':     '',
                                                'service_line_formset-0-cremeentity_ptr': line.id,
                                                'service_line_formset-0-user':            user.id,
                                                # 'service_line_formset-0-on_the_fly_item': '',  # <==
                                                'service_line_formset-0-unit_price':      '51',
                                                'service_line_formset-0-quantity':        str(line.quantity),
                                                'service_line_formset-0-discount':        str(line.discount),
                                                'service_line_formset-0-discount_unit':   str(line.discount_unit),
                                                'service_line_formset-0-vat_value':       line.vat_value_id,
                                                'service_line_formset-0-unit':            line.unit,
                                            }),
                                         }
                                   )
        self.assertNoFormError(response)

        line = self.refresh(line)
        self.assertIsNone(line.on_the_fly_item)
        self.assertEqual(Decimal('51'), line.unit_price)

    def test_multi_save_lines07(self):
        "Bad related model"
        user = self.login()
        orga = FakeOrganisation.objects.create(user=user, name='Foxhound')
        ct_id = ContentType.objects.get_for_model(ProductLine).id
        self.assertPOST404(
            self._build_msave_url(orga),
            data={ct_id: json_dump({
                         'product_line_formset-TOTAL_FORMS':       1,
                         'product_line_formset-INITIAL_FORMS':     0,
                         'product_line_formset-MAX_NUM_FORMS':     '',
                         'product_line_formset-0-user':            user.id,
                         'product_line_formset-0-on_the_fly_item': 'New on the fly product',
                         'product_line_formset-0-unit_price':      '69.0',
                         'product_line_formset-0-quantity':        '2',
                         'product_line_formset-0-discount':        '50.00',
                         'product_line_formset-0-discount_unit':   '1',
                         'product_line_formset-0-vat_value':       Vat.objects.first().id,
                         'product_line_formset-0-unit':            'month',
                     }),
              },
        )

    @skipIfCustomProductLine
    def test_global_discount_change(self):
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001', discount=0)[0]

        ProductLine.objects.create(user=user, unit_price=Decimal('10'),
                                   vat_value=Vat.get_default_vat(),
                                   related_document=invoice,
                                   on_the_fly_item='Flyyyyy',
                                  )

        discount_zero = Decimal('0.0')
        full_discount = Decimal('100.0')

        self.assertEqual(invoice.discount, discount_zero)

        invoice.discount = full_discount
        invoice.save()

        invoice = self.refresh(invoice)

        self.assertEqual(invoice.discount, full_discount)
        self.assertEqual(invoice.total_no_vat, discount_zero)
        self.assertEqual(invoice.total_vat, discount_zero)

    @skipIfCustomProductLine
    def test_rounding_policy(self):
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice0001')[0]

        kwargs = {'user': user, 'related_document': invoice}
        product_line = ProductLine.objects.create(on_the_fly_item='Flyyy product',
                                                  unit_price=Decimal('0.014'), quantity=1,
                                                  total_discount=False,
                                                  **kwargs
                                                 )
        # 0.014 rounded down to 0.01
        self.assertEqual(Decimal('0.01'), product_line.get_price_exclusive_of_tax())

        product_line = ProductLine.objects.create(on_the_fly_item='Flyyy product',
                                                  unit_price=Decimal('0.015'), quantity=1,
                                                  total_discount=False,
                                                  **kwargs
                                                 )
        # 0.015 rounded up to 0.02
        self.assertEqual(Decimal('0.02'), product_line.get_price_exclusive_of_tax())

        product_line = ProductLine.objects.create(on_the_fly_item='Flyyy product',
                                                  unit_price=Decimal('0.016'), quantity=1,
                                                  total_discount=False,
                                                  **kwargs
                                                 )
        # 0.016 rounded up to 0.02
        self.assertEqual(Decimal('0.02'), product_line.get_price_exclusive_of_tax())

    @skipIfCustomProductLine
    def test_inneredit(self):
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001', discount=0)[0]
        pline = ProductLine.objects.create(user=user, unit_price=Decimal('10'),
                                           vat_value=Vat.get_default_vat(),
                                           related_document=invoice,
                                           on_the_fly_item='Flyyyyy',
                                           comment='I believe',
                                          )

        build_url = self.build_inneredit_url
        url = build_url(pline, 'comment')
        self.assertGET200(url)

        comment = pline.comment + ' I can flyyy'
        response = self.client.post(url, data={'entities_lbl': [str(pline)],
                                               'field_value':  comment,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(comment, self.refresh(pline).comment)

        self.assertGET(400, build_url(pline, 'on_the_fly_item'))
        self.assertGET(400, build_url(pline, 'total_discount'))
        self.assertGET(400, build_url(pline, 'discount_unit'))
