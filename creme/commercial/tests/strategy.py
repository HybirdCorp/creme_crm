# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from persons.models import Organisation

    from commercial.models import *
    from commercial.tests.base import CommercialBaseTestCase
except Exception as e:
    print 'Error:', e


__all__ = ('StrategyTestCase',)


class StrategyTestCase(CommercialBaseTestCase):
    def test_strategy_create(self):
        url = '/commercial/strategy/add'
        self.assertEqual(200, self.client.get(url).status_code)

        name = 'Strat#1'
        response = self.client.post(url, follow=True,
                                    data={'user': self.user.pk,
                                          'name': name,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.redirect_chain)
        self.assertEqual(1, len(response.redirect_chain))

        strategies = Strategy.objects.all()
        self.assertEqual(1,    len(strategies))
        self.assertEqual(name, strategies[0].name)

    def test_strategy_edit(self):
        name = 'Strat#1'
        strategy = Strategy.objects.create(user=self.user, name=name)

        url = '/commercial/strategy/edit/%s' % strategy.id
        self.assertEqual(200, self.client.get(url).status_code)

        name += '_edited'
        response = self.client.post(url, follow=True,
                                    data={'user': self.user.pk,
                                          'name': name,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(strategy).name)

    def test_segment_add(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        url = '/commercial/strategy/%s/add/segment/' % strategy.id
        self.assertEqual(200, self.client.get(url).status_code)

        name = 'Industry'
        product = 'Description about product'
        place = 'Description about place'
        price = 'Description about price'
        promotion = 'Description about promotion'
        response = self.client.post(url, data={'name':      name,
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
        self.assertIn(name, description.segment.property_type.text)

    def _create_segment_desc(self, strategy, name):
        self.client.post('/commercial/strategy/%s/add/segment/' % strategy.id, data={'name': name})
        return strategy.segment_info.get(segment__name=name)

    def test_segment_link(self):
        strategy01 = Strategy.objects.create(user=self.user, name='Strat#1')
        industry = self._create_segment_desc(strategy01, 'Industry').segment
        self.assertEqual(1, strategy01.segment_info.count())

        strategy02 = Strategy.objects.create(user=self.user, name='Strat#2')
        self.assertEqual(0, strategy02.segment_info.count())

        url = '/commercial/strategy/%s/link/segment/' % strategy02.id
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        product = 'Description about product'
        place = 'Description about place'
        price = 'Description about price'
        promotion = 'Description about promotion'
        response = self.client.post(url, data={'segment':   industry.id,
                                               'product':   product,
                                               'place':     place,
                                               'price':     price,
                                               'promotion': promotion,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        seginfo = strategy02.segment_info.all()
        self.assertEqual(1, len(seginfo))

        description = seginfo[0]
        self.assertEqual(industry,  description.segment)
        self.assertEqual(product,   description.product)
        self.assertEqual(place,     description.place)
        self.assertEqual(price,     description.price)
        self.assertEqual(promotion, description.promotion)

    def test_segment_edit(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        name = 'Industry'
        segment_desc = self._create_segment_desc(strategy, name)

        url = '/commercial/strategy/%s/segment/edit/%s/' % (strategy.id, segment_desc.id)
        self.assertEqual(200, self.client.get(url).status_code)

        name += ' of Cheese'
        product = 'Description about product'
        place = 'Description about place'
        price = 'Description about price'
        promotion = 'Description about promotion'
        response = self.client.post(url, data={'name':      name,
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
        self.assertIn(name, description.segment.property_type.text)

    def test_asset_add(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        url = '/commercial/strategy/%s/add/asset/' % strategy.id
        self.assertEqual(200, self.client.get(url).status_code)

        name = 'Size'
        response = self.client.post(url, data={'name': name})
        self.assertEqual(200, response.status_code)

        assets = strategy.assets.all()
        self.assertEqual(1,    len(assets))
        self.assertEqual(name, assets[0].name)

    def test_asset_edit(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        name = 'Size'
        asset = CommercialAsset.objects.create(name=name, strategy=strategy)
        url = '/commercial/asset/edit/%s/' % asset.id
        self.assertEqual(200, self.client.get(url).status_code)

        name += '_edited'
        response = self.client.post(url, data={'name': name})
        self.assertEqual(200, response.status_code)

        asset = self.refresh(asset)
        self.assertEqual(name,     asset.name)
        self.assertEqual(strategy, asset.strategy)

    def test_asset_delete(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        asset = CommercialAsset.objects.create(name='Capital', strategy=strategy)
        self.assertEqual(1, strategy.assets.count())

        ct = ContentType.objects.get_for_model(CommercialAsset)
        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id,
                                    data={'id': asset.id}, follow=True
                                   )
        self.assertEqual(200, response.status_code)
        self.assertEqual(0,   strategy.assets.count())

    def test_charms_add(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        url = '/commercial/strategy/%s/add/charm/' % strategy.id
        self.assertEqual(200, self.client.get(url).status_code)

        name = 'Size'
        response = self.client.post(url, data={'name': name})
        self.assertEqual(200, response.status_code)

        charms = strategy.charms.all()
        self.assertEqual(1,    len(charms))
        self.assertEqual(name, charms[0].name)

    def test_charm_edit(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        name = 'Size'
        charm = MarketSegmentCharm.objects.create(name=name, strategy=strategy)

        url = '/commercial/charm/edit/%s/' % charm.id
        self.assertEqual(200, self.client.get(url).status_code)

        name += '_edited'
        response = self.client.post(url, data={'name': name})
        self.assertEqual(200, response.status_code)

        charm = self.refresh(charm)
        self.assertEqual(name,     charm.name)
        self.assertEqual(strategy, charm.strategy)

    def test_charm_delete(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        charm = MarketSegmentCharm.objects.create(name='Dollars', strategy=strategy)
        self.assertEqual(1, strategy.charms.count())

        ct = ContentType.objects.get_for_model(MarketSegmentCharm)
        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': charm.id}, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertEqual(0,   strategy.charms.count())

    def test_evaluated_orga(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        orga     = Organisation.objects.create(user=self.user, name='Nerv')

        url = '/commercial/strategy/%s/add/organisation/' % strategy.id
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={'organisations': orga.id})
        self.assertEqual(200, response.status_code)

        orgas = strategy.evaluated_orgas.all()
        self.assertEqual(1,       len(orgas))
        self.assertEqual(orga.pk, orgas[0].pk)

        self.assertEqual(200, self.client.get('/commercial/strategy/%s/organisation/%s/evaluation' % (strategy.id, orga.id)).status_code)
        self.assertEqual(200, self.client.get('/commercial/strategy/%s/organisation/%s/synthesis'  % (strategy.id, orga.id)).status_code)

        response = self.client.post('/commercial/strategy/%s/organisation/delete' % strategy.id,
                                    data={'id': orga.id}, follow=True
                                   )
        self.assertEqual(200, response.status_code)
        self.assertEqual(0,   strategy.evaluated_orgas.count())

    def _set_asset_score(self, strategy, orga, asset, segment_desc, score):
        response = self.client.post('/commercial/strategy/%s/set_asset_score' % strategy.id,
                                    data={'model_id':        asset.id,
                                          'segment_desc_id': segment_desc.id,
                                          'orga_id':         orga.id,
                                          'score':           score,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

    def test_set_asset_score01(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        segment_desc = self._create_segment_desc(strategy, 'Industry')
        asset = CommercialAsset.objects.create(name='Capital', strategy=strategy)

        orga = Organisation.objects.create(user=self.user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self.assertEqual(1, strategy.get_asset_score(orga, asset, segment_desc))
        self.assertEqual([(1, 3)], strategy.get_assets_totals(orga))

        score = 3
        self._set_asset_score(strategy, orga, asset, segment_desc, score)

        strategy = self.refresh(strategy) #cache....
        self.assertEqual(score, strategy.get_asset_score(orga, asset, segment_desc))
        self.assertEqual([(score, 3)], strategy.get_assets_totals(orga))

    def test_set_asset_score02(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        segment_desc01 = self._create_segment_desc(strategy, 'Industry')
        segment_desc02 = self._create_segment_desc(strategy, 'People')

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
                                    data={'model_id':        charm.id,
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

        strategy = self.refresh(strategy) #cache...
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

        strategy = self.refresh(strategy)
        self.assertEqual(score11, strategy.get_charm_score(orga, charm01, segment_desc01))
        self.assertEqual(score12, strategy.get_charm_score(orga, charm01, segment_desc02))
        self.assertEqual(score21, strategy.get_charm_score(orga, charm02, segment_desc01))
        self.assertEqual(score22, strategy.get_charm_score(orga, charm02, segment_desc02))

        self.assertEqual([(score11 + score21, 1), (score12 + score22, 3)], strategy.get_charms_totals(orga))

    def _set_segment_category(self, strategy, segment_desc, orga, category):
        response = self.client.post('/commercial/strategy/%s/set_segment_cat' % strategy.id,
                                    data={'segment_desc_id': segment_desc.id,
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

        strategy = self.refresh(strategy)
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
        self.assertEqual(set([individual.id]), set(ascore.segment_desc_id for ascore in asset_scores))

        charm_scores = MarketSegmentCharmScore.objects.all()
        self.assertEqual(2, len(charm_scores))
        self.assertEqual(set([individual.id]), set(cscore.segment_desc_id for cscore in charm_scores))

        cats = MarketSegmentCategory.objects.all()
        self.assertEqual(1, len(cats))
        self.assertEqual(set([individual.id]), set(cat.segment_desc_id for cat in cats))
