# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from django.utils.translation import ugettext as _

from creme.creme_core.forms.bulk import BulkForm

from ..models import Product
from .base import _BaseCreateForm, _BaseEditForm
from creme.products.forms.fields import CategoryField


class ProductCreateForm(_BaseCreateForm):
    class Meta(_BaseCreateForm.Meta):
        model = Product


class ProductEditForm(_BaseEditForm):
    class Meta(_BaseEditForm.Meta):
        model = Product


class ProductInnerEditCategory(BulkForm):
    def __init__(self, model, field_name, user, entities, is_bulk, **kwargs):
        super(ProductInnerEditCategory, self).__init__(model, field_name, user, entities, is_bulk, **kwargs)

        sub_category = CategoryField(label=_(u'Sub-category'))

        if not is_bulk:
            sub_category.initial = entities[0].sub_category

        self.fields['sub_category'] = sub_category

    def save(self, *args, **kwargs):
        entities = self.entities
        sub_category = self.cleaned_data['sub_category']

        for entity in entities:
            entity.category = sub_category.category
            entity.sub_category = sub_category
            entity.save()
