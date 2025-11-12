################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from itertools import chain

from django.utils.translation import gettext_lazy as _

from creme import commercial
from creme.creme_core.gui.bricks import (
    PaginatedBrick,
    QuerysetBrick,
    SimpleBrick,
)
from creme.creme_core.models import Relation, RelationType, SettingValue
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
)
from .setting_keys import orga_approaches_key

Opportunity = get_opportunity_model()
Act = commercial.get_act_model()
ActObjectivePattern = commercial.get_pattern_model()
Strategy = commercial.get_strategy_model()


class ApproachesBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('commercial', 'approaches')
    verbose_name = _('Commercial approaches')
    # description = TODO
    dependencies = (CommercialApproach,)
    permissions = 'commercial'
    order_by = '-creation_date'
    template_name = 'commercial/bricks/approaches.html'

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
        return self._render(self.get_template_context(
            context,
            CommercialApproach.get_approaches().prefetch_related('creme_entity'),
        ))


class SegmentsBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('commercial', 'segments')
    verbose_name = _('Market segments')
    dependencies = (MarketSegment,)
    order_by = 'name'
    template_name = 'commercial/bricks/segments.html'
    configurable = False
    # NB: used by the view <creme_core.views.bricks.BricksReloading>
    permissions = 'commercial'

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context, MarketSegment.objects.all(),
        ))


class SegmentDescriptionsBrick(PaginatedBrick):
    id = PaginatedBrick.generate_id('commercial', 'segment_info')
    verbose_name = _('Market segment descriptions')
    dependencies = (MarketSegment,)  # MarketSegmentDescription ??
    template_name = 'commercial/bricks/segments-info.html'
    target_ctypes = (Strategy,)
    permissions = 'commercial'

    def detailview_display(self, context):
        strategy = context['object']
        return self._render(self.get_template_context(
            context, strategy.get_segment_descriptions_list(),
        ))


class AssetsBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('commercial', 'assets')
    verbose_name = _('Commercial assets')
    dependencies = (CommercialAsset,)
    order_by = 'name'
    template_name = 'commercial/bricks/assets.html'
    target_ctypes = (Strategy,)
    permissions = 'commercial'

    def detailview_display(self, context):
        strategy = context['object']
        return self._render(self.get_template_context(
            context, strategy.assets.all(),
        ))


class CharmsBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('commercial', 'charms')
    verbose_name = _('Segment charms')
    dependencies = (MarketSegmentCharm,)
    order_by = 'name'
    template_name = 'commercial/bricks/charms.html'
    target_ctypes = (Strategy,)
    permissions = 'commercial'

    def detailview_display(self, context):
        strategy = context['object']
        return self._render(self.get_template_context(
            context, strategy.charms.all(),
        ))


class EvaluatedOrgasBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('commercial', 'evaluated_orgas')
    verbose_name = _('Evaluated organisations')
    dependencies = (MarketSegmentCharm,)
    order_by = 'name'
    template_name = 'commercial/bricks/evaluated-organisations.html'
    target_ctypes = (Strategy,)
    permissions = 'commercial'

    def detailview_display(self, context):
        strategy = context['object']

        return self._render(self.get_template_context(
            context, strategy.evaluated_orgas.all(),
        ))


class AssetsMatrixBrick(SimpleBrick):
    id = SimpleBrick.generate_id('commercial', 'assets_matrix')
    verbose_name = _('Assets / Segments matrix')
    # dependencies  = (CommercialAsset,) #useless (custom reload view....)
    template_name = 'commercial/bricks/assets-matrix.html'
    configurable = False
    permissions = 'commercial'

    def get_template_context(self, context, **extra_kwargs):
        # NB: credentials are OK : we are sure to use the custom reload view
        #     if 'strategy' & 'orga' are in the context
        strategy = context['strategy']
        orga = context['orga']

        return super().get_template_context(
            context,
            assets=strategy.get_assets_list(),
            segment_info=strategy.get_segment_descriptions_list(),
            totals=strategy.get_assets_totals(orga),
            **extra_kwargs
        )


