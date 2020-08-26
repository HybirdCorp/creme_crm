# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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
from collections import defaultdict
from copy import deepcopy
from itertools import chain
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Type,
)

from django.core.exceptions import ValidationError
# from django.db.models.query_utils import Q
from django.db.transaction import atomic
from django.forms.fields import CallableChoiceIterator, Field  # EMPTY_VALUES
from django.forms.widgets import Widget
from django.utils.translation import gettext_lazy as _

from ..core.entity_cell import (
    CELLS_MAP,
    EntityCell,
    EntityCellCustomField,
    EntityCellFunctionField,
    EntityCellRegularField,
    EntityCellRelation,
    EntityCellsRegistry,
)
# from ..core import function_field
from ..gui import listview
from ..models import (
    CremeEntity,
    CustomField,
    EntityCredentials,
    FieldsConfig,
    HeaderFilter,
    RelationType,
)
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
# _RFIELD_PREFIX = EntityCellRegularField.type_id + '-'
# _CFIELD_PREFIX = EntityCellCustomField.type_id + '-'
# _FFIELD_PREFIX = EntityCellFunctionField.type_id + '-'
# _RTYPE_PREFIX  = EntityCellRelation.type_id + '-'


class UniformEntityCellsWidget(Widget):
    type_id: str

    def __init__(self,
                 choices: Iterable[Tuple[str, EntityCell]] = (),
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choices = choices

    def get_context(self, name, value, attrs):
        context = super().get_context(name=name, value=value, attrs=attrs)

        widget_cxt = context['widget']
        widget_cxt['choices'] = self._refine_choices(self.choices)

        return context

    def _refine_choices(self, choices: Iterable[Tuple[str, EntityCell]]) -> list:
        sort_key = collator.sort_key

        return sorted(
            ((choice_id, str(cell)) for choice_id, cell in choices),
            key=lambda k: sort_key(k[1]),
        )


class EntityCellRegularFieldsWidget(UniformEntityCellsWidget):
    template_name = 'creme_core/forms/widgets/entity-cells/regular-fields.html'
    type_id = EntityCellRegularField.type_id

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
    # template_name = 'creme_core/forms/widgets/entity-cells.html'
    template_name = 'creme_core/forms/widgets/entity-cells/widget.html'

    # def __init__(self, user=None, model=None,
    #              model_fields=(), model_subfields=None,
    #              custom_fields=(),
    #              function_fields=(),
    #              relation_types=(),
    #              *args, **kwargs
    #             ):
    #     super().__init__(*args, **kwargs)
    #     self.user = user
    #     self.model = model
    #
    #     self.model_fields = model_fields
    #     self.model_subfields = model_subfields or {}
    #     self.custom_fields = custom_fields
    #     self.function_fields = function_fields
    #     self.relation_types = relation_types
    def __init__(self,
                 user=None,
                 model: Type[CremeEntity] = CremeEntity,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.model = model
        self._sub_widgets: List[UniformEntityCellsWidget] = []

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

    def _build_samples(self) -> List[Dict[str, str]]:
        user = self.user
        # model = self.model
        samples = []

        # PREFIX = len(_RFIELD_PREFIX); build = EntityCellRegularField.build
        # cells = [
        #     (field_id, build(model, field_id[PREFIX:]))
        #     for field_id, field_vname in self.model_fields
        # ]
        # cells.extend(
        #     (field_id, build(model, field_id[PREFIX:]))
        #     for choices in self.model_subfields.values()
        #     for field_id, field_vname in choices
        # )
        #
        # PREFIX = len(_FFIELD_PREFIX)
        # build = EntityCellFunctionField.build
        # cells.extend(
        #     (field_id, build(model, field_id[PREFIX:]))
        #     for field_id, field_vname in self.function_fields
        # )
        cells = [*chain.from_iterable(sub_w.choices for sub_w in self._sub_widgets)]

        # TODO: populate entities
        for entity in EntityCredentials.filter(
            user, self.model.objects.order_by('-modified'),
        )[:2]:
            dump = {}

            for choice_id, cell in cells:
                try:
                    value = str(cell.render_html(entity, user))
                except Exception as e:
                    logger.critical('EntityCellsWidget._build_samples(): %s', e)
                    value = ''

                dump[choice_id] = value

            samples.append(dump)

        return samples

    # @property
    # def model(self):
    #     return self._model
    #
    # @model.setter
    # def model(self, model):
    #     self._model = model or CremeEntity

    def get_context(self, name, value, attrs):
        if isinstance(value, list):
            # value = ','.join(f'{cell.type_id}-{cell.value}' for cell in value)
            # NB: we assume that the choice_id corresponds to the cells' keys
            #     which is not totally satisfactory...
            value = ','.join(cell.key for cell in value)

        context = super().get_context(name=name, value=value, attrs=attrs)

        widget_cxt = context['widget']
        widget_cxt['samples'] = self._build_samples()
        # widget_cxt['model_fields']    = self.model_fields
        # widget_cxt['model_subfields'] = self.model_subfields
        # widget_cxt['custom_fields']   = self.custom_fields
        # widget_cxt['function_fields'] = self.function_fields
        # widget_cxt['relation_types']  = self.relation_types

        for sub_widget in self._sub_widgets:
            sub_ctxt = sub_widget.get_context(name, value, attrs)['widget']
            widget_cxt[sub_widget.type_id] = sub_ctxt

        return context


class UniformEntityCellsField(Field):
    widget: Type[UniformEntityCellsWidget] = UniformEntityCellsWidget
    default_error_messages = {
        'invalid_value': _('This value is invalid: %(value)s'),
    }
    cell_class: Type[EntityCell] = EntityCell

    def __init__(self, *,
                 model: Type[CremeEntity] = CremeEntity,
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
    def choices(self) -> Iterable[Tuple[str, EntityCell]]:
        return CallableChoiceIterator(self._get_options)

    def _get_options(self) -> Iterator[Tuple[str, EntityCell]]:
        raise NotImplementedError

    @property
    def model(self) -> Type[CremeEntity]:
        return self._model

    @model.setter
    def model(self, model: Type[CremeEntity]):
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

    # This separated method makes overriding easier
    def _regular_fields_enum(self, model: Type[CremeEntity]) -> ModelFieldEnumerator:
        # NB: we enumerate all the fields of the model, with a deep=1 (ie: we
        # get also the sub-fields of ForeignKeys for example). We take care of
        # the FieldsConfig which can hide fields (ie: have to be removed from
        # the choices) ; but if a field was already selected (eg: the field
        # has been hidden _after_), it is not hidden, in order to not remove it
        # from the configuration (of HeaderFilter, CustomBlock...) silently
        # during its next edition.

        # TODO: manage FieldsConfig in ModelFieldEnumerator ??
        get_fconf = FieldsConfig.LocalCache().get_4_model

        non_hiddable_fnames: Dict[Type[CremeEntity], Set[str]] = defaultdict(set)
        cell_class = self.cell_class
        for cell in self._non_hiddable_cells:
            if isinstance(cell, cell_class):
                field_info = cell.field_info
                field = field_info[-1]
                non_hiddable_fnames[field.model].add(field.name)

                # BEWARE: if a sub-field (eg: 'image__name') cannot be hidden,
                # the related field (eg: 'image') cannot be hidden.
                if len(field_info) == 2:
                    non_hiddable_fnames[model].add(field_info[0].name)

        def field_excluder(field, deep):
            model = field.model

            return (
                get_fconf(model).is_field_hidden(field)
                and
                field.name not in non_hiddable_fnames[model]
            )

        return ModelFieldEnumerator(
            model, deep=self.fields_depth, only_leafs=False,
        ).filter(
            viewable=True,
        ).exclude(field_excluder)

    def _get_options(self):
        model = self.model
        build = self.cell_class.build

        for fields_chain in self._regular_fields_enum(model):
            cell = build(model, '__'.join(field.name for field in fields_chain))

            yield cell.key, cell


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
    }
    cell_class = EntityCellRelation

    def _get_options(self):
        model = self.model
        cell_class = self.cell_class

        for rtype in RelationType.objects.compatible(
            model, include_internals=True,
        ).order_by('predicate'):
            cell = cell_class(model=model, rtype=rtype)

            yield cell.key, cell

    def validate(self, value, *, check_in_options=False):
        super().validate(value, check_in_options=check_in_options)

        if value and not value.relation_type.is_compatible(self.model):
            raise ValidationError(
                self.error_messages['incompatible'],
                code='incompatible',
                params={
                    'model': self.model._meta.verbose_name,
                },
            )


class EntityCellsField(Field):
    widget = EntityCellsWidget
    default_error_messages = {
        # 'invalid': _('Enter a valid value.'),
        # 'invalid_type': 'The type of cell in invalid.',
        'invalid_type': 'The type of cell in invalid: %(type_id)s.',
    }

    field_classes: Set[Type[UniformEntityCellsField]] = {
        EntityCellRegularFieldsField,
        EntityCellCustomFieldsField,
        EntityCellFunctionFieldsField,
        EntityCellRelationsField,
    }

    # def __init__(self, *, content_type=None, function_field_registry=None, **kwargs):
    #     super().__init__(**kwargs)
    #     self.function_field_registry = function_field_registry or \
    #          function_field.function_field_registry
    #     self._non_hiddable_cells = []
    #     self.content_type = content_type
    #     self.user = None
    def __init__(self, *, model=CremeEntity, cell_registry=None, **kwargs):
        super().__init__(**kwargs)
        self._model = model
        self._non_hiddable_cells = []
        self._user = None
        self._sub_fields: List[UniformEntityCellsField] = []
        self.cell_registry = cell_registry or CELLS_MAP

    def __deepcopy__(self, memo):
        result = super().__deepcopy__(memo)
        result._non_hiddable_cells = deepcopy(self._non_hiddable_cells, memo)

        result._sub_fields = []
        result._create_sub_fields()

        result.widget.model = self.model

        return result

    # def _build_4_regularfield(self, model, name):
    #     return EntityCellRegularField.build(model=model, name=name[len(_RFIELD_PREFIX):])

    # def _build_4_customfield(self, model, name):
    #     return EntityCellCustomField(self._get_cfield(int(name[len(_CFIELD_PREFIX):])))

    # def _build_4_functionfield(self, model, name):
    #     return EntityCellFunctionField.build(model, name[len(_FFIELD_PREFIX):])

    # def _build_4_relation(self, model, name):
    #     return EntityCellRelation(model=model, rtype=self._get_rtype(name[len(_RTYPE_PREFIX):]))

    # def _choices_4_customfields(self, ct, builders):
    #     self._custom_fields = CustomField.objects.filter(content_type=ct)  # Cache
    #     self.widget.custom_fields = cfields_choices = []
    #
    #     for cf in self._custom_fields:
    #         field_id = _CFIELD_PREFIX + str(cf.id)
    #         cfields_choices.append((field_id, cf.name))
    #         builders[field_id] = EntityCellsField._build_4_customfield

    # def _choices_4_functionfields(self, ct, builders):
    #     self.widget.function_fields = ffields_choices = []
    #
    #     for f in self.function_field_registry.fields(ct.model_class()):
    #         field_id = _FFIELD_PREFIX + f.name
    #         ffields_choices.append((field_id, f.verbose_name))
    #         builders[field_id] = EntityCellsField._build_4_functionfield

    # def _regular_fields_enum(self, model):
    #
    #     # NB: we enumerate all the fields of the model, with a deep=1 (ie: we
    #     # get also the sub-fields of ForeignKeys for example). We take care of
    #     # the FieldsConfig which can hide fields (ie: have to be removed from
    #     # the choices) ; but if a field was already selected (eg: the field
    #     # has been hidden _after_), it is not hidden, in order to not remove it
    #     # from the configuration (of HeaderFilter, CustomBlock...) silently
    #     # during its next edition.
    #
    #     get_fconf = FieldsConfig.LocalCache().get_4_model
    #
    #     non_hiddable_fnames = defaultdict(set)
    #     for cell in self._non_hiddable_cells:
    #         if isinstance(cell, EntityCellRegularField):
    #             field_info = cell.field_info
    #             field = field_info[-1]
    #             non_hiddable_fnames[field.model].add(field.name)
    #
    #             # BEWARE: if a sub-field (eg: 'image__name') cannot be hidden,
    #             # the related field (eg: 'image') cannot be hidden.
    #             if len(field_info) == 2:
    #                 non_hiddable_fnames[model].add(field_info[0].name)
    #
    #     def field_excluder(field, deep):
    #         model = field.model
    #
    #         return (
    #             get_fconf(model).is_field_hidden(field)
    #             and
    #             field.name not in non_hiddable_fnames[model]
    #         )
    #
    #     return ModelFieldEnumerator(
    #         model, deep=1, only_leafs=False,
    #     ).filter(
    #         viewable=True,
    #     ).exclude(field_excluder)

    # def _choices_4_regularfields(self, ct, builders):
    #     widget = self.widget
    #     widget.model_fields = rfields_choices = []
    #     widget.model_subfields = subfields_choices = defaultdict(list)
    #
    #     for fields_info in self._regular_fields_enum(ct.model_class()):
    #         choices = rfields_choices if len(fields_info) == 1 else \
    #                   subfields_choices[_RFIELD_PREFIX + fields_info[0].name]  # FK, M2M
    #
    #         field_id = _RFIELD_PREFIX + '__'.join(field.name for field in fields_info)
    #         choices.append((field_id, str(fields_info[-1].verbose_name)))
    #         builders[field_id] = EntityCellsField._build_4_regularfield
    #
    #     sort_key = collator.sort_key
    #     sort_choice = lambda k: sort_key(k[1])
    #     rfields_choices.sort(key=sort_choice)
    #
    #     for subfield_choices in subfields_choices.values():
    #         subfield_choices.sort(key=sort_choice)

    # def _choices_4_relationtypes(self, ct, builders):
    #     # Cache
    #     self._relation_types = RelationType.objects.compatible(
    #         ct, include_internals=True,
    #     ).order_by('predicate')
    #     self.widget.relation_types = rtypes_choices = []
    #
    #     for rtype in self._relation_types:
    #         field_id = _RTYPE_PREFIX + rtype.id
    #         rtypes_choices.append((field_id, rtype.predicate))
    #         builders[field_id] = EntityCellsField._build_4_relation

    @property
    def cell_registry(self) -> EntityCellsRegistry:
        return self._cell_registry

    @cell_registry.setter
    def cell_registry(self, cell_registry: EntityCellsRegistry):
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
    def content_type(self):
        # return self._content_type
        warnings.warn(
            'The getter EntityCellsField.content_type is deprecated ; '
            'use the property "models" instead',
            DeprecationWarning
        )

        from django.contrib.contenttypes.models import ContentType

        return ContentType.objects.get_for_model(self._model)

    @content_type.setter
    def content_type(self, ct):
        # self._content_type = ct
        # self._builders = builders = {}
        #
        # if ct is None:
        #     self._model_fields = self._model_subfields = self._custom_fields \
        #                        = self._function_fields = self._relation_types \
        #                        = ()
        #     self.widget.model = None  # todo: test..
        # else:
        #     self.widget.model = ct.model_class()
        #
        #     self._choices_4_regularfields(ct, builders)
        #     self._choices_4_customfields(ct, builders)
        #     self._choices_4_functionfields(ct, builders)
        #     self._choices_4_relationtypes(ct, builders)
        warnings.warn(
            'The setter EntityCellsField.content_type is deprecated ; '
            'use the property "models" instead',
            DeprecationWarning
        )
        self.model = ct.model_class()

    # def _get_cfield(self, cfield_id):
    #     for cfield in self._custom_fields:
    #         if cfield.id == cfield_id:
    #             return cfield

    # def _get_rtype(self, rtype_id):
    #     for rtype in self._relation_types:
    #         if rtype.id == rtype_id:
    #             return rtype

    @property
    def model(self) -> Type[CremeEntity]:
        return self._model

    @model.setter
    def model(self, model: Type[CremeEntity]):
        self._model = self.widget.model = model

        for sub_field in self._sub_fields:
            sub_field.model = model

    @property
    def non_hiddable_cells(self) -> List[EntityCell]:
        return self._non_hiddable_cells

    @non_hiddable_cells.setter
    def non_hiddable_cells(self, cells: Iterable[EntityCell]):
        self._non_hiddable_cells[:] = cells
        # self.content_type = self._content_type

        for sub_field in self._sub_fields:
            sub_field.non_hiddable_cells = cells

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = self.widget.user = user

    # def clean(self, value):
    #     assert self._content_type
    #     cells = []
    #
    #     if value in EMPTY_VALUES:
    #         if self.required:
    #             raise ValidationError(self.error_messages['required'], code='required')
    #     else:
    #         model = self._content_type.model_class()
    #         get_builder = self._builders.get
    #
    #         for elt in value.split(','):
    #             builder = get_builder(elt)
    #
    #             if not builder:
    #                 raise ValidationError(self.error_messages['invalid'], code='invalid')
    #
    #             cells.append(builder(self, model, elt))
    #
    #     return cells

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
        'orphan_private':  _('A private view of list must be assigned to a user/team.'),
        'foreign_private': _('A private view of list must belong to you (or one of your teams).')
    }

    cells = EntityCellsField(label=_('Columns'))

    class Meta(CremeModelForm.Meta):
        model = HeaderFilter
        help_texts = {
            'user': _('All users can see the view, but only the owner can edit or delete it'),
            'is_private': _(
                'A private view of list can only be used by its owner '
                '(or the teammates if the owner is a team)'
            ),
        }

    blocks = CremeModelForm.blocks.new(('cells', _('Columns'), ['cells']))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].empty_label = _('All users')

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


class HeaderFilterCreateForm(_HeaderFilterForm):
    def __init__(self,
                 ctype: 'ContentType',
                 smart_columns_registry: Optional['SmartColumnsRegistry'] = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)

        registry = smart_columns_registry or listview.smart_columns_registry

        cells_f = self.fields['cells']
        # cells_f.content_type = self.instance.entity_type = ctype
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
            f'creme_core-userhf_{ct.app_label}-{ct.model}',
        )

        return instance


class HeaderFilterEditForm(_HeaderFilterForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        fields = self.fields

        if not instance.is_custom:
            del fields['is_private']

        cells_f = fields['cells']
        cells = instance.cells
        cells_f.non_hiddable_cells = cells
        # cells_f.content_type = instance.entity_type
        cells_f.model = instance.entity_type.model_class()
        cells_f.initial = cells
