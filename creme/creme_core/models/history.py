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
import warnings
from builtins import getattr
from datetime import date, datetime, time
from decimal import Decimal
from functools import partial
from json import JSONEncoder
from json import loads as json_load
from typing import (
    Any,
    Callable,
    Container,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Type,
    Union,
)

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import models
from django.db.models import Field, ForeignKey, Model, signals
from django.db.models.base import ModelState
from django.db.transaction import atomic
from django.dispatch import receiver
from django.utils.formats import date_format, number_format
from django.utils.timezone import localtime
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext

from ..core.field_tags import FieldTag
from ..global_info import (
    cached_per_request,
    get_global_info,
    get_per_request_cache,
    set_global_info,
)
from ..signals import pre_merge_related
from ..utils.dates import (
    date_from_ISO8601,
    date_to_ISO8601,
    dt_from_ISO8601,
    dt_to_ISO8601,
)
from ..utils.translation import get_model_verbose_name
from .creme_property import CremeProperty, CremePropertyType
from .custom_field import (
    CustomField,
    CustomFieldEnum,
    CustomFieldMultiEnum,
    CustomFieldValue,
)
from .entity import CremeEntity
from .entity_filter import EntityFilter
from .fields import CreationDateTimeField, CremeUserForeignKey, CTypeForeignKey
from .header_filter import HeaderFilter
from .relation import Relation, RelationType

logger = logging.getLogger(__name__)
_get_ct = ContentType.objects.get_for_model
# TODO: add a 'historisable' tag instead ??
#       or ClassKeyedMap + ModificationDateTimeField excluded
_EXCLUDED_FIELDS = ('modified',)
# TODO: ClassKeyedMap ??
_SERIALISABLE_FIELDS = frozenset((
    'CharField',
    'TextField',

    'IntegerField', 'BigIntegerField', 'PositiveIntegerField',
    'PositiveSmallIntegerField', 'SmallIntegerField',

    'BooleanField', 'NullBooleanField',

    'DecimalField',
    'FloatField',

    'DateField',
    'DateTimeField',
    'TimeField',

    'ForeignKey',

    # What about ?
    #   BigIntegerField
    #   CommaSeparatedIntegerField
    #   GenericIPAddressField
    #   UUIDField
    #   BinaryField

    # Excluded:
    #   'FilePathField' => not useful
    #   'FileField' => not serializable
))

_TIME_FMT = '%H:%M:%S.%f'


# TODO: in creme_core.utils ??
class _JSONEncoder(JSONEncoder):
    def default(self, o):
        # TODO: remove when json standard lib handles Decimal
        if isinstance(o, Decimal):
            return str(o)

        if isinstance(o, datetime):
            return dt_to_ISO8601(o)

        if isinstance(o, date):
            return date_to_ISO8601(o)

        if isinstance(o, time):
            return o.strftime(_TIME_FMT)

        return JSONEncoder.default(self, o)


# DEPRECATED
Printer = Callable[[Field, Any, Any], str]


def _basic_printer(field: Field, val, user) -> str:
    warnings.warn(
        'creme_core.models.history._basic_printer() is deprecated ; '
        'use creme_core.gui.history instead.',
        DeprecationWarning
    )

    if field.choices:
        # NB: django way for '_get_FIELD_display()' methods => would a linear search be faster ?
        val = dict(field.flatchoices).get(val, val)

    if val is None:
        return ''

    return str(val)


def _fk_printer(field: Field, val, user) -> str:
    warnings.warn(
        'creme_core.models.history._fk_printer() is deprecated ; '
        'use creme_core.gui.history instead.',
        DeprecationWarning
    )

    if val is None:
        return ''

    model = field.remote_field.model

    try:
        out = model.objects.get(pk=val)
    except model.DoesNotExist as e:
        logger.info(str(e))
        out = val
    else:
        if isinstance(out, CremeEntity):
            out = out.allowed_str(user)

    return str(out)


def _boolean_printer(field: Field, val, user) -> str:
    warnings.warn(
        'creme_core.models.history._boolean_printer() is deprecated ; '
        'use creme_core.gui.history instead.',
        DeprecationWarning
    )

    return (
        gettext('Yes') if val else
        gettext('No') if val is False else
        gettext('N/A')
    )


def _date_printer(field: Field, val, user) -> str:
    warnings.warn(
        'creme_core.models.history._date_printer() is deprecated ; '
        'use creme_core.gui.history instead.',
        DeprecationWarning
    )

    return date_format(date_from_ISO8601(val), 'DATE_FORMAT') if val else ''


def _datetime_printer(field: Field, val, user) -> str:
    warnings.warn(
        'creme_core.models.history._datetime_printer() is deprecated ; '
        'use creme_core.gui.history instead.',
        DeprecationWarning
    )

    return date_format(localtime(dt_from_ISO8601(val)), 'DATETIME_FORMAT') if val else ''


def _float_printer(field: Field, val, user):
    warnings.warn(
        'creme_core.models.history._float_printer() is deprecated ; '
        'use creme_core.gui.history instead.',
        DeprecationWarning
    )

    return number_format(val, use_l10n=True) if val is not None else ''


# DEPRECATED
_PRINTERS: Dict[str, Printer] = {
    'BooleanField': _boolean_printer,
    'NullBooleanField': _boolean_printer,

    'ForeignKey': _fk_printer,

    'DateField': _date_printer,
    'DateTimeField': _datetime_printer,

    'FloatField': _float_printer,
}


class _HistoryLineTypeRegistry:
    __slots__ = ('_hltypes', )

    def __init__(self):
        self._hltypes: Dict[int, Type['_HistoryLineType']] = {}

    def __call__(self, type_id: int):
        assert type_id not in self._hltypes, 'ID collision'

        def _aux(cls):
            self._hltypes[type_id] = cls
            cls.type_id = type_id
            return cls

        return _aux

    def __getitem__(self, i: int) -> Type['_HistoryLineType']:
        return self._hltypes[i]

    def __iter__(self) -> Iterator[Type['_HistoryLineType']]:
        return iter(self._hltypes.values())


