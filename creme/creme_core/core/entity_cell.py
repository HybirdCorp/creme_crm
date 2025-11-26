################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2025  Hybird
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
# import warnings
from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import DefaultDict

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models import Field, Model
from django.utils.functional import cached_property
from django.utils.html import escape
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from ..gui.actions import ActionRegistry
from ..gui.view_tag import ViewTag
from ..models import CremeEntity, CustomField, FieldsConfig, RelationType
from ..models import fields as core_fields
from ..utils.collections import ClassKeyedMap
from ..utils.db import populate_related
from ..utils.html import render_limited_list
from ..utils.meta import FieldInfo
from ..utils.unicode_collation import collator
from .field_tags import FieldTag
from .function_field import (
    FunctionField,
    FunctionFieldDecimal,
    FunctionFieldResultsList,
    function_field_registry,
)

# TODO: rename EntityCell to [Model]Cell ?
#       rename 'entity' argument to 'instance'.

logger = logging.getLogger(__name__)
MULTILINE_FIELDS = (
    models.TextField,
    core_fields.UnsafeHTMLField,
    models.ManyToManyField,
)
FIELDS_DATA_TYPES = ClassKeyedMap([
    (models.DateField,            'date'),
    (models.TimeField,            'time'),
    (models.DateTimeField,        'datetime'),

    (models.IntegerField,         'integer'),

    (models.TextField,            'text'),
    (models.EmailField,           'email'),

    (core_fields.PhoneField,      'phone'),
    (core_fields.DurationField,   'duration'),
    (core_fields.DatePeriod,      'period'),
    (core_fields.ColorField,      'color'),
    (core_fields.UnsafeHTMLField, 'html'),
    (core_fields.MoneyField,      'html'),
])


