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

from django.forms import ModelForm #, ModelMultipleChoiceField

#from creme_core.models.authent import CremeAppDroit, CremeDroitEntityType
from creme_core.models.authent_role import CremeRole
#from creme_core.forms.widgets import M2MWidget


#_entity_type_credentials = CremeDroitEntityType.objects.all()
#_app_credentials         = CremeAppDroit.objects.all()

#class RoleAddForm(ModelForm):
class RoleForm(ModelForm): #CremeModelForm ????
    #droits_entity_type = ModelMultipleChoiceField(queryset=_entity_type_credentials, required=False,  widget=M2MWidget(attrs={'model': 'CremeDroitEntityType'}))
    #droits_app         = ModelMultipleChoiceField(queryset=_app_credentials, required=False,  widget=M2MWidget(attrs={'model': 'CremeAppDroit'}))

    class Meta:
        model = CremeRole


#class RoleEditForm(ModelForm):
    #droits_entity_type = ModelMultipleChoiceField(queryset=_entity_type_credentials, required=False,  widget=M2MWidget(attrs={'model': 'CremeDroitEntityType'}))
    #droits_app         = ModelMultipleChoiceField(queryset=_app_credentials, required=False,  widget=M2MWidget(attrs={'model': 'CremeAppDroit'}))

    #class Meta:
        #model = CremeRole

