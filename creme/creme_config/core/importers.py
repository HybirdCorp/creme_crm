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
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Type, Union

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Model
from django.forms import ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from creme.creme_core.core import entity_cell
from creme.creme_core.core.entity_filter import EF_USER
from creme.creme_core.core.entity_filter.condition_handler import (
    CustomFieldConditionHandler,
    DateCustomFieldConditionHandler,
    DateRegularFieldConditionHandler,
    FilterConditionHandler,
    PropertyConditionHandler,
    RegularFieldConditionHandler,
    RelationConditionHandler,
    RelationSubFilterConditionHandler,
    SubFilterConditionHandler,
)
from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.gui.custom_form import (
    EntityCellCustomFormSpecial,
    FieldGroupList,
    customform_descriptor_registry,
)
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    BrickMypageLocation,
    ButtonMenuItem,
    CremeEntity,
    CremePropertyType,
    CustomBrickConfigItem,
    CustomField,
    CustomFieldEnumValue,
    CustomFormConfigItem,
    EntityFilter,
    EntityFilterCondition,
    FieldsConfig,
    HeaderFilter,
    MenuConfigItem,
    RelationBrickItem,
    RelationType,
    SearchConfigItem,
    SetCredentials,
    UserRole,
)
from creme.creme_core.models.custom_field import _TABLES as CF_TABLES
from creme.creme_core.utils.dependence_sort import (
    DependenciesLoopError,
    dependence_sort,
)
from creme.creme_core.utils.meta import FieldInfo

from .. import constants

logger = logging.getLogger(__name__)
get_ct = ContentType.objects.get_by_natural_key

ValidatedData = Dict[Model, Set[str]]
DeserializedInstance = Dict[str, Any]
DeserializedInstances = List[DeserializedInstance]
DeserializedData = Dict[str, Union[str, DeserializedInstances]]


def load_ct(ct_str: str) -> ContentType:
    return get_ct(*ct_str.split('.'))


def load_model(model_str: str) -> Model:
    return load_ct(model_str).model_class()


# ------------------------------------------------------------------------------

# TODO: factorise these classes with EntityCells build() methods ?
class CellProxy:
    """ Abstract class.

    CellProxies allows to validate data (deserialized JSON) describing an
    EntityCell, and then to build an instance.

    This is done in 2 steps, because some required instance (RelationType...)
    can be validated before being stored in DB (there are described in the
    importation data).
    """
    # Override this in child classes
    cell_cls: Type[entity_cell.EntityCell] = entity_cell.EntityCell

    def __init__(
            self,
            container_label: str,
            model: Type[CremeEntity],
            value: str,
            validated_data: ValidatedData):
        """Constructor.

        @param container_label: String used by error messages to identify related
               objects containing the cells (like HeaderFilter instance)
        @param model: model related to the HeaderFilter.
        @param value: deserialized data.
        @param validated_data: IDs of validated (future) instances ;
               dictionary <key=model ; values=set of IDs>
        """
        self.container_label = container_label
        self.model = model
        self.value = value

        self._validate(validated_data)

    def _validate(self, validated_data: ValidatedData) -> None:
        """Extracts & validates information from self.value.

        Raises exceptions to indicate errors.
        ValidationErrors contain friendlier error messages.
        """
        raise NotImplementedError

    def build_cell(self) -> Optional[entity_cell.EntityCell]:
        """
        @return: an EntityCell instance.
        """
        return self.cell_cls.build(self.model, self.value)


class CellProxiesRegistry:
    """Registry for CellProxy classes.

    Can be used as a decorator (see __call__() ).
    """
    def __init__(self):
        self._proxies_classes: Dict[str, Type[CellProxy]] = {}

    def __call__(self, proxy_cls: Type[CellProxy]) -> Type[CellProxy]:
        self._proxies_classes[proxy_cls.cell_cls.type_id] = proxy_cls
        return proxy_cls

    def get(self, type_id: str) -> Optional[Type[CellProxy]]:
        "@param type_id: see EntityCell.type_id."
        return self._proxies_classes.get(type_id)

    def build_proxies_from_dicts(self, *, model, container_label, cell_dicts, validated_data):
        cells_proxies = []

        for cell_dict in cell_dicts:  # TODO: check is a dict
            cell_type  = cell_dict['type']
            cell_value = cell_dict['value']

            cell_proxy_cls = self.get(cell_type)

            if cell_proxy_cls is None:
                raise ValidationError(
                    _(
                        'The column with type="{type}" is invalid in «{container}».'
                    ).format(type=cell_type, container=container_label)
                )

            cells_proxies.append(cell_proxy_cls(
                container_label=container_label,
                model=model,
                value=cell_value,
                validated_data=validated_data,
            ))

        return cells_proxies


CELL_PROXIES = CellProxiesRegistry()


@CELL_PROXIES
class CellProxyRegularField(CellProxy):
    cell_cls = entity_cell.EntityCellRegularField

    def _validate(self, validated_data):
        try:
            FieldInfo(self.model, self.value)
        except FieldDoesNotExist:
            raise ValidationError(
                _('The column with field="{field}" is invalid in «{container}».').format(
                    field=self.value, container=self.container_label,
                )
            )


@CELL_PROXIES
class CellProxyCustomField(CellProxy):
    cell_cls = entity_cell.EntityCellCustomField

    def _validate(self, validated_data):
        value = self.value

        if value not in validated_data[CustomField] and \
           not CustomField.objects.filter(uuid=value).exists():
            raise ValidationError(
                _(
                    'The column with custom-field="{uuid}" is invalid in «{container}».'
                ).format(uuid=value, container=self.container_label)
            )

    def build_cell(self):
        return self.cell_cls(CustomField.objects.get(uuid=self.value))


@CELL_PROXIES
class CellProxyFunctionField(CellProxy):
    cell_cls = entity_cell.EntityCellFunctionField

    registry = function_field_registry

    def _validate(self, validated_data):
        func_field = self.registry.get(self.model, self.value)

        if func_field is None:
            raise ValidationError(
                _(
                    'The column with function-field="{ffield}" is invalid in «{container}».'
                ).format(ffield=self.value, container=self.container_label)
            )


@CELL_PROXIES
class CellProxyRelation(CellProxy):
    cell_cls = entity_cell.EntityCellRelation

    def _validate(self, validated_data):
        value = self.value

        if value not in validated_data[RelationType] and \
           not RelationType.objects.filter(pk=value).exists():
            raise ValidationError(
                _(
                    'The column with relation-type="{rtype}" is invalid in «{container}».'
                ).format(rtype=value, container=self.container_label)
            )


