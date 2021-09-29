# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2021  Hybird
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
from collections import OrderedDict
from typing import Callable, Dict, Iterator, List, Set, Tuple, Type

from django.contrib.contenttypes.models import ContentType
from django.db.models import Model, QuerySet
from django.utils.translation import gettext as _

from creme.creme_core import models
from creme.creme_core.core import entity_cell
from creme.creme_core.core.entity_filter import condition_handler
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui.bricks import brick_registry
from creme.creme_core.gui.custom_form import (
    FieldGroup,
    FieldGroupList,
    customform_descriptor_registry,
)
from creme.creme_core.utils.unicode_collation import collator

from .. import constants

logger = logging.getLogger(__name__)


def dump_ct(ctype: ContentType) -> str:
    return '.'.join(ctype.natural_key())


class CellsExporterMixin:
    cell_exporters = {
        # TODO: 'uuid' key instead of 'value' to avoid confusion ??
        entity_cell.EntityCellCustomField.type_id: lambda cell: {
            'type': cell.type_id,
            'value': str(cell.custom_field.uuid),
        },
    }

    def dump_cell(self, cell):
        assert isinstance(cell, entity_cell.EntityCell)

        exporter = self.cell_exporters.get(cell.type_id)

        return cell.to_dict() if exporter is None else exporter(cell)


class Exporter:
    model: Type[Model] = models.CremeModel

    def get_queryset(self) -> QuerySet:
        return self.model._default_manager.all()

    def dump_instance(self, instance: Model) -> dict:
        raise NotImplementedError()

    def __call__(self) -> List[dict]:
        return [*map(self.dump_instance, self.get_queryset())]


class ExportersRegistry:
    """
    Exporters are function which read data in the RDBMS, and return
    "JSONifiable" data.
    These data can be imported (ie: writen in the RDBMS) by a related Importer
    (see importers.py).
    Generally each exporter is related to a model.

    The export view use a global instance of ExportersRegistry: EXPORTERS.
    The exporters which have to be used by this view must be registered
     (see register()).

    When an exporter is registered, an ID is given ; this ID will be used to
    name the "section" in the JSON data (indeed, the key in a dictionary).
    """
    class Collision(Exception):
        pass

    def __init__(self):
        self._registered: Dict[str, Tuple[int, Type[Exporter]]] = OrderedDict()
        self._unregistered: Set[str] = set()

    def __iter__(self) -> Iterator[Tuple[str, Exporter]]:
        for data_id, (__, exporter_cls) in self._registered.items():
            yield data_id, exporter_cls()

    def register(self, data_id: str, priority: int = 1):
        """Register an export function.

        It can be used as a decorator :

            my_registry = ExportersRegistry()

            @my_registry.register(data_id='my_model')
            def my_exporter():
                [...]

        @param data_id: ID (string) for the section in the big JSON dictionary.
               Generally a name related to the model.
        @param priority: If you want to override an exporter from your own app
               with your own exporter, register it with a higher priority
               (the vanilla exporters use the default priority, 1).
        @return: a function which takes the exporter function as only parameter
                (yep, it's better to use the decorator syntax).
        @raises: ExportersRegistry.Collision if an exporter with the same
                 data_id & priority is already registered.
        """
        def _aux(exporter: Type[Exporter]) -> Type[Exporter]:
            if data_id not in self._unregistered:
                registered = self._registered
                existing_item = registered.get(data_id)

                if existing_item is None:
                    registered[data_id] = (priority, exporter)
                else:
                    existing_priority = existing_item[0]

                    if existing_priority == priority:
                        raise self.Collision(
                            f'An exporter with this data ID is already registered: {data_id}'
                        )

                    if existing_priority > priority:
                        logger.warning(
                            'ExportersRegistry.register(): '
                            'exporter for data_id=%s with priority=%s '
                            'is ignored (there is already an exporter with priority=%s).',
                            data_id, priority, existing_priority,
                        )
                    else:
                        logger.warning(
                            'ExportersRegistry.register(): '
                            'the exporter for data_id=%s '
                            'with priority=%s overrides another exporter.',
                            data_id, priority,
                        )

                        registered[data_id] = (priority, exporter)

            return exporter

        return _aux

    def unregister(self, data_id: str) -> None:
        """Un-register the exporter associated to an ID.
        Future exporters registered with this ID will be ignored by register() too
        (so you do have to worry about apps order).

        @param data_id: see register().
        """
        self._unregistered.add(data_id)
        self._registered.pop(data_id, None)


