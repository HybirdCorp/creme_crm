################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2026  Hybird
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

from django.apps import apps
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import pgettext_lazy

from creme.creme_config.registry import config_registry
from creme.creme_core.gui.bricks import QuerysetBrick
from creme.creme_core.views.bricks import BricksReloading
from creme.creme_core.views.generic import BricksView, CremeModelCreationPopup
from creme.products.forms.category import NarrowedSubCategoryForm
from creme.products.models import Category, SubCategory


class NarrowedSubCategoriesBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('products', 'narrowed_subcategories_config')
    dependencies = (SubCategory,)
    template_name = 'products/bricks/narrowed-subcategories.html'

    def __init__(self, category):
        super().__init__()
        self.category = category

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            SubCategory.objects.filter(category=self.category),
            model_config=config_registry.get_app_registry('products')
                                        .get_model_conf(SubCategory),
        ))


class CategoryRelatedMixin:
    category_id_url_kwarg = 'category_id'

    _category = None

    def get_category(self):
        category = self._category
        if category is None:
            self._category = category = get_object_or_404(
                Category, id=self.kwargs[self.category_id_url_kwarg],
            )

        return category


class CategoryPortal(CategoryRelatedMixin, BricksView):
    """Configuration portal to configure the subcategories related to one Category instance"""
    template_name = 'products/config/category-portal.html'
    permissions = 'products.can_admin'
    bricks = [NarrowedSubCategoriesBrick]

    def get_bricks(self):
        return {
            'main': [
                brick_cls(category=self.get_category())
                for brick_cls in self.bricks
            ],
        }

    def get_bricks_reload_url(self):
        return reverse(
            'products__reload_category_brick', args=(self.get_category().id,),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.get_category()
        context['app_verbose_name'] = apps.get_app_config('products').verbose_name

        return context


class CategoryBricksReloading(CategoryRelatedMixin, BricksReloading):
    permissions = 'products.can_admin'
    bricks = CategoryPortal.bricks

    def get_bricks(self):
        bricks = []
        category = self.get_category()
        allowed_bricks = {brick_cls.id: brick_cls for brick_cls in self.bricks}

        for brick_id in self.get_brick_ids():
            try:
                brick_cls = allowed_bricks[brick_id]
            except KeyError as e:
                raise Http404('Invalid brick ID') from e

            bricks.append(brick_cls(category=category))

        return bricks

    def get_bricks_context(self):
        context = super().get_bricks_context()
        context['category'] = self.get_category()

        return context


class NarrowedSubCategoryCreation(CategoryRelatedMixin,
                                  CremeModelCreationPopup):
    model = SubCategory
    form_class = NarrowedSubCategoryForm
    title = pgettext_lazy('products', 'New sub-category for «{category}»')
    permissions = 'products.can_admin'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['category'] = self.get_category()

        return kwargs

    def get_title_format_data(self):
        return {'category': self.get_category()}
