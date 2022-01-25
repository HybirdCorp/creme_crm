# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2022  Hybird
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
# import warnings
import warnings
from functools import partial
from itertools import chain
from json import loads as json_load
from typing import (
    TYPE_CHECKING,
    Dict,
    FrozenSet,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
)

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models import BooleanField
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from ..core.field_tags import FieldTag
from ..global_info import get_per_request_cache
from ..utils.meta import FieldInfo
from ..utils.serializers import json_encode
from .base import CremeModel
from .fields import CTypeOneToOneField

if TYPE_CHECKING:
    # from ..utils.meta import ModelFieldEnumerator
    from django.db.models import Field, Model


logger = logging.getLogger(__name__)
FieldsDescriptions = List[Tuple[str, Dict[str, bool]]]


# TODO ?
# from enum import Enum
#
# class FieldsConfigFlag(Enum):
#     HIDDEN = 'hidden'
#     REQUIRED = 'required'
#
#     @classmethod
#     def is_valid(cls, value):
#         try:
#             cls(value)
#         except ValueError:
#             return False
#
#         return True
#
#     def __str__(self):
#         return self.value


class FieldsConfigManager(models.Manager):
    def configurable_fields(self, model: Type['Model']) -> Iterator[Tuple['Field', List[str]]]:
        conf_model = self.model
        REQUIRED = conf_model.REQUIRED
        HIDDEN = conf_model.HIDDEN
        meta = model._meta

        for field in chain(meta.fields, meta.many_to_many):
            if not field.get_tag(FieldTag.VIEWABLE):
                continue

            flags = []

            if (
                field.editable
                and field.blank
                and not field.many_to_many
                and not isinstance(field, BooleanField)
            ):
                # TODO: allow ManyToManyFields ?
                #   BEWARE: in CremeModel.full_clean() M2M cannot be checked,
                #           so in mass import they have to be checked specifically.
                flags.append(REQUIRED)

            if field.get_tag(FieldTag.OPTIONAL):
                flags.append(HIDDEN)

            if flags:
                yield field, flags

    # def field_enumerator(self, model: Type['Model']) -> 'ModelFieldEnumerator':
    #     from ..utils.meta import ModelFieldEnumerator
    #
    #     return ModelFieldEnumerator(
    #         # model, deep=0, only_leafs=False,
    #         model, depth=0, only_leaves=False,
    #     ).filter(viewable=True, optional=True)

    def get_by_natural_key(self, app_label, model):
        ct = ContentType.objects.get_by_natural_key(app_label, model)
        return self.get_for_model(ct.model_class())

    def get_for_model(self, model: Type['Model']) -> 'FieldsConfig':
        return self.get_for_models((model,))[model]

    def get_for_models(self,
                       models: Sequence[Type['Model']],
                       ) -> Dict[Type['Model'], 'FieldsConfig']:
        result = {}
        get_ct = ContentType.objects.get_for_model
        cache_key_fmt = 'creme_core-fields_config-{}'.format
        not_cached_ctypes = []

        cache = get_per_request_cache()

        # Step 1: fill 'result' with cached configs
        for model in models:
            ct = get_ct(model)
            fc = cache.get(cache_key_fmt(ct.id))

            if fc is None:
                # if self.is_model_valid(model):  # Avoid useless queries
                if self.has_configurable_fields(model):  # Avoid useless queries
                    not_cached_ctypes.append(ct)
            else:
                result[model] = fc

        # Step 2: fill 'result' with configs in DB
        for fc in self.filter(content_type__in=not_cached_ctypes):
            ct = fc.content_type
            result[ct.model_class()] = cache[cache_key_fmt(ct.id)] = fc

        # Step 3: fill 'result' with empty configs for remaining models
        for model in models:
            if model not in result:
                ct = get_ct(model)
                result[model] = cache[cache_key_fmt(ct.id)] = self.model(
                    content_type=ct,
                    descriptions=(),
                )

        return result

    def has_configurable_fields(self, model: Type['Model']) -> bool:
        return any(self.configurable_fields(model))

    def is_model_valid(self, model: Type['Model']) -> bool:
        # return any(self.field_enumerator(model))
        warnings.warn(
            'FieldsConfigManager.is_model_valid() is deprecated ; '
            'use has_configurable_fields() instead.',
            DeprecationWarning,
        )

        return self.has_configurable_fields(model)


