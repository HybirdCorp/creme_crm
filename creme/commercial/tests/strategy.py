# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType

    from creme.persons.models import Organisation

    from ..models import *
    from .base import CommercialBaseTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('StrategyTestCase',)


class StrategyTestCase(CommercialBaseTestCase):
    def _create_segment_desc(self, strategy, name):
        self.assertPOST200('/commercial/strategy/%s/add/segment/' % strategy.id,
                           data={'name': name}
                          )
        return strategy.segment_info.get(segment__name=name)

    def _set_asset_score(self, strategy, orga, asset, segment_desc, score):
        self.assertPOST200('/commercial/strategy/%s/set_asset_score' % strategy.id,
                           data={'model_id':        asset.id,
                                 'segment_desc_id': segment_desc.id,
                                 'orga_id':         orga.id,
                                 'score':           score,
                                }
                          )

    def _set_charm_score(self, strategy, orga, charm, segment_desc, score):
        self.assertPOST200('/commercial/strategy/%s/set_charm_score' % strategy.id,
                           data={'model_id':        charm.id,
                                 'segment_desc_id': segment_desc.id,
                                 'orga_id':         orga.id,
                                 'score':           score,
                                }
                          )

    def test_strategy_create(self):
        url = '/commercial/strategy/add'
        self.assertGET200(url)

        name = 'Strat#1'
        response = self.client.post(url, follow=True,
                                    data={'user': self.user.pk,
                                          'name': name,
                                         }
                                   )
        self.assertNoFormError(response)

        strategies = Strategy.objects.all()
        self.assertEqual(1, len(strategies))

        strategy = strategies[0]
        self.assertEqual(name, strategy.name)
        self.assertRedirects(response, strategy.get_absolute_url())

    def test_strategy_edit(self):
        name = 'Strat#1'
        strategy = Strategy.objects.create(user=self.user, name=name)

        url = '/commercial/strategy/edit/%s' % strategy.id
        self.assertGET200(url)

        name += '_edited'
        response = self.client.post(url, follow=True,
                                    data={'user': self.user.pk,
                                          'name': name,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(strategy).name)

    def test_segment_add(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        url = '/commercial/strategy/%s/add/segment/' % strategy.id
        self.assertGET200(url)

        name = 'Industry'
        product = 'Description about product'
        place = 'Description about place'
        price = 'Description about price'
        promotion = 'Description about promotion'
        self.assertPOST200(url, data={'name':      name,
                                      'product':   product,
                                      'place':     place,
                                      'price':     price,
                                      'promotion': promotion,
                                     }
                          )

        segment_info = strategy.segment_info.all()
        self.assertEqual(1, len(segment_info))

        description = segment_info[0]
        self.assertEqual(name,      description.segment.name)
        self.assertEqual(product,   description.product)
        self.assertEqual(place,     description.place)
        self.assertEqual(price,     description.price)
        self.assertEqual(promotion, description.promotion)
        self.assertIn(name, description.segment.property_type.text)

    def test_segment_link(self):
        create_strategy = partial(Strategy.objects.create, user=self.user)
        strategy01 = create_strategy(name='Strat#1')
        industry = self._create_segment_desc(strategy01, 'Industry').segment
        self.assertEqual(1, strategy01.segment_info.count())

        strategy02 = create_strategy(name='Strat#2')
        self.assertFalse(0, strategy02.segment_info.exists())

        url = '/commercial/strategy/%s/link/segment/' % strategy02.id
        self.assertGET200(url)

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
        self.assertGET200(url)

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
        self.assertNoFormError(response)

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
        self.assertGET200(url)

        name = 'Size'
        self.assertPOST200(url, data={'name': name})
        self.assertEqual([name], list(strategy.assets.values_list('name', flat=True)))

    def test_asset_edit(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        name = 'Size'
        asset = CommercialAsset.objects.create(name=name, strategy=strategy)
        url = '/commercial/asset/edit/%s/' % asset.id
        self.assertGET200(url)

        name += '_edited'
        self.assertPOST200(url, data={'name': name})

        asset = self.refresh(asset)
        self.assertEqual(name,     asset.name)
        self.assertEqual(strategy, asset.strategy)

    def test_asset_delete(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        asset = CommercialAsset.objects.create(name='Capital', strategy=strategy)
        self.assertEqual(1, strategy.assets.count())

        ct = ContentType.objects.get_for_model(CommercialAsset)
        self.assertPOST200('/creme_core/entity/delete_related/%s' % ct.id,
                           data={'id': asset.id}, follow=True
                          )
        self.assertFalse(strategy.assets.exists())

    def test_charms_add(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        url = '/commercial/strategy/%s/add/charm/' % strategy.id
        self.assertGET200(url)

        name = 'Size'
        self.assertPOST200(url, data={'name': name})
        self.assertEqual([name], list(strategy.charms.values_list('name', flat=True)))

    def test_charm_edit(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        name = 'Size'
        charm = MarketSegmentCharm.objects.create(name=name, strategy=strategy)

        url = '/commercial/charm/edit/%s/' % charm.id
        self.assertGET200(url)

        name += '_edited'
        self.assertPOST200(url, data={'name': name})

        charm = self.refresh(charm)
        self.assertEqual(name,     charm.name)
        self.assertEqual(strategy, charm.strategy)

    def test_charm_delete(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        charm = MarketSegmentCharm.objects.create(name='Dollars', strategy=strategy)
        self.assertEqual(1, strategy.charms.count())

        ct = ContentType.objects.get_for_model(MarketSegmentCharm)
        self.assertPOST200('/creme_core/entity/delete_related/%s' % ct.id,
                           data={'id': charm.id}, follow=True
                          )
        self.assertFalse(strategy.charms.exists())

    def test_add_evaluated_orga(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        orga     = Organisation.objects.create(user=self.user, name='Nerv')

        segment_desc = self._create_segment_desc(strategy, 'Industry')
        asset = CommercialAsset.objects.create(name='Capital', strategy=strategy)
        charm = MarketSegmentCharm.objects.create(name='Celebrity', strategy=strategy)

        url = '/commercial/strategy/%s/add/organisation/' % strategy.id
        self.assertGET200(url)
        self.assertPOST200(url, data={'organisations': '[%d]' % orga.id})
        self.assertEqual([orga], list(strategy.evaluated_orgas.all()))

        response = self.assertGET200('/commercial/strategy/%s/organisation/%s/evaluation' % (
                                            strategy.id, orga.id
                                        )
                                    )
        #self.assertTemplateUsed(response, 'commercial/templatetags/widget_score.html') #TODO: do not work ??
        self.assertContains(response, '<select name="asset_score_%s_%s"' % (asset.id, segment_desc.id))
        self.assertContains(response, '<select name="charm_score_%s_%s"' % (charm.id, segment_desc.id))

        response = self.assertGET200('/commercial/strategy/%s/organisation/%s/synthesis'  % (
                                            strategy.id, orga.id
                                        )
                                    )
        #self.assertTemplateUsed(response, 'commercial/templatetags/widget_category.html') #TODO: do not work ??
        self.assertContains(response, '<select name="segment_catselect_%s"' % segment_desc.id)

    def test_delete_evaluated_orga(self):
        create_strategy = partial(Strategy.objects.create, user=self.user)
        strategy1 = create_strategy(name='Strat#1')
        strategy2 = create_strategy(name='Strat#2')

        create_orga = partial(Organisation.objects.create, user=self.user)
        orga1 = create_orga(name='Nerv')
        orga2 = create_orga(name='Seele')

        strategy1.evaluated_orgas.add(orga1, orga2)
        strategy2.evaluated_orgas.add(orga1)

        segment_desc1 = self._create_segment_desc(strategy1, 'Industry')
        asset1 = CommercialAsset.objects.create(name='Capital', strategy=strategy1)
        charm1 = MarketSegmentCharm.objects.create(name='Celebrity', strategy=strategy1)

        # Scores = strategy1/orga1
        self._set_asset_score(strategy1, orga1, asset1, segment_desc1, 3)
        self._set_charm_score(strategy1, orga1, charm1, segment_desc1, 3)
        asset_score1 = self.get_object_or_fail(CommercialAssetScore,    organisation=orga1, segment_desc=segment_desc1)
        charm_score1 = self.get_object_or_fail(MarketSegmentCharmScore, organisation=orga1, segment_desc=segment_desc1)

        # Scores = strategy1/orga2
        self._set_asset_score(strategy1, orga2, asset1, segment_desc1, 3)
        self._set_charm_score(strategy1, orga2, charm1, segment_desc1, 3)
        asset_score2 = self.get_object_or_fail(CommercialAssetScore,    organisation=orga2, segment_desc=segment_desc1)
        charm_score2 = self.get_object_or_fail(MarketSegmentCharmScore, organisation=orga2, segment_desc=segment_desc1)

        # Scores = strategy2
        segment_desc2 = self._create_segment_desc(strategy2, 'Consumers')
        asset2 = CommercialAsset.objects.create(name='Capital', strategy=strategy2)
        charm2 = MarketSegmentCharm.objects.create(name='Celebrity', strategy=strategy2)
        self._set_asset_score(strategy2, orga1, asset2, segment_desc2, 3)
        self._set_charm_score(strategy2, orga1, charm2, segment_desc2, 3)
        asset_score3 = self.get_object_or_fail(CommercialAssetScore,    organisation=orga1, segment_desc=segment_desc2)
        charm_score3 = self.get_object_or_fail(MarketSegmentCharmScore, organisation=orga1, segment_desc=segment_desc2)

        self.assertPOST200('/commercial/strategy/%s/organisation/delete' % strategy1.id,
                           data={'id': orga1.id}, follow=True
                          )
        self.assertEqual([orga2], list(strategy1.evaluated_orgas.all()))

        self.assertDoesNotExist(asset_score1)
        self.get_object_or_fail(CommercialAssetScore, pk=asset_score2.pk) #no deleted (other orga)
        self.get_object_or_fail(CommercialAssetScore, pk=asset_score3.pk) #no deleted (other strategy)

        self.assertDoesNotExist(charm_score1)
        self.get_object_or_fail(MarketSegmentCharmScore, pk=charm_score2.pk) #no deleted (other orga)
        self.get_object_or_fail(MarketSegmentCharmScore, pk=charm_score3.pk) #no deleted (other strategy)

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

        create_asset = partial(CommercialAsset.objects.create, strategy=strategy)
        asset01 = create_asset(name='Capital')
        asset02 = create_asset(name='Size')

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

        strategy = self.refresh(strategy) #(cache....)
        self.assertEqual(score11, strategy.get_asset_score(orga, asset01, segment_desc01))
        self.assertEqual(score12, strategy.get_asset_score(orga, asset01, segment_desc02))
        self.assertEqual(score21, strategy.get_asset_score(orga, asset02, segment_desc01))
        self.assertEqual(score22, strategy.get_asset_score(orga, asset02, segment_desc02))

        self.assertEqual([(score11 + score21, 1), (score12 + score22, 3)],
                         strategy.get_assets_totals(orga)
                        )

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

        create_charm = partial(MarketSegmentCharm.objects.create, strategy=strategy)
        charm01 = create_charm(name='Money')
        charm02 = create_charm(name='Celebrity')

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

        self.assertEqual([(score11 + score21, 1), (score12 + score22, 3)],
                         strategy.get_charms_totals(orga)
                        )

    def _set_segment_category(self, strategy, segment_desc, orga, category):
        self.assertPOST200('/commercial/strategy/%s/set_segment_cat' % strategy.id,
                           data={'segment_desc_id': segment_desc.id,
                                 'orga_id':         orga.id,
                                 'category':        category,
                                }
                          )

    def test_segments_categories(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        industry    = self._create_segment_desc(strategy, 'Industry')
        individual  = self._create_segment_desc(strategy, 'Individual')
        community   = self._create_segment_desc(strategy, 'Community')
        association = self._create_segment_desc(strategy, 'Association')

        create_asset = partial(CommercialAsset.objects.create, strategy=strategy)
        asset01 = create_asset(name='Capital')
        asset02 = create_asset(name='Size')

        create_charm = partial(MarketSegmentCharm.objects.create, strategy=strategy)
        charm01 = create_charm(name='Money')
        charm02 = create_charm(name='Celebrity')

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

        def segment_ids(strategy, orga, cat):
            return (segment.id for segment in strategy.get_segments_for_category(orga, cat))

        self.assertEqual([association.id], list(segment_ids(strategy, orga, 4)))
        self.assertEqual([individual.id],  list(segment_ids(strategy, orga, 3)))
        self.assertEqual([community.id],   list(segment_ids(strategy, orga, 2)))
        self.assertEqual([industry.id],    list(segment_ids(strategy, orga, 1)))

        self._set_segment_category(strategy, individual, orga, 4)

        strategy = self.refresh(strategy)
        self.assertEqual([], list(segment_ids(strategy, orga, 3)))
        self.assertEqual(set([association.id, individual.id]),
                         set(segment_ids(strategy, orga, 4))
                        )
        self.assertEqual(1, MarketSegmentCategory.objects.count())

        self._set_segment_category(strategy, individual, orga, 2)

        strategy = self.refresh(strategy) #(cache....)
        self.assertEqual([association.id], list(segment_ids(strategy, orga, 4)))
        self.assertEqual([],               list(segment_ids(strategy, orga, 3)))
        self.assertEqual([industry.id],    list(segment_ids(strategy, orga, 1)))
        self.assertEqual(set([community.id, individual.id]),
                         set(segment_ids(strategy, orga, 2))
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
        self.assertDoesNotExist(strategy)

    def test_delete02(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        segment_desc = self._create_segment_desc(strategy, 'Industry')
        asset = CommercialAsset.objects.create(name='Capital', strategy=strategy)
        charm = MarketSegmentCharm.objects.create(name='Celebrity', strategy=strategy)

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
        self.client.post('/creme_core/entity/delete_related/%s' % ct.id,
                         data={'id': segment_desc.id}
                        )
        self.assertEqual(0, strategy.segment_info.count())
        self.assertEqual(1, MarketSegment.objects.count())

    def test_segment_unlink02(self):
        strategy = Strategy.objects.create(user=self.user, name='Strat#1')

        industry   = self._create_segment_desc(strategy, 'Industry')
        individual = self._create_segment_desc(strategy, 'Individual')

        create_asset = partial(CommercialAsset.objects.create, strategy=strategy)
        asset01 = create_asset(name='Capital')
        asset02 = create_asset(name='Size')

        create_charm = partial(MarketSegmentCharm.objects.create, strategy=strategy)
        charm01 = create_charm(name='Money')
        charm02 = create_charm(name='Celebrity')

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
        self.client.post('/creme_core/entity/delete_related/%s' % ct.id,
                         data={'id': industry.id}
                        )
        self.assertEqual(1, MarketSegmentDescription.objects.count())

        asset_scores = CommercialAssetScore.objects.all()
        self.assertEqual(2, len(asset_scores))
        self.assertEqual(set([individual.id]),
                         set(ascore.segment_desc_id for ascore in asset_scores)
                        )

        charm_scores = MarketSegmentCharmScore.objects.all()
        self.assertEqual(2, len(charm_scores))
        self.assertEqual(set([individual.id]),
                         set(cscore.segment_desc_id for cscore in charm_scores)
                        )

        cats = MarketSegmentCategory.objects.all()
        self.assertEqual(1, len(cats))
        self.assertEqual(set([individual.id]),
                         set(cat.segment_desc_id for cat in cats)
                        )
