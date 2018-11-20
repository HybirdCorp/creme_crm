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

from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import CremePropertyType
from creme.creme_core.utils import get_from_POST_or_404
# from creme.creme_core.views import generic
from creme.creme_core.views.generic import BricksView

from ..forms import creme_property_type as ptype_forms

from . import base
# from .portal import _config_portal


# @login_required
# def portal(request):
#     return _config_portal(request, 'creme_config/property_type_portal.html')
class Portal(BricksView):
    template_name = 'creme_config/property_type_portal.html'


# @login_required
# @permission_required('creme_core.can_admin')
# def add(request):
#     return generic.add_model_with_popup(
#         request, ptype_forms.CremePropertyTypeAddForm,
#         _('New custom type of property'),
#         submit_label=CremePropertyType.save_label,
#     )
class PropertyTypeCreation(base.ConfigModelCreation):
    model = CremePropertyType
    form_class = ptype_forms.CremePropertyTypeAddForm
    title = _('New custom type of property')


# @login_required
# @permission_required('creme_core.can_admin')
# def edit(request, property_type_id):
#     property_type = get_object_or_404(CremePropertyType, pk=property_type_id)
#
#     if not property_type.is_custom:
#         raise Http404("Can't edit a standard PropertyType")
#
#     if request.method == 'POST':
#         property_type_form = ptype_forms.CremePropertyTypeEditForm(property_type, user=request.user, data=request.POST)
#
#         if property_type_form.is_valid():
#             property_type_form.save()
#     else:
#         property_type_form = ptype_forms.CremePropertyTypeEditForm(property_type, user=request.user)
#
#     return generic.inner_popup(
#         request,
#         'creme_core/generics/blockform/edit_popup.html',
#         {'form':  property_type_form,
#          'title': _('Edit the type «{property}»').format(property=property_type),
#          'submit_label': _('Save the modifications'),
#         },
#         is_valid=property_type_form.is_valid(),
#         reload=False,
#         delegate_reload=True,
#     )
class PropertyTypeEdition(base.ConfigModelEdition):
    # model = CremePropertyType
    queryset = CremePropertyType.objects.filter(is_custom=True)
    form_class = ptype_forms.CremePropertyTypeEditForm
    pk_url_kwarg = 'ptype_id'
    title_format = pgettext_lazy('creme_config-property', 'Edit the type «{}»')


# TODO: use the view in creme_core instead
@login_required
@permission_required('creme_core.can_admin')
def delete(request):
    property_type = get_object_or_404(CremePropertyType, pk=get_from_POST_or_404(request.POST, 'id'))

    if not property_type.is_custom:
        raise Http404("Can't delete a standard PropertyType")

    property_type.delete()

    return HttpResponse()
