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

from django.utils.translation import ugettext_lazy as _

from creme_core.registry import creme_registry
from creme_core.gui.menu import creme_menu

from products.models import Product, Service


creme_registry.register_app('products', _(u'Products et services'), '/products')
creme_registry.register_entity_models(Product, Service)

creme_menu.register_app('products', '/products/', 'Produits et Services')
reg_menu = creme_menu.register_menu
reg_menu('products', '/products/',            _(u'Portal'))
reg_menu('products', '/products/products',    _(u'All products'))
reg_menu('products', '/products/product/add', _(u'Add a product'))
reg_menu('products', '/products/services',    _(u'All services'))
reg_menu('products', '/products/service/add', _(u'Add a service'))
