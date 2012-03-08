# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from django.forms import ModelChoiceField
from django.utils.translation import ugettext_lazy as _

from creme_core.forms import CremeEntityForm, CremeDateTimeField, GenericEntityField
from creme_core.forms.validators import validate_linkable_entity
from creme_core.signals import form_post_save

from persons.models import Organisation, Contact
from persons.workflow import transform_target_into_prospect

from opportunities.models import Opportunity


class OpportunityEditForm(CremeEntityForm):
    expected_closing_date = CremeDateTimeField(label=_(u'Expected closing date'), required=False)
    closing_date          = CremeDateTimeField(label=_(u'Actual closing date'), required=False)
    first_action_date     = CremeDateTimeField(label=_(u'Date of the first action'), required=False)

    class Meta(CremeEntityForm.Meta):
        model = Opportunity


class OpportunityCreateForm(OpportunityEditForm):
    target    = GenericEntityField(label=_(u"Target organisation / contact"), models=[Organisation, Contact], required=True)
    emit_orga = ModelChoiceField(label=_(u"Concerned organisation"), queryset=Organisation.get_all_managed_by_creme())

    def clean_target(self):
        return validate_linkable_entity(self.cleaned_data['target'], self.user)

    def clean_emit_orga(self):
        return validate_linkable_entity(self.cleaned_data['emit_orga'], self.user)

    def save(self, *args, **kwargs):
        instance = super(OpportunityCreateForm, self).save(*args, **kwargs)

        cleaned_data = self.cleaned_data
        target = cleaned_data['target']
        emit_orga = cleaned_data['emit_orga']

        instance.link_to_target(target)
        instance.link_to_emit_orga(emit_orga)
        transform_target_into_prospect(emit_orga, target, instance.user)

        form_post_save.send(sender=Opportunity, instance=instance, created=True)

        return instance
