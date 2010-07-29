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

from logging import debug

from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required

from creme_core.models.authent import CremeTypeDroit, CremeTypeEnsembleFiche, CremeDroitEntityType
from creme_core.views.generic import add_entity
from creme_core.entities_access.functions_for_permissions import get_view_or_die
from creme_core.constants import DROIT_MODULE_EST_ADMIN

from creme_config.forms.entity_type_credential import CremeDroitEntityTypeForm


portal_url = '/creme_config/roles/entity_credential/portal/'

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def add(request):
    """
        @Permissions : Admin to creme_config app
    """
    return add_entity(request, CremeDroitEntityTypeForm, portal_url, 'creme_core/generics/form/add.html')

@login_required
@get_view_or_die('creme_config')
def portal(request):
    """
        @Permissions : Acces OR Admin to creme_config app
    """
    return render_to_response('creme_config/roles/entity_credential_portal.html',
                              {},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def delete(request):
    """
        @Permissions : Admin to creme_config app
    """
    entity_cred = get_object_or_404(CremeDroitEntityType, pk=request.POST.get('id'))
    entity_cred.delete()

    return HttpResponse()

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def generate_all_possibilities(request):
    """
        @Permissions : Admin to creme_config app
    """
    all_ct = ContentType.objects.all()
    all_credential_types = CremeTypeDroit.objects.all()
    all_entity_file_types = CremeTypeEnsembleFiche.objects.all()

    for file_type in all_entity_file_types:
        for credential in all_credential_types:
            for ct in all_ct:
                try:
                    CremeDroitEntityType.objects.get_or_create(content_type=ct, type_droit=credential, type_ensemble_fiche=file_type)
                except Exception, e:
                    debug('Exception de creation CremeDroitEntityType : %s', e)

    return HttpResponseRedirect(portal_url)
