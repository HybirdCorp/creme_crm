# -*- coding: utf-8 -*-

try:
    from decimal import Decimal
    from functools import partial

    from django.core.urlresolvers import reverse

    from creme.creme_core.models import Currency, FieldsConfig

    from creme.persons.tests.base import skipIfCustomOrganisation

    from ..models import PaymentInformation
    from .base import _BillingTestCase, skipIfCustomInvoice, Invoice, Organisation
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


@skipIfCustomOrganisation
class PaymentInformationTestCase(_BillingTestCase):
    def setUp(self):
        # _BillingTestCase.setUp(self)
        self.login()

    def _build_add_url(self, orga):
        # return '/billing/payment_information/add/%s' % orga.id
        return reverse('billing__create_payment_info', args=(orga.id,))

    def _build_setdefault_url(self, pi, invoice):
        # return '/billing/payment_information/set_default/%s/%s' % (pi.id, invoice.id)
        return reverse('billing__set_default_payment_info', args=(pi.id, invoice.id))

    def test_createview01(self):
        organisation = Organisation.objects.create(user=self.user, name=u"Nintendo")
        url = self._build_add_url(organisation)
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(url, data={'user': self.user.pk,
                                                           'name': "RIB of %s" % organisation,
                                                          }
                                               )
                              )

        all_pi = PaymentInformation.objects.all()
        self.assertEqual(1, len(all_pi))

        pi = all_pi[0]
        self.assertIs(True, pi.is_default)
        self.assertEqual(organisation, pi.organisation)

    def test_createview02(self):
        organisation = Organisation.objects.create(user=self.user, name=u"Nintendo")
        first_pi = PaymentInformation.objects.create(organisation=organisation, name="RIB 1", is_default=True)

        url = self._build_add_url(organisation)
        self.assertGET200(url)

        response = self.client.post(url, data={'user':       self.user.pk,
                                               'name':       "RIB of %s" % organisation,
                                               'is_default': True,
                                              }
                                   )
        self.assertNoFormError(response)

        self.assertEqual(2, PaymentInformation.objects.count())

        second_pi = PaymentInformation.objects.exclude(pk=first_pi.pk)[0]
        self.assertIs(True, second_pi.is_default)

        second_pi.delete()
        self.assertIs(True, first_pi.is_default)

    def test_createview03(self):
        "Related is not an organisation"
        self.assertGET404(self._build_add_url(self.user.linked_contact))

    def test_editview01(self):
        organisation = Organisation.objects.create(user=self.user, name=u"Nintendo")
        pi = PaymentInformation.objects.create(organisation=organisation, name="RIB 1")

        # TODO: get_edit_absolute_url() ?
        # url = '/billing/payment_information/edit/%s' % pi.id
        url = reverse('billing__edit_payment_info', args=(pi.id,))
        self.assertGET200(url)

        rib_key = "00"
        name    = "RIB of %s" % organisation
        bic     = "pen ?"
        response = self.client.post(url, data={'user':    self.user.pk,
                                               'name':    name,
                                               'rib_key': rib_key,
                                               'bic':     bic,
                                              }
                                   )
        self.assertNoFormError(response)

        pi = self.refresh(pi)
        self.assertIs(True, pi.is_default)
        self.assertEqual(name,    pi.name)
        self.assertEqual(rib_key, pi.rib_key)
        self.assertEqual(bic,     pi.bic)

    def test_editview02(self):
        create_orga = partial(Organisation.objects.create, user=self.user)
        orga1 = create_orga(name='Nintendo')
        orga2 = create_orga(name='Sega')

        create_pi = PaymentInformation.objects.create
        pi_21 = create_pi(organisation=orga2, name="RIB 1", is_default=True)  # First if no filter by organisation
        pi_11 = create_pi(organisation=orga1, name="RIB 1", is_default=True)
        pi_12 = create_pi(organisation=orga1, name="RIB 2", is_default=False)

        self.assertTrue(self.refresh(pi_11).is_default)

        # url = '/billing/payment_information/edit/%s' % pi_12.id
        url = reverse('billing__edit_payment_info', args=(pi_12.id,))
        self.assertGET200(url)

        rib_key = "00"
        name    = "RIB of %s" % orga1
        bic     = "pen ?"
        self.assertNoFormError(self.client.post(url, data={'user':       self.user.pk,
                                                           'name':       name,
                                                           'rib_key':    rib_key,
                                                           'bic':        bic,
                                                           'is_default': True,
                                                          }
                                               )
                              )

        pi_11 = self.refresh(pi_11)
        pi_12 = self.refresh(pi_12)

        self.assertFalse(pi_11.is_default)
        self.assertTrue(pi_12.is_default)

        self.assertEqual(name,    pi_12.name)
        self.assertEqual(rib_key, pi_12.rib_key)
        self.assertEqual(bic,     pi_12.bic)

        pi_12.delete()
        self.assertIs(True, self.refresh(pi_11).is_default)

    @skipIfCustomInvoice
    def test_set_default_in_invoice01(self):
        invoice, sony_source, nintendo_target = self.create_invoice_n_orgas('Playstations')
        pi_sony = PaymentInformation.objects.create(organisation=sony_source, name="RIB sony")
        url = self._build_setdefault_url(pi_sony, invoice)
        self.assertGET404(url)
        self.assertPOST200(url)
        self.assertEqual(pi_sony, self.refresh(invoice).payment_info)

    @skipIfCustomInvoice
    def test_set_default_in_invoice02(self):
        sega = Organisation.objects.create(user=self.user, name=u"Sega")
        invoice, sony_source, nintendo_target = self.create_invoice_n_orgas('Playstations')

        create_pi = PaymentInformation.objects.create
        pi_nintendo = create_pi(organisation=nintendo_target, name="RIB nintendo")
        pi_sony     = create_pi(organisation=sony_source,     name="RIB sony")
        pi_sega     = create_pi(organisation=sega,            name="RIB sega")

        def assertPostStatus(code, pi):
            self.assertEqual(code,
                             self.client.post(self._build_setdefault_url(pi, invoice)) \
                                        .status_code
                            )

        assertPostStatus(404, pi_nintendo)
        assertPostStatus(404, pi_sega)
        assertPostStatus(200, pi_sony)

    @skipIfCustomInvoice
    def test_set_default_in_invoice03(self):
        "Trashed organisation"
        invoice, sony_source = self.create_invoice_n_orgas('Playstations')[:2]
        pi_sony = PaymentInformation.objects.create(organisation=sony_source, name='RIB sony')

        sony_source.trash()

        self.assertPOST403(self._build_setdefault_url(pi_sony, invoice))
        self.assertNotEqual(pi_sony, self.refresh(invoice).payment_info)

    @skipIfCustomInvoice
    def test_set_default_in_invoice04(self):
        "'payment_info' is hidden"
        invoice, sony_source = self.create_invoice_n_orgas('Playstations')[:2]
        pi_sony = PaymentInformation.objects.create(organisation=sony_source, name='RIB sony')

        FieldsConfig.create(Invoice,
                            descriptions=[('payment_info', {FieldsConfig.HIDDEN: True})],
                           )

        self.assertPOST409(self._build_setdefault_url(pi_sony, invoice))

    @skipIfCustomInvoice
    def test_set_null_in_invoice01(self):
        sega = Organisation.objects.create(user=self.user, name=u'Sega')
        invoice, sony_source, nintendo_target = self.create_invoice_n_orgas('Playstations')

        pi_sony = PaymentInformation.objects.create(organisation=sony_source, name="RIB sony")
        self.assertPOST200(self._build_setdefault_url(pi_sony, invoice))

        currency = Currency.objects.all()[0]
        response = self.client.post(invoice.get_edit_absolute_url(), follow=True,
                                    data={'user':            self.user.pk,
                                          'name':            'Dreamcast',
                                          'issuing_date':    '2010-9-7',
                                          'expiration_date': '2010-10-13',
                                          'status':          1,
                                          'currency':        currency.pk,
                                          'discount':        Decimal(),
                                          'source':          sega.id,
                                          'target':          self.genericfield_format_entity(nintendo_target),
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertIsNone(self.refresh(invoice).payment_info)

    def test_inneredit(self):
        organisation = Organisation.objects.create(user=self.user, name=u"Nintendo")
        pi = PaymentInformation.objects.create(organisation=organisation, name="RIB 1")

        build_url = self.build_inneredit_url
        url =  build_url(pi, 'name')
        self.assertGET200(url)

        name = pi.name + ' (default)'
        response = self.client.post(url, data={'entities_lbl': [unicode(pi)],
                                               'field_value':  name,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(pi).name)

        self.assertGET(400, build_url(pi, 'organisation'))
