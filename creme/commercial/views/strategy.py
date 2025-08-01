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

from django.db.transaction import atomic
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

import creme.creme_core.views.bricks as bricks_views
from creme.creme_core.core.workflow import run_workflow_engine
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic
from creme.persons import get_organisation_model

from .. import bricks as com_bricks
from .. import custom_forms, get_strategy_model
from ..constants import DEFAULT_HFILTER_STRATEGY
from ..forms import strategy as forms
from ..models import (
    CommercialAsset,
    CommercialAssetScore,
    MarketSegment,
    MarketSegmentCharm,
    MarketSegmentCharmScore,
    MarketSegmentDescription,
)

Strategy = get_strategy_model()


class StrategyCreation(generic.EntityCreation):
    model = Strategy
    form_class = custom_forms.STRATEGY_CREATION_CFORM


class StrategyDetail(generic.EntityDetail):
    model = Strategy
    template_name = 'commercial/view_strategy.html'
    pk_url_kwarg = 'strategy_id'


class StrategyEdition(generic.EntityEdition):
    model = Strategy
    form_class = custom_forms.STRATEGY_EDITION_CFORM
    pk_url_kwarg = 'strategy_id'


class StrategiesList(generic.EntitiesList):
    model = Strategy
    default_headerfilter_id = DEFAULT_HFILTER_STRATEGY


class _AddToStrategy(generic.AddingInstanceToEntityPopup):
    entity_id_url_kwarg = 'strategy_id'
    entity_classes = Strategy


class SegmentDescCreation(_AddToStrategy):
    model = MarketSegment
    form_class = forms.SegmentCreationForm
    title = _('New market segment for «{entity}»')


class SegmentLinking(_AddToStrategy):
    model = MarketSegmentDescription
    form_class = forms.SegmentLinkingForm
    title = _('New market segment for «{entity}»')


class AssetCreation(_AddToStrategy):
    model = CommercialAsset
    form_class = forms.AssetForm
    title = _('New commercial asset for «{entity}»')


class CharmCreation(_AddToStrategy):
    model = MarketSegmentCharm
    form_class = forms.CharmForm
    title = _('New segment charm for «{entity}»')


class EvaluatedOrgaAdding(generic.RelatedToEntityFormPopup):
    form_class = forms.AddOrganisationForm
    template_name = 'creme_core/generics/blockform/link-popup.html'
    title = _('New organisation(s) for «{entity}»')
    submit_label = _('Link the organisations')
    entity_id_url_kwarg = 'strategy_id'
    entity_classes = Strategy


class SegmentDescEdition(generic.RelatedToEntityEditionPopup):
    model = MarketSegmentDescription
    form_class = forms.SegmentEditionForm
    permissions = 'commercial'
    pk_url_kwarg = 'segdesc_id'
    title = _('Segment for «{entity}»')


class AssetEdition(generic.RelatedToEntityEditionPopup):
    model = CommercialAsset
    form_class = forms.AssetForm
    permissions = 'commercial'
    pk_url_kwarg = 'asset_id'
    title = _('Asset for «{entity}»')


class CharmEdition(generic.RelatedToEntityEditionPopup):
    model = MarketSegmentCharm
    form_class = forms.CharmForm
    permissions = 'commercial'
    pk_url_kwarg = 'charm_id'
    title = _('Charm for «{entity}»')


class OrganisationRemoving(generic.base.EntityRelatedMixin, generic.CremeDeletion):
    permissions = 'emails'
    entity_classes = Strategy
    entity_id_url_kwarg = 'strategy_id'

    organisation_id_arg = 'id'

    def perform_deletion(self, request):
        orga_id = get_from_POST_or_404(request.POST, self.organisation_id_arg, cast=int)
        strategy = self.get_related_entity()

        with atomic(), run_workflow_engine(user=request.user):
            strategy.evaluated_orgas.remove(orga_id)
            CommercialAssetScore.objects.filter(
                asset__strategy=strategy, organisation=orga_id,
            ).delete()
            MarketSegmentCharmScore.objects.filter(
                charm__strategy=strategy, organisation=orga_id,
            ).delete()


