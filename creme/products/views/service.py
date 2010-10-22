# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import add_entity, edit_entity, view_entity_with_template, list_view

from products.models import Service
from products.forms.service import ServiceCreateForm


@login_required
@permission_required('products')
@permission_required('products.add_service')
def add(request):
    return add_entity(request, ServiceCreateForm)

def edit(request, service_id):
    return edit_entity(request, service_id, Service, ServiceCreateForm, 'products')

@login_required
@permission_required('products')
def detailview(request, service_id):
    return view_entity_with_template(request, service_id, Service, '/products/service', 'products/view_service.html')

@login_required
@permission_required('products')
def listview(request):
    return list_view(request, Service, extra_dict={'add_url': '/products/service/add'})
