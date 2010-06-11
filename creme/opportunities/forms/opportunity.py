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

from django.forms import DateTimeField, ModelChoiceField
from django.utils.translation import ugettext_lazy as _

from creme_core.forms import CremeModelForm
from creme_core.forms.fields import CremeEntityField
from creme_core.forms.widgets import CalendarWidget

from persons.models import Organisation

from opportunities.models import Opportunity

from creme import form_post_save

class OpportunityEditForm(CremeModelForm):
    expiration_date = DateTimeField(label=_(u'Écheance'), widget=CalendarWidget())

    class Meta: #Meta(CremeModelForm.Meta) ??
        model = Opportunity
        exclude = CremeModelForm.exclude


class OpportunityCreateForm(OpportunityEditForm):
    target_orga = CremeEntityField(label=_(u"Organisation cible"), model=Organisation)
    emit_orga   = ModelChoiceField(label=_(u"Organisation concernée"), queryset=Organisation.objects.none())

    def __init__(self, *args, **kwargs):
        super(OpportunityCreateForm, self).__init__(*args, **kwargs)
        self.fields['emit_orga'].queryset = Organisation.get_all_managed_by_creme()

    def save(self):
        created = False if self.instance.pk else True
        super(OpportunityCreateForm, self).save()
        self.instance.link_to_target_orga(self.cleaned_data['target_orga'])
        self.instance.link_to_emit_orga(self.cleaned_data['emit_orga'])
        form_post_save.send (sender=Opportunity, instance=self.instance, created=created)
