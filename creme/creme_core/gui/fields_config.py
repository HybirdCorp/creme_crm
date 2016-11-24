# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2016  Hybird
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
# from itertools import chain
import warnings

from django.apps import apps
# from django.contrib.contenttypes.models import ContentType

from ..models import FieldsConfig  # CremeEntity
# from ..registry import creme_registry


class FieldsConfigRegistry(object):
    """Register the fields of other apps which are required."""
    # """Gives the models which can have a Fields configuration (see models.FieldsConfig).
    # The CremeEntity models are always configurable, & so they do not need to be
    # registered.
    # """
    def __init__(self):
        # self._extra_models = set()
        # Structure: [model][field_name] -> set of app_labels
        self._needed_fields = defaultdict(lambda: defaultdict(set))

    @property
    def ctypes(self):
        # get_for_model = ContentType.objects.get_for_model
        #
        # return (get_for_model(model)
        #             for model in chain(creme_registry.iter_entity_models(),
        #                                self._extra_models,
        #                               )
        #        )
        warnings.warn("FieldsConfigRegistry.ctypes property is deprecated ; "
                      "use FieldsConfig.valid_ctypes() instead.",
                      DeprecationWarning
                     )

        from itertools import ifilter, imap

        from django.contrib.contenttypes.models import ContentType

        return imap(ContentType.objects.get_for_model,
                    ifilter(FieldsConfig.is_model_valid, apps.get_models())
                   )

    def get_needing_apps(self, model, field_name):
        for app_label in self._needed_fields[model][field_name]:
            yield apps.get_app_config(app_label)

    def is_model_valid(self, model):
        # if creme_registry.is_entity_model_registered(model):
        #     return True
        #
        # return model in self._extra_models
        warnings.warn("FieldsConfigRegistry.is_model_valid() method is deprecated ; "
                      "use FieldsConfig.is_model_valid() instead.",
                      DeprecationWarning
                     )

        return FieldsConfig.is_model_valid(model)

    # def register(self, model):
    #     assert not issubclass(model, CremeEntity)
    #     self._extra_models.add(model)

    def register_needed_fields(self, app_label, model, *field_names):
        model_fields = self._needed_fields[model]

        for field_name in field_names:
            model_fields[field_name].add(app_label)


fields_config_registry = FieldsConfigRegistry()
