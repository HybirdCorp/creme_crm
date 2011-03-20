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

from django.db.models.fields import FieldDoesNotExist
from django.forms import Form, ModelForm, ModelChoiceField
from django.forms.forms import BoundField
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict as OrderedDict #use python2.6 OrderedDict later.....
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity


__all__ = ('FieldBlockManager', 'CremeForm', 'CremeModelForm', 'CremeModelWithUserForm', 'CremeEntityForm')


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
        result = OrderedDict()
        wildcard_cat = None
        field_set = set()

        for cat, block in self.__blocks.iteritems():
            field_names = block.field_names

            if field_names == '*': #wildcard
                result[cat] = block.name
                assert wildcard_cat is None, 'Only one wildcard is allowed: %s' % str(form)
                wildcard_cat = cat
            else:
                field_set |= set(field_names)
                result[cat] = (block.name, [(form[fn], form.fields[fn].required) for fn in field_names])

        if wildcard_cat is not None:
            block_name = result[wildcard_cat]
            result[wildcard_cat] = (block_name, [(form[name], field.required) for name, field in form.fields.iteritems() if name not in field_set])

        return result


class HookableForm(object):
    #Beware: use related method to manipulate
    _post_clean_callbacks = () # ==> add_post_clean_callback()
    _post_init_callbacks  = () # ==> add_post_init_callback()
    _post_save_callbacks  = () # ==> add_post_save_callback()

    @classmethod
    def __add_callback(cls, attrname, callback):
        callbacks = list(getattr(cls, attrname))
        callbacks.append(callback)
        setattr(cls, attrname, callbacks)

    @classmethod
    def add_post_clean_callback(cls, callback):
        cls.__add_callback('_post_clean_callbacks', callback)

    @classmethod
    def add_post_init_callback(cls, callback):
        cls.__add_callback('_post_init_callbacks', callback)

    @classmethod
    def add_post_save_callback(cls, callback):
        cls.__add_callback('_post_save_callbacks', callback)

    def _post_clean(self):
        for callback in self._post_clean_callbacks:
            callback(self)

    def _post_init(self):
        for callback in self._post_init_callbacks:
            callback(self)

    def _post_save(self):
        for callback in self._post_save_callbacks:
            callback(self)


class CremeForm(Form, HookableForm):
    blocks = FieldBlockManager(('general', _(u'General information'), '*'))

    def __init__(self, user, *args, **kwargs):
        """@param user The user that sends the request (i order to check the permissions)"""
        super(CremeForm, self).__init__(*args, **kwargs)
        self.user = user
        self._post_init()

    def clean(self, *args, **kwargs):
        res = super(CremeForm, self).clean(*args, **kwargs)
        self._post_clean()
        return res

    def get_blocks(self):
        return self.blocks.build(self)

    def save(self, *args, **kwargs):
        self._post_save()


class CremeModelForm(ModelForm, HookableForm):
    blocks = FieldBlockManager(('general', _(u'General information'), '*'))

    def __init__(self, user, *args, **kwargs):
        """@param user The user that sends the request (i order to check the permissions)"""
        super(CremeModelForm, self).__init__(*args, **kwargs)
        self.user = user
        self._post_init()

    def clean(self, *args, **kwargs):
        res = super(CremeModelForm, self).clean(*args, **kwargs)
        self._post_clean()
        return res

    def get_blocks(self):
        return self.blocks.build(self)

    def save(self, *args, **kwargs):
        instance = super(CremeModelForm, self).save(*args, **kwargs)
        self._post_save()
        return instance


class CremeModelWithUserForm(CremeModelForm):
    user = ModelChoiceField(label=_('User'), queryset=User.objects.all(), empty_label=None)

    def __init__(self, user, *args, **kwargs):
        super(CremeModelWithUserForm, self).__init__(user=user, *args, **kwargs)
        self.fields['user'].initial = user.id


class CremeEntityForm(CremeModelWithUserForm):
    class Meta:
        exclude = ('is_deleted', 'is_actived')

    def __init__(self, *args, **kwargs):
        super(CremeEntityForm, self).__init__(*args, **kwargs)
        assert self.instance, CremeEntity
        self._build_customfields()

        #Populate help_text in form widgets
        #Rule is form field help text or model field help text
        for field_name, form_field in self.fields.iteritems():
            try:
                model_field = self.instance._meta.get_field(field_name)
                help_text = form_field.help_text if form_field.help_text not in (None, u'') else model_field.help_text
                form_field.widget.help_text = help_text
            except FieldDoesNotExist:
                form_field.widget.help_text = form_field.help_text

    def _build_customfields(self):
        self._customs = self.instance.get_custom_fields_n_values()

        fields = self.fields

        for i, (cfield, cvalue) in enumerate(self._customs):
            fields[_CUSTOM_NAME % i] = cfield.get_formfield(cvalue)

    def save(self, *args, **kwargs):
        instance = super(CremeEntityForm, self).save(*args, **kwargs)
        cleaned_data = self.cleaned_data

        for i, (custom_field, custom_value) in enumerate(self._customs):
            value = cleaned_data[_CUSTOM_NAME % i] #TODO: factorize with _build_customfields() ?

            #TODO: in a CustomField method ???
            if custom_value:
                if not value:
                    custom_value.delete()
                else:
                    custom_value.set_value_n_save(value)
            elif value:
                custom_value = custom_field.get_value_class()(custom_field=custom_field, entity=instance)
                custom_value.set_value_n_save(value)

        return instance
