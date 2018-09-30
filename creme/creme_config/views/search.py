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

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import SearchConfigItem
from creme.creme_core.utils import get_from_POST_or_404  # get_ct_or_404
from creme.creme_core.views.generic.base import EntityCTypeRelatedMixin

from ..forms import search as search_forms

from . import base
from .portal import _config_portal


@login_required
def portal(request):
    return _config_portal(request, 'creme_config/search_portal.html')


# @login_required
# @permission_required('creme_core.can_admin')
# def add(request, ct_id):
#     ctype = get_ct_or_404(ct_id)
#
#     return generic.add_model_with_popup(
#         request, search_forms.SearchAddForm,
#         title=_('New search configuration for «{model}»').format(model=ctype),
#         initial={'content_type': ctype},
#     )
class SearchConfigCreation(EntityCTypeRelatedMixin,
                           base.BaseConfigCreation,
                          ):
    model = SearchConfigItem
    form_class = search_forms.SearchAddForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ctype'] = self.get_ctype()

        return kwargs

    def get_title(self):
        return _('New search configuration for «{model}»').format(
            model=self.get_ctype(),
        )


# @login_required
# @permission_required('creme_core.can_admin')
# def edit(request, search_config_id):
#     return generic.edit_model_with_popup(
#         request, query_dict={'pk': search_config_id},
#         model=SearchConfigItem,
#         form_class=search_forms.SearchEditForm,
#     )
class SearchConfigEdition(base.BaseConfigEdition):
    model = SearchConfigItem
    form_class = search_forms.SearchEditForm
    pk_url_kwarg = 'search_config_id'


@login_required
@permission_required('creme_core.can_admin')
def delete(request):
    sci = get_object_or_404(SearchConfigItem, id=get_from_POST_or_404(request.POST, 'id'))

    if sci.is_default:
        raise ConflictError('You cannot delete the default configuration')

    sci.delete()

    return HttpResponse()
