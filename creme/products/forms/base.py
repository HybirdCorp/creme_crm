# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014  Hybird
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

from creme.creme_core.forms import CremeEntityForm, CremeForm
from creme.creme_core.forms.fields import MultiCreatorEntityField
from creme.creme_core.forms.validators import validate_linkable_entities

from creme.media_managers.models import Image

from .fields import CategoryField


class _BaseForm(CremeEntityForm):
    sub_category = CategoryField(label=_(u'Sub-category'))

    class Meta(CremeEntityForm.Meta):
        #model = OVERLOAD ME
        exclude = CremeEntityForm.Meta.exclude + ('category', 'sub_category')

    def save(self, *args, **kwargs):
        instance = self.instance
        sub_category = self.cleaned_data['sub_category']

        instance.category = sub_category.category
        instance.sub_category = sub_category

        return super(_BaseForm, self).save(*args, **kwargs)


class _BaseCreateForm(_BaseForm):
    images = MultiCreatorEntityField(label=_(u'Images'), model=Image, required=False)

    def clean_images(self):
        return validate_linkable_entities(self.cleaned_data['images'], self.user)


class _BaseEditForm(_BaseForm):
    class Meta(_BaseForm.Meta):
        #model = OVERLOAD ME
        exclude = _BaseForm.Meta.exclude + ('images',)

    def __init__(self, *args, **kwargs):
        super(_BaseEditForm, self).__init__(*args, **kwargs)
        self.fields['sub_category'].initial = self.instance.sub_category


class AddImagesForm(CremeForm):
    images = MultiCreatorEntityField(label=_(u'Images'), model=Image)

    def __init__(self, entity, *args, **kwargs):
        super(AddImagesForm, self).__init__(*args, **kwargs)
        self.entity = entity
        self.fields['images'].q_filter = {'~id__in': list(entity.images.values_list('id', flat=True))}

    def clean_images(self):
        return validate_linkable_entities(self.cleaned_data['images'], self.user)

    def save(self):
        add_image = self.entity.images.add

        for image in self.cleaned_data['images']:
            add_image(image)
