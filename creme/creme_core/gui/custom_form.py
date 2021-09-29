# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020-2021  Hybird
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
from abc import ABC
from collections import OrderedDict
from copy import deepcopy
from itertools import chain
from typing import (
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

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Model
from django.forms.models import modelform_factory
from django.utils.translation import gettext_lazy as _

from ..core.entity_cell import (
    EntityCell,
    EntityCellCustomField,
    EntityCellRegularField,
    EntityCellsRegistry,
)
from ..forms.base import (
    LAYOUT_REGULAR,
    LAYOUTS,
    CremeEntityForm,
    FieldBlockManager,
    LayoutType,
)
from ..models import (
    CremeEntity,
    CustomField,
    CustomFormConfigItem,
    FieldsConfig,
)
from ..utils.collections import OrderedSet

logger = logging.getLogger(__name__)


# Cells ------------------------------------------------------------------------
class EntityCellCustomFormSpecial(EntityCell):
    type_id = 'cform_special'

    REMAINING_REGULARFIELDS = 'regularfields'
    REMAINING_CUSTOMFIELDS = 'customfields'
    RELATIONS = 'relations'
    CREME_PROPERTIES = 'properties'

    ALLOWED = OrderedDict([
        (REMAINING_REGULARFIELDS, _('*Remaining regular fields*')),
        (REMAINING_CUSTOMFIELDS,  _('*Remaining custom fields*')),
        (RELATIONS,               _('*Relationships*')),
        (CREME_PROPERTIES,        _('Properties')),
    ])

    def __init__(self, model, name):
        super().__init__(model=model, value=name)

    @classmethod
    def build(cls, model, name):
        if name not in cls.ALLOWED:
            logger.warning(
                'EntityCellCustomFormSpecial.build(): invalid name "%s"', name,
            )

            return None

        return cls(model=model, name=name)

    def render_html(self, entity, user):
        return ''

    def render_csv(self, entity, user):
        return ''

    @property
    def title(self):
        return str(self.ALLOWED.get(self.value, '??'))


base_cell_registry = EntityCellsRegistry().register(
    EntityCellRegularField,
    EntityCellCustomField,
    EntityCellCustomFormSpecial,
)


class CustomFormExtraSubCell:
    """When you want to add form-fields with a specific behaviour in a
    custom-form, the simplest way is to create a child class of
    CustomFormExtraSubCell.
    See CustomFormDescriptor.extra_sub_cells.
    """
    # Unique ID (within a EntityCellCustomFormExtra).
    # Override this in child classes.
    sub_type_id = ''
    # Label used in configuration UI.
    # Tips: you can use it in your formfield() method as label's value.
    verbose_name = '??'

    # Is the related form-field required
    # (eg: for the config to warn about missing required field).
    # NB: we do not use <formfield(...).required> to avoid potential heavy
    #     computing (SQL query to initialize) for a field which could be dropped.
    is_required = True

    def __init__(self, model: Type[Model]):
        self.model = model

    def __eq__(self, other):
        return (
            self.sub_type_id == other.sub_type_id
            and self.model == other.model
        )

    def formfield(self, instance: Model, user, **kwargs) -> forms.Field:
        raise NotImplementedError

    def into_cell(self) -> EntityCell:
        "Helper method for 'populate.py' scripts when creating CustomFormConfigItem."
        return EntityCellCustomFormExtra(sub_cell=self)

    def post_clean_instance(self, *,
                            instance: Model,
                            value,
                            form: CremeEntityForm) -> None:
        """This methods is called by the generated form after the instance has been cleaned.
        @raise ValidationError.
        """
        pass

    def post_save_instance(self, *,
                           instance: Model,
                           value,
                           form: CremeEntityForm) -> bool:
        """This methods is called by the generated form after the instance has been saved.
        @return: A boolean indicating if the instance should be saved again.
        """
        return False


class EntityCellCustomFormExtra(EntityCell):
    """Type of cells which wraps all the CustomFormExtraSubCell of a
    CustomFormDescriptor.
    You probably do not have to create one by hand.
    """
    type_id = 'cform_extra'
    allowed_sub_cell_classes: Sequence[Type[CustomFormExtraSubCell]] = ()

    def __init__(self, sub_cell: CustomFormExtraSubCell):
        super().__init__(model=sub_cell.model, value=sub_cell.sub_type_id)
        self.sub_cell = sub_cell

    @classmethod
    def build(cls, model, name):
        for sub_cell_cls in cls.allowed_sub_cell_classes:
            if sub_cell_cls.sub_type_id == name:
                return cls(sub_cell_cls(model=model))

        logger.warning(
            'CustomFormExtraEntityCell.build(): no sub-cell found for <model=%s name="%s"> '
            '(available: %s)',
            model, name, cls.allowed_sub_cell_classes,
        )

        return None

    def formfield(self, instance, user):
        sub_cell = self.sub_cell
        return sub_cell.formfield(instance, user=user, required=sub_cell.is_required)

    def render_html(self, entity, user):
        return ''

    def render_csv(self, entity, user):
        return ''

    @property
    def title(self):
        return str(self.sub_cell.verbose_name)


# Groups -----------------------------------------------------------------------

class AbstractFieldGroup:
    """Base class to describe group of field in a custom-form."""
    template_name: Optional[str] = None

    def __init__(self, layout: Optional[LayoutType] = None):
        self._layout = layout or LAYOUT_REGULAR

    def as_dict(self) -> dict:
        raise NotImplementedError

    def get_context(self) -> dict:
        return {}

    @property
    def layout(self) -> LayoutType:
        return self._layout

    @property
    def name(self) -> str:
        raise NotImplementedError


class ExtraFieldGroup(ABC, AbstractFieldGroup):
    """Base class to create hard coded group of fields with specific behaviour
    (ie: users cannot configure the fields).
    See <CustomFormDescriptor.extra_group_classes>.

    Hint: you should probably avoid this way & use CustomFormExtraSubCell if
          it's possible (because the users can configure them).
    Hint: the app "persons" use ExtraFieldGroup for the bloc "Addresses".
    """
    # Unique ID (within a CustomFormDescriptor) ; override in child classes
    # Hint: use a string in the form 'my_app-group_name'
    extra_group_id = ''
    name = 'PLACE HOLDER'
    # TODO: is_required ?

    def __init__(self, model: Type[Model], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._model = model

    def as_dict(self):
        group_id = self.extra_group_id
        if not group_id:
            raise ValueError(f'{type(self).__name__}.group_id is empty.')

        data = {'group_id': group_id}
        layout = self.layout
        if layout != LAYOUT_REGULAR:
            data['layout'] = layout

        return data

    def clean(self, form: CremeEntityForm) -> None:
        """This method is called by the generated form after the instance has been cleaned."""
        pass

    def formfields(self, instance: CremeEntity, user) -> Iterator[forms.Field]:
        yield from ()

    @property
    def model(self):
        return self._model

    def save(self, form: CremeEntityForm) -> bool:
        """This method is called by the generated form after the instance has been saved.
        @return: A boolean indicated if the instance should be saved again.
        """
        return False


class FieldGroup(AbstractFieldGroup):
    """Field-group which stores fields as EntityCells."""
    def __init__(self,
                 name: str,
                 cells: Iterable[EntityCell],
                 *args, **kwargs
                 ):
        super().__init__(*args, **kwargs)
        self._name = name
        self._cells = [*cells]

    def __repr__(self):
        return (
            f'{type(self).__name__}('
            f'name="{self._name}", '
            f'cells={self._cells}, '
            f'layout="{self._layout}"'
            f')'
        )

    def as_dict(self) -> dict:
        return {
            'name': self._name,
            'layout': self._layout,
            'cells': [cell.to_dict() for cell in self._cells],
        }

    @property
    def cells(self) -> Iterator[EntityCell]:
        yield from self._cells

    @property
    def name(self) -> str:
        return self._name


class FieldGroupList:
    """Sequence of AbstractFieldGroups."""
    BLOCK_ID_MISSING_FIELD = 'missing_required'
    BLOCK_ID_MISSING_CUSTOM_FIELD = 'missing_custom_required'
    BLOCK_ID_MISSING_EXTRA_FIELD = 'missing_extra_required'

    error_block_labels = {
        BLOCK_ID_MISSING_FIELD: _(
            'Missing required fields (update your configuration)'
        ),
        BLOCK_ID_MISSING_CUSTOM_FIELD: _(
            'Missing required custom fields (update your configuration)'
        ),
        BLOCK_ID_MISSING_EXTRA_FIELD: _(
            'Missing required special fields (update your configuration)'
        ),
    }

    def __init__(self,
                 model: Type[Model],
                 groups: Iterable[AbstractFieldGroup],
                 cell_registry: EntityCellsRegistry,
                 ):
        self._model = model
        self._groups = [*groups]
        self._cell_registry = cell_registry

    def __len__(self):
        return len(self._groups)

    def __getitem__(self, item: int) -> AbstractFieldGroup:
        return self._groups[item]

    def __iter__(self) -> Iterator[AbstractFieldGroup]:
        yield from self._groups

    def __repr__(self):
        return (
            f'{type(self).__name__}('
            f'model={self._model.__name__}, '
            f'groups={self._groups}'
            f')'
        )

    @property
    def cell_registry(self) -> EntityCellsRegistry:
        return self._cell_registry

    @property
    def model(self) -> Type[Model]:
        return self._model

    @classmethod
    def from_cells(cls,
                   model: Type[Model],
                   data: List[Union[dict, ExtraFieldGroup]],
                   cell_registry: EntityCellsRegistry,
                   allowed_extra_group_classes: Iterable[Type[ExtraFieldGroup]] = (),
                   ) -> 'FieldGroupList':
        """High level builder of FieldGroupList and contained AbstractFieldGroups.
        @param model: related model (hint: EntityCells use it).
        @param data: list of dicts or ExtraFieldGroups. The format of the dicts:
               - key "name" => string value (name of the group).
               - key "cells" => list of EntityCells, or tuples
                 (cell_class, arguments_dict_to_build_method)
                 Notice: you do not have to give "model" in <argument_dict_to_build_method>.
               - key "layout" (optional) => see <creme_core.forms.base.LAYOUTS>.
        @param cell_registry: use to pass accepted EntityCell classes.
        @param allowed_extra_group_classes: use to pass accepted ExtraFieldGroup classes.
        """
        def get_layout(desc):
            layout = desc.get('layout')

            if not layout:
                return None

            if layout not in LAYOUTS:
                logger.warning(
                    'FieldGroupList.from_cells(): '
                    'invalid layout "%s" (available: %s)',
                    layout, LAYOUTS,
                )
                return None

            return layout

        allowed_group_classes = tuple(allowed_extra_group_classes)

        def iter_group():
            for group_desc in data:
                if isinstance(group_desc, ExtraFieldGroup):
                    if not isinstance(group_desc, allowed_group_classes):
                        logger.warning(
                            'FieldGroupList.from_cells(): '
                            'invalid group class "%s" (available: [%s])',
                            type(group_desc).__name__,
                            ', '.join(c.__name__ for c in allowed_group_classes),
                        )
                    else:
                        yield group_desc
                else:
                    # TODO: factorise with HeaderFilterManager ?
                    cells = []

                    for cell_desc in group_desc['cells']:
                        if cell_desc is None:
                            continue

                        if isinstance(cell_desc, EntityCell):
                            cells.append(cell_desc)
                        else:
                            cell = cell_desc[0].build(model=model, **cell_desc[1])

                            if cell is not None:
                                cells.append(cell)

                    yield FieldGroup(
                        name=group_desc['name'],
                        cells=cells,
                        layout=get_layout(group_desc),
                    )

        return cls(model=model, groups=iter_group(), cell_registry=cell_registry)

    @classmethod
    def from_dicts(cls,
                   model: Type[Model],
                   data: List[dict],
                   cell_registry: EntityCellsRegistry,
                   allowed_extra_group_classes: Sequence[Type[ExtraFieldGroup]] = (),
                   ) -> 'FieldGroupList':
        """Builder of FieldGroupList and contained AbstractFieldGroups
        from de-serialized dicts.
        Hint: see as_dict() methods for ExtraFieldGroup/FieldGroup.
        """
        def iter_group():
            for group_data in data:
                if 'group_id' in group_data:
                    group_id = group_data['group_id']

                    for group_class in allowed_extra_group_classes:
                        if group_id == group_class.extra_group_id:
                            yield group_class(
                                model=model,
                                layout=group_data.get('layout'),
                            )
                            break
                    else:
                        logger.warning(
                            'FieldGroupList.from_dicts(): '
                            'invalid data (not allowed group ID "%s").',
                            group_id,
                        )
                else:
                    try:
                        cells = cell_registry.build_cells_from_dicts(
                            model=model,
                            dicts=group_data['cells'],
                        )[0]
                        name = group_data['name']
                        layout = group_data['layout']
                    except TypeError as e:
                        logger.warning(
                            'FieldGroupList.from_dicts(): '
                            'invalid data ("%s").',
                            e,
                        )
                    except KeyError as e:
                        logger.warning(
                            '%s.from_dicts(): invalid data (missing key "%s").',
                            cls.__name__, e,
                        )
                    else:
                        yield FieldGroup(name=name, layout=layout, cells=cells)

        return cls(model=model, groups=iter_group(), cell_registry=cell_registry)

    def form_class(self, *,
                   base_form_class=CremeEntityForm,
                   exclude_fields: Container[str] = (),
                   ) -> Type[CremeEntityForm]:
        """Main method of the custom-form system: it generate our final form class."""
        model = self.model

        cells_groups: List[FieldGroup] = []
        extra_groups: List[ExtraFieldGroup] = []
        for group in self._groups:
            if isinstance(group, ExtraFieldGroup):
                extra_groups.append(group)
            else:
                assert isinstance(group, FieldGroup)
                cells_groups.append(group)

        field_names = OrderedSet()

        for group in cells_groups:
            for cell in group.cells:
                if isinstance(cell, EntityCellRegularField):
                    field_info = cell.field_info

                    if not field_info[-1].editable:
                        logger.warning(
                            'A not editable field is used by the configuration '
                            '& will be ignored: %s', cell.value,
                        )
                    elif len(field_info) > 1:
                        logger.warning(
                            'A deep field is used by the configuration '
                            '& will be ignored: %s', cell.value,
                        )
                    else:
                        field_names.add(cell.value)

        if any(
            cell.value == EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS
            for group in cells_groups
            for cell in group.cells
            if isinstance(cell, EntityCellCustomFormSpecial)
        ):
            remaining_field_names = [
                field.name
                for field in chain(model._meta.fields, model._meta.many_to_many)
                if (
                    field.editable
                    and not field.auto_created
                    and field.name not in field_names
                    and field.name not in exclude_fields
                )
            ]
            forced_field_names = []
        else:
            is_field_required = FieldsConfig.objects.get_for_model(model).is_field_required

            remaining_field_names = []
            forced_field_names = [
                field.name
                for field in model._meta.fields
                if (
                    field.editable
                    and not field.auto_created
                    # and not field.blank
                    and is_field_required(field)
                    and field.name not in field_names
                    and field.name not in exclude_fields
                )
            ]

        cfields = [
            cell.custom_field
            for group in cells_groups
            for cell in group.cells
            if isinstance(cell, EntityCellCustomField)
        ]

        if any(
            cell.value == EntityCellCustomFormSpecial.REMAINING_CUSTOMFIELDS
            for group in cells_groups
            for cell in group.cells
            if isinstance(cell, EntityCellCustomFormSpecial)
        ):
            remaining_cfields = [
                cfield
                for cfield in CustomField.objects.get_for_model(model).values()
                if cfield not in cfields
            ]
            forced_cfields = []
        else:
            remaining_cfields = []
            forced_cfields = [
                cfield
                for cfield in CustomField.objects.get_for_model(model).values()
                if cfield.is_required and not cfield.is_deleted and cfield not in cfields
            ]

        use_properties = use_relations = False
        for group in cells_groups:
            for cell in group.cells:
                if isinstance(cell, EntityCellCustomFormSpecial):
                    cvalue = cell.value

                    if cvalue == EntityCellCustomFormSpecial.CREME_PROPERTIES:
                        use_properties = True
                    elif cvalue == EntityCellCustomFormSpecial.RELATIONS:
                        use_relations = True

        extra_cells = [
            cell
            for group in cells_groups
            for cell in group.cells
            if isinstance(cell, EntityCellCustomFormExtra)
        ]

        forced_extra_cells = []

        try:
            extra_cell_cls = self._cell_registry[EntityCellCustomFormExtra.type_id]
        except KeyError:
            logger.info(
                '%s.form_class(): no extra cell class registered.',
                type(self).__name__,
            )
        else:
            for sub_cell_cls in extra_cell_cls.allowed_sub_cell_classes:
                sub_type_id = sub_cell_cls.sub_type_id
                # NB: cannot compare cell directly (classes are different)
                if (
                    sub_cell_cls.is_required
                    and not any(
                        sub_type_id == extra_cell.sub_cell.sub_type_id
                        for extra_cell in extra_cells
                    )
                ):
                    forced_extra_cells.append(extra_cell_cls(sub_cell_cls(model=model)))

        class CustomModelForm(base_form_class):
            def __init__(this, *args, **kwargs):
                super().__init__(*args, **kwargs)

                fields = this.fields
                instance = this.instance
                user = this.user

                for cell in chain(extra_cells, forced_extra_cells):
                    fields[cell.key] = cell.formfield(instance=instance, user=user)

                for extra_group in extra_groups:
                    for ffield_name, ffield in extra_group.formfields(
                        instance=instance, user=user,
                    ):
                        fields[ffield_name] = ffield

            def _get_customfields_n_values(this, only_required):
                entity = this.instance
                CremeEntity.populate_custom_values([entity], cfields)

                return [
                    (cfield, entity.get_custom_value(cfield))
                    for cfield in chain(cfields, remaining_cfields, forced_cfields)
                    if not cfield.is_deleted
                ]

            def _use_properties_fields(this):
                return use_properties

            def _use_relations_fields(this):
                return use_relations

            def clean(this):
                cleaned_data = super().clean()

                instance = this.instance
                get_data = this.cleaned_data.get
                for cell in chain(extra_cells, forced_extra_cells):
                    key = cell.key
                    try:
                        # TODO: cell method ??
                        cell.sub_cell.post_clean_instance(
                            instance=instance, value=get_data(key), form=this,
                        )
                    except ValidationError as e:
                        this.add_error(key, e)

                for extra_group in extra_groups:
                    extra_group.clean(form=this)

                return cleaned_data

            def save(this, *args, **kwargs):
                instance = super().save(*args, **kwargs)

                get_data = this.cleaned_data.get
                save_again = False
                for cell in chain(extra_cells, forced_extra_cells):
                    # TODO: cell method ??
                    save_again |= cell.sub_cell.post_save_instance(
                        instance=instance, value=get_data(cell.key), form=this,
                    )

                for extra_group in extra_groups:
                    save_again |= extra_group.save(this)

                if save_again:
                    instance.save()

                return instance

        cls = modelform_factory(
            model,
            form=CustomModelForm,
            fields=[*field_names, *remaining_field_names, *forced_field_names],
        )

        def formfield_name(cell):
            if isinstance(cell, str):
                return cell

            if isinstance(cell, EntityCellRegularField):
                return cell.value

            if isinstance(cell, EntityCellCustomField):
                return CustomModelForm._build_customfield_name(cell.custom_field)

            if isinstance(cell, EntityCellCustomFormExtra):
                return cell.key

            return '??'

        def get_all_cells_or_fieldnames(group):
            for cell in getattr(group, 'cells', ()):
                if isinstance(cell, EntityCellCustomFormSpecial):
                    cvalue = cell.value
                    if cvalue == EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS:
                        for field_name in remaining_field_names:
                            yield field_name
                    elif cvalue == EntityCellCustomFormSpecial.REMAINING_CUSTOMFIELDS:
                        for cfield in remaining_cfields:
                            yield EntityCellCustomField(cfield)
                    elif cvalue == EntityCellCustomFormSpecial.RELATIONS:
                        yield 'rtypes_info'
                        yield 'relation_types'
                        yield 'semifixed_rtypes'
                    elif cvalue == EntityCellCustomFormSpecial.CREME_PROPERTIES:
                        yield 'property_types'
                    else:
                        logger.critical(
                            'Unknown special cell when building form block: %s',
                            cvalue,
                        )
                else:
                    yield cell

        blocks = [
            {
                'id': f'group_{i}',
                'label': group.name,
                'fields': [
                    formfield_name(cell)
                    for cell in get_all_cells_or_fieldnames(group)
                ],
                'layout': group.layout,
                'template': group.template_name,
                'context': group.get_context(),
            } for i, group in enumerate(self._groups)
        ]

        def add_error_block(block_id, field_names):
            blocks.append({
                'id': block_id,
                'label': self.error_block_labels[block_id],
                'fields': field_names,
            })

        if forced_field_names:
            logger.warning(
                'A form configuration for model "%s" ignores some required fields: %s',
                model.__name__, forced_field_names,
            )
            add_error_block(self.BLOCK_ID_MISSING_FIELD, forced_field_names)
        if forced_cfields:
            logger.warning(
                'A form configuration for model "%s" ignores some required custom fields: %s',
                model.__name__, forced_cfields,
            )
            build_fname = CustomModelForm._build_customfield_name
            add_error_block(
                self.BLOCK_ID_MISSING_CUSTOM_FIELD,
                [build_fname(cfield) for cfield in forced_cfields],
            )
        if forced_extra_cells:
            logger.warning(
                'A form configuration for model "%s" ignores some required extra cells: %s',
                model.__name__, forced_extra_cells,
            )
            add_error_block(
                self.BLOCK_ID_MISSING_EXTRA_FIELD,
                [cell.key for cell in forced_extra_cells],
            )

        cls.blocks = FieldBlockManager(*blocks)

        return cls


# Descriptor -------------------------------------------------------------------
class CustomFormDescriptor:
    """The descriptor contains the meta-data for a Custom form.
    Each instance is related to a CustomFormConfigItem instance which stores
    the custom-form data (groups of fields).
    """
    item_model = CustomFormConfigItem

    CREATION_FORM = 0
    EDITION_FORM = 1
    FORM_TYPES = {CREATION_FORM, EDITION_FORM}

    _excluded_fields: List[str]
    _extra_cells: List[CustomFormExtraSubCell]
    _form_type: int  # TODO: Literal ?

    base_cell_registry = base_cell_registry

    def __init__(self, *,
                 id: str,
                 model: Type[Model],
                 verbose_name: str,
                 form_type: int = CREATION_FORM,
                 base_form_class=CremeEntityForm,
                 excluded_fields: Sequence[str] = (),
                 extra_sub_cells: Sequence[CustomFormExtraSubCell] = (),
                 extra_group_classes: Iterable[Type[ExtraFieldGroup]] = (),
                 ):
        """Constructor.
        @param id: Unique ID (in the registry) ; name like
               'my_app-mymodel_{creation|edition}' are nice.
        @param model: Related model.
        @param form_type: CREATION_FORM or EDITION_FORM.
               (edition forms does not propose relationships/properties fields).
        @param base_form_class: base class to use for generated form class
               (see build_form_class()).
        @param excluded_fields: Field names to exclude from the generated form
               (similar to Form's Meta.exclude attribute).
        @param extra_sub_cells: sub-cells the custom-form can use.
        @param extra_group_classes: extra groups the custom-form can use.
        """
        assert issubclass(base_form_class, CremeEntityForm)

        self._id = id
        self._model = model
        self.form_type = form_type
        self.verbose_name = verbose_name
        self.base_form_class = base_form_class
        self.excluded_fields = excluded_fields
        self.extra_sub_cells = extra_sub_cells
        self.extra_group_classes = extra_group_classes

    def __str__(self):
        return str(self.verbose_name)

    def build_cell_registry(self) -> EntityCellsRegistry:
        # NB: notice that we do not modify the attribute type_id
        class DescriptorExtraCells(EntityCellCustomFormExtra):
            allowed_sub_cell_classes = [type(sub_cell) for sub_cell in self.extra_sub_cells]

        return deepcopy(self.base_cell_registry).register(DescriptorExtraCells)

    @property
    def excluded_fields(self) -> Iterator[str]:
        yield from self._excluded_fields

    @excluded_fields.setter
    def excluded_fields(self, field_names: Iterable[str]) -> None:
        get_field = self._model._meta.get_field

        # NB: get_field() to raise exception
        self._excluded_fields = [
            field_name for field_name in field_names if get_field(field_name)
        ]

    @property
    def extra_group_classes(self) -> Iterator[Type[ExtraFieldGroup]]:
        yield from self._extra_groups

    @extra_group_classes.setter
    def extra_group_classes(self, groups: Iterable[Type[ExtraFieldGroup]]) -> None:
        # TODO: check validity/type ?
        self._extra_groups = [*groups]

    @property
    def extra_sub_cells(self) -> Iterator[CustomFormExtraSubCell]:
        yield from self._extra_cells

    @extra_sub_cells.setter
    def extra_sub_cells(self, sub_cells: Iterable[CustomFormExtraSubCell]) -> None:
        def checked_cls(c):
            if not isinstance(c, CustomFormExtraSubCell):
                raise ValueError(
                    f'CustomFormDescriptor.extra_cells: '
                    f'{c!r} is not an instance of <CustomFormExtraSubCell>.'
                )

            if not c.sub_type_id:
                raise ValueError(
                    f'CustomFormDescriptor.extra_cells: '
                    f'<{type(c).__name__}> has no sub_type_id.'
                )

            return c

        self._extra_cells = list(map(checked_cls, sub_cells))

    @property
    def form_type(self):
        return self._form_type

    @form_type.setter
    def form_type(self, form_type) -> None:
        if form_type not in self.FORM_TYPES:
            raise ValueError(f'form_type: {form_type} not in {self.FORM_TYPES}')

        self._form_type = form_type

    @property
    def id(self) -> str:
        return self._id

    @property
    def model(self) -> Type[Model]:
        return self._model

    # def groups(self, item: Optional[CustomFormConfigItem] = None) -> FieldGroupList:
    def groups(self, item: CustomFormConfigItem) -> FieldGroupList:
        """Return a groups list built from the data stored in the related
        CustomFormConfigItem.
        REMOVED: You can pass the item to avoid an SQL query.
        """
        # item_model = self.item_model
        # try:
        #     item = item or item_model.objects.get(cform_id=self.id)
        # except item_model.DoesNotExist:
        #     logger.critical(
        #         'CustomFormDescriptor.groups(): it seems no instance of %s with '
        #         'the id="%s" has been populated.',
        #         item_model.__name__, self.id,
        #     )
        #     raise

        return FieldGroupList.from_dicts(
            model=self.model,
            data=item.groups_as_dicts(),
            cell_registry=self.build_cell_registry(),
            allowed_extra_group_classes=self._extra_groups,
        )

    # def build_form_class(self,
    #                      item: Optional[CustomFormConfigItem] = None,
    #                      ) -> Type[CremeEntityForm]:
    def build_form_class(self, item: CustomFormConfigItem) -> Type[CremeEntityForm]:
        """Return a form class built from the data stored in the related
        CustomFormConfigItem.
        REMOVED: You can pass the item to avoid an SQL query.
        """
        return self.groups(item).form_class(
            base_form_class=self.base_form_class,
            exclude_fields=set(self._excluded_fields),
        )


class CustomFormDescriptorRegistry:
    """Registry for CustomDescriptor (see apps.py).
    Used by creme_config to retrieve all available CustomDescriptors.
    """
    class RegistrationError(Exception):
        pass

    def __init__(self):
        self._descriptors: Dict[str, CustomFormDescriptor] = {}

    def __iter__(self) -> Iterator[CustomFormDescriptor]:
        return iter(self._descriptors.values())

    def get(self, id: str) -> Optional[CustomFormDescriptor]:
        return self._descriptors.get(id)

    def register(self, *descriptors: CustomFormDescriptor) -> 'CustomFormDescriptorRegistry':
        setdefault = self._descriptors.setdefault

        for desc in descriptors:
            if setdefault(desc.id, desc) is not desc:
                raise self.RegistrationError(
                    f"Duplicated CustomFormDescriptor's id: {desc.id}"
                )

        return self

    # TODO ?
    # def unregister(self, *descriptors):
    #     ...


customform_descriptor_registry = CustomFormDescriptorRegistry()
