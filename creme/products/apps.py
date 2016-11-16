# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2016  Hybird
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

from creme.creme_core.apps import CremeAppConfig


class ProductsConfig(CremeAppConfig):
    name = 'creme.products'
    verbose_name = _(u'Products and services')
    # dependencies = ['creme.media_managers']
    dependencies = ['creme.documents']

#    def ready(self):
    def all_apps_ready(self):
        from . import get_product_model, get_service_model

        self.Product = get_product_model()
        self.Service = get_service_model()
#        super(ProductsConfig, self).ready()
        super(ProductsConfig, self).all_apps_ready()

    def register_creme_app(self, creme_registry):
        creme_registry.register_app('products', _(u'Products and services'), '/products')

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Product, self.Service)

    def register_blocks(self, block_registry):
        from .blocks import images_block

        block_registry.register(images_block)

    def register_bulk_update(self, bulk_update_registry):
        from .forms.product import ProductInnerEditCategory

        register = bulk_update_registry.register
        register(self.Product, innerforms={'category':     ProductInnerEditCategory,
                                           'sub_category': ProductInnerEditCategory,
                                          }
                )

        register(self.Service, innerforms={'category':     ProductInnerEditCategory,
                                           'sub_category': ProductInnerEditCategory,
                                          }
                )

    def register_icons(self, icon_registry):
        reg_icon = icon_registry.register
        reg_icon(self.Product, 'images/product_%(size)s.png')
        reg_icon(self.Service, 'images/service_%(size)s.png')

    def register_menu(self, creme_menu):
        from django.core.urlresolvers import reverse_lazy as reverse

        from creme.creme_core.auth import build_creation_perm as cperm

        reg_item = creme_menu.register_app('products', '/products/').register_item
        reg_item('/products/',                        _(u'Portal of products and services'), 'products')
        reg_item(reverse('products__list_products'),  _(u'All products'),                    'products')
        reg_item(reverse('products__create_product'), self.Product.creation_label,           cperm(self.Product))
        reg_item(reverse('products__list_services'),  _(u'All services'),                    'products')
        reg_item(reverse('products__create_service'), self.Service.creation_label,           cperm(self.Service))

