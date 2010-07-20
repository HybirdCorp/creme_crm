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

from django.forms.fields import MultipleChoiceField
from django.forms.widgets import Select
from django.forms.fields import ChoiceField
from django.utils.translation import ugettext_lazy as _

from creme_core.forms import CremeEntityForm
from creme_core.forms.widgets import OrderedMultipleChoiceWidget

from reports2.models import Report2, Field


class CreateForm(CremeEntityForm):
    
    hf     = ChoiceField(required=False)
    filter = ChoiceField(required=False)

    columns       = MultipleChoiceField(label=_(u'Champs normaux'),       required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    custom_fields = MultipleChoiceField(label=_(u'Champs personnalisés'), required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    relations     = MultipleChoiceField(label=_(u'Relations'),            required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    functions     = MultipleChoiceField(label=_(u'Fonctions'),            required=False, choices=(), widget=OrderedMultipleChoiceWidget)

    class Meta:
        model = Report2
        exclude = CremeEntityForm.Meta.exclude + ('columns',)

    def __init__(self, *args, **kwargs):
        super(CreateForm, self).__init__(*args, **kwargs)
        instance = self.instance
        fields   = self.fields

    def save(self):
        super(CreateForm, self).save()

    #TODO : Clean between hf & columns one has to be set...

class EditForm(CremeEntityForm):
    class Meta:
        model = Report2
        exclude = CremeEntityForm.Meta.exclude

    def save(self):
        super(EditForm, self).save()