# ------------------------------------------------------------------------------

class Importer:
    """A base class for object which import model-instances from another
    deployment of Creme.

    These importers are fed with deserialized-JSON data (ie: data is list of
    dictionaries with string/int...).

    The import is done in 2 phases (validation then save) in order to be cleanly
    used by a form.

    When a JSON dictionary is imported, each importer must have a different data ID,
    which correspond to the key in the dictionary (section).

    An importer can have dependencies to indicate that some other importers should
    be used ie: their method validate() is called) before
    (see ImportersRegistry.build_importers()).
    """
    dependencies: Iterable[str] = ()  # Sequence of data IDs

    def __init__(self, data_id: str):
        self.data_id = data_id
        self._data = ()

    def validate(self,
                 deserialized_data: DeserializedData,
                 validated_data: ValidatedData) -> None:
        """Validate some deserialized data before saving them
        (ie: call save() _after_)).

        Internal data are built using deserialized_data ; it can raise various
        exception types during this process (ValueError, KeyError) which
        indicates data error to the caller.
        If an error is due to the user (eg: some imported data are colliding
        with existing data, & it can lead to tricky errors), a ValidationError
        with an human-readable message is raised.

        @param deserialized_data: dictionary.
        @param validated_data: dictionary <model_class: set of strings>,
               containing information about instances which will be created by
               the Importer instances used before.
        @raise: Various type of exception, but ValidationErrors indicate a user
                error.
        """
        section = deserialized_data.get(self.data_id) or []

        if not isinstance(section, list):
            raise ValueError(f'The section with key {self.data_id} is not a list.')

        self._validate_section(
            deserialized_section=section,
            validated_data=validated_data,
        )

    def _validate_section(self,
                          deserialized_section: DeserializedInstances,
                          validated_data: ValidatedData) -> None:
        """Validate the data corresponding to the data ID.

        @param deserialized_section: list of dictionaries.
        @param validated_data: see validate().
        @return: see validate().
        """
        raise NotImplementedError

    def save(self) -> None:
        """Save the data which have been validated (see validate())."""
        raise NotImplementedError


class ImportersRegistry:
    """
    Registry for classes inheriting <Importer>.

    The import view/form use a global instance of importersRegistry: IMPORTERS.
    The importers which have to be used by this view must be registered
    (see register()).
    """
    class Collision(Exception):
        pass

    def __init__(self):
        self._registered: Dict[str, Tuple[int, Type[Importer]]] = OrderedDict()
        self._unregistered: Set[str] = set()

    def build_importers(self) -> List[Importer]:
        importers = [
            importer_cls(data_id)
            for data_id, (__, importer_cls) in self._registered.items()
        ]

        return dependence_sort(
            importers,
            get_key=lambda imp: imp.data_id,
            get_dependencies=lambda imp: imp.dependencies,
        )

    def register(self, data_id: str, priority: int = 1):
        """Register an importer class (see Importer).

        It can be used as a decorator :

            my_registry = ImportersRegistry()

            @my_registry.register(data_id='my_model')
            class MyImporter(Importer):
                [...]

        @param data_id: this ID is used to build the importer instance
               (see Importer.__init__()) when the method build_importers() is
               called.
        @param priority: If you want to override an importer class from your own
               app with your own importer class, register it with a higher
               priority (the vanilla importers use the default priority, 1).
        @return: a function which takes the importer class as only parameter
                 (yep, it's better to use the decorator syntax).
        @raises: ImportersRegistry.Collision if an importer class with the same
                 data_id & priority is already registered.
        """
        def _aux(importer_cls: Type[Importer]) -> Type[Importer]:
            if data_id not in self._unregistered:
                data = self._registered
                existing_item = data.get(data_id)

                if existing_item is None:
                    data[data_id] = (priority, importer_cls)
                else:
                    existing_priority = existing_item[0]

                    if existing_priority == priority:
                        raise self.Collision(
                            f'An exporter with this data ID is already registered: {data_id}'
                        )

                    if existing_priority > priority:
                        logger.warning(
                            'ImportersRegistry.register(): importer for '
                            'data_id=%s with priority=%s is ignored (there is '
                            'already an importer with priority=%s).',
                            data_id, priority, existing_priority,
                        )
                    else:
                        logger.warning(
                            'ImportersRegistry.register(): the importer for '
                            'data_id=%s with priority=%s overrides another importer.',
                            data_id, priority,
                        )

                        data[data_id] = (priority, importer_cls)

            return importer_cls

        return _aux

    def unregister(self, data_id: str) -> None:
        """Un-register the importer class associated to an ID.
        Future importer classes registered with this ID will be ignored by register() too
        (so you do have to worry about apps order).

        @param data_id: see register().
        """
        self._unregistered.add(data_id)
        self._registered.pop(data_id, None)


IMPORTERS = ImportersRegistry()


@IMPORTERS.register(data_id=constants.ID_ROLES)
class UserRolesImporter(Importer):
    dependencies = [constants.ID_ENTITY_FILTERS]

    def _validate_section(self, deserialized_section, validated_data):
        def load_creds(info):
            ctype_str = info.get('ctype')
            data = {
                'value':     info['value'],
                'set_type':  info['type'],
                'ctype':     load_ct(ctype_str) if ctype_str else None,
                'forbidden': info.get('forbidden', False),
            }

            efilter_id = info.get('efilter')
            if efilter_id:
                if efilter_id not in validated_data[EntityFilter]:
                    raise ValidationError(
                        _('This filter PK is invalid: «{}».').format(efilter_id)
                    )

                data['efilter_id'] = efilter_id

            return data

        self._data = [
            {
                'name': role_info['name'],

                # TODO: validate these info
                'allowed_apps': role_info.get('allowed_apps', ()),
                'admin_4_apps': role_info.get('admin_4_apps', ()),

                'creatable_ctypes':  [
                    *map(load_ct, role_info.get('creatable_ctypes', ())),
                ],
                'exportable_ctypes': [
                    *map(load_ct, role_info.get('exportable_ctypes', ())),
                ],

                'credentials': [*map(load_creds, role_info.get('credentials', ()))],
            } for role_info in deserialized_section
        ]
        validated_data[UserRole].update(d['name'] for d in self._data)

    def save(self):
        for role_data in self._data:
            role, created = UserRole.objects.update_or_create(
                name=role_data['name'],
                defaults={
                    'allowed_apps': role_data['allowed_apps'],
                    'admin_4_apps': role_data['admin_4_apps'],
                },
            )

            role.creatable_ctypes.set(role_data['creatable_ctypes'])
            role.exportable_ctypes.set(role_data['exportable_ctypes'])

            if not created:
                role.credentials.all().delete()  # TODO: recycle instances

            for creds_info in role_data['credentials']:
                SetCredentials.objects.create(role=role, **creds_info)