TYPES_MAP = _HistoryLineTypeRegistry()

TYPE_CREATION        = 1
TYPE_EDITION         = 2
TYPE_DELETION        = 3
TYPE_RELATED         = 4
TYPE_PROP_ADD        = 5
TYPE_RELATION        = 6
TYPE_SYM_RELATION    = 7
TYPE_RELATION_DEL    = 8
TYPE_SYM_REL_DEL     = 9
TYPE_AUX_CREATION    = 10
TYPE_AUX_EDITION     = 11
TYPE_AUX_DELETION    = 12
TYPE_PROP_DEL        = 13
TYPE_TRASH           = 14
TYPE_CUSTOM_EDITION  = 15
TYPE_EXPORT          = 20


class _HistoryLineType:
    type_id: int  # = None  # Overload with TYPE_*
    verbose_name = 'OVERRIDE ME'
    has_related_line: bool = False
    is_about_relation: bool = False

    @classmethod
    def _build_fields_modifs(cls, instance) -> List[tuple]:
        modifs = []
        backup = getattr(instance, '_instance_backup', None)

        if backup is not None:
            backup['_state'] = ModelState()
            old_instance = instance.__class__()
            old_instance.__dict__ = backup
            excluded_fields: Container = (
                _EXCLUDED_FIELDS if isinstance(instance, CremeEntity) else ()
            )

            for field in instance._meta.fields:
                fname = field.name

                # if fname in excluded_fields or not field.get_tag('viewable'):
                if fname in excluded_fields or not field.get_tag(FieldTag.VIEWABLE):
                    continue

                old_value = getattr(old_instance, fname)
                new_value = getattr(instance, fname)

                if isinstance(field, ForeignKey):
                    old_value = old_value and old_value.pk
                    new_value = new_value and new_value.pk
                else:
                    try:
                        # Sometimes a form sets a string representing an int in
                        # an IntegerField (for example)
                        #   => the type difference leads to a useless log like:
                        #      Set field “My field” from “X” to “X”
                        new_value = field.clean(new_value, instance)
                    except ValidationError as e:
                        logger.debug(
                            'Error in _HistoryLineType._build_fields_modifs() [%s]: %s',
                            __name__, e,
                        )
                        continue

                if old_value != new_value:
                    if not new_value and not old_value:
                        # Ignore useless changes like : None -> ""
                        continue

                    modif: tuple

                    if field.get_internal_type() not in _SERIALISABLE_FIELDS:
                        modif = (fname,)
                    elif old_value:
                        modif = (fname, old_value, new_value)
                    else:
                        modif = (fname, new_value)

                    modifs.append(modif)

        return modifs

    @staticmethod
    def _create_entity_backup(entity: Model) -> None:
        entity._instance_backup = backup = entity.__dict__.copy()
        del backup['_state']

    def _get_printer(self, field: Field) -> Printer:
        warnings.warn(
            '_HistoryLineType._get_printer() is deprecated ; '
            'use creme_core.gui.history instead.',
            DeprecationWarning
        )

        return _PRINTERS.get(field.get_internal_type(), _basic_printer)

    def _verbose_modifications_4_fields(self,
                                        model_class: Type[Model],
                                        modifications: List[tuple],
                                        user) -> Iterator[str]:
        warnings.warn(
            '_HistoryLineType._verbose_modifications_4_fields() is deprecated ; '
            'use creme_core.gui.history instead.',
            DeprecationWarning
        )

        get_field = model_class._meta.get_field

        for modif in modifications:
            field_name = modif[0]
            try:
                field: Field = get_field(field_name)
            except FieldDoesNotExist:
                vmodif = gettext('Set field “{field}”').format(field=field_name)
            else:
                field_vname = field.verbose_name

                if isinstance(field, models.ManyToManyField):
                    removed_pks = modif[1]
                    added_pks = modif[2]

                    linked_instances = (
                        field.remote_field.model._default_manager.in_bulk(removed_pks + added_pks)
                    )
                    pk_details = []

                    def append_details(pks, format_str):
                        if pks:
                            # TODO: allowed_str() if entity...
                            pk_details.append(format_str.format(
                                ', '.join(str(linked_instances.get(pk, '?')) for pk in pks)
                            ))

                    append_details(removed_pks, '[{}] removed')
                    append_details(added_pks, '[{}] added')

                    vmodif = 'Field “{field}” changed: {details}.'.format(
                        field=field_vname,
                        details=', '.join(pk_details),
                    )
                else:
                    length = len(modif)

                    if length == 1:
                        vmodif = gettext('Set field “{field}”').format(field=field_vname)
                    elif length == 2:
                        vmodif = gettext('Set field “{field}” to “{value}”').format(
                            field=field_vname,
                            value=self._get_printer(field)(field, modif[1], user),
                        )
                    else:  # length == 3
                        printer = self._get_printer(field)
                        vmodif = gettext(
                            'Set field “{field}” from “{oldvalue}” to “{value}”'
                        ).format(
                            field=field_vname,
                            oldvalue=printer(field, modif[1], user),
                            value=printer(field, modif[2], user),
                        )

            yield vmodif

    def verbose_modifications(self,
                              modifications: List[tuple],
                              entity_ctype: ContentType,
                              user) -> Iterator[str]:
        warnings.warn(
            '_HistoryLineType.verbose_modifications() is deprecated ; '
            'use creme_core.gui.history instead.',
            DeprecationWarning
        )

        for m in self._verbose_modifications_4_fields(
            entity_ctype.model_class(), modifications, user,
        ):
            yield m


class _HLTCacheMixin:
    @classmethod
    def _get_cache_key(cls, instance):
        raise NotImplementedError

    @classmethod
    def _get_cached_line(cls, instance):
        raise NotImplementedError

    @classmethod
    def _set_cached_line(cls, instance, hline):
        raise NotImplementedError


class _HLTInstanceCacheMixin(_HLTCacheMixin):
    @classmethod
    def _get_cached_line(cls, instance):
        return getattr(instance, cls._get_cache_key(instance), None)

    @classmethod
    def _set_cached_line(cls, instance, hline):
        setattr(instance, cls._get_cache_key(instance), hline)