EXPORTERS = ExportersRegistry()


@EXPORTERS.register(data_id=constants.ID_ROLES)
class UserRoleExporter(Exporter):
    model = models.UserRole

    @staticmethod
    def dump_credentials(sc):
        assert isinstance(sc, models.SetCredentials)

        dumped = {
            'value': sc.value,
            'type': sc.set_type,
        }

        ctype = sc.ctype
        if ctype:
            dumped['ctype'] = dump_ct(ctype)

        forbidden = sc.forbidden
        if forbidden:
            dumped['forbidden'] = True

        efilter_id = sc.efilter_id
        if efilter_id:
            dumped['efilter'] = efilter_id

        return dumped

    def dump_instance(self, instance):
        assert isinstance(instance, models.UserRole)

        return {
            'name': instance.name,

            'allowed_apps': [*instance.allowed_apps],
            'admin_4_apps': [*instance.admin_4_apps],

            'creatable_ctypes':  [*map(dump_ct, instance.creatable_ctypes.all())],
            'exportable_ctypes': [*map(dump_ct, instance.exportable_ctypes.all())],

            'credentials': [*map(self.dump_credentials, instance.credentials.all())],
        }


@EXPORTERS.register(data_id=constants.ID_RTYPE_BRICKS)
class RelationBrickItemExporter(CellsExporterMixin, Exporter):
    model = models.RelationBrickItem

    def dump_instance(self, instance):
        assert isinstance(instance, models.RelationBrickItem)

        data = {
            'brick_id':      instance.brick_id,
            'relation_type': instance.relation_type_id,
        }

        ctypes_cells = [*instance.iter_cells()]
        if ctypes_cells:
            data['cells'] = [
                [dump_ct(ctype), [*map(self.dump_cell, cells)]]
                for ctype, cells in ctypes_cells
            ]

        return data


@EXPORTERS.register(data_id=constants.ID_CUSTOM_BRICKS)
class CustomBrickConfigItemExporter(CellsExporterMixin, Exporter):
    model = models.CustomBrickConfigItem

    def dump_instance(self, instance):
        assert isinstance(instance, models.CustomBrickConfigItem)

        return {
            'id':   instance.id,
            'name': instance.name,

            'content_type': dump_ct(instance.content_type),
            'cells': [*map(self.dump_cell, instance.cells)],
        }


class BrickExporterMixin:
    brick_registry = brick_registry

    @staticmethod
    def filter_non_exportable_items(qs):
        return qs.filter(
            brick_id__startswith=models.InstanceBrickConfigItem._brick_id_prefix,
        )

    def items_to_str(self, items):
        return ', '.join(
            brick.verbose_name
            for brick in self.brick_registry.get_bricks(
                brick_ids={bdl.brick_id for bdl in items}
            )
        )


@EXPORTERS.register(data_id=constants.ID_DETAIL_BRICKS)
class BrickDetailviewLocationExporter(BrickExporterMixin, Exporter):
    model = models.BrickDetailviewLocation

    def get_queryset(self):
        qs = self.model._default_manager.all()
        cursed_items = self.filter_non_exportable_items(qs)

        if cursed_items:
            ctypes = {bdl.content_type for bdl in cursed_items}
            try:
                ctypes.remove(None)
            except KeyError:
                default_config = False
            else:
                default_config = True

            ct_labels = sorted((str(ct) for ct in ctypes), key=collator.sort_key)

            if default_config:
                ct_labels.insert(0, _('Default configuration'))

            raise ConflictError(
                _(
                    'The configuration of blocks for detailed-views cannot be '
                    'exported because it contains references to some '
                    'instance-blocks ({blocks}), which are not managed, for the '
                    'following cases: {models}.'
                ).format(
                    blocks=self.items_to_str(cursed_items),
                    models=', '.join(ct_labels)
                )
            )

        return qs

    def dump_instance(self, instance):
        assert isinstance(instance, models.BrickDetailviewLocation)

        data = {
            'id':    instance.brick_id,
            'order': instance.order,
            'zone':  instance.zone,
        }

        ctype = instance.content_type
        if ctype:
            data['ctype'] = dump_ct(ctype)

        role = instance.role
        if role:
            data['role'] = role.name
        elif instance.superuser:
            data['superuser'] = True

        return data


