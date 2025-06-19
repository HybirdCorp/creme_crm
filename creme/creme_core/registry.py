################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

import logging
from collections.abc import Container, Iterator
from typing import TYPE_CHECKING

from django.utils.datastructures import OrderedSet

if TYPE_CHECKING:
    from .models import CremeEntity

logger = logging.getLogger(__name__)


class CremeRegistry:
    """Registry for CremeEntity models."""
    def __init__(self):
        self._entity_models = OrderedSet()

    def register_entity_models(self, *models: type[CremeEntity]) -> CremeRegistry:
        """Register CremeEntity models."""
        from .models import CremeEntity

        entity_models = self._entity_models

        for model in models:
            if not issubclass(model, CremeEntity):
                logger.critical(
                    'CremeRegistry.register_entity_models: %s is not '
                    'a subclass of CremeEntity, so we ignore it', model,
                )
                continue

            entity_models.add(model)

        return self

    def is_entity_model_registered(self, model: type[CremeEntity]) -> bool:
        return model in self._entity_models

    def iter_entity_models(self,
                           app_labels: Container[str] | None = None,
                           ) -> Iterator[type[CremeEntity]]:
        """Iterate on the registered models.
        @param app_labels: If None is given, all the registered models are yielded.
               If a container of app labels is given, only models related to
               these apps are yielded.
        """
        from .models import CustomEntityType

        if app_labels is None:
            yield from self._entity_models
            for ce_type in CustomEntityType.objects.all_types():
                if ce_type.enabled:  # TODO: in all_types()?
                    yield ce_type.entity_model
        else:
            for model in self._entity_models:
                if model._meta.app_label in app_labels:
                    yield model

            for ce_type in CustomEntityType.objects.all_types():
                if ce_type.enabled:  # TODO: in all_types()?
                    model = ce_type.entity_model
                    if model._meta.app_label in app_labels:
                        yield model


creme_registry = CremeRegistry()
