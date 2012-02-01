# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views import generic
from creme_core.utils import get_from_POST_or_404, jsonify

from persons.models import Organisation

from commercial.models import Strategy, MarketSegmentDescription, CommercialAsset, MarketSegmentCharm
from commercial.forms import strategy as forms
from commercial.blocks import assets_matrix_block, charms_matrix_block, assets_charms_matrix_block


@login_required
@permission_required('commercial')
@permission_required('commercial.add_strategy')
def add(request):
    return generic.add_entity(request, forms.StrategyForm)

@login_required
@permission_required('commercial')
def edit(request, strategy_id):
    return generic.edit_entity(request, strategy_id, Strategy, forms.StrategyForm)

@login_required
@permission_required('commercial')
def detailview(request, strategy_id):
    return generic.view_entity(request, strategy_id, Strategy, '/commercial/strategy',
                               template='commercial/view_strategy.html'
                              )

@login_required
@permission_required('commercial')
def listview(request):
    return generic.list_view(request, Strategy, extra_dict={'add_url': '/commercial/strategy/add'})

@login_required
@permission_required('commercial')
def add_segment(request, strategy_id):
    return generic.add_to_entity(request, strategy_id, forms.SegmentCreateForm,
                                 _(u"New market segment for <%s>"),
                                 entity_class=Strategy
                                )

@login_required
@permission_required('commercial')
def link_segment(request, strategy_id):
    return generic.add_to_entity(request, strategy_id, forms.SegmentLinkForm,
                                 _(u"New market segment for <%s>"),
                                 entity_class=Strategy
                                )

@login_required
@permission_required('commercial')
def add_asset(request, strategy_id):
    return generic.add_to_entity(request, strategy_id, forms.AssetForm,
                                 _(u"New commercial asset for <%s>"),
                                 entity_class=Strategy
                                )

@login_required
@permission_required('commercial')
def add_charm(request, strategy_id):
    return generic.add_to_entity(request, strategy_id, forms.CharmForm,
                                 _(u"New segment charm for <%s>"),
                                 entity_class=Strategy
                                )

@login_required
@permission_required('commercial')
def add_evalorga(request, strategy_id):
    return generic.add_to_entity(request, strategy_id, forms.AddOrganisationForm,
                                 _(u"New organisation for <%s>"),
                                 entity_class=Strategy
                                )

@login_required
@permission_required('commercial')
def edit_segment(request, strategy_id, seginfo_id):
    return generic.edit_related_to_entity(request, seginfo_id, MarketSegmentDescription,
                                          forms.SegmentEditForm, _(u"Segment for <%s>")
                                         )

@login_required
@permission_required('commercial')
def edit_asset(request, asset_id):
    return generic.edit_related_to_entity(request, asset_id, CommercialAsset,
                                          forms.AssetForm, _(u"Asset for <%s>")
                                         )

@login_required
@permission_required('commercial')
def edit_charm(request, charm_id):
    return generic.edit_related_to_entity(request, charm_id, MarketSegmentCharm,
                                          forms.CharmForm, _(u"Charm for <%s>")
                                         )

@login_required
@permission_required('commercial')
def delete_evalorga(request, strategy_id):
    strategy = get_object_or_404(Strategy, pk=strategy_id)
    strategy.can_change_or_die(request.user)

    strategy.evaluated_orgas.remove(get_from_POST_or_404(request.POST, 'id'))

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(strategy.get_absolute_url())

def _get_strategy_n_orga(request, strategy_id, orga_id):
    user = request.user

    strategy = get_object_or_404(Strategy, pk=strategy_id)
    strategy.can_view_or_die(user)

    orga = get_object_or_404(Organisation, pk=orga_id)
    orga.can_view_or_die(user)

    return strategy, orga

@login_required
@permission_required('commercial')
def _orga_view(request, strategy_id, orga_id, template):
    strategy, orga = _get_strategy_n_orga(request, strategy_id, orga_id)

    if not strategy.evaluated_orgas.filter(pk=orga_id).exists():
        raise Http404(_(u'This organisation <%(orga)s> is not (no more ?) evaluated by the strategy %(strategy)s') % {
                            'orga': orga, 'strategy': strategy}
                     )

    return render(request, template, {'orga': orga, 'strategy': strategy})

def orga_evaluation(request, strategy_id, orga_id):
    return _orga_view(request, strategy_id, orga_id, 'commercial/orga_evaluation.html')

def orga_synthesis(request, strategy_id, orga_id):
    return _orga_view(request, strategy_id, orga_id, 'commercial/orga_synthesis.html')

@login_required
@permission_required('commercial')
def _set_score(request, strategy_id, method_name):
    strategy = get_object_or_404(Strategy, pk=strategy_id)
    strategy.can_change_or_die(request.user)

    POST = request.POST
    model_id   = get_from_POST_or_404(POST, 'model_id', int)
    segment_desc_id = get_from_POST_or_404(POST, 'segment_desc_id', int)
    orga_id    = get_from_POST_or_404(POST, 'orga_id', int)
    score      = get_from_POST_or_404(POST, 'score', int)

    try:
        getattr(strategy, method_name)(model_id, segment_desc_id, orga_id, score)
    except Exception, e:
        raise Http404(str(e))

    return HttpResponse('', mimetype='text/javascript')

def set_asset_score(request, strategy_id):
    return _set_score(request, strategy_id, 'set_asset_score')

def set_charm_score(request, strategy_id):
    return _set_score(request, strategy_id, 'set_charm_score')

@login_required
@permission_required('commercial')
def set_segment_category(request, strategy_id):
    strategy = get_object_or_404(Strategy, pk=strategy_id)
    strategy.can_change_or_die(request.user)

    POST = request.POST
    segment_desc_id = get_from_POST_or_404(POST, 'segment_desc_id', int)
    orga_id         = get_from_POST_or_404(POST, 'orga_id', int)
    category        = get_from_POST_or_404(POST, 'category', int)

    try:
        strategy.set_segment_category(segment_desc_id, orga_id, category)
    except Exception, e:
        raise Http404(str(e))

    return HttpResponse('', mimetype='text/javascript')

@login_required
@permission_required('commercial')
@jsonify
def _reload_matrix(request, strategy_id, orga_id, block):
    strategy, orga = _get_strategy_n_orga(request, strategy_id, orga_id)

    context = RequestContext(request)
    context['orga']     = orga
    context['strategy'] = strategy

    return [(block.id_, block.detailview_display(context))]

def reload_assets_matrix(request, strategy_id, orga_id):
    return _reload_matrix(request, strategy_id, orga_id, assets_matrix_block)

def reload_charms_matrix(request, strategy_id, orga_id):
    return _reload_matrix(request, strategy_id, orga_id, charms_matrix_block)

def reload_assets_charms_matrix(request, strategy_id, orga_id):
    return _reload_matrix(request, strategy_id, orga_id, assets_charms_matrix_block)
