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

import warnings

from django.forms import ModelChoiceField, Form
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms import CremeEntityForm, GenericEntityField
from creme.creme_core.forms.validators import validate_linkable_entity
from creme.creme_core.signals import form_post_save

from creme import persons

from .. import get_opportunity_model


Opportunity = get_opportunity_model()
Organisation = persons.get_organisation_model()
Contact = persons.get_contact_model()


# Deprecated forms -------------------------------------------------------------
class OpportunityEditForm(CremeEntityForm):
    target = GenericEntityField(label=_('Target organisation / contact'),
                                models=[Organisation, Contact],
                               )

    class Meta(CremeEntityForm.Meta):
        model = Opportunity

    def __init__(self, *args, **kwargs):
        warnings.warn('opportunities.forms.opportunity.OpportunityEditForm is deprecated ; '
                      'use OpportunityEditionForm instead.',
                      DeprecationWarning
                     )

        super().__init__(*args, **kwargs)

        if self.instance.pk:  # Edition
            self.fields['target'].initial = self.instance.target

    def clean_target(self):
        self.instance.target = target = self.cleaned_data['target']

        return target


class OpportunityCreateForm(OpportunityEditForm):
    emitter = ModelChoiceField(label=_('Concerned organisation'),
                               queryset=Organisation.get_all_managed_by_creme(),
                               empty_label=None,
                              )

    def __init__(self, *args, **kwargs):
        warnings.warn('opportunities.forms.opportunity.OpportunityCreateForm is deprecated ; '
                      'use OpportunityCreationForm instead.',
                      DeprecationWarning
                     )

        super().__init__(*args, **kwargs)

    def clean_emitter(self):
        self.instance.emitter = emitter = validate_linkable_entity(self.cleaned_data['emitter'], self.user)

        return emitter

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)

        form_post_save.send(sender=Opportunity, instance=instance, created=True)

        return instance


# New forms --------------------------------------------------------------------
class OpportunityForm(CremeEntityForm):
    class Meta(CremeEntityForm.Meta):
        model = Opportunity


class TargetMixin(Form):
    target = GenericEntityField(label=_('Target organisation / contact'),
                                models=[Organisation, Contact],
                               )

    def clean_target(self):
        self.instance.target = target = self.cleaned_data['target']

        return target


class EmitterMixin(Form):
    emitter = ModelChoiceField(label=_('Concerned organisation'),
                               queryset=Organisation.get_all_managed_by_creme(),
                               empty_label=None,
                              )

    def clean_emitter(self):
        self.instance.emitter = emitter = \
            validate_linkable_entity(self.cleaned_data['emitter'], self.user)

        return emitter


class OpportunityEditionForm(TargetMixin, OpportunityForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['target'].initial = self.instance.target


class OpportunityCreationForm(TargetMixin, EmitterMixin, OpportunityForm):
    pass


class TargetedOpportunityCreationForm(EmitterMixin, OpportunityForm):
    def __init__(self, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.target = target
