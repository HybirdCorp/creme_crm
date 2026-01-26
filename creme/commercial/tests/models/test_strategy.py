from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from creme.commercial.models import (
    CommercialAsset,
    CommercialAssetScore,
    MarketSegment,
    MarketSegmentCategory,
    MarketSegmentCharm,
    MarketSegmentCharmScore,
    MarketSegmentDescription,
)
from creme.persons.tests.base import skipIfCustomOrganisation

from ..base import (
    CommercialBaseTestCase,
    Organisation,
    Strategy,
    skipIfCustomStrategy,
)


@skipIfCustomStrategy
class StrategyTestCase(CommercialBaseTestCase):
    def test_delete(self):
        strategy = Strategy.objects.create(user=self.get_root_user(), name='Strat#1')
        self.assertEqual(1, Strategy.objects.count())

        strategy.delete()
        self.assertDoesNotExist(strategy)

    @skipIfCustomOrganisation
    def test_delete__related_items(self):
        user = self.login_as_root_and_get()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        segment_desc = self._create_segment_desc(strategy, 'Industry')
        asset = CommercialAsset.objects.create(name='Capital', strategy=strategy)
        charm = MarketSegmentCharm.objects.create(name='Celebrity', strategy=strategy)

        orga = Organisation.objects.create(user=user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self._set_asset_score(strategy, orga, asset, segment_desc, 2)
        self._set_charm_score(strategy, orga, charm, segment_desc, 3)
        self._set_segment_category(strategy, segment_desc, orga, 2)

        self.assertEqual(1, Strategy.objects.count())
        self.assertEqual(2, MarketSegment.objects.count())  # 1 + 'All the organisations'
        self.assertEqual(1, MarketSegmentDescription.objects.count())
        self.assertEqual(1, CommercialAsset.objects.count())
        self.assertEqual(1, MarketSegmentCharm.objects.count())
        self.assertEqual(1, CommercialAssetScore.objects.count())
        self.assertEqual(1, MarketSegmentCharmScore.objects.count())
        self.assertEqual(1, MarketSegmentCategory.objects.count())

        strategy.delete()
        self.assertEqual(0, Strategy.objects.count())
        self.assertEqual(2, MarketSegment.objects.count())
        self.assertEqual(0, MarketSegmentDescription.objects.count())
        self.assertEqual(0, CommercialAsset.objects.count())
        self.assertEqual(0, MarketSegmentCharm.objects.count())
        self.assertEqual(0, CommercialAssetScore.objects.count())
        self.assertEqual(0, MarketSegmentCharmScore.objects.count())
        self.assertEqual(0, MarketSegmentCategory.objects.count())

    def test_delete_asset(self):
        user = self.login_as_root_and_get()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        asset = CommercialAsset.objects.create(name='Capital', strategy=strategy)
        self.assertEqual(1, strategy.assets.count())

        ct = ContentType.objects.get_for_model(CommercialAsset)
        self.assertPOST200(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            data={'id': asset.id}, follow=True,
        )
        self.assertFalse(strategy.assets.exists())

    def test_delete_charm(self):
        user = self.login_as_root_and_get()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        charm = MarketSegmentCharm.objects.create(name='Dollars', strategy=strategy)
        self.assertEqual(1, strategy.charms.count())

        ct = ContentType.objects.get_for_model(MarketSegmentCharm)
        self.assertPOST200(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            data={'id': charm.id}, follow=True,
        )
        self.assertFalse(strategy.charms.exists())

    def test_delete_segment_desc(self):
        user = self.login_as_root_and_get()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        segment_desc = self._create_segment_desc(strategy, 'People')

        self.assertEqual(1, strategy.segment_info.count())
        self.assertEqual(2, MarketSegment.objects.count())  # 1 + 'All the organisations'

        ct = ContentType.objects.get_for_model(MarketSegmentDescription)
        self.client.post(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            data={'id': segment_desc.id},
        )
        self.assertEqual(0, strategy.segment_info.count())
        self.assertEqual(2, MarketSegment.objects.count())

    @skipIfCustomOrganisation
    def test_delete_segment_desc__scores(self):
        user = self.login_as_root_and_get()
        strategy = Strategy.objects.create(user=user, name='Strat#1')

        industry   = self._create_segment_desc(strategy, 'Industry')
        individual = self._create_segment_desc(strategy, 'Individual')

        create_asset = partial(CommercialAsset.objects.create, strategy=strategy)
        asset1 = create_asset(name='Capital')
        asset2 = create_asset(name='Size')

        create_charm = partial(MarketSegmentCharm.objects.create, strategy=strategy)
        charm1 = create_charm(name='Money')
        charm2 = create_charm(name='Celebrity')

        orga = Organisation.objects.create(user=user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self._set_asset_score(strategy, orga, asset1, industry, 4)
        self._set_asset_score(strategy, orga, asset2, industry, 3)
        self._set_charm_score(strategy, orga, charm1, industry, 4)
        self._set_charm_score(strategy, orga, charm2, industry, 3)

        self._set_asset_score(strategy, orga, asset1, individual, 3)
        self._set_asset_score(strategy, orga, asset2, individual, 3)
        self._set_charm_score(strategy, orga, charm1, individual, 2)
        self._set_charm_score(strategy, orga, charm2, individual, 2)

        self._set_segment_category(strategy, industry,   orga, 2)
        self._set_segment_category(strategy, individual, orga, 4)

        self.assertEqual(2, MarketSegmentDescription.objects.count())
        self.assertEqual(4, CommercialAssetScore.objects.count())
        self.assertEqual(4, MarketSegmentCharmScore.objects.count())
        self.assertEqual(2, MarketSegmentCategory.objects.count())

        ct = ContentType.objects.get_for_model(MarketSegmentDescription)
        self.assertPOST200(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            data={'id': industry.id}, follow=True,
        )
        self.assertEqual(1, MarketSegmentDescription.objects.count())

        self.assertCountEqual(
            [individual.id] * 2,
            CommercialAssetScore.objects.values_list('segment_desc_id', flat=True),
        )
        self.assertCountEqual(
            [individual.id] * 2,
            MarketSegmentCharmScore.objects.values_list('segment_desc_id', flat=True),
        )
        self.assertCountEqual(
            [individual.id],
            MarketSegmentCategory.objects.values_list('segment_desc_id', flat=True),
        )