class CharmsMatrixBrick(SimpleBrick):
    id = SimpleBrick.generate_id('commercial', 'charms_matrix')
    verbose_name = _('Charms / Segments matrix')
    # dependencies = (MarketSegmentCharm,) #useless (custom reload view....)
    template_name = 'commercial/bricks/charms-matrix.html'
    configurable = False
    permissions = 'commercial'

    def get_template_context(self, context, **extra_kwargs):
        # NB: credentials are OK : we are sure to use the custom reload view
        #     if 'strategy' & 'orga' are in the context
        strategy = context['strategy']
        orga = context['orga']

        return super().get_template_context(
            context,
            charms=strategy.get_charms_list(),
            segment_info=strategy.get_segment_descriptions_list(),
            totals=strategy.get_charms_totals(orga),
            **extra_kwargs
        )


class AssetsCharmsMatrixBrick(SimpleBrick):
    id = SimpleBrick.generate_id('commercial', 'assets_charms_matrix')
    verbose_name = _('Assets / Charms matrix')
    # dependencies = (CommercialAsset, MarketSegmentCharm,) #useless (custom reload view....)
    template_name = 'commercial/bricks/assets-charms-matrix.html'
    configurable = False
    permissions = 'commercial'

    def get_template_context(self, context, **extra_kwargs):
        return super().get_template_context(
            context,
            # NB: credentials are OK; we are sure to use the custom reload view
            #     if 'strategy' is in the context
            segment_info=context['strategy'].get_segment_descriptions_list(),
            **extra_kwargs
        )


class ActObjectivesBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('commercial', 'objectives')
    verbose_name = _('Objectives of a Commercial Action')
    # NB: would be cool to add the Relation dependency only if needed
    #     (i.e. one of the listed objectives uses relationships), but
    #     modifying self.dependencies during the render is ugly.
    dependencies = (ActObjective, Relation)
    relation_type_deps = (REL_OBJ_COMPLETE_GOAL,)
    order_by = 'name'
    template_name = 'commercial/bricks/objectives.html'
    target_ctypes = (Act,)
    permissions = 'commercial'

    def detailview_display(self, context):
        act_id = context['object'].id
        # TODO: pre-populate EntityFilters ??
        return self._render(self.get_template_context(
            context,
            # NB: "act.objectives.all()" causes a strange additional query...
            ActObjective.objects.filter(act=act_id),
        ))


class RelatedOpportunitiesBrick(PaginatedBrick):
    id = PaginatedBrick.generate_id('commercial', 'opportunities')
    verbose_name = _('Opportunities related to a Commercial Action')
    dependencies = (Relation, Opportunity)
    relation_type_deps = (REL_OBJ_COMPLETE_GOAL,)
    template_name = 'commercial/bricks/opportunities.html'
    target_ctypes = (Act,)
    permissions = 'commercial'

    def detailview_display(self, context):
        act = context['object']

        return self._render(self.get_template_context(
            context, act.get_related_opportunities(),
            relation_type=RelationType.objects.get(id=REL_OBJ_COMPLETE_GOAL),
        ))


class PatternComponentsBrick(SimpleBrick):
    id = SimpleBrick.generate_id('commercial', 'pattern_components')
    verbose_name = _('Components of an Objective Pattern')
    dependencies = (ActObjectivePatternComponent,)
    template_name = 'commercial/bricks/components.html'
    target_ctypes = (ActObjectivePattern,)
    permissions = 'commercial'

    def _get_flattened_tree(self, pattern):
        flattened_tree = []

        def explore_tree(components, deep):
            for comp in components:
                comp.deep = deep
                flattened_tree.append(comp)
                explore_tree(comp.get_children(), deep + 1)

        explore_tree(pattern.get_components_tree(), 0)

        return flattened_tree

    def get_template_context(self, context, **extra_kwargs):
        return super().get_template_context(
            context,
            components=self._get_flattened_tree(pattern=context['object']),
            **extra_kwargs
        )
