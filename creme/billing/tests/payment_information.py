# -*- coding: utf-8 -*-

try:
    from decimal import Decimal

    from creme_core.models import Currency
    from creme_core.tests.base import CremeTestCase

    from persons.models import Organisation

    from billing.models import *
    from billing.constants import *
    from billing.tests.base import _BillingTestCase
except Exception as e:
    print 'Error:', e


__all__ = ('PaymentInformationTestCase',)

class PaymentInformationTestCase(_BillingTestCase, CremeTestCase):
    def test_createview01(self):
        self.login()

        organisation = Organisation.objects.create(user=self.user, name=u"Nintendo")
        url = '/billing/payment_information/add/%s' % organisation.id
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={'user': self.user.pk,
                                               'name': "RIB of %s" % organisation,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        all_pi = PaymentInformation.objects.all()
        self.assertEqual(1, len(all_pi))

        pi = all_pi[0]
        self.assertIs(True, pi.is_default)
        self.assertEqual(organisation, pi.organisation)

    def test_createview02(self):
        self.login()

        organisation = Organisation.objects.create(user=self.user, name=u"Nintendo")
        first_pi = PaymentInformation.objects.create(organisation=organisation, name="RIB 1", is_default=True)

        url = '/billing/payment_information/add/%s' % organisation.id
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={'user':       self.user.pk,
                                               'name':       "RIB of %s" % organisation,
                                               'is_default': True,
                                             }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        self.assertEqual(2, PaymentInformation.objects.count())

        second_pi = PaymentInformation.objects.exclude(pk=first_pi.pk)[0]
        self.assertIs(True, second_pi.is_default)

        second_pi.delete()
        self.assertIs(True, first_pi.is_default)

    def test_editview01(self):
        self.login()

        organisation = Organisation.objects.create(user=self.user, name=u"Nintendo")
        pi = PaymentInformation.objects.create(organisation=organisation, name="RIB 1")

        url = '/billing/payment_information/edit/%s' % pi.id
        self.assertEqual(200, self.client.get(url).status_code)

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
        self.assertEqual(200, response.status_code)

        pi = self.refresh(pi)
        self.assertIs(True, pi.is_default)
        self.assertEqual(name,    pi.name)
        self.assertEqual(rib_key, pi.rib_key)
        self.assertEqual(bic,     pi.bic)

    def test_editview02(self):
        self.login()

        organisation = Organisation.objects.create(user=self.user, name=u"Nintendo")
        pi_1  = PaymentInformation.objects.create(organisation=organisation, name="RIB 1", is_default=True)
        pi_2 = PaymentInformation.objects.create(organisation=organisation, name="RIB 2",  is_default=False)

        url = '/billing/payment_information/edit/%s' % pi_2.id
        self.assertEqual(200, self.client.get(url).status_code)

        rib_key = "00"
        name    = "RIB of %s" % organisation
        bic     = "pen ?"
        response = self.client.post(url, data={'user':       self.user.pk,
                                               'name':       name,
                                               'rib_key':    rib_key,
                                               'bic':        bic,
                                               'is_default': True,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        pi_1 = self.refresh(pi_1)
        pi_2 = self.refresh(pi_2)

        self.assertFalse(pi_1.is_default)
        self.assertTrue(pi_2.is_default)

        self.assertEqual(name,    pi_2.name)
        self.assertEqual(rib_key, pi_2.rib_key)
        self.assertEqual(bic,     pi_2.bic)

        pi_2.delete()
        self.assertIs(True, self.refresh(pi_1).is_default)

    def test_set_default_in_invoice01(self):
        self.login()

        invoice, sony_source, nintendo_target = self.create_invoice_n_orgas('Playstations')
        pi_sony = PaymentInformation.objects.create(organisation=sony_source, name="RIB sony")
        self.assertEqual(200, self.client.post('/billing/payment_information/set_default/%s/%s' % (pi_sony.id, invoice.id)).status_code)

        invoice = self.refresh(invoice)
        self.assertEqual(pi_sony, invoice.payment_info)

    def test_set_default_in_invoice02(self):
        self.login()

        sega = Organisation.objects.create(user=self.user, name=u"Sega")
        invoice, sony_source, nintendo_target = self.create_invoice_n_orgas('Playstations')

        pi_nintendo = PaymentInformation.objects.create(organisation=nintendo_target, name="RIB nintendo")
        pi_sony     = PaymentInformation.objects.create(organisation=sony_source,     name="RIB sony")
        pi_sega     = PaymentInformation.objects.create(organisation=sega,            name="RIB sega")

        def assertPostStatus(code, pi):
            self.assertEqual(code,
                             self.client.post('/billing/payment_information/set_default/%s/%s' % (pi.id, invoice.id)) \
                                        .status_code
                            )

        assertPostStatus(404, pi_nintendo)
        assertPostStatus(404, pi_sega)
        assertPostStatus(200, pi_sony)

    def test_set_null_in_invoice01(self):
        self.login()

        sega = Organisation.objects.create(user=self.user, name=u"Sega")
        invoice, sony_source, nintendo_target = self.create_invoice_n_orgas('Playstations')

        pi_sony = PaymentInformation.objects.create(organisation=sony_source, name="RIB sony")
        self.assertEqual(200, self.client.post('/billing/payment_information/set_default/%s/%s' % (pi_sony.id, invoice.id)).status_code)

        currency = Currency.objects.all()[0]
        response = self.client.post('/billing/invoice/edit/%s' % invoice.id, follow=True,
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
        self.assertEqual(200, response.status_code)
        self.assertIsNone(self.refresh(invoice).payment_info)