# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from logging import debug

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.models import EntityFilter, RelationType
from creme_core.gui.listview import ListViewState
from creme_core.forms.entity_filter import EntityFilterCreateForm, EntityFilterEditForm
from creme_core.views.generic import add_entity
from creme_core.utils import get_ct_or_404, get_from_POST_or_404, jsonify, creme_entity_content_types

#TODO: factorise with HeaderFilter ??

def _set_current_efilter(request, path, filter_instance):
    lvs = ListViewState.get_state(request, path)
    if lvs:
        lvs.entity_filter_id = filter_instance.id
        lvs.register_in_session(request)

@login_required
def add(request, ct_id):
    ct = get_ct_or_404(ct_id)

    if not request.user.has_perm(ct.app_label):
        raise Http404(_(u"You are not allowed to acceed to this app"))

    try:
        callback_url = ct.model_class().get_lv_absolute_url()
    except AttributeError:
        debug('%s has no get_lv_absolute_url() method ?!' % ct.model_class())
        callback_url = '/'

    return add_entity(request, EntityFilterCreateForm, callback_url,
                      template='creme_core/entity_filters.html',
                      extra_initial={'content_type': ct},
                      function_post_save=lambda req, instance: _set_current_efilter(req, callback_url, instance)
                     )

@login_required
def edit(request, efilter_id):
    efilter = get_object_or_404(EntityFilter, pk=efilter_id)
    user = request.user
    allowed, msg = efilter.can_edit_or_delete(user)

    if not allowed:
        raise Http404(msg)

    if request.method == 'POST':
        efilter_form = EntityFilterEditForm(user=user, data=request.POST, instance=efilter)

        if efilter_form.is_valid():
            efilter_form.save()

            return HttpResponseRedirect(efilter.entity_type.model_class().get_lv_absolute_url())
    else:
        efilter_form = EntityFilterEditForm(user=user, instance=efilter)

    return render_to_response('creme_core/entity_filters.html',
                              {'form': efilter_form},
                              context_instance=RequestContext(request)
                             )

@login_required
def delete(request):
    efilter      = get_object_or_404(EntityFilter, pk=get_from_POST_or_404(request.POST, 'id'))
    callback_url = efilter.entity_type.model_class().get_lv_absolute_url()
    allowed, msg = efilter.can_edit_or_delete(request.user)
    status = 400

    if allowed:
        try:
            efilter.delete()
        except EntityFilter.DependenciesError, e:
            return_msg = unicode(e)
        else:
            return_msg = _(u'Filter sucessfully deleted')
            status = 200
    else:
        return_msg = msg

    if request.is_ajax():
        return HttpResponse(return_msg, mimetype="text/javascript", status=status)

    return HttpResponseRedirect(callback_url)

#TODO: factorise with views.relations.json_predicate_content_types  ???
@login_required
@jsonify
def get_content_types(request, rtype_id):
    content_types = get_object_or_404(RelationType, pk=rtype_id).object_ctypes.all() or creme_entity_content_types()

    choices = [(0, _(u'All'))]
    choices.extend((ct.id, unicode(ct)) for ct in content_types)

    return choices

@login_required
@jsonify
def get_for_ctype(request, ct_id):
    ct = get_ct_or_404(ct_id)

    if not request.user.has_perm(ct.app_label): #TODO: helper in auth.py ??
        raise PermissionDenied(_(u"You are not allowed to acceed to this app"))

    return list(EntityFilter.objects.filter(entity_type=ct).values_list('id', 'name'))
