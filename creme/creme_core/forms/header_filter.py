# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from collections import defaultdict
import logging

from django.db.transaction import atomic
from django.forms.fields import EMPTY_VALUES, Field, ValidationError
from django.forms.widgets import Widget
from django.utils.translation import gettext_lazy as _

from ..core.entity_cell import (EntityCellRegularField,
        EntityCellCustomField, EntityCellFunctionField, EntityCellRelation)
from ..core import function_field
from ..gui import listview
from ..models import (CremeEntity, RelationType, CustomField, EntityCredentials,
        HeaderFilter, FieldsConfig)
from ..utils.id_generator import generate_string_id_and_save
from ..utils.meta import ModelFieldEnumerator
from ..utils.unicode_collation import collator

from .base import CremeModelForm


logger = logging.getLogger(__name__)
_RFIELD_PREFIX = EntityCellRegularField.type_id + '-'
_CFIELD_PREFIX = EntityCellCustomField.type_id + '-'
_FFIELD_PREFIX = EntityCellFunctionField.type_id + '-'
_RTYPE_PREFIX  = EntityCellRelation.type_id + '-'


# TODO: move to a separated file ??
class EntityCellsWidget(Widget):
    template_name = 'creme_core/forms/widgets/entity-cells.html'

    def __init__(self, user=None, model=None, model_fields=(), model_subfields=None, custom_fields=(),
                 function_fields=(), relation_types=(), *args, **kwargs
                ):
        super().__init__(*args, **kwargs)
        self.user = user
        self.model = model

        self.model_fields = model_fields
        self.model_subfields = model_subfields or {}
        self.custom_fields = custom_fields
        self.function_fields = function_fields
        self.relation_types = relation_types

    def _build_samples(self):
        user = self.user
        model = self.model
        samples = []

        PREFIX = len(_RFIELD_PREFIX); build = EntityCellRegularField.build
        cells = [(field_id, build(model, field_id[PREFIX:]))
                    for field_id, field_vname in self.model_fields
                ]
        cells.extend((field_id, build(model, field_id[PREFIX:]))
                        for choices in self.model_subfields.values()
                            for field_id, field_vname in choices
                    )

        PREFIX = len(_FFIELD_PREFIX); build = EntityCellFunctionField.build
        cells.extend((field_id, build(model, field_id[PREFIX:]))
                        for field_id, field_vname in self.function_fields
                    )

        # Missing CustomFields and Relationships

        for entity in EntityCredentials.filter(user, self.model.objects.order_by('-modified'))[:2]:
            dump = {}

            for field_id, cell in cells:
                try:
                    value = str(cell.render_html(entity, user))
                except Exception as e:
                    logger.critical('EntityCellsWidget._build_samples(): %s', e)
                    value = ''

                dump[field_id] = value

            samples.append(dump)

        return samples

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, model):
        self._model = model or CremeEntity

    def get_context(self, name, value, attrs):
        if isinstance(value, list):
            value = ','.join('{}-{}'.format(cell.type_id, cell.value) for cell in value)

        context = super().get_context(name=name, value=value, attrs=attrs)

        widget_cxt = context['widget']
        widget_cxt['samples'] = self._build_samples()
        widget_cxt['model_fields']    = self.model_fields
        widget_cxt['model_subfields'] = self.model_subfields
        widget_cxt['custom_fields']   = self.custom_fields
        widget_cxt['function_fields'] = self.function_fields
        widget_cxt['relation_types']  = self.relation_types

        return context


