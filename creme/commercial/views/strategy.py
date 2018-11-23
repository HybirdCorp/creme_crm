# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

import warnings

from django.db.transaction import atomic
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect  # render
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.views import bricks
from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.utils import get_from_POST_or_404, get_from_GET_or_404, jsonify
from creme.creme_core.views import generic
from creme.creme_core.views.decorators import POST_only

from creme.persons import get_organisation_model

from .. import get_strategy_model
from ..bricks import AssetsMatrixBrick, CharmsMatrixBrick, AssetsCharmsMatrixBrick
from ..constants import DEFAULT_HFILTER_STRATEGY
from ..forms import strategy as forms
from ..models import (MarketSegment, MarketSegmentDescription, CommercialAsset, CommercialAssetScore,
        MarketSegmentCharm, MarketSegmentCharmScore)


Strategy = get_strategy_model()

# Function views --------------------------------------------------------------


def abstract_add_strategy(request, form=forms.StrategyForm,
                          submit_label=Strategy.save_label,
                         ):
    warnings.warn('commercial.views.strategy.abstract_add_strategy() is deprecated ; '
                  'use the class-based view StrategyCreation instead.',
                  DeprecationWarning
                 )
    return generic.add_entity(request, form,
                              extra_template_dict={'submit_label': submit_label},
                             )


def abstract_edit_strategy(request, strategy_id, form=forms.StrategyForm):
    warnings.warn('commercial.views.strategy.abstract_edit_strategy() is deprecated ; '
                  'use the class-based view StrategyCreation instead.',
                  DeprecationWarning
                 )
    return generic.edit_entity(request, strategy_id, Strategy, form)


def abstract_view_strategy(request, strategy_id,
                           template='commercial/view_strategy.html',
                          ):
    warnings.warn('commercial.views.strategy.abstract_view_strategy() is deprecated ; '
                  'use the class-based view StrategyDetail instead.',
                  DeprecationWarning
                 )
    return generic.view_entity(request, strategy_id, Strategy, template=template)


@login_required
@permission_required(('commercial', cperm(Strategy)))
def add(request):
    warnings.warn('commercial.views.strategy.add() is deprecated.', DeprecationWarning)
    return abstract_add_strategy(request)


@login_required
@permission_required('commercial')
def edit(request, strategy_id):
    warnings.warn('commercial.views.strategy.edit() is deprecated.', DeprecationWarning)
    return abstract_edit_strategy(request, strategy_id)


@login_required
@permission_required('commercial')
def detailview(request, strategy_id):
    warnings.warn('commercial.views.strategy.detailview() is deprecated.', DeprecationWarning)
    return abstract_view_strategy(request, strategy_id)


@login_required
@permission_required('commercial')
def listview(request):
    return generic.list_view(request, Strategy, hf_pk=DEFAULT_HFILTER_STRATEGY)


# Class-based views  ----------------------------------------------------------

class StrategyCreation(generic.EntityCreation):
    model = Strategy
    form_class = forms.StrategyForm


class StrategyDetail(generic.EntityDetail):
    model = Strategy
    template_name = 'commercial/view_strategy.html'
    pk_url_kwarg = 'strategy_id'


class StrategyEdition(generic.EntityEdition):
    model = Strategy
    form_class = forms.StrategyForm
    pk_url_kwarg = 'strategy_id'


class _AddToStrategy(generic.AddingInstanceToEntityPopup):
    entity_id_url_kwarg = 'strategy_id'
    entity_classes = Strategy


class SegmentDescCreation(_AddToStrategy):
    model = MarketSegment
    form_class = forms.SegmentCreateForm
    title_format = _('New market segment for «{}»')


class SegmentLinking(_AddToStrategy):
    model = MarketSegmentDescription
    form_class = forms.SegmentLinkForm
    title_format = _('New market segment for «{}»')


class AssetCreation(_AddToStrategy):
    model = CommercialAsset
    form_class = forms.AssetForm
    title_format = _('New commercial asset for «{}»')


class CharmCreation(_AddToStrategy):
    model = MarketSegmentCharm
    form_class = forms.CharmForm
    title_format = _('New segment charm for «{}»')


class EvaluatedOrgaAdding(generic.RelatedToEntityFormPopup):
    form_class = forms.AddOrganisationForm
    template_name = 'creme_core/generics/blockform/link-popup.html'
    title_format = _('New organisation(s) for «{}»')
    submit_label = _('Link the organisation(s)')
    entity_id_url_kwarg = 'strategy_id'
    entity_classes = Strategy


class SegmentDescEdition(generic.RelatedToEntityEditionPopup):
    model = MarketSegmentDescription
    form_class = forms.SegmentEditForm
    permissions = 'commercial'
    pk_url_kwarg = 'segdesc_id'
    title_format = _('Segment for «{}»')