@IMPORTERS.register(data_id=constants.ID_MENU)
class MenuConfigImporter(Importer):
    def load_mci(self, mci_info: dict) -> dict:
        def info_as_kwargs(info):
            return {
                'entry_id': info['id'],
                'order': int(info['order']),
                'entry_data': info.get('data') or {},
            }

        data = info_as_kwargs(mci_info)
        data['children'] = [
            info_as_kwargs(child_info)
            for child_info in mci_info.get('children', ())
        ]

        return data

    def _validate_section(self, deserialized_section, validated_data):
        self._data = [*map(self.load_mci, deserialized_section)]

    def save(self):
        MenuConfigItem.objects.all().delete()  # TODO: recycle instances

        create_item = MenuConfigItem.objects.create

        for data in self._data:
            children = data.pop('children')
            parent = create_item(**data)

            for child_data in children:
                create_item(parent=parent, **child_data)


@IMPORTERS.register(data_id=constants.ID_BUTTONS)
class ButtonsConfigImporter(Importer):
    def load_bmi(self, bmi_info: dict) -> dict:
        data = {
            # 'id': bmi_info['id'],
            'button_id': bmi_info['button_id'],
            'order': int(bmi_info['order']),
        }

        natural_ctype = bmi_info.get('ctype')
        if natural_ctype:
            data['content_type'] = load_ct(natural_ctype)

        return data

    def _validate_section(self, deserialized_section, validated_data):
        self._data = [*map(self.load_bmi, deserialized_section)]

    def save(self):
        ButtonMenuItem.objects.all().delete()  # TODO: recycle instances

        for data in self._data:
            ButtonMenuItem.objects.create(**data)


@IMPORTERS.register(data_id=constants.ID_SEARCH)
class SearchConfigImporter(Importer):
    dependencies = [constants.ID_ROLES, constants.ID_CUSTOM_FIELDS]

    # TODO: registry with only regular & custom fields ??
    cells_proxies_registry = CELL_PROXIES

    def _validate_section(self, deserialized_section, validated_data):
        def load_sci(sci_info):
            ct = load_ct(sci_info['ctype'])
            model = ct.model_class()

            data = {
                'content_type': ct,
                # 'field_names':  str(sci_info['fields']),

                # 'json_cells':  sci_info['cells'],
                'cells': self.cells_proxies_registry.build_proxies_from_dicts(
                    model=model,
                    container_label=_('search configuration of model="{model}"').format(
                        model=model,
                    ),
                    cell_dicts=sci_info['cells'],
                    validated_data=validated_data,
                ),
            }

            role_name = sci_info.get('role')
            if role_name:
                if role_name in validated_data[UserRole]:
                    data['role_name'] = role_name
                else:
                    data['role'] = UserRole.objects.get(name=role_name)  # TODO: cache
            elif sci_info.get('superuser'):
                data['superuser'] = True

            if sci_info.get('disabled'):
                data['disabled'] = True

            return data

        self._data = [*map(load_sci, deserialized_section)]

    def save(self):
        for data in self._data:
            role_name = data.pop('role_name', None)
            if role_name:
                data['role'] = UserRole.objects.get(name=role_name)  # TODO: cache

            data['cells'] = [
                cell_proxy.build_cell() for cell_proxy in data['cells']
            ]

            SearchConfigItem.objects.create(**data)


@IMPORTERS.register(data_id=constants.ID_PROPERTY_TYPES)
class PropertyTypesImporter(Importer):
    def load_ptype(self, ptype_info: dict) -> dict:
        ptype_id = ptype_info['id']

        ptype = CremePropertyType.objects.filter(id=ptype_id, is_custom=False).first()
        if ptype is not None:
            raise ValidationError(
                _('This property type cannot be overridden: «{}».').format(ptype)
            )

        return {
            'id': ptype_id,
            'text': ptype_info['text'],
            'is_copiable': bool(ptype_info['is_copiable']),
            'subject_ctypes': [
                *map(load_ct, ptype_info.get('subject_ctypes', ())),
            ],
        }

    def _validate_section(self, deserialized_section, validated_data):
        self._data = [*map(self.load_ptype, deserialized_section)]
        validated_data[CremePropertyType].update(d['id'] for d in self._data)

    def save(self):
        for data in self._data:
            ptype_id       = data.pop('id')
            subject_ctypes = data.pop('subject_ctypes')
            ptype = CremePropertyType.objects.update_or_create(id=ptype_id, defaults=data)[0]
            ptype.subject_ctypes.set(subject_ctypes)