class BaseEvaluatedOrganisationView(generic.BricksView):
    permissions = 'commercial'
    bricks_reload_url_name = 'commercial__reload_matrix_brick'
    orga_id_url_kwarg = 'orga_id'
    strategy_id_url_kwarg = 'strategy_id'

    def get_bricks_reload_url(self):
        return reverse(
            self.bricks_reload_url_name,
            args=(self.get_strategy().id, self.get_organisation().id)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['strategy'] = self.get_strategy()
        context['orga'] = self.get_organisation()

        return context

    def get_organisation(self):
        try:
            orga = self.organisation  # NOQA
        except AttributeError:
            orga_id = self.kwargs[self.orga_id_url_kwarg]
            strategy = self.get_strategy()

            try:
                self.organisation = orga = strategy.evaluated_orgas.get(id=orga_id)
            except get_organisation_model().DoesNotExist:
                raise Http404(gettext(
                    'This organisation «{orga}» is not (no more?) evaluated by '
                    'the strategy «{strategy}»').format(
                    orga=orga_id, strategy=strategy,
                ))

            self.request.user.has_perm_to_view_or_die(orga)

        return orga

    def get_strategy(self):
        try:
            strategy = self.strategy  # NOQA
        except AttributeError:
            self.strategy = strategy = get_object_or_404(
                Strategy,
                pk=self.kwargs[self.strategy_id_url_kwarg],
            )
            self.request.user.has_perm_to_view_or_die(strategy)

        return strategy


class OrgaEvaluation(BaseEvaluatedOrganisationView):
    template_name = 'commercial/orga_evaluation.html'


class OrgaSynthesis(BaseEvaluatedOrganisationView):
    template_name = 'commercial/orga_synthesis.html'


class BaseScoreSetting(generic.base.EntityRelatedMixin, generic.CheckedView):
    permissions = 'commercial'
    entity_id_url_kwarg = 'strategy_id'
    entity_classes = Strategy
    entity_select_for_update = True

    model_id_arg = 'model_id'
    segment_desc_id_arg = 'segment_desc_id'
    score_arg = 'score'
    orga_id_arg = 'orga_id'

    def get_update_kwargs(self):
        POST = self.request.POST

        return {
            'segment_desc_id': get_from_POST_or_404(POST, self.segment_desc_id_arg, int),
            'orga_id':         get_from_POST_or_404(POST, self.orga_id_arg, int),
            'score':           get_from_POST_or_404(POST, self.score_arg, int),
        }

    @atomic
    def post(self, request, **kwargs):
        strategy = self.get_related_entity()
        model_id = get_from_POST_or_404(request.POST, self.model_id_arg, int)

        try:
            self.update_strategy(
                strategy=strategy,
                model_id=model_id,
                **self.get_update_kwargs()
            )
        except Exception as e:
            raise Http404(str(e)) from e

        return HttpResponse()

    def update_strategy(self, *, strategy, model_id, **kwargs):
        raise NotImplementedError


class AssetScoreSetting(BaseScoreSetting):
    def update_strategy(self, *, strategy, model_id, **kwargs):
        strategy.set_asset_score(asset_id=model_id, **kwargs)


class CharmScoreSetting(BaseScoreSetting):
    def update_strategy(self, *, strategy, model_id, **kwargs):
        strategy.set_charm_score(charm_id=model_id, **kwargs)


class SegmentCategorySetting(generic.base.EntityRelatedMixin, generic.CheckedView):
    permissions = 'commercial'
    entity_id_url_kwarg = 'strategy_id'
    entity_classes = Strategy
    entity_select_for_update = True

    segment_desc_id_arg = 'segment_desc_id'
    orga_id_arg = 'orga_id'
    category_id_arg = 'category'

    @atomic
    def post(self, request, **kwargs):
        strategy = self.get_related_entity()

        POST = request.POST
        segment_desc_id = get_from_POST_or_404(POST, self.segment_desc_id_arg, int)
        orga_id         = get_from_POST_or_404(POST, self.orga_id_arg,         int)
        category        = get_from_POST_or_404(POST, self.category_id_arg,     int)

        try:
            strategy.set_segment_category(segment_desc_id, orga_id, category)
        except Exception as e:
            raise Http404(str(e)) from e

        return HttpResponse()


class MatrixBricksReloading(bricks_views.BricksReloading):
    permissions = 'commercial'
    strategy_id_url_kwarg = 'strategy_id'
    orga_id_url_kwarg     = 'orga_id'
    allowed_bricks = {
        com_bricks.AssetsMatrixBrick.id:       com_bricks.AssetsMatrixBrick,
        com_bricks.CharmsMatrixBrick.id:       com_bricks.CharmsMatrixBrick,
        com_bricks.AssetsCharmsMatrixBrick.id: com_bricks.AssetsCharmsMatrixBrick,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.strategy     = None
        self.organisation = None

    def get_bricks(self):
        bricks = []
        allowed_bricks = self.allowed_bricks

        for brick_id in self.get_brick_ids():
            try:
                brick_cls = allowed_bricks[brick_id]
            except KeyError as e:
                raise Http404('Invalid brick ID') from e

            bricks.append(brick_cls())

        return bricks

    def get_bricks_context(self):
        context = super().get_bricks_context()
        context['orga'] = self.get_organisation()
        context['strategy'] = self.get_strategy()

        return context

    def get_organisation(self):
        orga = self.organisation

        if orga is None:
            self.organisation = orga = get_object_or_404(
                get_organisation_model(),
                pk=self.kwargs[self.orga_id_url_kwarg],
            )
            self.request.user.has_perm_to_view_or_die(orga)

        return orga

    def get_strategy(self):
        strategy = self.strategy

        if strategy is None:
            self.strategy = strategy = get_object_or_404(
                Strategy,
                pk=self.kwargs[self.strategy_id_url_kwarg],
            )
            self.request.user.has_perm_to_view_or_die(strategy)

        return strategy
