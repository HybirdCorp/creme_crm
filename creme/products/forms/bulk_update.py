################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

from django.utils.translation import gettext as _

# from creme.creme_core.forms.bulk import BulkForm
from creme.creme_core.gui.bulk_update import FieldOverrider

from .fields import SubCategoryField


# class ProductInnerEditCategory(BulkForm):
#     sub_category = CategoryField(label=_('Sub-category'))
#
#     def __init__(self, model, field, user=None, entities=(), is_bulk=False, **kwargs):
#         super().__init__(model, field, user, entities, is_bulk, **kwargs)
#
#         if not is_bulk:
#             self.fields['sub_category'].initial = entities[0].sub_category
#
#     def clean(self):
#         cleaned_data = super().clean()
#
#         if self.errors:
#             return cleaned_data
#
#         sub_category = cleaned_data['sub_category']
#
#         self._bulk_clean({
#             'category': sub_category.category,
#             'sub_category': sub_category,
#         })
#
#         return cleaned_data
#
#     def save(self, *args, **kwargs):
#         for entity in self.entities:
#             entity.save()
class CategoryOverrider(FieldOverrider):
    field_names = ['category', 'sub_category']

    def formfield(self, instances, user, **kwargs):
        field = SubCategoryField(
            model=type(instances[0]),
            field_name='sub_category',
            label=_('Sub-category'),
            user=user
        )

        if len(instances) == 1:
            instance = instances[0]
            if instance.pk:
                field.initial = instance.sub_category

        return field

    def post_clean_instance(self, *, instance, value, form):
        if value:
            instance.sub_category = value
            instance.category = value.category