@IMPORTERS.register(data_id=constants.ID_RELATION_TYPES)
class RelationTypesImporter(Importer):
    dependencies = [constants.ID_PROPERTY_TYPES]

    def _validate_section(self, deserialized_section, validated_data):
        created_ptype_ids = {*validated_data[CremePropertyType]}

        def load_ptypes(ptype_ids):
            if not isinstance(ptype_ids, list) or \
               not all(isinstance(pt_id, str) for pt_id in ptype_ids):
                raise ValueError(
                    f'RelationTypesImporter: '
                    f'*_ptypes values must be list of strings: {ptype_ids}'
                )

            ptypes = [
                *CremePropertyType.objects.filter(pk__in=ptype_ids),
            ] if ptype_ids else []

            if len(ptypes) != len(ptype_ids):
                non_existings_ids = {*ptype_ids} - {pt.id for pt in ptypes}
                imported_ids = [
                    pt_id
                    for pt_id in non_existings_ids
                    if pt_id in created_ptype_ids
                ]

                non_existings_ids.difference_update(imported_ids)

                if non_existings_ids:
                    raise ValidationError(
                        _('This property type PKs are invalid: {}.').format(
                            ', '.join(non_existings_ids)
                        )
                    )

                ptypes.extend(imported_ids)

            return ptypes

        def load_rtype(rtype_info):
            rtype_id = str(rtype_info['id'])

            if '-subject_' not in rtype_id:
                raise ValidationError(
                    _('This relation type PK is invalid: «{}».').format(rtype_id)
                )

            rtype = RelationType.objects.filter(id=rtype_id, is_custom=False).first()
            if rtype is not None:
                raise ValidationError(
                    _('This relation type cannot be overridden: «{}».').format(rtype)
                )

            sym_rtype_info = rtype_info['symmetric']

            return {
                'id':        rtype_id,
                'predicate': rtype_info['predicate'],

                'is_copiable':     bool(rtype_info['is_copiable']),
                'minimal_display': bool(rtype_info['minimal_display']),

                'subject_models': [*map(load_model, rtype_info.get('subject_ctypes', ()))],
                'object_models':  [*map(load_model, rtype_info.get('object_ctypes', ()))],

                'subject_ptypes': load_ptypes(rtype_info.get('subject_properties') or []),
                'object_ptypes':  load_ptypes(rtype_info.get('object_properties') or []),

                'symmetric': {
                    'id':        rtype_id.replace('-subject_', '-object_'),
                    'predicate': sym_rtype_info['predicate'],

                    'is_copiable':     bool(sym_rtype_info['is_copiable']),
                    'minimal_display': bool(sym_rtype_info['minimal_display']),
                },
            }

        self._data = data = [*map(load_rtype, deserialized_section)]

        validated_rtype_ids = validated_data[RelationType]
        validated_rtype_ids.update(d['id'] for d in data)
        validated_rtype_ids.update(d['symmetric']['id'] for d in data)

    def save(self):
        for data in self._data:
            sym_data = data['symmetric']
            RelationType.objects.smart_update_or_create(
                (
                    data['id'],
                    data['predicate'],
                    data.get('subject_models'),
                    data.get('subject_ptypes'),
                ),
                (
                    sym_data['id'],
                    sym_data['predicate'],
                    data.get('object_models'),
                    data.get('object_ptypes'),
                ),
                is_custom=True,
                is_copiable=(data['is_copiable'], sym_data['is_copiable']),
                minimal_display=(data['minimal_display'], sym_data['minimal_display']),
            )


@IMPORTERS.register(data_id=constants.ID_FIELDS_CONFIG)
class FieldsConfigImporter(Importer):
    def _validate_section(self, deserialized_section, validated_data):
        def load_fields_config(fconfig_info: dict) -> dict:
            ctype = load_ct(fconfig_info['ctype'])

            if FieldsConfig.objects.filter(content_type=ctype).exists():
                raise ValidationError(
                    _(
                        'There is already a fields configuration for the model «{}».'
                    ).format(ctype)
                )

            return {
                'content_type': ctype,
                'descriptions': fconfig_info['descriptions'],
            }

        self._data = [*map(load_fields_config, deserialized_section)]

    def save(self):
        for data in self._data:
            FieldsConfig.objects.create(**data)


@IMPORTERS.register(data_id=constants.ID_CUSTOM_FIELDS)
class CustomFieldsImporter(Importer):
    ENUM_TYPES = {
        CustomField.ENUM,
        CustomField.MULTI_ENUM
    }

    def load_cfield(self, cfield_info: dict) -> dict:
        field_type = int(cfield_info['type'])

        if field_type not in CF_TABLES:
            raise ValidationError(
                _('This custom-field type is invalid: {}.').format(field_type)
            )

        uuid = cfield_info['uuid']
        if CustomField.objects.filter(uuid=uuid).exists():
            raise ValidationError(
                _('There is already a custom-field with the same UUID: {}.').format(uuid)
            )

        name = cfield_info['name']
        ctype = load_ct(cfield_info['ctype'])
        if CustomField.objects.filter(content_type=ctype, name=name).exists():
            raise ValidationError(
                _('There is already a custom-field with the same name: {}.').format(name)
            )

        data = {
            'uuid': uuid,
            'name': name,
            'field_type': field_type,
            'content_type': ctype,
        }

        if field_type in self.ENUM_TYPES:
            data['choices'] = cfield_info['choices']

        return data

    def _validate_section(self, deserialized_section, validated_data):
        self._data = [*map(self.load_cfield, deserialized_section)]
        validated_data[CustomField].update(d['uuid'] for d in self._data)

    def save(self):
        for data in self._data:
            choices = data.pop('choices', ())
            # NB: we do not check if a custom-field with the same name already exists,
            #     because it is not checked by the CustomField form anyway.
            cfield = CustomField.objects.create(**data)

            for choice in choices:
                CustomFieldEnumValue.objects.create(custom_field=cfield, value=choice)


# Header Filters ---------------------------------------------------------------

@IMPORTERS.register(data_id=constants.ID_HEADER_FILTERS)
class HeaderFiltersImporter(Importer):
    dependencies = [constants.ID_RELATION_TYPES, constants.ID_CUSTOM_FIELDS]

    cells_proxies_registry = CELL_PROXIES

    def _validate_section(self, deserialized_section, validated_data):
        User = get_user_model()

        def load_hfilter(hfilter_info):
            hfilter_id = hfilter_info['id']
            hfilter = HeaderFilter.objects.filter(id=hfilter_id, is_custom=False).first()
            if hfilter is not None:
                raise ValidationError(
                    _('This view of list cannot be overridden: «{}».').format(hfilter)
                )

            model = load_model(hfilter_info['ctype'])
            data = {
                'id':         hfilter_id,
                'model':      model,
                'name':       str(hfilter_info['name']),
                'user':       None,
                'is_private': False,

                'cells':  self.cells_proxies_registry.build_proxies_from_dicts(
                    model=model,
                    container_label=_('view of list id="{id}"').format(id=hfilter_id),
                    cell_dicts=hfilter_info['cells'],
                    validated_data=validated_data,
                ),
            }

            username = hfilter_info.get('user')
            if username:
                data['is_private'] = bool(hfilter_info.get('is_private', False))

                try:
                    data['user'] = User.objects.get(username=username)
                except User.DoesNotExist:
                    logger.warning(
                        'HeaderFiltersImporter: this user does not exist '
                        '(filter is dropped): %s',
                        username,
                    )
                    return None

            return data

        self._data = [*filter(None, map(load_hfilter, deserialized_section))]
        validated_data[HeaderFilter].update(d['id'] for d in self._data)

    def save(self):
        create_hf = HeaderFilter.objects.create_if_needed

        for data in self._data:
            model = data['model']

            create_hf(
                pk=data['id'],
                model=model,
                is_custom=True,
                name=data['name'],
                user=data['user'],
                is_private=data['is_private'],
                cells_desc=[
                    cell_proxy.build_cell() for cell_proxy in data['cells']
                ],
            )


