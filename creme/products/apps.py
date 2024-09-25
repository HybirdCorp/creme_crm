################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2024  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class ProductsConfig(CremeAppConfig):
    default = True
    name = 'creme.products'
    verbose_name = _('Products and services')
    dependencies = ['creme.documents']

    def all_apps_ready(self):
        from . import get_product_model, get_service_model

        self.Product = get_product_model()
        self.Service = get_service_model()
        super().all_apps_ready()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Product, self.Service)

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(bricks.ImagesBrick)

    def register_bulk_update(self, bulk_update_registry):
        from .forms.bulk_update import CategoryOverrider

        register = bulk_update_registry.register
        register(self.Product).add_overriders(CategoryOverrider)
        register(self.Service).add_overriders(CategoryOverrider)

    def register_creme_config(self, config_registry):
        from . import models
        from .forms import category

        register_model = config_registry.register_model
        register_model(
            models.Category,    'category',
        )
        register_model(
            models.SubCategory, 'subcategory',
        ).creation(
            form_class=category.SubCategoryForm,
        ).edition(
            form_class=category.SubCategoryForm,
        )

    def register_custom_forms(self, cform_registry):
        from . import custom_forms

        cform_registry.register(
            custom_forms.PRODUCT_CREATION_CFORM,
            custom_forms.PRODUCT_EDITION_CFORM,

            custom_forms.SERVICE_CREATION_CFORM,
            custom_forms.SERVICE_EDITION_CFORM,
        )

    def register_enumerable(self, enumerable_registry):
        from . import enumerators, models

        enumerable_registry.register_field(
            models.SubCategory, 'category',
            enumerators.QSEnumerator,
        )

        enumerable_registry.register_related_model(
            models.SubCategory,
            enumerators.SubCategoryEnumerator,
        )

    def register_cloners(self, entity_cloner_registry):
        entity_cloner_registry.register(
            model=self.Product,
        ).register(
            model=self.Service,
        )

    def register_deletors(self, entity_deletor_registry):
        entity_deletor_registry.register(
            model=self.Product,
        ).register(
            model=self.Service,
        )

    def register_fields_config(self, fields_config_registry):
        fields_config_registry.register_models(self.Product, self.Service)

    def register_icons(self, icon_registry):
        icon_registry.register(
            self.Product, 'images/product_%(size)s.png',
        ).register(
            self.Service, 'images/service_%(size)s.png',
        )

    def register_mass_import(self, import_form_registry):
        from .forms.mass_import import get_massimport_form_builder

        import_form_registry.register(
            self.Product, get_massimport_form_builder,
        ).register(
            self.Service, get_massimport_form_builder,
        )

    def register_menu_entries(self, menu_registry):
        from . import menu

        menu_registry.register(
            menu.ProductsEntry, menu.ProductCreationEntry,
            menu.ServicesEntry, menu.ServiceCreationEntry,
        )

    def register_creation_menu(self, creation_menu_registry):
        creation_menu_registry.get_or_create_group(
            'management', label=_('Management'), priority=50,
        ).add_link(
            'products-create_product', self.Product, priority=20,
        ).add_link(
            'products-create_service', self.Service, priority=25,
        )