class AssetEdition(generic.RelatedToEntityEditionPopup):
    model = CommercialAsset
    form_class = forms.AssetForm
    permissions = 'commercial'
    pk_url_kwarg = 'asset_id'
    title_format = _('Asset for «{}»')


class CharmEdition(generic.RelatedToEntityEditionPopup):
    model = MarketSegmentCharm
    form_class = forms.CharmForm
    permissions = 'commercial'
    pk_url_kwarg = 'charm_id'
    title_format = _('Charm for «{}»')


# Other views  ----------------------------------------------------------------

# @login_required
# @permission_required('commercial')
# def add_segment(request, strategy_id):
#     return generic.add_to_entity(request, strategy_id, forms.SegmentCreateForm,
#                                  ugettext('New market segment for «%s»'),
#                                  entity_class=Strategy,
#                                  submit_label=MarketSegment.save_label,
#                                 )


# @login_required
# @permission_required('commercial')
# def link_segment(request, strategy_id):
#     return generic.add_to_entity(request, strategy_id, forms.SegmentLinkForm,
#                                  ugettext('New market segment for «%s»'),
#                                  entity_class=Strategy,
#                                  submit_label=MarketSegment.save_label,  # todo: MarketSegmentDescription ?
#                                 )


# @login_required
# @permission_required('commercial')
# def add_asset(request, strategy_id):
#     return generic.add_to_entity(request, strategy_id, forms.AssetForm,
#                                  ugettext('New commercial asset for «%s»'),
#                                  entity_class=Strategy,
#                                  submit_label=CommercialAsset.save_label,
#                                 )


# @login_required
# @permission_required('commercial')
# def add_charm(request, strategy_id):
#     return generic.add_to_entity(request, strategy_id, forms.CharmForm,
#                                  ugettext('New segment charm for «%s»'),
#                                  entity_class=Strategy,
#                                  submit_label=MarketSegmentCharm.save_label,
#                                 )


# @login_required
# @permission_required('commercial')
# def add_evalorga(request, strategy_id):
#     return generic.add_to_entity(request, strategy_id, forms.AddOrganisationForm,
#                                  ugettext('New organisation(s) for «%s»'),
#                                  entity_class=Strategy,
#                                  submit_label=_('Link the organisation(s)'),
#                                  template='creme_core/generics/blockform/link_popup.html',
#                                 )


# @login_required
# @permission_required('commercial')
# def edit_segment(request, strategy_id, seginfo_id):
#     return generic.edit_related_to_entity(request, seginfo_id, MarketSegmentDescription,
#                                           forms.SegmentEditForm, ugettext('Segment for «%s»'),
#                                          )


# @login_required
# @permission_required('commercial')
# def edit_asset(request, asset_id):
#     return generic.edit_related_to_entity(request, asset_id, CommercialAsset,
#                                           forms.AssetForm, ugettext('Asset for «%s»'),
#                                          )


# @login_required
# @permission_required('commercial')
# def edit_charm(request, charm_id):
#     return generic.edit_related_to_entity(request, charm_id, MarketSegmentCharm,
#                                           forms.CharmForm, ugettext('Charm for «%s»'),
#                                          )


@login_required
@permission_required('commercial')
def delete_evalorga(request, strategy_id):
    strategy = get_object_or_404(Strategy, pk=strategy_id)
    request.user.has_perm_to_change_or_die(strategy)

    orga_id = get_from_POST_or_404(request.POST, 'id', int)
    strategy.evaluated_orgas.remove(orga_id)
    CommercialAssetScore.objects.filter(asset__strategy=strategy, organisation=orga_id).delete()
    MarketSegmentCharmScore.objects.filter(charm__strategy=strategy, organisation=orga_id).delete()

    if request.is_ajax():
        return HttpResponse()

    return redirect(strategy)


# TODO: used once => inline
def _get_strategy_n_orga(request, strategy_id, orga_id):
    strategy = get_object_or_404(Strategy, pk=strategy_id)
    has_perm = request.user.has_perm_to_view_or_die
    has_perm(strategy)

    orga = get_object_or_404(get_organisation_model(), pk=orga_id)
    has_perm(orga)

    return strategy, orga