# Entity Filters ---------------------------------------------------------------
class ConditionProxy:
    """ Abstract class.

    ConditionProxies allows to validate data (deserialized JSON) describing an
    EntityFilterCondition, and then to build an (not saved) instance.

    This is done in 2 steps, because some required instance (RelationType...)
    can be validated before being stored in DB (there are described in the
    importation data).
    """

    type_id = 0  # Override in child classes

    def __init__(self,
                 efilter_id: str,
                 model: Type[CremeEntity],
                 name: str,
                 value: Any,
                 validated_data: ValidatedData,
                 ):
        """Constructor.

        @param efilter_id: ID of related EntityFilter instance
               (used by error messages).
        @param model: model related to the EntityFilter.
        @param name: deserialized name.
        @param value: deserialized value.
        @param validated_data: IDs of validated (future) instances ;
               dictionary <key=model ; values=set of IDs>.
        """
        self.efilter_id = efilter_id
        self.model = model
        self.name = name
        self.value = value

        self._validate(validated_data)

    def _validate(self, validated_data: ValidatedData):
        """Extracts & validates information from self.value.

        Raises exceptions to indicate errors.
        ValidationErrors contain friendlier error messages.
        """
        pass

    def _get_date_kwargs(self, value: dict) -> dict:
        kwargs = {'date_range': value.get('name')}

        start = value.get('start')
        if start:
            kwargs['start'] = date(**start)

        end = value.get('end')
        if end:
            kwargs['end'] = date(**end)

        return kwargs

    def build_condition(self) -> EntityFilterCondition:
        """
        @return: an EntityFilterCondition instance.
        """
        raise NotImplementedError

    @property
    def filter_dependencies(self) -> Iterable[str]:
        """ Returns the IDs of EntityFilters on which the related filter depends
        (some condition use a sub-filter).
        @return: Sequence of strings.
        """
        return ()

    def post_validate(self, validated_data: ValidatedData):
        """Validate the data after all the EntityFilters data have been validated.

        It's useful to detect invalid sub-filters.

        Raises exceptions to indicate errors.
        ValidationErrors contain friendlier error messages.

        @param validated_data: validated_data: IDs of validated (future) instances ;
               dictionary <key=model ; values=set of IDs>.
               Notice that this data should contains information about EntityFilters.
        """
        pass


class ConditionProxiesRegistry:
    """Registry for ConditionProxy classes.

    Can be used as a decorator (see __call__() ).
    """
    def __init__(self):
        self._proxies_classes: Dict[int, Type[ConditionProxy]] = {}

    def __call__(self, proxy_cls: Type[ConditionProxy]) -> Type[ConditionProxy]:
        self._proxies_classes[proxy_cls.type_id] = proxy_cls
        return proxy_cls

    def get(self, type_id: int) -> Optional[Type[ConditionProxy]]:
        return self._proxies_classes.get(type_id)


COND_PROXIES = ConditionProxiesRegistry()


@COND_PROXIES
class ConditionProxySubFilter(ConditionProxy):
    type_id = SubFilterConditionHandler.type_id

    def __init__(self, *args, **kwargs):
        super(ConditionProxySubFilter, self).__init__(*args, **kwargs)
        self.sub_filter = None

    def build_condition(self):
        return SubFilterConditionHandler.build_condition(
            subfilter=self.sub_filter or EntityFilter.objects.get(id=self.name),
        )

    @property
    def filter_dependencies(self):
        # Beware: if the sub_filter already exists, we do use it as dependencies
        #         because it indicates that this sub-filter is not imported
        #         (if we use it, it would cause a DependenciesLoopError)
        return [self.name] if self.sub_filter is None else []

    def post_validate(self, validated_data):
        sub_filter_id = self.name
        sub_filter = None

        if sub_filter_id not in validated_data[EntityFilter]:
            sub_filter = EntityFilter.objects.filter(id=sub_filter_id).first()

            if sub_filter is None:
                raise ValidationError(
                    _(
                        'The condition on sub-filter="{subfilter}" is invalid '
                        'in the filter id="{id}".'
                    ).format(subfilter=sub_filter_id, id=self.efilter_id)
                )

        self.sub_filter = sub_filter


@COND_PROXIES
class ConditionProxyRegularField(ConditionProxy):
    type_id = RegularFieldConditionHandler.type_id

    def _validate(self, validated_data):
        value = self.value

        self._cond = RegularFieldConditionHandler.build_condition(
            model=self.model,
            field_name=self.name,
            operator=int(value['operator']),
            values=value['values'],  # TODO: check is list ?
        )

    def build_condition(self):
        return self._cond


@COND_PROXIES
class ConditionProxyDateField(ConditionProxy):
    type_id = DateRegularFieldConditionHandler.type_id

    def _validate(self, validated_data):
        value = self.value

        self._cond = DateRegularFieldConditionHandler.build_condition(
            model=self.model,
            field_name=self.name,
            **self._get_date_kwargs(value)
        )

    def build_condition(self):
        return self._cond


@COND_PROXIES
class ConditionProxyRelation(ConditionProxy):
    type_id = RelationConditionHandler.type_id

    def _validate(self, validated_data):
        value = self.value
        self.has = bool(value['has'])
        self.entity = None

        entity_uuid = value.get('entity_uuid')
        if entity_uuid:
            self.entity = entity = CremeEntity.objects.filter(uuid=entity_uuid).first()

            if entity is None:
                raise ValidationError(
                    _(
                        'The condition on relation-type is invalid in the '
                        'filter id="{id}" (unknown uuid={uuid}).'
                    ).format(id=self.efilter_id, uuid=entity_uuid)
                )

        ct_str = value.get('ct')
        self.ct = load_ct(ct_str) if ct_str else None

        self.rtype = None

        rtype_id = self.name
        if rtype_id not in validated_data[RelationType]:
            self.rtype = rtype = RelationType.objects.filter(id=rtype_id).first()

            if rtype is None:
                raise ValidationError(
                    _(
                        'The condition on relation-type is invalid in the filter '
                        'id="{id}" (unknown relation-type={rtype}).'
                    ).format(rtype=rtype_id, id=self.efilter_id)
                )

    def build_condition(self):
        return RelationConditionHandler.build_condition(
            model=self.model,
            rtype=self.rtype or RelationType.objects.get(id=self.name),
            has=self.has,
            ct=self.ct,
            entity=self.entity,
        )


