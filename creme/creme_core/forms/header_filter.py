# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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
from json import dumps as json_dump

from django.db.transaction import commit_on_success
from django.forms.fields import EMPTY_VALUES, Field, ValidationError
from django.forms.util import flatatt
from django.forms.widgets import Widget
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from ..core.entity_cell import (EntityCellRegularField,
        EntityCellCustomField, EntityCellFunctionField, EntityCellRelation)
from ..gui.listview import smart_columns_registry
from ..models import CremeEntity, RelationType, CustomField, EntityCredentials, HeaderFilter
from ..utils.id_generator import generate_string_id_and_save
from ..utils.meta import ModelFieldEnumerator
from ..utils.unicode_collation import collator
from .base import CremeModelForm


_RFIELD_PREFIX = EntityCellRegularField.type_id + '-'
_CFIELD_PREFIX = EntityCellCustomField.type_id + '-'
_FFIELD_PREFIX = EntityCellFunctionField.type_id + '-'
_RTYPE_PREFIX  = EntityCellRelation.type_id + '-'


#TODO: move to a separated file ??
class EntityCellsWidget(Widget):
    def __init__(self, user=None, model=None, model_fields=(), model_subfields=None, custom_fields=(),
                 function_fields=(), relation_types=(), *args, **kwargs
                ):
        super(EntityCellsWidget, self).__init__(*args, **kwargs)
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
                        for choices in self.model_subfields.itervalues()
                            for field_id, field_vname in choices
                    )

        PREFIX = len(_FFIELD_PREFIX); build = EntityCellFunctionField.build
        cells.extend((field_id, build(model, field_id[PREFIX:]))
                        for field_id, field_vname in self.function_fields
                    )

        #missing CustomFields and Relationships

        for entity in EntityCredentials.filter(user, self.model.objects.order_by('-modified'))[:2]:
            dump = {}

            for field_id, cell in cells:
                try:
                    value = unicode(cell.render_html(entity, user))
                except Exception:
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

    def _build_render_context(self, name, value, attrs):
        attrs_map = self.build_attrs(attrs, name=name)

        if isinstance(value, list):
            value = ','.join('%s-%s' % (cell.type_id, cell.value) for cell in value)

        return {'attrs': mark_safe(flatatt(attrs)),
                'id':    attrs_map['id'],
                'name':  name,
                'value': value or '',

                'samples': mark_safe(json_dump(self._build_samples())),

                'model_fields':    self.model_fields,
                'model_subfields': self.model_subfields,
                'custom_fields':   self.custom_fields,
                'function_fields': self.function_fields,
                'relation_types':  self.relation_types,
               }

    def render(self, name, value, attrs=None):
        return render_to_string('creme_core/entity_cells_widget.html',
                                self._build_render_context( name, value, attrs)
                               )


