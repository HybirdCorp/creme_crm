################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2025  Hybird
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
from collections.abc import Callable, Iterator

from django.db.models import Model, QuerySet

from creme.creme_core import models
from creme.creme_core.core.entity_filter import condition_handler
from creme.creme_core.gui.bricks import brick_registry
from creme.creme_core.utils.content_type import ctype_as_key

from .. import constants

logger = logging.getLogger(__name__)


# TODO: should we export Workflows?
#  - probably hard to predict te behaviour, so we wait some feedback on Workflows before
#  - currently conditions are not very portable; improve filter/conditions before
class Exporter:
    model: type[Model] = models.CremeModel

    def get_queryset(self) -> QuerySet:
        return self.model._default_manager.all()

    def dump_instance(self, instance: Model) -> dict:
        raise NotImplementedError

    def __call__(self) -> list[dict]:
        return [*map(self.dump_instance, self.get_queryset())]


class ExportersRegistry:
    """
    Exporters are function which read data in the RDBMS, and return
    "JSONifiable" data.
    These data can be imported (i.e. writen in the RDBMS) by a related Importer
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

    def __init__(self) -> None:
        self._registered: dict[str, tuple[int, type[Exporter]]] = OrderedDict()
        self._unregistered: set[str] = set()

    def __iter__(self) -> Iterator[tuple[str, Exporter]]:
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
        def _aux(exporter: type[Exporter]) -> type[Exporter]:
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
            dumped['ctype'] = ctype_as_key(ctype)

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
            'uuid': str(instance.uuid),
            'name': instance.name,

            'allowed_apps': [*instance.allowed_apps],
            'admin_4_apps': [*instance.admin_4_apps],

            'creatable_ctypes':  [*map(ctype_as_key, instance.creatable_ctypes.all())],
            'exportable_ctypes': [*map(ctype_as_key, instance.exportable_ctypes.all())],

            'credentials': [*map(self.dump_credentials, instance.credentials.all())],
        }


@EXPORTERS.register(data_id=constants.ID_RTYPE_BRICKS)
class RelationBrickItemExporter(Exporter):
    model = models.RelationBrickItem

    def dump_instance(self, instance):
        assert isinstance(instance, models.RelationBrickItem)

        data = {
            'uuid':          str(instance.uuid),
            'relation_type': instance.relation_type_id,
        }

        cells_map = instance.json_cells_map
        if cells_map:
            data['cells'] = cells_map

        return data


@EXPORTERS.register(data_id=constants.ID_INSTANCE_BRICKS)
class InstanceBrickConfigItemExporter(Exporter):
    model = models.InstanceBrickConfigItem

    def dump_instance(self, instance):
        assert isinstance(instance, models.InstanceBrickConfigItem)

        return {
            'uuid':        str(instance.uuid),
            'brick_class': instance.brick_class_id,
            'entity':      str(instance.entity.uuid),
            'extra_data':  instance.json_extra_data,
        }


@EXPORTERS.register(data_id=constants.ID_CUSTOM_BRICKS)
class CustomBrickConfigItemExporter(Exporter):
    model = models.CustomBrickConfigItem

    def dump_instance(self, instance):
        assert isinstance(instance, models.CustomBrickConfigItem)

        return {
            'uuid': str(instance.uuid),
            'name': instance.name,

            'content_type': ctype_as_key(instance.content_type),
            'cells': instance.json_cells,
        }


class BrickExporterMixin:
    brick_registry = brick_registry

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
        return self.model._default_manager.all()

    def dump_instance(self, instance):
        assert isinstance(instance, models.BrickDetailviewLocation)

        data = {
            'id':    instance.brick_id,
            'order': instance.order,
            'zone':  instance.zone,
        }

        ctype = instance.content_type
        if ctype:
            data['ctype'] = ctype_as_key(ctype)

        role = instance.role
        if role:
            data['role'] = str(role.uuid)
        elif instance.superuser:
            data['superuser'] = True

        return data


@EXPORTERS.register(data_id=constants.ID_HOME_BRICKS)
class BrickHomeLocationExporter(BrickExporterMixin, Exporter):
    model = models.BrickHomeLocation

    def get_queryset(self):
        return self.model._default_manager.all()

    def dump_instance(self, instance):
        assert isinstance(instance, models.BrickHomeLocation)

        data = {
            'id': instance.brick_id,
            'order': instance.order,
        }

        # TODO: factorise
        role = instance.role
        if role:
            data['role'] = str(role.uuid)
        elif instance.superuser:
            data['superuser'] = True

        return data


@EXPORTERS.register(data_id=constants.ID_MYPAGE_BRICKS)
class BrickMypageLocationExporter(BrickExporterMixin, Exporter):
    model = models.BrickMypageLocation

    def get_queryset(self):
        return self.model._default_manager.filter(user=None)

    def dump_instance(self, instance):
        assert isinstance(instance, models.BrickMypageLocation)

        return {'id': instance.brick_id, 'order': instance.order}


@EXPORTERS.register(data_id=constants.ID_MENU)
class MenuItemExporter(Exporter):
    model = models.MenuConfigItem

    def get_queryset(self):
        # TODO: prefetch children
        return super().get_queryset().filter(parent=None).select_related('role')

    @staticmethod
    def dump_instance_simple(instance, dump_role=True):
        data = {
            'id':    instance.entry_id,
            'order': instance.order,
        }

        entry_data = instance.entry_data
        if entry_data:
            data['data'] = entry_data

        if dump_role:
            role = instance.role
            if role:
                data['role'] = str(role.uuid)
            elif instance.superuser:
                data['superuser'] = True

        return data

    def dump_instance(self, instance):
        assert isinstance(instance, models.MenuConfigItem)

        dump_simple = self.dump_instance_simple
        data = dump_simple(instance)

        children = [*instance.children.all()]
        if children:
            data['children'] = [dump_simple(child, dump_role=False) for child in children]

        return data


@EXPORTERS.register(data_id=constants.ID_BUTTONS)
class ButtonMenuItemExporter(Exporter):
    model = models.ButtonMenuItem

    def dump_instance(self, instance):
        assert isinstance(instance, models.ButtonMenuItem)

        data = {
            'order':     instance.order,
            'button_id': instance.button_id,
        }

        ctype = instance.content_type
        if ctype:
            data['ctype'] = ctype_as_key(ctype)

        role = instance.role
        if role:
            data['role'] = str(role.uuid)
        elif instance.superuser:
            data['superuser'] = True

        return data


@EXPORTERS.register(data_id=constants.ID_SEARCH)
class SearchConfigItemExporter(Exporter):
    model = models.SearchConfigItem

    def dump_instance(self, instance):
        assert isinstance(instance, models.SearchConfigItem)

        data = {
            'ctype': ctype_as_key(instance.content_type),
            'cells': instance.json_cells,
        }

        role = instance.role
        if role:
            data['role'] = str(role.uuid)
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
            'uuid': str(instance.uuid),
            'text': instance.text,
            'is_copiable': instance.is_copiable,
        }

        ctypes = instance.subject_ctypes.all()
        if ctypes:
            data['subject_ctypes'] = [*map(ctype_as_key, ctypes)]

        return data


@EXPORTERS.register(data_id=constants.ID_RELATION_TYPES)
class RelationTypeExporter(Exporter):
    model = models.RelationType

    def get_queryset(self):
        # TODO: prefetch
        return super().get_queryset().filter(
            is_custom=True,
            pk__contains='-subject_',
            enabled=True,
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
            data['subject_ctypes'] = [*map(ctype_as_key, subject_ctypes)]

        object_ctypes = instance.object_ctypes.all()
        if object_ctypes:
            data['object_ctypes'] = [*map(ctype_as_key, object_ctypes)]

        subject_prop_uuids = instance.subject_properties.values_list('uuid', flat=True)
        if subject_prop_uuids:
            data['subject_properties'] = [*map(str, subject_prop_uuids)]

        subject_forbidden_prop_uuids = instance.subject_forbidden_properties\
                                               .values_list('uuid', flat=True)
        if subject_forbidden_prop_uuids:
            data['subject_forbidden_properties'] = [*map(str, subject_forbidden_prop_uuids)]

        object_prop_uuids = instance.object_properties.values_list('uuid', flat=True)
        if object_prop_uuids:
            data['object_properties'] = [*map(str, object_prop_uuids)]

        object_forbidden_pro_uuids = instance.object_forbidden_properties\
                                             .values_list('uuid', flat=True)
        if object_forbidden_pro_uuids:
            data['object_forbidden_properties'] = [*map(str, object_forbidden_pro_uuids)]

        return data


@EXPORTERS.register(data_id=constants.ID_FIELDS_CONFIG)
class FieldsConfigExporter(Exporter):
    model = models.FieldsConfig

    def dump_instance(self, instance):
        assert isinstance(instance, models.FieldsConfig)

        return {
            'ctype': ctype_as_key(instance.content_type),
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
            'ctype': ctype_as_key(instance.content_type),
            'name': instance.name,
            'type': cf_type,
        }

        if cf_type in self.enum_types:
            data['choices'] = [
                # NB: .values('uuid', 'value') is not serializable with the UUID objects
                {
                    'uuid': str(uid),
                    'value': value,
                } for uid, value in instance.customfieldenumvalue_set
                                            .order_by('id')
                                            .values_list('uuid', 'value')
            ]

        return data


@EXPORTERS.register(data_id=constants.ID_HEADER_FILTERS)
class HeaderFilterExporter(Exporter):
    model = models.HeaderFilter

    def get_queryset(self):
        return super().get_queryset().filter(is_custom=True)

    def dump_instance(self, instance):
        assert isinstance(instance, models.HeaderFilter)

        data = {
            'id':    instance.id,
            'name':  instance.name,
            'ctype': ctype_as_key(instance.entity_type),
            'cells': instance.json_cells,
        }

        user = instance.user
        if user:
            data['user'] = str(user.uuid)

            if instance.is_private:
                data['is_private'] = True

        extra_data = instance.extra_data
        if extra_data:
            data['extra_data'] = extra_data

        return data


def _export_efc_customfield(cond: models.EntityFilterCondition) -> dict:
    value = cond.value
    del value['rname']

    return {
        # TODO: 'uuid' key instead of 'name' to avoid confusion ??
        'name': cond.name,
        'value': value,
    }


def _export_efc_datecustomfield(cond: models.EntityFilterCondition) -> dict:
    value = cond.value
    del value['rname']

    return {
        # TODO: 'uuid' key instead of 'name' to avoid confusion ??
        'name': cond.name,
        'value': value,
    }


@EXPORTERS.register(data_id=constants.ID_ENTITY_FILTERS)
class EntityFilterExporter(Exporter):
    model = models.EntityFilter

    condition_exporters: dict[int, Callable[[models.EntityFilterCondition], dict]] = {
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
            'ctype': ctype_as_key(instance.entity_type),
            'filter_type': instance.filter_type,
            'use_or': instance.use_or,
            'conditions': [
                *map(self.dump_filtercond, instance.conditions.all()),
            ],
        }

        user = instance.user
        if user:
            data['user'] = str(user.uuid)

            if instance.is_private:
                data['is_private'] = True

        extra_data = instance.extra_data
        if extra_data:
            data['extra_data'] = extra_data

        return data


@EXPORTERS.register(data_id=constants.ID_CUSTOM_FORMS)
class CustomFormsExporter(Exporter):
    model = models.CustomFormConfigItem

    def dump_instance(self, instance):
        assert isinstance(instance, models.CustomFormConfigItem)

        data = {
            'descriptor': instance.descriptor_id,
            'groups': instance.json_groups,
        }

        if instance.superuser:
            data['superuser'] = True
        elif instance.role:
            data['role'] = str(instance.role.uuid)

        return data


@EXPORTERS.register(data_id=constants.ID_CHANNELS)
class NotificationChannelsExporter(Exporter):
    model = models.NotificationChannel

    def get_queryset(self):
        return super().get_queryset().filter(deleted=None)

    def dump_instance(self, instance):
        assert isinstance(instance, models.NotificationChannel)

        data = {
            'uuid': str(instance.uuid),
            'required': instance.required,
            'default_outputs': instance.default_outputs,
        }

        if instance.type_id:
            data['type'] = instance.type_id
        else:
            data['name'] = instance.name
            data['description'] = instance.description

        return data
