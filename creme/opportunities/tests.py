# -*- coding: utf-8 -*-

try:
    from decimal import Decimal
    from datetime import date

    from django.utils.translation import ugettext as _
    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import RelationType, Relation, CremeProperty, SetCredentials, Currency
    from creme_core.constants import PROP_IS_MANAGED_BY_CREME, DEFAULT_CURRENCY_PK
    from creme_core.models.entity import CremeEntity
    from creme_core.tests.base import CremeTestCase

    from creme_config.models import SettingKey, SettingValue

    from persons.models import Organisation, Contact
    from persons.constants import REL_SUB_PROSPECT, REL_SUB_CUSTOMER_SUPPLIER

    from products.models import Product, Service

    from billing.models import Quote, SalesOrder, Invoice, Vat, ServiceLine
    from billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED

    from opportunities.models import *
    from opportunities.constants import *
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class OpportunitiesTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'documents', 'persons',
                     'commercial', 'billing', 'activities', 'opportunities'
                    )

    def _genericfield_format_entity(self, entity):
        return '{"ctype":"%s", "entity":"%s"}' % (entity.entity_type_id, entity.id)

    def _create_target_n_emitter(self, managed=True):
        user = self.user
        create_orga = Organisation.objects.create
        target  = create_orga(user=user, name='Target renegade')
        emitter = create_orga(user=user, name='My society')

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

        self.assertNotIn(REL_SUB_TARGETS, relation_types)
        self.get_relationtype_or_fail(REL_SUB_TARGETS, [Opportunity], [Contact, Organisation])

        self.assertNotIn(REL_SUB_EMIT_ORGA, relation_types)
        self.get_relationtype_or_fail(REL_OBJ_EMIT_ORGA, [Opportunity], [Organisation])

        self.assertIn(REL_OBJ_LINKED_PRODUCT, relation_types)
        self.assertNotIn(REL_SUB_LINKED_PRODUCT, relation_types)
        self.get_relationtype_or_fail(REL_OBJ_LINKED_PRODUCT, [Opportunity], [Product])

        self.assertIn(REL_OBJ_LINKED_SERVICE, relation_types)
        self.assertNotIn(REL_SUB_LINKED_SERVICE, relation_types)
        self.get_relationtype_or_fail(REL_OBJ_LINKED_SERVICE, [Opportunity], [Service])

        self.assertIn(REL_OBJ_LINKED_CONTACT, relation_types)
        self.assertNotIn(REL_SUB_LINKED_CONTACT, relation_types)
        self.get_relationtype_or_fail(REL_OBJ_LINKED_CONTACT, [Opportunity], [Contact])

        self.assertIn(REL_OBJ_LINKED_SALESORDER, relation_types)
        self.assertNotIn(REL_SUB_LINKED_SALESORDER, relation_types)
        self.get_relationtype_or_fail(REL_OBJ_LINKED_SALESORDER, [Opportunity], [SalesOrder])

        self.assertIn(REL_OBJ_LINKED_INVOICE, relation_types)
        self.assertNotIn(REL_SUB_LINKED_INVOICE, relation_types)
        self.get_relationtype_or_fail(REL_OBJ_LINKED_INVOICE, [Opportunity], [Invoice])

        self.assertIn(REL_OBJ_LINKED_QUOTE, relation_types)
        self.assertNotIn(REL_SUB_LINKED_QUOTE, relation_types)
        self.get_relationtype_or_fail(REL_OBJ_LINKED_QUOTE, [Opportunity], [Quote])

        self.assertIn(REL_OBJ_RESPONSIBLE, relation_types)
        self.assertNotIn(REL_SUB_RESPONSIBLE, relation_types)
        self.get_relationtype_or_fail(REL_OBJ_RESPONSIBLE, [Opportunity], [Contact])

        self.get_relationtype_or_fail(REL_OBJ_CURRENT_DOC, [Opportunity], [Invoice, Quote, SalesOrder])

        self.assertTrue(SalesPhase.objects.exists())
        self.assertTrue(Origin.objects.exists())

        keys = SettingKey.objects.filter(pk=SETTING_USE_CURRENT_QUOTE)
        self.assertEqual(1, len(keys))
        self.assertEqual(1, SettingValue.objects.filter(key=keys[0]).count())

    def test_portal(self):
        self.login()
        self.assertEqual(self.client.get('/opportunities/').status_code, 200)

    def test_createview01(self):
        self.login()

        url = '/opportunities/opportunity/add'
        self.assertEqual(200, self.client.post(url).status_code)

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
        self.assertEqual(200, response.status_code)

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
        response = self.client.post('/opportunities/opportunity/add', follow=True,
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
        self.assertEqual(200, response.status_code)

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

    def test_createview03(self):#Only contact & orga models are allowed
        self.login()

        response = self.client.post('/opportunities/opportunity/add')
        self.assertEqual(200, response.status_code)


        target, emitter = self._create_target_n_emitter()
        name  = 'Opportunity01'
        phase = SalesPhase.objects.all()[0]
        response = self.client.post('/opportunities/opportunity/add', follow=True,
                                    data={'user':                  self.user.pk,
                                          'name':                  name,
                                          'sales_phase':           phase.id,
                                          'expected_closing_date': '2010-9-20',
                                          'closing_date':          '2010-10-11',
                                          'target':                self._genericfield_format_entity(target),
                                          'emitter':               emitter.id,
                                          'first_action_date':     '2010-7-13',
                                         }
                                   )
        self.assertRaises(Opportunity.DoesNotExist, Opportunity.objects.get, name=name)

    def test_createview04(self): #link creds error
        self.login(is_superuser=False, allowed_apps=['opportunities'], creatable_models=[Opportunity])

        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_VIEW   | SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | SetCredentials.CRED_UNLINK, #no CRED_LINK
                                      set_type=SetCredentials.ESET_OWN
                                     )

        target, emitter = self._create_target_n_emitter()
        response = self.client.post('/opportunities/opportunity/add', follow=True,
                                    data={'user':         self.user.pk,
                                          'name':         'My opportunity',
                                          'sales_phase':  SalesPhase.objects.all()[0].id,
                                          'closing_date': '2011-03-14',
                                          'target':       self._genericfield_format_entity(target),
                                          'emitter':      emitter.id,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'target',
                             [_(u'You are not allowed to link this entity: %s') % (_(u'Entity #%s (not viewable)') % target.id)]
                            )
        self.assertFormError(response, 'form', 'emitter',
                             [_(u'You are not allowed to link this entity: %s') % (_(u'Entity #%s (not viewable)') % emitter.id)]
                            )

    def test_createview05(self): #emitter not managed by Creme
        self.login()

        target, emitter = self._create_target_n_emitter(managed=False)
        response = self.client.post('/opportunities/opportunity/add', follow=True,
                                    data={'user':         self.user.pk,
                                          'name':         'My opportunity',
                                          'sales_phase':  SalesPhase.objects.all()[0].id,
                                          'closing_date': '2011-03-14',
                                          'target':       self._genericfield_format_entity(target),
                                          'emitter':      emitter.id,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'emitter',
                             [_('Select a valid choice. That choice is not one of the available choices.')]
                            )

    def test_add_to_orga01(self):
        self.login()

        target, emitter = self._create_target_n_emitter()
        url = '/opportunities/opportunity/add_to/%s' % target.id
        self.assertEqual(200, self.client.get(url).status_code)

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
        self.assertEqual(302, response.status_code)

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(salesphase, opportunity.sales_phase)

        self.assertRelationCount(1, target,  REL_OBJ_TARGETS,   opportunity)
        self.assertRelationCount(1, emitter, REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

        name = 'Opportunity Two linked to %s' % target
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
        self.assertEqual(302, response.status_code)
        self.assertRelationCount(1, target, REL_SUB_PROSPECT, emitter)

    def test_add_to_orga02(self):
        self.login()

        target, emitter = self._create_target_n_emitter()
        url = '/opportunities/opportunity/add_to/%s/popup' % target.id
        self.assertEqual(200, self.client.get(url).status_code)

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
        self.assertEqual(200, response.status_code)

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(salesphase, opportunity.sales_phase)

        self.assertRelationCount(1, target,  REL_OBJ_TARGETS,   opportunity)
        self.assertRelationCount(1, emitter, REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

    def test_add_to_orga03(self): #with bad creds
        self.login(is_superuser=False, allowed_apps=['opportunities'], creatable_models=[Opportunity])

        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_VIEW   | SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | SetCredentials.CRED_UNLINK, #no CRED_LINK
                                      set_type=SetCredentials.ESET_OWN
                                     )

        target = Organisation.objects.create(user=self.user, name='Target renegade')
        self.assertEqual(403, self.client.get('/opportunities/opportunity/add_to/%s' % target.id).status_code)

    def test_add_to_contact01(self):
        self.login()

        target, emitter = self._create_target_n_emitter()
        url = '/opportunities/opportunity/add_to/%s' % target.id
        self.assertEqual(200, self.client.get(url).status_code)

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
        self.assertEqual(302, response.status_code)

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(salesphase, opportunity.sales_phase)

        self.assertRelationCount(1, target,  REL_OBJ_TARGETS,   opportunity)
        self.assertRelationCount(1, emitter, REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

        name = 'Opportunity 2 linked to %s' % target
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
        self.assertEqual(302, response.status_code)
        self.assertRelationCount(1, target, REL_SUB_PROSPECT, emitter)

    def test_add_to_contact02(self):
        self.login()

        target, emitter = self._create_target_n_emitter()
        url = '/opportunities/opportunity/add_to/%s/popup' % target.id
        self.assertEqual(200, self.client.get(url).status_code)

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
        self.assertEqual(200, response.status_code)

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(salesphase, opportunity.sales_phase)

        self.assertRelationCount(1, target,  REL_OBJ_TARGETS,   opportunity)
        self.assertRelationCount(1, emitter, REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

    def test_add_to_contact03(self): #with bad creds
        self.login(is_superuser=False, allowed_apps=['opportunities'], creatable_models=[Opportunity])

        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_VIEW   | SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | SetCredentials.CRED_UNLINK, #no CRED_LINK
                                      set_type=SetCredentials.ESET_OWN
                                     )

        target = Contact.objects.create(user=self.user, first_name='Target', last_name='renegade')
        self.assertEqual(403, self.client.get('/opportunities/opportunity/add_to/%s' % target.id).status_code)

    def test_add_to_something01(self): #Something different than a Contact or an Organisation
        self.login()

        target  = CremeEntity.objects.create(user=self.user)
        emitter = Organisation.objects.create(user=self.user, name='My society')
        opportunity_count = Opportunity.objects.count()

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        url = '/opportunities/opportunity/add_to/%s' % target.id
        self.assertEqual(200, self.client.get(url).status_code)

        name = 'Opportunity linked to %s' % target
        response = self.client.post(url, data={'user':         self.user.pk,
                                               'name':         name,
                                               'sales_phase':  SalesPhase.objects.all()[0].id,
                                               'closing_date': '2011-03-12',
                                               'target':       self._genericfield_format_entity(target),
                                               'emitter':      emitter.id,
                                              }
                                   )

        self.assertEqual(opportunity_count, Opportunity.objects.count())#No new opportunity was created
        self.assertFormError(response, 'form', 'target', [_(u'This content type is not allowed.')])

    def test_editview(self):
        self.login()

        name = 'opportunity01'
        opportunity = self._create_opportunity_n_organisations(name)[0]
        url = '/opportunities/opportunity/edit/%s' % opportunity.id
        self.assertEqual(200, self.client.post(url).status_code)

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
        self.assertEqual(200, response.status_code)

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

        response = self.client.get('/opportunities/opportunities')
        self.assertEqual(200, response.status_code)

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
        self.assertEqual(200, self.client.post(url, follow=True).status_code)

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
        ct = ContentType.objects.get_for_model(Quote)
        gendoc_url = self._build_gendoc_url(opportunity, ContentType.objects.get_for_model(Quote))

        self.client.post(gendoc_url)
        quote1 = Quote.objects.all()[0]

        self.client.post(gendoc_url)
        quote2 = Quote.objects.exclude(pk=quote1.id)[0]

        url = self._build_setcurrentquote_url(opportunity, quote1)
        self.assertGET404(url)
        self.assertEqual(200, self.client.post(url, follow=True).status_code)

        self.assertRelationCount(1, quote2, REL_SUB_BILL_ISSUED,   emitter)
        self.assertRelationCount(1, quote2, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, quote2, REL_SUB_LINKED_QUOTE,  opportunity)
        self.assertRelationCount(0, quote2, REL_SUB_CURRENT_DOC,   opportunity)

        self.assertRelationCount(1, quote1, REL_SUB_BILL_ISSUED,   emitter)
        self.assertRelationCount(1, quote1, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, quote1, REL_SUB_LINKED_QUOTE,  opportunity)
        self.assertRelationCount(1, quote1, REL_SUB_CURRENT_DOC,   opportunity)

    def _set_quote_config(self, use_current_quote):
        sv = SettingValue.objects.get(key=SETTING_USE_CURRENT_QUOTE)
        sv.value = use_current_quote
        sv.save()

    def test_current_quote_2(self): #refresh the estimated_sales when we change which quote is the current
        self.login()

        opportunity = self._create_opportunity_n_organisations()[0]
        url = self._build_gendoc_url(opportunity, ContentType.objects.get_for_model(Quote))

        opportunity.estimated_sales = Decimal('1000')
        opportunity.save()

        self.client.post(url)
        quote1 = Quote.objects.all()[0]
        sl1 = ServiceLine.objects.create(user=self.user, related_document=quote1, on_the_fly_item='Stuff1', unit_price=Decimal("300"))

        self.client.post(url)
        quote2 = Quote.objects.exclude(pk=quote1.id)[0]
        sl2 = ServiceLine.objects.create(user=self.user, related_document=quote2, on_the_fly_item='Stuff1', unit_price=Decimal("500"))

        self._set_quote_config(True)
        url = self._build_setcurrentquote_url(opportunity, quote1)
        self.assertEqual(200, self.client.post(url, follow=True).status_code)

        opportunity = self.refresh(opportunity)
        self.assertEqual(opportunity.estimated_sales, quote1.total_no_vat) # 300

        url = self._build_setcurrentquote_url(opportunity, quote2)
        self.assertEqual(200, self.client.post(url, follow=True).status_code)

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
        sl1 = ServiceLine.objects.create(user=self.user, related_document=quote1,
                                         on_the_fly_item='Foobar', unit_price=Decimal("300")
                                        )

        url = self._build_setcurrentquote_url(opportunity, quote1)
        self.assertEqual(200, self.client.post(url, follow=True).status_code)

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
        self.assertEqual(200, self.client.post(self._build_setcurrentquote_url(opportunity, quote), follow=True).status_code)

        ServiceLine.objects.create(user=self.user, related_document=quote, on_the_fly_item='Stuff', unit_price=Decimal("300"))
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

        create_orga = Organisation.objects.create
        user = self.user
        opp = Opportunity.objects.create(user=user, name='Opp', currency=currency,
                                         sales_phase=SalesPhase.objects.all()[0],
                                         emitter=create_orga(user=user, name='My society'),
                                         target=create_orga(user=user,  name='Target renegade'),
                                        )

        response = self.client.post('/creme_config/creme_core/currency/delete', data={'id': currency.pk})
        self.assertEqual(404, response.status_code)
        self.assertTrue(Currency.objects.filter(pk=currency.pk).exists())

        opp = self.get_object_or_fail(Opportunity, pk=opp.pk)
        self.assertEqual(currency, opp.currency)


class SalesPhaseTestCase(CremeTestCase):
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

        self.assertEqual(200, self.client.get('/creme_config/opportunities/portal/').status_code)

        response = self.client.get('/creme_config/opportunities/sales_phase/portal/')
        self.assertEqual(200, response.status_code)
        self.assertContains(response, sp1.name)
        self.assertContains(response, sp2.name)

        url = '/creme_config/opportunities/sales_phase/down/%s' % sp1.id
        self.assertGET404(url)
        self.assertEqual(200, self.client.post(url).status_code)

        self.assertEqual(2, self.refresh(sp1).order)
        self.assertEqual(1, self.refresh(sp2).order)

    def test_incr_order02(self):
        self.login()

        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming', order=1)
        sp2 = create_phase(name='Abandoned',   order=2)
        sp3 = create_phase(name='Won',         order=3)
        sp4 = create_phase(name='Lost',        order=4)

        self.assertEqual(200, self.client.post('/creme_config/opportunities/sales_phase/down/%s' % sp2.id).status_code)

        self.assertEqual(1, self.refresh(sp1).order)
        self.assertEqual(3, self.refresh(sp2).order)
        self.assertEqual(2, self.refresh(sp3).order)
        self.assertEqual(4, self.refresh(sp4).order)

    def test_incr_order03(self): #errrors
        self.login()

        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming', order=1)
        sp2 = create_phase(name='Abandoned',   order=2)

        url = '/creme_config/opportunities/sales_phase/down/%s'
        self.assertPOST404(url % sp2.id)
        self.assertPOST404(url % (sp2.id + sp1.id)) #odd pk

    def test_decr_order01(self):
        self.login()

        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming', order=1)
        sp2 = create_phase(name='Abandoned',   order=2)
        sp3 = create_phase(name='Won',         order=3)
        sp4 = create_phase(name='Lost',        order=4)

        self.assertEqual(200, self.client.post('/creme_config/opportunities/sales_phase/up/%s' % sp3.id).status_code)

        self.assertEqual(1, self.refresh(sp1).order)
        self.assertEqual(3, self.refresh(sp2).order)
        self.assertEqual(2, self.refresh(sp3).order)
        self.assertEqual(4, self.refresh(sp4).order)

    def test_decr_order02(self): #error
        self.login()

        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming', order=1)
        sp2 = create_phase(name='Abandoned',   order=2)

        self.assertPOST404('/creme_config/opportunities/sales_phase/up/%s' % sp1.id)

    def test_delete01(self):
        self.login()

        sp = SalesPhase.objects.create(name='Forthcoming', order=1)
        response = self.client.post('/creme_config/opportunities/sales_phase/delete', data={'id': sp.pk})
        self.assertEqual(200, response.status_code)
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

        response = self.client.post('/creme_config/opportunities/sales_phase/delete', data={'id': sp.pk})
        self.assertEqual(404, response.status_code)
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

        response = self.client.get('/creme_config/opportunities/origin/portal/')
        self.assertEqual(200, response.status_code)
        self.assertContains(response, origin1.name)
        self.assertContains(response, origin2.name)

        self.assertPOST404('/creme_config/opportunities/origin/down/%s' % origin1.id)

    def test_delete(self): #set to null
        origin = Origin.objects.create(name='Web site')

        create_orga = Organisation.objects.create
        user = self.user
        opp = Opportunity.objects.create(user=self.user, name='Opp', origin=origin,
                                         sales_phase=SalesPhase.objects.create(name='Forthcoming', order=1),
                                         emitter=create_orga(user=user, name='My society'),
                                         target=create_orga(user=user,  name='Target renegade'),
                                        )

        response = self.client.post('/creme_config/opportunities/origin/delete', data={'id': origin.pk})
        self.assertEqual(200, response.status_code)
        self.assertFalse(Origin.objects.filter(pk=origin.pk).exists())

        opp = self.get_object_or_fail(Opportunity, pk=opp.pk)
        self.assertIsNone(opp.origin)