@COND_PROXIES
class ConditionProxyRelationSubFilter(ConditionProxy):
    type_id = RelationSubFilterConditionHandler.type_id

    sub_filter: Optional[EntityFilter] = None

    def _validate(self, validated_data):
        value = self.value
        self.has = bool(value['has'])
        self.sub_filter_id = value['filter_id']

        # TODO: factorise
        self.rtype = None

        rtype_id = self.name
        if rtype_id not in validated_data[RelationType]:
            self.rtype = rtype = RelationType.objects.filter(id=rtype_id).first()

            if rtype is None:
                raise ValidationError(
                    _(
                        'The condition on related sub-filter="{subfilter}" is '
                        'invalid in the filter id="{id}" '
                        '(unknown relation-type ID).'
                    ).format(subfilter=self.sub_filter_id, id=self.efilter_id)
                )

    def build_condition(self):
        return RelationSubFilterConditionHandler.build_condition(
            model=self.model,
            rtype=self.rtype or RelationType.objects.get(id=self.name),
            subfilter=self.sub_filter or EntityFilter.objects.get(id=self.sub_filter_id),
            has=self.has,
        )

    @property
    def filter_dependencies(self):
        # Beware: if the sub_filter already exists, we do use it as dependencies
        #         because it indicates that this sub-filter is not imported
        #         (if we use it, it would cause a DependenciesLoopError)
        return [self.sub_filter_id] if self.sub_filter is None else []

    # TODO: factorise
    def post_validate(self, validated_data):
        sub_filter_id = self.sub_filter_id
        sub_filter = None

        if sub_filter_id not in validated_data[EntityFilter]:
            sub_filter = EntityFilter.objects.filter(id=sub_filter_id).first()

            if sub_filter is None:
                raise ValidationError(
                    _(
                        'The condition on related sub-filter="{subfilter}" is '
                        'invalid in the filter id="{id}" (unknown filter ID).'
                    ).format(subfilter=sub_filter_id, id=self.efilter_id)
                )

        self.sub_filter = sub_filter


@COND_PROXIES
class ConditionProxyProperty(ConditionProxy):
    type_id = PropertyConditionHandler.type_id

    def _validate(self, validated_data):
        self.has = bool(self.value)
        self.ptype = None

        ptype_id = self.name
        if ptype_id not in validated_data[CremePropertyType]:
            self.ptype = ptype = CremePropertyType.objects.filter(id=ptype_id).first()

            if ptype is None:
                raise ValidationError(
                    _(
                        'The condition on property-type="{ptype}" is invalid in '
                        'the filter id="{id}".'
                    ).format(ptype=ptype_id, id=self.efilter_id)
                )

    def build_condition(self):
        return PropertyConditionHandler.build_condition(
            model=self.model,
            ptype=self.ptype or CremePropertyType.objects.get(id=self.name),
            has=self.has,
        )


class BaseConditionProxyCustomField(ConditionProxy):
    type_id = CustomFieldConditionHandler.type_id

    def _validate(self, validated_data):
        cf_id = self.name
        if cf_id not in validated_data[CustomField]:
            # TODO: search in existing Customfield ??
            raise ValidationError(
                _(
                    'The condition on custom-field="{cfield}" is invalid in the '
                    'filter id="{id}".'
                ).format(cfield=cf_id, id=self.efilter_id)
            )


@COND_PROXIES
class ConditionProxyCustomField(BaseConditionProxyCustomField):
    def _validate(self, validated_data):
        value = self.value
        self.operator = value['operator']
        self.values = value['values']

        super(ConditionProxyCustomField, self)._validate(validated_data)

    def build_condition(self):
        return CustomFieldConditionHandler.build_condition(
            custom_field=CustomField.objects.get(uuid=self.name),
            operator=self.operator,
            values=self.values,
        )


@COND_PROXIES
class ConditionProxyDateCustomField(BaseConditionProxyCustomField):
    type_id = DateCustomFieldConditionHandler.type_id

    def build_condition(self):
        value = self.value

        return DateCustomFieldConditionHandler.build_condition(
            custom_field=CustomField.objects.get(uuid=self.name),
            **self._get_date_kwargs(value)
        )


# TODO: factorise with HeaderFiltersImporter
@IMPORTERS.register(data_id=constants.ID_ENTITY_FILTERS)
class EntityFiltersImporter(Importer):
    dependencies = [
        constants.ID_RELATION_TYPES,
        constants.ID_PROPERTY_TYPES,
        constants.ID_CUSTOM_FIELDS,
    ]

    conditions_proxies_registry = COND_PROXIES

    def _validate_section(self, deserialized_section, validated_data):
        User = get_user_model()

        def load_efilter(efilter_info):
            efilter_id = efilter_info['id']

            efilter = EntityFilter.objects.filter(id=efilter_id, is_custom=False).first()
            if efilter is not None:
                raise ValidationError(
                    _('This filter cannot be overridden: «{}».').format(efilter)
                )

            model = load_model(efilter_info['ctype'])
            conditions_proxies = []

            for cond_dict in efilter_info['conditions']:  # TODO: check is a dict ?
                cond_type = cond_dict['type']
                cond_name = cond_dict['name']

                cond_proxy_cls = self.conditions_proxies_registry.get(cond_type)

                if cond_proxy_cls is None:
                    raise ValidationError(
                        _('The condition with type="{type}" is invalid '
                          'in the filter id="{id}".').format(
                            type=cond_type, id=efilter_id,
                        )
                    )
                try:
                    cond_proxy = cond_proxy_cls(
                        efilter_id=efilter_id,
                        model=model,
                        name=cond_name,
                        value=cond_dict.get('value'),
                        validated_data=validated_data,
                    )
                except FilterConditionHandler.ValueError as e:
                    raise ValidationError(
                        _(
                            'A condition is invalid in the filter id="{id}" [{error}].'
                        ).format(
                            id=efilter_id, error=e,
                        )
                    )

                conditions_proxies.append(cond_proxy)

            # TODO: improve errors detection in EntityFilterCondition.error() ?
            #      -  error() need a filter (to get the model)
            #      -  error() do not check all error
            #      VS a map of builders right here
            # if any(cond.error for cond in conditions):
            #     raise ValidationError(
            #       gettext('A column is invalid in the view of list with id="{}".').format(name)
            #     )

            data = {
                'id':         efilter_id,
                'model':      model,
                'filter_type': efilter_info.get('filter_type', EF_USER),
                'name':       str(efilter_info['name']),
                'user':       None,
                'is_private': False,
                'use_or':     efilter_info.get('use_or', False),
                'conditions': conditions_proxies,
            }

            username = efilter_info.get('user')
            if username:
                data['is_private'] = bool(efilter_info.get('is_private', False))

                try:
                    data['user'] = User.objects.get(username=username)
                except User.DoesNotExist:
                    logger.warning(
                        'EntityFiltersImporter: this user does not exist '
                        '(filter is dropped): %s',
                        username,
                    )
                    return None

            return data

        filters_data = [*filter(None, map(load_efilter, deserialized_section))]
        validated_data[EntityFilter].update(d['id'] for d in filters_data)

        for data in filters_data:
            filter_dependencies = []

            for cond_proxy in data['conditions']:
                cond_proxy.post_validate(validated_data)
                filter_dependencies.extend(cond_proxy.filter_dependencies)

            data['deps'] = filter_dependencies

        try:
            self._data = dependence_sort(
                filters_data,
                get_key=lambda filter_data: filter_data['id'],
                get_dependencies=lambda filter_data: filter_data['deps'],
            )
        except DependenciesLoopError as e:
            raise ValidationError(mark_safe(
                _('There is a cycle between the filters [{}].').format(
                    str(e).replace('\n', '<br>'),
                )
            ))

    def save(self):
        # NB: EntityFilter.objects.smart_update_or_create() :
        #      - not OK for system filters
        #      - do not want the latest
        for data in self._data:
            pk = data['id']
            filter_type = data['filter_type']

            if EntityFilter.objects.filter(pk=pk).exists():
                # TODO: test
                raise ValueError(
                    _('The filter with id="{id}" already exists.').format(id=pk)
                )

            ef = EntityFilter.objects.create(
                pk=pk,
                name=data['name'],
                is_custom=True,
                user=data['user'],
                use_or=data['use_or'],
                entity_type=data['model'],
                is_private=data['is_private'],
                filter_type=filter_type,
            )

            conditions = []
            for cond_proxy in data['conditions']:
                cond = cond_proxy.build_condition()
                cond.filter_type = filter_type

                conditions.append(cond)

            ef.set_conditions(conditions)


