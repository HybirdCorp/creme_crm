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

from django.forms import ModelMultipleChoiceField
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from ..models import CremeProperty, CremePropertyType
from ..utils import entities_to_str
from .base import CremeForm
from .fields import ReadonlyMessageField


class _AddPropertiesForm(CremeForm):
    types = ModelMultipleChoiceField(
        label=_('Type of property'),
        queryset=CremePropertyType.objects.none(),
    )


class AddPropertiesForm(_AddPropertiesForm):
    def __init__(self, entity, *args, **kwargs):
        # We need this entity in super constructor when post_init_callback is called.
        # TODO: Add unit tests for this !
        self.entity = entity
        super().__init__(*args, **kwargs)

        excluded = CremeProperty.objects.filter(
            creme_entity=entity.id,
        ).values_list('type', flat=True)
        self.fields['types'].queryset = CremePropertyType.objects.compatible(
            type(entity)
        ).filter(enabled=True).exclude(pk__in=excluded)

    def save(self):
        create = CremeProperty.objects.safe_create

        for ptype in self.cleaned_data['types']:
            create(creme_entity=self.entity, type=ptype)


class AddPropertiesBulkForm(_AddPropertiesForm):
    entities_lbl = ReadonlyMessageField(label=_('Related entities'))

    def __init__(self, model, entities, forbidden_entities, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entities = entities
        fields = self.fields
        user = self.user

        fields['types'].queryset = CremePropertyType.objects.compatible(
            model
        ).filter(enabled=True)
        fields['entities_lbl'].initial = (
            entities_to_str(entities, user)
            if entities else
            gettext('NONE !')
        )

        if forbidden_entities:
            fields['bad_entities_lbl'] = ReadonlyMessageField(
                label=gettext('Uneditable entities'),
                initial=entities_to_str(forbidden_entities, user),
            )

    def save(self):
        CremeProperty.objects.safe_multi_save([
            CremeProperty(type=ptype, creme_entity=entity)
            for entity in self.entities
            for ptype in self.cleaned_data['types']
        ])