class _HLTRequestCacheMixin(_HLTCacheMixin):
    @classmethod
    def _get_cached_line(cls, instance):
        cache = get_per_request_cache()
        cache_key = cls._get_cache_key(instance)
        return cache.get(cache_key)

    @classmethod
    def _set_cached_line(cls, instance, hline):
        get_per_request_cache()[cls._get_cache_key(instance)] = hline


class _HLTManyToManyMixin:
    @staticmethod
    def _initial_m2m_modification(field_id, removed_pk_set, added_pk_set):
        yield field_id, sorted(removed_pk_set), sorted(added_pk_set)

    @staticmethod
    def _updated_m2m_modifications(existing_modifications,
                                   field_id,
                                   removed_pk_set, added_pk_set):
        accumulated_added = {*added_pk_set}
        accumulated_removed = {*removed_pk_set}

        for info in existing_modifications:
            if info[0] != field_id:
                yield info
            else:
                accumulated_removed.update(info[1])
                accumulated_added.update(info[2])

        yield (
            field_id,
            sorted(accumulated_removed - accumulated_added),
            sorted(accumulated_added - accumulated_removed),
        )


@TYPES_MAP(TYPE_CREATION)
class _HLTEntityCreation(_HistoryLineType):
    verbose_name = _('Creation')

    @classmethod
    def create_line(cls, entity: CremeEntity) -> None:
        HistoryLine._create_line_4_instance(entity, cls.type_id, date=entity.created)
        # We do not backup here (and the handler _prepare_log() only creates if
        # PK exists), in order to keep a kind of 'creation session'.
        # So when you create a CremeEntity, while you still use the same python
        # object, multiple save() will not generate several HistoryLine objects.


@TYPES_MAP(TYPE_EDITION)
class _HLTEntityEdition(_HLTManyToManyMixin,
                        _HLTInstanceCacheMixin,
                        _HistoryLineType):
    verbose_name = _('Edition')

    @classmethod
    def _get_cache_key(cls, instance):
        return '_historyline_edition'

    @classmethod
    def create_lines(cls, entity: CremeEntity) -> None:
        modifs = _HistoryLineType._build_fields_modifs(entity)

        if modifs:
            hline = cls._get_cached_line(entity)

            if hline is None:
                hline = HistoryLine._create_line_4_instance(
                    entity, cls.type_id, date=entity.modified, modifs=modifs,
                )
                _HLTRelatedEntity.create_lines(entity, hline)
                cls._create_entity_backup(entity)
                cls._set_cached_line(entity, hline)
            else:
                # NB: to build attribute "_modifications"  TODO: improve HistoryLine API...
                hline._read_attrs()

                # NB: we could merge modifications of the same field, but one
                #     should avoiding multiple save() (& so HistoryLine can help
                #     detecting these cases).
                modifications = [*hline._modifications, *modifs]

                # hline._modifications = modifications  # TODO
                hline.value = hline._encode_attrs(entity, modifs=modifications)
                hline.save()

    @classmethod
    def create_lines_for_m2m(cls,
                             entity: CremeEntity,
                             m2m_name: str,
                             removed_pk_set: Iterable = (),
                             added_pk_set: Iterable = (),
                             ) -> None:
        hline = cls._get_cached_line(entity)

        if hline is None:
            hline = HistoryLine._create_line_4_instance(
                entity, cls.type_id,
                modifs=[*cls._initial_m2m_modification(m2m_name, removed_pk_set, added_pk_set)],
            )
            cls._set_cached_line(entity, hline)

            _HLTRelatedEntity.create_lines(entity, hline)
        else:
            # NB: to build attribute "_modifications"  TODO: improve HistoryLine API...
            hline._read_attrs()

            modifications = [
                *cls._updated_m2m_modifications(
                    existing_modifications=hline._modifications,
                    field_id=m2m_name,
                    removed_pk_set=removed_pk_set, added_pk_set=added_pk_set,
                ),
            ]

            # hline._modifications = modifications  # TODO
            hline.value = hline._encode_attrs(entity, modifs=modifications)
            hline.save()


