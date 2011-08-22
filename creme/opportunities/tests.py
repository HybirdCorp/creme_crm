# -*- coding: utf-8 -*-

from datetime import date

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, Relation, CremeProperty, SetCredentials
from creme_core.constants import PROP_IS_MANAGED_BY_CREME
from creme_core.models.entity import CremeEntity
from creme_core.tests.base import CremeTestCase

from creme_config.models import SettingKey, SettingValue

from persons.models import Organisation, Contact

from products.models import Product, Service

from billing.models import Quote, SalesOrder, Invoice
from billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED

from opportunities.models import *
from opportunities.constants import *


class OpportunitiesTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'documents', 'persons', 'commercial', 'billing', 'opportunities')

    def genericfield_format_entity(self, entity):
        return '{"ctype":"%s", "entity":"%s"}' % (entity.entity_type_id, entity.id)

    def test_populate(self): #test get_compatible_ones() too
        ct = ContentType.objects.get_for_model(Opportunity)
        relation_types = dict((rtype.id, rtype) for rtype in RelationType.get_compatible_ones(ct))

        self.failIf(REL_SUB_TARGETS in relation_types)
        self.get_relationtype_or_fail(REL_SUB_TARGETS, [Opportunity], [Contact, Organisation])

        self.assert_(REL_OBJ_LINKED_PRODUCT in relation_types)
        self.failIf(REL_SUB_LINKED_PRODUCT in relation_types)
        self.get_relationtype_or_fail(REL_OBJ_LINKED_PRODUCT, [Opportunity], [Product])

        self.assert_(REL_OBJ_LINKED_SERVICE in relation_types)
        self.failIf(REL_SUB_LINKED_SERVICE in relation_types)
        self.get_relationtype_or_fail(REL_OBJ_LINKED_SERVICE, [Opportunity], [Service])

        self.assert_(REL_OBJ_LINKED_CONTACT in relation_types)
        self.failIf(REL_SUB_LINKED_CONTACT in relation_types)
        self.get_relationtype_or_fail(REL_OBJ_LINKED_CONTACT, [Opportunity], [Contact])

        self.assert_(REL_OBJ_LINKED_SALESORDER in relation_types)
        self.failIf(REL_SUB_LINKED_SALESORDER in relation_types)
        self.get_relationtype_or_fail(REL_OBJ_LINKED_SALESORDER, [Opportunity], [SalesOrder])

        self.assert_(REL_OBJ_LINKED_INVOICE in relation_types)
        self.failIf(REL_SUB_LINKED_INVOICE in relation_types)
        self.get_relationtype_or_fail(REL_OBJ_LINKED_INVOICE, [Opportunity], [Invoice])

        self.assert_(REL_OBJ_LINKED_QUOTE in relation_types)
        self.failIf(REL_SUB_LINKED_QUOTE in relation_types)
        self.get_relationtype_or_fail(REL_OBJ_LINKED_QUOTE, [Opportunity], [Quote])

        self.assert_(REL_OBJ_RESPONSIBLE in relation_types)
        self.failIf(REL_SUB_RESPONSIBLE in relation_types)
        self.get_relationtype_or_fail(REL_OBJ_RESPONSIBLE, [Opportunity], [Contact])

        self.assert_(REL_OBJ_EMIT_ORGA in relation_types)
        self.failIf(REL_SUB_EMIT_ORGA in relation_types)
        self.get_relationtype_or_fail(REL_OBJ_EMIT_ORGA, [Opportunity], [Organisation])

        self.get_relationtype_or_fail(REL_OBJ_CURRENT_DOC, [Opportunity], [Invoice, Quote, SalesOrder])

        self.assert_(SalesPhase.objects.exists())
        self.assert_(Origin.objects.exists())

        keys = SettingKey.objects.filter(pk=SETTING_USE_LINES)
        self.assertEqual(1, len(keys))
        self.assertEqual(1, SettingValue.objects.filter(key=keys[0]).count())

    def create_opportunity(self, name):
        create_orga = Organisation.objects.create
        target  = create_orga(user=self.user, name='Target renegade')
        emitter = create_orga(user=self.user, name='My society')

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        response = self.client.post('/opportunities/opportunity/add', follow=True,
                                    data={
                                            'user':         self.user.pk,
                                            'name':         name,
                                            'sales_phase':  SalesPhase.objects.all()[0].id,
                                            'closing_date': '2010-10-11',
                                            'target':       self.genericfield_format_entity(target),
                                            'emit_orga':    emitter.id,
                                    }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            opportunity = Opportunity.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        return opportunity, target, emitter

    def test_opportunity_createview01(self):
        self.login()

        response = self.client.post('/opportunities/opportunity/add')
        self.assertEqual(200, response.status_code)

        create_orga = Organisation.objects.create
        target  = create_orga(user=self.user, name='Target renegade')
        emitter = create_orga(user=self.user, name='My society')

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        name  = 'Opportunity01'
        phase = SalesPhase.objects.all()[0]
        response = self.client.post('/opportunities/opportunity/add', follow=True,
                                    data={
                                            'user':                  self.user.pk,
                                            'name':                  name,
                                            'sales_phase':           phase.id,
                                            'expected_closing_date': '2010-9-20',
                                            'closing_date':          '2010-10-11',
                                            'target':                self.genericfield_format_entity(target),
                                            'emit_orga':             emitter.id,
                                            'first_action_date':     '2010-7-13',
                                    }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            opportunity = Opportunity.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(phase, opportunity.sales_phase)
        self.assertEqual(date(2010, 9,  20), opportunity.expected_closing_date)
        self.assertEqual(date(2010, 10, 11), opportunity.closing_date)
        self.assertEqual(date(2010, 7,  13), opportunity.first_action_date)

        filter_ = Relation.objects.filter
        self.assertEqual(1, filter_(subject_entity=target,  type=REL_OBJ_TARGETS, object_entity=opportunity).count())
        self.assertEqual(1, filter_(subject_entity=emitter, type=REL_SUB_EMIT_ORGA,    object_entity=opportunity).count())

    def test_opportunity_createview02(self):
        self.login()

        response = self.client.post('/opportunities/opportunity/add')
        self.assertEqual(200, response.status_code)

        target  = Contact.objects.create(user=self.user, first_name='Target', last_name='renegade')
        emitter = Organisation.objects.create(user=self.user, name='My society')

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        name  = 'Opportunity01'
        phase = SalesPhase.objects.all()[0]
        response = self.client.post('/opportunities/opportunity/add', follow=True,
                                    data={
                                            'user':                  self.user.pk,
                                            'name':                  name,
                                            'sales_phase':           phase.id,
                                            'expected_closing_date': '2010-9-20',
                                            'closing_date':          '2010-10-11',
                                            'target':                self.genericfield_format_entity(target),
                                            'emit_orga':             emitter.id,
                                            'first_action_date':     '2010-7-13',
                                    }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            opportunity = Opportunity.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(phase, opportunity.sales_phase)
        self.assertEqual(date(2010, 9,  20), opportunity.expected_closing_date)
        self.assertEqual(date(2010, 10, 11), opportunity.closing_date)
        self.assertEqual(date(2010, 7,  13), opportunity.first_action_date)

        filter_ = Relation.objects.filter
        self.assertEqual(1, filter_(subject_entity=target,  type=REL_OBJ_TARGETS, object_entity=opportunity).count())
        self.assertEqual(1, filter_(subject_entity=emitter, type=REL_SUB_EMIT_ORGA,    object_entity=opportunity).count())

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
                                    data={
                                            'user':                  self.user.pk,
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
        self.login(is_superuser=False, allowed_apps=['opportunities'])

        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_VIEW   | SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | SetCredentials.CRED_UNLINK, #no CRED_LINK
                                      set_type=SetCredentials.ESET_OWN)
        self.role.creatable_ctypes = [ContentType.objects.get_for_model(Opportunity)]

        create_orga = Organisation.objects.create
        target  = create_orga(user=self.user, name='Target renegade')
        emitter = create_orga(user=self.user, name='My society')

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        response = self.client.post('/opportunities/opportunity/add', follow=True,
                                    data={
                                            'user':         self.user.pk,
                                            'name':         'My opportunity',
                                            'sales_phase':  SalesPhase.objects.all()[0].id,
                                            'closing_date': '2011-03-14',
                                            'target':       self.genericfield_format_entity(target),
                                            'emit_orga':    emitter.id,
                                    }
                                   )
        self.assertEqual(200, response.status_code)

        try:
            form = response.context['form']
        except Exception, e:
            self.fail(str(e))

        self.assert_(form.errors)
        self.assertEqual(set(['target', 'emit_orga']), set(form.errors.keys()))

    def test_add_to_orga01(self):
        self.login()

        create_orga = Organisation.objects.create
        target  = create_orga(user=self.user, name='Target renegade')
        emitter = create_orga(user=self.user, name='My society')

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        url = '/opportunities/opportunity/add_to/%s' % target.id
        self.assertEqual(200, self.client.get(url).status_code)

        salesphase_id = SalesPhase.objects.all()[0].id
        name = 'Opportunity linked to %s' % target
        response = self.client.post(url, data={
                                                'user':         self.user.pk,
                                                'name':         name,
                                                'sales_phase':  salesphase_id,
                                                'closing_date': '2011-03-12',
                                                'target':       self.genericfield_format_entity(target),
                                                'emit_orga':    emitter.id,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(302, response.status_code)

        try:
            opportunity = Opportunity.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(salesphase_id, opportunity.sales_phase_id)

        filter_ = Relation.objects.filter
        self.assertEqual(1, filter_(subject_entity=target,  type=REL_OBJ_TARGETS, object_entity=opportunity).count())
        self.assertEqual(1, filter_(subject_entity=emitter, type=REL_SUB_EMIT_ORGA,    object_entity=opportunity).count())

    def test_add_to_orga02(self):
        self.login()

        create_orga = Organisation.objects.create
        target  = create_orga(user=self.user, name='Target renegade')
        emitter = create_orga(user=self.user, name='My society')

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        url = '/opportunities/opportunity/add_to/%s/popup' % target.id
        self.assertEqual(200, self.client.get(url).status_code)

        salesphase_id = SalesPhase.objects.all()[0].id
        name = 'Opportunity linked to %s' % target
        response = self.client.post(url, data={
                                                'user':         self.user.pk,
                                                'name':         name,
                                                'sales_phase':  salesphase_id,
                                                'closing_date': '2011-03-12',
                                                'target':       self.genericfield_format_entity(target),
                                                'emit_orga':    emitter.id,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            opportunity = Opportunity.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(salesphase_id, opportunity.sales_phase_id)

        filter_ = Relation.objects.filter
        self.assertEqual(1, filter_(subject_entity=target,  type=REL_OBJ_TARGETS, object_entity=opportunity).count())
        self.assertEqual(1, filter_(subject_entity=emitter, type=REL_SUB_EMIT_ORGA,    object_entity=opportunity).count())

    def test_add_to_orga03(self): #with bad creds
        self.login(is_superuser=False, allowed_apps=['opportunities'])

        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_VIEW   | SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | SetCredentials.CRED_UNLINK, #no CRED_LINK
                                      set_type=SetCredentials.ESET_OWN)
        self.role.creatable_ctypes = [ContentType.objects.get_for_model(Opportunity)]

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

        salesphase_id = SalesPhase.objects.all()[0].id
        name = 'Opportunity linked to %s' % target
        response = self.client.post(url, data={
                                                'user':         self.user.pk,
                                                'name':         name,
                                                'sales_phase':  salesphase_id,
                                                'closing_date': '2011-03-12',
                                                'target':       self.genericfield_format_entity(target),
                                                'emit_orga':    emitter.id,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(302, response.status_code)

        try:
            opportunity = Opportunity.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(salesphase_id, opportunity.sales_phase_id)

        filter_ = Relation.objects.filter
        self.assertEqual(1, filter_(subject_entity=target,  type=REL_OBJ_TARGETS, object_entity=opportunity).count())
        self.assertEqual(1, filter_(subject_entity=emitter, type=REL_SUB_EMIT_ORGA,    object_entity=opportunity).count())

    def test_add_to_contact02(self):
        self.login()

        target  = Contact.objects.create(user=self.user, first_name='Target', last_name='renegade')
        emitter = Organisation.objects.create(user=self.user, name='My society')

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=emitter)

        url = '/opportunities/opportunity/add_to/%s/popup' % target.id
        self.assertEqual(200, self.client.get(url).status_code)

        salesphase_id = SalesPhase.objects.all()[0].id
        name = 'Opportunity linked to %s' % target
        response = self.client.post(url, data={
                                                'user':         self.user.pk,
                                                'name':         name,
                                                'sales_phase':  salesphase_id,
                                                'closing_date': '2011-03-12',
                                                'target':       self.genericfield_format_entity(target),
                                                'emit_orga':    emitter.id,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            opportunity = Opportunity.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(salesphase_id, opportunity.sales_phase_id)

        filter_ = Relation.objects.filter
        self.assertEqual(1, filter_(subject_entity=target,  type=REL_OBJ_TARGETS, object_entity=opportunity).count())
        self.assertEqual(1, filter_(subject_entity=emitter, type=REL_SUB_EMIT_ORGA,    object_entity=opportunity).count())

    def test_add_to_contact03(self): #with bad creds
        self.login(is_superuser=False, allowed_apps=['opportunities'])

        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_VIEW   | SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | SetCredentials.CRED_UNLINK, #no CRED_LINK
                                      set_type=SetCredentials.ESET_OWN)
        self.role.creatable_ctypes = [ContentType.objects.get_for_model(Opportunity)]

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

        response = self.client.get('/opportunities/opportunity/add_to/%s' % target.id)
        self.assertEqual(200, response.status_code)

        salesphase_id = SalesPhase.objects.all()[0].id
        name = 'Opportunity linked to %s' % target
        response = self.client.post('/opportunities/opportunity/add_to/%s' % target.id, data={
                                                'user':         self.user.pk,
                                                'name':         name,
                                                'sales_phase':  salesphase_id,
                                                'closing_date': '2011-03-12',
                                                'target':       self.genericfield_format_entity(target),
                                                'emit_orga':    emitter.id,
                                              }
                                   )

        self.assertEqual(opportunity_count, Opportunity.objects.count())#No new opportunity was created
        try:
            form = response.context['form']
        except Exception, e:
            self.fail(str(e))

        self.assert_(form.errors)
        self.assertEqual(set(['target']), set(form.errors.keys()))

    def test_opportunity_generate_new_doc01(self):
        self.login()

        self.failIf(Quote.objects.count())

        opportunity, target, emitter = self.create_opportunity('Opportunity01')
        ct = ContentType.objects.get_for_model(Quote)
        url = '/opportunities/opportunity/generate_new_doc/%s/%s' % (opportunity.id, ct.id)

        self.assertEqual(404, self.client.get(url).status_code)
        self.assertEqual(200, self.client.post(url, follow=True).status_code)

        quotes = Quote.objects.all()
        self.assertEqual(1, len(quotes))

        quote = quotes[0]
        self.assert_((date.today() - quote.issuing_date).seconds < 10)
        self.assertEqual(1, quote.status_id)

        def count_relations(type_id, object_id):
            return Relation.objects.filter(subject_entity=quote, type=type_id, object_entity=object_id).count()

        self.assertEqual(1, count_relations(type_id=REL_SUB_BILL_ISSUED,   object_id=emitter))
        self.assertEqual(1, count_relations(type_id=REL_SUB_BILL_RECEIVED, object_id=target))
        self.assertEqual(1, count_relations(type_id=REL_SUB_LINKED_QUOTE,  object_id=opportunity))
        self.assertEqual(1, count_relations(type_id=REL_SUB_CURRENT_DOC,   object_id=opportunity))

    def test_opportunity_generate_new_doc02(self):
        self.login()

        opportunity, target, emitter = self.create_opportunity('Opportunity01')
        ct = ContentType.objects.get_for_model(Quote)

        self.client.post('/opportunities/opportunity/generate_new_doc/%s/%s' % (opportunity.id, ct.id))
        quote1 = Quote.objects.all()[0]

        self.client.post('/opportunities/opportunity/generate_new_doc/%s/%s' % (opportunity.id, ct.id))
        quotes = Quote.objects.exclude(pk=quote1.id)
        self.assertEqual(1, len(quotes))

        quote2 = quotes[0]

        filter_ = Relation.objects.filter
        self.assertEqual(1, filter_(subject_entity=quote2, type=REL_SUB_BILL_ISSUED,   object_entity=emitter).count())
        self.assertEqual(1, filter_(subject_entity=quote2, type=REL_SUB_BILL_RECEIVED, object_entity=target).count())
        self.assertEqual(1, filter_(subject_entity=quote2, type=REL_SUB_LINKED_QUOTE,  object_entity=opportunity).count())
        self.assertEqual(1, filter_(subject_entity=quote2, type=REL_SUB_CURRENT_DOC,   object_entity=opportunity).count())

        self.assertEqual(1, filter_(subject_entity=quote1, type=REL_SUB_BILL_ISSUED,   object_entity=emitter).count())
        self.assertEqual(1, filter_(subject_entity=quote1, type=REL_SUB_BILL_RECEIVED, object_entity=target).count())
        self.assertEqual(1, filter_(subject_entity=quote1, type=REL_SUB_LINKED_QUOTE,  object_entity=opportunity).count())
        self.assertEqual(0, filter_(subject_entity=quote1, type=REL_SUB_CURRENT_DOC,   object_entity=opportunity).count())

    #def test_opportunity_generate_new_doc03(self): #TODO test with credentials problems

    def test_set_current_quote(self):
        self.login()

        opportunity, target, emitter = self.create_opportunity('Opportunity01')
        ct = ContentType.objects.get_for_model(Quote)
        gen_quote = lambda: self.client.post('/opportunities/opportunity/generate_new_doc/%s/%s' % (opportunity.id, ct.id))

        gen_quote()
        quote1 = Quote.objects.all()[0]

        gen_quote()
        quote2 = Quote.objects.exclude(pk=quote1.id)[0]

        url = '/opportunities/opportunity/%s/linked/quote/%s/set_current/' % (opportunity.id, quote1.id)
        self.assertEqual(404, self.client.get(url).status_code)
        self.assertEqual(200, self.client.post(url, follow=True).status_code)

        filter_ = Relation.objects.filter
        self.assertEqual(1, filter_(subject_entity=quote2, type=REL_SUB_BILL_ISSUED,   object_entity=emitter).count())
        self.assertEqual(1, filter_(subject_entity=quote2, type=REL_SUB_BILL_RECEIVED, object_entity=target).count())
        self.assertEqual(1, filter_(subject_entity=quote2, type=REL_SUB_LINKED_QUOTE,  object_entity=opportunity).count())
        self.assertEqual(0, filter_(subject_entity=quote2, type=REL_SUB_CURRENT_DOC,   object_entity=opportunity).count())

        self.assertEqual(1, filter_(subject_entity=quote1, type=REL_SUB_BILL_ISSUED,   object_entity=emitter).count())
        self.assertEqual(1, filter_(subject_entity=quote1, type=REL_SUB_BILL_RECEIVED, object_entity=target).count())
        self.assertEqual(1, filter_(subject_entity=quote1, type=REL_SUB_LINKED_QUOTE,  object_entity=opportunity).count())
        self.assertEqual(1, filter_(subject_entity=quote1, type=REL_SUB_CURRENT_DOC,   object_entity=opportunity).count())
