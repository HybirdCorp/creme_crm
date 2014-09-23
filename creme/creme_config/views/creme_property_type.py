# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import CremePropertyType
from creme.creme_core.views.generic import add_model_with_popup, inner_popup
from creme.creme_core.utils import get_from_POST_or_404

from ..forms.creme_property_type import CremePropertyTypeEditForm, CremePropertyTypeAddForm


@login_required
@permission_required('creme_core.can_admin')
def add(request):
    return add_model_with_popup(request, CremePropertyTypeAddForm, _(u'New custom type of property'))

@login_required
@permission_required('creme_core.can_admin')
def edit(request, property_type_id):
    property_type = get_object_or_404(CremePropertyType, pk=property_type_id)

    if not property_type.is_custom:
        raise Http404("Can't edit a standard PropertyType")

    if request.method == 'POST':
        property_type_form = CremePropertyTypeEditForm(property_type, user=request.user, data=request.POST)

        if property_type_form.is_valid():
            property_type_form.save()
    else:
        property_type_form = CremePropertyTypeEditForm(property_type, user=request.user)

    return inner_popup(request,
                       'creme_core/generics/blockform/edit_popup.html',
                       {'form':  property_type_form,
                        'title': _(u'Edit the type "%s"') % property_type,
                       },
                       is_valid=property_type_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

@login_required
#@permission_required('creme_config')
def portal(request):
    return render(request, 'creme_config/property_type_portal.html')

@login_required
@permission_required('creme_core.can_admin')
def delete(request):
    property_type = get_object_or_404(CremePropertyType, pk=get_from_POST_or_404(request.POST, 'id'))

    if not property_type.is_custom:
        raise Http404("Can't delete a standard PropertyType")

    property_type.delete()

    return HttpResponse()