@TYPES_MAP(TYPE_CUSTOM_EDITION)
class _HLTCustomFieldsEdition(_HLTManyToManyMixin,
                              _HLTRequestCacheMixin,
                              _HistoryLineType):
    verbose_name = _('Edition (custom fields)')

    backup_attname = '_history_value_backup'

    @classmethod
    def _create_cvalue_backup(cls, custom_value: CustomFieldValue):
        if not isinstance(custom_value, CustomFieldMultiEnum):
            storable_value = (
                custom_value.value_id
                if isinstance(custom_value, CustomFieldEnum) else
                custom_value.value
            )
            setattr(custom_value, cls.backup_attname, storable_value)

    @classmethod
    def _get_cache_key(cls, instance):
        return f'creme_core-history_lines-custom-{instance.id}'

    @classmethod
    def create_lines(cls, custom_value: CustomFieldValue, emptied=False) -> None:
        if isinstance(custom_value, CustomFieldMultiEnum):
            return

        entity = custom_value.entity

        old_value = getattr(custom_value, cls.backup_attname, None)
        new_value = (
            None if emptied else (
                custom_value.value_id
                if isinstance(custom_value, CustomFieldEnum) else
                custom_value.value
            )
        )
        new_modif = (
            (custom_value.custom_field_id, new_value)
            if custom_value.is_empty_value(old_value) else
            (custom_value.custom_field_id, old_value, new_value)
        )
        hline = cls._get_cached_line(entity)

        if hline is None:
            hline = HistoryLine._create_line_4_instance(
                entity, cls.type_id, modifs=[new_modif],
            )
            cls._set_cached_line(entity, hline)
            _HLTRelatedEntity.create_lines(entity, hline)
        else:
            # NB: to build attribute "_modifications"  TODO: improve HistoryLine API...
            hline._read_attrs()

            # NB: we could merge modifications of the same custom field, but one
            #     should avoiding multiple save() (& so HistoryLine can help
            #     detecting these cases).
            modifications = [*hline._modifications, new_modif]

            # hline._modifications = modifications TODO
            hline.value = hline._encode_attrs(entity, modifs=modifications)
            hline.save()

    # TODO: factorise
    @classmethod
    def create_lines_for_multienum(cls,
                                   custom_value,
                                   removed_pk_set: Iterable = (),
                                   added_pk_set: Iterable = (),
                                   **kwargs
                                   ) -> None:
        entity = custom_value.entity
        cfield_id = custom_value.custom_field_id
        hline = cls._get_cached_line(entity)

        if hline is None:
            hline = HistoryLine._create_line_4_instance(
                entity, cls.type_id,
                modifs=[*cls._initial_m2m_modification(cfield_id, removed_pk_set, added_pk_set)],
            )
            cls._set_cached_line(entity, hline)
            _HLTRelatedEntity.create_lines(entity, hline)
        else:
            # NB: to build attribute "_modifications"  TODO: improve HistoryLine API...
            hline._read_attrs()

            modifications = [
                *cls._updated_m2m_modifications(
                    existing_modifications=hline._modifications,
                    field_id=cfield_id,
                    removed_pk_set=removed_pk_set, added_pk_set=added_pk_set,
                ),
            ]

            # hline._modifications = modifications  # TODO
            hline.value = hline._encode_attrs(entity, modifs=modifications)
            hline.save()

    def verbose_modifications(self,
                              modifications: List[tuple],
                              entity_ctype: ContentType,
                              user) -> Iterator[str]:
        warnings.warn(
            '_HLTCustomFieldsEdition.verbose_modifications() is deprecated ; '
            'use creme_core.gui.history instead.',
            DeprecationWarning
        )

        get_cfield = CustomField.objects.get

        for modif in modifications:
            field_id = modif[0]
            try:
                cfield: CustomField = get_cfield(id=field_id)
            except CustomField.DoesNotExist:  # TODO: test
                vmodif = 'Set field id={field} (seems removed)'.format(field=field_id)
            else:
                if cfield.field_type == CustomField.MULTI_ENUM:
                    # NB: we should retrieve the labels of choices instead of PK,
                    #     but HistoryLineExplainer is the good way now;
                    #     this method exists only for compatibility.
                    pk_details = []

                    def append_details(pks, format_str):
                        if pks:
                            pk_details.append(format_str.format(
                                ', '.join(str(pk) for pk in pks)
                            ))

                    append_details(modif[1], '[{}] removed')
                    append_details(modif[2], '[{}] added')

                    vmodif = 'Field “{field}” changed: {details}.'.format(
                        field=cfield.name,
                        details=', '.join(pk_details),
                    )
                else:
                    # NB: same remark than above but with _PRINTERS.
                    length = len(modif)

                    if length == 1:
                        vmodif = gettext('Set field “{field}”').format(field=cfield.name)
                    elif length == 2:
                        vmodif = gettext('Set field “{field}” to “{value}”').format(
                            field=cfield.name, value=modif[1],
                        )
                    else:  # length == 3
                        pass
                        vmodif = gettext(
                            'Set field “{field}” from “{oldvalue}” to “{value}”'
                        ).format(field=cfield.name, oldvalue=modif[1], value=modif[2])

            yield vmodif


@TYPES_MAP(TYPE_DELETION)
class _HLTEntityDeletion(_HistoryLineType):
    verbose_name = _('Deletion')

    @classmethod
    def create_line(cls, entity: CremeEntity) -> None:
        HistoryLine.objects.create(
            entity_ctype=entity.entity_type,
            entity_owner=entity.user,
            type=cls.type_id,
            value=HistoryLine._encode_attrs(entity),
        )


@TYPES_MAP(TYPE_TRASH)
class _HLTEntityTrash(_HistoryLineType):
    verbose_name = _('Trash')

    @classmethod
    def create_line(cls, entity: CremeEntity) -> None:
        backup = getattr(entity, '_instance_backup', None)

        if backup and backup['is_deleted'] != entity.is_deleted:
            HistoryLine.objects.create(
                entity=entity,
                entity_ctype=entity.entity_type,
                entity_owner=entity.user,
                type=cls.type_id,
                value=HistoryLine._encode_attrs(
                    entity, modifs=[entity.is_deleted],
                ),
            )

    def verbose_modifications(self, modifications, entity_ctype, user):
        warnings.warn(
            '_HLTEntityTrash.verbose_modifications() is deprecated ; '
            'use creme_core.gui.history instead.',
            DeprecationWarning
        )

        if modifications[0]:
            yield gettext('Sent to the trash')
        else:
            yield gettext('Restored')


@TYPES_MAP(TYPE_RELATED)
class _HLTRelatedEntity(_HistoryLineType):
    verbose_name = _('Related modification')
    has_related_line = True

    @classmethod
    def create_lines(cls, entity: CremeEntity, related_line: 'HistoryLine'):
        # rtypes_ids = HistoryConfigItem.objects.values_list('relation_type', flat=True)
        relations = Relation.objects.filter(
            subject_entity=entity.id,
            # type__in=rtypes_ids,
            type__in=HistoryConfigItem.objects.configured_relation_type_ids(),
        ).select_related('object_entity')

        if relations:
            object_entities = [r.object_entity for r in relations]
            create_line = partial(
                HistoryLine._create_line_4_instance,
                ltype=cls.type_id, date=entity.modified, related_line_id=related_line.id,
            )

            CremeEntity.populate_real_entities(object_entities)  # Optimisation

            for related_entity in object_entities:
                create_line(related_entity.get_real_entity())


