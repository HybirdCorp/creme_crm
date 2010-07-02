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
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CustomField, CustomFieldEnumValue
from creme_core.forms import CremeModelForm
from creme_core.forms.fields import ListEditionField
from creme_core.utils import creme_entity_content_types


class CustomFieldsBaseForm(CremeModelForm):
    field_type  = TypedChoiceField(label=_(u'Type du champ'), choices=CustomField.FIELD_TYPES.iteritems(), coerce=int)
    enum_values = CharField(widget=Textarea(), label=_(u'Contenu de la liste'), required=False,
                            help_text=_(u'Mettez les choix possibles (un par ligne) si vous avez choisi le type "Liste de choix".'))

    class Meta(CremeModelForm.Meta):
        model = CustomField

    def clean(self):
        cdata = self.cleaned_data

        if cdata['field_type'] == CustomField.ENUM and not cdata['enum_values'].strip():
            raise ValidationError(_(u'La liste de choix ne doit pas être vide si vous choisissez le type "Liste de choix"'))

        return cdata

    def save(self):
        super(CustomFieldsBaseForm, self).save()

        cleaned_data = self.cleaned_data

        if cleaned_data['field_type'] == CustomField.ENUM:
            create_enum_value = CustomFieldEnumValue.objects.create
            cfield = self.instance

            for enum_value in cleaned_data['enum_values'].splitlines():
                create_enum_value(custom_field=cfield, value=enum_value)


class CustomFieldsCTAddForm(CustomFieldsBaseForm):
    content_type = ModelChoiceField(label=_(u'Resource associée'), queryset=ContentType.objects.none(),
                                    help_text=_(u'Les autres champs personnalisés de ce type de ressource seront choisis en éditant la configuration'))

    def __init__(self, *args, **kwargs):
        super(CustomFieldsCTAddForm, self).__init__(*args, **kwargs)

        entity_ct_ids = set(ct.id for ct in creme_entity_content_types())
        used_ct_ids   = set(CustomField.objects.values_list('content_type_id', flat=True))
        self.fields['content_type'].queryset = ContentType.objects.filter(pk__in=entity_ct_ids - used_ct_ids)

        #TODO: use 'ContentType.objects.get_for_id' in Button config (Block config too ?)


class CustomFieldsAddForm(CustomFieldsBaseForm):
    class Meta(CustomFieldsBaseForm.Meta):
        exclude = CremeModelForm.Meta.exclude + ('content_type',)

    def __init__(self, *args, **kwargs):
        super(CustomFieldsAddForm, self).__init__(*args, **kwargs)
        self.ct = self.initial['ct']

    def save(self):
        self.instance.content_type = self.ct
        super(CustomFieldsAddForm, self).save()


class CustomFieldsEditForm(CremeModelForm):
    class Meta(CremeModelForm.Meta):
        model = CustomField
        #exclude = CremeModelForm.Meta.exclude + ('content_type',)
        fields = ('name',)

    def __init__(self, *args, **kwargs):
        super(CustomFieldsEditForm, self).__init__(*args, **kwargs)

        if self.instance.field_type == CustomField.ENUM:
            self._enum_values = CustomFieldEnumValue.objects.filter(custom_field=self.instance)

            fields = self.fields
            fields['old_choices'] = ListEditionField(content=[enum.value for enum in self._enum_values],
                                                     label=_(u'Choix existants de la liste'),
                                                     help_text=_(u'Décochez les choix que vous voulez supprimer.'))
            fields['new_choices'] = CharField(widget=Textarea(), required=False,
                                              label=_(u'Nouveaux choix de la liste'), 
                                              help_text=_(u'Rentrez les nouveaux choix possibles (un par ligne).'))

    def save(self):
        super(CustomFieldsEditForm, self).save()

        cfield = self.instance

        if cfield.field_type == CustomField.ENUM:
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
