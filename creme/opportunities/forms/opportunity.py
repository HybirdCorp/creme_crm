# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from creme.creme_core.forms import CremeEntityForm, GenericEntityField
from creme.creme_core.forms.validators import validate_linkable_entity
from creme.creme_core.signals import form_post_save

from creme.persons import get_contact_model, get_organisation_model

from .. import get_opportunity_model


Opportunity = get_opportunity_model()
Organisation = get_organisation_model()
Contact = get_contact_model()


class OpportunityEditForm(CremeEntityForm):
    target = GenericEntityField(label=_(u'Target organisation / contact'),
                                models=[Organisation, Contact],
                               )

    class Meta(CremeEntityForm.Meta):
        model = Opportunity

    def __init__(self, *args, **kwargs):
        # super(OpportunityEditForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)

        if self.instance.pk:  # Edition
            self.fields['target'].initial = self.instance.target

    def clean_target(self):
        self.instance.target = target = self.cleaned_data['target']

        return target


class OpportunityCreateForm(OpportunityEditForm):
    emitter = ModelChoiceField(label=_(u'Concerned organisation'),
                               queryset=Organisation.get_all_managed_by_creme(),
                               empty_label=None,
                              )

    def clean_emitter(self):
        self.instance.emitter = emitter = validate_linkable_entity(self.cleaned_data['emitter'], self.user)

        return emitter

    def save(self, *args, **kwargs):
        # instance = super(OpportunityCreateForm, self).save(*args, **kwargs)
        instance = super().save(*args, **kwargs)

        form_post_save.send(sender=Opportunity, instance=instance, created=True)

        return instance
