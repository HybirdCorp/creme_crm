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

from django.http import HttpResponse
from django.core import serializers
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required

from creme_core.entities_access.functions_for_permissions import add_view_or_die
from creme_core.views.generic import add_entity

from persons.models import Address
from persons.forms.address import AddressWithOrganisationForm


@login_required
@add_view_or_die(ContentType.objects.get_for_model(Address), app_name="all_creme_apps")
def add(request):
    req_get = request.GET.get

    if req_get('popup') == "true":
        template = "creme_core/generics/blockform/add_popup.html"
    else:
        template = 'creme_core/generics/blockform/add.html'

    callback_url = req_get('callback_url') or "/creme_core/nothing/"

    return add_entity(request,
                      AddressWithOrganisationForm,
                      callback_url,
                      template,
                      extra_initial={'organisation_id': req_get('organisation_id')})

@login_required
def get_org_addresses(request):
    POST_get = request.POST.get
    verbose_field = POST_get('verbose_field', '')
    addresses = Address.objects.filter(content_type__id=POST_get('ct_id'), object_id=POST_get('entity_id'))

    return HttpResponse(serializers.serialize('json', addresses, fields=(verbose_field)), mimetype="text/javascript")
