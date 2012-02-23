# -*- coding: utf-8 -*-

try:
    from decimal import Decimal
    from datetime import date

    from django.utils.translation import ugettext as _
    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import RelationType, Relation, CremeProperty, SetCredentials
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

    def genericfield_format_entity(self, entity):
        return '{"ctype":"%s", "entity":"%s"}' % (entity.entity_type_id, entity.id)

    def test_populate(self): #test get_compatible_ones() too
        ct = ContentType.objects.get_for_model(Opportunity)
        relation_types = dict((rtype.id, rtype) for rtype in RelationType.get_compatible_ones(ct))

        self.assertNotIn(REL_SUB_TARGETS, relation_types)
        self.get_relationtype_or_fail(REL_SUB_TARGETS, [Opportunity], [Contact, Organisation])

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

        self.assertIn(REL_OBJ_EMIT_ORGA, relation_types)
        self.assertNotIn(REL_SUB_EMIT_ORGA, relation_types)
        self.get_relationtype_or_fail(REL_OBJ_EMIT_ORGA, [Opportunity], [Organisation])

        self.get_relationtype_or_fail(REL_OBJ_CURRENT_DOC, [Opportunity], [Invoice, Quote, SalesOrder])

        self.assertTrue(SalesPhase.objects.exists())
        self.assertTrue(Origin.objects.exists())

        keys = SettingKey.objects.filter(pk=SETTING_USE_CURRENT_QUOTE)
        self.assertEqual(1, len(keys))
        self.assertEqual(1, SettingValue.objects.filter(key=keys[0]).count())

    def test_portal(self):
        self.login()
        self.assertEqual(self.client.get('/opportunities/').status_code, 200)

    def create_opportunity(self, name):
        create_orga = Organisation.objects.create
        target  = create_orga(user=self.user, name='Target renegade')
        emitter = create_orga(user=self.user, name='My society')

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        response = self.client.post('/opportunities/opportunity/add', follow=True,
                                    data={'user':         self.user.pk,
                                          'name':         name,
                                          'sales_phase':  SalesPhase.objects.all()[0].id,
                                          'closing_date': '2010-10-11',
                                          'target':       self.genericfield_format_entity(target),
                                          'emit_orga':    emitter.id,
                                          'currency':     DEFAULT_CURRENCY_PK,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        return self.get_object_or_fail(Opportunity, name=name), target, emitter

    def test_opportunity_createview01(self):
        self.login()

        url = '/opportunities/opportunity/add'
        self.assertEqual(200, self.client.post(url).status_code)

        create_orga = Organisation.objects.create
        target  = create_orga(user=self.user, name='Target renegade')
        emitter = create_orga(user=self.user, name='My society')

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        name  = 'Opportunity01'
        phase = SalesPhase.objects.all()[0]
        response = self.client.post(url, follow=True,
                                    data={'user':                  self.user.pk,
                                          'name':                  name,
                                          'sales_phase':           phase.id,
                                          'expected_closing_date': '2010-9-20',
                                          'closing_date':          '2010-10-11',
                                          'target':                self.genericfield_format_entity(target),
                                          'emit_orga':             emitter.id,
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
    
    def test_opportunity_createview02(self):
        self.login()

        target  = Contact.objects.create(user=self.user, first_name='Target', last_name='renegade')
        emitter = Organisation.objects.create(user=self.user, name='My society')

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        name  = 'Opportunity01'
        phase = SalesPhase.objects.all()[0]
        response = self.client.post('/opportunities/opportunity/add', follow=True,
                                    data={'user':                  self.user.pk,
                                          'name':                  name,
                                          'sales_phase':           phase.id,
                                          'expected_closing_date': '2010-9-20',
                                          'closing_date':          '2010-10-11',
                                          'target':                self.genericfield_format_entity(target),
                                          'emit_orga':             emitter.id,
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

    def test_opportunity_createview03(self):#Only contact & orga models are allowed
        self.login()

        response = self.client.post('/opportunities/opportunity/add')
        self.assertEqual(200, response.status_code)

        target  = CremeEntity.objects.create(user=self.user)
        emitter = Organisation.objects.create(user=self.user, name='My society')

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        name  = 'Opportunity01'
        phase = SalesPhase.objects.all()[0]
        response = self.client.post('/opportunities/opportunity/add', follow=True,
                                    data={'user':                  self.user.pk,
                                          'name':                  name,
                                          'sales_phase':           phase.id,
                                          'expected_closing_date': '2010-9-20',
                                          'closing_date':          '2010-10-11',
                                          'target':                self.genericfield_format_entity(target),
                                          'emit_orga':             emitter.id,
                                          'first_action_date':     '2010-7-13',
                                         }
                                   )
        self.assertRaises(Opportunity.DoesNotExist, Opportunity.objects.get, name=name)

    def test_opportunity_createview04(self): #link creds error
        self.login(is_superuser=False, allowed_apps=['opportunities'], creatable_models=[Opportunity])

        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_VIEW   | SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | SetCredentials.CRED_UNLINK, #no CRED_LINK
                                      set_type=SetCredentials.ESET_OWN
                                     )

        create_orga = Organisation.objects.create
        target  = create_orga(user=self.user, name='Target renegade')
        emitter = create_orga(user=self.user, name='My society')

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        response = self.client.post('/opportunities/opportunity/add', follow=True,
                                    data={'user':         self.user.pk,
                                          'name':         'My opportunity',
                                          'sales_phase':  SalesPhase.objects.all()[0].id,
                                          'closing_date': '2011-03-14',
                                          'target':       self.genericfield_format_entity(target),
                                          'emit_orga':    emitter.id,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'target',
                             [_(u'You are not allowed to link this entity: %s') % (_(u'Entity #%s (not viewable)') % target.id)]
                            )
        self.assertFormError(response, 'form', 'emit_orga',
                             [_(u'You are not allowed to link this entity: %s') % (_(u'Entity #%s (not viewable)') % emitter.id)]
                            )

    def test_add_to_orga01(self):
        self.login()

        create_orga = Organisation.objects.create
        target  = create_orga(user=self.user, name='Target renegade')
        emitter = create_orga(user=self.user, name='My society')

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        url = '/opportunities/opportunity/add_to/%s' % target.id
        self.assertEqual(200, self.client.get(url).status_code)

        salesphase = SalesPhase.objects.all()[0]
        name = 'Opportunity linked to %s' % target
        response = self.client.post(url, data={'user':         self.user.pk,
                                               'name':         name,
                                               'sales_phase':  salesphase.id,
                                               'closing_date': '2011-03-12',
                                               'target':       self.genericfield_format_entity(target),
                                               'emit_orga':    emitter.id,
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
                                               'target':       self.genericfield_format_entity(target),
                                               'emit_orga':    emitter.id,
                                               'currency':     DEFAULT_CURRENCY_PK,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(302, response.status_code)
        self.assertRelationCount(1, target, REL_SUB_PROSPECT, emitter)

    def test_add_to_orga02(self):
        self.login()

        create_orga = Organisation.objects.create
        target  = create_orga(user=self.user, name='Target renegade')
        emitter = create_orga(user=self.user, name='My society')

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        url = '/opportunities/opportunity/add_to/%s/popup' % target.id
        self.assertEqual(200, self.client.get(url).status_code)

        salesphase = SalesPhase.objects.all()[0]
        name = 'Opportunity linked to %s' % target
        response = self.client.post(url, data={'user':         self.user.pk,
                                               'name':         name,
                                               'sales_phase':  salesphase.id,
                                               'closing_date': '2011-03-12',
                                               'target':       self.genericfield_format_entity(target),
                                               'emit_orga':    emitter.id,
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

        create_orga = Organisation.objects.create
        target  = create_orga(user=self.user, name='Target renegade')
        emitter = create_orga(user=self.user, name='My society')

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        self.assertEqual(403, self.client.get('/opportunities/opportunity/add_to/%s' % target.id).status_code)

    def test_add_to_contact01(self):
        self.login()

        target  = Contact.objects.create(user=self.user, first_name='Target', last_name='renegade')
        emitter = Organisation.objects.create(user=self.user, name='My society')

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        url = '/opportunities/opportunity/add_to/%s' % target.id
        self.assertEqual(200, self.client.get(url).status_code)

        salesphase = SalesPhase.objects.all()[0]
        name = 'Opportunity linked to %s' % target
        response = self.client.post(url, data={'user':         self.user.pk,
                                               'name':         name,
                                               'sales_phase':  salesphase.id,
                                               'closing_date': '2011-03-12',
                                               'target':       self.genericfield_format_entity(target),
                                               'emit_orga':    emitter.id,
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
                                               'target':       self.genericfield_format_entity(target),
                                               'emit_orga':    emitter.id,
                                               'currency':     DEFAULT_CURRENCY_PK,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(302, response.status_code)
        self.assertRelationCount(1, target, REL_SUB_PROSPECT, emitter)

    def test_add_to_contact02(self):
        self.login()

        target  = Contact.objects.create(user=self.user, first_name='Target', last_name='renegade')
        emitter = Organisation.objects.create(user=self.user, name='My society')

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        url = '/opportunities/opportunity/add_to/%s/popup' % target.id
        self.assertEqual(200, self.client.get(url).status_code)

        salesphase = SalesPhase.objects.all()[0]
        name = 'Opportunity linked to %s' % target
        response = self.client.post(url, data={'user':         self.user.pk,
                                               'name':         name,
                                               'sales_phase':  salesphase.id,
                                               'closing_date': '2011-03-12',
                                               'target':       self.genericfield_format_entity(target),
                                               'emit_orga':    emitter.id,
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

        target  = Contact.objects.create(user=self.user, first_name='Target', last_name='renegade')
        emitter = Organisation.objects.create(user=self.user, name='My society')

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

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
                                               'target':       self.genericfield_format_entity(target),
                                               'emit_orga':    emitter.id,
                                              }
                                   )

        self.assertEqual(opportunity_count, Opportunity.objects.count())#No new opportunity was created
        self.assertFormError(response, 'form', 'target', [_(u'This content type is not allowed.')])

    def _build_gendoc_url(self, opportunity, ct):
        return '/opportunities/opportunity/generate_new_doc/%s/%s' % (
                        opportunity.id, ct.id
                    )

    def test_opportunity_generate_new_doc01(self):
        self.login()

        self.assertEqual(0, Quote.objects.count())

        opportunity, target, emitter = self.create_opportunity('Opportunity01')
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

    def test_opportunity_generate_new_doc02(self):
        self.login()

        opportunity, target, emitter = self.create_opportunity('Opportunity01')
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

    def test_opportunity_generate_new_doc04(self):
        self.login()

        opportunity, target, emitter = self.create_opportunity('Opportunity01')
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

    def test_set_current_quote_1(self):
        self.login()

        opportunity, target, emitter = self.create_opportunity('Opportunity01')
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

    def test_set_current_quote_2(self):
        self.login()

        opportunity, target, emitter = self.create_opportunity('Opportunity01')
        url = self._build_gendoc_url(opportunity, ContentType.objects.get_for_model(Quote))

        opportunity.estimated_sales = Decimal('1000')
        opportunity.save()

        self.client.post(url)
        quote1 = Quote.objects.all()[0]
        sl1 = ServiceLine.objects.create(user=self.user, related_document=quote1, on_the_fly_item='Stuff1', unit_price=Decimal("300"))

        self.client.post(url)
        quote2 = Quote.objects.exclude(pk=quote1.id)[0]
        sl2 = ServiceLine.objects.create(user=self.user, related_document=quote2, on_the_fly_item='Stuff1', unit_price=Decimal("500"))

        use_current_quote = SettingValue.objects.get(key=SETTING_USE_CURRENT_QUOTE)
        use_current_quote.value = True
        use_current_quote.save()

        url = self._build_setcurrentquote_url(opportunity, quote1)
        self.assertEqual(200, self.client.post(url, follow=True).status_code)

        opportunity = self.refresh(opportunity)
        self.assertEqual(opportunity.estimated_sales, quote1.get_total()) # 300

        url = self._build_setcurrentquote_url(opportunity, quote2)
        self.assertEqual(200, self.client.post(url, follow=True).status_code)

        opportunity = self.refresh(opportunity)
        self.assertEqual(opportunity.estimated_sales, quote2.get_total()) # 500

    def test_set_current_quote_3(self):
        self.login()

        opportunity, target, emitter = self.create_opportunity('Opportunity01')

        use_current_quote = SettingValue.objects.get(key=SETTING_USE_CURRENT_QUOTE)
        use_current_quote.value = False
        use_current_quote.save()

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

    def test_get_weighted_sales(self):
        self.login()
        opportunity, target, emitter = self.create_opportunity('Opportunity01')
        funf = opportunity.function_fields.get('get_weighted_sales')
        self.assertIsNotNone(funf)

        self.assertIsNone(opportunity.estimated_sales)
        self.assertIsNone(opportunity.chance_to_win)
        self.assertEqual(0, opportunity.get_weighted_sales())
        self.assertEqual(0, funf(opportunity).for_html())

        opportunity.estimated_sales = 1000
        opportunity.chance_to_win   =  10
        self.assertEqual(100, opportunity.get_weighted_sales())
        self.assertEqual(100, funf(opportunity).for_html())


class SalesPhaseTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        SalesPhase.objects.all().delete()
        cls.populate('creme_core', 'creme_config')

    def test_create_n_order(self):
        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming', description='...', order=2)
        sp2 = create_phase(name='Abandoned',   description='...', order=1)

        self.assertEqual([sp2, sp1], list(SalesPhase.objects.all()))

    def test_incr_order01(self):
        self.login()

        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming', description='...', order=1)
        sp2 = create_phase(name='Abandoned',   description='...', order=2)

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
        sp1 = create_phase(name='Forthcoming', description='...', order=1)
        sp2 = create_phase(name='Abandoned',   description='...', order=2)
        sp3 = create_phase(name='Won',         description='...', order=3)
        sp4 = create_phase(name='Lost',        description='...', order=4)

        self.assertEqual(200, self.client.post('/creme_config/opportunities/sales_phase/down/%s' % sp2.id).status_code)

        self.assertEqual(1, self.refresh(sp1).order)
        self.assertEqual(3, self.refresh(sp2).order)
        self.assertEqual(2, self.refresh(sp3).order)
        self.assertEqual(4, self.refresh(sp4).order)

    def test_incr_order03(self): #errrors
        self.login()

        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming', description='...', order=1)
        sp2 = create_phase(name='Abandoned',   description='...', order=2)

        url = '/creme_config/opportunities/sales_phase/down/%s'
        self.assertPOST404(url % sp2.id)
        self.assertPOST404(url % (sp2.id + sp1.id)) #odd pk

    def test_decr_order01(self):
        self.login()

        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming', description='...', order=1)
        sp2 = create_phase(name='Abandoned',   description='...', order=2)
        sp3 = create_phase(name='Won',         description='...', order=3)
        sp4 = create_phase(name='Lost',        description='...', order=4)

        self.assertEqual(200, self.client.post('/creme_config/opportunities/sales_phase/up/%s' % sp3.id).status_code)

        self.assertEqual(1, self.refresh(sp1).order)
        self.assertEqual(3, self.refresh(sp2).order)
        self.assertEqual(2, self.refresh(sp3).order)
        self.assertEqual(4, self.refresh(sp4).order)

    def test_decr_order02(self): #error
        self.login()

        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming', description='...', order=1)
        sp2 = create_phase(name='Abandoned',   description='...', order=2)

        self.assertPOST404('/creme_config/opportunities/sales_phase/up/%s' % sp1.id)


class OriginTestCase(CremeTestCase):
    def test_config(self):
        self.login()
        self.populate('creme_core', 'creme_config')

        create_origin = Origin.objects.create
        origin1 = create_origin(name='Web site', description='...')
        origin2 = create_origin(name='Mouth',    description='...')

        response = self.client.get('/creme_config/opportunities/origin/portal/')
        self.assertEqual(200, response.status_code)
        self.assertContains(response, origin1.name)
        self.assertContains(response, origin2.name)

        self.assertPOST404('/creme_config/opportunities/origin/down/%s' % origin1.id)
