# -*- coding: utf-8 -*-

try:
    from datetime import date
    from decimal import Decimal
    from functools import partial

    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme_core.tests.base import CremeTestCase
    from creme_core.tests.views.csv_import import CSVImportBaseTestCaseMixin
    from creme_core.models import CremeEntity, RelationType, CremeProperty, SetCredentials, Currency
    from creme_core.auth.entity_credentials import EntityCredentials
    from creme_core.constants import PROP_IS_MANAGED_BY_CREME, DEFAULT_CURRENCY_PK

    from creme_config.models import SettingKey, SettingValue

    from persons.models import Organisation, Contact
    from persons.constants import REL_SUB_PROSPECT, REL_SUB_CUSTOMER_SUPPLIER

    from products.models import Product, Service

    from billing.models import Quote, SalesOrder, Invoice, ServiceLine #Vat
    from billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED

    from opportunities.models import Opportunity, SalesPhase, Origin
    import opportunities.constants as opp_constants
    from opportunities.constants import (REL_OBJ_TARGETS, REL_SUB_EMIT_ORGA, REL_SUB_LINKED_INVOICE,
                                         REL_SUB_LINKED_QUOTE, REL_SUB_CURRENT_DOC)
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class OpportunitiesTestCase(CremeTestCase, CSVImportBaseTestCaseMixin):
    ADD_URL = '/opportunities/opportunity/add'
    ADDTO_URL = '/opportunities/opportunity/add_to/%s'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'documents', 'persons',
                     'commercial', 'billing', 'activities', 'opportunities'
                    )

    def tearDown(self):
        if self.doc:
            self.doc.filedata.delete() #clean

    def _genericfield_format_entity(self, entity):
        return '{"ctype":"%s", "entity":"%s"}' % (entity.entity_type_id, entity.id)

    def _create_target_n_emitter(self, managed=True, contact=False):
        user = self.user
        create_orga = Organisation.objects.create
        emitter = create_orga(user=user, name='My society')
        target  = create_orga(user=user, name='Target renegade') if not contact else \
                  Contact.objects.create(user=user, first_name='Target', last_name='Renegade')

        if managed:
            CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        return target, emitter

    def _create_opportunity_n_organisations(self, name='Opp'):
        target, emitter = self._create_target_n_emitter()
        opp = Opportunity.objects.create(user=self.user, name=name,
                                         sales_phase=SalesPhase.objects.all()[0],
                                         emitter=emitter, target=target,
                                        )

        return opp, target, emitter

    def test_populate(self): #test get_compatible_ones() too
        ct = ContentType.objects.get_for_model(Opportunity)
        relation_types = dict((rtype.id, rtype) for rtype in RelationType.get_compatible_ones(ct))

        self.assertNotIn(opp_constants.REL_SUB_TARGETS, relation_types)
        self.get_relationtype_or_fail(opp_constants.REL_SUB_TARGETS, [Opportunity], [Contact, Organisation])

        self.assertNotIn(REL_SUB_EMIT_ORGA, relation_types)
        self.get_relationtype_or_fail(opp_constants.REL_OBJ_EMIT_ORGA, [Opportunity], [Organisation])

        self.assertIn(opp_constants.REL_OBJ_LINKED_PRODUCT, relation_types)
        self.assertNotIn(opp_constants.REL_SUB_LINKED_PRODUCT, relation_types)
        self.get_relationtype_or_fail(opp_constants.REL_OBJ_LINKED_PRODUCT, [Opportunity], [Product])

        self.assertIn(opp_constants.REL_OBJ_LINKED_SERVICE, relation_types)
        self.assertNotIn(opp_constants.REL_SUB_LINKED_SERVICE, relation_types)
        self.get_relationtype_or_fail(opp_constants.REL_OBJ_LINKED_SERVICE, [Opportunity], [Service])

        self.assertIn(opp_constants.REL_OBJ_LINKED_CONTACT, relation_types)
        self.assertNotIn(opp_constants.REL_SUB_LINKED_CONTACT, relation_types)
        self.get_relationtype_or_fail(opp_constants.REL_OBJ_LINKED_CONTACT, [Opportunity], [Contact])

        self.assertIn(opp_constants.REL_OBJ_LINKED_SALESORDER, relation_types)
        self.assertNotIn(opp_constants.REL_SUB_LINKED_SALESORDER, relation_types)
        self.get_relationtype_or_fail(opp_constants.REL_OBJ_LINKED_SALESORDER, [Opportunity], [SalesOrder])

        self.assertIn(opp_constants.REL_OBJ_LINKED_INVOICE, relation_types)
        self.assertNotIn(REL_SUB_LINKED_INVOICE, relation_types)
        self.get_relationtype_or_fail(opp_constants.REL_OBJ_LINKED_INVOICE, [Opportunity], [Invoice])

        self.assertIn(opp_constants.REL_OBJ_LINKED_QUOTE, relation_types)
        self.assertNotIn(REL_SUB_LINKED_QUOTE, relation_types)
        self.get_relationtype_or_fail(opp_constants.REL_OBJ_LINKED_QUOTE, [Opportunity], [Quote])

        self.assertIn(opp_constants.REL_OBJ_RESPONSIBLE, relation_types)
        self.assertNotIn(opp_constants.REL_SUB_RESPONSIBLE, relation_types)
        self.get_relationtype_or_fail(opp_constants.REL_OBJ_RESPONSIBLE, [Opportunity], [Contact])

        self.get_relationtype_or_fail(opp_constants.REL_OBJ_CURRENT_DOC, [Opportunity], [Invoice, Quote, SalesOrder])

        self.assertTrue(SalesPhase.objects.exists())
        self.assertTrue(Origin.objects.exists())

        keys = SettingKey.objects.filter(pk=opp_constants.SETTING_USE_CURRENT_QUOTE)
        self.assertEqual(1, len(keys))
        self.assertEqual(1, SettingValue.objects.filter(key=keys[0]).count())

    def test_portal(self):
        self.login()
        self.assertGET200('/opportunities/')

    def test_createview01(self):
        self.login()

        url = self.ADD_URL
        self.assertGET200(url)

        target, emitter = self._create_target_n_emitter()
        name  = 'Opportunity01'
        phase = SalesPhase.objects.all()[0]
        response = self.client.post(url, follow=True,
                                    data={'user':                  self.user.pk,
                                          'name':                  name,
                                          'sales_phase':           phase.id,
                                          'expected_closing_date': '2010-9-20',
                                          'closing_date':          '2010-10-11',
                                          'target':                self._genericfield_format_entity(target),
                                          'emitter':               emitter.id,
                                          'first_action_date':     '2010-7-13',
                                          'currency':              DEFAULT_CURRENCY_PK,
                                         }
                                   )
        self.assertNoFormError(response)

        opportunity =  self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(phase,              opportunity.sales_phase)
        self.assertEqual(date(2010, 9,  20), opportunity.expected_closing_date)
        self.assertEqual(date(2010, 10, 11), opportunity.closing_date)
        self.assertEqual(date(2010, 7,  13), opportunity.first_action_date)

        self.assertRelationCount(1, target,  REL_OBJ_TARGETS,   opportunity)
        self.assertEqual(target, opportunity.target)

        self.assertRelationCount(1, emitter, REL_SUB_EMIT_ORGA, opportunity)
        self.assertEqual(emitter, opportunity.emitter)

        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

    def test_createview02(self):
        self.login()

        target, emitter = self._create_target_n_emitter()
        name  = 'Opportunity01'
        phase = SalesPhase.objects.all()[0]
        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'user':                  self.user.pk,
                                          'name':                  name,
                                          'sales_phase':           phase.id,
                                          'expected_closing_date': '2010-9-20',
                                          'closing_date':          '2010-10-11',
                                          'target':                self._genericfield_format_entity(target),
                                          'emitter':               emitter.id,
                                          'first_action_date':     '2010-7-13',
                                          'currency':              DEFAULT_CURRENCY_PK,
                                         }
                                   )
        self.assertNoFormError(response)

        opportunity =  self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(phase,              opportunity.sales_phase)
        self.assertEqual(date(2010, 9,  20), opportunity.expected_closing_date)
        self.assertEqual(date(2010, 10, 11), opportunity.closing_date)
        self.assertEqual(date(2010, 7,  13), opportunity.first_action_date)

        self.assertRelationCount(1, target,  REL_OBJ_TARGETS,   opportunity)
        self.assertRelationCount(1, emitter, REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

        with self.assertNumQueries(1):
            prop_emitter = opportunity.emitter
        self.assertEqual(emitter, prop_emitter)

        with self.assertNumQueries(3):
            prop_target = opportunity.target
        self.assertEqual(target, prop_target)

    def test_createview03(self):
        "Only contact & orga models are allowed as target"
        self.login()

        target = emitter = Invoice.objects.create(user=self.user, name='Invoice01',
                                                  expiration_date=date(year=2012, month=12, day=15),
                                                  status_id=1, number='INV0001',
                                                  currency_id=DEFAULT_CURRENCY_PK,
                                                 )
        name  = 'Opportunity01'
        phase = SalesPhase.objects.all()[0]
        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'user':                  self.user.pk,
                                          'name':                  name,
                                          'sales_phase':           phase.id,
                                          'expected_closing_date': '2010-9-20',
                                          'closing_date':          '2010-10-11',
                                          'target':                self._genericfield_format_entity(target),
                                          'emitter':               emitter.id,
                                          'first_action_date':     '2010-7-13',
                                          'currency':              DEFAULT_CURRENCY_PK,
                                         }
                                   )
        self.assertFormError(response, 'form', 'target', [_('This content type is not allowed.')])
        self.assertFormError(response, 'form', 'emitter',
                             [_('Select a valid choice. That choice is not one of the available choices.')]
                            )
        self.assertRaises(Opportunity.DoesNotExist, Opportunity.objects.get, name=name)

    def test_createview04(self):
        "LINK credentials error"
        self.login(is_superuser=False, allowed_apps=['opportunities'], creatable_models=[Opportunity])

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   | EntityCredentials.CHANGE | \
                                            EntityCredentials.DELETE | EntityCredentials.UNLINK, #no LINK
                                      set_type=SetCredentials.ESET_OWN
                                     )

        target, emitter = self._create_target_n_emitter()
        response = self.assertPOST200(self.ADD_URL, follow=True,
                                      data={'user':         self.user.pk,
                                            'name':         'My opportunity',
                                            'sales_phase':  SalesPhase.objects.all()[0].id,
                                            'closing_date': '2011-03-14',
                                            'target':       self._genericfield_format_entity(target),
                                            'emitter':      emitter.id,
                                            'currency':     DEFAULT_CURRENCY_PK,
                                           }
                                     )

        fmt1 = _(u'You are not allowed to link this entity: %s')
        fmt2 = _(u'Entity #%s (not viewable)')
        self.assertFormError(response, 'form', 'target',  [fmt1 % (fmt2 % target.id)])
        self.assertFormError(response, 'form', 'emitter', [fmt1 % (fmt2 % emitter.id)])

    def test_createview05(self):
        "Emitter not managed by Creme"
        self.login()

        target, emitter = self._create_target_n_emitter(managed=False)
        response = self.assertPOST200(self.ADD_URL, follow=True,
                                      data={'user':         self.user.pk,
                                            'name':         'My opportunity',
                                            'sales_phase':  SalesPhase.objects.all()[0].id,
                                            'closing_date': '2011-03-14',
                                            'target':       self._genericfield_format_entity(target),
                                            'emitter':      emitter.id,
                                            }
                                     )
        self.assertFormError(response, 'form', 'emitter',
                             [_('Select a valid choice. That choice is not one of the available choices.')]
                            )

    def test_add_to_orga01(self):
        self.login()

        target, emitter = self._create_target_n_emitter()
        url = self.ADDTO_URL % target.id
        self.assertGET200(url)

        salesphase = SalesPhase.objects.all()[0]
        name = 'Opportunity linked to %s' % target
        response = self.client.post(url, data={'user':         self.user.pk,
                                               'name':         name,
                                               'sales_phase':  salesphase.id,
                                               'closing_date': '2011-03-12',
                                               'target':       self._genericfield_format_entity(target),
                                               'emitter':      emitter.id,
                                               'currency':     DEFAULT_CURRENCY_PK,
                                              }
                                   )
        self.assertNoFormError(response, status=302)

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(salesphase, opportunity.sales_phase)

        self.assertRelationCount(1, target,  REL_OBJ_TARGETS,   opportunity)
        self.assertRelationCount(1, emitter, REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

        response = self.client.post(url, follow=True,
                                    data={'user':         self.user.pk,
                                          'name':         'Opportunity Two linked to %s' % target,
                                          'sales_phase':  salesphase.id,
                                          'closing_date': '2011-03-12',
                                          'target':       self._genericfield_format_entity(target),
                                          'emitter':      emitter.id,
                                          'currency':     DEFAULT_CURRENCY_PK,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertRelationCount(1, target, REL_SUB_PROSPECT, emitter)

    def test_add_to_orga02(self):
        self.login()

        target, emitter = self._create_target_n_emitter()
        url = '/opportunities/opportunity/add_to/%s/popup' % target.id
        self.assertGET200(url)

        salesphase = SalesPhase.objects.all()[0]
        name = 'Opportunity linked to %s' % target
        response = self.client.post(url, data={'user':         self.user.pk,
                                               'name':         name,
                                               'sales_phase':  salesphase.id,
                                               'closing_date': '2011-03-12',
                                               'target':       self._genericfield_format_entity(target),
                                               'emitter':      emitter.id,
                                               'currency':     DEFAULT_CURRENCY_PK,
                                              }
                                   )
        self.assertNoFormError(response)

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(salesphase, opportunity.sales_phase)

        self.assertRelationCount(1, target,  REL_OBJ_TARGETS,   opportunity)
        self.assertRelationCount(1, emitter, REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

    def test_add_to_orga03(self):
        "Try to add with wrong credentials (no link credentials)"
        self.login(is_superuser=False, allowed_apps=['opportunities'], creatable_models=[Opportunity])

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   | EntityCredentials.CHANGE | \
                                            EntityCredentials.DELETE | EntityCredentials.UNLINK, #no LINK
                                      set_type=SetCredentials.ESET_OWN
                                     )

        target = Organisation.objects.create(user=self.user, name='Target renegade')
        self.assertGET403(self.ADDTO_URL % target.id)

    def test_add_to_contact01(self):
        "Target is a Contact"
        self.login()

        target, emitter = self._create_target_n_emitter(contact=True)
        url = self.ADDTO_URL % target.id
        self.assertGET200(url)

        salesphase = SalesPhase.objects.all()[0]
        name = 'Opportunity linked to %s' % target
        response = self.client.post(url, data={'user':         self.user.pk,
                                               'name':         name,
                                               'sales_phase':  salesphase.id,
                                               'closing_date': '2011-03-12',
                                               'target':       self._genericfield_format_entity(target),
                                               'emitter':      emitter.id,
                                               'currency':     DEFAULT_CURRENCY_PK,
                                              }
                                   )
        self.assertNoFormError(response, status=302)

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(salesphase, opportunity.sales_phase)

        self.assertRelationCount(1, target,  REL_OBJ_TARGETS,   opportunity)
        self.assertRelationCount(1, emitter, REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

        response = self.client.post(url, follow=True,
                                    data={'user':         self.user.pk,
                                          'name':         'Opportunity 2 linked to %s' % target,
                                          'sales_phase':  salesphase.id,
                                          'closing_date': '2011-03-12',
                                          'target':       self._genericfield_format_entity(target),
                                          'emitter':      emitter.id,
                                          'currency':     DEFAULT_CURRENCY_PK,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertRelationCount(1, target, REL_SUB_PROSPECT, emitter)

    def test_add_to_contact02(self):
        "Popup version"
        self.login()

        target, emitter = self._create_target_n_emitter(contact=True)
        url = '/opportunities/opportunity/add_to/%s/popup' % target.id
        self.assertGET200(url)

        salesphase = SalesPhase.objects.all()[0]
        name = 'Opportunity linked to %s' % target
        response = self.client.post(url, data={'user':         self.user.pk,
                                               'name':         name,
                                               'sales_phase':  salesphase.id,
                                               'closing_date': '2011-03-12',
                                               'target':       self._genericfield_format_entity(target),
                                               'emitter':      emitter.id,
                                               'currency':     DEFAULT_CURRENCY_PK,
                                              }
                                   )
        self.assertNoFormError(response)

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(salesphase, opportunity.sales_phase)

        self.assertRelationCount(1, target,  REL_OBJ_TARGETS,   opportunity)
        self.assertRelationCount(1, emitter, REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

    def test_add_to_contact03(self):
        "User can not link to the Contact target"
        self.login(is_superuser=False, allowed_apps=['opportunities'], creatable_models=[Opportunity])

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   | EntityCredentials.CHANGE | \
                                            EntityCredentials.DELETE | EntityCredentials.UNLINK, #no LINK
                                      set_type=SetCredentials.ESET_OWN
                                     )

        target = Contact.objects.create(user=self.user, first_name='Target', last_name='Renegade')
        self.assertGET403(self.ADDTO_URL % target.id)

    def test_add_to_something01(self):
        "Target is not a Contact/Organisation"
        self.login()

        target  = CremeEntity.objects.create(user=self.user)
        emitter = Organisation.objects.create(user=self.user, name='My society')
        opportunity_count = Opportunity.objects.count()

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        url = self.ADDTO_URL % target.id
        self.assertGET200(url) #TODO: is it normal ??

        response = self.client.post(url, data={'user':         self.user.pk,
                                               'name':         'Opp #1',
                                               'sales_phase':  SalesPhase.objects.all()[0].id,
                                               'closing_date': '2011-03-12',
                                               'target':       self._genericfield_format_entity(target),
                                               'emitter':      emitter.id,
                                              }
                                   )
        self.assertFormError(response, 'form', 'target', [_(u'This content type is not allowed.')])
        self.assertEqual(opportunity_count, Opportunity.objects.count())#No new opportunity was created

    def test_editview(self):
        self.login()

        name = 'opportunity01'
        opportunity = self._create_opportunity_n_organisations(name)[0]
        url = '/opportunities/opportunity/edit/%s' % opportunity.id
        self.assertGET200(url)

        name = name.title()
        reference = '1256'
        phase = SalesPhase.objects.all()[1]
        currency = Currency.objects.create(name='Oolong', local_symbol='0', international_symbol='OOL')
        response = self.client.post(url, follow=True,
                                    data={'user':                  self.user.pk,
                                          'name':                  name,
                                          'reference':             reference,
                                          'sales_phase':           phase.id,
                                          'expected_closing_date': '2011-4-26',
                                          'closing_date':          '2011-5-15',
                                          'first_action_date':     '2011-5-1',
                                          'currency':              currency.id,
                                         }
                                   )
        self.assertNoFormError(response)

        opportunity = self.refresh(opportunity)
        self.assertEqual(name,                             opportunity.name)
        self.assertEqual(reference,                        opportunity.reference)
        self.assertEqual(phase,                            opportunity.sales_phase)
        self.assertEqual(currency,                         opportunity.currency)
        self.assertEqual(date(year=2011, month=4, day=26), opportunity.expected_closing_date)
        self.assertEqual(date(year=2011, month=5, day=15), opportunity.closing_date)
        self.assertEqual(date(year=2011, month=5, day=1),  opportunity.first_action_date)

    def test_listview(self):
        self.login()

        opp1 = self._create_opportunity_n_organisations('Opp1')[0]
        opp2 = self._create_opportunity_n_organisations('Opp2')[0]

        response = self.assertGET200('/opportunities/opportunities')

        with self.assertNoException():
            opps_page = response.context['entities']

        self.assertEqual(2, opps_page.paginator.count)
        self.assertEqual(set([opp1, opp2]), set(opps_page.object_list))

    def test_clone(self):
        self.login()

        opportunity, target, emitter = self._create_opportunity_n_organisations()
        cloned = opportunity.clone()

        self.assertEqual(opportunity.name,         cloned.name)
        self.assertEqual(opportunity.sales_phase,  cloned.sales_phase)
        self.assertEqual(opportunity.closing_date, cloned.closing_date)

        self.assertRelationCount(1, emitter, REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, emitter, REL_SUB_EMIT_ORGA, cloned)

        self.assertRelationCount(1, target, REL_OBJ_TARGETS, opportunity)
        self.assertRelationCount(1, target, REL_OBJ_TARGETS, cloned) #<== internal

    def _build_gendoc_url(self, opportunity, ct):
        return '/opportunities/opportunity/generate_new_doc/%s/%s' % (
                        opportunity.id, ct.id
                    )

    def test_generate_new_doc01(self):
        self.login()

        self.assertEqual(0, Quote.objects.count())

        opportunity, target, emitter = self._create_opportunity_n_organisations()
        url = self._build_gendoc_url(opportunity, ContentType.objects.get_for_model(Quote))

        self.assertGET404(url)
        self.assertPOST200(url, follow=True)

        quotes = Quote.objects.all()
        self.assertEqual(1, len(quotes))

        quote = quotes[0]
        self.assertLess((date.today() - quote.issuing_date).seconds, 10)
        self.assertEqual(1, quote.status_id)

        self.assertRelationCount(1, quote, REL_SUB_BILL_ISSUED,   emitter)
        self.assertRelationCount(1, quote, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, quote, REL_SUB_LINKED_QUOTE,  opportunity)
        self.assertRelationCount(1, quote, REL_SUB_CURRENT_DOC,   opportunity)

        self.assertRelationCount(1, target, REL_SUB_PROSPECT, emitter)

    def test_generate_new_doc02(self):
        self.login()

        opportunity, target, emitter = self._create_opportunity_n_organisations()
        url = self._build_gendoc_url(opportunity, ContentType.objects.get_for_model(Quote))

        self.client.post(url)
        quote1 = Quote.objects.all()[0]

        self.client.post(url)
        quotes = Quote.objects.exclude(pk=quote1.id)
        self.assertEqual(1, len(quotes))
        quote2 = quotes[0]

        self.assertRelationCount(1, quote2, REL_SUB_BILL_ISSUED,   emitter)
        self.assertRelationCount(1, quote2, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, quote2, REL_SUB_LINKED_QUOTE,  opportunity)
        self.assertRelationCount(1, quote2, REL_SUB_CURRENT_DOC,   opportunity)

        self.assertRelationCount(1, quote1, REL_SUB_BILL_ISSUED,   emitter)
        self.assertRelationCount(1, quote1, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, quote1, REL_SUB_LINKED_QUOTE,  opportunity)
        self.assertRelationCount(0, quote1, REL_SUB_CURRENT_DOC,   opportunity)

        self.assertRelationCount(1, target, REL_SUB_PROSPECT, emitter)

    #def test_opportunity_generate_new_doc03(self): #TODO test with credentials problems

    def test_generate_new_doc04(self):
        self.login()

        opportunity, target, emitter = self._create_opportunity_n_organisations()
        url = self._build_gendoc_url(opportunity, ContentType.objects.get_for_model(Invoice))

        self.client.post(url)
        invoice1 = Invoice.objects.all()[0]

        self.client.post(url)
        invoices = Invoice.objects.exclude(pk=invoice1.id)
        self.assertEqual(1, len(invoices))

        invoices2 = invoices[0]
        self.assertRelationCount(1, invoices2, REL_SUB_BILL_ISSUED,    emitter)
        self.assertRelationCount(1, invoices2, REL_SUB_BILL_RECEIVED,  target)
        self.assertRelationCount(1, invoices2, REL_SUB_LINKED_INVOICE, opportunity)

        self.assertRelationCount(1, invoice1, REL_SUB_BILL_ISSUED,    emitter)
        self.assertRelationCount(1, invoice1, REL_SUB_BILL_RECEIVED,  target)
        self.assertRelationCount(1, invoice1, REL_SUB_LINKED_INVOICE, opportunity)

        self.assertRelationCount(1, target, REL_SUB_CUSTOMER_SUPPLIER, emitter)

    def _build_setcurrentquote_url(self, opportunity, quote):
        return '/opportunities/opportunity/%s/linked/quote/%s/set_current/' % (
                    opportunity.id, quote.id
                )

    def test_current_quote_1(self):
        self.login()

        opportunity, target, emitter = self._create_opportunity_n_organisations()
        gendoc_url = self._build_gendoc_url(opportunity, ContentType.objects.get_for_model(Quote))

        self.client.post(gendoc_url)
        quote1 = Quote.objects.all()[0]

        self.client.post(gendoc_url)
        quote2 = Quote.objects.exclude(pk=quote1.id)[0]

        url = self._build_setcurrentquote_url(opportunity, quote1)
        self.assertGET404(url)
        self.assertPOST200(url, follow=True)

        self.assertRelationCount(1, quote2, REL_SUB_BILL_ISSUED,   emitter)
        self.assertRelationCount(1, quote2, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, quote2, REL_SUB_LINKED_QUOTE,  opportunity)
        self.assertRelationCount(0, quote2, REL_SUB_CURRENT_DOC,   opportunity)

        self.assertRelationCount(1, quote1, REL_SUB_BILL_ISSUED,   emitter)
        self.assertRelationCount(1, quote1, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, quote1, REL_SUB_LINKED_QUOTE,  opportunity)
        self.assertRelationCount(1, quote1, REL_SUB_CURRENT_DOC,   opportunity)

    def _set_quote_config(self, use_current_quote):
        sv = SettingValue.objects.get(key=opp_constants.SETTING_USE_CURRENT_QUOTE)
        sv.value = use_current_quote
        sv.save()

    def test_current_quote_2(self):
        "Refresh the estimated_sales when we change which quote is the current"
        self.login()

        opportunity = self._create_opportunity_n_organisations()[0]
        url = self._build_gendoc_url(opportunity, ContentType.objects.get_for_model(Quote))

        opportunity.estimated_sales = Decimal('1000')
        opportunity.save()

        create_sline = partial(ServiceLine.objects.create, user=self.user)

        self.client.post(url)
        quote1 = Quote.objects.all()[0]
        create_sline(related_document=quote1, on_the_fly_item='Stuff1', unit_price=Decimal("300"))

        self.client.post(url)
        quote2 = Quote.objects.exclude(pk=quote1.id)[0]
        create_sline(related_document=quote2, on_the_fly_item='Stuff1', unit_price=Decimal("500"))

        self._set_quote_config(True)
        url = self._build_setcurrentquote_url(opportunity, quote1)
        self.assertPOST200(url, follow=True)

        opportunity = self.refresh(opportunity)
        self.assertEqual(opportunity.estimated_sales, quote1.total_no_vat) # 300

        self.assertPOST200(self._build_setcurrentquote_url(opportunity, quote2), follow=True)
        opportunity = self.refresh(opportunity)
        self.assertEqual(opportunity.estimated_sales, quote2.total_no_vat) # 500

    def test_current_quote_3(self):
        self.login()

        opportunity = self._create_opportunity_n_organisations()[0]
        self._set_quote_config(False)

        estimated_sales = Decimal('69')
        opportunity.estimated_sales = estimated_sales
        opportunity.save()

        self.client.post(self._build_gendoc_url(opportunity, ContentType.objects.get_for_model(Quote)))
        quote1 = Quote.objects.all()[0]
        ServiceLine.objects.create(user=self.user, related_document=quote1,
                                   on_the_fly_item='Foobar', unit_price=Decimal("300")
                                  )

        self.assertPOST200(self._build_setcurrentquote_url(opportunity, quote1), follow=True)

        opportunity = self.refresh(opportunity)
        self.assertEqual(opportunity.estimated_sales, opportunity.get_total()) # 69
        self.assertEqual(opportunity.estimated_sales, estimated_sales) # 69

    def test_current_quote_4(self):
        self.login()
        self._set_quote_config(True)

        opportunity = self._create_opportunity_n_organisations()[0]
        self.client.post(self._build_gendoc_url(opportunity, ContentType.objects.get_for_model(Quote)))

        quote = Quote.objects.all()[0]
        self.assertEqual(self.refresh(opportunity).estimated_sales, quote.total_no_vat)
        self.assertPOST200(self._build_setcurrentquote_url(opportunity, quote), follow=True)

        ServiceLine.objects.create(user=self.user, related_document=quote,
                                   on_the_fly_item='Stuff', unit_price=Decimal("300"),
                                  )
        self.assertEqual(300, self.refresh(quote).total_no_vat)
        self.assertEqual(300, self.refresh(opportunity).estimated_sales)

    def test_get_weighted_sales(self):
        self.login()

        opportunity = self._create_opportunity_n_organisations()[0]
        funf = opportunity.function_fields.get('get_weighted_sales')
        self.assertIsNotNone(funf)

        self.assertIsNone(opportunity.estimated_sales)
        self.assertIsNone(opportunity.chance_to_win)
        self.assertEqual(0, opportunity.get_weighted_sales())
        self.assertEqual('0.0', funf(opportunity).for_html())

        opportunity.estimated_sales = 1000
        opportunity.chance_to_win   =  10
        self.assertEqual(100, opportunity.get_weighted_sales())
        self.assertEqual('100.0', funf(opportunity).for_html())

    def test_delete_currency(self):
        self.login()

        currency = Currency.objects.create(name=u'Berry', local_symbol=u'B', international_symbol=u'BRY')

        user = self.user
        create_orga = partial(Organisation.objects.create, user=user)
        opp = Opportunity.objects.create(user=user, name='Opp', currency=currency,
                                         sales_phase=SalesPhase.objects.all()[0],
                                         emitter=create_orga(name='My society'),
                                         target=create_orga(name='Target renegade'),
                                        )
        self.assertPOST404('/creme_config/creme_core/currency/delete', data={'id': currency.pk})
        self.assertTrue(Currency.objects.filter(pk=currency.pk).exists())

        opp = self.get_object_or_fail(Opportunity, pk=opp.pk)
        self.assertEqual(currency, opp.currency)

    def test_csv_import01(self):
        self.login()
        user = self.user

        count = Opportunity.objects.count()
        max_order = max(sp.order for sp in SalesPhase.objects.all())

        #Opportunity #1
        emitter1 = Organisation.objects.filter(properties__type=PROP_IS_MANAGED_BY_CREME)[0]
        target1  = Organisation.objects.create(user=user, name='Acme')
        sp1 = SalesPhase.objects.all()[0]

        #Opportunity #2
        target2_name = 'Black label society'
        sp2_name = 'IAmNotSupposedToAlreadyExist'
        self.assertFalse(SalesPhase.objects.filter(name=sp2_name))

        #Opportunity #3
        target3 = Contact.objects.create(user=user, first_name='Mike', last_name='Danton')

        #Opportunity #4
        target4_last_name = 'Renegade'

        #Opportunity #5
        sp5 = SalesPhase.objects.all()[1]

        lines = [('Opp01', sp1.name, '1000', '2000', target1.name, ''),
                 ('Opp02', sp2_name, '100',  '200',  target2_name, ''),
                 ('Opp03', sp1.name, '100',  '200',  '',           target3.last_name),
                 ('Opp04', sp1.name, '100',  '200',  '',           target4_last_name),
                 ('Opp05', '',       '100',  '200',  target1.name, ''),
                 #TODO emitter by name
                ]

        doc = self._build_doc(lines)
        url = self._build_csvimport_url(Opportunity)
        self.assertGET200(url)

        response = self.client.post(url, data={'csv_step':     1,
                                               'csv_document': doc.id,
                                               #csv_has_header

                                               'user':    user.id,
                                               'emitter': emitter1.id,

                                               'name_colselect':            1,
                                               'estimated_sales_colselect': 3,
                                               'made_sales_colselect':      4,

                                               'sales_phase_colselect': 2,
                                               'sales_phase_create':    True,
                                               'sales_phase_defval':    sp5.pk,

                                               'target_orga_colselect':    5,
                                               'target_orga_create':       True,
                                               'target_contact_colselect': 6,
                                               'target_contact_create':    True,

                                               'currency_colselect': 0,
                                               'currency_defval':    DEFAULT_CURRENCY_PK,

                                               'reference_colselect':              0,
                                               'chance_to_win_colselect':          0,
                                               'expected_closing_date_colselect':  0,
                                               'closing_date_colselect':           0,
                                               'origin_colselect':                 0,
                                               'description_colselect':            0,
                                               'first_action_date_colselect':      0,

                                                #'property_types',
                                                #'fixed_relations',
                                                #'dyn_relations',
                                              }
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']

        self.assertFalse(list(form.import_errors))
        self.assertEqual(len(lines), form.imported_objects_count)
        self.assertEqual(len(lines), form.lines_count)

        self.assertEqual(count + len(lines), Opportunity.objects.count())

        opp1 = self.get_object_or_fail(Opportunity, name='Opp01')
        self.assertEqual(user,      opp1.user)
        self.assertEqual(1000,      opp1.estimated_sales)
        self.assertEqual(2000,      opp1.made_sales)
        self.assertEqual(sp1,       opp1.sales_phase)
        self.assertFalse(opp1.reference)
        self.assertIsNone(opp1.origin)
        self.assertEqual(emitter1, opp1.get_source())
        self.assertEqual(target1,  opp1.get_target())

        sp2 = self.get_object_or_fail(SalesPhase, name=sp2_name)
        self.assertEqual(max_order + 1, sp2.order)

        opp2 = self.get_object_or_fail(Opportunity, name='Opp02')
        self.assertEqual(user,      opp2.user)
        self.assertEqual(100,       opp2.estimated_sales)
        self.assertEqual(200,       opp2.made_sales)
        self.assertEqual(sp2, opp2.sales_phase)
        self.assertEqual(self.get_object_or_fail(Organisation, name=target2_name),
                         opp2.get_target()
                        )

        opp3 = self.get_object_or_fail(Opportunity, name='Opp03')
        self.assertEqual(target3, opp3.get_target())

        opp4 = self.get_object_or_fail(Opportunity, name='Opp04')
        self.assertEqual(self.get_object_or_fail(Contact, last_name=target4_last_name),
                         opp4.get_target()
                        )

        opp5 = self.get_object_or_fail(Opportunity, name='Opp05')
        self.assertEqual(sp5, opp5.sales_phase)

    def test_csv_import02(self):
        "SalesPhase creation forbidden by the user"
        self.login()

        count = Opportunity.objects.count()

        emitter = Organisation.objects.filter(properties__type=PROP_IS_MANAGED_BY_CREME)[0]
        target1 = Organisation.objects.create(user=self.user, name='Acme')

        sp1_name = 'IAmNotSupposedToAlreadyExist'
        self.assertFalse(SalesPhase.objects.filter(name=sp1_name))

        lines = [('Opp01', sp1_name, '1000', '2000', target1.name, '')]
        doc = self._build_doc(lines)
        response = self.client.post(self._build_csvimport_url(Opportunity),
                                    data={'csv_step':     1,
                                          'csv_document': doc.id,
                                          #csv_has_header

                                          'user':    self.user.id,
                                          'emitter': emitter.id,

                                          'name_colselect':            1,
                                          'estimated_sales_colselect': 3,
                                          'made_sales_colselect':      4,

                                          'sales_phase_colselect': 2,
                                          'sales_phase_create':    '', #<=======
                                          #'sales_phase_defval':   [...], #<=======

                                          'target_orga_colselect':    5,
                                          'target_orga_create':       True,
                                          'target_contact_colselect': 6,
                                          'target_contact_create':    True,

                                          'currency_colselect': 0,
                                          'currency_defval':    DEFAULT_CURRENCY_PK,

                                          'reference_colselect':              0,
                                          'chance_to_win_colselect':          0,
                                          'expected_closing_date_colselect':  0,
                                          'closing_date_colselect':           0,
                                          'origin_colselect':                 0,
                                          'description_colselect':            0,
                                          'first_action_date_colselect':      0,

                                           #'property_types',
                                           #'fixed_relations',
                                           #'dyn_relations',
                                        }
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(2, len(form.import_errors)) #2 errors: retrieving of SalesPhase failed, creation of Opportunity failed
        self.assertEqual(0, form.imported_objects_count)
        self.assertEqual(len(lines), form.lines_count)

        self.assertEqual(count, Opportunity.objects.count())
        self.assertFalse(SalesPhase.objects.filter(name=sp1_name).count())

    def test_csv_import03(self):
        "SalesPhase is required"
        self.login()

        emitter = Organisation.objects.filter(properties__type=PROP_IS_MANAGED_BY_CREME)[0]
        target  = Organisation.objects.create(user=self.user, name='Acme')

        lines = [('Opp01', '1000', '2000', target.name)]
        doc = self._build_doc(lines)
        response = self.client.post(self._build_csvimport_url(Opportunity),
                                    data={'csv_step':     1,
                                          'csv_document': doc.id,
                                          #csv_has_header

                                          'user':    self.user.id,
                                          'emitter': emitter.id,

                                          'name_colselect':            1,
                                          'estimated_sales_colselect': 2,
                                          'made_sales_colselect':      3,

                                          'sales_phase_colselect': 0,  #<=======
                                          'sales_phase_create':    '',
                                          #'sales_phase_defval':   [...],

                                          'target_orga_colselect':    4,
                                          'target_orga_create':       '',
                                          'target_contact_colselect': 0,
                                          'target_contact_create':    '',

                                          'currency_colselect': 0,
                                          'currency_defval':    DEFAULT_CURRENCY_PK,

                                          'reference_colselect':              0,
                                          'chance_to_win_colselect':          0,
                                          'expected_closing_date_colselect':  0,
                                          'closing_date_colselect':           0,
                                          'origin_colselect':                 0,
                                          'description_colselect':            0,
                                          'first_action_date_colselect':      0,

                                           #'property_types',
                                           #'fixed_relations',
                                           #'dyn_relations',
                                        }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'sales_phase', [_('This field is required.')])

    def test_csv_import04(self): #creation of Organisation/Contact is not wanted
        self.login()

        count = Opportunity.objects.count()
        emitter = Organisation.objects.filter(properties__type=PROP_IS_MANAGED_BY_CREME)[0]

        orga_name = 'NERV'
        contact_name = 'Ikari'
        lines = [('Opp01', 'SP name', '1000', '2000', orga_name, ''),
                 ('Opp02', 'SP name', '1000', '2000', '',        contact_name),
                ]
        doc = self._build_doc(lines)
        response = self.client.post(self._build_csvimport_url(Opportunity),
                                    data={'csv_step':     1,
                                          'csv_document': doc.id,
                                          #csv_has_header

                                          'user':    self.user.id,
                                          'emitter': emitter.id,

                                          'name_colselect':            1,
                                          'estimated_sales_colselect': 3,
                                          'made_sales_colselect':      4,

                                          'sales_phase_colselect': 2,
                                          'sales_phase_create':    True,

                                          'target_orga_colselect':    5,
                                          'target_orga_create':       '', #<===
                                          'target_contact_colselect': 6,
                                          'target_contact_create':    '', #<===

                                          'currency_colselect': 0,
                                          'currency_defval':    DEFAULT_CURRENCY_PK,

                                          'reference_colselect':              0,
                                          'chance_to_win_colselect':          0,
                                          'expected_closing_date_colselect':  0,
                                          'closing_date_colselect':           0,
                                          'origin_colselect':                 0,
                                          'description_colselect':            0,
                                          'first_action_date_colselect':      0,

                                          #'property_types',
                                          #'fixed_relations',
                                          #'dyn_relations',
                                         }
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']

        errors = list(form.import_errors)
        self.assertEqual(4, len(errors)) #4 errors: retrieving of Organisation/Contact failed, creation of Opportunities failed
        self.assertIn(_('Organisation'), errors[0][1])
        self.assertIn(_('Contact'),      errors[2][1])

        self.assertEqual(0, form.imported_objects_count)

        self.assertEqual(count, Opportunity.objects.count())
        self.assertFalse(Organisation.objects.filter(name=orga_name))
        self.assertFalse(Contact.objects.filter(last_name=contact_name))


class SalesPhaseTestCase(CremeTestCase):
    DOWN_URL   = '/creme_config/opportunities/sales_phase/down/%s'
    UP_URL     = '/creme_config/opportunities/sales_phase/up/%s'
    DELETE_URL = '/creme_config/opportunities/sales_phase/delete'

    @classmethod
    def setUpClass(cls):
        SalesPhase.objects.all().delete()
        cls.populate('creme_core', 'creme_config')

    def test_create_n_order(self):
        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming', order=2)
        sp2 = create_phase(name='Abandoned',   order=1)

        self.assertEqual([sp2, sp1], list(SalesPhase.objects.all()))

    def test_incr_order01(self):
        self.login()

        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming', order=1)
        sp2 = create_phase(name='Abandoned',   order=2)

        self.assertGET200('/creme_config/opportunities/portal/')

        response = self.assertGET200('/creme_config/opportunities/sales_phase/portal/')
        self.assertContains(response, sp1.name)
        self.assertContains(response, sp2.name)

        url = self.DOWN_URL % sp1.id
        self.assertGET404(url)
        self.assertPOST200(url)

        self.assertEqual(2, self.refresh(sp1).order)
        self.assertEqual(1, self.refresh(sp2).order)

    def test_incr_order02(self):
        self.login()

        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming', order=1)
        sp2 = create_phase(name='Abandoned',   order=2)
        sp3 = create_phase(name='Won',         order=3)
        sp4 = create_phase(name='Lost',        order=4)

        self.assertPOST200(self.DOWN_URL % sp2.id)

        self.assertEqual(1, self.refresh(sp1).order)
        self.assertEqual(3, self.refresh(sp2).order)
        self.assertEqual(2, self.refresh(sp3).order)
        self.assertEqual(4, self.refresh(sp4).order)

    def test_incr_order03(self):
        "Errrors"
        self.login()

        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming', order=1)
        sp2 = create_phase(name='Abandoned',   order=2)

        url = self.DOWN_URL
        self.assertPOST404(url % sp2.id)
        self.assertPOST404(url % (sp2.id + sp1.id)) #odd pk

    def test_decr_order01(self):
        self.login()

        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming', order=1)
        sp2 = create_phase(name='Abandoned',   order=2)
        sp3 = create_phase(name='Won',         order=3)
        sp4 = create_phase(name='Lost',        order=4)

        self.assertPOST200(self.UP_URL % sp3.id)

        self.assertEqual(1, self.refresh(sp1).order)
        self.assertEqual(3, self.refresh(sp2).order)
        self.assertEqual(2, self.refresh(sp3).order)
        self.assertEqual(4, self.refresh(sp4).order)

    def test_decr_order02(self):
        "Error: can move up the first one"
        self.login()

        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming', order=1)
        create_phase(name='Abandoned', order=2)

        self.assertPOST404(self.UP_URL % sp1.id)

    def test_delete01(self):
        self.login()

        sp = SalesPhase.objects.create(name='Forthcoming', order=1)
        self.assertPOST200(self.DELETE_URL, data={'id': sp.pk})
        self.assertFalse(SalesPhase.objects.filter(pk=sp.pk).exists())

    def test_delete02(self):
        self.login()

        sp = SalesPhase.objects.create(name='Forthcoming', order=1)

        create_orga = Organisation.objects.create
        user = self.user
        opp = Opportunity.objects.create(user=user, name='Opp', sales_phase=sp,
                                         emitter=create_orga(user=user, name='My society'),
                                         target=create_orga(user=user,  name='Target renegade'),
                                        )
        self.assertPOST404(self.DELETE_URL, data={'id': sp.pk})
        self.assertTrue(SalesPhase.objects.filter(pk=sp.pk).exists())

        opp = self.get_object_or_fail(Opportunity, pk=opp.pk)
        self.assertEqual(sp, opp.sales_phase)


class OriginTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def setUp(self):
        self.login()

    def test_config(self):
        create_origin = Origin.objects.create
        origin1 = create_origin(name='Web site')
        origin2 = create_origin(name='Mouth')

        response = self.assertGET200('/creme_config/opportunities/origin/portal/')
        self.assertContains(response, origin1.name)
        self.assertContains(response, origin2.name)

        self.assertPOST404('/creme_config/opportunities/origin/down/%s' % origin1.id)

    def test_delete(self):
        "Set to null"
        origin = Origin.objects.create(name='Web site')

        user = self.user
        create_orga = partial(Organisation.objects.create, user=user)
        opp = Opportunity.objects.create(user=user, name='Opp', origin=origin,
                                         sales_phase=SalesPhase.objects.create(name='Forthcoming', order=1),
                                         emitter=create_orga(name='My society'),
                                         target=create_orga(name='Target renegade'),
                                        )

        self.assertPOST200('/creme_config/opportunities/origin/delete', data={'id': origin.pk})
        self.assertFalse(Origin.objects.filter(pk=origin.pk).exists())

        opp = self.get_object_or_fail(Opportunity, pk=opp.pk)
        self.assertIsNone(opp.origin)
