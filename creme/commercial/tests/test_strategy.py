# -*- coding: utf-8 -*-

from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import CremePropertyType, SetCredentials
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.tests.base import skipIfCustomOrganisation

from ..bricks import (
    AssetsCharmsMatrixBrick,
    AssetsMatrixBrick,
    CharmsMatrixBrick,
)
from ..models import (
    CommercialAsset,
    CommercialAssetScore,
    MarketSegment,
    MarketSegmentCategory,
    MarketSegmentCharm,
    MarketSegmentCharmScore,
    MarketSegmentDescription,
)
from .base import (
    CommercialBaseTestCase,
    Organisation,
    Strategy,
    skipIfCustomStrategy,
)


@skipIfCustomStrategy
class StrategyTestCase(BrickTestCaseMixin, CommercialBaseTestCase):
    @staticmethod
    def _build_link_segment_url(strategy):
        return reverse('commercial__link_segment', args=(strategy.id,))

    @staticmethod
    def _build_edit_segmentdesc_url(segment_desc):
        return reverse('commercial__edit_segment_desc', args=(segment_desc.id,))

    def test_strategy_create(self):
        user = self.login()
        url = reverse('commercial__create_strategy')
        self.assertGET200(url)

        name = 'Strat#1'
        response = self.client.post(
            url,
            follow=True,
            data={'user': user.pk, 'name': name},
        )
        self.assertNoFormError(response)

        strategies = Strategy.objects.all()
        self.assertEqual(1, len(strategies))

        strategy = strategies[0]
        self.assertEqual(name, strategy.name)
        self.assertRedirects(response, strategy.get_absolute_url())

    def test_strategy_edit(self):
        user = self.login()
        name = 'Strat#1'
        strategy = Strategy.objects.create(user=user, name=name)

        url = strategy.get_edit_absolute_url()
        self.assertGET200(url)

        name += '_edited'
        response = self.client.post(
            url,
            follow=True,
            data={'user': user.pk, 'name': name},
        )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(strategy).name)

    def test_listview(self):
        user = self.login()
        create_strategy = partial(Strategy.objects.create, user=user)
        strategies = {create_strategy(name='Strat#1'), create_strategy(name='Strat#2')}
        response = self.assertGET200(reverse('commercial__list_strategies'))

        with self.assertNoException():
            strategies_page = response.context['page_obj']

        self.assertSetEqual(strategies, {*strategies_page.object_list})

    def test_segment_add(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')

        url = reverse('commercial__create_segment_desc', args=(strategy.id,))

        context = self.assertGET200(url).context
        self.assertEqual(
            _('New market segment for «{entity}»').format(entity=strategy),
            context.get('title'),
        )
        self.assertEqual(MarketSegmentDescription.save_label, context.get('submit_label'))

        name = 'Industry'
        product = 'Description about product'
        place = 'Description about place'
        price = 'Description about price'
        promotion = 'Description about promotion'
        self.assertPOST200(
            url,
            data={
                'name':      name,
                'product':   product,
                'place':     place,
                'price':     price,
                'promotion': promotion,
            },
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

    def test_segment_create01(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')

        url = self._build_add_segmentdesc_url(strategy)
        self.assertGET200(url)

        name = 'Industry'
        product = 'Description about product...'
        place = 'Description about place...'
        price = 'Description about price...'
        promotion = 'Description about promotion...'
        description = self._create_segment_desc(strategy, name, product, place, price, promotion)

        self.assertEqual(product,   description.product)
        self.assertEqual(place,     description.place)
        self.assertEqual(price,     description.price)
        self.assertEqual(promotion, description.promotion)

        industry = description.segment
        self.assertEqual(name, industry.name)

        # Collision with segment name
        response = self.assertPOST200(
            url,
            data={
                'name': name,
                'product':   'Another' + product,
                'place':     'Another' + place,
                'price':     'Another' + price,
                'promotion': 'Another' + promotion,
            },
        )
        self.assertFormError(
            response, 'form', 'name', _('A segment with this name already exists'),
        )

    def test_segment_create02(self):
        "Collision with property type name."
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')

        name = 'Industry'
        pname = _('is in the segment «{}»').format(name)
        CremePropertyType.objects.smart_update_or_create(
            str_pk='commercial-test_segment_create02', text=pname,
        )

        response = self.assertPOST200(
            self._build_add_segmentdesc_url(strategy), data={'name': name},
        )
        self.assertFormError(
            response, 'form', 'name',
            _('A property with the name «%(name)s» already exists') % {'name': pname},
        )

    def test_segment_link(self):
        user = self.login()
        create_strategy = partial(Strategy.objects.create, user=user)
        strategy01 = create_strategy(name='Strat#1')
        industry = self._create_segment_desc(strategy01, 'Industry').segment
        self.assertEqual(1, strategy01.segment_info.count())

        strategy02 = create_strategy(name='Strat#2')
        self.assertFalse(0, strategy02.segment_info.exists())

        url = self._build_link_segment_url(strategy02)
        context = self.assertGET200(url).context
        self.assertEqual(
            _('New market segment for «{entity}»').format(entity=strategy02),
            context.get('title'),
        )
        self.assertEqual(
            MarketSegmentDescription.save_label, context.get('submit_label'),
        )

        # ---
        product = 'Description about product'
        place = 'Description about place'
        price = 'Description about price'
        promotion = 'Description about promotion'
        response = self.client.post(
            url,
            data={
                'segment':   industry.id,
                'product':   product,
                'place':     place,
                'price':     price,
                'promotion': promotion,
            },
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

    def test_segment_edit01(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        name = 'Industry'
        segment_desc = self._create_segment_desc(strategy, name)

        url = self._build_edit_segmentdesc_url(segment_desc)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(
            _('Segment for «{entity}»').format(entity=strategy),
            response.context.get('title'),
        )

        name += ' of Cheese'
        product = 'Description about product'
        place = 'Description about place'
        price = 'Description about price'
        promotion = 'Description about promotion'
        response = self.client.post(
            url,
            data={
                'name':      name,
                'product':   product,
                'place':     place,
                'price':     price,
                'promotion': promotion,
            },
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

    def test_segment_edit02(self):
        "No name change => no collision"
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        name = 'Industry'
        product = 'description about product'
        segment_desc = self._create_segment_desc(strategy, name, product=product)

        product = product.title()
        response = self.client.post(
            self._build_edit_segmentdesc_url(segment_desc),
            data={'name': name, 'product': product},
        )
        self.assertNoFormError(response)

        segment_desc = self.refresh(segment_desc)
        self.assertEqual(product, segment_desc.product)

        segment = segment_desc.segment
        self.assertEqual(name, segment.name)
        self.assertIn(name,    segment.property_type.text)

    def test_segment_edit03(self):
        "Segment with no property type"
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        segment = MarketSegment.objects.filter(property_type=None)[0]
        response = self.client.post(
            self._build_link_segment_url(strategy),
            data={'segment': segment.id},
        )
        self.assertNoFormError(response)

        seginfo = strategy.segment_info.all()
        self.assertEqual(1, len(seginfo))

        segment_desc = seginfo[0]
        self.assertEqual(segment,  segment_desc.segment)
        self.assertFalse(segment_desc.product)

        product = 'Description about product'
        response = self.client.post(
            self._build_edit_segmentdesc_url(segment_desc),
            data={'name': segment.name, 'product': product},
        )
        self.assertNoFormError(response)
        self.assertEqual(product, self.refresh(segment_desc).product)

    def test_asset_add(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')

        url = reverse('commercial__create_asset', args=(strategy.id,))
        context = self.assertGET200(url).context
        self.assertEqual(
            _('New commercial asset for «{entity}»').format(entity=strategy),
            context.get('title'),
        )
        self.assertEqual(CommercialAsset.save_label, context.get('submit_label'))

        # ---
        name = 'Size'
        self.assertPOST200(url, data={'name': name})
        self.assertListEqual([name], [*strategy.assets.values_list('name', flat=True)])

    def test_asset_edit(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        name = 'Size'
        asset = CommercialAsset.objects.create(name=name, strategy=strategy)
        url = asset.get_edit_absolute_url()
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(
            _('Asset for «{entity}»').format(entity=strategy),
            response.context.get('title'),
        )

        # ---
        name += '_edited'
        self.assertPOST200(url, data={'name': name})

        asset = self.refresh(asset)
        self.assertEqual(name,     asset.name)
        self.assertEqual(strategy, asset.strategy)

    def test_asset_delete(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        asset = CommercialAsset.objects.create(name='Capital', strategy=strategy)
        self.assertEqual(1, strategy.assets.count())

        ct = ContentType.objects.get_for_model(CommercialAsset)
        self.assertPOST200(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            data={'id': asset.id}, follow=True,
        )
        self.assertFalse(strategy.assets.exists())

    def test_charms_add(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')

        url = reverse('commercial__create_charm', args=(strategy.id,))
        context = self.assertGET200(url).context
        self.assertEqual(
            _('New segment charm for «{entity}»').format(entity=strategy),
            context.get('title'),
        )
        self.assertEqual(MarketSegmentCharm.save_label, context.get('submit_label'))

        name = 'Size'
        self.assertPOST200(url, data={'name': name})
        self.assertListEqual([name], [*strategy.charms.values_list('name', flat=True)])

    def test_charm_edit(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        name = 'Size'
        charm = MarketSegmentCharm.objects.create(name=name, strategy=strategy)

        url = charm.get_edit_absolute_url()
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(
            _('Charm for «{entity}»').format(entity=strategy),
            response.context.get('title'),
        )

        # ---
        name += '_edited'
        self.assertPOST200(url, data={'name': name})

        charm = self.refresh(charm)
        self.assertEqual(name,     charm.name)
        self.assertEqual(strategy, charm.strategy)

    def test_charm_delete(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        charm = MarketSegmentCharm.objects.create(name='Dollars', strategy=strategy)
        self.assertEqual(1, strategy.charms.count())

        ct = ContentType.objects.get_for_model(MarketSegmentCharm)
        self.assertPOST200(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            data={'id': charm.id}, follow=True,
        )
        self.assertFalse(strategy.charms.exists())

    @skipIfCustomOrganisation
    def test_add_evaluated_orga(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        orga = Organisation.objects.create(user=user, name='Nerv')

        segment_desc = self._create_segment_desc(strategy, 'Industry')
        asset = CommercialAsset.objects.create(name='Capital', strategy=strategy)
        charm = MarketSegmentCharm.objects.create(name='Celebrity', strategy=strategy)

        url = reverse('commercial__add_evaluated_orgas', args=(strategy.id,))
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(
            _('New organisation(s) for «{entity}»').format(entity=strategy),
            context.get('title'),
        )
        self.assertEqual(_('Link the organisation(s)'), context.get('submit_label'))

        # ---
        self.assertPOST200(
            url, data={'organisations': self.formfield_value_multi_creator_entity(orga)},
        )
        self.assertListEqual([orga], [*strategy.evaluated_orgas.all()])

        response = self.assertGET200(
            reverse('commercial__orga_evaluation', args=(strategy.id, orga.id)),
        )
        self.assertTemplateUsed(response, 'commercial/orga_evaluation.html')
        self.assertTemplateUsed(response, 'commercial/templatetags/widget-score.html')

        get = response.context.get
        self.assertEqual(orga,     get('orga'))
        self.assertEqual(strategy, get('strategy'))
        self.assertEqual(
            reverse('commercial__reload_matrix_brick', args=(strategy.id, orga.id)),
            get('bricks_reload_url'),
        )

        self.assertContains(
            response,
            """<select onchange="creme.commercial.setScore(this, '{url}', """
            """{asset_id}, {segment_id}, {orga_id});">""".format(
                url=reverse('commercial__set_asset_score', args=(strategy.id,)),
                asset_id=asset.id,
                segment_id=segment_desc.id,
                orga_id=orga.id,
            ),
        )
        self.assertContains(
            response,
            """<select onchange="creme.commercial.setScore(this, '{url}', """
            """{asset_id}, {segment_id}, {orga_id});">""".format(
                url=reverse('commercial__set_charm_score', args=(strategy.id,)),
                asset_id=charm.id,
                segment_id=segment_desc.id,
                orga_id=orga.id,
            ),
        )

        # ---
        response = self.assertGET200(
            reverse('commercial__orga_synthesis', args=(strategy.id, orga.id))
        )
        self.assertTemplateUsed(response, 'commercial/orga_synthesis.html')
        self.assertContains(response, f'<li data-segment="{segment_desc.id}"')

        get = response.context.get
        self.assertEqual(orga,     get('orga'))
        self.assertEqual(strategy, get('strategy'))
        self.assertEqual(
            reverse('commercial__reload_matrix_brick', args=(strategy.id, orga.id)),
            get('bricks_reload_url'),
        )

    @skipIfCustomOrganisation
    def test_view_evaluated_orga01(self):
        "Unrelated organisation"
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        orga = Organisation.objects.create(user=user, name='Nerv')
        self.assertGET404(reverse('commercial__orga_evaluation', args=(strategy.id, orga.id)))

    @skipIfCustomOrganisation
    def test_view_evaluated_orga02(self):
        "Not super-user"
        user = self.login(is_superuser=False, allowed_apps=['commercial', 'persons'])

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_ALL,
        )

        strategy = Strategy.objects.create(user=user, name='Strat#1')
        orga = Organisation.objects.create(user=user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self.assertGET200(
            reverse('commercial__orga_evaluation', args=(strategy.id, orga.id))
        )

    @skipIfCustomOrganisation
    def test_view_evaluated_orga03(self):
        "Must see the Strategy"
        user = self.login(is_superuser=False, allowed_apps=['commercial', 'persons'])

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_OWN,
        )

        strategy = Strategy.objects.create(user=self.other_user, name='Strat#1')
        self.assertFalse(user.has_perm_to_view(strategy))

        orga = Organisation.objects.create(user=user, name='Nerv')
        self.assertTrue(user.has_perm_to_view(orga))

        strategy.evaluated_orgas.add(orga)

        self.assertGET403(
            reverse('commercial__orga_evaluation', args=(strategy.id, orga.id))
        )

    @skipIfCustomOrganisation
    def test_view_evaluated_orga04(self):
        "Must see the Organisation"
        user = self.login(is_superuser=False, allowed_apps=['commercial', 'persons'])

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_OWN,
        )

        strategy = Strategy.objects.create(user=user, name='Strat#1')
        self.assertTrue(user.has_perm_to_view(strategy))

        orga = Organisation.objects.create(user=self.other_user, name='Nerv')
        self.assertFalse(user.has_perm_to_view(orga))

        strategy.evaluated_orgas.add(orga)

        self.assertGET403(
            reverse('commercial__orga_evaluation', args=(strategy.id, orga.id))
        )

    @skipIfCustomOrganisation
    def test_delete_evaluated_orga(self):
        user = self.login()

        create_strategy = partial(Strategy.objects.create, user=user)
        strategy1 = create_strategy(name='Strat#1')
        strategy2 = create_strategy(name='Strat#2')

        create_orga = partial(Organisation.objects.create, user=user)
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
        asset_score1 = self.get_object_or_fail(
            CommercialAssetScore, organisation=orga1, segment_desc=segment_desc1,
        )
        charm_score1 = self.get_object_or_fail(
            MarketSegmentCharmScore, organisation=orga1, segment_desc=segment_desc1,
        )

        # Scores = strategy1/orga2
        self._set_asset_score(strategy1, orga2, asset1, segment_desc1, 3)
        self._set_charm_score(strategy1, orga2, charm1, segment_desc1, 3)
        asset_score2 = self.get_object_or_fail(
            CommercialAssetScore, organisation=orga2, segment_desc=segment_desc1,
        )
        charm_score2 = self.get_object_or_fail(
            MarketSegmentCharmScore, organisation=orga2, segment_desc=segment_desc1,
        )

        # Scores = strategy2
        segment_desc2 = self._create_segment_desc(strategy2, 'Consumers')
        asset2 = CommercialAsset.objects.create(name='Capital', strategy=strategy2)
        charm2 = MarketSegmentCharm.objects.create(name='Celebrity', strategy=strategy2)
        self._set_asset_score(strategy2, orga1, asset2, segment_desc2, 3)
        self._set_charm_score(strategy2, orga1, charm2, segment_desc2, 3)
        asset_score3 = self.get_object_or_fail(
            CommercialAssetScore, organisation=orga1, segment_desc=segment_desc2,
        )
        charm_score3 = self.get_object_or_fail(
            MarketSegmentCharmScore, organisation=orga1, segment_desc=segment_desc2,
        )

        self.assertPOST200(
            reverse('commercial__remove_evaluated_orga', args=(strategy1.id,)),
            data={'id': orga1.id}, follow=True,
        )
        self.assertListEqual([orga2], [*strategy1.evaluated_orgas.all()])

        self.assertDoesNotExist(asset_score1)

        # Not deleted (other organisation)
        self.get_object_or_fail(CommercialAssetScore, pk=asset_score2.pk)

        # Not deleted (other strategy)
        self.get_object_or_fail(CommercialAssetScore, pk=asset_score3.pk)

        self.assertDoesNotExist(charm_score1)

        # Not deleted (other organisation)
        self.get_object_or_fail(MarketSegmentCharmScore, pk=charm_score2.pk)

        # Not deleted (other strategy)
        self.get_object_or_fail(MarketSegmentCharmScore, pk=charm_score3.pk)

    @skipIfCustomOrganisation
    def test_set_asset_score01(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        segment_desc = self._create_segment_desc(strategy, 'Industry')
        asset = CommercialAsset.objects.create(name='Capital', strategy=strategy)

        orga = Organisation.objects.create(user=user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self.assertEqual(1, strategy.get_asset_score(orga, asset, segment_desc))
        self.assertEqual([(1, 3)], strategy.get_assets_totals(orga))

        score = 3
        self._set_asset_score(strategy, orga, asset, segment_desc, score)

        strategy = self.refresh(strategy)  # Cache....
        self.assertEqual(score, strategy.get_asset_score(orga, asset, segment_desc))
        self.assertEqual([(score, 3)], strategy.get_assets_totals(orga))

    @skipIfCustomOrganisation
    def test_set_asset_score02(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')

        segment_desc01 = self._create_segment_desc(strategy, 'Industry')
        segment_desc02 = self._create_segment_desc(strategy, 'People')

        create_asset = partial(CommercialAsset.objects.create, strategy=strategy)
        asset01 = create_asset(name='Capital')
        asset02 = create_asset(name='Size')

        orga = Organisation.objects.create(user=user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self.assertEqual(1, strategy.get_asset_score(orga, asset01, segment_desc01))
        self.assertEqual(1, strategy.get_asset_score(orga, asset01, segment_desc02))
        self.assertEqual(1, strategy.get_asset_score(orga, asset02, segment_desc01))
        self.assertEqual(1, strategy.get_asset_score(orga, asset02, segment_desc02))

        self.assertEqual([(2, 3), (2, 3)], strategy.get_assets_totals(orga))

        score11 = 1
        score12 = 4
        score21 = 3
        score22 = 2
        self._set_asset_score(strategy, orga, asset01, segment_desc01, score11)
        self._set_asset_score(strategy, orga, asset01, segment_desc02, score12)
        self._set_asset_score(strategy, orga, asset02, segment_desc01, score21)
        self._set_asset_score(strategy, orga, asset02, segment_desc02, score22)

        strategy = self.refresh(strategy)  # (cache....)
        self.assertEqual(score11, strategy.get_asset_score(orga, asset01, segment_desc01))
        self.assertEqual(score12, strategy.get_asset_score(orga, asset01, segment_desc02))
        self.assertEqual(score21, strategy.get_asset_score(orga, asset02, segment_desc01))
        self.assertEqual(score22, strategy.get_asset_score(orga, asset02, segment_desc02))

        self.assertListEqual(
            [(score11 + score21, 1), (score12 + score22, 3)],
            strategy.get_assets_totals(orga),
        )

    @skipIfCustomOrganisation
    def test_set_charm_score01(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        segment_desc = self._create_segment_desc(strategy, 'Industry')
        charm = MarketSegmentCharm.objects.create(name='Celebrity', strategy=strategy)

        orga = Organisation.objects.create(user=user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self.assertEqual(1, strategy.get_charm_score(orga, charm, segment_desc))
        self.assertListEqual([(1, 3)], strategy.get_charms_totals(orga))

        score = 3
        self._set_charm_score(strategy, orga, charm, segment_desc, score)

        strategy = self.refresh(strategy)  # Cache...
        self.assertEqual(score, strategy.get_charm_score(orga, charm, segment_desc))
        self.assertListEqual([(score, 3)], strategy.get_charms_totals(orga))

    @skipIfCustomOrganisation
    def test_set_charm_score02(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        segment_desc01 = self._create_segment_desc(strategy, 'Industry')
        segment_desc02 = self._create_segment_desc(strategy, 'People')

        create_charm = partial(MarketSegmentCharm.objects.create, strategy=strategy)
        charm01 = create_charm(name='Money')
        charm02 = create_charm(name='Celebrity')

        orga = Organisation.objects.create(user=user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self.assertEqual(1, strategy.get_charm_score(orga, charm01, segment_desc01))
        self.assertEqual(1, strategy.get_charm_score(orga, charm01, segment_desc02))
        self.assertEqual(1, strategy.get_charm_score(orga, charm02, segment_desc01))
        self.assertEqual(1, strategy.get_charm_score(orga, charm02, segment_desc02))

        self.assertEqual([(2, 3), (2, 3)], strategy.get_charms_totals(orga))

        score11 = 1
        score12 = 4
        score21 = 3
        score22 = 2
        self._set_charm_score(strategy, orga, charm01, segment_desc01, score11)
        self._set_charm_score(strategy, orga, charm01, segment_desc02, score12)
        self._set_charm_score(strategy, orga, charm02, segment_desc01, score21)
        self._set_charm_score(strategy, orga, charm02, segment_desc02, score22)

        strategy = self.refresh(strategy)
        self.assertEqual(score11, strategy.get_charm_score(orga, charm01, segment_desc01))
        self.assertEqual(score12, strategy.get_charm_score(orga, charm01, segment_desc02))
        self.assertEqual(score21, strategy.get_charm_score(orga, charm02, segment_desc01))
        self.assertEqual(score22, strategy.get_charm_score(orga, charm02, segment_desc02))

        self.assertListEqual(
            [(score11 + score21, 1), (score12 + score22, 3)],
            strategy.get_charms_totals(orga),
        )

    def _set_segment_category(self, strategy, segment_desc, orga, category):
        self.assertPOST200(
            reverse('commercial__set_segment_category', args=(strategy.id,)),
            data={
                'segment_desc_id': segment_desc.id,
                'orga_id':         orga.id,
                'category':        category,
            },
        )

    @skipIfCustomOrganisation
    def test_segments_categories(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')

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

        orga = Organisation.objects.create(user=user, name='Nerv')
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

        self.assertListEqual([association.id], [*segment_ids(strategy, orga, 4)])
        self.assertListEqual([individual.id],  [*segment_ids(strategy, orga, 3)])
        self.assertListEqual([community.id],   [*segment_ids(strategy, orga, 2)])
        self.assertListEqual([industry.id],    [*segment_ids(strategy, orga, 1)])

        self._set_segment_category(strategy, individual, orga, 4)

        strategy = self.refresh(strategy)
        self.assertListEqual([], [*segment_ids(strategy, orga, 3)])
        self.assertSetEqual(
            {association.id, individual.id},
            {*segment_ids(strategy, orga, 4)},
        )
        self.assertEqual(1, MarketSegmentCategory.objects.count())

        self._set_segment_category(strategy, individual, orga, 2)

        strategy = self.refresh(strategy)  # (cache....)
        self.assertListEqual([association.id], [*segment_ids(strategy, orga, 4)])
        self.assertListEqual([],               [*segment_ids(strategy, orga, 3)])
        self.assertListEqual([industry.id],    [*segment_ids(strategy, orga, 1)])
        self.assertSetEqual(
            {community.id, individual.id},
            {*segment_ids(strategy, orga, 2)}
        )
        self.assertEqual(1, MarketSegmentCategory.objects.count())

        self.assertEqual(1, strategy.get_segment_category(orga, industry))
        self.assertEqual(2, strategy.get_segment_category(orga, individual))
        self.assertEqual(2, strategy.get_segment_category(orga, community))
        self.assertEqual(4, strategy.get_segment_category(orga, association))

    def test_delete01(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        self.assertEqual(1, Strategy.objects.count())

        strategy.delete()
        self.assertDoesNotExist(strategy)

    @skipIfCustomOrganisation
    def test_delete02(self):
        user = self.login()
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

    def test_segment_unlink01(self):
        user = self.login()
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
    def test_segment_unlink02(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')

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

    def test_inneredit_segmentdesc(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        segment_desc = self._create_segment_desc(strategy, 'Industry', product='green powder')

        build_url = self.build_inneredit_url
        url = build_url(segment_desc, 'product')
        self.assertGET200(url)

        product = segment_desc.product.title()
        response = self.client.post(
            url,
            data={
                'entities_lbl': [str(segment_desc)],
                'field_value':  product,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(product, self.refresh(segment_desc).product)

        self.assertGET(400, build_url(segment_desc, 'strategy'))
        self.assertGET(400, build_url(segment_desc, 'segment'))

    @skipIfCustomOrganisation
    def test_reload_assets_matrix(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        segment_desc = self._create_segment_desc(strategy, 'Industry')
        asset = CommercialAsset.objects.create(name='Size', strategy=strategy)

        orga = Organisation.objects.create(user=user, name='Nerv')
        strategy.evaluated_orgas.add(orga)
        self._set_asset_score(strategy, orga, asset, segment_desc, 1)

        brick_id = AssetsMatrixBrick.id_
        response = self.assertGET200(
            reverse('commercial__reload_matrix_brick', args=(strategy.id, orga.id)),
            data={'brick_id': brick_id},
        )

        result = response.json()
        self.assertIsList(result, length=1)

        result = result[0]
        self.assertIsList(result, length=2)
        self.assertEqual(brick_id, result[0])
        self.get_brick_node(self.get_html_tree(result[1]), brick_id)

    @skipIfCustomOrganisation
    def test_reload_charms_matrix(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        segment_desc = self._create_segment_desc(strategy, 'Industry')
        charm = MarketSegmentCharm.objects.create(name='Dollars', strategy=strategy)

        orga = Organisation.objects.create(user=self.user, name='Nerv')
        strategy.evaluated_orgas.add(orga)
        self._set_charm_score(strategy, orga, charm, segment_desc, 1)

        brick_id = CharmsMatrixBrick.id_
        response = self.assertGET200(
            reverse('commercial__reload_matrix_brick', args=(strategy.id, orga.id)),
            data={'brick_id': brick_id},
        )

        result = response.json()[0]
        self.assertEqual(brick_id, result[0])
        self.get_brick_node(self.get_html_tree(result[1]), brick_id)

    @skipIfCustomOrganisation
    def test_reload_assets_charms_matrix(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        segment_desc = self._create_segment_desc(strategy, 'Industry')
        asset = CommercialAsset.objects.create(name='Size', strategy=strategy)
        charm = MarketSegmentCharm.objects.create(name='Dollars', strategy=strategy)

        orga = Organisation.objects.create(user=self.user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self._set_asset_score(strategy, orga, asset, segment_desc, 1)
        self._set_charm_score(strategy, orga, charm, segment_desc, 1)

        brick_id = AssetsCharmsMatrixBrick.id_
        response = self.assertGET200(
            reverse('commercial__reload_matrix_brick', args=(strategy.id, orga.id)),
            data={'brick_id': brick_id},
        )

        result = response.json()[0]
        self.assertEqual(brick_id, result[0])
        self.get_brick_node(self.get_html_tree(result[1]), brick_id)
