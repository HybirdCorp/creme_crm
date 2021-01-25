# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2021  Hybird
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
from django.db.models.query_utils import Q
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeForm  # CremeEntityForm
from creme.creme_core.gui.custom_form import CustomFormExtraSubCell
from creme.documents.forms.fields import MultiImageEntityField

from .fields import CategoryField


class SubCategorySubCell(CustomFormExtraSubCell):
    sub_type_id = 'products_subcategory'
    verbose_name = _('Category & sub-category')

    def formfield(self, instance, user, **kwargs):
        field = CategoryField(label=self.verbose_name, user=user, **kwargs)

        if instance.sub_category_id:
            field.initial = instance.sub_category

        return field

    def post_clean_instance(self, *, instance, value, form):
        instance.category = value.category
        instance.sub_category = value


# class _BaseForm(CremeEntityForm):
#     sub_category = CategoryField(label=_('Sub-category'))
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('products.forms.base._BaseForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)
#
#     class Meta(CremeEntityForm.Meta):
#         # model = OVERLOAD ME
#         exclude = (*CremeEntityForm.Meta.exclude, 'category', 'sub_category')
#
#     def save(self, *args, **kwargs):
#         instance = self.instance
#         sub_category = self.cleaned_data['sub_category']
#
#         instance.category = sub_category.category
#         instance.sub_category = sub_category
#
#         return super().save(*args, **kwargs)


# class _BaseEditForm(_BaseForm):
#     class Meta(_BaseForm.Meta):
#         # model = OVERLOAD ME
#         exclude = (*_BaseForm.Meta.exclude, 'images')
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('products.forms.base._BaseEditForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)
#         self.fields['sub_category'].initial = self.instance.sub_category


class AddImagesForm(CremeForm):
    images = MultiImageEntityField(label=_('Images'))

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entity = entity

        images_f = self.fields['images']
        images_f.q_filter = ~Q(id__in=[*entity.images.values_list('id', flat=True)])
        images_f.force_creation = True

    def save(self):
        add_image = self.entity.images.add

        for image in self.cleaned_data['images']:
            add_image(image)
