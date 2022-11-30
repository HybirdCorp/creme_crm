################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2022  Hybird
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

from django.db.models.query_utils import Q
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeForm
from creme.creme_core.gui.custom_form import CustomFormExtraSubCell
from creme.documents.forms.fields import MultiImageEntityField

from .fields import SubCategoryField


class SubCategorySubCell(CustomFormExtraSubCell):
    sub_type_id = 'products_subcategory'
    verbose_name = _('Category & sub-category')

    def formfield(self, instance, user, **kwargs):
        field = SubCategoryField(
            model=type(instance),
            field_name='sub_category',
            label=self.verbose_name,
            user=user,
            **kwargs
        )

        if instance.sub_category_id:
            field.initial = instance.sub_category

        return field

    def post_clean_instance(self, *, instance, value, form):
        if value:
            instance.category = value.category
            instance.sub_category = value


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
