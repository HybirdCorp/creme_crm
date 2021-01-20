# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.shortcuts import get_object_or_404

from creme import products
from creme.creme_core.auth.decorators import login_required
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic
from creme.creme_core.views.decorators import jsonify

from .. import custom_forms
from ..constants import DEFAULT_HFILTER_PRODUCT
from ..models import Category, SubCategory
from .base import ImagesAddingBase

Product = products.get_product_model()
Service = products.get_service_model()


@jsonify
@login_required
def get_subcategories(request, category_id):
    get_object_or_404(Category, pk=category_id)
    return [
        *SubCategory.objects
                    .filter(category=category_id)
                    .order_by('id')
                    .values_list('id', 'name'),
    ]


class ImageRemoving(generic.base.EntityRelatedMixin, generic.CremeDeletion):
    permissions = 'products'
    entity_classes = [Product, Service]

    image_id_arg = 'id'

    def perform_deletion(self, request):
        img_id = get_from_POST_or_404(request.POST, self.image_id_arg, cast=int)
        self.get_related_entity().images.remove(img_id)


class ProductCreation(generic.EntityCreation):
    model = Product
    form_class = custom_forms.PRODUCT_CREATION_CFORM


class ProductDetail(generic.EntityDetail):
    model = Product
    template_name = 'products/view_product.html'
    pk_url_kwarg = 'product_id'


class ProductEdition(generic.EntityEdition):
    model = Product
    form_class = custom_forms.PRODUCT_EDITION_CFORM
    pk_url_kwarg = 'product_id'


class ProductsList(generic.EntitiesList):
    model = Product
    default_headerfilter_id = DEFAULT_HFILTER_PRODUCT


class ImagesAdding(ImagesAddingBase):
    entity_id_url_kwarg = 'product_id'
    entity_classes = Product
