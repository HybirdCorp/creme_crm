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

from django.forms import ModelForm, ModelChoiceField, CharField
from django.forms.widgets import Select

from creme_core.models.authent import CremeAppDroit, CremeAppTypeDroit
from creme_core.registry import creme_registry


class CremeAppDroitForm(ModelForm):
    type_droit = ModelChoiceField(queryset=CremeAppTypeDroit.objects.all())
    name_app   = CharField(widget=Select())

    def __init__(self, *args, **kwargs):
        super(CremeAppDroitForm, self).__init__(*args, **kwargs)
        self.fields['name_app'].widget.choices = ((app, app) for app in creme_registry._apps) #beurk

    def save(self):
        cleaned_data = self.cleaned_data
        creme_app = CremeAppDroit()
        creme_app.type_droit = cleaned_data['type_droit']
        creme_app.name_app = cleaned_data['name_app']
        creme_app.save()

    class Meta:
        model = CremeAppDroit
