# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.db.models import CharField, ForeignKey, CASCADE
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from creme.creme_core.models import CremeModel


class Category(CremeModel):
    name        = CharField(_(u'Name of the category'), max_length=100)
    description = CharField(_(u'Description'), max_length=100)

    creation_label = pgettext_lazy('products-category', u'Create a category')

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'products'
        verbose_name = pgettext_lazy('products-category', u'Category')
        verbose_name_plural = pgettext_lazy('products-category', u'Categories')
        ordering = ('name',)


class SubCategory(CremeModel):
    name        = CharField(_(u'Name of the sub-category'), max_length=100)
    description = CharField(_(u'Description'), max_length=100)
    category    = ForeignKey(Category, verbose_name=_(u'Parent category'), on_delete=CASCADE).set_tags(viewable=False)

    creation_label = pgettext_lazy('products-sub_category', u'Create a sub-category')

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'products'
        verbose_name = pgettext_lazy('products-sub_category', u'Sub-category')
        verbose_name_plural = pgettext_lazy('products-sub_category', u'Sub-categories')
        ordering = ('name',)