class FieldsConfig(CremeModel):
    content_type = CTypeOneToOneField(editable=False, primary_key=True)
    raw_descriptions = models.TextField(editable=False)  # TODO: JSONField ?

    objects = FieldsConfigManager()

    creation_label = _('Create a fields configuration')
    save_label     = _('Save the configuration')

    HIDDEN = 'hidden'
    REQUIRED = 'required'

    _excluded_fnames: Optional[Set[str]] = None  # TODO: FrozenSet
    _required_fnames: Optional[FrozenSet[str]] = None

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

        def get_4_model(self, model: Type['Model']) -> 'FieldsConfig':
            # return self.get_4_models((model,))[model]
            warnings.warn(
                'FieldsConfig.LocalCache.get_4_model() is deprecated ; '
                'use get_for_model() instead.',
                DeprecationWarning,
            )

            return self.get_for_model(model)

        def get_for_model(self, model: Type['Model']) -> 'FieldsConfig':
            return self.get_for_models((model,))[model]

        def get_4_models(self,
                         models: Iterable[Type['Model']],
                         ) -> Dict[Type['Model'], 'FieldsConfig']:
            warnings.warn(
                'FieldsConfig.LocalCache.get_4_models() is deprecated ; '
                'use get_for_models() instead.',
                DeprecationWarning,
            )

            return self.get_for_models(models)

        def get_for_models(self,
                           models: Iterable[Type['Model']],
                           ) -> Dict[Type['Model'], 'FieldsConfig']:
            result = {}
            configs = self._configs
            missing_models = []

            for model in models:
                fconf = configs.get(model)

                if fconf is None:
                    missing_models.append(model)
                else:
                    result[model] = fconf

            retrieved_configs = FieldsConfig.objects.get_for_models(missing_models)
            configs.update(retrieved_configs)
            result.update(retrieved_configs)

            return result

        def is_fieldinfo_hidden(self, field_info: FieldInfo) -> bool:
            """Is one of the fields in the chain hidden?
            @param field_info: creme_core.utils.meta.FieldInfo instance.
            """
            fields_n_models = []
            related_model = field_info.model
            for field in field_info:
                # if field.get_tag('optional'):
                if field.get_tag(FieldTag.OPTIONAL):
                    fields_n_models.append((field, related_model))

                if field.is_relation:
                    related_model = field.remote_field.model

            fconfigs = self.get_for_models(
                {field_n_model[1] for field_n_model in fields_n_models}
            )

            return any(
                fconfigs[model].is_field_hidden(field)
                for field, model in fields_n_models
            )

    def __str__(self):
        return gettext('Configuration of {model}').format(model=self.content_type)

    @classmethod
    def _check_descriptions(cls, model: Type['Model'], descriptions):
        safe_descriptions = []
        errors = False
        get_field = model._meta.get_field
        HIDDEN = cls.HIDDEN
        REQUIRED = cls.REQUIRED

        for field_name, field_conf in descriptions:
            try:
                field = get_field(field_name)
            except FieldDoesNotExist as e:
                logger.warning('FieldsConfig: problem with field "%s" ("%s")', field_name, e)
                errors = True
                continue

            if not field.get_tag(FieldTag.VIEWABLE):
                logger.warning('FieldsConfig: the field "%s" is not viewable', field_name)
                errors = True
                continue

            if HIDDEN in field_conf and REQUIRED in field_conf:
                raise FieldsConfig.InvalidAttribute(
                    f'The field "{field_name}" cannot be hidden & required at the same time'
                )

            valid_conf = {}

            for name, value in field_conf.items():
                if name == HIDDEN:
                    if not field.get_tag(FieldTag.OPTIONAL):
                        logger.warning('FieldsConfig: the field "%s" is not optional', field_name)
                        errors = True
                        continue
                elif name == REQUIRED:
                    if not field.editable:
                        logger.warning('FieldsConfig: the field "%s" is not editable', field_name)
                        errors = True
                        continue

                    if not field.blank:
                        logger.warning('FieldsConfig: the field "%s" is not blank', field_name)
                        errors = True
                        continue

                    if field.many_to_many:
                        logger.warning(
                            'FieldsConfig: the field "%s" is a ManyToManyField '
                            '& cannot be required',
                            field_name
                        )
                        errors = True
                        continue
                else:
                    raise FieldsConfig.InvalidAttribute(f'Invalid attribute name: "{name}"')

                if not isinstance(value, bool):
                    raise FieldsConfig.InvalidAttribute(f'Invalid attribute value: "{value}"')

                valid_conf[name] = value

            if valid_conf:
                safe_descriptions.append((field_name, valid_conf))

        # NB: we sort by field name to keep a stable order through editions
        safe_descriptions.sort(key=lambda t: t[0])

        return errors, safe_descriptions

    # @classmethod
    # def create(cls, model, descriptions=()):
    #     warnings.warn('FieldsConfig.create() is deprecated ; '
    #                   'use FieldsConfig.objects.create() instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     return cls.objects.create(content_type=model, descriptions=descriptions)

    @property
    def descriptions(self) -> FieldsDescriptions:
        """Getter.
        @return List of couples (field_name, attributes). 'attributes' is a dictionary
                which keys are in {FieldsConfig.HIDDEN, FieldsConfig.REQUIRED},
                and values are Booleans.
                 eg:
                    [
                        ('phone',    {FieldsConfig.REQUIRED: True}),
                        ('birthday', {FieldsConfig.HIDDEN: True}),
                    ]
        """
        errors, desc = self._check_descriptions(
            self.content_type.model_class(),
            json_load(self.raw_descriptions),
        )

        if errors:
            logger.warning('FieldsConfig: we save the corrected descriptions.')
            self.descriptions = desc
            self.save()

        return desc

    @descriptions.setter
    def descriptions(self, value: FieldsDescriptions) -> None:
        ctype = self.content_type
        if not ctype:
            raise ValueError(
                'FieldsConfig.descriptions: '
                'the content type has not been passed or is invalid.'
            )

        model = ctype.model_class()
        assert model is not None

        self.raw_descriptions = json_encode(
            self._check_descriptions(model, value)[1]
        )

    @property
    def errors_on_hidden(self) -> List[str]:
        """Are some hidden fields needed ?
        @return List of strings.
        """
        # TODO: pass the registry as argument/store it in an (class?) attribute
        from ..gui.fields_config import fields_config_registry

        get_apps = partial(
            fields_config_registry.get_needing_apps,
            model=self.content_type.model_class(),
        )
        # TODO: cached_lazy_gettext
        fmt = gettext('Warning: the app «{app}» need the field «{field}».').format

        return [
            fmt(app=app.verbose_name, field=field.verbose_name)
            for field in self.hidden_fields
            for app in get_apps(field_name=field.name)
        ]

    # TODO: frozenset + property (see 'required_field_names()')
    def _get_hidden_field_names(self) -> Set[str]:
        excluded = self._excluded_fnames

        if excluded is None:
            HIDDEN = self.HIDDEN
            self._excluded_fnames = excluded = {
                fname
                for fname, attrs in self.descriptions if attrs.get(HIDDEN, False)
            }

        return excluded

    # TODO: factorise with _get_hidden_field_names
    @property
    def required_field_names(self) -> FrozenSet[str]:
        """Get the names of fields which are required by configuration.
        Notice that fields which are "naturally" required are ignored, only the
        configured ones are returned.
        """
        required = self._required_fnames

        if required is None:
            REQUIRED = self.REQUIRED
            self._required_fnames = required = frozenset(
                fname
                for fname, attrs in self.descriptions if attrs.get(REQUIRED, False)
            )

        return required

    # @classmethod
    # def field_enumerator(cls, model):
    #     warnings.warn('FieldsConfig.field_enumerator() is deprecated ; '
    #                   'use FieldsConfig.objects.field_enumerator() instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     return cls.objects.field_enumerator(model)

    # @classmethod
    # def filter_cells(cls,
    #                  model: Type['Model'],
    #                  cells):
    #     """Yields not hidden cells.
    #     @param model: Class inheriting django.db.models.Model.
    #     @param cells: Iterable of EntityCell instances.
    #     @yield EntityCell instances.
    #     """
    #     warnings.warn(
    #         'FieldsConfig.filter_cells() is deprecated ; '
    #         'use EntityCell.is_excluded instead.',
    #         DeprecationWarning
    #     )
    #
    #     from ..core.entity_cell import EntityCellRegularField
    #
    #     fconfigs = cls.LocalCache()
    #
    #     for cell in cells:
    #         if (
    #             not isinstance(cell, EntityCellRegularField)
    #             or
    #             not fconfigs.is_fieldinfo_hidden(cell.field_info)
    #         ):
    #             yield cell

    # @classmethod
    # def get_4_model(cls, model):
    #     warnings.warn('FieldsConfig.get_4_model() is deprecated ; '
    #                   'use FieldsConfig.objects.get_for_model() instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     return cls.objects.get_for_model(model)

    # @classmethod
    # def get_4_models(cls, models):
    #     warnings.warn('FieldsConfig.get_4_models() is deprecated ; '
    #                   'use FieldsConfig.objects.get_for_models() instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     return cls.objects.get_for_models(models)

    @property
    def hidden_fields(self) -> Iterator['Field']:
        get_field = self.content_type.model_class()._meta.get_field

        for field_name in self._get_hidden_field_names():
            yield get_field(field_name)

    # TODO: factorise
    @property
    def required_fields(self) -> Iterator['Field']:
        get_field = self.content_type.model_class()._meta.get_field

        for field_name in self.required_field_names:
            yield get_field(field_name)

    def is_field_hidden(self, field: 'Field') -> bool:
        return field.name in self._get_hidden_field_names()

    def is_field_required(self, field: 'Field') -> bool:
        "Is a field required (naturally or by configuration)?"
        return (
            not isinstance(field, BooleanField)
            and (
                not field.blank or field.name in self.required_field_names
            )
        )

    def is_fieldname_hidden(self, field_name: str) -> bool:
        "NB: if the field does not exist, it is considered as hidden."
        try:
            field = self.content_type.model_class()._meta.get_field(field_name)
        except FieldDoesNotExist:
            return True

        return self.is_field_hidden(field)

    def is_fieldname_required(self, field_name: str) -> bool:
        # "NB: if the field does not exist, it is considered as not required."
        # try:
        field = self.content_type.model_class()._meta.get_field(field_name)
        # except FieldDoesNotExist:
        #     return True  # TODO ?

        return self.is_field_required(field)

    # @classmethod
    # def is_model_valid(cls, model):
    #     warnings.warn('FieldsConfig.is_model_valid() is deprecated ; '
    #                   'use FieldsConfig.objects.is_model_valid() instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     return cls.objects.is_model_valid(model)

    # def save(self, *args, **kwargs):
    #     if not type(self).objects.is_model_valid(self.content_type.model_class()):
    #         raise self.InvalidModel("This model cannot have a FieldsConfig")
    #
    #     super().save(*args, **kwargs)

    def update_form_fields(self, form_fields) -> None:
        for field_name in self._get_hidden_field_names():
            form_fields.pop(field_name, None)

        for field_name in self.required_field_names:
            try:
                form_fields[field_name].required = True
            except KeyError:
                # TODO: we need the form class for a better message
                logger.critical(
                    'The field "%s" has been configured to be required '
                    'but the current form does not use this field ; '
                    'please contact your administrator.',
                    field_name,
                )
                # TODO: is it possible that field does not exist any more ?
                form_fields[field_name] = (
                    self.content_type
                        .model_class()
                        ._meta
                        .get_field(field_name)
                        .formfield(required=True)
                )

    def natural_key(self):
        return self.content_type.natural_key()
