# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from collections import OrderedDict
import logging

from django.contrib.auth import get_user_model
from django.db.models.fields import FieldDoesNotExist
from django.forms import Form, ModelForm, ModelChoiceField
from django.utils.translation import ugettext_lazy as _

from ..models import CremeEntity, CustomFieldValue, FieldsConfig


__all__ = ('FieldBlockManager', 'CremeForm', 'CremeModelForm',
           'CremeModelWithUserForm', 'CremeEntityForm',
          )

logger = logging.getLogger(__name__)
# _CUSTOM_NAME = 'custom_field_%s'
_CUSTOM_NAME = 'custom_field_{}'


class _FieldBlock:
    __slots__ = ('name', 'field_names')

    def __init__(self, verbose_name, field_names):
        """
        @param verbose_name: Name of the block (displayed in the output).
        @param field_names: Sequence of strings (fields names in the form)
               or string '*' (wildcard->all remaining fields).
        """
        self.name = verbose_name
        self.field_names = list(field_names) if field_names != '*' else field_names

    def __str__(self):  # For debugging
        return u'<_FieldBlock: {} {}>'.format(self.name, self.field_names)


class FieldBlocksGroup:
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

            if field_names == '*': # Wildcard
                blocks_data[cat] = block.name
                assert wildcard_cat is None, 'Only one wildcard is allowed: {}'.format(form)
                wildcard_cat = cat
            else:
                field_set |= set(field_names)
                block_data = []

                for fn in field_names:
                    try:
                        bound_field = form[fn]
                    except KeyError as e:
                        logger.debug('FieldBlocksGroup: %s', e)
                    else:
                        block_data.append((bound_field, form.fields[fn].required))

                blocks_data[cat] = (block.name, block_data)

        if wildcard_cat is not None:
            block_name = blocks_data[wildcard_cat]
            blocks_data[wildcard_cat] = (block_name,
                                         [(form[name], field.required)
                                              for name, field in form.fields.items()
                                                  if name not in field_set
                                         ],
                                        )

    def __getitem__(self, category):
        """Beware: it pops the retrieved value (__getitem__ is more comfortable
        to be used in templates than a classical method with an argument).
        @return A block descriptor (see FieldBlocksGroup doc string).
        """
        return self._blocks_data.pop(category)

    def __iter__(self):
        """Iterates on the non used blocks (see __getitem__).
        @return A sequence of block descriptors (see FieldBlocksGroup doc string).
        """
        return iter(self._blocks_data.values())


class FieldBlockManager:
    __slots__ = ('__blocks',)

    def __init__(self, *blocks):
        """Constructor.
        @param blocks tuples with 3 elements : category(string), verbose_name(i18n string), sequence of field names
                      3rd element can be instead a wildcard (the string '*') which mean 'all remaining fields'.
                      Only zero or one wildcard is allowed.
        """
        # Beware: use a list comprehension instead of a generator expression with this constructor
        self.__blocks = OrderedDict([(cat, _FieldBlock(name, field_names)) for cat, name, field_names in blocks])

    def new(self, *blocks):
        """Create a clone of self, updated with new blocks.
        @param blocks see __init__(). New blocks are merged with self's blocks.
        """
        merged_blocks = OrderedDict([(cat, _FieldBlock(block.name, block.field_names))
                                        for cat, block in self.__blocks.items()
                                    ]
                                   )
        to_add = []

        for cat, name, fields in blocks:
            field_block = merged_blocks.get(cat)

            if field_block is not None:
                field_block.name = name
                field_block.field_names.extend(fields)
            else:
                to_add.append((cat, _FieldBlock(name, fields)))  # Can't add during iteration

        for cat, field_block in to_add:
            merged_blocks[cat] = field_block

        fdm = FieldBlockManager()
        fdm.__blocks = merged_blocks  # Yerk....

        return fdm

    def build(self, form):
        """You should not call this directly ; see CremeForm/CremeModelForm
        get_blocks() method.
        @param form An instance of django.forms.Form.
        @return An instance of FieldBlocksGroup.
        """
        return FieldBlocksGroup(form, self.__blocks.items())


