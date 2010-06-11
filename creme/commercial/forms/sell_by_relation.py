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

from django.forms.models import ModelForm
from django.forms import CharField
from django.forms.util import ErrorList
#from django.utils.translation import ugettext_lazy as _

from creme_core.forms.widgets import CalendarWidget

from commercial.models import SellByRelation

#TOD: beuark....

class SellByRelationEditForm(ModelForm):
    class Meta:
        model = SellByRelation
        #TODO: utiliser un exclude Common (is_deleted etc...) + champs specifiques ou 'fields ='
        exclude = ['type', 'symmetric_relation',
                   'subject_content_type', 'subject_id',
                   'object_content_type', 'object_id', 'is_deleted', 'user',
                   'entity_type', 'int_value',
                   'is_actived', 'id']

    date_paiement = CharField(required=False, widget=CalendarWidget())

    #TODO: use *args, **kwargs.....
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False, instance=None, *args, **kwargs):
        super(SellByRelationEditForm, self).__init__(data, files, auto_id, prefix,
                                initial, error_class, label_suffix, empty_permitted, instance, *args, **kwargs)

        self.fields["char_value"].label = 'Commentaire'
        self.fields["date_paiement"].initial = self.instance.date_paiement

    def save(self):
        if self.cleaned_data["date_paiement"] == "":
            self.cleaned_data["date_paiement"] = None 

        super(SellByRelationEditForm, self).save()
