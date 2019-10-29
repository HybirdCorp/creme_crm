# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from django.conf import settings
from django.core.exceptions import PermissionDenied
# from django.http import HttpResponse, HttpResponseRedirect
# from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _  # gettext

# from .. import utils
# from ..auth.decorators import login_required
from ..forms import header_filter as hf_forms
from ..http import CremeJsonResponse
from ..models import HeaderFilter
from ..utils import get_from_GET_or_404

from . import generic, entity_filter
from .generic import base
# from .decorators import jsonify

logger = logging.getLogger(__name__)


# class HeaderFilterCreation(entity_filter.FilterCreationMixin,
#                            generic.CremeModelCreation,
#                           ):
class HeaderFilterCreation(base.EntityCTypeRelatedMixin,
                           entity_filter.FilterMixin,
                           generic.CremeModelCreation,
                          ):
    model = HeaderFilter
    form_class = hf_forms.HeaderFilterCreateForm
    template_name = 'creme_core/forms/header-filter.html'
    ctype_form_kwarg = 'ctype'

    def form_valid(self, form):
        response = super().form_valid(form)
        self.save_in_session('header_filter_id')

        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs[self.ctype_form_kwarg] = self.get_ctype()

        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial['is_private'] = settings.FILTERS_INITIAL_PRIVATE

        return initial


# class HeaderFilterEdition(entity_filter.FilterEditionMixin,
class HeaderFilterEdition(entity_filter.FilterMixin,
                          generic.CremeModelEdition,
                         ):
    model = HeaderFilter
    form_class = hf_forms.HeaderFilterEditForm
    template_name = 'creme_core/forms/header-filter.html'
    pk_url_kwarg = 'hfilter_id'
    submit_label = _('Save the modified view')

    def get_object(self, *args, **kwargs):
        hfilter = super().get_object(*args, **kwargs)
        self.check_filter_permissions(filter_obj=hfilter, user=self.request.user)

        return hfilter


# @login_required
# def delete(request):
#     hf           = get_object_or_404(HeaderFilter, pk=utils.get_from_POST_or_404(request.POST, 'id'))
#     callback_url = hf.entity_type.model_class().get_lv_absolute_url()
#     allowed, msg = hf.can_delete(request.user)
#
#     if allowed:
#         hf.delete()
#
#         return_msg = gettext('View successfully deleted')
#         status = 200
#     else:
#         return_msg = msg
#         status = 400
#
#     if request.is_ajax():
#         return HttpResponse(return_msg, status=status)
#
#     return HttpResponseRedirect(callback_url)
class HeaderFilterDeletion(generic.CremeModelDeletion):
    model = HeaderFilter

    def check_instance_permissions(self, instance, user):
        allowed, msg = instance.can_delete(user)
        if not allowed:
            raise PermissionDenied(msg)

    def get_success_url(self):
        return self.object.entity_type.model_class().get_lv_absolute_url()


# @login_required
# @jsonify
# def get_for_ctype(request):
#     ct_id = utils.get_from_GET_or_404(request.GET, 'ct_id', int)
#     ct = utils.get_ct_or_404(ct_id)
#     user = request.user
#
#     user.has_perm_to_access_or_die(ct.app_label)
#
#     return list(HeaderFilter.get_for_user(user, ct).values_list('id', 'name'))
class HeaderFilterChoices(base.ContentTypeRelatedMixin, base.CheckedView):
    response_class = CremeJsonResponse
    ctype_id_arg = 'ct_id'

    def check_related_ctype(self, ctype):
        self.request.user.has_perm_to_access_or_die(ctype.app_label)

    def get_ctype_id(self):
        return get_from_GET_or_404(self.request.GET, self.ctype_id_arg, int)

    def get_choices(self):
        return [*HeaderFilter.get_for_user(self.request.user, self.get_ctype())
                             .values_list('id', 'name')
               ]

    def get(self, request, *args, **kwargs):
        return self.response_class(
            self.get_choices(),
            safe=False,  # Result is not a dictionary
        )