@EXPORTERS.register(data_id=constants.ID_HOME_BRICKS)
class BrickHomeLocationExporter(BrickExporterMixin, Exporter):
    model = models.BrickHomeLocation

    def get_queryset(self):
        qs = self.model._default_manager.all()
        cursed_items = self.filter_non_exportable_items(qs)

        if cursed_items:
            raise ConflictError(
                _(
                    'The configuration of blocks for Home cannot be exported '
                    'because it contains references to some instance-blocks '
                    '({blocks}), which are not managed.'
                ).format(blocks=self.items_to_str(cursed_items))
            )

        return qs

    def dump_instance(self, instance):
        assert isinstance(instance, models.BrickHomeLocation)

        data = {
            'id': instance.brick_id,
            'order': instance.order,
        }

        # TODO: factorise
        role = instance.role
        if role:
            data['role'] = role.name
        elif instance.superuser:
            data['superuser'] = True

        return data


@EXPORTERS.register(data_id=constants.ID_MYPAGE_BRICKS)
class BrickMypageLocationExporter(BrickExporterMixin, Exporter):
    model = models.BrickMypageLocation

    def get_queryset(self):
        qs = self.model._default_manager.filter(user=None)
        cursed_items = self.filter_non_exportable_items(qs)

        if cursed_items:
            raise ConflictError(
                _(
                    'The configuration of blocks for «My page» cannot be exported '
                    'because it contains references to some instance-blocks '
                    '({blocks}), which are not managed.'
                ).format(blocks=self.items_to_str(cursed_items))
            )

        return qs

    def dump_instance(self, instance):
        assert isinstance(instance, models.BrickMypageLocation)

        return {'id': instance.brick_id, 'order': instance.order}


@EXPORTERS.register(data_id=constants.ID_MENU)
class MenuItemExporter(Exporter):
    model = models.MenuConfigItem

    def get_queryset(self):
        # TODO: prefetch children
        return super().get_queryset().filter(parent=None)

    @staticmethod
    def dump_instance_simple(instance):
        data = {
            'id':    instance.entry_id,
            'order': instance.order,
        }

        entry_data = instance.entry_data
        if entry_data:
            data['data'] = entry_data

        return data

    def dump_instance(self, instance):
        assert isinstance(instance, models.MenuConfigItem)

        dump_simple = self.dump_instance_simple
        data = dump_simple(instance)

        children = [*instance.children.all()]
        if children:
            data['children'] = [dump_simple(child) for child in children]

        return data


@EXPORTERS.register(data_id=constants.ID_BUTTONS)
class ButtonMenuItemExporter(Exporter):
    model = models.ButtonMenuItem

    def dump_instance(self, instance):
        assert isinstance(instance, models.ButtonMenuItem)

        data = {
            # 'id':        instance.id,
            'order':     instance.order,
            'button_id': instance.button_id,
        }

        ctype = instance.content_type
        if ctype:
            data['ctype'] = dump_ct(ctype)

        return data


@EXPORTERS.register(data_id=constants.ID_SEARCH)
class SearchConfigItemExporter(CellsExporterMixin, Exporter):
    model = models.SearchConfigItem

    def dump_instance(self, instance):
        assert isinstance(instance, models.SearchConfigItem)

        data = {
            'ctype': dump_ct(instance.content_type),
            # 'fields': instance.field_names,
            'cells': [*map(self.dump_cell, instance.cells)],
        }

        role = instance.role
        if role:
            data['role'] = role.name
        elif instance.superuser:
            data['superuser'] = True

        if instance.disabled:
            data['disabled'] = True

        return data


