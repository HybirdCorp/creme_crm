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
from django.forms.fields import MultipleChoiceField, ChoiceField
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _

from creme_core.registry import creme_registry
from creme_core.forms import CremeEntityForm
from creme_core.forms.widgets import OrderedMultipleChoiceWidget
from creme_core.forms.fields import AjaxChoiceField, AjaxMultipleChoiceField

from reports2.models import Report2, Field

class CreateForm(CremeEntityForm):
    
    hf     = AjaxChoiceField(required=False)
    filter = AjaxChoiceField(required=False)

    columns       = AjaxMultipleChoiceField(label=_(u'Champs normaux'),       required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    custom_fields = AjaxMultipleChoiceField(label=_(u'Champs personnalisés'), required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    relations     = AjaxMultipleChoiceField(label=_(u'Relations'),            required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    functions     = AjaxMultipleChoiceField(label=_(u'Fonctions'),            required=False, choices=(), widget=OrderedMultipleChoiceWidget)

    class Meta:
        model = Report2
        exclude = CremeEntityForm.Meta.exclude 

    def __init__(self, *args, **kwargs):
        super(CreateForm, self).__init__(*args, **kwargs)
        instance = self.instance
        fields   = self.fields
        ct_get = ContentType.objects.get_for_model
        cts = [ct_get(model) for model in creme_registry.iter_entity_models()]
        cts.sort(key=lambda ct: ct.name)
        fields['ct'].choices = [(ct.id, ct.name) for ct in cts]

    def clean(self):
        cleaned_data = self.cleaned_data
        get_data     = cleaned_data.get
        fields       = self.fields

        hf            = get_data('hf')
        columns       = get_data('columns')
        custom_fields = get_data('custom_fields')
        relations     = get_data('relations')
        functions     = get_data('functions')

        _fields_choices = [unicode(fields[f].label) for f in ['columns','custom_fields','relations', 'functions']]

        if not hf and not (columns or custom_fields or relations or functions):
            raise ValidationError(_(u"Vous devez sélectionner soit une vue existante, soit au moins un champs parmi : %s" % ", ".join(_fields_choices)))

        return cleaned_data

    def save(self):
        #super(CreateForm, self).save()
        cleaned_data = self.cleaned_data


class EditForm(CremeEntityForm):
    class Meta:
        model = Report2
        exclude = CremeEntityForm.Meta.exclude

    def save(self):
        super(EditForm, self).save()
