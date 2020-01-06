# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.views import generic
from creme.creme_core.views.generic.base import EntityRelatedMixin

from creme import persons

from .. import get_opportunity_model
from ..constants import DEFAULT_HFILTER_OPPORTUNITY
from ..forms import opportunity as opp_forms
from ..models import SalesPhase

Opportunity = get_opportunity_model()


class _BaseOpportunityCreation(generic.EntityCreation):
    model = Opportunity
    form_class = opp_forms.OpportunityCreationForm

    def get_initial(self):
        initial = super().get_initial()
        initial['sales_phase'] = SalesPhase.objects.first()

        return initial


class OpportunityCreation(_BaseOpportunityCreation):
    pass


class RelatedOpportunityCreation(EntityRelatedMixin, _BaseOpportunityCreation):
    entity_id_url_kwarg = 'person_id'
    entity_classes = [
        persons.get_contact_model(),
        persons.get_organisation_model(),
    ]

    def check_related_entity_permissions(self, entity, user):
        # We don't need the link credentials with future Opportunity because
        # Target/emitter relationships are internal (they are mandatory
        # and can be seen as ForeignKeys).
        user.has_perm_to_link_or_die(entity)

    def get_initial(self):
        initial = super().get_initial()
        initial['target'] = self.get_related_entity()

        return initial


# TODO: factorise ?
class RelatedOpportunityCreationPopup(generic.AddingInstanceToEntityPopup):
    model = Opportunity
    form_class = opp_forms.TargetedOpportunityCreationForm
    permissions = ['opportunities', cperm(Opportunity)]
    title = _('New opportunity targeting «{entity}»')
    entity_id_url_kwarg = 'person_id'
    entity_form_kwarg = 'target'
    entity_classes = [
        persons.get_contact_model(),
        persons.get_organisation_model(),
    ]

    def check_related_entity_permissions(self, entity, user):
        # We don't need the link credentials with future Opportunity because
        # Target/emitter relationships are internal (they are mandatory
        # and can be seen as ForeignKeys).
        user.has_perm_to_link_or_die(entity)

    def get_initial(self):
        initial = super().get_initial()
        initial['sales_phase'] = SalesPhase.objects.first()

        return initial


class OpportunityDetail(generic.EntityDetail):
    model = Opportunity
    template_name = 'opportunities/view_opportunity.html'
    pk_url_kwarg = 'opp_id'


class OpportunityEdition(generic.EntityEdition):
    model = Opportunity
    form_class = opp_forms.OpportunityEditionForm
    pk_url_kwarg = 'opp_id'


class OpportunitiesList(generic.EntitiesList):
    model = Opportunity
    default_headerfilter_id = DEFAULT_HFILTER_OPPORTUNITY
