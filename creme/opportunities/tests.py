# -*- coding: utf-8 -*-

from datetime import date

from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, Relation, CremeProperty
from creme_core.management.commands.creme_populate import Command as PopulateCommand
from creme_core.constants import REL_SUB_RELATED_TO, REL_OBJ_RELATED_TO, PROP_IS_MANAGED_BY_CREME

from documents.constants import REL_SUB_CURRENT_DOC

from persons.models import Organisation

#from products.models import *

from billing.models import Quote
from billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED

from opportunities.models import *
from opportunities.constants import *


class OpportunitiesTestCase(TestCase):
    def login(self):
        if not self.user:
            user = User.objects.create(username='Gally')
            user.set_password(self.password)
            user.is_superuser = True
            user.save()
            self.user = user

        logged = self.client.login(username=self.user.username, password=self.password)
        self.assert_(logged, 'Not logged in')

    def setUp(self):
        PopulateCommand().handle(application=['creme_core', 'documents', 'billing', 'opportunities'])
        self.password = 'test'
        self.user = None

    def test_populate(self): #test get_compatible_ones() too
        ct = ContentType.objects.get_for_model(Opportunity)
        relation_types = dict((rtype.id, rtype) for rtype in RelationType.get_compatible_ones(ct))

        self.failIf(REL_SUB_TARGETS_ORGA in relation_types)

        self.assert_(REL_OBJ_LINKED_PRODUCT in relation_types)
        self.failIf(REL_SUB_LINKED_PRODUCT in relation_types)

        self.assert_(REL_OBJ_LINKED_SERVICE in relation_types)
        self.failIf(REL_SUB_LINKED_SERVICE in relation_types)

        self.assert_(REL_OBJ_LINKED_CONTACT in relation_types)
        self.failIf(REL_SUB_LINKED_CONTACT in relation_types)

        self.assert_(REL_OBJ_LINKED_SALESORDER in relation_types)
        self.failIf(REL_SUB_LINKED_SALESORDER in relation_types)

        self.assert_(REL_OBJ_LINKED_INVOICE in relation_types)
        self.failIf(REL_SUB_LINKED_INVOICE in relation_types)

        self.assert_(REL_OBJ_LINKED_QUOTE in relation_types)
        self.failIf(REL_SUB_LINKED_QUOTE in relation_types)

        self.assert_(REL_OBJ_RESPONSIBLE in relation_types)
        self.failIf(REL_SUB_RESPONSIBLE in relation_types)

        self.assert_(REL_OBJ_EMIT_ORGA in relation_types)
        self.failIf(REL_SUB_EMIT_ORGA in relation_types)

        self.assert_(REL_SUB_RELATED_TO in relation_types)
        self.assert_(REL_OBJ_RELATED_TO in relation_types)

        self.assert_(SalesPhase.objects.exists())
        self.assert_(Origin.objects.exists())

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
                                            'target_orga':  target.id,
                                            'emit_orga':    emitter.id,
                                    }
                                   )
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

        opportunity, target, emitter = self.create_opportunity('Opportunity01')

        filter_ = Relation.objects.filter
        self.assertEqual(1, filter_(subject_entity=target,  type=REL_OBJ_TARGETS_ORGA, object_entity=opportunity).count())
        self.assertEqual(1, filter_(subject_entity=emitter, type=REL_SUB_EMIT_ORGA,    object_entity=opportunity).count())

    def test_opportunity_generate_new_doc01(self):
        self.login()

        self.failIf(Quote.objects.all())

        opportunity, target, emitter = self.create_opportunity('Opportunity01')
        ct = ContentType.objects.get_for_model(Quote)

        response = self.client.get('/opportunities/opportunity/generate_new_doc/%s/%s' % (opportunity.id, ct.id), follow=True)
        self.assertEqual(200, response.status_code)

        quotes = Quote.objects.all()
        self.assertEqual(1 , len(quotes))

        quote = quotes[0]
        self.assert_((date.today() - quote.issuing_date).seconds < 10)
        self.assertEqual(1, quote.status_id)

        filter_ = Relation.objects.filter
        self.assertEqual(1, filter_(subject_entity=quote, type=REL_SUB_BILL_ISSUED,   object_entity=emitter).count())
        self.assertEqual(1, filter_(subject_entity=quote, type=REL_SUB_BILL_RECEIVED, object_entity=target).count())
        self.assertEqual(1, filter_(subject_entity=quote, type=REL_SUB_LINKED_QUOTE,  object_entity=opportunity).count())
        self.assertEqual(1, filter_(subject_entity=quote, type=REL_SUB_CURRENT_DOC,   object_entity=opportunity).count())

    def test_opportunity_generate_new_doc02(self):
        self.login()

        opportunity, target, emitter = self.create_opportunity('Opportunity01')
        ct = ContentType.objects.get_for_model(Quote)

        self.client.get('/opportunities/opportunity/generate_new_doc/%s/%s' % (opportunity.id, ct.id))
        quote1 = Quote.objects.all()[0]

        self.client.get('/opportunities/opportunity/generate_new_doc/%s/%s' % (opportunity.id, ct.id))

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

    #def test_opportunity_generate_new_doc02(self): #TODO test with credentials problems

    def test_set_current_quote(self):
        self.login()

        opportunity, target, emitter = self.create_opportunity('Opportunity01')
        ct = ContentType.objects.get_for_model(Quote)

        self.client.get('/opportunities/opportunity/generate_new_doc/%s/%s' % (opportunity.id, ct.id))
        quote1 = Quote.objects.all()[0]

        self.client.get('/opportunities/opportunity/generate_new_doc/%s/%s' % (opportunity.id, ct.id))
        quote2 = Quote.objects.exclude(pk=quote1.id)[0]

        response = self.client.get('/opportunities/opportunity/%s/linked/quote/%s/set_current/' % (opportunity.id, quote1.id), follow=True)
        self.assertEqual(200, response.status_code)

        filter_ = Relation.objects.filter
        self.assertEqual(1, filter_(subject_entity=quote2, type=REL_SUB_BILL_ISSUED,   object_entity=emitter).count())
        self.assertEqual(1, filter_(subject_entity=quote2, type=REL_SUB_BILL_RECEIVED, object_entity=target).count())
        self.assertEqual(1, filter_(subject_entity=quote2, type=REL_SUB_LINKED_QUOTE,  object_entity=opportunity).count())
        self.assertEqual(0, filter_(subject_entity=quote2, type=REL_SUB_CURRENT_DOC,   object_entity=opportunity).count())

        self.assertEqual(1, filter_(subject_entity=quote1, type=REL_SUB_BILL_ISSUED,   object_entity=emitter).count())
        self.assertEqual(1, filter_(subject_entity=quote1, type=REL_SUB_BILL_RECEIVED, object_entity=target).count())
        self.assertEqual(1, filter_(subject_entity=quote1, type=REL_SUB_LINKED_QUOTE,  object_entity=opportunity).count())
        self.assertEqual(1, filter_(subject_entity=quote1, type=REL_SUB_CURRENT_DOC,   object_entity=opportunity).count())

#TODO: test add_to_orga (with bad creds etc...)