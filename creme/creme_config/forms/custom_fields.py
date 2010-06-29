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

from django.forms import ChoiceField, ModelChoiceField
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.forms import CremeModelForm
from creme_core.models import CustomField
from creme_core.utils import creme_entity_content_types


class CustomFieldsBaseForm(CremeModelForm):
    field_type = ChoiceField(label=_(u'Type du champ'), choices=CustomField.FIELD_TYPES.iteritems())

    class Meta(CremeModelForm.Meta):
        model = CustomField


class CustomFieldsCTAddForm(CustomFieldsBaseForm):
    content_type = ModelChoiceField(label=_(u'Resource associée'), queryset=ContentType.objects.none(),
                                    help_text=_(u'Les autres champs personnalisés de ce type de ressource seront choisis en éditant la configuration'))

    def __init__(self, *args, **kwargs):
        super(CustomFieldsCTAddForm, self).__init__(*args, **kwargs)

        entity_ct_ids = set(ct.id for ct in creme_entity_content_types())
        used_ct_ids   = set(CustomField.objects.values_list('content_type_id', flat=True)) #.distinct() ??
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
    class Meta(CustomFieldsBaseForm.Meta):
        #exclude = CremeModelForm.Meta.exclude + ('content_type',)
        fields = ('name',)
