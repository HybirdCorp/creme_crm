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

from ..global_info import get_per_request_cache
from .entity import CremeEntity

_all = ['CustomEntityType']
custom_classes = {}


# ------------------------------------------------------------------------------
class CustomEntityTypeManager(models.Manager):
    cache_key = 'creme_core-custom_entities'

    def _items_map(self):
        cache = get_per_request_cache()
        items_map = cache.get(self.cache_key)
        if items_map is None:
            items_map = cache[self.cache_key] = {item.number: item for item in self.all()}

        return items_map

    # TODO: better name?
    def items(self):
        yield from self._items_map().values()

    # TODO: name is more relevant if number == id (i.e. no 'number' field)
    def get_for_id(self, id: int):
        return self._items_map().get(id)


class CustomEntityType(models.Model):
    # TODO: test model for unique? (x2)
    number = models.PositiveSmallIntegerField(unique=True, editable=False)
    name   = models.CharField(unique=True, max_length=50)
    # TODO: plural name??

    objects = CustomEntityTypeManager()

    creation_label = _('Create a type of entity')
    save_label = _('Save the type of entity')

    class Meta:
        app_label = 'creme_core'
        ordering = ('name',)

    def __str__(self):
        return self.name

    # TODO: clean() to validate 'number'?

    @property
    def entity_model(self) -> type[CremeEntity]:
        return custom_classes[self.number]


# ------------------------------------------------------------------------------
def __create_model(name, base_model, fields=None, app_label='creme_core', module='', options=None):
    # Set up a dictionary to simulate declarations within a class
    attrs = {
        '__module__': module,
        'Meta': type(
            'Meta',  # Name
            (),  # Base models
            {'app_label': app_label, **(options or {})},  # Attributes
        ),
        **(fields or {}),
    }

    return type(name, (base_model,), attrs)


# TODO: abstract parent class instead ??
def _get_absolute_url(self):
    return reverse('creme_core__view_custom_entity', args=(self.custom_id, self.id,))


def _get_edit_absolute_url(self):
    return reverse('creme_core__edit_custom_entity', args=(self.custom_id, self.id,))


def _get_lv_absolute_url(cls):
    return reverse('creme_core__list_custom_entities', args=(cls.custom_id,))


for i in range(1, 6):
    name = f'CustomEntity{i}'
    globals()[name] = kls = __create_model(
        name=name,
        base_model=CremeEntity,
        module='creme.creme_core.models.custom_entity',
        fields={
            'name': models.CharField(_('Name'), max_length=50),
            'custom_id': i,
            '__str__': lambda self: self.name,
            'get_absolute_url': _get_absolute_url,
            'get_edit_absolute_url': _get_edit_absolute_url,
            # TODO: classmethod in CremeEntity?
            'get_lv_absolute_url': classmethod(_get_lv_absolute_url),
        },
        options={'ordering': ('name',)}
    )
    custom_classes[i] = kls
    _all.append(name)

__all__ = tuple(_all)
del _all
