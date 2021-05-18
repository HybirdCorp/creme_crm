# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021  Hybird
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

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import header_filter as hfilter_forms
from creme.creme_core.models import HeaderFilter
from creme.creme_core.views import generic
from creme.creme_core.views.entity_filter import FilterMixin
from creme.creme_core.views.generic.base import EntityCTypeRelatedMixin


class Portal(generic.BricksView):
    template_name = 'creme_config/portals/header-filter.html'


class HeaderFilterCreation(EntityCTypeRelatedMixin,
                           generic.CremeModelCreationPopup):
    model = HeaderFilter
    form_class = hfilter_forms.HeaderFilterCreateForm
    title = _('Create a view for «{model}»')
    ctype_form_kwarg = 'ctype'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs[self.ctype_form_kwarg] = self.get_ctype()

        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial['is_private'] = settings.FILTERS_INITIAL_PRIVATE

        return initial

    def get_title_format_data(self):
        ctxt = super().get_title_format_data()
        ctxt['model'] = self.get_ctype()

        return ctxt


class HeaderFilterEdition(FilterMixin, generic.CremeModelEditionPopup):
    model = HeaderFilter
    form_class = hfilter_forms.HeaderFilterEditForm
    pk_url_kwarg = 'hfilter_id'
    submit_label = _('Save the view')

    def get_object(self, *args, **kwargs):
        hfilter = super().get_object(*args, **kwargs)
        self.check_filter_permissions(filter_obj=hfilter, user=self.request.user)

        return hfilter