# @login_required
# @permission_required('commercial')
# def _orga_view(request, strategy_id, orga_id, template):
#     strategy, orga = _get_strategy_n_orga(request, strategy_id, orga_id)
#
#     if not strategy.evaluated_orgas.filter(pk=orga_id).exists():
#         raise Http404(ugettext('This organisation «{orga}» is not (no more ?) evaluated by the strategy «{strategy}»').format(
#                             orga=orga, strategy=strategy)
#                      )
#
#     return render(request, template,
#                   context={'orga': orga,
#                            'strategy': strategy,
#                            'bricks_reload_url': reverse('commercial__reload_matrix_brick', args=(strategy.id, orga.id)),
#                           },
#                  )
class BaseEvaluatedOrganisationView(generic.BricksView):
    permissions = 'commercial'
    bricks_reload_url_name = 'commercial__reload_matrix_brick'
    orga_id_url_kwarg = 'orga_id'
    strategy_id_url_kwarg = 'strategy_id'

    def get_bricks_reload_url(self):
        return reverse('commercial__reload_matrix_brick',
                       args=(self.get_strategy().id, self.get_organisation().id)
                      )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['strategy'] = self.get_strategy()
        context['orga'] = self.get_organisation()

        return context

    def get_organisation(self):
        try:
            orga = getattr(self, 'organisation')
        except AttributeError:
            orga_id = self.kwargs[self.orga_id_url_kwarg]
            strategy = self.get_strategy()

            try:
                self.organisation = orga = strategy.evaluated_orgas.get(id=orga_id)
            except get_organisation_model().DoesNotExist:
                raise Http404(ugettext(
                    'This organisation «{orga}» is not (no more ?) evaluated by '
                    'the strategy «{strategy}»').format(
                    orga=orga_id, strategy=strategy,
                ))

            self.request.user.has_perm_to_view_or_die(orga)

        return orga

    def get_strategy(self):
        try:
            strategy = getattr(self, 'strategy')
        except AttributeError:
            self.strategy = strategy = \
                get_object_or_404(Strategy,
                                  pk=self.kwargs[self.strategy_id_url_kwarg],
                                 )
            self.request.user.has_perm_to_view_or_die(strategy)

        return strategy


# def orga_evaluation(request, strategy_id, orga_id):
#     return _orga_view(request, strategy_id, orga_id, 'commercial/orga_evaluation.html')
class OrgaEvaluation(BaseEvaluatedOrganisationView):
    template_name = 'commercial/orga_evaluation.html'


# def orga_synthesis(request, strategy_id, orga_id):
#     return _orga_view(request, strategy_id, orga_id, 'commercial/orga_synthesis.html')
class OrgaSynthesis(BaseEvaluatedOrganisationView):
    template_name = 'commercial/orga_synthesis.html'


@POST_only
@login_required
@permission_required('commercial')
@atomic
def _set_score(request, strategy_id, method_name):
    # strategy = get_object_or_404(Strategy, pk=strategy_id)
    strategy = get_object_or_404(Strategy.objects.select_for_update(), pk=strategy_id)

    request.user.has_perm_to_change_or_die(strategy)

    POST = request.POST
    model_id   = get_from_POST_or_404(POST, 'model_id', int)
    segment_desc_id = get_from_POST_or_404(POST, 'segment_desc_id', int)
    orga_id    = get_from_POST_or_404(POST, 'orga_id', int)
    score      = get_from_POST_or_404(POST, 'score', int)

    try:
        getattr(strategy, method_name)(model_id, segment_desc_id, orga_id, score)
    except Exception as e:
        raise Http404(str(e)) from e

    return HttpResponse()


def set_asset_score(request, strategy_id):
    return _set_score(request, strategy_id, 'set_asset_score')


def set_charm_score(request, strategy_id):
    return _set_score(request, strategy_id, 'set_charm_score')


@POST_only
@login_required
@permission_required('commercial')
@atomic
def set_segment_category(request, strategy_id):
    # strategy = get_object_or_404(Strategy, pk=strategy_id)
    strategy = get_object_or_404(Strategy.objects.select_for_update(), pk=strategy_id)

    request.user.has_perm_to_change_or_die(strategy)

    POST = request.POST
    segment_desc_id = get_from_POST_or_404(POST, 'segment_desc_id', int)
    orga_id         = get_from_POST_or_404(POST, 'orga_id', int)
    category        = get_from_POST_or_404(POST, 'category', int)

    try:
        strategy.set_segment_category(segment_desc_id, orga_id, category)
    except Exception as e:
        raise Http404(str(e)) from e

    return HttpResponse()


@login_required
@permission_required('commercial')
@jsonify
def reload_matrix_brick(request, strategy_id, orga_id):
    brick_id = get_from_GET_or_404(request.GET, 'brick_id')

    if brick_id == AssetsMatrixBrick.id_:
        brick = AssetsMatrixBrick()
    elif brick_id == CharmsMatrixBrick.id_:
        brick = CharmsMatrixBrick()
    elif brick_id == AssetsCharmsMatrixBrick.id_:
        brick = AssetsCharmsMatrixBrick()
    else:
        raise Http404('Invalid brick ID')

    strategy, orga = _get_strategy_n_orga(request, strategy_id, orga_id)

    return bricks.bricks_render_info(request, bricks=[brick],
                                     context=bricks.build_context(request, orga=orga, strategy=strategy),
                                    )