@TYPES_MAP(TYPE_PROP_ADD)
class _HLTPropertyCreation(_HistoryLineType):
    verbose_name = _('Property creation')
    _fmt = _('Add property “{}”')

    @classmethod
    def create_line(cls, prop: CremeProperty):
        HistoryLine._create_line_4_instance(
            prop.creme_entity, cls.type_id, modifs=[prop.type_id],
        )

    def verbose_modifications(self, modifications, entity_ctype, user):
        warnings.warn(
            '_HLTPropertyCreation.verbose_modifications() is deprecated ; '
            'use creme_core.gui.history instead.',
            DeprecationWarning
        )

        ptype_id = modifications[0]

        try:
            ptype_text = CremePropertyType.objects.get(pk=ptype_id).text
        except CremePropertyType.DoesNotExist:
            ptype_text = ptype_id

        yield self._fmt.format(ptype_text)


@TYPES_MAP(TYPE_PROP_DEL)
class _HLTPropertyDeletion(_HLTPropertyCreation):
    verbose_name = _('Property deletion')
    _fmt = _('Delete property “{}”')

    @classmethod
    def create_line(cls, prop: CremeProperty) -> None:
        HistoryLine._create_line_4_instance(
            prop.creme_entity, cls.type_id, modifs=[prop.type_id],
        )


@TYPES_MAP(TYPE_RELATION)
class _HLTRelation(_HistoryLineType):
    verbose_name = _('Relationship')
    has_related_line = True
    is_about_relation = True
    _fmt = _('Add a relationship “{}”')

    @classmethod
    def _create_lines(cls,
                      relation: Relation,
                      sym_cls: Type[_HistoryLineType],
                      date=None) -> None:
        create_line = partial(HistoryLine._create_line_4_instance, date=date)
        hline     = create_line(relation.subject_entity, cls.type_id)
        hline_sym = create_line(
            relation.object_entity, sym_cls.type_id,
            modifs=[relation.type.symmetric_type_id],
            related_line_id=hline.id,
        )
        hline.value = HistoryLine._encode_attrs(
            hline.entity,
            modifs=[relation.type_id], related_line_id=hline_sym.id,
        )
        hline.save()

    @classmethod
    def create_lines(cls, relation: Relation, created: bool):
        if not created:
            cls._create_lines(
                relation if '-subject_' in relation.type_id else relation.symmetric_relation,
                _HLTSymRelation, relation.created,
            )

    def verbose_modifications(self, modifications, entity_ctype, user):
        warnings.warn(
            '_HLTRelation.verbose_modifications() is deprecated ; '
            'use creme_core.gui.history instead.',
            DeprecationWarning
        )

        rtype_id = modifications[0]

        try:
            predicate = RelationType.objects.get(pk=rtype_id).predicate
        except RelationType.DoesNotExist:
            predicate = rtype_id

        yield self._fmt.format(predicate)


@TYPES_MAP(TYPE_SYM_RELATION)
class _HLTSymRelation(_HLTRelation):
    pass


@TYPES_MAP(TYPE_RELATION_DEL)
class _HLTRelationDeletion(_HLTRelation):
    verbose_name = _('Relationship deletion')
    _fmt = _('Delete a relationship “{}”')

    @classmethod
    def create_lines(cls, relation: Relation, *args, **kwargs):
        if '-subject_' in relation.type_id:
            cls._create_lines(relation, _HLTSymRelationDeletion)


@TYPES_MAP(TYPE_SYM_REL_DEL)
class _HLTSymRelationDeletion(_HLTRelationDeletion):
    pass


@TYPES_MAP(TYPE_AUX_CREATION)
class _HLTAuxCreation(_HistoryLineType):
    verbose_name = _('Auxiliary (creation)')

    @staticmethod
    def _model_info(ct_id):
        model_class = ContentType.objects.get_for_id(ct_id).model_class()
        return model_class, model_class._meta.verbose_name

    @staticmethod
    def _build_modifs(related):
        return [_get_ct(related).id, related.pk, str(related)]

    @classmethod
    def create_line(cls, related: Model) -> None:
        HistoryLine._create_line_4_instance(
            related.get_related_entity(), cls.type_id,
            modifs=cls._build_modifs(related),
        )

    def verbose_modifications(self, modifications, entity_ctype, user):
        warnings.warn(
            '_HLTAuxCreation.verbose_modifications() is deprecated ; '
            'use creme_core.gui.history instead.',
            DeprecationWarning
        )

        ct_id, aux_id, str_obj = modifications

        yield gettext('Add <{type}>: “{value}”').format(
            type=self._model_info(ct_id)[1], value=str_obj,
        )


@TYPES_MAP(TYPE_AUX_EDITION)
class _HLTAuxEdition(_HLTManyToManyMixin,
                     _HLTInstanceCacheMixin,
                     _HLTAuxCreation):
    verbose_name = _('Auxiliary (edition)')

    @classmethod
    def _get_cache_key(cls, instance):
        return '_historyline_aux_edition'

    @classmethod
    def create_line(cls, related: Model) -> None:
        # TODO: factorise better ?
        fields_modifs = cls._build_fields_modifs(related)

        if fields_modifs:
            hline = cls._get_cached_line(related)

            if hline is None:
                hline = HistoryLine._create_line_4_instance(
                    related.get_related_entity(),
                    cls.type_id,
                    modifs=[cls._build_modifs(related), *fields_modifs],
                )
                cls._create_entity_backup(related)
                cls._set_cached_line(related, hline)
            else:
                # NB: to build attribute "_modifications"  TODO: improve HistoryLine API...
                hline._read_attrs()

                # NB: we could merge modification of the same field, but one
                #     should avoiding multiple save() (& so HistoryLine can help
                #     detecting these cases).
                modifications = [*hline._modifications, *fields_modifs]

                # hline._modifications = modifications  # TODO
                hline.value = hline._encode_attrs(
                    cls._build_modifs(related), modifs=modifications,
                )
                hline.save()
        elif getattr(related, '_hline_reassigned', False):
            _HLTAuxCreation.create_line(related)

    @classmethod
    def create_line_for_m2m(cls,
                            related: Model,
                            m2m_name: str,
                            removed_pk_set: Iterable = (),
                            added_pk_set: Iterable = (),
                            ) -> None:
        hline = cls._get_cached_line(related)
        entity = related.get_related_entity()

        if hline is None:
            hline = HistoryLine._create_line_4_instance(
                entity, cls.type_id,
                modifs=[
                    cls._build_modifs(related),
                    *cls._initial_m2m_modification(m2m_name, removed_pk_set, added_pk_set),
                ],
            )
            cls._set_cached_line(related, hline)
        else:
            # NB: to build attribute "_modifications"  TODO: improve HistoryLine API...
            hline._read_attrs()

            existing = hline._modifications
            modifications = [
                existing[0],
                *cls._updated_m2m_modifications(
                    existing_modifications=existing[1:],
                    field_id=m2m_name,
                    removed_pk_set=removed_pk_set, added_pk_set=added_pk_set,
                ),
            ]

            # hline._modifications = modifications  # TODO
            hline.value = hline._encode_attrs(entity, modifs=modifications)
            hline.save()

    def verbose_modifications(self, modifications, entity_ctype, user):
        warnings.warn(
            '_HLTAuxEdition.verbose_modifications() is deprecated ; '
            'use creme_core.gui.history instead.',
            DeprecationWarning
        )

        ct_id, aux_id, str_obj = modifications[0]
        model_class, verbose_name = self._model_info(ct_id)

        yield gettext('Edit <{type}>: “{value}”').format(
            type=verbose_name, value=str_obj,
        )

        for m in self._verbose_modifications_4_fields(model_class, modifications[1:], user):
            yield m


