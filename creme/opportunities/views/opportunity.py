# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme.creme_core.models import CremeEntity
from creme.creme_core.utils.queries import get_first_or_None
from creme.creme_core.views.generic import (add_entity, add_model_with_popup,
                                          edit_entity, view_entity, list_view)

from ..forms.opportunity import OpportunityCreateForm, OpportunityEditForm
from ..models import Opportunity, SalesPhase


@login_required
@permission_required('opportunities')
@permission_required('opportunities.add_opportunity')
def add(request):
    return add_entity(request, OpportunityCreateForm,
                      extra_initial={'sales_phase': get_first_or_None(SalesPhase)},
                      extra_template_dict={'submit_label': _('Save the opportunity')},
                     )

@login_required
@permission_required('opportunities')
@permission_required('opportunities.add_opportunity')
def add_to(request, ce_id, inner_popup=False):
    centity = get_object_or_404(CremeEntity, pk=ce_id).get_real_entity()
    user = request.user

    user.has_perm_to_link_or_die(centity)
    # We don't need the link credentials with future Opportunity because
    # Target/emitter relationships are internal (they are mandatory
    # and can be seen as ForeignKeys).

    initial = {'target': '{"ctype":"%s","entity":"%s"}' % (centity.entity_type_id, centity.id), #TODO: This is not an easy way to init the field...
               'sales_phase': get_first_or_None(SalesPhase),
              }

    if inner_popup:
        response = add_model_with_popup(request, OpportunityCreateForm,
                                        title=_(u'New opportunity related to <%s>') %
                                                    centity.allowed_unicode(user),
                                        initial=initial,
                                       )
    else:
        response = add_entity(request, OpportunityCreateForm, extra_initial=initial,
                              extra_template_dict={'submit_label': _('Save the opportunity')},
                             )

    return response

@login_required
@permission_required('opportunities')
def edit(request, opp_id):
    return edit_entity(request, opp_id, Opportunity, OpportunityEditForm)

@login_required
@permission_required('opportunities')
def detailview(request, opp_id):
    return view_entity(request, opp_id, Opportunity, '/opportunities/opportunity',
                       'opportunities/view_opportunity.html',
                      )

@login_required
@permission_required('opportunities')
def listview(request):
    return list_view(request, Opportunity, extra_dict={'add_url': '/opportunities/opportunity/add'})
