# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

import logging
from typing import TYPE_CHECKING, Iterator, Type

from django.utils.datastructures import OrderedSet

if TYPE_CHECKING:
    from .models import CremeEntity

logger = logging.getLogger(__name__)


class CremeRegistry:
    """Registry for Creme Applications and Entities."""
    def __init__(self):
        self._entity_models = OrderedSet()

    def register_entity_models(self, *models: Type['CremeEntity']) -> None:
        """Register CremeEntity models."""
        from .models import CremeEntity

        entity_models = self._entity_models

        for model in models:
            if not issubclass(model, CremeEntity):
                logger.critical(
                    'CremeRegistry.register_entity_models: "%s" is not'
                    ' a subclass of CremeEntity, so we ignore it', model,
                )
                continue

            entity_models.add(model)

    def is_entity_model_registered(self, model: Type['CremeEntity']) -> bool:
        return model in self._entity_models

    def iter_entity_models(self) -> Iterator[Type['CremeEntity']]:
        return iter(self._entity_models)


creme_registry = CremeRegistry()
