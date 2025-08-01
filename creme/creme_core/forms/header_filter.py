################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
from collections import defaultdict
from collections.abc import Iterable, Iterator
from copy import deepcopy
from itertools import chain
from typing import TYPE_CHECKING
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.transaction import atomic
from django.forms.fields import Field
from django.forms.widgets import Widget
from django.utils.choices import CallableChoiceIterator
from django.utils.translation import gettext_lazy as _

from ..core.entity_cell import (
    CELLS_MAP,
    EntityCell,
    EntityCellCustomField,
    EntityCellFunctionField,
    EntityCellRegistry,
    EntityCellRegularField,
    EntityCellRelation,
)
from ..gui import listview
from ..gui.view_tag import ViewTag
from ..models import (
    CremeEntity,
    CustomField,
    EntityCredentials,
    FieldsConfig,
    HeaderFilter,
    RelationType,
    SettingValue,
)
from ..models.utils import model_verbose_name
from ..setting_keys import global_filters_edition_key
from ..utils.id_generator import generate_string_id_and_save
from ..utils.meta import ModelFieldEnumerator
from ..utils.unicode_collation import collator
from .base import CremeModelForm

if TYPE_CHECKING:
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.gui.listview.smart_columns import (
        SmartColumnsRegistry,
    )

logger = logging.getLogger(__name__)


