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

from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import CremeEntity
from creme.creme_core.views import generic
from creme.creme_core.views.generic.base import EntityRelatedMixin

from creme import persons

from .. import get_opportunity_model
from ..constants import DEFAULT_HFILTER_OPPORTUNITY
from ..forms import opportunity as opp_forms
from ..models import SalesPhase


Opportunity = get_opportunity_model()

# Function views --------------------------------------------------------------


def abstract_add_opportunity(request, form=opp_forms.OpportunityCreateForm,
                             submit_label=Opportunity.save_label,
                            ):
    warnings.warn('opportunities.views.opportunity.abstract_add_opportunity() is deprecated ; '
                  'use the class-based view OpportunityCreation instead.',
                  DeprecationWarning
                 )
    return generic.add_entity(request, form,
                              extra_initial={'sales_phase': SalesPhase.objects.first()},
                              extra_template_dict={'submit_label': submit_label},
                             )


def abstract_add_related_opportunity(request, entity_id, form=opp_forms.OpportunityCreateForm,
                                     title=_('New opportunity related to «%s»'),
                                     submit_label=Opportunity.save_label,
                                     inner_popup=False,
                                    ):
    warnings.warn('opportunities.views.opportunity.abstract_add_related_opportunity() is deprecated ; '
                  'use the class-based views RelatedOpportunityCreation & '
                  'RelatedOpportunityCreationPopup instead.',
                  DeprecationWarning
                 )

    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()
    user = request.user

    user.has_perm_to_link_or_die(entity)
    # We don't need the link credentials with future Opportunity because
    # Target/emitter relationships are internal (they are mandatory
    # and can be seen as ForeignKeys).

    initial = {
        # 'target': form(user).fields['target'].from_python(entity),
        'target':      entity,
        'sales_phase': SalesPhase.objects.first(),
    }

    if inner_popup:
        response = generic.add_model_with_popup(request, form,
                                                title=title % entity.allowed_str(user),
                                                initial=initial,
                                                submit_label=submit_label,
                                               )
    else:
        response = generic.add_entity(request, form, extra_initial=initial,
                                      extra_template_dict={'submit_label': submit_label},
                                     )

    return response


def abstract_edit_opportunity(request, opp_id, form=opp_forms.OpportunityEditForm):
    warnings.warn('opportunities.views.opportunity.abstract_edit_opportunity() is deprecated ; '
                  'use the class-based view OpportunityEdition instead.',
                  DeprecationWarning
                 )
    return generic.edit_entity(request, opp_id, Opportunity, form)


def abstract_view_opportunity(request, opp_id,
                              template='opportunities/view_opportunity.html',
                             ):
    warnings.warn('opportunities.views.opportunity.abstract_view_opportunity() is deprecated ; '
                  'use the class-based view OpportunityDetail instead.',
                  DeprecationWarning
                 )
    return generic.view_entity(request, opp_id, model=Opportunity, template=template)


@login_required
@permission_required(('opportunities', cperm(Opportunity)))
def add(request):
    warnings.warn('opportunities.views.opportunity.add() is deprecated .', DeprecationWarning)
    return abstract_add_opportunity(request)


@login_required
@permission_required(('opportunities', cperm(Opportunity)))
def add_to(request, ce_id, inner_popup=False):
    warnings.warn('opportunities.views.opportunity.add_to() is deprecated .', DeprecationWarning)
    return abstract_add_related_opportunity(request, entity_id=ce_id,
                                            inner_popup=inner_popup,
                                           )


@login_required
@permission_required('opportunities')
def edit(request, opp_id):
    warnings.warn('opportunities.views.opportunity.edit() is deprecated .', DeprecationWarning)
    return abstract_edit_opportunity(request, opp_id)


@login_required
@permission_required('opportunities')
def detailview(request, opp_id):
    warnings.warn('opportunities.views.opportunity.detailview() is deprecated .', DeprecationWarning)
    return abstract_view_opportunity(request, opp_id)


@login_required
@permission_required('opportunities')
def listview(request):
    return generic.list_view(request, Opportunity, hf_pk=DEFAULT_HFILTER_OPPORTUNITY)


# Class-based views  ----------------------------------------------------------

class _BaseOpportunityCreation(generic.EntityCreation):
    model = Opportunity
    form_class = opp_forms.OpportunityCreateForm

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
class RelatedOpportunityCreationPopup(generic.AddingToEntity):
    model = Opportunity
    form_class = opp_forms.OpportunityCreateForm
    permissions = ['opportunities', cperm(Opportunity)]
    title_format = _('New opportunity related to «{}»')
    entity_id_url_kwarg = 'person_id'
    entity_form_kwarg = None
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
        initial['target'] = self.get_related_entity()

        return initial


class OpportunityDetail(generic.detailview.EntityDetail):
    model = Opportunity
    template_name = 'opportunities/view_opportunity.html'
    pk_url_kwarg = 'opp_id'


class OpportunityEdition(generic.EntityEdition):
    model = Opportunity
    form_class = opp_forms.OpportunityEditForm
    pk_url_kwarg = 'opp_id'
