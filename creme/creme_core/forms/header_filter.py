# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from ..gui.field_printers import field_printers_registry
from ..models.header_filter import (HeaderFilterItem, HeaderFilter,
                            HFI_FIELD, HFI_RELATION, HFI_FUNCTION, HFI_CUSTOM)
from ..models import RelationType, CustomField, EntityCredentials
from ..utils.id_generator import generate_string_id_and_save
from ..utils.meta import ModelFieldEnumerator
from ..utils.unicode_collation import collator
from .base import CremeModelForm


_RFIELD_PREFIX = 'rfield-'
_CFIELD_PREFIX = 'cfield-'
_FFIELD_PREFIX = 'ffield-'
_RTYPE_PREFIX  = 'rtype-'

_PREFIXES_MAP = {
    HFI_FIELD:    _RFIELD_PREFIX,
    HFI_CUSTOM:   _CFIELD_PREFIX,
    HFI_FUNCTION: _FFIELD_PREFIX,
    HFI_RELATION: _RTYPE_PREFIX,
}


class HeaderFilterItemsWidget(Widget):
    def __init__(self, user=None, model=None, model_fields=(), model_subfields=(), custom_fields=(),
                 function_fields=(), relation_types=(), *args, **kwargs
                ):
        super(HeaderFilterItemsWidget, self).__init__(*args, **kwargs)
        self.user = user
        self.model = model

        self.model_fields = model_fields
        self.model_subfields = model_subfields
        self.custom_fields = custom_fields
        self.function_fields = function_fields
        self.relation_types = relation_types

    def _build_samples(self):
        user = self.user
        model = self.model
        samples = []

        #TODO: factorise with HF/listview templatetags
        print_field_value = field_printers_registry.get_html_field_value
        LEN_RFIELD_PREFIX = len(_RFIELD_PREFIX)

        get_func_field = model.function_fields.get
        LEN_FFIELD_PREFIX = len(_FFIELD_PREFIX)

        for entity in EntityCredentials.filter(user, self.model.objects.order_by('-modified'))[:2]:
            dump = {}

            #TODO: genexpr ?
            for field_id, field_vname in self.model_fields:
                dump[field_id] = unicode(print_field_value(entity, field_id[LEN_RFIELD_PREFIX:], user))

            for choices in self.model_subfields.itervalues():
                for field_id, field_vname in choices:
                    try:
                        value = unicode(print_field_value(entity, field_id[LEN_RFIELD_PREFIX:], user))
                    except Exception: #print_field_value can raise AttributeError if M2M is empty...
                        value = ''

                    dump[field_id] = value

            #missing CustomFields and Relationships

            for field_id, field_vname in self.function_fields:
                dump[field_id] = get_func_field(field_id[LEN_FFIELD_PREFIX:])(entity).for_html()

            samples.append(dump)

        return samples

    def render(self, name, value, attrs=None):
        attrs_map = self.build_attrs(attrs, name=name)

        if isinstance(value, list):
            value = ','.join(_PREFIXES_MAP[item.type] + item.name for item in value)

        return render_to_string('creme_core/header_filter_items_widget.html',
                                {'attrs': mark_safe(flatatt(attrs)),
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
                               )


class HeaderFilterItemsField(Field):
    widget = HeaderFilterItemsWidget

    def __init__(self, content_type=None, *args, **kwargs):
        super(HeaderFilterItemsField, self).__init__(*args, **kwargs)
        self.content_type = content_type
        self.user = None

    def _build_4_field(self, model, name):
        return HeaderFilterItem.build_4_field(model=model, name=name[len(_RFIELD_PREFIX):])

    def _build_4_customfield(self, model, name):
        return HeaderFilterItem.build_4_customfield(self._get_cfield(int(name[len(_CFIELD_PREFIX):])))

    def _build_4_functionfield(self, model, name):
        return HeaderFilterItem.build_4_functionfield(model.function_fields.get(name[len(_FFIELD_PREFIX):]))

    def _build_4_relation(self, model, name):
        return HeaderFilterItem.build_4_relation(self._get_rtype(name[len(_RTYPE_PREFIX):]))

    @property
    def content_type(self):
        return self._content_type

    @content_type.setter
    def content_type(self, ct):
        self._content_type = ct

        if ct is None:
            self._model_fields = self._model_subfields = self._custom_fields \
                               = self._function_fields = self._relation_types \
                               = ()
        else:
            widget = self.widget
            model = widget.model = ct.model_class()
            self._builders = builders = {}

            #caches
            self._relation_types = RelationType.get_compatible_ones(ct, include_internals=True) \
                                               .order_by('predicate') #TODO: unicode collation
            self._custom_fields  = CustomField.objects.filter(content_type=ct)

            #TODO: factorise ??

            #Regular Fields --------------------------------------------------
            #TODO: make the managing of subfields by the widget ??
            #TODO: remove subfields with len() == 1 (done in template for now)
            rfields_choices = []
            subfields_choices = defaultdict(list) #TODO: sort too ??

            for fields_info in ModelFieldEnumerator(model, deep=1, only_leafs=False).filter(viewable=True):
                choices = rfields_choices if len(fields_info) == 1 else \
                          subfields_choices[_RFIELD_PREFIX + fields_info[0].name] #FK, M2M

                field_id = _RFIELD_PREFIX + '__'.join(field.name for field in fields_info)
                choices.append((field_id, unicode(fields_info[-1].verbose_name)))
                builders[field_id] = HeaderFilterItemsField._build_4_field

            sort_key = collator.sort_key
            sort_choice = lambda k: sort_key(k[1]) #TODO: in utils ?
            rfields_choices.sort(key=sort_choice)

            for subfield_choices in subfields_choices.itervalues():
                subfield_choices.sort(key=sort_choice)

            widget.model_fields = rfields_choices
            widget.model_subfields = subfields_choices

            #Custom Fields ---------------------------------------------------
            widget.custom_fields = cfields_choices = [] #TODO: sort ?

            for cf in self._custom_fields:
                field_id = _CFIELD_PREFIX + str(cf.id)
                cfields_choices.append((field_id, cf.name))
                builders[field_id] = HeaderFilterItemsField._build_4_customfield

            #Function Fields -------------------------------------------------
            widget.function_fields = ffields_choices = [] #TODO: sort ?

            for f in model.function_fields:
                field_id = _FFIELD_PREFIX + f.name
                ffields_choices.append((field_id, f.verbose_name))
                builders[field_id] = HeaderFilterItemsField._build_4_functionfield

            #Relationships ---------------------------------------------------
            #TODO: sort ? smart categories ('all', 'contacts') ?
            widget.relation_types = rtypes_choices = []

            for rtype in self._relation_types:
                field_id = _RTYPE_PREFIX + rtype.id
                rtypes_choices.append((field_id, rtype.predicate))
                builders[field_id] = HeaderFilterItemsField._build_4_relation

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
        hf_items = []

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

                hf_items.append(builder(self, model, elt))

        return hf_items


#TODO: create and edit form ????
class HeaderFilterForm(CremeModelForm):
    items = HeaderFilterItemsField(label=_(u'Columns'))

    blocks = CremeModelForm.blocks.new(('items', _('Columns'), ['items']))

    class Meta:
        model = HeaderFilter

    def __init__(self, *args, **kwargs):
        super(HeaderFilterForm, self).__init__(*args, **kwargs)
        instance = self.instance
        fields   = self.fields

        user_f = fields['user']
        user_f.empty_label = _(u'All users')
        user_f.help_text   = _(u'All users can see the view, but only the owner can edit or delete it')

        items_f = fields['items']

        if instance.id:
            items_f.content_type = instance.entity_type
            items_f.initial = instance.items
        else:
            items_f.content_type = instance.entity_type = self.initial.get('content_type')
            #TODO: popular fields prechecked ??

    @commit_on_success
    def save(self):
        instance = self.instance
        instance.is_custom = True

        if instance.id:
            super(HeaderFilterForm, self).save()
        else:
            ct = instance.entity_type

            super(HeaderFilterForm, self).save(commit=False)
            generate_string_id_and_save(HeaderFilter, [instance],
                                        'creme_core-userhf_%s-%s' % (ct.app_label, ct.model)
                                       )

        instance.set_items(self.cleaned_data['items'])

        return instance
