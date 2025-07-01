################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025  Hybird
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

from collections.abc import Iterator

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
        """Get all existing type of custom entities.
        Notice that it totally  ignores the values of the fields 'enabled' & 'deleted'.
        """
        yield from self._cached_types().values()

    def get_for_id(self, id: int) -> CustomEntityType | None:
        """Get an instance of CustomEntityType by its ID in database."""
        return self._cached_types().get(id)

    def get_for_model(self, model: type[models.Model]) -> CustomEntityType | None:
        """Get the instance of CustomEntityType corresponding to a model
        <None> is returned if the model does not correspond a custom type.
        """
        for id, custom_model in CustomEntityType.custom_classes.items():
            if custom_model == model:
                return self.get_for_id(id)

        return None


class CustomEntityType(models.Model):
    """A CustomEntityType is related to a model inheriting CremeEntity, and it
    can be configured by the administrators in order this type corresponds to
    the meaning they want.
    Once a type is enabled, the related model:
      - gets menu entries to its creation view & its list-view.
      - can have HeaderFilters & EntityFilters to customise the list-view as a
        regular CremeEntity model.
      - can have bricks & buttons to customise the detail-view as a
        regular CremeEntity model.
      - etc...
    """
    # We cannot rely on the model's _meta.verbose_name & _meta.verbose_name_plural
    # because they are hard coded in the class definition. We must store them in DB.
    name        = models.CharField(_('Name'), max_length=50)
    plural_name = models.CharField(_('Name (plural)'), max_length=50)

    # If enabled == True, the type is used (i.e. it is visible by users as a real entity type)
    # When an administrator want to disable a type, we first mark it as <deleted==true>.
    # So the type is not available to create new instances, & existing instances
    # can be calmly deleted. And when all instances have been removed, the type
    # can be safely marked as <enabled==False> again.
    # TODO: should we use a PositiveSmallIntegerField with 3 values
    #       (ENABLED/SOON_DISABLED/DISABLED)??
    enabled = models.BooleanField(default=False, editable=False)
    deleted = models.BooleanField(default=False, editable=False)

    objects = CustomEntityTypeManager()

    # TODO: model fields for that?
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
        """Get the model corresponding to this instance."""
        return self.custom_classes[self.id]
