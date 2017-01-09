# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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
from django.db.transaction import atomic
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
# from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic, decorators

from .. import get_organisation_model, constants
from ..forms import organisation as orga_forms


Organisation = get_organisation_model()


def abstract_add_organisation(request, form=orga_forms.OrganisationForm,
                              template='persons/add_organisation_form.html',
                              # submit_label=_('Save the organisation'),
                              submit_label=Organisation.save_label,
                             ):
    return generic.add_entity(request, form, template=template,
                              extra_template_dict={'submit_label': submit_label},
                             )


def abstract_edit_organisation(request, organisation_id, form=orga_forms.OrganisationForm,
                               template='persons/edit_organisation_form.html',
                              ):
    return generic.edit_entity(request, organisation_id, model=Organisation,
                               edit_form=form, template=template,
                              )


def abstract_view_organisation(request,organisation_id,
                               template='persons/view_organisation.html',
                              ):
    return generic.view_entity(request, organisation_id, model=Organisation,
                               template=template,
                              )


@login_required
@permission_required(('persons', cperm(Organisation)))
def add(request):
    return abstract_add_organisation(request)


@login_required
@permission_required('persons')
def edit(request, organisation_id):
    return abstract_edit_organisation(request, organisation_id)


@login_required
@permission_required('persons')
def detailview(request, organisation_id):
    return abstract_view_organisation(request, organisation_id)


@login_required
@permission_required('persons')
def listview(request):
    return generic.list_view(request, Organisation, hf_pk=constants.DEFAULT_HFILTER_ORGA)


# TODO: set the HF in the url ????
@login_required
@permission_required('persons')
def list_my_leads_my_customers(request):
    # TODO: use a constant for 'persons-hf_leadcustomer' ??
    return generic.list_view(request, Organisation, hf_pk='persons-hf_leadcustomer',
                             extra_dict={'list_title': ugettext(u'List of my suspects / prospects / customers')},
                             extra_q=Q(relations__type__in=(constants.REL_SUB_CUSTOMER_SUPPLIER,
                                                            constants.REL_SUB_PROSPECT,
                                                            constants.REL_SUB_SUSPECT,
                                                           ),
                                       # relations__object_entity__properties__type=PROP_IS_MANAGED_BY_CREME,
                                       relations__object_entity__in=[o.id for o in Organisation.get_all_managed_by_creme()],
                                      ),
                            )


@login_required
@permission_required('creme_core.can_admin')
def set_managed(request):
    if request.method == 'POST':
        form = orga_forms.ManagedOrganisationsForm(user=request.user, data=request.POST)

        if form.is_valid():
            form.save()
    else:
        form = orga_forms.ManagedOrganisationsForm(user=request.user)

    return generic.inner_popup(request,
                               'creme_core/generics/blockform/edit_popup.html',
                               {'form':         form,
                                'title':        _(u'Add some managed organisations'),
                                'submit_label': _(u'Save the modifications'),
                               },
                               is_valid=form.is_valid(),
                               reload=False,
                               delegate_reload=True,
                              )


@decorators.POST_only
@login_required
@permission_required('creme_core.can_admin')
def unset_managed(request):
    orga = get_object_or_404(Organisation, id=get_from_POST_or_404(request.POST, 'id'), is_managed=True)

    request.user.has_perm_to_change_or_die(orga)

    with atomic():
        ids = Organisation.objects.select_for_update().filter(is_managed=True).values_list('id', flat=True)

        if orga.id in ids:  # In case a concurrent call to this view has been done
            if len(ids) >= 2:
                orga.is_managed = False
                orga.save()
            else:
                raise ConflictError(ugettext(u'You must have at least one managed organisation.'))

    return HttpResponse()
