################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
from django.utils.translation import gettext_lazy as _

from creme import persons
from creme.creme_core.forms import CremeEntityForm, GenericEntityField
from creme.creme_core.forms.validators import validate_linkable_entity
from creme.creme_core.forms.widgets import PrettySelect
from creme.creme_core.gui.custom_form import CustomFormExtraSubCell

from .. import get_opportunity_model

Opportunity = get_opportunity_model()
Organisation = persons.get_organisation_model()
Contact = persons.get_contact_model()


class OpportunitySubCell(CustomFormExtraSubCell):
    def __init__(self, model=Opportunity):
        super().__init__(model=model)


class OppTargetSubCell(OpportunitySubCell):
    sub_type_id = 'opportunities_target'
    verbose_name = _('Target organisation / contact')

    def formfield(self, instance, user, **kwargs):
        field = GenericEntityField(**{
            'label': self.verbose_name,
            'models': [Organisation, Contact],
            'user': user,
            **kwargs
        })

        if instance.pk:
            field.initial = instance.target

        return field

    def post_clean_instance(self, *, instance, value, form):
        instance.target = value


class OppEmitterSubCell(OpportunitySubCell):
    sub_type_id = 'opportunities_emitter'
    verbose_name = _('Concerned organisation')

    def formfield(self, instance, user, **kwargs):
        field = ModelChoiceField(**{
            'label': self.verbose_name,
            'queryset': Organisation.objects.filter_managed_by_creme(),
            'empty_label': None,
            'widget': PrettySelect,
            **kwargs
        })

        # NB: should not be used
        if instance.pk:
            field.initial = instance.emitter.id

        return field

    def post_clean_instance(self, *, instance, value, form):
        if value:
            instance.emitter = validate_linkable_entity(
                entity=value, user=form.user,
            )


class BaseCustomForm(CremeEntityForm):
    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        get_key = self.subcell_key
        self.target_cell_key = get_key(OppTargetSubCell)
        self.emitter_cell_key = get_key(OppEmitterSubCell)

        initial = self.initial
        initial_target = initial.get('target')
        if initial_target:
            initial[self.target_cell_key] = initial_target
