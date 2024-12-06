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

from __future__ import annotations

from typing import Iterator

from django.db import models
from django.utils.translation import gettext_lazy as _

from ..global_info import get_per_request_cache
from .entity import CremeEntity


class CustomEntityTypeManager(models.Manager):
    cache_key = 'creme_core-custom_entities'

    def _cached_types(self):
        cache = get_per_request_cache()
        types = cache.get(self.cache_key)
        if types is None:
            types = cache[self.cache_key] = {ce_type.id: ce_type for ce_type in self.all()}

        return types

    def all_types(self) -> Iterator[CustomEntityType]:
        yield from self._cached_types().values()

    def get_for_id(self, id: int) -> CustomEntityType | None:
        return self._cached_types().get(id)

    def get_for_model(self, model: type[models.Model]) -> CustomEntityType | None:
        for id, custom_model in CustomEntityType.custom_classes.items():
            if custom_model == model:
                return self.get_for_id(id)

        return None


class CustomEntityType(models.Model):
    name        = models.CharField(_('Name'), max_length=50)
    plural_name = models.CharField(_('Name (plural)'), max_length=50)

    enabled = models.BooleanField(default=False, editable=False)
    deleted = models.BooleanField(default=False, editable=False)

    objects = CustomEntityTypeManager()

    creation_label = _('Create a type of entity')
    save_label = _('Save the type of entity')

    # NB: all model-classes which can be used as custom entity should be added
    #     to this dict. The <int> MUST be the ID of the CustomEntityType's instance
    #     corresponding to these classes. See
    #      - creme.creme_core.populate._populate_custom_entity_types()
    #      - creme.custom_entities.models
    custom_classes: dict[int, type[CremeEntity]] = {}

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('Custom entity')
        verbose_name_plural = _('Custom entities')
        ordering = ('name',)

    def __str__(self):
        return self.name

    @property
    def entity_model(self) -> type[CremeEntity]:
        return self.custom_classes[self.id]
