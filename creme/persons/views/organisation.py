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

from django.db.models.query_utils import Q
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.constants import PROP_IS_MANAGED_BY_CREME
from creme_core.views.generic import add_entity, edit_entity, view_entity, list_view

from persons.models import Organisation
from persons.forms.organisation import OrganisationForm
from persons.constants import REL_SUB_SUSPECT, REL_SUB_PROSPECT, REL_SUB_CUSTOMER_OF

@login_required
@permission_required('persons')
@permission_required('persons.add_organisation')
def add(request):
    return add_entity(request, OrganisationForm, template="persons/add_organisation_form.html")

@login_required
@permission_required('persons')
def edit(request, organisation_id):
    return edit_entity(request, organisation_id, Organisation, OrganisationForm, template='persons/edit_organisation_form.html')

@login_required
@permission_required('persons')
def detailview(request, organisation_id):
    return view_entity(request, organisation_id, Organisation, '/persons/organisation', 'persons/view_organisation.html')

@login_required
@permission_required('persons')
def listview(request):
    return list_view(request, Organisation, extra_dict={'add_url': '/persons/organisation/add'})

#TODO: set the HF in the url ????
@login_required
@permission_required('persons')
def list_my_leads_my_customers(request):
    #use a constant for 'persons-hf_leadcustomer' ??
    return list_view(request, Organisation, hf_pk='persons-hf_leadcustomer',
                     extra_dict={'list_title': _(u'List of my suspects / prospects / customers')},
                     extra_q=Q(relations__type__in=[REL_SUB_CUSTOMER_OF, REL_SUB_PROSPECT, REL_SUB_SUSPECT],
                               relations__object_entity__properties__type=PROP_IS_MANAGED_BY_CREME))