@EXPORTERS.register(data_id=constants.ID_PROPERTY_TYPES)
class CremePropertyTypeExporter(Exporter):
    model = models.CremePropertyType

    def get_queryset(self):
        return super().get_queryset().filter(is_custom=True)

    def dump_instance(self, instance):
        assert isinstance(instance, models.CremePropertyType)

        data = {
            'id': instance.id,
            'text': instance.text,
            'is_copiable': instance.is_copiable,
        }

        ctypes = instance.subject_ctypes.all()
        if ctypes:
            data['subject_ctypes'] = [*map(dump_ct, ctypes)]

        return data


@EXPORTERS.register(data_id=constants.ID_RELATION_TYPES)
class RelationTypeExporter(Exporter):
    model = models.RelationType

    def get_queryset(self):
        return super().get_queryset().filter(
            is_custom=True,
            pk__contains='-subject_',
        )

    @staticmethod
    def dump_rtype_core(rtype):
        assert isinstance(rtype, models.RelationType)

        return {
            'id':              rtype.id,
            'predicate':       rtype.predicate,
            'is_copiable':     rtype.is_copiable,
            'minimal_display': rtype.minimal_display,
        }

    def dump_instance(self, instance):
        assert isinstance(instance, models.RelationType)

        data = self.dump_rtype_core(instance)
        data['symmetric'] = self.dump_rtype_core(instance.symmetric_type)

        subject_ctypes = instance.subject_ctypes.all()
        if subject_ctypes:
            data['subject_ctypes'] = [*map(dump_ct, subject_ctypes)]

        object_ctypes = instance.object_ctypes.all()
        if object_ctypes:
            data['object_ctypes'] = [*map(dump_ct, object_ctypes)]

        subject_properties = instance.subject_properties.values_list('id', flat=True)
        if subject_properties:
            data['subject_properties'] = [*subject_properties]

        object_properties = instance.object_properties.values_list('id', flat=True)
        if object_properties:
            data['object_properties'] = [*object_properties]

        return data


@EXPORTERS.register(data_id=constants.ID_FIELDS_CONFIG)
class FieldsConfigExporter(Exporter):
    model = models.FieldsConfig

    def dump_instance(self, instance):
        assert isinstance(instance, models.FieldsConfig)

        return {
            'ctype': dump_ct(instance.content_type),
            'descriptions': instance.descriptions,
        }


@EXPORTERS.register(data_id=constants.ID_CUSTOM_FIELDS)
class CustomFieldExporter(Exporter):
    model = models.CustomField

    enum_types = {
        models.CustomField.ENUM,
        models.CustomField.MULTI_ENUM,
    }

    def dump_instance(self, instance):
        assert isinstance(instance, models.CustomField)

        cf_type = instance.field_type
        data = {
            'uuid': str(instance.uuid),
            'ctype': dump_ct(instance.content_type),
            'name': instance.name,
            'type': cf_type,
        }

        if cf_type in self.enum_types:
            data['choices'] = [
                *instance.customfieldenumvalue_set
                         .order_by('id')
                         .values_list('value', flat=True)
            ]

        return data


@EXPORTERS.register(data_id=constants.ID_HEADER_FILTERS)
class HeaderFilterExporter(CellsExporterMixin, Exporter):
    model = models.HeaderFilter

    def get_queryset(self):
        return super().get_queryset().filter(is_custom=True)

    def dump_instance(self, instance):
        assert isinstance(instance, models.HeaderFilter)

        data = {
            'id':    instance.id,
            'name':  instance.name,
            'ctype': dump_ct(instance.entity_type),
            'cells': [*map(self.dump_cell, instance.cells)],
        }

        user = instance.user
        if user:
            data['user'] = user.username

            if instance.is_private:
                data['is_private'] = True

        return data


