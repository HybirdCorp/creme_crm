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
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import CremeEntity
from creme.creme_core.utils import jsonify, get_from_POST_or_404
from creme.creme_core.views.generic import (add_entity, add_to_entity,
        edit_entity, view_entity, list_view)

from ..models import Product, Service, Category, SubCategory
from ..forms.base import AddImagesForm
from ..forms.product import ProductCreateForm, ProductEditForm


@login_required
@permission_required('products')
@permission_required('products.add_product')
def add(request):
    return add_entity(request, ProductCreateForm,
                      extra_template_dict={'submit_label': _('Save the product')},
                     )

@login_required
@permission_required('products')
def edit(request, product_id):
    return edit_entity(request, product_id, Product, ProductEditForm)

@login_required
@permission_required('products')
def detailview(request, product_id):
    return view_entity(request, product_id, Product, '/products/product',
                       'products/view_product.html',
                      )

@login_required
@permission_required('products')
def listview(request):
    return list_view(request, Product, extra_dict={'add_url': '/products/product/add'})

@jsonify
@login_required
def get_subcategories(request, category_id):
    get_object_or_404(Category, pk=category_id)
    return list(SubCategory.objects.filter(category=category_id)
                                   .order_by('id')
                                   .values_list('id', 'name')
               )

@login_required
@permission_required('products')
def add_images(request, product_id):
    return add_to_entity(request, product_id, AddImagesForm,
                         ugettext('New images for <%s>'),
                         entity_class=Product,
                        )

@login_required
@permission_required('products')
def remove_image(request, entity_id):
    img_id = get_from_POST_or_404(request.POST, 'id')
    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()

    if not isinstance(entity, (Product, Service)):
        raise Http404('Entity should be a Product/Service')

    request.user.has_perm_to_change_or_die(entity)

    entity.images.remove(img_id)

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return redirect(entity)
