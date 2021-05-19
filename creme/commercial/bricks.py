# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from collections import defaultdict
from itertools import chain

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from creme import commercial
from creme.creme_core.gui.bricks import Brick, PaginatedBrick, QuerysetBrick
from creme.creme_core.models import Relation, SettingValue
from creme.opportunities import get_opportunity_model
from creme.opportunities.constants import REL_SUB_TARGETS
from creme.persons import get_organisation_model

from .constants import REL_OBJ_COMPLETE_GOAL
from .models import (
    ActObjective,
    ActObjectivePatternComponent,
    CommercialApproach,
    CommercialAsset,
    MarketSegment,
    MarketSegmentCharm,
    MarketSegmentDescription,
)
from .setting_keys import orga_approaches_key

get_ct = ContentType.objects.get_for_model
Opportunity = get_opportunity_model()
Act = commercial.get_act_model()
ActObjectivePattern = commercial.get_pattern_model()
Strategy = commercial.get_strategy_model()


class ApproachesBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('commercial', 'approaches')
    verbose_name = _('Commercial approaches')
    # description = TODO
    dependencies = (CommercialApproach,)
    # order_by = 'title'
    order_by = '-creation_date'
    template_name = 'commercial/bricks/approaches.html'

    # TODO: factorise with assistants blocks (CremeEntity method ??)
    @staticmethod
    def _populate_related_real_entities(comapps, user):
        entities_ids_by_ct = defaultdict(set)

        for comapp in comapps:
            entities_ids_by_ct[comapp.entity_content_type_id].add(comapp.entity_id)

        entities_map = {}
        get_ct = ContentType.objects.get_for_id

        for ct_id, entities_ids in entities_ids_by_ct.items():
            entities_map.update(get_ct(ct_id).model_class().objects.in_bulk(entities_ids))

        for comapp in comapps:
            comapp.creme_entity = entities_map[comapp.entity_id]

    def detailview_display(self, context):
        entity = context['object']
        pk = entity.pk

        if isinstance(entity, get_organisation_model()) and \
           not SettingValue.objects.get_4_key(orga_approaches_key, default=True).value:
            # TODO: regroup the queries
            managers_ids  = entity.get_managers().values_list('id', flat=True)
            employees_ids = entity.get_employees().values_list('id', flat=True)
            opportunities_ids = Opportunity.objects.filter(
                relations__type=REL_SUB_TARGETS, relations__object_entity=entity,
            ).values_list('id', flat=True)

            approaches = CommercialApproach.objects.filter(
                entity_id__in=chain([pk], managers_ids, employees_ids, opportunities_ids),
            )
        else:
            approaches = CommercialApproach.get_approaches(pk)

        return self._render(self.get_template_context(context, approaches))

    def home_display(self, context):
        btc = self.get_template_context(
            context, CommercialApproach.get_approaches(),
        )
        self._populate_related_real_entities(btc['page'].object_list, context['user'])

        return self._render(btc)


class SegmentsBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('commercial', 'segments')
    verbose_name = _('Market segments')
    dependencies = (MarketSegment,)
    order_by = 'name'
    template_name = 'commercial/bricks/segments.html'
    configurable = False
    # permission = 'commercial'
    permissions = 'commercial'  # NB: used by the view creme_core.views.blocks.reload_basic

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context, MarketSegment.objects.all(),
        ))


class SegmentDescriptionsBrick(PaginatedBrick):
    id_ = QuerysetBrick.generate_id('commercial', 'segment_info')
    verbose_name = _('Market segment descriptions')
    dependencies = (MarketSegment,)  # MarketSegmentDescription ??
    template_name = 'commercial/bricks/segments-info.html'
    target_ctypes = (Strategy,)

    def detailview_display(self, context):
        strategy = context['object']
        return self._render(self.get_template_context(
            context, strategy.get_segment_descriptions_list(),
            ct_id=get_ct(MarketSegmentDescription).id,
        ))


class AssetsBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('commercial', 'assets')
    verbose_name = _('Commercial assets')
    dependencies = (CommercialAsset,)
    order_by = 'name'
    template_name = 'commercial/bricks/assets.html'
    target_ctypes = (Strategy,)

    def detailview_display(self, context):
        strategy = context['object']
        return self._render(self.get_template_context(
            context, strategy.assets.all(),
        ))


class CharmsBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('commercial', 'charms')
    verbose_name = _('Segment charms')
    dependencies = (MarketSegmentCharm,)
    order_by = 'name'
    template_name = 'commercial/bricks/charms.html'
    target_ctypes = (Strategy,)

    def detailview_display(self, context):
        strategy = context['object']
        return self._render(self.get_template_context(
            context, strategy.charms.all(),
        ))


class EvaluatedOrgasBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('commercial', 'evaluated_orgas')
    verbose_name = _('Evaluated organisations')
    dependencies = (MarketSegmentCharm,)
    order_by = 'name'
    template_name = 'commercial/bricks/evaluated-organisations.html'
    target_ctypes = (Strategy,)

    def detailview_display(self, context):
        strategy = context['object']

        return self._render(self.get_template_context(
            context, strategy.evaluated_orgas.all(),
        ))


class AssetsMatrixBrick(Brick):
    id_ = Brick.generate_id('commercial', 'assets_matrix')
    verbose_name = _('Assets / Segments matrix')
    # dependencies  = (CommercialAsset,) #useless (custom reload view....)
    template_name = 'commercial/bricks/assets-matrix.html'
    configurable = False

    def detailview_display(self, context):
        # NB: credentials are OK : we are sure to use the custom reload view
        #     if 'strategy' & 'orga' are in the context
        strategy = context['strategy']
        orga = context['orga']
        return self._render(self.get_template_context(
            context,
            assets=strategy.get_assets_list(),
            segment_info=strategy.get_segment_descriptions_list(),
            totals=strategy.get_assets_totals(orga),
        ))


class CharmsMatrixBrick(Brick):
    id_ = Brick.generate_id('commercial', 'charms_matrix')
    verbose_name = _('Charms / Segments matrix')
    # dependencies = (MarketSegmentCharm,) #useless (custom reload view....)
    template_name = 'commercial/bricks/charms-matrix.html'
    configurable = False

    def detailview_display(self, context):
        # NB: credentials are OK : we are sure to use the custom reload view
        #     if 'strategy' & 'orga' are in the context
        strategy = context['strategy']
        orga = context['orga']
        return self._render(self.get_template_context(
            context,
            charms=strategy.get_charms_list(),
            segment_info=strategy.get_segment_descriptions_list(),
            totals=strategy.get_charms_totals(orga),
        ))


class AssetsCharmsMatrixBrick(Brick):
    id_ = Brick.generate_id('commercial', 'assets_charms_matrix')
    verbose_name = _('Assets / Charms matrix')
    # dependencies = (CommercialAsset, MarketSegmentCharm,) #useless (custom reload view....)
    template_name = 'commercial/bricks/assets-charms-matrix.html'
    configurable = False

    def detailview_display(self, context):
        # NB: credentials are OK : we are sure to use the custom reload view
        #     if 'strategy' & 'orga' are in the context
        strategy = context['strategy']
        return self._render(self.get_template_context(
            context,
            segment_info=strategy.get_segment_descriptions_list(),
        ))


class ActObjectivesBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('commercial', 'objectives')
    verbose_name = _('Objectives of a Commercial Action')
    # NB: would be cool to add the Relation dependency only if needed
    #     (ie: one of the listed objectives uses relationships), but
    #     modifying self.dependencies during the render is ugly.
    dependencies = (ActObjective, Relation)
    relation_type_deps = (REL_OBJ_COMPLETE_GOAL,)
    order_by = 'name'
    template_name = 'commercial/bricks/objectives.html'
    target_ctypes = (Act,)

    def detailview_display(self, context):
        act_id = context['object'].id
        # TODO: pre-populate EntityFilters ??
        return self._render(self.get_template_context(
            context,
            # NB: "act.objectives.all()" causes a strange additional query...
            ActObjective.objects.filter(act=act_id),
            ct_id=get_ct(ActObjective).id,
        ))


class RelatedOpportunitiesBrick(PaginatedBrick):
    id_ = PaginatedBrick.generate_id('commercial', 'opportunities')
    verbose_name = _('Opportunities related to a Commercial Action')
    dependencies = (Relation, Opportunity)
    relation_type_deps = (REL_OBJ_COMPLETE_GOAL,)
    template_name = 'commercial/bricks/opportunities.html'
    target_ctypes = (Act,)

    def detailview_display(self, context):
        act = context['object']

        return self._render(self.get_template_context(
            context, act.get_related_opportunities(),
            predicate_id=REL_OBJ_COMPLETE_GOAL,
        ))


class PatternComponentsBrick(Brick):
    id_ = Brick.generate_id('commercial', 'pattern_components')
    verbose_name = _('Components of an Objective Pattern')
    dependencies = (ActObjectivePatternComponent,)
    template_name = 'commercial/bricks/components.html'
    target_ctypes = (ActObjectivePattern,)

    def detailview_display(self, context):
        pattern = context['object']
        flattened_tree = []

        def explore_tree(components, deep):
            for comp in components:
                comp.deep = deep
                flattened_tree.append(comp)
                explore_tree(comp.get_children(), deep + 1)

        explore_tree(pattern.get_components_tree(), 0)

        return self._render(self.get_template_context(
            context,
            components=flattened_tree,
            ct_id=get_ct(ActObjectivePatternComponent).id,
        ))
