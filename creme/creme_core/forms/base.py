# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

#from logging import debug

from django import forms
from django.forms import Form, ModelForm, ModelChoiceField
from django.forms.forms import BoundField
from django.utils.translation import ugettext as _
from django.utils.datastructures import SortedDict as OrderedDict #use python2.6 OrderedDict later.....
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, CustomField, CustomFieldValue, CustomFieldEnumValue


_FIELD_TYPES = {
                CustomField.INT:   forms.IntegerField,
                CustomField.FLOAT: forms.DecimalField,
                CustomField.STR:   forms.CharField,
                CustomField.ENUM:  forms.ChoiceField,
               }

_CUSTOM_NAME = 'custom_field_%s'


class _FieldBlock(object):
    __slots__ = ('name', 'field_names')

    def __init__(self, verbose_name, field_names):
        """
        @param verbose_name name of the block (displayed in the output)
        @param field_names sequence of strings (fields names in the form) or string '*' (wildcard->all remainings fields)
        """
        self.name        = verbose_name
        self.field_names = list(field_names) if field_names != '*' else field_names

    def __unicode__(self): #to debug
        return u'<_FieldBlock: %s %s>' % (self.name, self.field_names)


class FieldBlockManager(object):
    __slots__ = ('__blocks',)

    def __init__(self, *blocks):
        """
        @param blocks tuples with 3 elements : category(string), verbose_name(i18n string), sequence of field names
                      3rd element can be instead a wildcard (the string '*') which mean 'all remaining fields'.
                      Only zero or one wildcard is allowed.
        """
        #beware: use a list comprehension instead of a generator expression with this constructor
        self.__blocks = OrderedDict([(cat, _FieldBlock(name, field_names)) for cat, name, field_names in blocks])

    def new(self, *blocks):
        """
        Create a clone of self, updated with new blocks.
        @param blocks see __init__(). New blocks are merged with self's blocks.
        """
        merged_blocks = OrderedDict([(cat, _FieldBlock(block.name, block.field_names)) for cat, block in self.__blocks.iteritems()])
        to_add        = []

        for cat, name, fields in blocks:
            field_block = merged_blocks.get(cat)

            if field_block is not None:
                field_block.name = name
                field_block.field_names.extend(fields)
            else:
                to_add.append((cat, _FieldBlock(name, fields))) #can't add during iteration

        for cat, field_block in to_add:
            merged_blocks[cat] = field_block

        fdm = FieldBlockManager()
        fdm.__blocks = merged_blocks #bof....

        return fdm

    def build(self, form): #build in the blocks objects themselves ??
        """
        @return A list of block descriptors. A blocks descriptor is a tuple
               (block_verbose_name, [list of tuples (BoundField, fiels_is_required)]).
        """
        result = []
        wildcard_index = None
        field_set = set()

        for i, block in enumerate(self.__blocks.itervalues()):
            field_names = block.field_names

            if field_names == '*': #wildcard
                result.append(block.name)
                assert wildcard_index is None, 'Only one wildcard is allowed: %s' % str(form)
                wildcard_index = i
            else:
                field_set |= set(field_names)
                result.append((block.name, [(form[fn], form.fields[fn].required) for fn in field_names]))

        if wildcard_index is not None:
            block_name = result[wildcard_index]
            result[wildcard_index] = (block_name, [(form[name], field.required) for name, field in form.fields.iteritems() if name not in field_set])

        return result


class CremeForm(Form):
    blocks = FieldBlockManager(('general', _(u'Informations générales'), '*'))

    def get_blocks(self):
        return self.blocks.build(self)


class CremeModelForm(ModelForm):
    #user = ModelChoiceField(label=_('Utilisateur'), queryset=User.objects.all(), empty_label=None) #TODO: in a CremeEntityForm ??

    callback_url = None
    blocks       = FieldBlockManager(('general', _(u'Informations générales'), '*'))
    exclude      = ('is_deleted', 'is_actived') #remove ??

    class Meta:
        exclude = ('is_deleted', 'is_actived') #TODO: in a CremeEntityForm ??

    def __init__(self, *args, **kwargs):
        super(CremeModelForm, self).__init__(*args, **kwargs)

        if isinstance(self.instance, CremeEntity): #TODO: in a CremeEntityForm  instead ???
            self._build_customfields()

    def get_blocks(self):
        return self.blocks.build(self)

#COMMENTED 29 june 2010
#    def get_value_for_field(self, field_name):
#        """Return value for a field"""
#        data = None
#        if field_name in self.fields.keys():
#            bf = BoundField(self, self.fields[field_name], field_name)
#            if not self.is_bound:
#                data = self.initial.get(field_name, bf.field.initial)
#                if callable(data):
#                    data = data()
#            else:
#                data = bf.data
#        return data

    def _build_formfield(self, custom_field):
        field =  _FIELD_TYPES[custom_field.field_type](label=custom_field.name, required=False)

        if custom_field.field_type == CustomField.ENUM:
            choices = [('', '-------')]
            choices += CustomFieldEnumValue.objects.filter(custom_field=custom_field).values_list('id', 'value')
            field.choices = choices

        customvalue = self._customvalues.get(custom_field.id, '')

        if customvalue:
            field.initial = customvalue.value

        return field

    def _build_customfields(self): #TODO: in a CremeEntityForm ??
        #move to CremeEntity ???
        cfields = CustomField.objects.filter(content_type=ContentType.objects.get_for_model(self.instance))

        if not cfields:
            self._customfields = ()
            self._customvalues = {}
            return

        self._customfields = cfields

        entity = self.instance

        if entity.id: #EDITION
            #TODO: factorise with CremeEntity.get_custom_fields() ???
             self._customvalues = dict((cfv.custom_field_id, cfv)
                                            for cfv in CustomFieldValue.objects.filter(custom_field__in=cfields,
                                                                                       entity=entity.id))
        else: #CREATION
            self._customvalues = {}

        fields = self.fields
        for i, cfield in enumerate(cfields):
            fields[_CUSTOM_NAME % i] = self._build_formfield(cfield)

    def save(self, *args, **kwargs):
        super(CremeModelForm, self).save(*args, **kwargs)

        if not isinstance(self.instance, CremeEntity): ####
            return

        cleaned_data = self.cleaned_data
        instance     = self.instance

        for i, cfield in enumerate(self._customfields):
            value = cleaned_data[_CUSTOM_NAME % i] #TODO: factorize with _build_customfields() ?
            customvalue = self._customvalues.get(cfield.id)

            if customvalue:
                if value:
                    customvalue.value = value
                    customvalue.save() #TODO: save only if there is a change ??
                else:
                    customvalue.delete()
            elif value:
                CustomFieldValue.objects.create(custom_field=cfield, entity=instance, value=value)
