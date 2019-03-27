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

from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from creme.creme_core.auth import decorators
from creme.creme_core.models import CremePropertyType
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views.generic import BricksView

from ..forms import creme_property_type as ptype_forms

from . import base


class Portal(BricksView):
    template_name = 'creme_config/property_type_portal.html'


class PropertyTypeCreation(base.ConfigModelCreation):
    model = CremePropertyType
    form_class = ptype_forms.CremePropertyTypeAddForm
    title = _('New custom type of property')


class PropertyTypeEdition(base.ConfigModelEdition):
    # model = CremePropertyType
    queryset = CremePropertyType.objects.filter(is_custom=True)
    form_class = ptype_forms.CremePropertyTypeEditForm
    pk_url_kwarg = 'ptype_id'
    title = pgettext_lazy('creme_config-property', 'Edit the type «{object}»')


# TODO: use the view in creme_core instead
@decorators.login_required
@decorators.permission_required('creme_core.can_admin')
def delete(request):
    property_type = get_object_or_404(CremePropertyType, pk=get_from_POST_or_404(request.POST, 'id'))

    if not property_type.is_custom:
        raise Http404("Can't delete a standard PropertyType")

    property_type.delete()

    return HttpResponse()
