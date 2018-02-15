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

from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import CremeEntity
from creme.creme_core.views.generic import (add_entity, add_model_with_popup,
        edit_entity, view_entity, list_view)

from .. import get_opportunity_model
from ..constants import DEFAULT_HFILTER_OPPORTUNITY
from ..forms.opportunity import OpportunityCreateForm, OpportunityEditForm
from ..models import SalesPhase


Opportunity = get_opportunity_model()


def abstract_add_opportunity(request, form=OpportunityCreateForm,
                             submit_label=Opportunity.save_label,
                            ):
    return add_entity(request, form,
                      extra_initial={'sales_phase': SalesPhase.objects.first()},
                      extra_template_dict={'submit_label': submit_label},
                     )


def abstract_add_related_opportunity(request, entity_id, form=OpportunityCreateForm,
                                     title=_(u'New opportunity related to «%s»'),
                                     submit_label=Opportunity.save_label,
                                     inner_popup=False,
                                    ):
    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()
    user = request.user

    user.has_perm_to_link_or_die(entity)
    # We don't need the link credentials with future Opportunity because
    # Target/emitter relationships are internal (they are mandatory
    # and can be seen as ForeignKeys).

    # TODO: this is not an easy way to init the field...
    initial = {'target': form(user).fields['target'].from_python(entity),
               'sales_phase': SalesPhase.objects.first(),
              }

    if inner_popup:
        response = add_model_with_popup(request, form,
                                        title=title % entity.allowed_unicode(user),
                                        initial=initial,
                                        submit_label=submit_label,
                                       )
    else:
        response = add_entity(request, form, extra_initial=initial,
                              extra_template_dict={'submit_label': submit_label},
                             )

    return response


def abstract_edit_opportunity(request, opp_id, form=OpportunityEditForm):
    return edit_entity(request, opp_id, Opportunity, form)


def abstract_view_opportunity(request, opp_id,
                              template='opportunities/view_opportunity.html',
                             ):
    return view_entity(request, opp_id, model=Opportunity, template=template)


@login_required
@permission_required(('opportunities', cperm(Opportunity)))
def add(request):
    return abstract_add_opportunity(request)


@login_required
@permission_required(('opportunities', cperm(Opportunity)))
def add_to(request, ce_id, inner_popup=False):
    return abstract_add_related_opportunity(request, entity_id=ce_id,
                                            inner_popup=inner_popup,
                                           )


@login_required
@permission_required('opportunities')
def edit(request, opp_id):
    return abstract_edit_opportunity(request, opp_id)


@login_required
@permission_required('opportunities')
def detailview(request, opp_id):
    return abstract_view_opportunity(request, opp_id)


@login_required
@permission_required('opportunities')
def listview(request):
    return list_view(request, Opportunity, hf_pk=DEFAULT_HFILTER_OPPORTUNITY)
