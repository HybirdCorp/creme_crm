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

# import warnings

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext_lazy as _, ugettext

from .. import utils
from ..auth.decorators import login_required
from ..core.exceptions import ConflictError
from ..forms.header_filter import HeaderFilterForm
from ..gui.listview import ListViewState
from ..models import HeaderFilter, CremeEntity
from .generic import add_entity
from .utils import build_cancel_path


def _set_current_hf(request, path, hf_instance):
    lvs = ListViewState.get_state(request, path)
    if lvs:
        lvs.header_filter_id = hf_instance.id
        lvs.register_in_session(request)


@login_required
def add(request, content_type_id, extra_template_dict=None):
    ct_entity = utils.get_ct_or_404(content_type_id)

    if not request.user.has_perm(ct_entity.app_label):
        raise PermissionDenied(ugettext(u"You are not allowed to access to this app"))

    model = ct_entity.model_class()

    if not issubclass(model, CremeEntity):
        raise ConflictError(u'This model is not a entity model: %s' % model)

    callback_url = request.POST.get('cancel_url')

    if not callback_url:
        try:
            callback_url = model.get_lv_absolute_url()
        except AttributeError:
            callback_url = '/'

    ctx = {}
    if extra_template_dict:
        ctx.update(extra_template_dict)

    return add_entity(request, HeaderFilterForm, callback_url,
                      template='creme_core/header_filter_form.html',
                      extra_initial={'content_type': ct_entity},
                      extra_template_dict=ctx,
                      function_post_save=lambda r, i: _set_current_hf(r, callback_url, i),
                     )


@login_required
def edit(request, header_filter_id):
    hf = get_object_or_404(HeaderFilter, pk=header_filter_id)
    user = request.user
    allowed, msg = hf.can_edit(user)

    if not allowed:
        raise PermissionDenied(msg)

    if request.method == 'POST':
        POST = request.POST
        cancel_url = POST.get('cancel_url')
        hf_form = HeaderFilterForm(user=user, data=POST, instance=hf)

        if hf_form.is_valid():
            hf_form.save()

            return HttpResponseRedirect(cancel_url or
                                        hf.entity_type.model_class().get_lv_absolute_url()
                                       )
    else:
        hf_form = HeaderFilterForm(user=user, instance=hf)
        cancel_url = build_cancel_path(request)

    return render(request, 'creme_core/header_filter_form.html',
                  {'form': hf_form,
                   'cancel_url': cancel_url,
                   'submit_label': _('Save the modified view'),
                  }
                 )


@login_required
def delete(request):
    hf           = get_object_or_404(HeaderFilter, pk=utils.get_from_POST_or_404(request.POST, 'id'))
    callback_url = hf.entity_type.model_class().get_lv_absolute_url()
    allowed, msg = hf.can_delete(request.user)

    if allowed:
        hf.delete()

        return_msg = ugettext(u'View successfully deleted')
        status = 200
    else:
        return_msg = msg
        status = 400

    if request.is_ajax():
        return HttpResponse(return_msg, content_type="text/javascript", status=status)

    return HttpResponseRedirect(callback_url)


@login_required
@utils.jsonify
# def get_for_ctype(request, ct_id=None):
def get_for_ctype(request):
    # if ct_id is None:
    #     ct_id = utils.get_from_GET_or_404(request.GET, 'ct_id', int)
    # else:
    #     warnings.warn('header_filter.get_for_ctype(): the URL argument "ct_id" is deprecated ; '
    #                   'use the GET parameter instead.',
    #                   DeprecationWarning
    #                  )
    ct_id = utils.get_from_GET_or_404(request.GET, 'ct_id', int)
    ct = utils.get_ct_or_404(ct_id)
    user = request.user

    if not user.has_perm(ct.app_label):  # TODO: helper in auth.py ??
        raise PermissionDenied(ugettext(u'You are not allowed to access to this app'))

    return list(HeaderFilter.get_for_user(user, ct).values_list('id', 'name'))
