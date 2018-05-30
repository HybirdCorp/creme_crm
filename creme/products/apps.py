# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2018  Hybird
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
    dependencies = ['creme.documents']

    def all_apps_ready(self):
        from . import get_product_model, get_service_model

        self.Product = get_product_model()
        self.Service = get_service_model()
        super(ProductsConfig, self).all_apps_ready()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Product, self.Service)

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(bricks.ImagesBrick)

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

    def register_mass_import(self, import_form_registry):
        from .forms.mass_import import get_massimport_form_builder

        register = import_form_registry.register
        register(self.Product, get_massimport_form_builder)
        register(self.Service, get_massimport_form_builder)

    def register_menu(self, creme_menu):
        # from django.conf import settings

        Product = self.Product
        Service = self.Service

        # if settings.OLD_MENU:
        #     from django.urls import reverse_lazy as reverse
        #     from creme.creme_core.auth import build_creation_perm as cperm
        #
        #     reg_item = creme_menu.register_app('products', '/products/').register_item
        #     reg_item(reverse('products__portal'),         _(u'Portal of products and services'), 'products')
        #     reg_item(reverse('products__list_products'),  _(u'All products'),                    'products')
        #     reg_item(reverse('products__create_product'), Product.creation_label,                cperm(Product))
        #     reg_item(reverse('products__list_services'),  _(u'All services'),                    'products')
        #     reg_item(reverse('products__create_service'), Service.creation_label,                cperm(Service))
        # else:
        LvURLItem = creme_menu.URLItem.list_view
        creme_menu.get('features') \
                  .get_or_create(creme_menu.ContainerItem, 'management', priority=50,
                                 defaults={'label': _(u'Management')},
                                ) \
                  .add(LvURLItem('products-products', model=Product), priority=20) \
                  .add(LvURLItem('products-services', model=Service), priority=25)
        creme_menu.get('creation', 'any_forms') \
                  .get_or_create_group('management', label=_(u'Management'), priority=50) \
                  .add_link('products-create_product', Product, priority=20) \
                  .add_link('products-create_service', Service, priority=25)