def _export_efc_relation(cond: models.EntityFilterCondition) -> dict:
    value = cond.value

    dumped_value = {'has': value['has']}

    entity_id = value.get('entity_id')
    if entity_id:
        dumped_value['entity_uuid'] = str(
            models.CremeEntity.objects.filter(id=entity_id).values_list('uuid', flat=True)[0]
        )
    else:
        ct_id = value.get('ct_id')
        if ct_id:
            dumped_value['ct'] = dump_ct(ContentType.objects.get_for_id(ct_id))

    return {
        'name': cond.name,
        'value': dumped_value,
    }


def _export_efc_customfield(cond: models.EntityFilterCondition) -> dict:
    value = cond.value
    del value['rname']

    return {
        # TODO: 'uuid' key instead of 'name' to avoid confusion ??
        # TODO: better error message tah the get()'s one...
        'name': str(models.CustomField.objects.get(id=cond.name).uuid),
        'value': value,
    }


def _export_efc_datecustomfield(cond: models.EntityFilterCondition) -> dict:
    value = cond.value
    del value['rname']

    return {
        # TODO: 'uuid' key instead of 'name' to avoid confusion ??
        # TODO: better error message tah the get()'s one...
        'name': str(models.CustomField.objects.get(id=cond.name).uuid),
        'value': value,
    }


@EXPORTERS.register(data_id=constants.ID_ENTITY_FILTERS)
class EntityFilterExporter(Exporter):
    model = models.EntityFilter

    condition_exporters: Dict[int, Callable[[models.EntityFilterCondition], dict]] = {
        condition_handler.RelationConditionHandler.type_id:        _export_efc_relation,
        condition_handler.CustomFieldConditionHandler.type_id:     _export_efc_customfield,
        condition_handler.DateCustomFieldConditionHandler.type_id: _export_efc_datecustomfield,
    }

    def get_queryset(self):
        return super().get_queryset().filter(is_custom=True)

    def dump_filtercond(self, cond: models.EntityFilterCondition) -> dict:
        dumped = {'type': cond.type}
        exporter = self.condition_exporters.get(cond.type)

        if exporter:
            dumped.update(exporter(cond))
        else:
            dumped['name'] = cond.name

            if cond.value:
                dumped['value'] = cond.value

        return dumped

    # TODO: check 'EntityFilterCondition.error' before sending shitty filters ??
    def dump_instance(self, instance):
        assert isinstance(instance, models.EntityFilter)

        data = {
            'id': instance.id,
            'name': instance.name,
            'ctype': dump_ct(instance.entity_type),
            'filter_type': instance.filter_type,
            'use_or': instance.use_or,
            'conditions': [
                *map(self.dump_filtercond, instance.conditions.all()),
            ],
        }

        user = instance.user
        if user:
            data['user'] = user.username

            if instance.is_private:
                data['is_private'] = True

        return data


@EXPORTERS.register(data_id=constants.ID_CUSTOM_FORMS)
class CustomFormsExporter(CellsExporterMixin, Exporter):
    model = models.CustomFormConfigItem
    cform_registry = customform_descriptor_registry

    def dump_group(self, group):
        return {
            'name': group.name,
            'layout': group.layout,
            'cells': [self.dump_cell(cell) for cell in group.cells],
        } if isinstance(group, FieldGroup) else group.as_dict()

    def dump_groups(self, item):
        # descriptor = self.cform_registry.get(item.cform_id)
        descriptor = self.cform_registry.get(item.descriptor_id)

        return [
            self.dump_group(group)
            for group in FieldGroupList.from_dicts(
                model=descriptor.model,
                data=item.groups_as_dicts(),
                cell_registry=descriptor.build_cell_registry(),
                allowed_extra_group_classes=(*descriptor.extra_group_classes,)
            )
        ]

    def dump_instance(self, instance):
        assert isinstance(instance, models.CustomFormConfigItem)

        # return {
        #     'id': instance.cform_id,
        #     # 'groups': instance.groups_as_dicts(),
        #     'groups': self.dump_groups(instance),
        # }
        data = {
            'descriptor': instance.descriptor_id,
            'groups': self.dump_groups(instance),
        }

        if instance.superuser:
            data['superuser'] = True
        elif instance.role:
            data['role'] = instance.role.name

        return data
