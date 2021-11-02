# -*- coding: utf-8 -*-

from functools import partial

from django.template import Context, Template
from django.urls import reverse

from creme.commercial.models import CommercialAsset, MarketSegmentCharm

from .base import (
    CommercialBaseTestCase,
    Organisation,
    Strategy,
    skipIfCustomStrategy,
)


@skipIfCustomStrategy
class CommercialTagsTestCase(CommercialBaseTestCase):
    def test_segments_for_category(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')

        industry   = self._create_segment_desc(strategy, 'Industry')
        individual = self._create_segment_desc(strategy, 'Individual')
        community  = self._create_segment_desc(strategy, 'Community')
        self._create_segment_desc(strategy, 'Association')

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

        with self.assertNoException():
            render = Template(
                r'{% load commercial_tags %}'
                r'{% commercial_segments_for_category strategy orga 1 as segments_1 %}'
                r'<ul>'
                r'{% for segment in segments_1 %}'
                r'  <li data-segment="{{segment.id}}">{{segment}}</li>'
                r'{% endfor %}'
                r'</ul>'
                r'{% commercial_segments_for_category strategy orga 2 as segments_2 %}'
                r'<ul>'
                r'{% for segment in segments_2 %}'
                r'  <li data-segment="{{segment.id}}">{{segment}}</li>'
                r'{% endfor %}'
                r'</ul>'
            ).render(Context({'strategy': strategy, 'orga': orga}))

        self.assertHTMLEqual(
            f'<ul><li data-segment="{industry.id}">Industry</li></ul>'
            f'<ul><li data-segment="{community.id}">Community</li></ul>',
            render,
        )

    def test_widget_asset_score(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        industry = self._create_segment_desc(strategy, 'Industry')
        asset = CommercialAsset.objects.create(name='Capital', strategy=strategy)

        orga = Organisation.objects.create(user=user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self._set_asset_score(strategy, orga, asset, industry, 4)

        with self.assertNoException():
            template = Template(
                r'{% load commercial_tags %}'
                r'{% commercial_widget_asset_score seg_desc asset %}'
            )

        ctxt = Context({
            'user': user,
            'strategy': strategy,
            'orga': orga,
            'seg_desc': industry,
            'asset': asset,
        })

        with self.assertNoException():
            render1 = template.render(ctxt)

        url = reverse('commercial__set_asset_score', args=(strategy.id,))
        self.assertHTMLEqual(
            f'''
<select onchange="creme.commercial.setScore(this, '{url}', {asset.id}, {industry.id}, {orga.id});">
  <option value="1">1</option>
  <option value="2">2</option>
  <option value="3">3</option>
  <option value="4" selected>4</option>
</select>''', # NOQA
            render1,
        )

        # ---
        ctxt['user'] = self.other_user
        with self.assertNoException():
            render2 = template.render(ctxt)

        self.assertHTMLEqual(
            '<select disabled="true">'
            '  <option value="1">1</option>'
            '  <option value="2">2</option>'
            '  <option value="3">3</option>'
            '  <option value="4" selected>4</option>'
            '</select>',
            render2,
        )

    def test_widget_charm_score(self):
        user = self.login()
        strategy = Strategy.objects.create(user=user, name='Strat#1')
        industry = self._create_segment_desc(strategy, 'Industry')
        charm = MarketSegmentCharm.objects.create(strategy=strategy, name='Money')

        orga = Organisation.objects.create(user=user, name='Nerv')
        strategy.evaluated_orgas.add(orga)

        self._set_charm_score(strategy, orga, charm, industry, 3)

        with self.assertNoException():
            template = Template(
                r'{% load commercial_tags %}'
                r'{% commercial_widget_charm_score seg_desc charm %}'
            )

        ctxt = Context({
            'user': user,
            'strategy': strategy,
            'orga': orga,
            'seg_desc': industry,
            'charm': charm,
        })

        with self.assertNoException():
            render1 = template.render(ctxt)

        url = reverse('commercial__set_charm_score', args=(strategy.id,))
        self.assertHTMLEqual(
            f'''
<select onchange="creme.commercial.setScore(this, '{url}', {charm.id}, {industry.id}, {orga.id});">
  <option value="1">1</option>
  <option value="2">2</option>
  <option value="3" selected>3</option>
  <option value="4">4</option>
</select>''', # NOQA
            render1,
        )

        # ---
        ctxt['user'] = self.other_user
        with self.assertNoException():
            render2 = template.render(ctxt)

        self.assertHTMLEqual(
            '<select disabled="true">'
            '  <option value="1">1</option>'
            '  <option value="2">2</option>'
            '  <option value="3" selected>3</option>'
            '  <option value="4">4</option>'
            '</select>',
            render2,
        )
