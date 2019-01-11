# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2018  Hybird
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

from functools import partial
from json import loads as jsonloads, dumps as jsondumps
import logging

from django.contrib.contenttypes.models import ContentType
from django.db.models import TextField, FieldDoesNotExist
from django.utils.translation import ugettext_lazy as _, ugettext

from ..core.entity_cell import EntityCellRegularField
from ..global_info import get_per_request_cache
from .base import CremeModel
from .fields import CTypeOneToOneField

logger = logging.getLogger(__name__)


class FieldsConfig(CremeModel):
    content_type     = CTypeOneToOneField(editable=False, primary_key=True)  # verbose_name=_('Related type')
    raw_descriptions = TextField(editable=False)  # null=True  #TODO: JSONField ?

    creation_label = _('Create a fields configuration')
    save_label     = _('Save the configuration')

    HIDDEN = 'hidden'

    _excluded_fnames = None

    class Meta:
        app_label = 'creme_core'

    class InvalidAttribute(Exception):
        pass

    class InvalidModel(Exception):
        pass

    class LocalCache:
        __slots__ = ('_configs', )

        def __init__(self):
            self._configs = {}

        def get_4_model(self, model):
            return self.get_4_models((model,))[model]

        def get_4_models(self, models):
            result = {}
            configs = self._configs
            missing_models = []

            for model in models:
                fconf = configs.get(model)

                if fconf is None:
                    missing_models.append(model)
                else:
                    result[model] = fconf

            retrieved_configs = FieldsConfig.get_4_models(missing_models)
            configs.update(retrieved_configs)
            result.update(retrieved_configs)

            return result

        def is_fieldinfo_hidden(self, model, field_info):
            """
            @param model Class inheriting django.db.models.Model.
            @param field_info creme_core.utils.meta.FieldInfo instance.
            """
            if self.get_4_model(model).is_field_hidden(field_info[0]):
                return True

            if len(field_info) > 1:
                assert len(field_info) == 2  # TODO: manage deeper fields + unit tests

                if self.get_4_model(field_info[0].remote_field.model).is_field_hidden(field_info[1]):
                    return True

            return False

    def __str__(self):
        return ugettext('Configuration of {model}').format(model=self.content_type)

    @staticmethod
    def _check_descriptions(model, descriptions):
        safe_descriptions = []
        errors = False
        get_field = model._meta.get_field
        HIDDEN = FieldsConfig.HIDDEN

        for field_name, field_conf in descriptions:
            try:
                field = get_field(field_name)
            except FieldDoesNotExist as e:
                logger.warning('FieldsConfig: problem with field "%s" ("%s")', field_name, e)
                errors = True
                continue

            if not field.get_tag('optional'):
                logger.warning('FieldsConfig: the field "%s" is not optional', field_name)
                errors = True
                continue

            for name, value in field_conf.items():
                if name != HIDDEN:
                    raise FieldsConfig.InvalidAttribute('Invalid attribute name: "{}"'.format(name))

                if not isinstance(value, bool):
                    raise FieldsConfig.InvalidAttribute('Invalid attribute value: "{}"'.format(value))

            safe_descriptions.append((field_name, field_conf))

        return errors, safe_descriptions

    @classmethod
    def create(cls, model, descriptions=()):  # TODO: in a manager ?
        if not cls.is_model_valid(model):
            raise cls.InvalidModel("This model cannot have a FieldsConfig")

        return FieldsConfig.objects.create(content_type=ContentType.objects.get_for_model(model),
                                           descriptions=descriptions,
                                          )

    @property
    def descriptions(self):
        """Getter.
        @return Sequence of couples (field_name, attributes). 'attributes' is
                a dictionary with keys are in {FieldsConfig.HIDDEN} (yes only
                one at the moment), and values are Booleans.
                 eg:
                    [('phone',    {FieldsConfig.HIDDEN: True}),
                     ('birthday', {FieldsConfig.HIDDEN: True}),
                    ]
        """
        errors, desc = self._check_descriptions(self.content_type.model_class(),
                                                jsonloads(self.raw_descriptions),
                                               )

        if errors:
            logger.warning('FieldsConfig: we save the corrected descriptions.')
            self.descriptions = desc
            self.save()

        return desc

    @descriptions.setter
    def descriptions(self, value):
        self.raw_descriptions = jsondumps(
                self._check_descriptions(self.content_type.model_class(), value)[1]
            )

    @property
    def errors_on_hidden(self):
        """Are some hidden fields needed ?
        @return List of unicode strings.
        """
        # TODO: would be better to pas the registry as argument
        from ..gui.fields_config import fields_config_registry

        get_apps = partial(fields_config_registry.get_needing_apps,
                           model=self.content_type.model_class(),
                          )
        # TODO: cached_lazy_ugettext
        fmt = ugettext('Warning: the app «{app}» need the field «{field}».').format

        return [fmt(app=app.verbose_name, field=field.verbose_name)
                    for field in self.hidden_fields
                        for app in get_apps(field_name=field.name)
               ]

    def _get_hidden_field_names(self):
        excluded = self._excluded_fnames

        if excluded is None:
            HIDDEN = self.HIDDEN
            self._excluded_fnames = excluded = {
                fname for fname, attrs in self.descriptions if attrs.get(HIDDEN, False)
            }

        return excluded

    @staticmethod
    def field_enumerator(model):
        from ..utils.meta import ModelFieldEnumerator

        return ModelFieldEnumerator(model, deep=0, only_leafs=False).filter(viewable=True, optional=True)

    @classmethod
    def filter_cells(cls, model, cells):
        """Yields not hidden cells.
        @param model Class inheriting django.db.models.Model.
        @param cells Iterable of EntityCell instances.
        """
        fconfigs = cls.LocalCache()

        for cell in cells:
            if not isinstance(cell, EntityCellRegularField) or \
               not fconfigs.is_fieldinfo_hidden(model, cell.field_info):
                yield cell

    # TODO: in a manager ?
    @classmethod
    def get_4_model(cls, model):
        return cls.get_4_models((model,))[model]

    # TODO: in a manager ?
    @classmethod
    def get_4_models(cls, models):
        result = {}
        get_ct = ContentType.objects.get_for_model
        cache_key_fmt = 'creme_core-fields_config-{}'
        not_cached_ctypes = []

        cache = get_per_request_cache()

        # Step 1: fill 'result' with cached configs
        for model in models:
            ct = get_ct(model)
            fc = cache.get(cache_key_fmt.format(ct.id))

            if fc is None:
                if cls.is_model_valid(model):  # Avoid useless queries
                    not_cached_ctypes.append(ct)
            else:
                result[model] = fc

        # Step 2: fill 'result' with configs in DB
        for fc in FieldsConfig.objects.filter(content_type__in=not_cached_ctypes):
            ct = fc.content_type
            result[ct.model_class()] = cache[cache_key_fmt.format(ct.id)] = fc

        # Step 3: fill 'result' with empty configs for remaining models
        for model in models:
            if model not in result:
                ct = get_ct(model)
                result[model] = cache[cache_key_fmt.format(ct.id)] = \
                    FieldsConfig(content_type=ct, descriptions=())

        return result

    @property
    def hidden_fields(self):
        get_field = self.content_type.model_class()._meta.get_field

        for field_name in self._get_hidden_field_names():
            yield get_field(field_name)

    def is_field_hidden(self, field):
        return field.name in self._get_hidden_field_names()

    def is_fieldname_hidden(self, field_name):
        "NB: if the field does not exist, it is considered as hidden."
        try:
            field = self.content_type.model_class()._meta.get_field(field_name)
        except FieldDoesNotExist:
            return True

        return self.is_field_hidden(field)

    @classmethod
    def is_model_valid(cls, model):
        return any(cls.field_enumerator(model))

    def update_form_fields(self, form_fields):
        for field_name in self._get_hidden_field_names():
            form_fields.pop(field_name, None)