class EntityCell:
    """Represents a value accessor; it's a kind of super field. It can
    retrieve a value stored in entities (of the same type).
    This values can be (see child classes) :
     - regular fields (in the django model way).
     - custom field (see models.CustomField).
     - function fields (see core.FunctionField).
     - other entities linked by a Relation (of a given RelationType).
     - ...
    """
    type_id: str  # Used for register ; overload in child classes (string type)
    verbose_name = '??'

    _listview_css_class = None
    _header_listview_css_class = None

    # TODO: keywords only?
    def __init__(self,
                 model: type[Model],
                 value: str = '',
                 is_hidden: bool = False,
                 is_excluded: bool = False,
                 ):
        """Constructor.

        @param model: Related model.
        @param value: How to access to the instance's data
               (e.g. field's name, custom field's ID...).
        @param is_hidden: Should the cell be visible? Notice that a hidden cell
               will be present in the list-views with a style <display: none;>.
        @param is_excluded: Should the cell be totally ignored.
               (e.g. field hidden by configuration).
               Contrarily to 'is_hidden', the cell won't be present in the
               list-views for example.

        @return: True means <ignore me>.
        """
        self._model = model
        self.value = value
        self.is_hidden = is_hidden
        self.is_excluded = is_excluded

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        return (
            self.type_id == other.type_id
            and self.model == other.model
            and self.value == other.value
            # TODO: compare other fields
        )

    def __repr__(self):
        return (
            f"<EntityCell("
            f"model=<{self.model.__name__}>, "
            f"type='{self.type_id}', "
            f"value='{self.value}'"
            f")>"
        )

    def __str__(self):
        return self.title

    def _get_field_class(self) -> type[Field]:
        return Field

    def _get_listview_css_class(self, attr_name: str):
        from ..gui.field_printers import field_printer_registry

        listview_css_class = getattr(self, attr_name)

        if listview_css_class is None:
            registry_getter = getattr(field_printer_registry, f'get{attr_name}_for_field')
            listview_css_class = registry_getter(self._get_field_class())
            setattr(self, attr_name, listview_css_class)

        return listview_css_class

    @classmethod
    def build(cls, model: type[Model], name: str) -> EntityCell | None:
        """Abstract helper method to build an EntityCell instance.

        @param model: Class inheriting <CremeEntity>.
        @param name: String containing an ID/UUID/name... (depending on the type of cell).
        @return: An instance of EntityCell, or None (if an error occurred).
        """
        raise NotImplementedError

    @property
    def data_type(self) -> str | None:
        return FIELDS_DATA_TYPES[self._get_field_class()]

    @property
    def model(self) -> type[Model]:
        return self._model

    @property
    def key(self) -> str:
        "Return an ID that should be unique in a EntityCell set."
        return f'{self.type_id}-{self.value}'

    @property
    def portable_key(self) -> str:
        """Return an ID that should be unique in a EntityCell set.
        This is the 'portable' (see to_dict() documentation) version of key.
        """
        return f'{self.type_id}-{self.portable_value}'

    @property
    def listview_css_class(self) -> str:
        return self._get_listview_css_class('_listview_css_class')

    @property
    def header_listview_css_class(self) -> str:
        return self._get_listview_css_class('_header_listview_css_class')

    @property
    def is_multiline(self) -> bool:
        return issubclass(self._get_field_class(), MULTILINE_FIELDS)

    @staticmethod
    def mixed_populate_entities(cells: Iterable[EntityCell],
                                entities: Sequence[CremeEntity],
                                user,
                                ) -> None:
        """Fill caches of CremeEntity objects with grouped SQL queries, & so
        avoid multiple queries when rendering the cells.
        The given cells are grouped by types, and then the method
        'populate_entities()' of each used type is called.
        @param cells: Instances of (subclasses of) EntityCell.
        @param entities: Instances of CremeEntities (or subclass).
        @param user: Instance of <contrib.auth.get_user_model()>.
        """
        cell_groups: DefaultDict[type[EntityCell], list[EntityCell]] = defaultdict(list)

        for cell in cells:
            cell_groups[cell.__class__].append(cell)

        for cell_cls, cell_group in cell_groups.items():
            cell_cls.populate_entities(cell_group, entities, user)

    @staticmethod
    def populate_entities(cells: Iterable[EntityCell],
                          entities: Sequence[CremeEntity],
                          user,
                          ) -> None:
        """Fill caches of CremeEntity objects with grouped SQL queries, & so
        avoid multiple queries when rendering the cells.
        The given cells MUST HAVE THE SAME TYPE (corresponding to the class
        the method belongs).
        @param cells: Instances of (subclasses of) EntityCell.
        @param entities: Instances of CremeEntities (or subclass).
        @param user: Instance of <contrib.auth.get_user_model()>.
        """
        pass

    def render(self, entity: CremeEntity, user, tag: ViewTag) -> str:
        raise NotImplementedError

    @property
    def description(self) -> str:
        return ''

    @property
    def title(self) -> str:
        raise NotImplementedError

    @property
    def portable_value(self) -> str:
        return self.value

    def to_dict(self, portable=False) -> dict:
        """Get a JSONifiable dictionary representation of the cell.
        This dict can be given to <EntityCellsRegistry.build_cell_from_dict()>
        (see "dict_cell" argument).

        @param portable: If True, the value can be "easily" imported in another DB
               (Creme will try to use this format for data stored in DB).
               If False, the data could be local only (but shorter).
               E.g. for CustomFields, UUID will be used in portable mode,
               & ID in the other case.
        @return: A dictionary indicating the type & the value of the cell.
        """
        return {
            'type': self.type_id,
            'value': self.portable_value if portable else self.value,
        }


