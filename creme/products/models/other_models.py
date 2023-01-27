################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2023  Hybird
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

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

# from creme.creme_core.models import CremeModel
from creme.creme_core.models import MinionModel


# class Category(CremeModel):
class Category(MinionModel):
    name = models.CharField(_('Name of the category'), max_length=100)
    description = models.CharField(_('Description'), max_length=100, blank=True)

    creation_label = pgettext_lazy('products-category', 'Create a category')

    class Meta:
        app_label = 'products'
        verbose_name = pgettext_lazy('products-category', 'Category')
        verbose_name_plural = pgettext_lazy('products-category', 'Categories')
        ordering = ('name',)

    def __str__(self):
        return self.name


# class SubCategory(CremeModel):
class SubCategory(MinionModel):
    name = models.CharField(_('Name of the sub-category'), max_length=100)
    description = models.CharField(_('Description'), max_length=100, blank=True)
    category = models.ForeignKey(
        Category,
        verbose_name=_('Parent category'), on_delete=models.CASCADE,
    ).set_tags(viewable=False)

    creation_label = pgettext_lazy('products-sub_category', 'Create a sub-category')

    class Meta:
        app_label = 'products'
        verbose_name = pgettext_lazy('products-sub_category', 'Sub-category')
        verbose_name_plural = pgettext_lazy('products-sub_category', 'Sub-categories')
        ordering = ('name',)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.is_custom and self.category.is_custom:
            raise ValueError(
                f'The SubCategory id="{self.id}" is not custom,'
                f'so the related Category cannot be custom.',
            )

        super().save(*args, **kwargs)
