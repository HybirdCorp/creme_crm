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

from django.db.models.fields import FieldDoesNotExist
from django.forms import Form, ModelForm, ModelChoiceField
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict as OrderedDict #use python2.7 OrderedDict later.....
from django.contrib.auth.models import User

from ..models import CremeEntity, CustomFieldValue


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


class FieldBlocksGroup(object):
    """You should not build them directly ; use FieldBlockManager.build() instead.
    It contains a list of block descriptors. A blocks descriptor is a tuple
    (block_verbose_name, [list of tuples (BoundField, field_is_required)]).
    """
    def __init__(self, form, blocks_items):
        self._blocks_data = blocks_data = OrderedDict()
        wildcard_cat = None
        field_set = set()

        for cat, block in blocks_items:
            field_names = block.field_names

            if field_names == '*': #wildcard
                blocks_data[cat] = block.name
                assert wildcard_cat is None, 'Only one wildcard is allowed: %s' % str(form)
                wildcard_cat = cat
            else:
                field_set |= set(field_names)
                blocks_data[cat] = (block.name, [(form[fn], form.fields[fn].required) for fn in field_names])

        if wildcard_cat is not None:
            block_name = blocks_data[wildcard_cat]
            blocks_data[wildcard_cat] = (block_name,
                                         [(form[name], field.required)
                                              for name, field in form.fields.iteritems()
                                                  if name not in field_set
                                         ],
                                        )

    def __getitem__(self, category):
        """Beware: it pops the retreieved value (__getitem__ is more confortable
        to be used in templates than a classical method with an argument).
        @return A block descriptor (see FieldBlocksGroup doc string).
        """
        return self._blocks_data.pop(category)

    def __iter__(self):
        """Iterates on the non used blocks (see __getitem__).
        @return A sequence of block descriptors (see FieldBlocksGroup doc string).
        """
        return self._blocks_data.itervalues()


class FieldBlockManager(object):
    __slots__ = ('__blocks',)

    def __init__(self, *blocks):
        """Constructor.
        @param blocks tuples with 3 elements : category(string), verbose_name(i18n string), sequence of field names
                      3rd element can be instead a wildcard (the string '*') which mean 'all remaining fields'.
                      Only zero or one wildcard is allowed.
        """
        #beware: use a list comprehension instead of a generator expression with this constructor
        self.__blocks = OrderedDict([(cat, _FieldBlock(name, field_names)) for cat, name, field_names in blocks])

    def new(self, *blocks):
        """Create a clone of self, updated with new blocks.
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

    def build(self, form):
        """You should not call this directly ; see CremeForm/CremeModelForm
        get_blocks() method.
        @param form An instance of django.forms.Form.
        @return An instance of FieldBlocksGroup.
        """
        return FieldBlocksGroup(form, self.__blocks.iteritems())


class HookableForm(object):
    #Beware: use related method to manipulate
    _creme_post_clean_callbacks = () # ==> add_post_clean_callback()
    _creme_post_init_callbacks  = () # ==> add_post_init_callback()
    _creme_post_save_callbacks  = () # ==> add_post_save_callback()

    @classmethod
    def __add_callback(cls, attrname, callback):
        callbacks = list(getattr(cls, attrname))
        callbacks.append(callback)
        setattr(cls, attrname, callbacks)

    @classmethod
    def add_post_clean_callback(cls, callback):
        cls.__add_callback('_creme_post_clean_callbacks', callback)

    @classmethod
    def add_post_init_callback(cls, callback):
        cls.__add_callback('_creme_post_init_callbacks', callback)

    @classmethod
    def add_post_save_callback(cls, callback):
        cls.__add_callback('_creme_post_save_callbacks', callback)

    def _creme_post_clean(self):
        for callback in self._creme_post_clean_callbacks:
            callback(self)

    def _creme_post_init(self):
        for callback in self._creme_post_init_callbacks:
            callback(self)

    def _creme_post_save(self):
        for callback in self._creme_post_save_callbacks:
            callback(self)

    def as_span(self): #TODO: in another base class
        """Returns this form rendered as HTML <span>s."""
        return self._html_output(normal_row=u'<span%(html_class_attr)s>%(label)s %(field)s%(help_text)s</span>',
                                 error_row=u'%s',
                                 row_ender='</span>',
                                 help_text_html=u' <span class="helptext">%s</span>',
                                 errors_on_separate_row=False,
                                )


class CremeForm(Form, HookableForm):
    blocks = FieldBlockManager(('general', _(u'General information'), '*'))

    def __init__(self, user, *args, **kwargs):
        """@param user The user that sends the request (i order to check the permissions)"""
        super(CremeForm, self).__init__(*args, **kwargs)
        self.user = user

        for fn, field in self.fields.iteritems():
            field.user = user #used by CreatorModelChoiceField for example

        self._creme_post_init()

    def clean(self, *args, **kwargs):
        res = super(CremeForm, self).clean(*args, **kwargs)
        self._creme_post_clean()
        return res

    def get_blocks(self):
        return self.blocks.build(self)

    def save(self, *args, **kwargs):
        self._creme_post_save()


class CremeModelForm(ModelForm, HookableForm):
    blocks = FieldBlockManager(('general', _(u'General information'), '*'))

    def __init__(self, user, *args, **kwargs):
        """@param user The user that sends the request (i order to check the permissions)"""
        super(CremeModelForm, self).__init__(*args, **kwargs)
        self.user = user

        for fn, field in self.fields.iteritems():
            field.user = user #used by CreatorModelChoiceField for example

        self._creme_post_init()

    def clean(self, *args, **kwargs):
        res = super(CremeModelForm, self).clean(*args, **kwargs)
        self._creme_post_clean()
        return res

    def get_blocks(self):
        return self.blocks.build(self)

    def save(self, *args, **kwargs):
        instance = super(CremeModelForm, self).save(*args, **kwargs)
        self._creme_post_save()
        return instance


class CremeModelWithUserForm(CremeModelForm):
    user = ModelChoiceField(label=_('Owner user'), queryset=User.objects.filter(is_staff=False), empty_label=None) #label=_('User')

    def __init__(self, user, *args, **kwargs):
        super(CremeModelWithUserForm, self).__init__(user=user, *args, **kwargs)
        self.fields['user'].initial = user.id


class CremeEntityForm(CremeModelWithUserForm):
    class Meta: #TODO: remove ???
        exclude = () #'is_deleted', 'is_actived'

    def __init__(self, *args, **kwargs):
        super(CremeEntityForm, self).__init__(*args, **kwargs)
        assert self.instance, CremeEntity
        self._build_customfields()

        #TODO: move in CremeModelForm ???
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
            CustomFieldValue.save_values_for_entities(custom_field, [instance], value)

        return instance
