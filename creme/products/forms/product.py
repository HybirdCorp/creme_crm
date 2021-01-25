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

# import warnings
from django.utils.translation import gettext as _

from creme.creme_core.forms.bulk import BulkForm

# from .. import get_product_model
# from .base import _BaseEditForm, _BaseForm
from .fields import CategoryField

# Product = get_product_model()


# class ProductCreateForm(_BaseForm):
#     class Meta(_BaseForm.Meta):
#         model = Product
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('ProductCreateForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)


# class ProductEditForm(_BaseEditForm):
#     class Meta(_BaseEditForm.Meta):
#         model = Product
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('ProductEditForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)


class ProductInnerEditCategory(BulkForm):
    sub_category = CategoryField(label=_('Sub-category'))

    def __init__(self, model, field, user=None, entities=(), is_bulk=False, **kwargs):
        super().__init__(model, field, user, entities, is_bulk, **kwargs)

        if not is_bulk:
            self.fields['sub_category'].initial = entities[0].sub_category

    def clean(self):
        cleaned_data = super().clean()

        if self.errors:
            return cleaned_data

        sub_category = cleaned_data['sub_category']

        self._bulk_clean({
            'category': sub_category.category,
            'sub_category': sub_category,
        })

        return cleaned_data

    def save(self, *args, **kwargs):
        for entity in self.entities:
            entity.save()
