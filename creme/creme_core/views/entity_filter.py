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

import logging

from django.core.exceptions import PermissionDenied
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _, ugettext

from .. import utils
from ..auth.decorators import login_required
from ..forms import entity_filter as efilter_forms
from ..gui.listview import ListViewState
from ..models import EntityFilter, RelationType
from . import generic
from .decorators import jsonify
from .generic.base import EntityCTypeRelatedMixin

logger = logging.getLogger(__name__)


class FilterMixin:
    """Code factorisation with HeaderFilter views."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lv_url = None

    def build_lv_url(self):
        url = self.lv_url

        if url is None:
            url = self.request.POST.get('cancel_url')

            if not url:
                model = self.object.entity_type.model_class()

                try:
                    url = model.get_lv_absolute_url()
                except AttributeError:
                    logger.debug('"%s" has no get_lv_absolute_url() method ?!', model)
                    url = ''

            self.lv_url = url

        return url

    def get_success_url(self):
        return self.build_lv_url() or reverse('creme_core__home')


class FilterCreationMixin(EntityCTypeRelatedMixin, FilterMixin):
    ctype_form_kwarg = 'ctype'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs[self.ctype_form_kwarg] = self.get_ctype()

        return kwargs

    def save_in_session(self, lvs_attr):
        request = self.request
        lv_url = self.build_lv_url()
        lvs = ListViewState.get_state(request, lv_url) or \
              ListViewState(url=lv_url)

        setattr(lvs, lvs_attr, self.object.id)
        lvs.register_in_session(request)


class FilterEditionMixin(FilterMixin):
    def get_object(self, *args, **kwargs):
        filter_ = super().get_object(*args, **kwargs)

        allowed, msg = filter_.can_edit(self.request.user)
        if not allowed:
            raise PermissionDenied(msg)

        return filter_


class EntityFilterCreation(FilterCreationMixin, generic.CremeModelCreation):
    model = EntityFilter
    form_class = efilter_forms.EntityFilterCreateForm
    template_name = 'creme_core/forms/entity-filter.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        self.save_in_session('entity_filter_id')

        return response


class EntityFilterEdition(FilterEditionMixin, generic.CremeModelEdition):
    model = EntityFilter
    form_class = efilter_forms.EntityFilterEditForm
    template_name = 'creme_core/forms/entity-filter.html'
    pk_url_kwarg = 'efilter_id'
    submit_label = _('Save the modified filter')


@login_required
def delete(request):
    efilter      = get_object_or_404(EntityFilter, pk=utils.get_from_POST_or_404(request.POST, 'id'))
    callback_url = efilter.entity_type.model_class().get_lv_absolute_url()
    allowed, msg = efilter.can_delete(request.user)
    status = 400  # TODO: 409 ??

    if allowed:
        try:
            efilter.delete()
        except EntityFilter.DependenciesError as e:
            return_msg = str(e)
        except ProtectedError as e:
            return_msg = ugettext('«{}» can not be deleted because of its dependencies.').format(efilter)
            return_msg += render_to_string('creme_core/templatetags/widgets/list_instances.html',
                                           {'objects': e.args[1][:25], 'user': request.user},
                                           request=request,
                                          )
        else:
            return_msg = ugettext('Filter successfully deleted')
            status = 200
    else:
        return_msg = msg

    if request.is_ajax():
        return HttpResponse(return_msg, status=status)

    return HttpResponseRedirect(callback_url)


# TODO: factorise with views.relations.json_rtype_ctypes  ???
@login_required
@jsonify
def get_content_types(request, rtype_id):
    content_types = get_object_or_404(RelationType, pk=rtype_id).object_ctypes.all() or \
                    utils.creme_entity_content_types()

    choices = [(0, ugettext('All'))]
    choices.extend((ct.id, str(ct)) for ct in content_types)

    return choices


@login_required
@jsonify
def get_for_ctype(request):
    GET = request.GET
    ct_id = utils.get_from_GET_or_404(GET, 'ct_id', int)
    include_all = utils.get_from_GET_or_404(GET, 'all', cast=utils.bool_from_str_extended, default='0')
    ct = utils.get_ct_or_404(ct_id)
    user = request.user

    user.has_perm_to_access_or_die(ct.app_label)

    choices = [('', ugettext('All'))] if include_all else []
    choices.extend(EntityFilter.get_for_user(user, ct).values_list('id', 'name'))

    return choices