class EntityCellsField(Field):
    widget = EntityCellsWidget

    def __init__(self, content_type=None, *args, **kwargs):
        super(EntityCellsField, self).__init__(*args, **kwargs)
        self.content_type = content_type
        self.user = None

    def _build_4_regularfield(self, model, name):
        return EntityCellRegularField.build(model=model, name=name[len(_RFIELD_PREFIX):])

    def _build_4_customfield(self, model, name):
        return EntityCellCustomField(self._get_cfield(int(name[len(_CFIELD_PREFIX):])))

    def _build_4_functionfield(self, model, name):
        return EntityCellFunctionField.build(model, name[len(_FFIELD_PREFIX):])

    def _build_4_relation(self, model, name):
        return EntityCellRelation(self._get_rtype(name[len(_RTYPE_PREFIX):]))

    def _choices_4_customfields(self, ct, builders):
        self._custom_fields = CustomField.objects.filter(content_type=ct) #cache
        self.widget.custom_fields = cfields_choices = [] #TODO: sort ?

        for cf in self._custom_fields:
            field_id = _CFIELD_PREFIX + str(cf.id)
            cfields_choices.append((field_id, cf.name))
            builders[field_id] = EntityCellsField._build_4_customfield

    def _choices_4_functionfields(self, ct, builders):
        self.widget.function_fields = ffields_choices = [] #TODO: sort ?

        for f in ct.model_class().function_fields:
            field_id = _FFIELD_PREFIX + f.name
            ffields_choices.append((field_id, f.verbose_name))
            builders[field_id] = EntityCellsField._build_4_functionfield

    def _regular_fields_enum(self, model): #this separated method make overloading easier (see reports)
        return ModelFieldEnumerator(model, deep=1, only_leafs=False).filter(viewable=True)

    def _choices_4_regularfields(self, ct, builders):
        #TODO: make the managing of subfields by the widget ??
        #TODO: remove subfields with len() == 1 (done in template for now)
        widget = self.widget
        widget.model_fields = rfields_choices = []
        widget.model_subfields = subfields_choices = defaultdict(list) #TODO: sort too ??

        for fields_info in self._regular_fields_enum(ct.model_class()):
            choices = rfields_choices if len(fields_info) == 1 else \
                      subfields_choices[_RFIELD_PREFIX + fields_info[0].name] #FK, M2M

            field_id = _RFIELD_PREFIX + '__'.join(field.name for field in fields_info)
            choices.append((field_id, unicode(fields_info[-1].verbose_name)))
            builders[field_id] = EntityCellsField._build_4_regularfield

        sort_key = collator.sort_key
        sort_choice = lambda k: sort_key(k[1]) #TODO: in utils ?
        rfields_choices.sort(key=sort_choice)

        for subfield_choices in subfields_choices.itervalues():
            subfield_choices.sort(key=sort_choice)

    def _choices_4_relationtypes(self, ct, builders):
        #cache
        self._relation_types = RelationType.get_compatible_ones(ct, include_internals=True) \
                                           .order_by('predicate') #TODO: unicode collation
        #TODO: sort ? smart categories ('all', 'contacts') ?
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
            self.widget.model = None #TODO: test..
            #self.widget.model_fields = () TODO: etc... (widget.reset() ??)
        else:
            self.widget.model = ct.model_class()

            self._choices_4_regularfields(ct, builders)
            self._choices_4_customfields(ct, builders)
            self._choices_4_functionfields(ct, builders)
            self._choices_4_relationtypes(ct, builders)

    #NB: _get_cfield_name() & _get_rtype() : we do linear searches because
    #   there are very few searches => build a dict wouldn't be faster
    def _get_cfield(self, cfield_id):
        for cfield in self._custom_fields:
            if cfield.id == cfield_id:
                return cfield

    def _get_rtype(self, rtype_id):
        for rtype in self._relation_types:
            if rtype.id == rtype_id:
                return rtype

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = self.widget.user = user

    #TODO: to_python() + validate() instead ??
    def clean(self, value):
        assert self._content_type
        cells = []

        if value in EMPTY_VALUES:
            if self.required:
                raise ValidationError(self.error_messages['required'])
        else:
            model = self._content_type.model_class()
            get_builder = self._builders.get

            for elt in value.split(','):
                builder = get_builder(elt)

                if not builder:
                    raise ValidationError(self.error_messages['invalid'])

                cells.append(builder(self, model, elt))

        return cells


#TODO: create and edit form ????
class HeaderFilterForm(CremeModelForm):
    cells = EntityCellsField(label=_(u'Columns'))

    blocks = CremeModelForm.blocks.new(('cells', _('Columns'), ['cells']))

    class Meta:
        model = HeaderFilter

    def __init__(self, *args, **kwargs):
        super(HeaderFilterForm, self).__init__(*args, **kwargs)
        instance = self.instance
        fields   = self.fields

        user_f = fields['user']
        user_f.empty_label = _(u'All users')
        user_f.help_text   = _(u'All users can see the view, but only the owner can edit or delete it')

        cells_f = fields['cells']

        if instance.id:
            cells_f.content_type = instance.entity_type
            cells_f.initial = instance.cells
        else:
            cells_f.content_type = instance.entity_type = ct = self.initial.get('content_type')
            cells_f.initial = smart_columns_registry.get_cells(ct.model_class())

    @commit_on_success
    def save(self):
        instance = self.instance
        instance.is_custom = True
        instance.cells = self.cleaned_data['cells']

        if instance.id:
            super(HeaderFilterForm, self).save()
        else:
            ct = instance.entity_type

            super(HeaderFilterForm, self).save(commit=False)
            generate_string_id_and_save(HeaderFilter, [instance],
                                        'creme_core-userhf_%s-%s' % (ct.app_label, ct.model)
                                       )

        return instance