class CellProxyCustomFormSpecial(CellProxy):
    cell_cls = EntityCellCustomFormSpecial

    def _validate(self, validated_data):
        pass


custom_forms_cells_registry = CellProxiesRegistry()
# TODO: add a method 'register()' ??
custom_forms_cells_registry(CellProxyRegularField)
custom_forms_cells_registry(CellProxyCustomField)
custom_forms_cells_registry(CellProxyCustomFormSpecial)


@IMPORTERS.register(data_id=constants.ID_CUSTOM_FORMS)
class CustomFormsImporter(Importer):
    dependencies = [constants.ID_ROLES, constants.ID_CUSTOM_FIELDS]
    registry = customform_descriptor_registry
    cells_proxies_registry = custom_forms_cells_registry

    # def load_cform_item(self, cform_item_info: dict) -> dict:
    def load_cform_item(self, cform_item_info: dict, validated_data) -> dict:
        data = {}

        # cform_id = cform_item_info.get('id')
        # if cform_id is None:
        #     raise ValidationError('The custom-form ID is missing')
        desc_id = cform_item_info.get('descriptor')
        if desc_id is None:
            raise ValidationError("The custom-form descriptor's ID is missing")

        # desc = self.registry.get(str(cform_id))
        desc = self.registry.get(desc_id)
        if desc is None:
            # raise ValidationError(f'The custom-form ID is invalid: {cform_id}')
            raise ValidationError(f"The custom-form descriptor ID is invalid: {desc_id}")

        data['descriptor'] = desc
        data['superuser'] = bool(cform_item_info.get('superuser'))

        # TODO:
        #    role_name = cform_item_info.get('role', None)
        #    if role_name in validated_data[UserRole]:
        #        data['role_name'] = role_name
        #    else:
        #        data['role'] = UserRole.objects.get(name=role_name)
        data['role_name'] = cform_item_info.get('role', None)

        # data['groups'] = cform_item_info['groups']

        def load_group(group_info):
            if 'cells' in group_info:
                return {
                    **group_info,
                    'cells': self.cells_proxies_registry.build_proxies_from_dicts(
                        model=desc.model,
                        container_label=_('custom-form with id="{id}"').format(id=desc.id),
                        cell_dicts=group_info['cells'],
                        validated_data=validated_data,
                    ),
                }
            else:
                return group_info

        data['groups'] = [load_group(g) for g in cform_item_info['groups']]

        return data

    def _validate_section(self, deserialized_section, validated_data):
        # self._data = [*map(self.load_cform_item, deserialized_section)]
        self._data = [
            self.load_cform_item(
                cform_item_info=item_info, validated_data=validated_data,
            ) for item_info in deserialized_section
        ]

    def save(self):
        # instances = CustomFormConfigItem.objects.in_bulk()
        #
        # def finalize_group_info(group_info):
        #     if 'cells' in group_info:
        #         return {
        #             **group_info,
        #             'cells': [
        #                 cell_proxy.build_cell().to_dict()
        #                 for cell_proxy in group_info['cells']
        #             ],
        #         }
        #     else:
        #         return group_info
        #
        # for data in self._data:
        #     descriptor = data['descriptor']
        #     instance = instances[descriptor.id]
        #     model = descriptor.model
        #     cell_registry = descriptor.build_cell_registry()
        #
        #     instance.store_groups(FieldGroupList(
        #         model=model,
        #         cell_registry=cell_registry,
        #         groups=[
        #             *FieldGroupList.from_dicts(
        #                 model=model,
        #                 data=[finalize_group_info(d) for d in data['groups']],
        #                 cell_registry=cell_registry,
        #                 allowed_extra_group_classes=(*descriptor.extra_group_classes,)
        #             ),
        #         ],
        #     ))
        #     instance.save()
        instances = {
            (cfci.descriptor_id, getattr(cfci.role, 'name', None), cfci.superuser): cfci
            for cfci in CustomFormConfigItem.objects.select_related('role')
        }

        # NB: yes we build cell from dicts a then rebuild dicts ;
        #     it's not optimal but we avoid doing things manually.
        def finalize_group_info(group_info):
            if 'cells' in group_info:
                return {
                    **group_info,
                    'cells': [
                        cell_proxy.build_cell().to_dict()
                        for cell_proxy in group_info['cells']
                    ],
                }
            else:
                return group_info

        for data in self._data:
            # TODO: is this a problem that if instance does not exist there is an error ?
            descriptor = data['descriptor']
            superuser = data['superuser']

            role_name = data.pop('role_name', None)
            if role_name:
                role = UserRole.objects.get(name=role_name)  # TODO: cache
            else:
                role = None

            instance = instances.get((descriptor.id, role_name, superuser))
            if instance is None:
                instance = CustomFormConfigItem(
                    descriptor_id=descriptor.id,
                    superuser=superuser,
                    role=role,
                )

            model = descriptor.model
            cell_registry = descriptor.build_cell_registry()

            instance.store_groups(FieldGroupList(
                model=model,
                cell_registry=cell_registry,
                groups=[
                    *FieldGroupList.from_dicts(
                        model=model,
                        data=[finalize_group_info(d) for d in data['groups']],
                        cell_registry=cell_registry,
                        allowed_extra_group_classes=(*descriptor.extra_group_classes,)
                    ),
                ],
            ))
            instance.save()