class HookableForm:
    # Beware: use related method to manipulate
    _creme_post_clean_callbacks = ()  # ==> add_post_clean_callback()
    _creme_post_init_callbacks  = ()  # ==> add_post_init_callback()
    _creme_post_save_callbacks  = ()  # ==> add_post_save_callback()

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

    def as_span(self):  # TODO: in another base class
        """Returns this form rendered as HTML <span>s."""
        return self._html_output(normal_row='<span%(html_class_attr)s>%(label)s %(field)s%(help_text)s</span>',
                                 error_row='%s',
                                 row_ender='</span>',
                                 help_text_html=' <span class="helptext">%s</span>',
                                 errors_on_separate_row=False,
                                )


class CremeForm(Form, HookableForm):
    blocks = FieldBlockManager(('general', _('General information'), '*'))

    def __init__(self, user, *args, **kwargs):
        """@param user The user who sends the request (i order to check the permissions)"""
        # super(CremeForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)
        self.user = user

        for fn, field in self.fields.items():
            field.user = user  # Used by CreatorModelChoiceField for example

        self._creme_post_init()

    def clean(self, *args, **kwargs):
        # res = super(CremeForm, self).clean(*args, **kwargs)
        res = super().clean(*args, **kwargs)
        self._creme_post_clean()
        return res

    def get_blocks(self):
        return self.blocks.build(self)

    def save(self, *args, **kwargs):
        self._creme_post_save()


class CremeModelForm(ModelForm, HookableForm):
    blocks = FieldBlockManager(('general', _('General information'), '*'))

    class Meta:
        fields = '__all__'

    def __init__(self, user, *args, **kwargs):
        """@param user The user that sends the request (in order to check the permissions)"""
        # super(CremeModelForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)
        self.user = user

        for fn, field in self.fields.items():
            field.user = user  # Used by CreatorModelChoiceField for example

        self.fields_configs = fc = FieldsConfig.LocalCache()
        fc.get_4_model(self.instance.__class__).update_form_fields(self.fields)

        self._creme_post_init()

    def clean(self, *args, **kwargs):
        # res = super(CremeModelForm, self).clean(*args, **kwargs)
        res = super().clean(*args, **kwargs)
        self._creme_post_clean()
        return res

    def get_blocks(self):
        return self.blocks.build(self)

    def save(self, *args, **kwargs):
        # instance = super(CremeModelForm, self).save(*args, **kwargs)
        instance = super().save(*args, **kwargs)
        self._creme_post_save()
        return instance


class CremeModelWithUserForm(CremeModelForm):
    user = ModelChoiceField(label=_('Owner user'), empty_label=None, queryset=None)

    def __init__(self, user, *args, **kwargs):
        # super(CremeModelWithUserForm, self).__init__(user=user, *args, **kwargs)
        super().__init__(user=user, *args, **kwargs)
        user_f = self.fields['user']
        user_f.queryset = get_user_model().objects.filter(is_staff=False)
        user_f.initial = user.id


class CremeEntityForm(CremeModelWithUserForm):
    class Meta:
        exclude = ()
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        # super(CremeEntityForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)
        assert self.instance, CremeEntity
        self._build_customfields()

        # TODO: move in CremeModelForm ???
        # Populate help_text in form widgets
        # Rule is form field help text or model field help text
        for field_name, form_field in self.fields.items():
            try:
                model_field = self.instance._meta.get_field(field_name)
                help_text = form_field.help_text if form_field.help_text not in (None, u'') else model_field.help_text
                form_field.widget.help_text = help_text
            except FieldDoesNotExist:
                form_field.widget.help_text = form_field.help_text

    def _build_customfields(self):
        self._customs = self.instance.get_custom_fields_n_values()

        fields = self.fields

        # TODO: why not use cfield.id as 'i' ??
        for i, (cfield, cvalue) in enumerate(self._customs):
            # fields[_CUSTOM_NAME % i] = cfield.get_formfield(cvalue)
            fields[_CUSTOM_NAME.format(i)] = cfield.get_formfield(cvalue)

    def save(self, *args, **kwargs):
        # instance = super(CremeEntityForm, self).save(*args, **kwargs)
        instance = super().save(*args, **kwargs)
        cleaned_data = self.cleaned_data

        for i, (custom_field, custom_value) in enumerate(self._customs):
            # value = cleaned_data[_CUSTOM_NAME % i]
            value = cleaned_data[_CUSTOM_NAME.format(i)]  # TODO: factorize with _build_customfields() ?
            CustomFieldValue.save_values_for_entities(custom_field, [instance], value)

        return instance
