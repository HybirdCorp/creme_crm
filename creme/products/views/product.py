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

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.entities_access.functions_for_permissions import add_view_or_die, get_view_or_die
from creme_core.views.generic import add_entity, edit_entity, view_entity_with_template, list_view

from products.models import Product
from products.forms.product import ProductCreateForm


@login_required
@get_view_or_die('products')
@add_view_or_die(ContentType.objects.get_for_model(Product), None, 'products')
def add(request):
    return add_entity(request, ProductCreateForm)

def edit(request, product_id):
    return edit_entity(request, product_id, Product, ProductCreateForm, 'products')

@login_required
@get_view_or_die('products')
def detailview(request, product_id):
    return view_entity_with_template(request,
                                     product_id,
                                     Product,
                                     '/products/product',
                                     'products/view_products.html')

login_required
@get_view_or_die('products')
def listview(request):
    return list_view(request, Product, extra_dict={'add_url':'/products/product/add'})
