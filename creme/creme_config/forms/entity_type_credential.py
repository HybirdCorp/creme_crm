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

from django.forms import ModelForm, ModelChoiceField
from django.contrib.contenttypes.models import ContentType

from creme_core.models.authent import CremeDroitEntityType, CremeTypeDroit, CremeTypeEnsembleFiche


class CremeDroitEntityTypeForm(ModelForm):
    content_type        = ModelChoiceField(queryset=ContentType.objects.all())
    type_droit          = ModelChoiceField(queryset=CremeTypeDroit.objects.all())
    type_ensemble_fiche = ModelChoiceField(queryset=CremeTypeEnsembleFiche.objects.all())

    def save(self):
        cleaned_data = self.cleaned_data
        c = CremeDroitEntityType()
        c.content_type = cleaned_data['content_type']
        c.type_droit = cleaned_data['type_droit']
        c.type_ensemble_fiche = cleaned_data['type_ensemble_fiche']
        c.id_fiche_role_ou_equipe = cleaned_data['id_fiche_role_ou_equipe']
        c.save()

    class Meta:
        model = CremeDroitEntityType
#        exclude = ('id_fiche_role_ou_equipe')