class EntityCellsField(Field):
    widget = EntityCellsWidget
    default_error_messages = {
        'invalid': _('Enter a valid value.'),
    }

    # def __init__(self, content_type=None, function_field_registry=None, *args, **kwargs):
    def __init__(self, *, content_type=None, function_field_registry=None, **kwargs):
        # super().__init__(*args, **kwargs)
        super().__init__(**kwargs)
        self.function_field_registry = function_field_registry or function_field.function_field_registry
        self._non_hiddable_cells = []
        self.content_type = content_type
        self.user = None

    def _build_4_regularfield(self, model, name):
        return EntityCellRegularField.build(model=model, name=name[len(_RFIELD_PREFIX):])

    def _build_4_customfield(self, model, name):
        return EntityCellCustomField(self._get_cfield(int(name[len(_CFIELD_PREFIX):])))

    def _build_4_functionfield(self, model, name):
        return EntityCellFunctionField.build(model, name[len(_FFIELD_PREFIX):])

    def _build_4_relation(self, model, name):
        return EntityCellRelation(model=model, rtype=self._get_rtype(name[len(_RTYPE_PREFIX):]))

    def _choices_4_customfields(self, ct, builders):
        self._custom_fields = CustomField.objects.filter(content_type=ct)  # Cache
        self.widget.custom_fields = cfields_choices = []  # TODO: sort ?

        for cf in self._custom_fields:
            field_id = _CFIELD_PREFIX + str(cf.id)
            cfields_choices.append((field_id, cf.name))
            builders[field_id] = EntityCellsField._build_4_customfield

    def _choices_4_functionfields(self, ct, builders):
        self.widget.function_fields = ffields_choices = []  # TODO: sort ?

        # for f in ct.model_class().function_fields:
        for f in self.function_field_registry.fields(ct.model_class()):
            field_id = _FFIELD_PREFIX + f.name
            ffields_choices.append((field_id, f.verbose_name))
            builders[field_id] = EntityCellsField._build_4_functionfield

    def _regular_fields_enum(self, model):  # This separated method makes overloading easier (see reports)
#        return ModelFieldEnumerator(model, deep=1, only_leafs=False).filter(viewable=True)

        # NB: we enumerate all the fields of the model, with a deep=1 (ie: we
        # get also the sub-fields of ForeignKeys for example). We take care of
        # the FieldsConfig which can hide fields (ie: have to be removed from
        # the choices) ; but if a field was already selected (eg: the field
        # has been hidden _after_), it is not hidden, in order to not remove it
        # from the configuration (of HeaderFilter, CustomBlock...) silently
        # during its next edition.

        # TODO: manage FieldsConfig in ModelFieldEnumerator ??
        # TODO: factorise with FieldsConfig.filter_cells
        get_fconf = FieldsConfig.LocalCache().get_4_model

        non_hiddable_fnames = defaultdict(set)
        for cell in self._non_hiddable_cells:
            if isinstance(cell, EntityCellRegularField):
                field_info = cell.field_info
                field = field_info[-1]
                non_hiddable_fnames[field.model].add(field.name)

                # BEWARE: if a sub-field (eg: 'image__name') cannot be hidden,
                # the related field (eg: 'image') cannot be hidden.
                if len(field_info) == 2:
                    non_hiddable_fnames[model].add(field_info[0].name)

        def field_excluder(field, deep):
            model = field.model

            return get_fconf(model).is_field_hidden(field) and \
                   field.name not in non_hiddable_fnames[model]

        return ModelFieldEnumerator(model, deep=1, only_leafs=False) \
                        .filter(viewable=True) \
                        .exclude(field_excluder)

    def _choices_4_regularfields(self, ct, builders):
        # TODO: make the managing of subfields by the widget ??
        # TODO: remove subfields with len() == 1 (done in template for now)
        widget = self.widget
        widget.model_fields = rfields_choices = []
        widget.model_subfields = subfields_choices = defaultdict(list)  # TODO: sort too ??

        for fields_info in self._regular_fields_enum(ct.model_class()):
            choices = rfields_choices if len(fields_info) == 1 else \
                      subfields_choices[_RFIELD_PREFIX + fields_info[0].name]  # FK, M2M

            field_id = _RFIELD_PREFIX + '__'.join(field.name for field in fields_info)
            choices.append((field_id, str(fields_info[-1].verbose_name)))
            builders[field_id] = EntityCellsField._build_4_regularfield

        sort_key = collator.sort_key
        sort_choice = lambda k: sort_key(k[1])  # TODO: in utils ?
        rfields_choices.sort(key=sort_choice)

        for subfield_choices in subfields_choices.values():
            subfield_choices.sort(key=sort_choice)

    def _choices_4_relationtypes(self, ct, builders):
        # Cache
        self._relation_types = RelationType.objects.compatible(ct, include_internals=True) \
                                           .order_by('predicate')  # TODO: unicode collation
        # TODO: sort ? smart categories ('all', 'contacts') ?
        self.widget.relation_types = rtypes_choices = []

        for rtype in self._relation_types:
            field_id = _RTYPE_PREFIX + rtype.id
            rtypes_choices.append((field_id, rtype.predicate))
            builders[field_id] = EntityCellsField._build_4_relation

    @property
    def content_type(self):
        return self._content_type

    @content_type.setter
    def content_type(self, ct):
        self._content_type = ct
        self._builders = builders = {}

        if ct is None:
            self._model_fields = self._model_subfields = self._custom_fields \
                               = self._function_fields = self._relation_types \
                               = ()
            self.widget.model = None  # TODO: test..
        else:
            self.widget.model = ct.model_class()

            self._choices_4_regularfields(ct, builders)
            self._choices_4_customfields(ct, builders)
            self._choices_4_functionfields(ct, builders)
            self._choices_4_relationtypes(ct, builders)

    # NB: _get_cfield_name() & _get_rtype() : we do linear searches because
    #     there are very few searches => build a dict wouldn't be faster
    def _get_cfield(self, cfield_id):
        for cfield in self._custom_fields:
            if cfield.id == cfield_id:
                return cfield

    def _get_rtype(self, rtype_id):
        for rtype in self._relation_types:
            if rtype.id == rtype_id:
                return rtype

    @property
    def non_hiddable_cells(self):
        return self._non_hiddable_cells

    @non_hiddable_cells.setter
    def non_hiddable_cells(self, cells):
        self._non_hiddable_cells[:] = cells
        # TODO: reset content_type

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = self.widget.user = user

    # TODO: to_python() + validate() instead ??
    def clean(self, value):
        assert self._content_type
        cells = []

        if value in EMPTY_VALUES:
            if self.required:
                raise ValidationError(self.error_messages['required'], code='required')
        else:
            model = self._content_type.model_class()
            get_builder = self._builders.get

            for elt in value.split(','):
                builder = get_builder(elt)

                if not builder:
                    raise ValidationError(self.error_messages['invalid'], code='invalid')

                cells.append(builder(self, model, elt))

        return cells


