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


class LoggedTestCase(TestCase):
    def setUp(self):
        self.password = 'test'

        user = User.objects.create(username='Bilbo', is_superuser=True)
        user.set_password(self.password)
        user.save()
        self.user = user

        logged = self.client.login(username=user.username, password=self.password)
        self.assert_(logged, 'Not logged in')


class StrategyTestCase(LoggedTestCase):
    def test_strategy_create(self):
        response = self.client.get('/commercial/strategy/add')
        self.assertEqual(response.status_code, 200)

        name = 'Strat#1'
        response = self.client.post('/commercial/strategy/add', follow=True,
                                    data={
                                            'user': self.user.pk,
                                            'name': name,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)
        self.assert_(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)

        strategies = Strategy.objects.all()
        self.assertEqual(1, len(strategies))

        strategy = strategies[0]
        self.assertEqual(name, strategy.name)

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
                                         })
        self.assertEqual(response.status_code, 200)

        strategy = Strategy.objects.get(pk=strategy.pk)
        self.assertEqual(name, strategy.name)

    def test_segment_add(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        response = self.client.get('/commercial/strategy/%s/add/segment/' % strategy.id)
        self.assertEqual(response.status_code, 200)

        name = 'Industry'
        response = self.client.post('/commercial/strategy/%s/add/segment/' % strategy.id,
                                    data={'name': name})
        self.assertEqual(response.status_code, 200)

        segments = strategy.segments.all()
        self.assertEqual(1,    len(segments))
        self.assertEqual(name, segments[0].name)

    def test_segment_edit(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        name = 'Industry'
        segment = MarketSegment.objects.create(name=name, strategy=strategy)

        response = self.client.get('/commercial/segment/edit/%s/' % segment.id)
        self.assertEqual(response.status_code, 200)

        name += 'of Cheese'
        response = self.client.post('/commercial/segment/edit/%s/' % segment.id,
                                    data={'name': name})
        self.assertEqual(response.status_code, 200)

        segment = MarketSegment.objects.get(pk=segment.pk)
        self.assertEqual(name,        segment.name)
        self.assertEqual(strategy.id, segment.strategy_id)

    def test_segment_delete(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        segment = MarketSegment.objects.create(name='Industry', strategy=strategy)
        self.assertEqual(1, len(strategy.segments.all()))

        response = self.client.post('/commercial/segment/delete', data={'id': segment.id}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(0, len(strategy.segments.all()))

    def test_asset_add(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        response = self.client.get('/commercial/strategy/%s/add/asset/' % strategy.id)
        self.assertEqual(response.status_code, 200)

        name = 'Size'
        response = self.client.post('/commercial/strategy/%s/add/asset/' % strategy.id,
                                    data={'name': name})
        self.assertEqual(response.status_code, 200)

        assets = strategy.assets.all()
        self.assertEqual(1, len(assets))
        self.assertEqual(name, assets[0].name)

    def test_asset_edit(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        name = 'Size'
        asset = CommercialAsset.objects.create(name=name, strategy=strategy)

        response = self.client.get('/commercial/asset/edit/%s/' % asset.id)
        self.assertEqual(response.status_code, 200)

        name += '_edited'
        response = self.client.post('/commercial/asset/edit/%s/' % asset.id,
                                    data={'name': name})
        self.assertEqual(response.status_code, 200)

        asset = CommercialAsset.objects.get(pk=asset.pk)
        self.assertEqual(name,        asset.name)
        self.assertEqual(strategy.id, asset.strategy_id)

    def test_asset_delete(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        asset = CommercialAsset.objects.create(name='Capital', strategy=strategy)
        self.assertEqual(1, len(strategy.assets.all()))

        response = self.client.post('/commercial/asset/delete', data={'id': asset.id}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(0, len(strategy.assets.all()))

    def test_charms_add(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        response = self.client.get('/commercial/strategy/%s/add/charm/' % strategy.id)
        self.assertEqual(response.status_code, 200)

        name = 'Size'
        response = self.client.post('/commercial/strategy/%s/add/charm/' % strategy.id,
                                    data={'name': name})
        self.assertEqual(response.status_code, 200)

        charms = strategy.charms.all()
        self.assertEqual(1,    len(charms))
        self.assertEqual(name, charms[0].name)

    def test_charm_edit(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        name = 'Size'
        charm = MarketSegmentCharm.objects.create(name=name, strategy=strategy)

        response = self.client.get('/commercial/charm/edit/%s/' % charm.id)
        self.assertEqual(response.status_code, 200)

        name += '_edited'
        response = self.client.post('/commercial/charm/edit/%s/' % charm.id,
                                    data={'name': name})
        self.assertEqual(response.status_code, 200)

        charm = MarketSegmentCharm.objects.get(pk=charm.pk)
        self.assertEqual(name,        charm.name)
        self.assertEqual(strategy.id, charm.strategy_id)

    def test_charm_delete(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        charm = MarketSegmentCharm.objects.create(name='Dollars', strategy=strategy)
        self.assertEqual(1, len(strategy.charms.all()))

        response = self.client.post('/commercial/charm/delete', data={'id': charm.id}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(0, len(strategy.charms.all()))

    def test_evaluated_orga(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        orga     = Organisation.objects.create(user=self.user, name='Nerv')

        response = self.client.get('/commercial/strategy/%s/add/organisation/' % strategy.id)
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/commercial/strategy/%s/add/organisation/' % strategy.id,
                                    data={'organisations': orga.id})
        self.assertEqual(response.status_code, 200)

        orgas = strategy.evaluated_orgas.all()
        self.assertEqual(1,       len(orgas))
        self.assertEqual(orga.pk, orgas[0].pk)

        self.assertEqual(200, self.client.get('/commercial/strategy/%s/organisation/%s/evaluation' % (strategy.id, orga.id)).status_code)
        self.assertEqual(200, self.client.get('/commercial/strategy/%s/organisation/%s/synthesis'  % (strategy.id, orga.id)).status_code)

        response = self.client.post('/commercial/strategy/%s/organisation/delete' % strategy.id,
                                    data={'id': orga.id}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(0, len(strategy.evaluated_orgas.all()))

    def _set_asset_score(self, strategy, orga, asset, segment, score):
        response = self.client.post('/commercial/strategy/%s/set_asset_score' % strategy.id,
                                    data={
                                            'model_id':   asset.id,
                                            'segment_id': segment.id,
                                            'orga_id':    orga.id,
                                            'score':      score,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

    def test_set_asset_score01(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        segment  = MarketSegment.objects.create(name='Industry', strategy=strategy)
        asset    = CommercialAsset.objects.create(name='Capital', strategy=strategy)

        orga = Organisation.objects.create(user=self.user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self.assertEqual(1, strategy.get_asset_score(orga, asset, segment))
        self.assertEqual([(1, 3)], strategy.get_assets_totals(orga))

        score = 3
        self._set_asset_score(strategy, orga, asset, segment, score)

        strategy = Strategy.objects.get(pk=strategy.pk) #refresh object (cache....)
        self.assertEqual(score, strategy.get_asset_score(orga, asset, segment))
        self.assertEqual([(score, 3)], strategy.get_assets_totals(orga))

    def test_set_asset_score02(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        create_segment = MarketSegment.objects.create
        segment01 = create_segment(name='Industry', strategy=strategy)
        segment02 = create_segment(name='People', strategy=strategy)

        create_asset = CommercialAsset.objects.create
        asset01 = create_asset(name='Capital', strategy=strategy)
        asset02 = create_asset(name='Size', strategy=strategy)

        orga = Organisation.objects.create(user=self.user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self.assertEqual(1, strategy.get_asset_score(orga, asset01, segment01))
        self.assertEqual(1, strategy.get_asset_score(orga, asset01, segment02))
        self.assertEqual(1, strategy.get_asset_score(orga, asset02, segment01))
        self.assertEqual(1, strategy.get_asset_score(orga, asset02, segment02))

        self.assertEqual([(2, 3), (2, 3)], strategy.get_assets_totals(orga))

        score11 = 1; score12 = 4; score21 = 3; score22 = 2
        self._set_asset_score(strategy, orga, asset01, segment01, score11)
        self._set_asset_score(strategy, orga, asset01, segment02, score12)
        self._set_asset_score(strategy, orga, asset02, segment01, score21)
        self._set_asset_score(strategy, orga, asset02, segment02, score22)

        strategy = Strategy.objects.get(pk=strategy.pk) #refresh object (cache....)
        self.assertEqual(score11, strategy.get_asset_score(orga, asset01, segment01))
        self.assertEqual(score12, strategy.get_asset_score(orga, asset01, segment02))
        self.assertEqual(score21, strategy.get_asset_score(orga, asset02, segment01))
        self.assertEqual(score22, strategy.get_asset_score(orga, asset02, segment02))

        self.assertEqual([(score11 + score21, 1), (score12 + score22, 3)], strategy.get_assets_totals(orga))

    def _set_charm_score(self, strategy, orga, charm, segment, score):
        response = self.client.post('/commercial/strategy/%s/set_charm_score' % strategy.id,
                                    data={
                                            'model_id':   charm.id,
                                            'segment_id': segment.id,
                                            'orga_id':    orga.id,
                                            'score':      score,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

    def test_set_charm_score01(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        segment  = MarketSegment.objects.create(name='Industry', strategy=strategy)
        charm    = MarketSegmentCharm.objects.create(name='Celebrity', strategy=strategy)

        orga = Organisation.objects.create(user=self.user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self.assertEqual(1, strategy.get_charm_score(orga, charm, segment))
        self.assertEqual([(1, 3)], strategy.get_charms_totals(orga))

        score = 3
        self._set_charm_score(strategy, orga, charm, segment, score)

        strategy = Strategy.objects.get(pk=strategy.pk) #refresh object (cache....)
        self.assertEqual(score, strategy.get_charm_score(orga, charm, segment))
        self.assertEqual([(score, 3)], strategy.get_charms_totals(orga))

    def test_set_charm_score02(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        create_segment = MarketSegment.objects.create
        segment01 = create_segment(name='Industry', strategy=strategy)
        segment02 = create_segment(name='People', strategy=strategy)

        create_charm = MarketSegmentCharm.objects.create
        charm01 = create_charm(name='Money', strategy=strategy)
        charm02 = create_charm(name='Celebrity', strategy=strategy)

        orga = Organisation.objects.create(user=self.user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self.assertEqual(1, strategy.get_charm_score(orga, charm01, segment01))
        self.assertEqual(1, strategy.get_charm_score(orga, charm01, segment02))
        self.assertEqual(1, strategy.get_charm_score(orga, charm02, segment01))
        self.assertEqual(1, strategy.get_charm_score(orga, charm02, segment02))

        self.assertEqual([(2, 3), (2, 3)], strategy.get_charms_totals(orga))

        score11 = 1; score12 = 4; score21 = 3; score22 = 2
        self._set_charm_score(strategy, orga, charm01, segment01, score11)
        self._set_charm_score(strategy, orga, charm01, segment02, score12)
        self._set_charm_score(strategy, orga, charm02, segment01, score21)
        self._set_charm_score(strategy, orga, charm02, segment02, score22)

        strategy = Strategy.objects.get(pk=strategy.pk) #refresh object (cache....)
        self.assertEqual(score11, strategy.get_charm_score(orga, charm01, segment01))
        self.assertEqual(score12, strategy.get_charm_score(orga, charm01, segment02))
        self.assertEqual(score21, strategy.get_charm_score(orga, charm02, segment01))
        self.assertEqual(score22, strategy.get_charm_score(orga, charm02, segment02))

        self.assertEqual([(score11 + score21, 1), (score12 + score22, 3)], strategy.get_charms_totals(orga))

    def test_delete01(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        self.assertEqual(1, Strategy.objects.count())

        strategy.delete()
        self.assertEqual(0, Strategy.objects.count())

    def test_delete02(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        segment  = MarketSegment.objects.create(name='Industry', strategy=strategy)
        asset    = CommercialAsset.objects.create(name='Capital', strategy=strategy)
        charm    = MarketSegmentCharm.objects.create(name='Celebrity', strategy=strategy)

        orga = Organisation.objects.create(user=self.user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self._set_asset_score(strategy, orga, asset, segment, 2)
        self._set_charm_score(strategy, orga, charm, segment, 3)

        self.assertEqual(1, Strategy.objects.count())
        self.assertEqual(1, MarketSegment.objects.count())
        self.assertEqual(1, CommercialAsset.objects.count())
        self.assertEqual(1, MarketSegmentCharm.objects.count())
        self.assertEqual(1, CommercialAssetScore.objects.count())
        self.assertEqual(1, MarketSegmentCharmScore.objects.count())

        strategy.delete()
        self.assertEqual(0, Strategy.objects.count())
        self.assertEqual(0, MarketSegment.objects.count())
        self.assertEqual(0, CommercialAsset.objects.count())
        self.assertEqual(0, MarketSegmentCharm.objects.count())
        self.assertEqual(0, CommercialAssetScore.objects.count())
        self.assertEqual(0, MarketSegmentCharmScore.objects.count())

    def _set_segment_category(self, strategy, segment, orga, category):
        response = self.client.post('/commercial/strategy/%s/set_segment_cat' % strategy.id,
                                    data={
                                            'segment_id': segment.id,
                                            'orga_id':    orga.id,
                                            'category':   category,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

    def test_segments_categories(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        create_segment = MarketSegment.objects.create
        industry    = create_segment(name='Industry', strategy=strategy)
        individual  = create_segment(name='Individual', strategy=strategy)
        community   = create_segment(name='Community', strategy=strategy)
        association = create_segment(name='Association', strategy=strategy)

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


class ActTestCase(LoggedTestCase):
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

    def test_create(self):
        response = self.client.get('/commercial/act/add')
        self.assertEqual(200, response.status_code)

        name = 'Act#1'
        atype = ActType.objects.create(title='Show')
        response = self.client.post('/commercial/act/add', follow=True,
                                    data={
                                            'user':     self.user.pk,
                                            'name':     name,
                                            'start':    '2011-11-20',
                                            'due_date': '2011-12-25',
                                            'act_type': atype.id,
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

    def create_act(self):
        atype = ActType.objects.create(title='Show')
        return Act.objects.create(user=self.user, name='NAME', expected_sales=1000, cost=50,
                                 goal='GOAL', start=date(2010, 11, 25), due_date=date(2011, 12, 26),
                                 act_type=atype)

    def test_edit(self):
        act = self.create_act()
        response = self.client.get('/commercial/act/edit/%s' % act.id)
        self.assertEqual(200, response.status_code)

        name = 'Act#1'
        expected_sales = 2000
        cost = 100
        goal = 'Win'
        atype = ActType.objects.create(title='Demo')
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
        create_act = Act.objects.create
        acts = [create_act(user=self.user, name='NAME_%s' % i, expected_sales=1000,
                           cost=50, goal='GOAL', act_type=atype,
                           start=date(2010, 11, 25), due_date=date(2011, 12, 26)
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

    def assertNoFormError(self, response):
        try:
            errors = response.context['form'].errors
        except Exception, e:
            pass
        else:
            if errors:
                self.fail(errors)

    def test_add_objective01(self):
        act = self.create_act()
        response = self.client.get('/commercial/act/%s/add/custom_objective' % act.id)
        self.assertEqual(200, response.status_code)
        self.assertEqual(0,   ActObjective.objects.count())

        name = 'Objective#1'
        response = self.client.post('/commercial/act/%s/add/custom_objective' % act.id,
                                    data={'name': name})
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        self.assertEqual(1, ActObjective.objects.count())

        objectives = ActObjective.objects.filter(act=act.id)
        self.assertEqual(1, len(objectives))

        objective = objectives[0]
        self.assertEqual(name,   objective.name)
        self.assertEqual(act.id, objective.act_id)
        self.assertEqual(0,      objective.counter)
        self.failIf(objective.reached)

    def test_add_objective02(self):
        act = self.create_act()
        response = self.client.get('/commercial/act/%s/add/relation_objective' % act.id)
        self.assertEqual(200, response.status_code)
        self.assertEqual(0,   ActObjective.objects.count())

        name  = 'Objective#2'
        ct_id = ContentType.objects.get_for_model(Organisation).id
        response = self.client.post('/commercial/act/%s/add/relation_objective' % act.id,
                                    data={
                                            'name':  name,
                                            'ctype': ct_id,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)
        self.assertEqual(1, ActObjective.objects.count())

        objectives = ActObjective.objects.filter(act=act.id)
        self.assertEqual(1, len(objectives))

        objective = objectives[0]
        self.assertEqual(name,   objective.name)
        self.assertEqual(act.id, objective.act_id)
        self.assertEqual(0,      objective.counter)
        self.assertEqual(ct_id,  objective.ctype_id)

    def test_edit_objective01(self):
        act = self.create_act()
        objective = ActObjective.objects.create(act=act, name='OBJ#1')

        response = self.client.get('/commercial/objective/%s/edit' % objective.id)
        self.assertEqual(200, response.status_code)

        name = 'OBJ_NAME'
        response = self.client.post('/commercial/objective/%s/edit' % objective.id,
                                    data={
                                            'name': name
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        objective = ActObjective.objects.get(pk=objective.id)
        self.assertEqual(name, objective.name)

    def test_delete_objective01(self):
        act = self.create_act()
        objective = ActObjective.objects.create(act=act, name='OBJ#1')

        response = self.client.post('/commercial/objective/delete', data={'id': objective.id})
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
        self.assertEqual(-2, ActObjective.objects.get(pk=objective.id).counter)

    def test_reach_objective(self):
        act = self.create_act()
        objective = ActObjective.objects.create(act=act, name='OBJ#1')
        self.failIf(objective.reached)

        response = self.client.post('/commercial/objective/%s/reach' % objective.id, data={'reached': 'true'})
        self.assertEqual(200, response.status_code)
        self.assert_(ActObjective.objects.get(pk=objective.id).reached)

        response = self.client.post('/commercial/objective/%s/reach' % objective.id, data={'reached': 'false'})
        self.assertEqual(200, response.status_code)
        self.failIf(ActObjective.objects.get(pk=objective.id).reached)

    def test_count_relations(self):
        PopulateCommand().handle(application=['commercial']) #'creme_core', 'persons'
        RelationType.objects.get(pk=REL_SUB_COMPLETE_GOAL) #raise exception if error

        act = self.create_act()
        objective = ActObjective.objects.create(act=act, name='Orga counter', ctype=ContentType.objects.get_for_model(Organisation))
        self.assertEqual(0, objective.get_relations_count())

        orga01 = Organisation.objects.create(user=self.user, name='Ferraille corp')
        Relation.create(orga01, REL_SUB_COMPLETE_GOAL, act, user_id=self.user.pk)
        self.assertEqual(1, objective.get_relations_count())

        orga02 = Organisation.objects.create(user=self.user, name='World company')
        Relation.create(orga02, REL_SUB_COMPLETE_GOAL, act, user_id=self.user.pk)
        self.assertEqual(2, objective.get_relations_count())

        contact = Contact.objects.create(user=self.user, first_name='Monsieur', last_name='Ferraille')
        Relation.create(contact, REL_SUB_COMPLETE_GOAL, act, user_id=self.user.pk)
        self.assertEqual(2, objective.get_relations_count())

    def test_related_opportunities(self):
        PopulateCommand().handle(application=['commercial']) #'creme_core', 'persons'
        RelationType.objects.get(pk=REL_SUB_OPPORT_LINKED) #raise exception if error

        act = self.create_act()
        self.assertEqual([], act.get_related_opportunities())
        self.assertEqual(0,  act.get_made_sales())

        sales_phase = SalesPhase.objects.create(name='Foresale', description='Foresale')
        opp01 = Opportunity.objects.create(user=self.user, name='OPP01', sales_phase=sales_phase, closing_date=date.today())
        Relation.create(opp01, REL_SUB_OPPORT_LINKED, act, user_id=self.user.pk)

        act = Act.objects.get(pk=act.id) #refresh cache
        self.assertEqual([opp01.id], [o.id for o in act.get_related_opportunities()])
        self.assertEqual(0,          act.get_made_sales())

        opp01.made_sales = 1500; opp01.save()
        self.assertEqual(1500, Act.objects.get(pk=act.id).get_made_sales())

        opp02 = Opportunity.objects.create(user=self.user, name='OPP01', sales_phase=sales_phase, closing_date=date.today(), made_sales=500)
        Relation.create(opp02, REL_SUB_OPPORT_LINKED, act, user_id=self.user.pk)
        act  = Act.objects.get(pk=act.id) #refresh cache
        opps = act.get_related_opportunities()
        self.assertEqual(2, len(opps))
        self.assertEqual(set([opp01.id, opp02.id]), set(o.id for o in opps))
        self.assertEqual(2000, Act.objects.get(pk=act.id).get_made_sales())

#TODO: (tests SellByRelation)
