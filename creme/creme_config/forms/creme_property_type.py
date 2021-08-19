# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.forms import BooleanField, CharField, ValidationError
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeForm, MultiEntityCTypeChoiceField
from creme.creme_core.models import CremePropertyType


class _CremePropertyTypeBaseForm(CremeForm):
    text = CharField(label=_('Text'), help_text=_("For example: 'is pretty'"))
    is_copiable = BooleanField(
        label=_('Is copiable'), initial=True, required=False,
        help_text=_(
            'Are the properties with this type copied when an entity is cloned?'
        ),
    )
    subject_ctypes = MultiEntityCTypeChoiceField(
        label=_('Related to types of entities'),
        help_text=_('No selected type means that all types are accepted'),
        required=False,
    )

    def __init__(self, instance=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance


class CremePropertyTypeAddForm(_CremePropertyTypeBaseForm):
    error_messages = {
        'duplicated_name': _('A property type with this name already exists.'),
    }

    def clean_text(self):
        text = self.cleaned_data['text']

        # TODO: unique constraint in model too ??
        if CremePropertyType.objects.filter(text=text).exists():
            raise ValidationError(
                self.error_messages['duplicated_name'],
                code='duplicated_name',
            )

        return text

    def save(self):
        get_data = self.cleaned_data.get
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='creme_config-userproperty',
            text=get_data('text'),
            subject_ctypes=get_data('subject_ctypes'),
            is_custom=True, generate_pk=True,
            is_copiable=get_data('is_copiable'),
        )
        super().save()

        return ptype


class CremePropertyTypeEditForm(_CremePropertyTypeBaseForm):
    def __init__(self, instance, *args, **kwargs):
        super().__init__(instance=instance, *args, **kwargs)
        fields = self.fields

        fields['text'].initial = instance.text
        fields['is_copiable'].initial = instance.is_copiable
        fields['subject_ctypes'].initial = [
            ct.id for ct in instance.subject_ctypes.all()
        ]

    def save(self):
        get_data = self.cleaned_data.get
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk=self.instance.id,
            text=get_data('text'),
            subject_ctypes=get_data('subject_ctypes'),
            is_custom=True,
            is_copiable=get_data('is_copiable'),
        )
        super().save()

        return ptype
