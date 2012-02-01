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

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required

from creme_core.models.header_filter import HeaderFilter, HeaderFilterList
from creme_core.forms.header_filter import HeaderFilterForm
from creme_core.views.generic import add_entity
from creme_core.gui.listview import ListViewState
from creme_core.utils import get_ct_or_404, get_from_POST_or_404, jsonify


def _set_current_hf(request, path, hf_instance):
    lvs = ListViewState.get_state(request, path)
    if lvs:
        lvs.header_filter_id = hf_instance.id
        lvs.register_in_session(request)

@login_required
def add(request, content_type_id, extra_template_dict=None): #TODO: extra_template_dict used ???
    ct_entity = get_ct_or_404(content_type_id)

    if not request.user.has_perm(ct_entity.app_label):
        raise Http404(_(u"You are not allowed to acceed to this app"))

    try:
        callback_url = ct_entity.model_class().get_lv_absolute_url()
    except AttributeError:
        callback_url = '/'

    return add_entity(request, HeaderFilterForm, callback_url,
                      template='creme_core/header_filters.html',
                      extra_initial={'content_type': ct_entity},
                      extra_template_dict=extra_template_dict or {},
                      function_post_save=lambda r, i: _set_current_hf(r, callback_url, i)
                     )

@login_required
def edit(request, header_filter_id):
    hf = get_object_or_404(HeaderFilter, pk=header_filter_id)
    user = request.user
    allowed, msg = hf.can_edit_or_delete(user)

    if not allowed:
        raise Http404(msg)

    if request.method == 'POST':
        hf_form = HeaderFilterForm(user=user, data=request.POST, instance=hf)

        if hf_form.is_valid():
            hf_form.save()

            return HttpResponseRedirect(hf.entity_type.model_class().get_lv_absolute_url())
    else:
        hf_form = HeaderFilterForm(user=user, instance=hf)

    return render(request, 'creme_core/header_filters.html', {'form': hf_form})

@login_required
def delete(request):
    hf           = get_object_or_404(HeaderFilter, pk=get_from_POST_or_404(request.POST, 'id'))
    callback_url = hf.entity_type.model_class().get_lv_absolute_url()
    allowed, msg = hf.can_edit_or_delete(request.user)

    if allowed:
        hf.delete()

        return_msg = _(u'View sucessfully deleted')
        status = 200
    else:
        return_msg = msg
        status = 400

    if request.is_ajax():
        return HttpResponse(return_msg, mimetype="text/javascript", status=status)

    return HttpResponseRedirect(callback_url)

@login_required
@jsonify
def get_for_ctype(request, ct_id):
    ct = get_ct_or_404(ct_id)

    if not request.user.has_perm(ct.app_label): #TODO: helper in auth.py ??
        raise PermissionDenied(_(u"You are not allowed to acceed to this app"))

    return list(HeaderFilter.objects.filter(entity_type=ct).order_by('id').values_list('id', 'name'))