class UniformEntityCellsWidget(Widget):
    type_id: str

    def __init__(self,
                 choices: Iterable[tuple[str, EntityCell]] = (),
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choices = choices

    def get_context(self, name, value, attrs):
        context = super().get_context(name=name, value=value, attrs=attrs)

        widget_cxt = context['widget']
        widget_cxt['choices'] = self._refine_choices(self.choices)

        return context

    def _refine_choices(self, choices: Iterable[tuple[str, EntityCell]]) -> list:
        sort_key = collator.sort_key

        return sorted(
            ((choice_id, str(cell)) for choice_id, cell in choices),
            key=lambda k: sort_key(k[1]),
        )


class EntityCellRegularFieldsWidget(UniformEntityCellsWidget):
    template_name = 'creme_core/forms/widgets/entity-cells/regular-fields.html'
    type_id = EntityCellRegularField.type_id

    # <True> means: when a FK/M2M has only one sub-field, hide it
    hide_alone_subfield = True

    # <True> means: hide the checkbox of fields with displayed sub-fields
    only_leaves = False

    def get_context(self, name, value, attrs):
        context = super().get_context(name=name, value=value, attrs=attrs)

        widget_ctxt = context['widget']
        widget_ctxt['hide_alone_subfield'] = self.hide_alone_subfield
        widget_ctxt['only_leaves'] = self.only_leaves

        return context

    def _refine_choices(self, choices):
        main_choices = {}
        sub_choices = defaultdict(list)

        for choice_id, cell in choices:
            field_info = cell.field_info
            label = str(field_info[-1].verbose_name)

            if len(field_info) > 1:
                sub_choices[field_info[0].name].append((choice_id, label))
            else:
                main_choices[field_info[0].name] = (choice_id, label)

        sort_key = collator.sort_key

        def sort_choices(c):
            return sorted(c, key=lambda k: sort_key(k[1]))

        return sort_choices(
            (choice_id, label, sort_choices(sub_choices[field_name]))
            for field_name, (choice_id, label) in main_choices.items()
        )


class EntityCellCustomFieldsWidget(UniformEntityCellsWidget):
    template_name = 'creme_core/forms/widgets/entity-cells/custom-fields.html'
    type_id = EntityCellCustomField.type_id


class EntityCellFunctionFieldsWidget(UniformEntityCellsWidget):
    template_name = 'creme_core/forms/widgets/entity-cells/function-fields.html'
    type_id = EntityCellFunctionField.type_id


# TODO: smart categories ('all', 'contacts') ?
class EntityCellRelationsWidget(UniformEntityCellsWidget):
    template_name = 'creme_core/forms/widgets/entity-cells/relationships.html'
    type_id = EntityCellRelation.type_id


class EntityCellsWidget(Widget):
    template_name = 'creme_core/forms/widgets/entity-cells/widget.html'

    def __init__(self,
                 user=None,
                 model: type[CremeEntity] = CremeEntity,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.model = model
        self._sub_widgets: list[UniformEntityCellsWidget] = []

    def __deepcopy__(self, memo):
        result = super().__deepcopy__(memo)
        result._sub_widgets = deepcopy(self._sub_widgets, memo)

        return result

    @property
    def sub_widgets(self) -> Iterator[UniformEntityCellsWidget]:
        yield from self._sub_widgets

    @sub_widgets.setter
    def sub_widgets(self, widgets: Iterable[UniformEntityCellsWidget]):
        self._sub_widgets[:] = widgets

    def _build_samples(self) -> list[dict[str, str]]:
        user = self.user
        samples = []
        cells = [*chain.from_iterable(sub_w.choices for sub_w in self._sub_widgets)]
        entities = [
            *EntityCredentials.filter(
                user=user, queryset=self.model.objects.order_by('-modified'),
            )[:2],
        ]
        EntityCell.mixed_populate_entities(
            cells=[choice[1] for choice in cells],
            entities=entities, user=user,
        )

        for entity in entities:
            dump = {}

            for choice_id, cell in cells:
                try:
                    # TODO: add a "tag" attribute?
                    # TODO: would be cool to customize the value used to limit
                    #  the size of <ul> (see 'settings.CELL_SIZE'), but it would
                    #  need several API breaking to pass this limit (cells,
                    #  field printers etc...). Or use a new tag HTML_SAMPLE?
                    value = str(cell.render(entity, user, tag=ViewTag.HTML_LIST))
                except Exception as e:
                    logger.critical('EntityCellsWidget._build_samples(): %s', e)
                    value = ''

                dump[choice_id] = value

            samples.append(dump)

        return samples

    def get_context(self, name, value, attrs):
        if isinstance(value, list):
            # NB: we assume that the choice_id corresponds to the cells' keys
            #     which is not totally satisfactory...
            value = ','.join(cell.key for cell in value)

        context = super().get_context(name=name, value=value, attrs=attrs)

        widget_cxt = context['widget']
        widget_cxt['uuid'] = uuid4()
        widget_cxt['samples'] = self._build_samples()

        for sub_widget in self._sub_widgets:
            sub_ctxt = sub_widget.get_context(name, value, attrs)['widget']
            widget_cxt[sub_widget.type_id] = sub_ctxt

        return context


class UniformEntityCellsField(Field):
    widget: type[UniformEntityCellsWidget] = UniformEntityCellsWidget
    default_error_messages = {
        'invalid_value': _('This value is invalid: %(value)s'),
    }
    cell_class: type[EntityCell] = EntityCell

    def __init__(self, *,
                 model: type[CremeEntity] = CremeEntity,
                 non_hiddable_cells: Iterable[EntityCell] = (),
                 **kwargs):
        super().__init__(**kwargs)
        self._non_hiddable_cells = [*non_hiddable_cells]
        # self.user = ... TODO ?
        self.model = model

    def __deepcopy__(self, memo):
        result = super().__deepcopy__(memo)
        result._update_choices()

        return result

    @property
    def choices(self) -> Iterable[tuple[str, EntityCell]]:
        return CallableChoiceIterator(self._get_options)

    def _get_options(self) -> Iterator[tuple[str, EntityCell]]:
        raise NotImplementedError

    @property
    def model(self) -> type[CremeEntity]:
        return self._model

    @model.setter
    def model(self, model: type[CremeEntity]):
        self._model = model
        self._update_choices()

    @property
    def non_hiddable_cells(self) -> Iterator[EntityCell]:
        return iter(self._non_hiddable_cells)

    @non_hiddable_cells.setter
    def non_hiddable_cells(self, cells: Iterable[EntityCell]):
        self._non_hiddable_cells[:] = cells

    def to_python(self, value):
        cell_value = value[len(self.cell_class.type_id) + 1:]
        cell = self.cell_class.build(self.model, cell_value)

        if value and not cell:
            raise ValidationError(
                self.error_messages['invalid_value'],
                code='invalid_value',
                params={'value': cell_value},
            )

        return cell

    def _update_choices(self) -> None:
        self.widget.choices = self.choices

    def validate(self, value, *, check_in_options=True):
        super().validate(value)

        if value and check_in_options:
            cell_key = value.key

            if not any(cell_key == cell.key for __, cell in self._get_options()):
                raise ValidationError(
                    self.error_messages['invalid_value'],
                    code='invalid_value',
                    params={'value': value.value},
                )


class EntityCellRegularFieldsField(UniformEntityCellsField):
    widget = EntityCellRegularFieldsWidget
    cell_class = EntityCellRegularField
    fields_depth = 1
    only_leaves = False

    default_error_messages = {
        'not_leaf': _('This field has sub-field & cannot be selected: %(value)s'),
    }

    # This separated method makes overriding easier
    def _regular_fields_enum(self, model: type[CremeEntity]) -> ModelFieldEnumerator:
        # NB: we enumerate all the fields of the model, with a deep=1 (i.e. we
        # get also the subfields of ForeignKeys for example). We take care of
        # the FieldsConfig which can hide fields (i.e. have to be removed from
        # the choices) ; but if a field was already selected (e.g. the field
        # has been hidden _after_), it is not hidden, in order to not remove it
        # from the configuration (of HeaderFilter, CustomBlock...) silently
        # during its next edition.

        # TODO: manage FieldsConfig in ModelFieldEnumerator ??
        get_fconf = FieldsConfig.LocalCache().get_for_model

        non_hiddable_fnames: dict[type[CremeEntity], set[str]] = defaultdict(set)
        cell_class = self.cell_class
        for cell in self._non_hiddable_cells:
            if isinstance(cell, cell_class):
                field_info = cell.field_info
                length = len(field_info)

                if length == 1:
                    non_hiddable_fnames[model].add(field_info[0].name)
                else:
                    assert length == 2  # TODO: manage greater length ?

                    root = field_info[0]

                    # NB: not 'field.model' because of inheritance.
                    #     For example, (remember that 'image' is a FK to
                    #     'documents.models.Document') the field
                    #     'image__description' must reference Document, not CremeEntity.
                    non_hiddable_fnames[root.related_model].add(field_info[1].name)

                    # NB: if a sub-field (e.g. 'image__name') cannot be hidden,
                    #     the related field (e.g. 'image') cannot be hidden.
                    non_hiddable_fnames[model].add(root.name)

        def field_excluder(*, model, field, depth):
            return (
                get_fconf(model).is_field_hidden(field)
                and field.name not in non_hiddable_fnames[model]
            )

        return ModelFieldEnumerator(
            model, depth=self.fields_depth, only_leaves=False,
        ).filter(
            viewable=True,
        ).exclude(field_excluder)

    def _get_options(self):
        model = self.model
        build = self.cell_class.build

        for fields_chain in self._regular_fields_enum(model):
            cell = build(model, '__'.join(field.name for field in fields_chain))

            yield cell.key, cell

    def validate(self, value, **kwargs):
        super().validate(value, **kwargs)

        if self.only_leaves and value:
            if value.field_info[-1].is_relation:
                raise ValidationError(
                    self.error_messages['not_leaf'],
                    code='not_leaf',
                    params={'value': value.value},
                )


class EntityCellCustomFieldsField(UniformEntityCellsField):
    widget = EntityCellCustomFieldsWidget
    cell_class = EntityCellCustomField

    def _custom_fields(self):
        cell_class = self.cell_class

        _non_hiddable_cfield_ids = {
            cell.custom_field.id
            for cell in self._non_hiddable_cells
            if isinstance(cell, cell_class)
        }

        for cfield in CustomField.objects.get_for_model(self.model).values():
            if not cfield.is_deleted or cfield.id in _non_hiddable_cfield_ids:
                yield cfield

    def _get_options(self):
        cell_class = self.cell_class

        for cf in self._custom_fields():
            cell = cell_class(cf)

            yield cell.key, cell


class EntityCellFunctionFieldsField(UniformEntityCellsField):
    widget = EntityCellFunctionFieldsWidget
    cell_class = EntityCellFunctionField

    def _get_options(self):
        model = self.model
        cell_class = self.cell_class

        for f in cell_class.field_registry.fields(model):
            cell = cell_class(model=model, func_field=f)

            yield cell.key, cell


class EntityCellRelationsField(UniformEntityCellsField):
    widget = EntityCellRelationsWidget
    default_error_messages = {
        'incompatible': _('This type of relationship is not compatible with «%(model)s».'),
        'disabled':     _('This type of relationship is disabled.'),
    }
    cell_class = EntityCellRelation

    def _get_options(self):
        model = self.model
        cell_class = self.cell_class

        _non_hiddable_rtype_ids = {
            cell.relation_type.id
            for cell in self._non_hiddable_cells
            if isinstance(cell, cell_class)
        }

        for rtype in RelationType.objects.compatible(
            model, include_internals=True,
        ).filter(
            Q(enabled=True) | Q(id__in=_non_hiddable_rtype_ids)
        ):
            cell = cell_class(model=model, rtype=rtype)

            yield cell.key, cell

    def validate(self, value, *, check_in_options=False):
        super().validate(value, check_in_options=check_in_options)

        if value:
            rtype = value.relation_type

            if not rtype.is_compatible(self.model):
                raise ValidationError(
                    self.error_messages['incompatible'],
                    code='incompatible',
                    params={'model': model_verbose_name(self.model)},
                )

            if not rtype.enabled and value not in self._non_hiddable_cells:
                raise ValidationError(self.error_messages['disabled'], code='disabled')


class EntityCellsField(Field):
    widget = EntityCellsWidget
    default_error_messages = {
        'invalid_type': 'The type of cell in invalid: %(type_id)s.',
    }

    field_classes: set[type[UniformEntityCellsField]] = {
        EntityCellRegularFieldsField,
        EntityCellCustomFieldsField,
        EntityCellFunctionFieldsField,
        EntityCellRelationsField,
    }

    def __init__(self, *, model=CremeEntity, cell_registry=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._model = model
        self._non_hiddable_cells: list[EntityCell] = []
        self._user = None
        self._sub_fields: list[UniformEntityCellsField] = []
        self.cell_registry = cell_registry or CELLS_MAP

    def __deepcopy__(self, memo):
        result = super().__deepcopy__(memo)
        result._non_hiddable_cells = deepcopy(self._non_hiddable_cells, memo)

        result._sub_fields = []
        result._create_sub_fields()

        result.widget.model = self.model

        return result

    @property
    def cell_registry(self) -> EntityCellRegistry:
        return self._cell_registry

    @cell_registry.setter
    def cell_registry(self, cell_registry: EntityCellRegistry):
        self._cell_registry = cell_registry

        self._create_sub_fields()

    def _create_sub_fields(self) -> None:
        sub_fields = []

        model = self._model
        cell_registry = self._cell_registry

        non_hiddable_cells = self._non_hiddable_cells
        sub_widgets = []

        for field_cls in self.field_classes:
            if field_cls.cell_class.type_id in cell_registry:
                field = field_cls(
                    model=model,
                    non_hiddable_cells=non_hiddable_cells,
                )
                sub_fields.append(field)
                sub_widgets.append(field.widget)

        self._sub_fields[:] = sub_fields
        self.widget.sub_widgets = sub_widgets

    @property
    def model(self) -> type[CremeEntity]:
        return self._model

    @model.setter
    def model(self, model: type[CremeEntity]):
        self._model = self.widget.model = model

        for sub_field in self._sub_fields:
            sub_field.model = model

    @property
    def non_hiddable_cells(self) -> list[EntityCell]:
        return self._non_hiddable_cells

    @non_hiddable_cells.setter
    def non_hiddable_cells(self, cells: Iterable[EntityCell]):
        self._non_hiddable_cells[:] = cells

        for sub_field in self._sub_fields:
            sub_field.non_hiddable_cells = cells

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = self.widget.user = user

    def to_python(self, value):
        cells = []

        if value:
            for sub_value in value.split(','):
                cell_type_id = sub_value.split('-', 1)[0]

                for sub_field in self._sub_fields:
                    if cell_type_id == sub_field.cell_class.type_id:
                        cells.append(sub_field.clean(sub_value))
                        break
                else:
                    raise ValidationError(
                        self.error_messages['invalid_type'],
                        code='invalid_type',
                        params={'type_id': cell_type_id},
                    )

        return cells


class _HeaderFilterForm(CremeModelForm):
    error_messages = {
        'orphan_private':  _(
            'A private view of list must be assigned to a user/team.'
        ),
        'foreign_private': _(
            'A private view of list must belong to you (or one of your teams).'
        ),
    }

    cells = EntityCellsField(label=_('Columns'))

    class Meta(CremeModelForm.Meta):
        model = HeaderFilter

    blocks = CremeModelForm.blocks.new({
        'id': 'cells', 'label': _('Columns'), 'fields': ['cells'],
    })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_f = self.fields['user']
        user_f.empty_label = _('No owner')
        user_f.help_text = _(
            'If you assign an owner, only the owner can edit or delete the view; '
            'views without owner can be edited/deleted by all users'
        ) if SettingValue.objects.get_4_key(global_filters_edition_key).value else _(
            'If you assign an owner, only the owner can edit or delete the view; '
            'views without owner can only be edited/deleted by superusers'
        )

    def clean(self):
        cdata = self.cleaned_data

        if not self._errors:
            is_private = cdata.get('is_private', False)

            if is_private:
                owner = cdata.get('user')

                if not owner:
                    self.add_error(
                        'user',
                        ValidationError(
                            self.error_messages['orphan_private'],
                            code='orphan_private',
                        ),
                    )
                else:
                    req_user = self.user

                    if not req_user.is_staff:
                        if owner.is_team:
                            if req_user.id not in owner.teammates:
                                self.add_error(
                                    'user',
                                    ValidationError(
                                        self.error_messages['foreign_private'],
                                        code='foreign_private',
                                    )
                                )
                        elif owner != req_user:
                            self.add_error(
                                'user',
                                ValidationError(
                                    self.error_messages['foreign_private'],
                                    code='foreign_private',
                                )
                            )

            self.instance.cells = cdata['cells']

        return cdata


class HeaderFilterCreationForm(_HeaderFilterForm):
    def __init__(self,
                 ctype: ContentType,
                 smart_columns_registry: SmartColumnsRegistry | None = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)

        registry = smart_columns_registry or listview.smart_columns_registry

        cells_f = self.fields['cells']
        self.instance.entity_type = ctype
        cells_f.model = model = ctype.model_class()
        cells_f.initial = registry.get_cells(model)

    @atomic
    def save(self, *args, **kwargs):
        instance = self.instance
        ct = instance.entity_type

        kwargs['commit'] = False
        super().save(*args, **kwargs)
        generate_string_id_and_save(
            HeaderFilter, [instance],
            f'creme_core-userhf_{ct.app_label}-{ct.model}-',
        )

        return instance


# TODO: factorise?
class HeaderFilterCloningForm(_HeaderFilterForm):
    def __init__(self,
                 source: HeaderFilter,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = self.fields

        fields['is_private'].initial = True
        # fields['name'].initial = _('Clone of ...') TODO?

        cells_f = self.fields['cells']
        ctype = source.entity_type
        self.instance.entity_type = ctype
        cells_f.model = ctype.model_class()
        cells_f.initial = source.cells

    @atomic
    def save(self, *args, **kwargs):
        instance = self.instance
        ct = instance.entity_type

        kwargs['commit'] = False
        super().save(*args, **kwargs)
        generate_string_id_and_save(
            HeaderFilter, [instance],
            f'creme_core-userhf_{ct.app_label}-{ct.model}-',
        )

        return instance


class HeaderFilterEditionForm(_HeaderFilterForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        fields = self.fields

        if not instance.is_custom:
            del fields['is_private']

        cells_f = fields['cells']
        cells = instance.cells
        cells_f.non_hiddable_cells = cells
        cells_f.model = instance.entity_type.model_class()
        cells_f.initial = cells