class EntityCellRegistry:
    __slots__ = ('_cell_classes', )

    class RegistrationError(Exception):
        pass

    def __init__(self) -> None:
        self._cell_classes: dict[str, type[EntityCell]] = {}

    def __call__(self, cls: type[EntityCell]):
        self.register(cls)

        return cls

    def __contains__(self, type_id: str):
        return type_id in self._cell_classes

    def __getitem__(self, type_id: str):
        return self._cell_classes[type_id]

    def _build_cell(self, model: type[Model], type_id: str, value: str) -> EntityCell | None:
        cls = self._cell_classes.get(type_id)
        if cls is None:
            logger.exception(
                'EntityCellsRegistry._build_cell(): unknown type_id="%s"',
                type_id,
            )
            return None

        return cls.build(model, value)

    def build_cell_from_dict(self, model: type[Model], dict_cell: dict) -> EntityCell | None:
        try:
            type_id = dict_cell['type']
            value = dict_cell['value']
        except KeyError:
            logger.exception(
                'EntityCellsRegistry.build_cell_from_dict(): data=%s',
                dict_cell,
            )
            return None

        return self._build_cell(model=model, type_id=type_id, value=value)

    def build_cells_from_dicts(self,
                               model: type[Model],
                               dicts: Iterable[dict],
                               ) -> tuple[list[EntityCell], bool]:
        """Build some EntityCells instance from an iterable of dictionaries.

        @param model: Class inheriting <django.db.model.Model> related to the cells.
        @param dicts: Iterable of dictionaries ; see 'EntityCell.to_dict()'.
        @return: tuple(list_of_cells, errors) ; 'errors' is a boolean.
        """
        cells = []
        errors = False

        try:
            for dict_cell in dicts:
                cell = self.build_cell_from_dict(model, dict_cell)

                if cell is not None:
                    cells.append(cell)
                else:
                    errors = True
        except Exception:
            logger.exception(
                'EntityCellsRegistry.build_cells_from_dicts(): all data=%s',
                dicts
            )
            errors = True

        return cells, errors

    def build_cell_from_key(self, model: type[Model], key: str) -> EntityCell | None:
        try:
            type_id, value = key.split('-', 1)
        except ValueError:
            logger.exception(
                'EntityCellsRegistry.build_cell_from_key(): data=%s',
                key,
            )
            return None

        return self._build_cell(model=model, type_id=type_id, value=value)

    def build_cells_from_keys(self,
                              model: type[Model],
                              keys: Iterable[str],
                              ) -> tuple[list[EntityCell], bool]:
        """Build some EntityCells instance from an iterable of keys (strings).

        @param model: Class inheriting <django.db.model.Model> related to the cells.
        @param keys: Iterable of strings ; see 'EntityCell.key'.
        @return: tuple(list_of_cells, errors) ; 'errors' is a boolean.
        """
        cells = []
        errors = False

        for key in keys:
            cell = self.build_cell_from_key(model, key)

            if cell is not None:
                cells.append(cell)
            else:
                errors = True

        return cells, errors

    @property
    def cell_classes(self):
        return iter(self._cell_classes.values())

    def register(self, *cell_classes: type[EntityCell]):
        store = self._cell_classes.setdefault

        for cls in cell_classes:
            if store(cls.type_id, cls) is not cls:
                raise self.RegistrationError(f'Duplicated Cell id: {cls.type_id}')

        return self


CELLS_MAP = EntityCellRegistry()


# def __getattr__(name):
#     if name == 'EntityCellsRegistry':
#         warnings.warn(
#             '"EntityCellsRegistry" is deprecated; use "EntityCellRegistry" instead.',
#             DeprecationWarning,
#         )
#         return EntityCellRegistry
#
#     raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# @CELLS_MAP TODO
class EntityCellActions(EntityCell):
    type_id = 'actions'
    verbose_name = _('Actions')

    # def __init__(self, model, actions_registry):
    def __init__(self, model, action_registry: ActionRegistry):
        """Constructor.

        @param model: see <EntityCell.model>.
        @param action_registry: Instance of 'creme.creme_core.gui.actions.ActionRegistry'.
               Used to get the actions related to the model.
        """
        super().__init__(model=model, value='entity_actions')
        # self.registry = actions_registry
        self.registry = action_registry

    def _sort_actions(self, actions):
        collator_key = collator.sort_key
        actions.sort(key=lambda a: (not a.is_default, collator_key(a.label)))

        return actions

    def bulk_actions(self, user):
        """Get a sorted list of the visible <gui.actions.BulkAction> instances
        corresponding to the registered bulk actions (see 'registry' attribute).

        @param user: User who displays this page (used to compute credentials).
               Instance of 'django.contrib.auth.get_user_model()'.
        @return: A list of instances of 'gui.actions.BulkActions'.
        """
        # TODO: filter by is_visible in actions_registry.bulk_actions() ??
        return self._sort_actions([
            action
            for action in self.registry.bulk_actions(user=user, model=self.model)
            if action.is_visible
        ])

    def instance_actions(self, instance: Model, user):
        """Get a sorted list of the visible <gui.actions.UIAction> instances
        corresponding to the registered instance actions (see 'registry' attribute).

        @param instance: Should be an instance of 'self.model'.
        @param user: User who displays this page (used to compute credentials).
               Instance of 'django.contrib.auth.get_user_model()'.
        @return: A list of instances of 'gui.actions.UIActions'.
        """
        # TODO: filter by is_visible in actions_registry.instance_actions() ??
        return self._sort_actions([
            action
            for action in self.registry.instance_actions(user=user, instance=instance)
            if action.is_visible
        ])

    def render(self, entity: CremeEntity, user, tag):
        return ''

    @cached_property
    def title(self):
        return gettext('Actions')


