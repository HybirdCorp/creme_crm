# -*- coding: utf-8 -*-

import warnings

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.gui.block import PaginatedBlock
from creme.creme_core.models import Relation

from creme.opportunities import get_opportunity_model

from . import get_act_model
from .bricks import (
    ApproachesBrick as ApproachesBlock,
    SegmentsBrick as SegmentsBlock,
    SegmentDescriptionsBrick as SegmentDescriptionsBlock,
    AssetsBrick as AssetsBlock,
    CharmsBrick as CharmsBlock,
    EvaluatedOrgasBrick as EvaluatedOrgasBlock,
    AssetsMatrixBrick as AssetsMatrixBlock,
    CharmsMatrixBrick as CharmsMatrixBlock,
    AssetsCharmsMatrixBrick as AssetsCharmsMatrixBlock,
    ActObjectivesBrick as ActObjectivesBlock,
    PatternComponentsBrick as PatternComponentsBlock,
)
from .constants import  REL_OBJ_COMPLETE_GOAL


warnings.warn('commercial.blocks is deprecated ; use commercial.bricks instead.', DeprecationWarning)

Opportunity = get_opportunity_model()
Act = get_act_model()
get_ct = ContentType.objects.get_for_model


class RelatedOpportunitiesBlock(PaginatedBlock):
    id_           = PaginatedBlock.generate_id('commercial', 'opportunities')
    dependencies  = (Relation, Opportunity)
    # NB: the relation_type_deps is commented because it avoid the RelationsBlock
    #     to display the entities link with this RelationType, so when they are
    #     Opportunities these entities are not displayed at all on the detailview
    # => Problem the block is not reloaded when a Relationship is created from
    #    the RelationsBlock....
    # relation_type_deps = (REL_OBJ_COMPLETE_GOAL,)
    verbose_name  = _(u'Opportunities related to a Commercial Action')
    template_name = 'commercial/templatetags/block_opportunities.html'
    target_ctypes = (Act,)

    # _OPPORT_CT = get_ct(Opportunity)

    def detailview_display(self, context):
        act = context['object']

        return self._render(self.get_block_template_context(
                        context, act.get_related_opportunities(),
                        update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, act.pk),
                        predicate_id=REL_OBJ_COMPLETE_GOAL,
                        # opp_ct=self._OPPORT_CT,
                        opp_ct=get_ct(Opportunity),
                       )
                    )

approaches_block            = ApproachesBlock()
segment_descriptions_block  = SegmentDescriptionsBlock()
assets_block                = AssetsBlock()
charms_block                = CharmsBlock()
evaluated_orgas_block       = EvaluatedOrgasBlock()
assets_matrix_block         = AssetsMatrixBlock()
charms_matrix_block         = CharmsMatrixBlock()
assets_charms_matrix_block  = AssetsCharmsMatrixBlock()
act_objectives_block        = ActObjectivesBlock()
related_opportunities_block = RelatedOpportunitiesBlock()
pattern_components_block    = PatternComponentsBlock()


blocks_list = (
    approaches_block,
    SegmentsBlock(),
    segment_descriptions_block,
    assets_block,
    charms_block,
    evaluated_orgas_block,
    assets_matrix_block,
    charms_matrix_block,
    assets_charms_matrix_block,
    act_objectives_block,
    related_opportunities_block,
    pattern_components_block,
)
