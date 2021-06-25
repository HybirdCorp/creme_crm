# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2021  Hybird
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

from collections import defaultdict
from typing import DefaultDict, Iterator, Set, Type

from django.apps import AppConfig, apps
from django.db.models import Model

from creme.creme_core.models import CremeModel


class FieldsConfigRegistry:
    """Registry related to model fields configuration.
    See <creme_core.models.FieldsConfig>.
    """
    _needed_fields: DefaultDict[Type[Model], DefaultDict[str, Set[str]]]

    def __init__(self):
        self._models = set()
        # Structure: [model][field_name] -> set of app_labels
        self._needed_fields = defaultdict(lambda: defaultdict(set))

    def get_needing_apps(self,
                         model: Type[CremeModel],
                         field_name: str,
                         ) -> Iterator[AppConfig]:
        """Get the apps which need a given field."""
        for app_label in self._needed_fields[model][field_name]:
            yield apps.get_app_config(app_label)

    def is_model_registered(self, model: Type[Model]) -> bool:
        return model in self._models

    @property
    def models(self) -> Iterator[Type[CremeModel]]:
        "Get the registered models."
        return iter(self._models)

    def register_models(self, *models: Type[CremeModel]):
        """Register models which can have a fields configuration.
        Models must inherit CremeModel in order to get a correct 'full_clean()'
        implementation.
        """
        self._models.update(models)
        return self

    def register_needed_fields(self,
                               app_label: str,
                               model: Type[CremeModel],
                               *field_names: str,
                               ) -> 'FieldsConfigRegistry':
        """Register the fields of other apps which are required."""
        model_fields = self._needed_fields[model]

        for field_name in field_names:
            model_fields[field_name].add(app_label)

        return self


fields_config_registry = FieldsConfigRegistry()
