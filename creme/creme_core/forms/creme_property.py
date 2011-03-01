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

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.forms import ModelMultipleChoiceField, CharField, ValidationError
from django.forms.widgets import HiddenInput
from django.utils.translation import ugettext_lazy as _, ugettext

from creme_core.models import CremePropertyType, CremeProperty
from creme_core.forms import CremeForm
from creme_core.forms.widgets import UnorderedMultipleChoiceWidget, Label
from creme_core.forms.fields import MultiCremeEntityField
from creme_core.forms.validators import validate_editable_entities
from creme_core.utils import entities2unicode


class AddPropertiesForm(CremeForm):
    types = ModelMultipleChoiceField(label=_(u'Type of property'),
                                    queryset=CremePropertyType.objects.none(),
                                    widget=UnorderedMultipleChoiceWidget)

    def __init__(self, entity, *args, **kwargs):
        super(AddPropertiesForm, self).__init__(*args, **kwargs)
        self.entity = entity

        #TODO: move queryset to a CremePropertyType method ??
        self.fields['types'].queryset = CremePropertyType.objects.filter(Q(subject_ctypes=entity.entity_type_id) |
                                                                         Q(subject_ctypes__isnull=True))

    def save (self):
        create_property = CremeProperty.objects.create
        entity = self.entity

        for prop_type in self.cleaned_data['types']:
            create_property(type=prop_type, creme_entity=entity)


class AddPropertiesBulkForm(CremeForm):
    types        = ModelMultipleChoiceField(label=_(u'Type of property'),
                                            queryset=CremePropertyType.objects.none(),
                                            widget=UnorderedMultipleChoiceWidget)

    entities     = MultiCremeEntityField(model=None, widget=HiddenInput)
    entities_lbl = CharField(label=_(u"Related entities"), widget=Label(), required=False)

    def __init__(self, model, entities, forbidden_entities, *args, **kwargs):
        super(AddPropertiesBulkForm, self).__init__(*args, **kwargs)
        fields = self.fields

        ct = ContentType.objects.get_for_model(model)

        fields['entities'].model   = model
        fields['entities'].initial = ','.join([str(e.id) for e in entities])

        fields['types'].queryset = CremePropertyType.get_compatible_ones(ct)#TODO:Sort?
        fields['entities_lbl'].initial = entities2unicode(entities, self.user) if entities else ugettext(u'NONE !')

        if forbidden_entities:
            self.fields['bad_entities_lbl'] = CharField(label=ugettext(u"Uneditable entities"),
                                                        widget=Label,
                                                        initial=entities2unicode(forbidden_entities, self.user)
                                                       )

    def clean(self):
        if self._errors:
            return self.cleaned_data

        cleaned_data = self.cleaned_data

        types_ids = cleaned_data['types'].values_list('id')

        if not types_ids:
            raise ValidationError(ugettext(u'No property types'))

        if CremePropertyType.objects.filter(pk__in=types_ids).count() < len(types_ids):
            raise ValidationError(ugettext(u"Some property types doesn't not exist"))

        validate_editable_entities(cleaned_data['entities'], self.user)

        return cleaned_data

    def save(self):
        entities = self.cleaned_data['entities']
        types    = self.cleaned_data['types']
        property_get_or_create = CremeProperty.objects.get_or_create

        for entity in entities:
            for type in types:
                property_get_or_create(type=type, creme_entity=entity)