class _HeaderFilterForm(CremeModelForm):
    error_messages = {
        'orphan_private':  _('A private view of list must be assigned to a user/team.'),
        'foreign_private': _('A private view of list must belong to you (or one of your teams).')
    }

    cells = EntityCellsField(label=_('Columns'))

    blocks = CremeModelForm.blocks.new(('cells', _('Columns'), ['cells']))

    class Meta(CremeModelForm.Meta):
        model = HeaderFilter
        help_texts = {
            'user': _('All users can see the view, but only the owner can edit or delete it'),
            'is_private': _('A private view of list can only be used by its owner '
                            '(or the teammates if the owner is a team)'
                           ),
        }

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
                    self.add_error('user',
                                   ValidationError(self.error_messages['orphan_private'],
                                                   code='orphan_private',
                                                  )
                                  )
                else:
                    req_user = self.user

                    if not req_user.is_staff:
                        if owner.is_team:
                            if req_user.id not in owner.teammates:
                                self.add_error('user',
                                               ValidationError(self.error_messages['foreign_private'],
                                                               code='foreign_private',
                                                              )
                                              )
                        elif owner != req_user:
                            self.add_error('user',
                                           ValidationError(self.error_messages['foreign_private'],
                                                           code='foreign_private',
                                                          )
                                          )

            self.instance.cells = cdata['cells']

        return cdata


class HeaderFilterCreateForm(_HeaderFilterForm):
    def __init__(self, ctype, smart_columns_registry=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        registry = smart_columns_registry or listview.smart_columns_registry

        cells_f = self.fields['cells']
        cells_f.content_type = self.instance.entity_type = ctype
        cells_f.initial = registry.get_cells(ctype.model_class())

    @atomic
    def save(self, *args, **kwargs):
        instance = self.instance
        ct = instance.entity_type

        kwargs['commit'] = False
        super().save(*args, **kwargs)
        generate_string_id_and_save(HeaderFilter, [instance],
                                    'creme_core-userhf_{}-{}'.format(ct.app_label, ct.model)
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
        cells_f.content_type = instance.entity_type
        cells_f.initial = cells