@TYPES_MAP(TYPE_AUX_DELETION)
class _HLTAuxDeletion(_HLTAuxCreation):
    verbose_name = _('Auxiliary (deletion)')

    @staticmethod
    def _build_modifs(related):
        return [_get_ct(related).id, str(related)]

    def verbose_modifications(self, modifications, entity_ctype, user):
        warnings.warn(
            '_HLTAuxDeletion.verbose_modifications() is deprecated ; '
            'use creme_core.gui.history instead.',
            DeprecationWarning
        )

        ct_id, str_obj = modifications

        yield gettext('Delete <{type}>: “{value}”').format(
            type=self._model_info(ct_id)[1], value=str_obj,
        )


@TYPES_MAP(TYPE_EXPORT)
class _HLTEntityExport(_HistoryLineType):
    verbose_name = _('Mass export')

    @classmethod
    def create_line(cls,
                    ctype: ContentType,
                    user,
                    count: int,
                    hfilter: HeaderFilter,
                    efilter: Optional[EntityFilter] = None) -> 'HistoryLine':
        """Builder of HistoryLine representing a CSV/XLS/... massive export.

        @param ctype: ContentType instance ; type of exported entities.
        @param user: User who does the export.
        @param hfilter: HeaderFilter instance used.
        @param efilter: EntityFilter instance used (or None).
        @return: Created instance of line.
        """
        modifs = [count, hfilter.name]
        if efilter:
            modifs.append(efilter.name)

        return HistoryLine.objects.create(
            entity_ctype=ctype,
            entity_owner=user,
            type=cls.type_id,
            value=HistoryLine._encode_attrs(instance='', modifs=modifs),
        )

    def verbose_modifications(self, modifications, entity_ctype, user):
        warnings.warn(
            '_HLTEntityExport.verbose_modifications() is deprecated ; '
            'use creme_core.gui.history instead.',
            DeprecationWarning
        )

        count = modifications[0]

        yield gettext(
            'Export of {count} «{model}» (view «{view}» & filter «{filter}»)'
        ).format(
            count=count,
            model=get_model_verbose_name(entity_ctype.model_class(), count),
            view=modifications[1],
            filter=(
                modifications[2]
                if len(modifications) >= 3 else
                pgettext('creme_core-filter', 'All')),
        )


