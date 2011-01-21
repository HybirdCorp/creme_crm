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

from django.utils.translation import ugettext as _
#from django.http import HttpResponse
#from django.core import serializers
#from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import add_to_entity, edit_related_to_entity #add_entity

from persons.models import Address #, Organisation
from persons.forms.address import AddressWithEntityForm


#Commented on 3 December 2010
#@login_required
##@add_view_or_die(__ct_address, app_name="all_creme_apps")
#@permission_required('persons')
#def add(request):
    #req_get = request.GET.get
    #orga    = get_object_or_404(Organisation, pk=req_get('organisation_id'))

    ##TODO: credentials ?

    #if req_get('popup') == "true":
        #template = "creme_core/generics/blockform/add_popup.html"
    #else:
        #template = 'creme_core/generics/blockform/add.html'

    #callback_url = req_get('callback_url') or "/creme_core/nothing/"

    #return add_entity(request,
                      #AddressWithEntityForm,
                      #callback_url,
                      #template,
                      ##extra_initial={'organisation_id': req_get('organisation_id')})
                      #extra_initial={'entity': orga})

@login_required
@permission_required('persons')
def edit(request, address_id):
    return edit_related_to_entity(request, address_id, Address, AddressWithEntityForm, _(u"Address for <%s>"))

@login_required
@permission_required('persons')
def ipopup_add_adress(request, entity_id):
    return add_to_entity(request, entity_id, AddressWithEntityForm, _(u'Adding Address to <%s>'))

#Commented on 3 December 2010
##TODO: credentials ??
#@login_required
#@permission_required('persons')
#def get_org_addresses(request):
    #POST_get = request.POST.get #TODO: '[]' to raise exception instead ??
    #verbose_field = POST_get('verbose_field', '')
    #addresses = Address.objects.filter(content_type=POST_get('ct_id'), object_id=POST_get('entity_id'))

    #return HttpResponse(serializers.serialize('json', addresses, fields=(verbose_field)), mimetype="text/javascript")
