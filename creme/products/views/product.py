# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import CremeEntity
from creme.creme_core.utils import jsonify, get_from_POST_or_404
from creme.creme_core.views.generic import (add_entity, add_to_entity,
        edit_entity, view_entity, list_view)

from .. import get_product_model, get_service_model
from ..forms.base import AddImagesForm
from ..forms.product import ProductCreateForm, ProductEditForm
from ..models import Category, SubCategory # Product, Service


Product = get_product_model()
Service = get_service_model()


def abstract_add_product(request, form=ProductCreateForm,
                         submit_label=_('Save the product'),
                        ):
    return add_entity(request, form,
                      extra_template_dict={'submit_label': submit_label},
                     )


def abstract_edit_product(request, product_id, form=ProductEditForm):
    return edit_entity(request, product_id, Product, form)


def abstract_view_product(request, product_id,
                          template='products/view_product.html',
                         ):
    return view_entity(request, product_id, Product, template=template,
                       path='/products/product',
                      )


@login_required
# @permission_required(('products', 'products.add_product'))
@permission_required(('products', cperm(Product)))
def add(request):
    return abstract_add_product(request)


@login_required
@permission_required('products')
def edit(request, product_id):
    return abstract_edit_product(request, product_id)


@login_required
@permission_required('products')
def detailview(request, product_id):
    return abstract_view_product(request, product_id)


@login_required
@permission_required('products')
def listview(request):
    return list_view(request, Product,
                     # extra_dict={'add_url': '/products/product/add'}
                     extra_dict={'add_url': reverse('products__create_product')},
                    )


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
                         ugettext(u'New images for «%s»'),
                         entity_class=Product,
                         submit_label=_('Link the images'),
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
        return HttpResponse("", content_type="text/javascript")

    return redirect(entity)
