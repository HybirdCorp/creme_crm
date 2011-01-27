# -*- coding: utf-8 -*-

from datetime import datetime, date

from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, Relation, CremePropertyType, CremeProperty, CremeEntity
from creme_core.management.commands.creme_populate import Command as PopulateCommand

from persons.models import Contact, Organisation

from opportunities.models import Opportunity, SalesPhase

from commercial.models import *
from commercial.constants import *


class CommercialTestCase(TestCase):
    def login(self):
        if not self.user:
            user = User.objects.create(username='Frodo')
            user.set_password(self.password)
            user.is_superuser = True
            user.save()
            self.user = user

        logged = self.client.login(username=self.user.username, password=self.password)
        self.assert_(logged, 'Not logged in')

    def setUp(self):
        PopulateCommand().handle(application=['creme_core', 'persons', 'commercial'])
        self.password = 'test'
        self.user = None

    def test_commercial01(self): #populate
        try:
            RelationType.objects.get(pk=REL_SUB_SOLD_BY)
            RelationType.objects.get(pk=REL_OBJ_SOLD_BY)
            CremePropertyType.objects.get(pk=PROP_IS_A_SALESMAN)
        except Exception, e:
            self.fail(str(e))

    def test_commapp01(self):
        self.login()

        entity = CremeEntity.objects.create(user=self.user)

        response = self.client.get('/commercial/approach/add/%s/' % entity.id)
        self.assertEqual(response.status_code, 200)

        title       = 'TITLE'
        description = 'DESCRIPTION'
        response = self.client.post('/commercial/approach/add/%s/' % entity.id,
                                    data={
                                            'user':        self.user.pk,
                                            'title':       title,
                                            'description': description,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

        commapps = CommercialApproach.objects.all()
        self.assertEqual(1, len(commapps))

        commapp = commapps[0]
        self.assertEqual(title,       commapp.title)
        self.assertEqual(description, commapp.description)
        self.assertEqual(entity.id,   commapp.entity_id)

        tdelta = (datetime.today() - commapp.creation_date)
        self.assert_(tdelta.seconds < 10)

    def test_salesman_create(self):
        self.login()

        response = self.client.get('/commercial/salesman/add')
        self.assertEqual(response.status_code, 200)

        first_name = 'John'
        last_name  = 'Doe'

        response = self.client.post('/commercial/salesman/add', follow=True,
                                    data={
                                            'user':       self.user.pk,
                                            'first_name': first_name,
                                            'last_name':  last_name,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)
        self.assert_(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)

        salesmen = Contact.objects.filter(properties__type=PROP_IS_A_SALESMAN)
        self.assertEqual(1, len(salesmen))

        salesman = salesmen[0]
        self.assertEqual(first_name, salesman.first_name)
        self.assertEqual(last_name,  salesman.last_name)

    def test_salesman_listview01(self):
        self.login()

        self.failIf(Contact.objects.filter(properties__type=PROP_IS_A_SALESMAN).count())

        response = self.client.get('/commercial/salesmen')
        self.assertEqual(response.status_code, 200)

        try:
            salesmen_page = response.context['entities']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(1, salesmen_page.number)
        self.failIf(salesmen_page.paginator.count)

    def test_salesman_listview02(self):
        self.login()

        self.client.post('/commercial/salesman/add', data={'user': self.user.pk, 'first_name': 'first_name1', 'last_name': 'last_name1'})
        self.client.post('/commercial/salesman/add', data={'user': self.user.pk, 'first_name': 'first_name2', 'last_name': 'last_name2'})
        salesmen = Contact.objects.filter(properties__type=PROP_IS_A_SALESMAN)
        self.assertEqual(2, len(salesmen))

        response = self.client.get('/commercial/salesmen')
        self.assertEqual(response.status_code, 200)

        try:
            salesmen_page = response.context['entities']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(1, salesmen_page.number)
        self.assertEqual(2, salesmen_page.paginator.count)
        self.assertEqual(set(s.id for s in salesmen), set(o.id for o in salesmen_page.object_list))

    def test_portal(self):
        self.login()
        response = self.client.get('/commercial/')
        self.assertEqual(response.status_code, 200)

    def test_populate(self):
        PopulateCommand().handle(application=['creme_core', 'persons', 'commercial'])
        self.assertEqual(3, ActType.objects.count())

        rtypes = RelationType.objects.filter(pk=REL_SUB_OPPORT_LINKED)
        self.assertEqual(1, len(rtypes))

        rtype = rtypes[0]
        get_ct = ContentType.objects.get_for_model
        self.assertEqual([get_ct(Opportunity).id], [ct.id for ct in rtype.subject_ctypes.all()])
        self.assertEqual([get_ct(Act).id],         [ct.id for ct in rtype.object_ctypes.all()])

        rtypes = RelationType.objects.filter(pk=REL_SUB_COMPLETE_GOAL)
        self.assertEqual(1, len(rtypes))
        self.assertEqual([get_ct(Act).id], [ct.id for ct in rtypes[0].object_ctypes.all()])


class LoggedTestCase(TestCase):
    def setUp(self):
        self.password = 'test'

        user = User.objects.create(username='Bilbo', is_superuser=True)
        user.set_password(self.password)
        user.save()
        self.user = user

        logged = self.client.login(username=user.username, password=self.password)
        self.assert_(logged, 'Not logged in')

    def assertNoFormError(self, response):
        try:
            errors = response.context['form'].errors
        except Exception, e:
            pass
        else:
            if errors:
                self.fail(errors)

    def _create_segment(self):
        #TODO: use a true segment creation view ??
        ptype = CremePropertyType.create('commercial-_prop_unitest', 'Segment type')
        return MarketSegment.objects.create(name='Segment#1', property_type=ptype)


class MarketSegmentTestCase(LoggedTestCase):
    def test_create(self):
        response = self.client.get('/commercial/market_segment/add')
        self.assertEqual(200, response.status_code)

        name = 'Industry'
        response = self.client.post('/commercial/market_segment/add', data={'name': name})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            segment = MarketSegment.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        self.assert_(name in segment.property_type.text)

    def test_listview(self):
        response = self.client.get('/commercial/market_segments')
        self.assertEqual(200, response.status_code)

    #TODO: segment can be deleted ??
    #def test_segment_delete(self):
        #strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        #segment = MarketSegment.objects.create(name='Industry', strategy=strategy)
        #self.assertEqual(1, len(strategy.segments.all()))

        #response = self.client.post('/commercial/segment/delete', data={'id': segment.id}, follow=True)
        #self.assertEqual(response.status_code, 200)
        #self.assertEqual(0, len(strategy.segments.all()))


class StrategyTestCase(LoggedTestCase):
    def test_strategy_create(self):
        response = self.client.get('/commercial/strategy/add')
        self.assertEqual(response.status_code, 200)

        name = 'Strat#1'
        response = self.client.post('/commercial/strategy/add', follow=True,
                                    data={
                                            'user':      self.user.pk,
                                            'name':      name,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)
        self.assert_(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)

        strategies = Strategy.objects.all()
        self.assertEqual(1, len(strategies))
        self.assertEqual(name, strategies[0].name)

    def test_strategy_edit(self):
        name = 'Strat#1'
        strategy = Strategy.objects.create(user=self.user, name=name)

        response = self.client.get('/commercial/strategy/edit/%s' % strategy.id)
        self.assertEqual(response.status_code, 200)

        name += '_edited'
        response = self.client.post('/commercial/strategy/edit/%s' % strategy.id, follow=True,
                                    data={
                                            'user': self.user.pk,
                                            'name': name,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        strategy = Strategy.objects.get(pk=strategy.pk)
        self.assertEqual(name, strategy.name)

    def test_segment_add(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        response = self.client.get('/commercial/strategy/%s/add/segment/' % strategy.id)
        self.assertEqual(200, response.status_code)

        name = 'Industry'
        product = 'Description about product'
        place = 'Description about place'
        price = 'Description about price'
        promotion = 'Description about promotion'
        response = self.client.post('/commercial/strategy/%s/add/segment/' % strategy.id,
                                    data={
                                            'name':      name,
                                            'product':   product,
                                            'place':     place,
                                            'price':     price,
                                            'promotion': promotion,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        segment_info = strategy.segment_info.all()
        self.assertEqual(1, len(segment_info))

        description = segment_info[0]
        self.assertEqual(name,      description.segment.name)
        self.assertEqual(product,   description.product)
        self.assertEqual(place,     description.place)
        self.assertEqual(price,     description.price)
        self.assertEqual(promotion, description.promotion)
        self.assert_(name in description.segment.property_type.text)

    def _create_segment_desc(self, strategy, name):
        self.client.post('/commercial/strategy/%s/add/segment/' % strategy.id, data={'name': name})
        return strategy.segment_info.get(segment__name=name)

    def test_segment_link(self):
        strategy01 = Strategy.objects.create(user=self.user, name='Strat#1')
        industry = self._create_segment_desc(strategy01, 'Industry')
        self.assertEqual(1, strategy01.segment_info.count())

        strategy02 = Strategy.objects.create(user=self.user, name='Strat#2')
        self.assertEqual(0,   strategy02.segment_info.count())

        response = self.client.get('/commercial/strategy/%s/link/segment/' % strategy02.id)
        self.assertEqual(200, response.status_code)

        product = 'Description about product'
        place = 'Description about place'
        price = 'Description about price'
        promotion = 'Description about promotion'
        response = self.client.post('/commercial/strategy/%s/link/segment/' % strategy02.id,
                                    data={
                                            'segment':   industry.id,
                                            'product':   product,
                                            'place':     place,
                                            'price':     price,
                                            'promotion': promotion,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        seginfo = strategy02.segment_info.all()
        self.assertEqual(1, len(seginfo))

        description = seginfo[0]
        self.assertEqual(industry.segment_id, description.segment_id)
        self.assertEqual(product,             description.product)
        self.assertEqual(place,               description.place)
        self.assertEqual(price,               description.price)
        self.assertEqual(promotion,           description.promotion)

    def test_segment_edit(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        name = 'Industry'
        segment_desc = self._create_segment_desc(strategy, name)

        response = self.client.get('/commercial/strategy/%s/segment/edit/%s/' % (strategy.id, segment_desc.id))
        self.assertEqual(200, response.status_code)

        name += ' of Cheese'
        product = 'Description about product'
        place = 'Description about place'
        price = 'Description about price'
        promotion = 'Description about promotion'
        response = self.client.post('/commercial/strategy/%s/segment/edit/%s/' % (strategy.id, segment_desc.id),
                                    data={
                                            'name':      name,
                                            'product':   product,
                                            'place':     place,
                                            'price':     price,
                                            'promotion': promotion,
                                        }
                                   )
        self.assertEqual(200, response.status_code)

        descriptions = strategy.segment_info.all()
        self.assertEqual(1, len(descriptions))

        description = descriptions[0]
        self.assertEqual(name,      description.segment.name)
        self.assertEqual(product,   description.product)
        self.assertEqual(place,     description.place)
        self.assertEqual(price,     description.price)
        self.assertEqual(promotion, description.promotion)
        self.assert_(name in description.segment.property_type.text)

    def test_asset_add(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        response = self.client.get('/commercial/strategy/%s/add/asset/' % strategy.id)
        self.assertEqual(200, response.status_code)

        name = 'Size'
        response = self.client.post('/commercial/strategy/%s/add/asset/' % strategy.id,
                                    data={'name': name}
                                   )
        self.assertEqual(200, response.status_code)

        assets = strategy.assets.all()
        self.assertEqual(1, len(assets))
        self.assertEqual(name, assets[0].name)

    def test_asset_edit(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        name = 'Size'
        asset = CommercialAsset.objects.create(name=name, strategy=strategy)

        response = self.client.get('/commercial/asset/edit/%s/' % asset.id)
        self.assertEqual(200, response.status_code)

        name += '_edited'
        response = self.client.post('/commercial/asset/edit/%s/' % asset.id,
                                    data={'name': name}
                                   )
        self.assertEqual(200, response.status_code)

        asset = CommercialAsset.objects.get(pk=asset.pk)
        self.assertEqual(name,        asset.name)
        self.assertEqual(strategy.id, asset.strategy_id)

    def test_asset_delete(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        asset = CommercialAsset.objects.create(name='Capital', strategy=strategy)
        self.assertEqual(1, len(strategy.assets.all()))

        ct = ContentType.objects.get_for_model(CommercialAsset)
        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': asset.id}, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertEqual(0,   len(strategy.assets.all()))

    def test_charms_add(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        response = self.client.get('/commercial/strategy/%s/add/charm/' % strategy.id)
        self.assertEqual(200, response.status_code)

        name = 'Size'
        response = self.client.post('/commercial/strategy/%s/add/charm/' % strategy.id,
                                    data={'name': name}
                                   )
        self.assertEqual(200, response.status_code)

        charms = strategy.charms.all()
        self.assertEqual(1,    len(charms))
        self.assertEqual(name, charms[0].name)

    def test_charm_edit(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        name = 'Size'
        charm = MarketSegmentCharm.objects.create(name=name, strategy=strategy)

        response = self.client.get('/commercial/charm/edit/%s/' % charm.id)
        self.assertEqual(200, response.status_code)

        name += '_edited'
        response = self.client.post('/commercial/charm/edit/%s/' % charm.id,
                                    data={'name': name}
                                   )
        self.assertEqual(200, response.status_code)

        charm = MarketSegmentCharm.objects.get(pk=charm.pk)
        self.assertEqual(name,        charm.name)
        self.assertEqual(strategy.id, charm.strategy_id)

    def test_charm_delete(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        charm = MarketSegmentCharm.objects.create(name='Dollars', strategy=strategy)
        self.assertEqual(1, len(strategy.charms.all()))

        ct = ContentType.objects.get_for_model(MarketSegmentCharm)
        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': charm.id}, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, len(strategy.charms.all()))

    def test_evaluated_orga(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        orga     = Organisation.objects.create(user=self.user, name='Nerv')

        response = self.client.get('/commercial/strategy/%s/add/organisation/' % strategy.id)
        self.assertEqual(200, response.status_code)

        response = self.client.post('/commercial/strategy/%s/add/organisation/' % strategy.id,
                                    data={'organisations': orga.id})
        self.assertEqual(200, response.status_code)

        orgas = strategy.evaluated_orgas.all()
        self.assertEqual(1,       len(orgas))
        self.assertEqual(orga.pk, orgas[0].pk)

        self.assertEqual(200, self.client.get('/commercial/strategy/%s/organisation/%s/evaluation' % (strategy.id, orga.id)).status_code)
        self.assertEqual(200, self.client.get('/commercial/strategy/%s/organisation/%s/synthesis'  % (strategy.id, orga.id)).status_code)

        response = self.client.post('/commercial/strategy/%s/organisation/delete' % strategy.id,
                                    data={'id': orga.id}, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertEqual(0,   len(strategy.evaluated_orgas.all()))

    def _set_asset_score(self, strategy, orga, asset, segment_desc, score):
        response = self.client.post('/commercial/strategy/%s/set_asset_score' % strategy.id,
                                    data={
                                            'model_id':        asset.id,
                                            'segment_desc_id': segment_desc.id,
                                            'orga_id':         orga.id,
                                            'score':           score,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

    def test_set_asset_score01(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        segment_desc  = self._create_segment_desc(strategy, 'Industry')
        asset    = CommercialAsset.objects.create(name='Capital', strategy=strategy)

        orga = Organisation.objects.create(user=self.user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self.assertEqual(1, strategy.get_asset_score(orga, asset, segment_desc))
        self.assertEqual([(1, 3)], strategy.get_assets_totals(orga))

        score = 3
        self._set_asset_score(strategy, orga, asset, segment_desc, score)

        strategy = Strategy.objects.get(pk=strategy.pk) #refresh object (cache....)
        self.assertEqual(score, strategy.get_asset_score(orga, asset, segment_desc))
        self.assertEqual([(score, 3)], strategy.get_assets_totals(orga))

    def test_set_asset_score02(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        segment_desc01  = self._create_segment_desc(strategy, 'Industry')
        segment_desc02  = self._create_segment_desc(strategy, 'People')

        create_asset = CommercialAsset.objects.create
        asset01 = create_asset(name='Capital', strategy=strategy)
        asset02 = create_asset(name='Size', strategy=strategy)

        orga = Organisation.objects.create(user=self.user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self.assertEqual(1, strategy.get_asset_score(orga, asset01, segment_desc01))
        self.assertEqual(1, strategy.get_asset_score(orga, asset01, segment_desc02))
        self.assertEqual(1, strategy.get_asset_score(orga, asset02, segment_desc01))
        self.assertEqual(1, strategy.get_asset_score(orga, asset02, segment_desc02))

        self.assertEqual([(2, 3), (2, 3)], strategy.get_assets_totals(orga))

        score11 = 1; score12 = 4; score21 = 3; score22 = 2
        self._set_asset_score(strategy, orga, asset01, segment_desc01, score11)
        self._set_asset_score(strategy, orga, asset01, segment_desc02, score12)
        self._set_asset_score(strategy, orga, asset02, segment_desc01, score21)
        self._set_asset_score(strategy, orga, asset02, segment_desc02, score22)

        strategy = Strategy.objects.get(pk=strategy.pk) #refresh object (cache....)
        self.assertEqual(score11, strategy.get_asset_score(orga, asset01, segment_desc01))
        self.assertEqual(score12, strategy.get_asset_score(orga, asset01, segment_desc02))
        self.assertEqual(score21, strategy.get_asset_score(orga, asset02, segment_desc01))
        self.assertEqual(score22, strategy.get_asset_score(orga, asset02, segment_desc02))

        self.assertEqual([(score11 + score21, 1), (score12 + score22, 3)], strategy.get_assets_totals(orga))

    def _set_charm_score(self, strategy, orga, charm, segment_desc, score):
        response = self.client.post('/commercial/strategy/%s/set_charm_score' % strategy.id,
                                    data={
                                            'model_id':        charm.id,
                                            'segment_desc_id': segment_desc.id,
                                            'orga_id':         orga.id,
                                            'score':           score,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

    def test_set_charm_score01(self):
        strategy     = Strategy.objects.create(user=self.user, name='Strat#1')
        segment_desc = self._create_segment_desc(strategy, 'Industry')
        charm        = MarketSegmentCharm.objects.create(name='Celebrity', strategy=strategy)

        orga = Organisation.objects.create(user=self.user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self.assertEqual(1, strategy.get_charm_score(orga, charm, segment_desc))
        self.assertEqual([(1, 3)], strategy.get_charms_totals(orga))

        score = 3
        self._set_charm_score(strategy, orga, charm, segment_desc, score)

        strategy = Strategy.objects.get(pk=strategy.pk) #refresh object (cache....)
        self.assertEqual(score, strategy.get_charm_score(orga, charm, segment_desc))
        self.assertEqual([(score, 3)], strategy.get_charms_totals(orga))

    def test_set_charm_score02(self):
        strategy  = Strategy.objects.create(user=self.user, name='Strat#1')
        segment_desc01 = self._create_segment_desc(strategy, 'Industry')
        segment_desc02 = self._create_segment_desc(strategy, 'People')

        create_charm = MarketSegmentCharm.objects.create
        charm01 = create_charm(name='Money', strategy=strategy)
        charm02 = create_charm(name='Celebrity', strategy=strategy)

        orga = Organisation.objects.create(user=self.user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self.assertEqual(1, strategy.get_charm_score(orga, charm01, segment_desc01))
        self.assertEqual(1, strategy.get_charm_score(orga, charm01, segment_desc02))
        self.assertEqual(1, strategy.get_charm_score(orga, charm02, segment_desc01))
        self.assertEqual(1, strategy.get_charm_score(orga, charm02, segment_desc02))

        self.assertEqual([(2, 3), (2, 3)], strategy.get_charms_totals(orga))

        score11 = 1; score12 = 4; score21 = 3; score22 = 2
        self._set_charm_score(strategy, orga, charm01, segment_desc01, score11)
        self._set_charm_score(strategy, orga, charm01, segment_desc02, score12)
        self._set_charm_score(strategy, orga, charm02, segment_desc01, score21)
        self._set_charm_score(strategy, orga, charm02, segment_desc02, score22)

        strategy = Strategy.objects.get(pk=strategy.pk) #refresh object (cache....)
        self.assertEqual(score11, strategy.get_charm_score(orga, charm01, segment_desc01))
        self.assertEqual(score12, strategy.get_charm_score(orga, charm01, segment_desc02))
        self.assertEqual(score21, strategy.get_charm_score(orga, charm02, segment_desc01))
        self.assertEqual(score22, strategy.get_charm_score(orga, charm02, segment_desc02))

        self.assertEqual([(score11 + score21, 1), (score12 + score22, 3)], strategy.get_charms_totals(orga))

    def _set_segment_category(self, strategy, segment_desc, orga, category):
        response = self.client.post('/commercial/strategy/%s/set_segment_cat' % strategy.id,
                                    data={
                                            'segment_desc_id': segment_desc.id,
                                            'orga_id':         orga.id,
                                            'category':        category,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

    def test_segments_categories(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        industry    = self._create_segment_desc(strategy, 'Industry')
        individual  = self._create_segment_desc(strategy, 'Individual')
        community   = self._create_segment_desc(strategy, 'Community')
        association = self._create_segment_desc(strategy, 'Association')

        create_asset = CommercialAsset.objects.create
        asset01 = create_asset(name='Capital', strategy=strategy)
        asset02 = create_asset(name='Size', strategy=strategy)

        create_charm = MarketSegmentCharm.objects.create
        charm01 = create_charm(name='Money', strategy=strategy)
        charm02 = create_charm(name='Celebrity', strategy=strategy)

        orga = Organisation.objects.create(user=self.user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self._set_asset_score(strategy, orga, asset01, industry, 4)
        self._set_asset_score(strategy, orga, asset02, industry, 3)
        self._set_charm_score(strategy, orga, charm01, industry, 4)
        self._set_charm_score(strategy, orga, charm02, industry, 3)

        self._set_asset_score(strategy, orga, asset01, individual, 3)
        self._set_asset_score(strategy, orga, asset02, individual, 3)
        self._set_charm_score(strategy, orga, charm01, individual, 1)
        self._set_charm_score(strategy, orga, charm02, individual, 1)

        self._set_asset_score(strategy, orga, asset01, community, 2)
        self._set_asset_score(strategy, orga, asset02, community, 1)
        self._set_charm_score(strategy, orga, charm01, community, 3)
        self._set_charm_score(strategy, orga, charm02, community, 4)

        self.assertEqual([association.id], [segment.id for segment in strategy.get_segments_for_category(orga, 4)])
        self.assertEqual([individual.id],  [segment.id for segment in strategy.get_segments_for_category(orga, 3)])
        self.assertEqual([community.id],   [segment.id for segment in strategy.get_segments_for_category(orga, 2)])
        self.assertEqual([industry.id],    [segment.id for segment in strategy.get_segments_for_category(orga, 1)])

        self._set_segment_category(strategy, individual, orga, 4)

        strategy = Strategy.objects.get(pk=strategy.pk) #refresh object (cache....)
        self.assertEqual([], [segment.id for segment in strategy.get_segments_for_category(orga, 3)])
        self.assertEqual(set([association.id, individual.id]),
                         set(segment.id for segment in strategy.get_segments_for_category(orga, 4))
                        )
        self.assertEqual(1, MarketSegmentCategory.objects.count())

        self._set_segment_category(strategy, individual, orga, 2)

        strategy = Strategy.objects.get(pk=strategy.pk) #refresh object (cache....)
        self.assertEqual([association.id], [segment.id for segment in strategy.get_segments_for_category(orga, 4)])
        self.assertEqual([],               [segment.id for segment in strategy.get_segments_for_category(orga, 3)])
        self.assertEqual([industry.id],    [segment.id for segment in strategy.get_segments_for_category(orga, 1)])
        self.assertEqual(set([community.id, individual.id]),
                         set(segment.id for segment in strategy.get_segments_for_category(orga, 2))
                        )
        self.assertEqual(1, MarketSegmentCategory.objects.count())

        self.assertEqual(1, strategy.get_segment_category(orga, industry))
        self.assertEqual(2, strategy.get_segment_category(orga, individual))
        self.assertEqual(2, strategy.get_segment_category(orga, community))
        self.assertEqual(4, strategy.get_segment_category(orga, association))

    def test_delete01(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        self.assertEqual(1, Strategy.objects.count())

        strategy.delete()
        self.assertEqual(0, Strategy.objects.count())

    def test_delete02(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        segment_desc  = self._create_segment_desc(strategy, 'Industry')
        asset    = CommercialAsset.objects.create(name='Capital', strategy=strategy)
        charm    = MarketSegmentCharm.objects.create(name='Celebrity', strategy=strategy)

        orga = Organisation.objects.create(user=self.user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self._set_asset_score(strategy, orga, asset, segment_desc, 2)
        self._set_charm_score(strategy, orga, charm, segment_desc, 3)
        self._set_segment_category(strategy, segment_desc, orga, 2)

        self.assertEqual(1, Strategy.objects.count())
        self.assertEqual(1, MarketSegment.objects.count())
        self.assertEqual(1, MarketSegmentDescription.objects.count())
        self.assertEqual(1, CommercialAsset.objects.count())
        self.assertEqual(1, MarketSegmentCharm.objects.count())
        self.assertEqual(1, CommercialAssetScore.objects.count())
        self.assertEqual(1, MarketSegmentCharmScore.objects.count())
        self.assertEqual(1, MarketSegmentCategory.objects.count())

        strategy.delete()
        self.assertEqual(0, Strategy.objects.count())
        self.assertEqual(1, MarketSegment.objects.count())
        self.assertEqual(0, MarketSegmentDescription.objects.count())
        self.assertEqual(0, CommercialAsset.objects.count())
        self.assertEqual(0, MarketSegmentCharm.objects.count())
        self.assertEqual(0, CommercialAssetScore.objects.count())
        self.assertEqual(0, MarketSegmentCharmScore.objects.count())
        self.assertEqual(0, MarketSegmentCategory.objects.count())

    def test_segment_unlink01(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        segment_desc = self._create_segment_desc(strategy, 'People')

        self.assertEqual(1, strategy.segment_info.count())
        self.assertEqual(1, MarketSegment.objects.count())

        ct = ContentType.objects.get_for_model(MarketSegmentDescription)
        self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': segment_desc.id})
        self.assertEqual(0, strategy.segment_info.count())
        self.assertEqual(1, MarketSegment.objects.count())

    def test_segment_unlink02(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        industry   = self._create_segment_desc(strategy, 'Industry')
        individual = self._create_segment_desc(strategy, 'Individual')

        create_asset = CommercialAsset.objects.create
        asset01 = create_asset(name='Capital', strategy=strategy)
        asset02 = create_asset(name='Size', strategy=strategy)

        create_charm = MarketSegmentCharm.objects.create
        charm01 = create_charm(name='Money', strategy=strategy)
        charm02 = create_charm(name='Celebrity', strategy=strategy)

        orga = Organisation.objects.create(user=self.user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self._set_asset_score(strategy, orga, asset01, industry, 4)
        self._set_asset_score(strategy, orga, asset02, industry, 3)
        self._set_charm_score(strategy, orga, charm01, industry, 4)
        self._set_charm_score(strategy, orga, charm02, industry, 3)

        self._set_asset_score(strategy, orga, asset01, individual, 3)
        self._set_asset_score(strategy, orga, asset02, individual, 3)
        self._set_charm_score(strategy, orga, charm01, individual, 2)
        self._set_charm_score(strategy, orga, charm02, individual, 2)

        self._set_segment_category(strategy, industry,   orga, 2)
        self._set_segment_category(strategy, individual, orga, 4)

        self.assertEqual(2, MarketSegmentDescription.objects.count())
        self.assertEqual(4, CommercialAssetScore.objects.count())
        self.assertEqual(4, MarketSegmentCharmScore.objects.count())
        self.assertEqual(2, MarketSegmentCategory.objects.count())

        ct = ContentType.objects.get_for_model(MarketSegmentDescription)
        self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': industry.id})
        self.assertEqual(1, MarketSegmentDescription.objects.count())

        asset_scores = CommercialAssetScore.objects.all()
        self.assertEqual(2, len(asset_scores))
        self.assert_(set([individual.id]), set(ascore.segment_desc_id for ascore in asset_scores))

        charm_scores = MarketSegmentCharmScore.objects.all()
        self.assertEqual(2, len(charm_scores))
        self.assert_(set([individual.id]), set(cscore.segment_desc_id for cscore in charm_scores))

        cats = MarketSegmentCategory.objects.all()
        self.assertEqual(1, len(cats))
        self.assert_(set([individual.id]), set(cat.segment_desc_id for cat in cats))


class ActTestCase(LoggedTestCase):
    def test_create(self):
        response = self.client.get('/commercial/act/add')
        self.assertEqual(200, response.status_code)

        name = 'Act#1'
        atype = ActType.objects.create(title='Show')
        segment = self._create_segment()
        response = self.client.post('/commercial/act/add', follow=True,
                                    data={
                                            'user':           self.user.pk,
                                            'name':           name,
                                            'expected_sales': 1000,
                                            'start':          '2011-11-20',
                                            'due_date':       '2011-12-25',
                                            'act_type':       atype.id,
                                            'segment':        segment.id,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assert_(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)

        acts = Act.objects.all()
        self.assertEqual(1, len(acts))

        act = acts[0]
        self.assertEqual(name,     act.name)
        self.assertEqual(atype.id, act.act_type_id)

        start = act.start
        self.assertEqual(2011, start.year)
        self.assertEqual(11,   start.month)
        self.assertEqual(20,   start.day)

        due_date = act.due_date
        self.assertEqual(2011, due_date.year)
        self.assertEqual(12,   due_date.month)
        self.assertEqual(25,   due_date.day)

    def create_act(self, expected_sales=1000):
        return Act.objects.create(user=self.user, name='NAME',
                                  expected_sales=expected_sales, cost=50,
                                  goal='GOAL', start=date(2010, 11, 25),
                                  due_date=date(2011, 12, 26),
                                  act_type=ActType.objects.create(title='Show'),
                                  segment = self._create_segment(),
                                 )

    def test_edit(self):
        act = self.create_act()
        response = self.client.get('/commercial/act/edit/%s' % act.id)
        self.assertEqual(200, response.status_code)

        name = 'Act#1'
        expected_sales = 2000
        cost = 100
        goal = 'Win'
        atype = ActType.objects.create(title='Demo')
        segment = self._create_segment()
        response = self.client.post('/commercial/act/edit/%s' % act.id, follow=True,
                                    data={
                                            'user':            self.user.pk,
                                            'name':            name,
                                            'start':           '2011-11-20',
                                            'due_date':        '2011-12-25',
                                            'expected_sales':  expected_sales,
                                            'cost':            cost,
                                            'goal':            goal,
                                            'act_type':        atype.id,
                                            'segment':         segment.id,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assert_(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)

        act = Act.objects.get(pk=act.id)
        self.assertEqual(name,           act.name)
        self.assertEqual(cost,           act.cost)
        self.assertEqual(expected_sales, act.expected_sales)
        self.assertEqual(goal,           act.goal)
        self.assertEqual(atype.id,       act.act_type_id)

        start = act.start
        self.assertEqual(2011, start.year)
        self.assertEqual(11,   start.month)
        self.assertEqual(20,   start.day)

        due_date = act.due_date
        self.assertEqual(2011, due_date.year)
        self.assertEqual(12,   due_date.month)
        self.assertEqual(25,   due_date.day)

    def test_listview(self):
        PopulateCommand().handle(application=['creme_core', 'persons', 'commercial'])

        atype = ActType.objects.create(title='Show')
        segment = self._create_segment()
        create_act = Act.objects.create
        acts = [create_act(user=self.user, name='NAME_%s' % i, expected_sales=1000,
                           cost=50, goal='GOAL', act_type=atype, segment=segment,
                           start=date(2010, 11, 25), due_date=date(2011, 12, 26),
                          ) for i in xrange(1, 3)
               ]

        response = self.client.get('/commercial/acts')
        self.assertEqual(200, response.status_code)

        try:
            acts_page = response.context['entities']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(1, acts_page.number)
        self.assertEqual(2, acts_page.paginator.count)
        self.assertEqual(set(a.id for a in acts), set(o.id for o in acts_page.object_list))

    def test_detailview(self):
        act = self.create_act()
        response = self.client.get('/commercial/act/%s' % act.id)
        self.assertEqual(200, response.status_code)

    def test_add_objective01(self):
        act = self.create_act()
        response = self.client.get('/commercial/act/%s/add/objective' % act.id)
        self.assertEqual(200, response.status_code)
        self.assertEqual(0,   ActObjective.objects.count())

        name = 'Objective#1'
        counter_goal = 20
        response = self.client.post('/commercial/act/%s/add/objective' % act.id,
                                    data={
                                            'name':         name,
                                            'counter_goal': counter_goal,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        objectives = ActObjective.objects.filter(act=act.id)
        self.assertEqual(1, len(objectives))

        objective = objectives[0]
        self.assertEqual(name,         objective.name)
        self.assertEqual(act.id,       objective.act_id)
        self.assertEqual(0,            objective.counter)
        self.assertEqual(counter_goal, objective.counter_goal)
        self.assert_(objective.ctype_id is None)

        self.assertEqual(0, objective.get_count())
        self.failIf(objective.reached)

        objective.counter = counter_goal
        objective.save()
        objective = ActObjective.objects.get(pk=objective.id) #refresh cache
        self.assertEqual(counter_goal, objective.get_count())
        self.assert_(objective.reached)

    def test_add_objective02(self):
        act = self.create_act()

        response = self.client.get('/commercial/act/%s/add/objective' % act.id)
        self.assertEqual(200, response.status_code)
        self.assertEqual(0,   ActObjective.objects.count())

        name  = 'Objective#2'
        counter_goal = 2
        ct_id = ContentType.objects.get_for_model(Organisation).id
        response = self.client.post('/commercial/act/%s/add/objective' % act.id,
                                    data={
                                            'name':         name,
                                            'ctype':        ct_id,
                                            'counter_goal': counter_goal,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)
        self.assertEqual(1, ActObjective.objects.count())

        objectives = ActObjective.objects.filter(act=act.id)
        self.assertEqual(1, len(objectives))

        objective = objectives[0]
        self.assertEqual(name,         objective.name)
        self.assertEqual(act.id,       objective.act_id)
        self.assertEqual(0,            objective.counter)
        self.assertEqual(counter_goal, objective.counter_goal)
        self.assertEqual(ct_id,        objective.ctype_id)

    def test_add_objectives_from_pattern01(self):
        act = self.create_act(expected_sales=20000)
        pattern = ActObjectivePattern.objects.create(user=self.user, name='Mr Pattern',
                                                     average_sales=5000, #NB: 20000 / 5000 => Ratio = 4
                                                     segment=act.segment,
                                                    )

        ct_contact = ContentType.objects.get_for_model(Contact)
        ct_orga    = ContentType.objects.get_for_model(Organisation)
        create_component = ActObjectivePatternComponent.objects.create
        root01  = create_component(name='Root01',   success_rate=20,  pattern=pattern, ctype=ct_contact)
        root02  = create_component(name='Root02',   success_rate=50,  pattern=pattern)
        child01 = create_component(name='Child 01', success_rate=33, pattern=pattern, parent=root01)
        child02 = create_component(name='Child 02', success_rate=10,  pattern=pattern, parent=root01, ctype=ct_orga)

        response = self.client.get('/commercial/act/%s/add/objectives_from_pattern' % act.id)
        self.assertEqual(200, response.status_code)

        response = self.client.post('/commercial/act/%s/add/objectives_from_pattern' % act.id,
                                    data={'pattern': pattern.id}
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertEqual(5,   ActObjective.objects.filter(act=act.id).count())

        try:
            objective01 = act.objectives.get(name='Root01')
            objective02 = act.objectives.get(name='Root02')
            objective11 = act.objectives.get(name='Child 01')
            objective12 = act.objectives.get(name='Child 02')
            objective00 = act.objectives.exclude(pk__in=[objective01.id, objective02.id, objective11.id, objective12.id,])[0]
        except Exception, e:
            self.fail(str(e))

        self.assert_(all(o.counter == 0 for o in [objective00, objective01, objective02, objective11, objective12]))
        self.assert_(objective00.ctype_id is None)
        self.assertEqual(ct_contact.id, objective01.ctype_id)
        self.assertEqual(ct_orga.id,    objective12.ctype_id)
        self.assert_(objective02.ctype_id is None)
        self.assert_(objective11.ctype_id is None)

        self.assertEqual(4,   objective00.counter_goal) #ratio = 4
        self.assertEqual(20,  objective01.counter_goal) # 20% -> 4  * 5
        self.assertEqual(8,   objective02.counter_goal) # 50% -> 4  * 2
        self.assertEqual(61,  objective11.counter_goal) # 33% -> 20 * 3,3
        self.assertEqual(200, objective12.counter_goal) # 10% -> 20 * 10

    def test_add_objectives_from_pattern02(self):
        act = self.create_act(expected_sales=21000)
        pattern = ActObjectivePattern.objects.create(user=self.user, name='Mr Pattern',
                                                     average_sales=5000, #NB: 21000 / 5000 => Ratio = 5
                                                     segment=act.segment,
                                                    )

        response = self.client.post('/commercial/act/%s/add/objectives_from_pattern' % act.id,
                                    data={'pattern': pattern.id}
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        objectives = ActObjective.objects.filter(act=act.id)
        self.assertEqual(1, len(objectives))
        self.assertEqual(5,   objectives[0].counter_goal)

    def test_edit_objective01(self):
        act = self.create_act()
        objective = ActObjective.objects.create(act=act, name='OBJ#1')
        self.assertEqual(1, objective.counter_goal)

        response = self.client.get('/commercial/objective/%s/edit' % objective.id)
        self.assertEqual(200, response.status_code)

        name = 'OBJ_NAME'
        counter_goal = 3
        response = self.client.post('/commercial/objective/%s/edit' % objective.id,
                                    data={
                                            'name':         name,
                                            'counter_goal': counter_goal,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        objective = ActObjective.objects.get(pk=objective.id)
        self.assertEqual(name,         objective.name)
        self.assertEqual(counter_goal, objective.counter_goal)

    def test_delete_objective01(self):
        act = self.create_act()
        objective = ActObjective.objects.create(act=act, name='OBJ#1')
        ct = ContentType.objects.get_for_model(ActObjective)

        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': objective.id})
        self.assertEqual(302, response.status_code)
        self.assertEqual(0,   ActObjective.objects.filter(pk=objective.id).count())

    def test_incr_objective_counter(self):
        act = self.create_act()
        objective = ActObjective.objects.create(act=act, name='OBJ#1')
        self.assertEqual(0, objective.counter)

        response = self.client.post('/commercial/objective/%s/incr' % objective.id, data={'diff': 1})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, ActObjective.objects.get(pk=objective.id).counter)

        response = self.client.post('/commercial/objective/%s/incr' % objective.id, data={'diff': -3})
        self.assertEqual(200, response.status_code)
        self.assertEqual(-2,  ActObjective.objects.get(pk=objective.id).counter)

    def test_count_relations(self):
        PopulateCommand().handle(application=['commercial']) #'creme_core', 'persons'
        RelationType.objects.get(pk=REL_SUB_COMPLETE_GOAL) #raise exception if error

        act = self.create_act()
        objective = ActObjective.objects.create(act=act, name='Orga counter', counter_goal=2,
                                                ctype=ContentType.objects.get_for_model(Organisation)
                                               )
        self.assertEqual(0, objective.get_count())
        self.failIf(objective.reached)

        orga01 = Organisation.objects.create(user=self.user, name='Ferraille corp')
        Relation.objects.create(subject_entity=orga01, type_id=REL_SUB_COMPLETE_GOAL, object_entity=act, user=self.user)
        objective = ActObjective.objects.get(pk=objective.id) #refresh cache
        self.assertEqual(1, objective.get_count())
        self.failIf(objective.reached)

        orga02 = Organisation.objects.create(user=self.user, name='World company')
        Relation.objects.create(subject_entity=orga02, type_id=REL_SUB_COMPLETE_GOAL, object_entity=act, user=self.user)
        objective = ActObjective.objects.get(pk=objective.id) #refresh cache
        self.assertEqual(2, objective.get_count())
        self.assert_(objective.reached)

        contact = Contact.objects.create(user=self.user, first_name='Monsieur', last_name='Ferraille')
        Relation.objects.create(subject_entity=contact, type_id=REL_SUB_COMPLETE_GOAL, object_entity=act, user=self.user)
        objective = ActObjective.objects.get(pk=objective.id) #refresh cache
        self.assertEqual(2, objective.get_count())
        self.assert_(objective.reached)

    def test_related_opportunities(self):
        PopulateCommand().handle(application=['commercial']) #'creme_core', 'persons'
        RelationType.objects.get(pk=REL_SUB_OPPORT_LINKED) #raise exception if error

        act = self.create_act()
        self.assertEqual([], act.get_related_opportunities())
        self.assertEqual(0,  act.get_made_sales())

        sales_phase = SalesPhase.objects.create(name='Foresale', description='Foresale')
        opp01 = Opportunity.objects.create(user=self.user, name='OPP01', sales_phase=sales_phase, closing_date=date.today())
        Relation.objects.create(subject_entity=opp01, type_id=REL_SUB_OPPORT_LINKED, object_entity=act, user=self.user)

        act = Act.objects.get(pk=act.id) #refresh cache
        self.assertEqual([opp01.id], [o.id for o in act.get_related_opportunities()])
        self.assertEqual(0,          act.get_made_sales())

        opp01.made_sales = 1500; opp01.save()
        self.assertEqual(1500, Act.objects.get(pk=act.id).get_made_sales())

        opp02 = Opportunity.objects.create(user=self.user, name='OPP01', sales_phase=sales_phase, closing_date=date.today(), made_sales=500)
        Relation.objects.create(subject_entity=opp02, type_id=REL_SUB_OPPORT_LINKED, object_entity=act, user=self.user)
        act  = Act.objects.get(pk=act.id) #refresh cache
        opps = act.get_related_opportunities()
        self.assertEqual(2, len(opps))
        self.assertEqual(set([opp01.id, opp02.id]), set(o.id for o in opps))
        self.assertEqual(2000, Act.objects.get(pk=act.id).get_made_sales())


class ActObjectivePatternTestCase(LoggedTestCase):
    def assertFormError(self, response):
        try:
            errors = response.context['form'].errors
        except Exception, e:
            self.fail(str(e))
        else:
            if not errors:
                self.fail('No errors')

    def test_create(self):
        response = self.client.get('/commercial/objective_pattern/add')
        self.assertEqual(200, response.status_code)

        segment = self._create_segment()
        name = 'ObjPattern#1'
        average_sales = 5000
        response = self.client.post('/commercial/objective_pattern/add', follow=True,
                                    data={
                                            'user':          self.user.pk,
                                            'name':          name,
                                            'average_sales': average_sales,
                                            'segment':       segment.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assert_(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)

        patterns = ActObjectivePattern.objects.all()
        self.assertEqual(1, len(patterns))

        pattern = patterns[0]
        self.assertEqual(name,          pattern.name)
        self.assertEqual(average_sales, pattern.average_sales)
        self.assertEqual(segment.id,    pattern.segment.id)

    def _create_pattern(self, name='ObjPattern', average_sales=1000):
        return ActObjectivePattern.objects.create(user=self.user, name=name,
                                                  average_sales=average_sales,
                                                  segment=self._create_segment(),
                                                 )

    def test_edit(self):
        name = 'ObjPattern'
        average_sales = 1000
        pattern = self._create_pattern(name, average_sales)

        response = self.client.get('/commercial/objective_pattern/edit/%s' % pattern.id)
        self.assertEqual(200, response.status_code)

        name += '_edited'
        average_sales *= 2
        segment = self._create_segment()
        response = self.client.post('/commercial/objective_pattern/edit/%s' % pattern.id,
                                    data={
                                            'user':          self.user.pk,
                                            'name':          name,
                                            'average_sales': average_sales,
                                            'segment':       segment.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(302, response.status_code)

        pattern = ActObjectivePattern.objects.get(pk=pattern.id)
        self.assertEqual(name,          pattern.name)
        self.assertEqual(average_sales, pattern.average_sales)
        self.assertEqual(segment.id,    pattern.segment.id)

    def test_listview(self):
        PopulateCommand().handle(application=['creme_core', 'persons', 'commercial'])

        create_patterns = ActObjectivePattern.objects.create
        patterns = [create_patterns(user=self.user,
                                    name='ObjPattern#%s' % i,
                                    average_sales=1000 * i,
                                    segment=self._create_segment(),
                                   ) for i in xrange(1, 4)
                   ]

        response = self.client.get('/commercial/objective_patterns')
        self.assertEqual(200, response.status_code)

        try:
            patterns_page = response.context['entities']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(1, patterns_page.number)
        self.assertEqual(3, patterns_page.paginator.count)
        self.assertEqual(set(p.id for p in patterns), set(o.id for o in patterns_page.object_list))

    def test_add_root_pattern_component01(self): #no parent component, no counted relation
        pattern  = self._create_pattern()
        response = self.client.get('/commercial/objective_pattern/%s/add_component' % pattern.id)
        self.assertEqual(200, response.status_code)

        name = 'Signed opportunities'
        response = self.client.post('/commercial/objective_pattern/%s/add_component' % pattern.id,
                                    data={
                                            'name':         name,
                                            'success_rate': 10,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        components = pattern.components.all()
        self.assertEqual(1, len(components))

        component = components[0]
        self.assertEqual(name, component.name)
        self.assert_(component.parent is None)
        self.assert_(component.ctype is None)

    def test_add_root_pattern_component02(self): #counted relation (no parent component)
        pattern = self._create_pattern()
        name = 'Called contacts'
        ct = ContentType.objects.get_for_model(Contact)
        response = self.client.post('/commercial/objective_pattern/%s/add_component' % pattern.id,
                                    data={
                                            'name':         name,
                                            'ctype':        ct.id,
                                            'success_rate': 15,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        components = pattern.components.all()
        self.assertEqual(1, len(components))

        component = components[0]
        self.assertEqual(name,  component.name)
        self.assertEqual(ct.id, component.ctype.id)

    def test_add_child_pattern_component01(self): #parent component
        pattern = self._create_pattern()
        comp01 = ActObjectivePatternComponent.objects.create(name='Signed opportunities', pattern=pattern, success_rate=50)

        response = self.client.get('/commercial/objective_pattern/component/%s/add_child' % comp01.id)
        self.assertEqual(200, response.status_code)

        name = 'Spread Vcards'
        response = self.client.post('/commercial/objective_pattern/component/%s/add_child' % comp01.id,
                                    data={
                                            'name':         name,
                                            'success_rate': 20,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        children = comp01.children.all()
        self.assertEqual(1, len(children))

        comp02 = children[0]
        self.assertEqual(name,      comp02.name)
        self.assertEqual(comp01.id, comp02.parent_id)
        self.assert_(comp02.ctype is None)

        name = 'Called contacts'
        ct   = ContentType.objects.get_for_model(Contact)
        response = self.client.post('/commercial/objective_pattern/component/%s/add_child' % comp01.id,
                                    data={
                                            'name':         name,
                                            'ctype':        ct.id,
                                            'success_rate': 60,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertEqual(2,   len(comp01.children.all()))

        try:
            comp03 = comp01.children.get(name=name)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(ct.id, comp03.ctype.id)

    def test_add_parent_pattern_component01(self):
        pattern = self._create_pattern()
        comp01 = ActObjectivePatternComponent.objects.create(name='Sent mails', pattern=pattern, success_rate=5)
        response = self.client.get('/commercial/objective_pattern/component/%s/add_parent' % comp01.id)
        self.assertEqual(200, response.status_code)

        name = 'Signed opportunities'
        success_rate = 50
        response = self.client.post('/commercial/objective_pattern/component/%s/add_parent' % comp01.id,
                                    data={
                                            'name':         name,
                                            'success_rate': success_rate,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        pattern = ActObjectivePattern.objects.get(pk=pattern.id)
        components = pattern.components.all()
        self.assertEqual(2, len(components))

        child = components[0]
        self.assertEqual(comp01.id, child.id)

        parent = components[1]
        self.assertEqual(name,            parent.name)
        self.assertEqual(success_rate,    parent.success_rate)
        self.assertEqual(None,            parent.parent_id)
        self.assertEqual(child.parent_id, parent.id)

    def test_add_parent_pattern_component02(self):
        pattern = self._create_pattern()
        comp01 = ActObjectivePatternComponent.objects.create(name='Signed opportunities', pattern=pattern, success_rate=50)
        comp02 = ActObjectivePatternComponent.objects.create(name='Spread Vcards',        pattern=pattern, success_rate=1, parent=comp01)

        name = 'Called contacts'
        ct   = ContentType.objects.get_for_model(Contact)
        response = self.client.post('/commercial/objective_pattern/component/%s/add_parent' % comp02.id,
                                    data={
                                            'name':         name,
                                            'ctype':        ct.id,
                                            'success_rate': 20,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        pattern = ActObjectivePattern.objects.get(pk=pattern.id)
        components = pattern.components.all()
        self.assertEqual(3, len(components))

        grandpa = components[0]
        self.assertEqual(comp01.id, grandpa.id)

        child = components[1]
        self.assertEqual(comp02.id, child.id)

        parent = components[2]
        self.assertEqual(name,  parent.name)
        self.assertEqual(ct.id, parent.ctype_id)

        self.assertEqual(child.parent_id,  parent.id)
        self.assertEqual(parent.parent_id, grandpa.id)

    def test_add_pattern_component_errors(self):
        pattern = self._create_pattern()
        self.assertFormError(self.client.post('/commercial/objective_pattern/%s/add_component' % pattern.id,
                                              data={
                                                    'name':         'Signed opportunities',
                                                    'success_rate': 0, #minimunm is 1
                                                   }
                                             )
                            )

        self.assertFormError(self.client.post('/commercial/objective_pattern/%s/add_component' % pattern.id,
                                              data={
                                                    'name':         'Signed opportunities',
                                                    'success_rate': 101, #maximum is 100
                                                   }
                                             )
                            )

    def test_get_component_tree(self):
        pattern = self._create_pattern()

        create_component = ActObjectivePatternComponent.objects.create
        root01  = create_component(name='Root01',   pattern=pattern,                 success_rate=1)
        root02  = create_component(name='Root02',   pattern=pattern,                 success_rate=1)
        child01 = create_component(name='Child 01', pattern=pattern, parent=root01,  success_rate=1)
        child11 = create_component(name='Child 11', pattern=pattern, parent=child01, success_rate=1)
        child12 = create_component(name='Child 12', pattern=pattern, parent=child01, success_rate=1)
        child13 = create_component(name='Child 13', pattern=pattern, parent=child01, success_rate=1)
        child02 = create_component(name='Child 02', pattern=pattern, parent=root01,  success_rate=1)
        child21 = create_component(name='Child 21', pattern=pattern, parent=child02, success_rate=1)

        comptree = pattern.get_components_tree() #TODO: test that no additionnal queries are done ???
        self.assert_(isinstance(comptree, list))
        self.assertEqual(2, len(comptree))

        rootcomp01 = comptree[0]
        self.assert_(isinstance(rootcomp01, ActObjectivePatternComponent))
        self.assertEqual(root01.id, rootcomp01.id)
        self.assertEqual(root02.id, comptree[1].id)

        children = rootcomp01.get_children()
        self.assertEqual(2, len(children))

        compchild01 = children[0]
        self.assert_(isinstance(compchild01, ActObjectivePatternComponent))
        self.assertEqual(child01.id, compchild01.id)
        self.assertEqual(3, len(compchild01.get_children()))

        self.assertEqual(1, len(children[1].get_children()))

    def test_delete_pattern_component01(self):
        pattern = self._create_pattern()
        comp01 = ActObjectivePatternComponent.objects.create(name='Signed opportunities', pattern=pattern, success_rate=20)
        ct = ContentType.objects.get_for_model(ActObjectivePatternComponent)

        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id,
                                    data={'id': comp01.id}
                                   )
        self.assertNoFormError(response)
        self.assertEqual(302, response.status_code)
        self.assertEqual(0,   ActObjectivePatternComponent.objects.filter(pk=comp01.id).count())

    def test_delete_pattern_component02(self):
        pattern = self._create_pattern()
        create_comp = ActObjectivePatternComponent.objects.create
        comp00 = create_comp(name='Signed opportunities', pattern=pattern,                success_rate=1) #NB: should not be removed
        comp01 = create_comp(name='DELETE ME',            pattern=pattern,                success_rate=1)
        comp02 = create_comp(name='Will be orphaned01',   pattern=pattern, parent=comp01, success_rate=1)
        comp03 = create_comp(name='Will be orphaned02',   pattern=pattern, parent=comp01, success_rate=1)
        comp04 = create_comp(name='Will be orphaned03',   pattern=pattern, parent=comp02, success_rate=1)
        comp05 = create_comp(name='Smiles done',          pattern=pattern,                success_rate=1) #NB: should not be removed
        comp06 = create_comp(name='Stand by me',          pattern=pattern, parent=comp05, success_rate=1) #NB: should not be removed

        ct = ContentType.objects.get_for_model(ActObjectivePatternComponent)
        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': comp01.id})
        self.assertNoFormError(response)
        self.assertEqual(302, response.status_code)

        remaining_ids = pattern.components.all().values_list('id', flat=True)
        self.assertEqual(3, len(remaining_ids))
        self.assertEqual(set([comp00.id, comp05.id, comp06.id]), set(remaining_ids))

#TODO: (tests SellByRelation)