@CELLS_MAP
class EntityCellRegularField(EntityCell):
    type_id = 'regular_field'
    verbose_name = _('Fields')

    def __init__(self, model, name, field_info: FieldInfo, is_hidden=False):
        "Use build() instead of using this constructor directly."
        self._field_info = field_info
        self._printers = {}

        super().__init__(
            model=model,
            value=name,
            is_hidden=is_hidden,
            is_excluded=(
                not all(field.get_tag(FieldTag.VIEWABLE) for field in field_info)
                or FieldsConfig.LocalCache().is_fieldinfo_hidden(field_info)
            ),
        )

    @classmethod
    def build(cls,
              model: type[Model],
              name: str,
              *,
              is_hidden: bool = False,
              ) -> EntityCellRegularField | None:
        """Helper method to build an EntityCellRegularField instance.

        @param model: Class inheriting <django.db.models.Model>.
        @param name: String representing a 'chain' of fields, e.g. 'book__author__name'.
        @param is_hidden: See EntityCell.is_hidden.
        @return: An instance of EntityCellRegularField, or None (if an error occurred).
        """
        try:
            field_info = FieldInfo(model, name)
        except FieldDoesNotExist as e:
            logger.warning(
                'EntityCellRegularField(): problem with field "%s" ("%s")',
                name, e,
            )
            return None

        return cls(model=model, name=name, field_info=field_info, is_hidden=is_hidden)

    @property
    def field_info(self) -> FieldInfo:
        """ Getter for attribute 'field_info'.

        @return: An instance of creme_core.utils.meta.FieldInfo.
        """
        return self._field_info

    @property
    def is_multiline(self):
        return any(isinstance(f, MULTILINE_FIELDS) for f in self._field_info)

    def _get_field_class(self):
        return self._field_info[-1].__class__

    @staticmethod
    def populate_entities(cells, entities, user):
        populate_related(entities, [cell.value for cell in cells])

    def render(self, entity, user, tag):
        printer = self._printers.get(tag)

        if printer is None:
            # TODO: pass the 'field_printers_registry' in a context dict when
            #       building our instance? (see EntityCellFunctionField too)
            from ..gui.field_printers import field_printer_registry

            self._printers[tag] = printer = field_printer_registry.build_field_printer(
                model=entity.__class__,
                field_name=self.value,
                tag=tag,
            )

        return printer(entity, user)

    @property
    def description(self):
        return str(self._field_info[-1].help_text)

    @cached_property
    def title(self):
        return (
            str(self._field_info.verbose_name)
            if not self.is_excluded else
            gettext('{} [hidden]').format(self._field_info.verbose_name)
        )


