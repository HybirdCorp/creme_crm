################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CremeEntity, CustomEntityType


class CustomEntityBase(CremeEntity):
    name = models.CharField(_('Name'), max_length=50)

    # ID of the related CustomEntityType instance (so, it must be unique for each class).
    custom_id = 0

    class Meta:
        abstract = True
        app_label = 'custom_entities'
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('custom_entities__view_custom_entity', args=(self.custom_id, self.id,))

    # TODO: classmethod in CremeEntity?
    @classmethod
    def get_create_absolute_url(cls):
        return reverse('custom_entities__create_custom_entity', args=(cls.custom_id,))

    def get_edit_absolute_url(self):
        return reverse('custom_entities__edit_custom_entity', args=(self.custom_id, self.id,))

    # TODO: classmethod in CremeEntity?
    @classmethod
    def get_lv_absolute_url(cls):
        return reverse('custom_entities__list_custom_entities', args=(cls.custom_id,))


all_custom_models = []
for i in range(1, 21):
    name = f'CustomEntity{i}'
    globals()[name] = CustomEntityType.custom_classes[i] = kls = type(
        name,
        (CustomEntityBase,),  # Base classes
        {
            '__module__': 'creme.custom_entities.models',
            'custom_id':  i,
        },  # Attributes
    )
    all_custom_models.append(kls)
