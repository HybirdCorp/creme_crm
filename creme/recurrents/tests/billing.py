# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import Currency
    from creme.creme_core.tests.base import CremeTestCase, skipIfNotInstalled

    from creme.persons.models import Organisation

    if 'creme.billing' in settings.INSTALLED_APPS:
        from creme.billing.models import (Invoice, InvoiceStatus, TemplateBase,
                Quote, QuoteStatus, SalesOrder, SalesOrderStatus,
                CreditNote, CreditNoteStatus)
        billing_installed = True
    else:
        billing_installed = False

    from ..models import RecurrentGenerator #Periodicity
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('RecurrentsBillingTestCase',)


class RecurrentsBillingTestCase(CremeTestCase):
    ADD_URL = '/recurrents/generator/add'

    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        apps = ['creme_config', 'recurrents']

        if billing_installed:
            apps.append('billing')

        cls.populate(*apps)

    def _aux_test_create(self, model, status_model):
        self.login()
        user = self.user
        url = self.ADD_URL
        self.assertGET200(url)

        gen_name = 'Recurrent invoice'
        ct = ContentType.objects.get_for_model(model)
        #periodicity = Periodicity.objects.all()[0]
        response = self.client.post(url,
                                    data={'recurrent_generator_wizard-current_step': 0,

                                          '0-user':             user.id,
                                          '0-name':             gen_name,
                                          '0-ct':               ct.id,
                                          '0-first_generation': '08-07-2014 11:00',
                                          #'0-periodicity':      periodicity.id,
                                          '0-periodicity_0':    'months',
                                          '0-periodicity_1':    '1',
                                         }
                                    )
        self.assertNoWizardFormError(response)

        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source Orga')
        target = create_orga(name='Target Orga')

        tpl_name = 'Subscription invoice'
        status    = status_model.objects.all()[0]
        currency = Currency.objects.all()[0]
        discount = 0
        response = self.client.post(url, follow=True,
                                    data={'recurrent_generator_wizard-current_step': 1,

                                          '1-user':     user.id,
                                          '1-name':     tpl_name,
                                          '1-currency': currency.id,
                                          '1-discount': discount,
                                          '1-status':   status.id,
                                          '1-source':   source.id,
                                          '1-target':   '{"ctype":"%s", "entity":"%s"}' % (
                                                             target.entity_type_id,
                                                             target.id,
                                                         ),
                                         },
                                   )
        self.assertNoWizardFormError(response)

        gen = self.get_object_or_fail(RecurrentGenerator, name=gen_name)
        tpl = self.get_object_or_fail(TemplateBase, name=tpl_name)

        self.assertEqual(user,        gen.user)
        self.assertEqual(ct,          gen.ct)
        #self.assertEqual(periodicity, gen.periodicity)
        self.assertEqual({'type': 'months', 'value': 1}, gen.periodicity.as_dict())
        self.assertEqual(self.create_datetime(year=2014, month=7, day=8, hour=11),
                         gen.first_generation
                        )
        #self.assertEqual(gen.last_generation, gen.first_generation)
        self.assertIsNone(gen.last_generation)
        self.assertEqual(tpl, gen.template.get_real_entity())
        self.assertTrue(gen.is_working)

        self.assertEqual(user,      tpl.user)
        self.assertEqual(currency,  tpl.currency)
        self.assertEqual(status.id, tpl.status_id)
        self.assertEqual(discount,  tpl.discount)
        self.assertEqual(source,    tpl.get_source().get_real_entity())
        self.assertEqual(target,    tpl.get_target().get_real_entity())

        self.assertEqual(status.name, tpl.verbose_status)

    @skipIfNotInstalled('creme.billing')
    def test_create_invoice(self):
        self._aux_test_create(Invoice, InvoiceStatus)

    @skipIfNotInstalled('creme.billing')
    def test_create_quote(self):
        self._aux_test_create(Quote, QuoteStatus)

    @skipIfNotInstalled('creme.billing')
    def test_create_order(self):
        self._aux_test_create(SalesOrder, SalesOrderStatus)

    @skipIfNotInstalled('creme.billing')
    def test_create_note(self):
        self._aux_test_create(CreditNote, CreditNoteStatus)

    @skipIfNotInstalled('creme.billing')
    def test_create_credentials01(self):
        "Creation credentials for generated models"
        self.login(is_superuser=False, allowed_apps=['persons', 'recurrents'],
                   creatable_models=[RecurrentGenerator, Quote], #not Invoice
                  )

        url = self.ADD_URL
        self.assertGET200(url)

        user = self.user
        #periodicity = Periodicity.objects.all()[0]

        def post(model):
            ct = ContentType.objects.get_for_model(model)
            return self.client.post(url,
                                    data={'recurrent_generator_wizard-current_step': 0,

                                          '0-user':             user.id,
                                          '0-name':             'Recurrent billing obj',
                                          '0-ct':               ct.id,
                                          '0-first_generation': '08-07-2014 11:00',
                                          #'0-periodicity':      periodicity.id,
                                          '0-periodicity_0':    'weeks',
                                          '0-periodicity_1':    '3',
                                         }
                                   )

        response = post(Invoice)

        #TODO: in CremeTestCase ??
        self.assertEqual(200, response.status_code)

        with self.assertNoException(): 
            errors = response.context['wizard']['form'].errors

        self.assertEqual({'ct': [_('Select a valid choice. That choice is not one of the available choices.')]},
                         errors
                        )

        response = post(Quote)
        self.assertNoWizardFormError(response)

    def test_create_credentials02(self):
        "App credentials"
        self.login(is_superuser=False, allowed_apps=['persons'], #not 'recurrents'
                   creatable_models=[RecurrentGenerator, Quote],
                  )

        self.assertGET403(self.ADD_URL)

    @skipIfNotInstalled('creme.billing')
    def test_create_credentials03(self):
        "Creation credentials for generator"
        self.login(is_superuser=False, allowed_apps=['persons', 'recurrents'],
                   creatable_models=[Quote], #not RecurrentGenerator
                  )
        self.assertGET403(self.ADD_URL)