class HistoryLine(Model):
    entity = models.ForeignKey(CremeEntity, null=True, on_delete=models.SET_NULL)

    # We do not use entity.entity_type because we keep history of the deleted entities.
    entity_ctype = CTypeForeignKey()

    # We do not use entity.user because we keep history of the deleted entities
    entity_owner = CremeUserForeignKey()

    # Not a FK to a User object because we want to keep the same line after the
    # deletion of a User.
    username = models.CharField(max_length=30)

    date = CreationDateTimeField(_('Date'))

    type  = models.PositiveSmallIntegerField(_('Type'))  # See TYPE_*
    value = models.TextField(null=True)  # TODO: use a JSONField ? (see EntityFilter)

    ENABLED: bool = True  # False means that no new HistoryLines are created.

    _line_type: Optional[_HistoryLineType] = None
    _entity_repr: Optional[str] = None
    _modifications: Optional[list] = None
    _related_line_id: Optional[int] = None
    _related_line: Union['HistoryLine', bool, None] = False

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('Line of history')
        verbose_name_plural = _('Lines of history')

    def __repr__(self):
        return (
            f'HistoryLine('
            f'entity_id={self.entity_id}, '
            f'entity_owner_id={self.entity_owner_id}, '
            f'username={self.username}, '
            f'date={self.date}, '
            f'type={self.type}, '
            f'value={self.value}'
            f')'
        )

    def __str__(self):
        return repr(self)

    @staticmethod
    @atomic
    def delete_lines(line_qs) -> None:
        """Delete the given HistoryLines & the lines related to them.
        @param line_qs: QuerySet on HistoryLine.
        """
        from ..core.paginator import FlowPaginator

        deleted_ids = set()
        paginator = FlowPaginator(
            queryset=line_qs.order_by('id'), key='id', per_page=1024,
        )

        for hlines_page in paginator.pages():
            for hline in hlines_page.object_list:
                deleted_ids.add(hline.id)
                hline.delete()

        related_types = [
            type_cls.type_id for type_cls in TYPES_MAP if type_cls.has_related_line
        ]

        while True:
            progress = False
            qs = HistoryLine.objects.filter(type__in=related_types)
            paginator = FlowPaginator(
                queryset=qs.order_by('id'), key='id', per_page=1024,
            )

            for hlines_page in paginator.pages():
                for hline in hlines_page.object_list:
                    related_line_id = hline._get_related_line_id()

                    if related_line_id is not None and related_line_id in deleted_ids:
                        deleted_ids.add(hline.id)
                        hline.delete()
                        progress = True

            if not progress:
                break

    @staticmethod
    def disable(instance) -> None:
        """Disable history for this instance.
        @type instance: Can be an instance of CremeEntity, Relation,
              CremeProperty, an auxiliary model.
        """
        instance._hline_disabled = True

    @staticmethod
    def mark_as_reassigned(instance, old_reference, new_reference, field_name: str):
        """ Indicate to the history system that an instance has been modified
        by replacing a FK value.

        It is useful when merging 2 entities with auxiliary instances, in order
        to detect a change in these auxiliary instances (because if these FK are
        internal & so not considered as 'information' fields the modifications
        will not caused a TYPE_AUX_EDITION line to be created) ; so HistoryLines
        corresponding to the move of the auxiliary instances from the deleted
        entity to the remaining one will be created.

        @param instance: modified instance.
        @param old_reference: object which was referenced by the FK.
        @param new_reference: object which is referenced by the FK now.
        @param field_name: name of the FK field.
        """
        instance._hline_reassigned = (old_reference, new_reference, field_name)

    @classmethod
    def _encode_attrs(cls, instance, modifs=(), related_line_id: Optional[int] = None) -> str:
        value: list = [str(instance)]
        if related_line_id:
            value.append(related_line_id)

        encode = _JSONEncoder().encode

        try:
            attrs = encode(value + [*modifs])
        except TypeError as e:
            logger.warning('HistoryLine._encode_attrs(): %s', e)
            attrs = encode(value)

        return attrs

    def _read_attrs(self) -> None:
        value = json_load(self.value)
        self._entity_repr = value.pop(0)
        self._related_line_id = value.pop(0) if self.line_type.has_related_line else 0
        self._modifications = value

    @property
    def entity_repr(self):
        if self._entity_repr is None:
            self._read_attrs()

        return self._entity_repr

    def get_type_str(self):
        return self.line_type.verbose_name

    @property
    def line_type(self) -> _HistoryLineType:
        _line_type = self._line_type

        if _line_type is None:
            self._line_type = _line_type = TYPES_MAP[self.type]()

        return _line_type

    @property
    def modifications(self):
        if self._modifications is None:
            self._read_attrs()

        return self._modifications

    def get_verbose_modifications(self, user) -> List[str]:
        warnings.warn(
            'creme_core.models.HistoryLine.get_verbose_modifications() is deprecated ; '
            'use creme_core.gui.history instead.',
            DeprecationWarning
        )

        try:
            return [
                *self.line_type.verbose_modifications(
                    self.modifications, self.entity_ctype, user,
                ),
            ]
        except Exception:
            logger.exception('Error in %s', self.__class__.__name__)
            return ['??']

    def _get_related_line_id(self) -> Optional[int]:
        if self._related_line_id is None:
            self._read_attrs()

        return self._related_line_id

    @staticmethod
    def populate_users(hlines: Sequence['HistoryLine'], user):
        """Set the internal cache for 'user' in some HistoryLines, to optimize queries.

        @param hlines: Sequence of HistoryLine instances (need to be iterated twice)
        @param user: current user (instance of get_user_model()) ;
              no query is need to retrieve it again.
        """
        # We retrieve the User instances corresponding to the line usernames,
        # in order to have a verbose display.
        # We avoid a useless query to User if the only used User is the
        # current User (which is already retrieved).
        usernames = {hline.username for hline in hlines}
        usernames.discard(user.username)

        users = {user.username: user}

        if usernames:
            users.update(
                (u.username, u)
                for u in get_user_model().objects.filter(username__in=usernames)
            )

        for hline in hlines:
            hline.user = users.get(hline.username)

    @classmethod
    def populate_related_lines(cls, hlines: Sequence['HistoryLine']):
        pool = {hline.id: hline for hline in hlines}
        unpopulated = [hline for hline in hlines if hline._related_line is False]

        missing_line_ids = []
        for hline in unpopulated:
            related_id = hline._get_related_line_id()
            if related_id and related_id not in pool:
                missing_line_ids.append(related_id)

        # NB: in_bulk() avoid query if missing_line_ids is empty
        pool.update(cls._default_manager.in_bulk(missing_line_ids))

        for hline in unpopulated:
            hline._related_line = pool.get(hline._get_related_line_id())

    @property
    def related_line(self) -> Optional['HistoryLine']:
        if self._related_line is False:
            self._related_line = None
            line_id = self._get_related_line_id()

            if line_id:
                try:
                    self._related_line = HistoryLine.objects.get(pk=line_id)
                except HistoryLine.DoesNotExist:
                    pass

        return self._related_line

    @classmethod
    def _create_line_4_instance(
            cls,
            instance,
            ltype: int,
            date=None,
            modifs=(),
            related_line_id=None):
        """Builder.
        @param ltype: See TYPE_*
        @param date: If not given, will be 'now'.
        @param modifs: List of tuples containing JSONifiable values.
        @param related_line_id: HistoryLine.id.
        """
        kwargs = {
            'entity': instance,
            'entity_ctype': instance.entity_type,
            'entity_owner': instance.user,
            'type': ltype,
            'value': cls._encode_attrs(
                instance,
                modifs=modifs,
                related_line_id=related_line_id,
            ),
        }

        if date:
            kwargs['date'] = date

        return cls.objects.create(**kwargs)

    def save(self, *args, **kwargs):
        if self.ENABLED:
            # if self.pk is None: TODO ?
            user = get_global_info('user')
            self.username = user.username if user else ''

            super().save(*args, **kwargs)

    @property
    def user(self):
        try:
            user = getattr(self, '_user_cache')
        except AttributeError:
            username = self.username
            self._user_cache = user = get_user_model().objects.filter(
                username=username,
            ).first() if username else None

        return user

    @user.setter
    def user(self, user):
        self._user_cache = user
        self.username = user.username if user else ''


# TODO: method of CremeEntity ??
def _final_entity(entity) -> bool:
    "Is the instance an instance of a 'leaf' class."
    return entity.entity_type_id == _get_ct(entity).id


