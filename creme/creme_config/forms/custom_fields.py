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

from itertools import izip

from django.forms import TypedChoiceField, ModelChoiceField, CharField, ValidationError
from django.forms.widgets import Textarea
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.contenttypes.models import ContentType

from creme_core.models.custom_field import CustomField, CustomFieldEnumValue, _TABLES
from creme_core.forms import CremeModelForm
from creme_core.forms.fields import ListEditionField
from creme_core.utils import creme_entity_content_types


class CustomFieldsBaseForm(CremeModelForm):
    field_type  = TypedChoiceField(label=_(u'Type of field'), choices=[(i, klass.verbose_name) for i, klass in _TABLES.iteritems()], coerce=int)
    enum_values = CharField(widget=Textarea(), label=_(u'List content'), required=False,
                            help_text=_(u'Give the possible  choices (one per line) if you choose the type "Choices list".'))

    class Meta:
        model = CustomField

    def clean(self):
        cdata = self.cleaned_data

        if cdata['field_type'] in (CustomField.ENUM, CustomField.MULTI_ENUM) and not cdata['enum_values'].strip():
            raise ValidationError(ugettext(u'The choices list must not be empty if you choose the type "Choices list".'))

        return cdata

    def save(self):
        super(CustomFieldsBaseForm, self).save()

        cleaned_data = self.cleaned_data

        if cleaned_data['field_type'] in (CustomField.ENUM, CustomField.MULTI_ENUM):
            create_enum_value = CustomFieldEnumValue.objects.create
            cfield = self.instance

            for enum_value in cleaned_data['enum_values'].splitlines():
                create_enum_value(custom_field=cfield, value=enum_value)


class CustomFieldsCTAddForm(CustomFieldsBaseForm):
    content_type = ModelChoiceField(label=_(u'Related resource'), queryset=ContentType.objects.none(),
                                    help_text=_(u'The other custom fields for this type of resource will be chosen by editing the configuration'))

    def __init__(self, *args, **kwargs):
        super(CustomFieldsCTAddForm, self).__init__(*args, **kwargs)

        entity_ct_ids = set(ct.id for ct in creme_entity_content_types())
        used_ct_ids   = set(CustomField.objects.values_list('content_type_id', flat=True))
        self.fields['content_type'].queryset = ContentType.objects.filter(pk__in=entity_ct_ids - used_ct_ids)


class CustomFieldsAddForm(CustomFieldsBaseForm):
    class Meta(CustomFieldsBaseForm.Meta):
        exclude = ('content_type',)

    def __init__(self, *args, **kwargs):
        super(CustomFieldsAddForm, self).__init__(*args, **kwargs)
        self.ct = self.initial['ct']

    def save(self):
        self.instance.content_type = self.ct
        super(CustomFieldsAddForm, self).save()


class CustomFieldsEditForm(CremeModelForm):
    class Meta:
        model = CustomField
        fields = ('name',)

    def __init__(self, *args, **kwargs):
        super(CustomFieldsEditForm, self).__init__(*args, **kwargs)

        if self.instance.field_type in (CustomField.ENUM, CustomField.MULTI_ENUM):
            self._enum_values = CustomFieldEnumValue.objects.filter(custom_field=self.instance)

            fields = self.fields
            fields['old_choices'] = ListEditionField(content=[enum.value for enum in self._enum_values],
                                                     label=ugettext(u'Existing choices of the list'),
                                                     help_text=ugettext(u'Uncheck the choices you want to delete.'))
            fields['new_choices'] = CharField(widget=Textarea(), required=False,
                                              label=ugettext(u'New choices of the list'),
                                              help_text=ugettext(u'Give the new possible choices (one per line).'))

    def save(self):
        super(CustomFieldsEditForm, self).save()

        cfield = self.instance

        if cfield.field_type in (CustomField.ENUM, CustomField.MULTI_ENUM):
            cleaned_data = self.cleaned_data

            for cfev, new_value in izip(self._enum_values, cleaned_data['old_choices']):
                if new_value is None:
                    cfev.delete()
                elif cfev.value != new_value:
                    cfev.value = new_value
                    cfev.save()

            create_enum_value = CustomFieldEnumValue.objects.create
            for enum_value in cleaned_data['new_choices'].splitlines():
                create_enum_value(custom_field=cfield, value=enum_value)
