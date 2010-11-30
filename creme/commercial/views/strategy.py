# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import (list_view, add_entity, add_to_entity,
                                      edit_entity, view_entity_with_template,
                                      inner_popup)
from creme_core.utils import get_from_POST_or_404, jsonify

from persons.models import Organisation

from commercial.models import Strategy, MarketSegment, CommercialAsset, MarketSegmentCharm
from commercial.forms.strategy import StrategyForm, SegmentForm, AssetForm, CharmForm, AddOrganisationForm
from commercial.blocks import assets_matrix_block


@login_required
@permission_required('commercial')
@permission_required('commercial.add_strategy')
def add(request):
    return add_entity(request, StrategyForm)

def edit(request, strategy_id):
    return edit_entity(request, strategy_id, Strategy, StrategyForm, 'commercial')

@login_required
@permission_required('commercial')
def detailview(request, strategy_id):
    return view_entity_with_template(request, strategy_id, Strategy, '/commercial/strategy',
                                     template='commercial/view_strategy.html'
                                    )

@login_required
@permission_required('commercial')
#@change_page_for_last_item_viewed
def listview(request):
    return list_view(request, Strategy, extra_dict={'add_url': '/commercial/strategy/add'})

def add_segment(request, strategy_id):
    return add_to_entity(request, strategy_id, SegmentForm, _(u"New market segment for <%s>"),
                         entity_class=Strategy)

def add_asset(request, strategy_id):
    return add_to_entity(request, strategy_id, AssetForm, _(u"New commercial asset for <%s>"),
                         entity_class=Strategy)

def add_charm(request, strategy_id):
    return add_to_entity(request, strategy_id, CharmForm, _(u"New segment charm for <%s>"),
                         entity_class=Strategy)

def add_evalorga(request, strategy_id):
    return add_to_entity(request, strategy_id, AddOrganisationForm, _(u"New organisation for <%s>"),
                         entity_class=Strategy)

@login_required
@permission_required('commercial')
def _edit(request, model_id, model_class, form_class, title):
    model = get_object_or_404(model_class, pk=model_id)
    strategy = model.strategy

    strategy.can_change_or_die(request.user)

    if request.POST:
        edit_form = form_class(strategy, request.POST, instance=model)

        if edit_form.is_valid():
            edit_form.save()
    else: # return page on GET request
        edit_form = form_class(entity=strategy, instance=model)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {
                        'form':  edit_form,
                        'title': title % strategy,
                       },
                       is_valid=edit_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

def edit_segment(request, segment_id):
    return _edit(request, segment_id, MarketSegment, SegmentForm, _(u"Segment for <%s>"))

def edit_asset(request, asset_id):
    return _edit(request, asset_id, CommercialAsset, AssetForm, _(u"Asset for <%s>"))

def edit_charm(request, charm_id):
    return _edit(request, charm_id, MarketSegmentCharm, CharmForm, _(u"Charm for <%s>"))

@login_required
@permission_required('commercial')
def _delete(request, model_class):
    model = get_object_or_404(model_class, pk=get_from_POST_or_404(request.POST, 'id'))

    model.strategy.can_change_or_die(request.user)
    model.delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(model.strategy.get_absolute_url())

def delete_segment(request):
    return _delete(request, MarketSegment)

def delete_asset(request):
    return _delete(request, CommercialAsset)

def delete_charm(request):
    return _delete(request, MarketSegmentCharm)

@login_required
@permission_required('commercial')
def delete_evalorga(request, strategy_id):
    strategy = get_object_or_404(Strategy, pk=strategy_id)
    strategy.can_change_or_die(request.user)

    strategy.evaluated_orgas.remove(get_from_POST_or_404(request.POST, 'id'))

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(strategy.get_absolute_url())

@login_required
@permission_required('commercial')
def orga_evaluation(request, strategy_id, orga_id):
    user = request.user

    strategy = get_object_or_404(Strategy, pk=strategy_id)
    strategy.can_view_or_die(user)

    orga = get_object_or_404(Organisation, pk=orga_id)
    #orga.can_view_or_die(user) #TODO: improve template ?? (deactivate <a> tag)

    if not strategy.evaluated_orgas.filter(pk=orga_id).exists():
        raise Http404(_(u'This organisation <%(orga)s> is not (no more ?) evaluated by the strategy %(strategy)s') % {
                            'orga': orga, 'strategy': strategy}
                     )

    return render_to_response('commercial/orga_evaluation.html',
                              {'orga': orga, 'strategy': strategy}, #TODO: factorise with Http404 ??
                              context_instance=RequestContext(request))

@login_required
@permission_required('commercial')
def set_asset_score(request, strategy_id):
    strategy = get_object_or_404(Strategy, pk=strategy_id)
    strategy.can_change_or_die(request.user)

    POST = request.POST

    try:
        asset_id   = int(POST['asset_id'])
        segment_id = int(POST['segment_id'])
        orga_id    = int(POST['orga_id'])
        score      = int(POST['score'])
    except Exception, e:
        raise Http404('Problem with a posted arg: %s' % str(e))

    if not 1 <= score <= 4:
        raise Http404('Problem with a "score" arg: not 1 <= %s <= 4' % score)

    try:
        strategy.set_asset_score(asset_id, segment_id, orga_id, score)
    except Exception, e:
        raise Http404(str(e))

    return HttpResponse('', mimetype='text/javascript')

@login_required
@permission_required('commercial')
@jsonify
def reload_assets_matrix(request, strategy_id, orga_id):
    strategy = get_object_or_404(Strategy, pk=strategy_id)
    strategy.can_view_or_die(request.user)

    context = RequestContext(request)
    context['orga']     = get_object_or_404(Organisation, pk=orga_id)
    context['strategy'] = strategy

    return [(assets_matrix_block.id_, assets_matrix_block.detailview_display(context))]