@receiver(signals.post_init)
def _prepare_log(sender, instance, **kwargs):
    if hasattr(instance, 'get_related_entity'):
        _HistoryLineType._create_entity_backup(instance)
    elif isinstance(instance, CremeEntity) and instance.id and _final_entity(instance):
        _HistoryLineType._create_entity_backup(instance)
    elif isinstance(instance, CustomFieldValue):
        _HLTCustomFieldsEdition._create_cvalue_backup(instance)
    # XXX: following billing lines problem should not exist anymore
    #      (several inheritance levels are avoided).
    # TODO: replace with this code
    #      problem with billing lines : the update view does not retrieve
    #      final class, so 'instance.entity_type_id == _get_ct(instance).id'
    #      test avoid the creation of a line
    #      --> find a better way to test if a final object is alive ?
    # if isinstance(instance, CremeEntity):
    #     if not instance.id or instance.entity_type_id != _get_ct(instance).id:
    #         return
    # elif not hasattr(instance, 'get_related_entity'):
    #     return
    #
    # _HistoryLineType._create_entity_backup(instance)


@receiver(signals.post_save)
def _log_creation_edition(sender, instance, created, **kwargs):
    if getattr(instance, '_hline_disabled', False):  # see HistoryLine.disable
        return

    try:
        if isinstance(instance, CremeProperty):
            _HLTPropertyCreation.create_line(instance)
        elif isinstance(instance, Relation):
            _HLTRelation.create_lines(instance, created)
        elif hasattr(instance, 'get_related_entity'):
            if created:
                _HLTAuxCreation.create_line(instance)
            else:
                _HLTAuxEdition.create_line(instance)
        elif isinstance(instance, CremeEntity):
            if created:
                _HLTEntityCreation.create_line(instance)
            else:
                _HLTEntityEdition.create_lines(instance)
                _HLTEntityTrash.create_line(instance)
        elif isinstance(instance, CustomFieldValue):
            _HLTCustomFieldsEdition.create_lines(instance)
    except Exception:
        logger.exception(
            'Error in _log_creation_edition() ; HistoryLine may not be created.'
        )


@receiver(signals.m2m_changed)
def _log_m2m_edition(sender, instance, action, pk_set, **kwargs):
    if getattr(instance, '_hline_disabled', False):  # see HistoryLine.disable
        return

    if hasattr(instance, 'get_related_entity'):
        create = partial(_HLTAuxEdition.create_line_for_m2m, related=instance)
    elif isinstance(instance, CremeEntity):
        create = partial(_HLTEntityEdition.create_lines_for_m2m, entity=instance)
    elif isinstance(instance, CustomFieldMultiEnum):
        create = partial(
            _HLTCustomFieldsEdition.create_lines_for_multienum,
            custom_value=instance,
        )
    else:
        return

    for field in type(instance)._meta.many_to_many:
        if sender is field.remote_field.through:
            m2m_field = field
            break
    else:
        logger.warning('_log_m2m_edition: ManyToManyField not found: %s', sender)
        return

    kwargs = {}

    if action == 'post_add':
        kwargs['added_pk_set'] = pk_set
    elif action == 'post_remove':
        kwargs['removed_pk_set'] = pk_set
    elif action == 'pre_clear':
        # NB: this case is not very optimized (extra query),
        #     but it should not be a problem in real life.
        kwargs['removed_pk_set'] = {
            *getattr(instance, m2m_field.name).values_list('pk', flat=True),
        }
    else:
        return

    create(m2m_name=m2m_field.name, **kwargs)


def _get_deleted_entity_ids() -> set:
    del_ids = get_global_info('deleted_entity_ids')

    if del_ids is None:
        del_ids = set()
        set_global_info(deleted_entity_ids=del_ids)

    return del_ids


@receiver(signals.pre_delete)
def _log_deletion(sender, instance, **kwargs):
    if getattr(instance, '_hline_disabled', False):  # See HistoryLine.disable
        return

    # When we are dealing with CremeEntities, we check that we are dealing
    # with the final class, because the signal is send several times, with
    # several 'level' of class. We don't want to create several HistoryLines
    # (and some things are deleted by higher levels that make objects
    # inconsistent & that can cause 'crashes').
    try:
        if isinstance(instance, CremeProperty):
            _HLTPropertyDeletion.create_line(instance)
        elif isinstance(instance, Relation):
            _HLTRelationDeletion.create_lines(instance)
        elif hasattr(instance, 'get_related_entity'):
            if not isinstance(instance, CremeEntity) or _final_entity(instance):
                entity = instance.get_related_entity()

                if entity is None:
                    logger.debug(
                        '_log_deletion(): an auxiliary entity seems orphan (id=%s)'
                        ' -> can not create HistoryLine',
                        instance.id,
                    )
                elif entity.id not in _get_deleted_entity_ids():
                    _HLTAuxDeletion.create_line(instance)
        elif isinstance(instance, CremeEntity) and _final_entity(instance):
            _get_deleted_entity_ids().add(instance.id)
            _HLTEntityDeletion.create_line(instance)
        elif isinstance(instance, CustomFieldValue):
            _HLTCustomFieldsEdition.create_lines(instance, emptied=True)
    except Exception:
        logger.exception('Error in _log_deletion() ; HistoryLine may not be created.')


class HistoryConfigItemManager(models.Manager):
    @cached_per_request('creme_core-history_rtypes')
    def configured_relation_type_ids(self):
        return [*self.values_list('relation_type', flat=True)]


class HistoryConfigItem(Model):
    relation_type = models.OneToOneField(RelationType, on_delete=models.CASCADE)

    objects = HistoryConfigItemManager()

    class Meta:
        app_label = 'creme_core'


@receiver(pre_merge_related)
def _handle_merge(sender, other_entity, **kwargs):
    # We do not want these lines to be re-assigned to the remaining entity.
    # TODO: should we clone/copy for TYPE_RELATED
    HistoryLine.objects.filter(entity=other_entity.id).update(entity=None)