@CELLS_MAP
class EntityCellCustomField(EntityCell):
    type_id = 'custom_field'
    verbose_name = _('Custom fields')

    @staticmethod
    def _multi_enum_html(entity, cf_value, user, cfield):
        return render_limited_list(
            items=[] if cf_value is None else cf_value.get_enumvalues(),
            limit=settings.CELL_SIZE,
        )

    _HTML_EXTRA_RENDERER = {
        CustomField.ENUM:
            lambda entity, cf_value, user, cfield:
            escape(cf_value) if cf_value is not None else '',
        CustomField.MULTI_ENUM:
            _multi_enum_html.__func__,
    }
    _EXTRA_RENDERERS = {
        ViewTag.HTML_DETAIL: _HTML_EXTRA_RENDERER.copy(),
        ViewTag.HTML_LIST:   _HTML_EXTRA_RENDERER.copy(),
        ViewTag.HTML_FORM:   _HTML_EXTRA_RENDERER.copy(),

        ViewTag.TEXT_PLAIN: {
            CustomField.ENUM:
                lambda entity, cf_value, user, cfield:
                str(cf_value) if cf_value is not None else '',
            CustomField.MULTI_ENUM:
                lambda entity, cf_value, user, cfield:
                ' / '.join(str(val) for val in cf_value.get_enumvalues())
                if cf_value is not None else '',
        },
    }

    def __init__(self, customfield: CustomField):
        self._customfield = customfield

        super().__init__(
            model=customfield.content_type.model_class(),
            value=str(customfield.id),
            is_hidden=False,
            is_excluded=customfield.is_deleted,
        )

        self._printers = {}

    @classmethod
    def build(cls, model: type[Model], name: str) -> EntityCellCustomField | None:
        """Helper method to build an EntityCellCustomField instance.

        @param model: Class inheriting <CremeEntity>.
        @param name: String containing the ID, or the UUID, of a CustomField instance.
        @return: An instance of EntityCellCustomField, or None (if an error occurred).
        """
        cfield = None
        cfields = CustomField.objects.get_for_model(model)

        # NB: we prefer use the cache with all model's CustomFields because of
        #     high probability to use several CustomFields in the same request.

        # if isinstance(name, int):
        #     warnings.warn(
        #         'EntityCellCustomField.build() with integer value is deprecated; '
        #         'pass a string (ID ou UUID) instead.',
        #         DeprecationWarning
        #     )
        #     cfield = cfields.get(name)
        # elif name.isdigit():
        if name.isdigit():
            cfield = cfields.get(int(name))
        else:
            for cf in cfields.values():
                if str(cf.uuid) == name:
                    cfield = cf
                    break

        if cfield is None:
            logger.warning(
                'EntityCellCustomField: custom field (uu)id="%s" (on model %s) does not exist',
                name, model,
            )
            return None

        return cls(cfield)

    @property
    def custom_field(self) -> CustomField:
        return self._customfield

    def _get_field_class(self):
        return type(self._customfield.value_class._meta.get_field('value'))

    @property
    def portable_value(self):
        return str(self._customfield.uuid)

    def render(self, entity, user, tag):
        printer = self._printers.get(tag)

        if printer is None:
            cfield = self.custom_field

            renderer = self._EXTRA_RENDERERS.get(tag).get(cfield.field_type)
            if renderer is not None:
                def printer(entity, user):
                    cf_value = entity.get_custom_value(cfield)
                    return renderer(entity, cf_value, user, cfield)
            else:
                # TODO: see EntityCellRegularField for remark on registry
                from ..gui.field_printers import field_printer_registry

                field_cls = self._get_field_class()
                regular_printer = next(
                    field_printer_registry.printers_for_field_type(type=field_cls, tags=tag)
                )
                regular_field = field_cls()

                def printer(entity, user):
                    cf_value = entity.get_custom_value(cfield)

                    return regular_printer(
                        instance=entity,
                        value=cf_value.value,
                        user=user,
                        field=regular_field,  # <== HACK
                    ) if cf_value is not None else ''

            self._printers[tag] = printer

        return printer(entity, user)

    @staticmethod
    def populate_entities(cells, entities, user):
        CremeEntity.populate_custom_values(
            entities,
            [cell.custom_field for cell in cells],
        )  # NB: not itervalues()

    @property
    def description(self):
        return self._customfield.description

    @cached_property
    def title(self):
        return (
            gettext('{} [deleted]').format(self._customfield.name)
            if self.is_excluded else
            self._customfield.name
        )