@IMPORTERS.register(data_id=constants.ID_RTYPE_BRICKS)
class RelationBrickItemsImporter(Importer):
    # Cells can contain reference to RelationTypes/CustomFields
    dependencies = [constants.ID_RELATION_TYPES, constants.ID_CUSTOM_FIELDS]

    cells_proxies_registry = CELL_PROXIES

    def _validate_section(self, deserialized_section, validated_data):
        def load_ctype_cells(rtype_id, ctype_cells_info):
            ctype = load_ct(ctype_cells_info[0])

            return ctype, self.cells_proxies_registry.build_proxies_from_dicts(
                model=ctype.model_class(),
                container_label=_('block for relation-type id="{id}"').format(id=rtype_id),
                cell_dicts=ctype_cells_info[1],
                validated_data=validated_data,
            )

        self._data = data = []

        for info in deserialized_section:
            rtype_id = info['relation_type']
            data.append({
                'brick_id': info['brick_id'],
                'relation_type_id': rtype_id,
                'cells': [
                    load_ctype_cells(rtype_id, ctype_cells)
                    for ctype_cells in info.get('cells', ())
                ],
            })

    def save(self):
        RelationBrickItem.objects.all().delete()  # TODO: recycle instances

        for data in self._data:
            cell_proxies = data.pop('cells')
            rbi = RelationBrickItem(**data)

            for ctype, ctype_cell_proxies in cell_proxies:
                rbi.set_cells(
                    ctype,
                    [cell_proxy.build_cell() for cell_proxy in ctype_cell_proxies],
                )

            rbi.save()


@IMPORTERS.register(data_id=constants.ID_CUSTOM_BRICKS)
class CustomBrickConfigItemsImporter(Importer):
    # Cells can contain reference to RelationTypes/CustomFields
    dependencies = [constants.ID_RELATION_TYPES, constants.ID_CUSTOM_FIELDS]

    cells_proxies_registry = CELL_PROXIES

    def _validate_section(self, deserialized_section, validated_data):
        self._data = data = []

        for info in deserialized_section:
            cbci_id = info['id']
            ctype = load_ct(info['content_type'])

            data.append({
                'id': cbci_id,
                'name': info['name'],
                'content_type': ctype,
                'cells': self.cells_proxies_registry.build_proxies_from_dicts(
                    model=ctype.model_class(),
                    container_label=_('custom block with id="{id}"').format(id=cbci_id),
                    cell_dicts=info['cells'],
                    validated_data=validated_data,
                )
            })

    def save(self):
        CustomBrickConfigItem.objects.all().delete()  # TODO: recycle instances

        for data in self._data:
            cell_proxies = data.pop('cells')

            CustomBrickConfigItem.objects.create(
                cells=[cell_proxy.build_cell() for cell_proxy in cell_proxies],
                **data,
            )


@IMPORTERS.register(data_id=constants.ID_DETAIL_BRICKS)
class DetailviewBricksLocationsImporter(Importer):
    dependencies = [constants.ID_ROLES]

    def _validate_section(self, deserialized_section, validated_data):
        ZONE_NAMES = BrickDetailviewLocation.ZONE_NAMES

        def validated_zone(zone):
            if zone not in ZONE_NAMES:
                raise ValueError(
                    _('The brick zone «{}» is not valid.').format(zone)
                )

            return zone

        def load_loc(info):
            data = {
                'brick_id': info['id'],
                'order':    int(info['order']),
                'zone':     validated_zone(int(info['zone'])),
            }

            natural_ctype = info.get('ctype')
            if natural_ctype:
                data['content_type'] = load_ct(natural_ctype)

            role_name = info.get('role')
            if role_name:
                if role_name in validated_data[UserRole]:
                    data['role_name'] = role_name
                else:
                    data['role'] = UserRole.objects.get(name=role_name)  # TODO: cache
            elif info.get('superuser'):
                data['superuser'] = True

            return data

        self._data = [*map(load_loc, deserialized_section)]

    def save(self):
        BrickDetailviewLocation.objects.all().delete()  # TODO: recycle instances

        for data in self._data:
            role_name = data.pop('role_name', None)
            if role_name:
                data['role'] = UserRole.objects.get(name=role_name)  # TODO: cache

            BrickDetailviewLocation.objects.create(**data)


# TODO: factorise
@IMPORTERS.register(data_id=constants.ID_HOME_BRICKS)
class HomeBricksLocationsImporter(Importer):
    dependencies = [constants.ID_ROLES]

    def _validate_section(self, deserialized_section, validated_data):
        def load_loc(info):
            data = {
                'brick_id': info['id'],
                'order':    int(info['order']),
            }

            role_name = info.get('role')
            if role_name:
                if role_name in validated_data[UserRole]:
                    data['role_name'] = role_name
                else:
                    data['role'] = UserRole.objects.get(name=role_name)  # TODO: cache
            elif info.get('superuser'):
                data['superuser'] = True

            return data

        self._data = [*map(load_loc, deserialized_section)]

    def save(self):
        BrickHomeLocation.objects.all().delete()  # TODO: recycle instances

        for data in self._data:
            role_name = data.pop('role_name', None)
            if role_name:
                data['role'] = UserRole.objects.get(name=role_name)  # TODO: cache

            BrickHomeLocation.objects.create(**data)


@IMPORTERS.register(data_id=constants.ID_MYPAGE_BRICKS)
class MypageBricksLocationsImporter(Importer):
    def _validate_section(self, deserialized_section, validated_data):
        self._data = [
            {
                'brick_id': loc_info['id'],
                'order':    int(loc_info['order']),
            } for loc_info in deserialized_section
        ]

    def save(self):
        BrickMypageLocation.objects.filter(user=None).delete()  # TODO: recycle instances

        for data in self._data:
            BrickMypageLocation.objects.create(**data)
