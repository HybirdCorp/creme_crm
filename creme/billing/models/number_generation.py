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

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from creme.creme_core.global_info import get_per_request_cache
from creme.creme_core.models import CremeModel
from creme.creme_core.models.fields import EntityCTypeForeignKey
from creme.persons.models import AbstractOrganisation

from .base import Base


class NumberGeneratorItemManager(models.Manager):
    class ItemsForModel:
        def __init__(self, items):
            self._items = {item.organisation_id: item for item in items}

        def __iter__(self):
            yield from self._items.values()

        def get_for_organisation(self,
                                 organisation: AbstractOrganisation,
                                 ) -> NumberGeneratorItem | None:
            return self._items.get(organisation.id)

    def get_for_model(self, model: type[Base]) -> ItemsForModel:
        cache_key = f'billing-number_{model.__name__.lower()}'
        cache = get_per_request_cache()

        try:
            items = cache[cache_key]
        except KeyError:
            cache[cache_key] = items = self.ItemsForModel(
                self.filter(numbered_type=ContentType.objects.get_for_model(model))
                # TODO: <select_related('organisation')> ?
            )

        return items

    def get_for_instance(self, entity: Base) -> NumberGeneratorItem | None:
        return self.get_for_model(type(entity)).get_for_organisation(entity.source)


class NumberGeneratorItem(CremeModel):
    organisation = models.ForeignKey(
        settings.PERSONS_ORGANISATION_MODEL, on_delete=models.CASCADE,
    )
    numbered_type = EntityCTypeForeignKey()
    is_edition_allowed = models.BooleanField(
        verbose_name=_('Editable number'),
        help_text=_('Can the number be manually edited?'),
        default=True,
    )
    data = models.JSONField(default=dict)

    objects = NumberGeneratorItemManager()

    class Meta:
        app_label = 'billing'
        unique_together = ('organisation', 'numbered_type')

    def __eq__(self, other):
        return (
            isinstance(other, type(self))
            and self.organisation_id == other.organisation_id
            and self.numbered_type == other.numbered_type
            and self.is_edition_allowed == other.is_edition_allowed
            and self.data == other.data
        )

    # NB: we define __hash__() it because we define __eq__();
    #     not defining it makes delete() crash.
    def __hash__(self):
        return self.id

    def __str__(self):
        return (
            f'NumberGenerationItem('
            f'organisation="{self.organisation}", '
            f'numbered_type="{self.numbered_type}", '
            f'data={self.data}'
            f')'
        )

    @property
    def description(self) -> list[str]:
        from creme.billing.core import number_generation

        gen = number_generation.number_generator_registry.get(item=self)

        return gen.description if gen else ['??']