# TODO: add an attribute FunctionField.description & use it?
@CELLS_MAP
class EntityCellFunctionField(EntityCell):
    type_id = 'function_field'
    verbose_name = _('Computed fields')

    _FUNFIELD_CSS = {  # TODO: ClassKeyedMap ?
        FunctionFieldDecimal: models.DecimalField,
    }
    field_registry = function_field_registry

    def __init__(self, model, func_field: FunctionField):
        self._functionfield = func_field

        super().__init__(
            model=model,
            value=func_field.name,
            is_hidden=func_field.is_hidden,
        )

    @classmethod
    def build(cls,
              model: type[Model],
              # func_field_name: str,
              name: str,
              ) -> EntityCellFunctionField | None:
        """Helper method to build an EntityCellFunctionField instance.

        @param model: Class inheriting <CremeEntity>.
        @param name: Name of a FunctionField class (i.e. string used to register it).
        @return: An instance of EntityCellFunctionField, or None (if an error occurred).
        """
        func_field = cls.field_registry.get(model=model, name=name)

        if func_field is None:
            logger.warning(
                'EntityCellFunctionField: function field "%s" does not exist',
                name,
            )
            return None

        return cls(model=model, func_field=func_field)

    @property
    def function_field(self) -> FunctionField:
        return self._functionfield

    def _get_field_class(self):
        return self._FUNFIELD_CSS.get(self._functionfield.result_type, Field)

    @property
    def is_multiline(self):
        return issubclass(self._functionfield.result_type, FunctionFieldResultsList)

    @staticmethod
    def populate_entities(cells, entities, user):
        for cell in cells:
            cell.function_field.populate_entities(entities, user)

    def render(self, entity, user, tag):
        return self.function_field(entity, user).render(tag)

    @cached_property
    def title(self):
        return str(self._functionfield.verbose_name)


@CELLS_MAP
class EntityCellRelation(EntityCell):
    type_id = 'relation'
    verbose_name = _('Relationships')

    def __init__(self,
                 model: type[Model],
                 rtype: RelationType,
                 is_hidden: bool = False,
                 ):
        self._rtype = rtype
        super().__init__(
            model=model,
            value=str(rtype.id),
            is_hidden=is_hidden,
            is_excluded=(not rtype.enabled),
        )

    @classmethod
    def build(cls,
              model: type[Model],
              name: str,
              *,
              is_hidden: bool = False,
              ) -> EntityCellRelation | None:
        """Helper method to build an EntityCellRelation instance.

        @param model: Class inheriting <CremeEntity>.
        @param value: ID of a RelationType instance.
        @param: hidden: See EntityCell.is_hidden.
        @return: An instance of EntityCellRelation, or None (if an error occurred).
        """
        try:
            rtype = RelationType.objects.get(pk=name)
        except RelationType.DoesNotExist:
            logger.warning(
                'EntityCellRelation: relation type "%s" does not exist',
                name,
            )
            return None

        return cls(model=model, rtype=rtype, is_hidden=is_hidden)

    @property
    def is_multiline(self):
        return True

    @property
    def relation_type(self) -> RelationType:
        return self._rtype

    @staticmethod
    def populate_entities(cells, entities, user):
        CremeEntity.populate_relations(
            entities,
            [cell.relation_type.id for cell in cells]
        )

    def render(self, entity, user, tag):
        if tag in {ViewTag.HTML_DETAIL, ViewTag.HTML_LIST, ViewTag.HTML_FORM}:
            from ..templatetags.creme_widgets import widget_entity_hyperlink

            related_entities = entity.get_related_entities(self.value, True)
            a_target = '_blank' if tag == ViewTag.HTML_FORM else '_self'

            sort_key = collator.sort_key
            related_entities.sort(key=lambda e: sort_key(str(e)))

            # NB: about limiting the number of results
            #     It would be probably better to limit the number of elements in the SQL query
            #     (notice we would not have the exact count anymore) but as we often prefetch
            #     things to group queries it would not be easy & force us to break some APIs.
            #     Limiting the size of the rendered HTML is not optimal but should be enough
            #     in the general case to avoid the biggest issues (<ul>s with several thousand
            #     of <li>s which annoy the browsers).
            #     This is true with other uses of 'render_limited_list()' (like M2M,
            #     FunctionFieldResult...).
            return render_limited_list(
                items=related_entities,
                limit=settings.CELL_SIZE,
                render_item=lambda e: widget_entity_hyperlink(e, user, target=a_target),
            )
        else:
            has_perm = user.has_perm_to_view
            return '/'.join(sorted(
                (
                    str(o)
                    for o in entity.get_related_entities(self.value, True)
                    if has_perm(o)
                ),
                key=collator.sort_key,
            ))

    @property
    def title(self):
        return (
            gettext('{} [disabled]').format(self._rtype.predicate)
            if self.is_excluded else
            self._rtype.predicate
        )


class EntityCellVolatile(EntityCell):
    """Base class for cells added on-the-go, which are not configured & do not
    correspond to any previous type.
    """
    type_id = 'volatile'
