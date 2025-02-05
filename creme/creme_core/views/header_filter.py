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

import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from ..forms import header_filter as hf_forms
from ..http import CremeJsonResponse
from ..models import HeaderFilter
from ..utils import get_from_GET_or_404
from . import entity_filter, generic
from .generic import base

logger = logging.getLogger(__name__)


class HeaderFilterCreation(base.EntityCTypeRelatedMixin,
                           entity_filter.FilterMixin,
                           generic.CremeModelCreation):
    model = HeaderFilter
    form_class = hf_forms.HeaderFilterCreationForm
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


class HeaderFilterCloning(entity_filter.FilterMixin,
                          generic.CremeModelCreation):
    model = HeaderFilter
    form_class = hf_forms.HeaderFilterCloningForm
    template_name = 'creme_core/forms/header-filter.html'
    pk_url_kwarg = 'hfilter_id'
    source_form_kwarg = 'source'

    def get_source(self):
        hfilter = get_object_or_404(HeaderFilter, pk=self.kwargs[self.pk_url_kwarg])
        self.request.user.has_perm_to_access_or_die(hfilter.entity_type.app_label)

        return hfilter

    def form_valid(self, form):
        response = super().form_valid(form)
        self.save_in_session('header_filter_id')

        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs[self.source_form_kwarg] = self.get_source()

        return kwargs

    # TODO?
    # def get_initial(self):
    #     initial = super().get_initial()
    #     initial['is_private'] = settings.FILTERS_INITIAL_PRIVATE
    #
    #     return initial


class HeaderFilterEdition(entity_filter.FilterMixin,
                          generic.CremeModelEdition):
    model = HeaderFilter
    form_class = hf_forms.HeaderFilterEditionForm
    template_name = 'creme_core/forms/header-filter.html'
    pk_url_kwarg = 'hfilter_id'
    submit_label = _('Save the modified view')

    def get_object(self, *args, **kwargs):
        hfilter = super().get_object(*args, **kwargs)
        self.check_filter_permissions(filter_obj=hfilter, user=self.request.user)

        return hfilter


class HeaderFilterDeletion(generic.CremeModelDeletion):
    model = HeaderFilter

    def check_instance_permissions(self, instance, user):
        allowed, msg = instance.can_delete(user)
        if not allowed:
            raise PermissionDenied(msg)

    def get_success_url(self):
        # TODO: callback_url?
        return self.object.entity_type.model_class().get_lv_absolute_url()


class HeaderFilterChoices(base.ContentTypeRelatedMixin, base.CheckedView):
    response_class = CremeJsonResponse
    ctype_id_arg = 'ct_id'

    def check_related_ctype(self, ctype):
        self.request.user.has_perm_to_access_or_die(ctype.app_label)

    def get_ctype_id(self):
        return get_from_GET_or_404(self.request.GET, self.ctype_id_arg, int)

    def get_choices(self):
        return [
            *HeaderFilter.objects.filter_by_user(self.request.user)
                                 .filter(entity_type=self.get_ctype())
                                 .values_list('id', 'name'),
        ]

    def get(self, request, *args, **kwargs):
        return self.response_class(
            self.get_choices(),
            safe=False,  # Result is not a dictionary
        )
