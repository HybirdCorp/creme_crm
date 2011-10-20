# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.utils.translation import ugettext_lazy as _

from creme_core.registry import creme_registry
from creme_core.gui import creme_menu, icon_registry, bulk_update_registry

from products.models import Product, Service


creme_registry.register_app('products', _(u'Products and services'), '/products')
creme_registry.register_entity_models(Product, Service)

reg_item = creme_menu.register_app('products', '/products/').register_item
reg_item('/products/',            _(u'Portal of products and services'), 'products')
reg_item('/products/products',    _(u'All products'),                    'products')
reg_item('/products/product/add', _(u'Add a product'),                   'products.add_product')
reg_item('/products/services',    _(u'All services'),                    'products')
reg_item('/products/service/add', _(u'Add a service'),                   'products.add_service')

reg_icon = icon_registry.register
reg_icon(Product, 'images/product_%(size)s.png')
reg_icon(Service, 'images/service_%(size)s.png')

bulk_update_registry.register(
    (Product, ['category', 'sub_category']),
)
