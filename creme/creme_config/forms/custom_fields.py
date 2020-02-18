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

from django.forms import TypedChoiceField, CharField, ValidationError
from django.forms.widgets import Textarea
from django.utils.translation import gettext_lazy as _, gettext

from creme.creme_core.forms import CremeModelForm
from creme.creme_core.forms.fields import EntityCTypeChoiceField, ListEditionField
from creme.creme_core.forms.widgets import DynamicSelect
from creme.creme_core.models.custom_field import CustomField, CustomFieldEnumValue, _TABLES

# TODO: User friendly order in choices fields
# TODO: rename CustomField*Form (without 's')


class CustomFieldsBaseForm(CremeModelForm):
    field_type  = TypedChoiceField(label=_('Type of field'), coerce=int,
                                   choices=[(i, klass.verbose_name) for i, klass in _TABLES.items()],
                                  )
    enum_values = CharField(widget=Textarea(), label=_('Available choices'), required=False,
                            help_text=_('Give the possible choices (one per line) '
                                        'if you choose the type "Choice list".'
                                       ),
                           )

    error_messages = {
        'empty_list': _('The choices list must not be empty '
                        'if you choose the type "Choice list".'
                       ),
    }

    class Meta(CremeModelForm.Meta):
        model = CustomField

    def clean(self):
        cdata = super().clean()

        if cdata.get('field_type') in (CustomField.ENUM, CustomField.MULTI_ENUM) \
           and not cdata['enum_values'].strip():
            raise ValidationError(self.error_messages['empty_list'],
                                  code='empty_list',
                                 )

        return cdata

    def save(self):
        instance = super().save()
        cleaned_data = self.cleaned_data

        if cleaned_data['field_type'] in (CustomField.ENUM, CustomField.MULTI_ENUM):
            create_enum_value = CustomFieldEnumValue.objects.create

            for enum_value in cleaned_data['enum_values'].splitlines():
                create_enum_value(custom_field=instance, value=enum_value)

        return instance


class CustomFieldsCTAddForm(CustomFieldsBaseForm):
    content_type = EntityCTypeChoiceField(
                        label=_('Related resource'),
                        help_text=_('The other custom fields for this type of resource '
                                    'will be chosen by editing the configuration'
                                   ),
                        widget=DynamicSelect({'autocomplete': True})
                    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        used_ct_ids = {*CustomField.objects.values_list('content_type_id', flat=True)}
        ct_field = self.fields['content_type']
        ct_field.ctypes = (ct for ct in ct_field.ctypes if ct.id not in used_ct_ids)


class CustomFieldsAddForm(CustomFieldsBaseForm):
    error_messages = {
        **CustomFieldsBaseForm.error_messages,
        'duplicated_name': _('There is already a custom field with this name.'),
    }

    class Meta(CustomFieldsBaseForm.Meta):
        exclude = ('content_type',)

    def __init__(self, ctype, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ct = ctype

    def clean_name(self):
        name = self.cleaned_data['name']

        if CustomField.objects.filter(content_type=self.ct, name=name).exists():
            raise ValidationError(self.error_messages['duplicated_name'],
                                  code='duplicated_name',
                                 )

        return name

    def save(self):
        self.instance.content_type = self.ct
        return super().save()


class CustomFieldsEditForm(CremeModelForm):
    # TODO: factorise
    error_messages = {
        'duplicated_name': _('There is already a custom field with this name.'),
    }

    class Meta:
        model = CustomField
        fields = ('name',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.field_type in (CustomField.ENUM, CustomField.MULTI_ENUM):
            self._enum_values = CustomFieldEnumValue.objects.filter(custom_field=self.instance)

            fields = self.fields
            fields['old_choices'] = ListEditionField(
                content=[enum.value for enum in self._enum_values],
                label=gettext('Existing choices of the list'),
                help_text=gettext('Uncheck the choices you want to delete.'),
            )
            fields['new_choices'] = CharField(
                widget=Textarea(), required=False,
                label=gettext('New choices of the list'),
                help_text=gettext('Give the new possible choices (one per line).'),
            )

    def clean_name(self):
        name = self.cleaned_data['name']
        instance = self.instance

        if CustomField.objects.filter(content_type=instance.content_type, name=name)\
                              .exclude(id=instance.id)\
                              .exists():
            raise ValidationError(self.error_messages['duplicated_name'],
                                  code='duplicated_name',
                                 )

        return name

    def save(self):
        cfield = super().save()

        if cfield.field_type in (CustomField.ENUM, CustomField.MULTI_ENUM):
            cleaned_data = self.cleaned_data

            for cfev, new_value in zip(self._enum_values, cleaned_data['old_choices']):
                if new_value is None:
                    cfev.delete()
                elif cfev.value != new_value:
                    cfev.value = new_value
                    cfev.save()

            create_enum_value = CustomFieldEnumValue.objects.create
            for enum_value in cleaned_data['new_choices'].splitlines():
                create_enum_value(custom_field=cfield, value=enum_value)

        return cfield
