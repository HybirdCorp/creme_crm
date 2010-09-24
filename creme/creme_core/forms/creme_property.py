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

from django.db.models import Q
from django.forms import ModelMultipleChoiceField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremePropertyType, CremeProperty
from creme_core.forms import CremeForm
from creme_core.forms.widgets import UnorderedMultipleChoiceWidget


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
