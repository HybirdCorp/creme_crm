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
from django.http import HttpResponse, HttpResponseRedirect
from django.core import serializers
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.models import CremeEntity
from creme_core.views.generic import add_entity, add_to_entity, inner_popup
from creme_core.utils import get_from_POST_or_404

from persons.models import Address, Organisation
from persons.forms.address import AddressWithEntityForm


@login_required
#@add_view_or_die(__ct_address, app_name="all_creme_apps")
@permission_required('persons')
def add(request):
    req_get = request.GET.get
    orga    = get_object_or_404(Organisation, pk=req_get('organisation_id'))

    #TODO: credentials ?

    if req_get('popup') == "true":
        template = "creme_core/generics/blockform/add_popup.html"
    else:
        template = 'creme_core/generics/blockform/add.html'

    callback_url = req_get('callback_url') or "/creme_core/nothing/"

    return add_entity(request,
                      AddressWithEntityForm,
                      callback_url,
                      template,
                      #extra_initial={'organisation_id': req_get('organisation_id')})
                      extra_initial={'entity': orga})


@login_required
@permission_required('persons')
#@edit_view_or_die(__ct_address, app_name="all_creme_apps")
def edit(request, address_id):
    address = get_object_or_404(Address, pk=address_id)
    entity = address.owner

    #die_status = edit_object_or_die(request, address)
    #if die_status:
        #return die_status
    entity.change_or_die(request.user)

    if request.POST:
        edit_form = AddressWithEntityForm(entity, request.POST, instance=address)

        if edit_form.is_valid():
            edit_form.save()
    else:
        edit_form = AddressWithEntityForm(entity, instance=address)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {
                        'form':  edit_form,
                        'title': _(u"Address for <%s>") % entity,
                       },
                       is_valid=edit_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

@login_required
#@edit_view_or_die(__ct_address, app_name="all_creme_apps")
@permission_required('persons')
def delete(request, pk_key='id'):
    address = get_object_or_404(Address, pk=get_from_POST_or_404(request.POST, pk_key))

    #die_status = delete_object_or_die(request, address)
    #if die_status:
        #return die_status
    address.owner.change_or_die(request.user)

    address.delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")
    else:
        return HttpResponseRedirect(address.owner.get_absolute_url())

@login_required #TODO: twice... (see add_to_entity())
#@add_view_or_die(__ct_address, app_name="all_creme_apps")
@permission_required('persons')
def ipopup_add_adress(request, entity_id):
    return add_to_entity(request, entity_id, AddressWithEntityForm, _(u'Adding Address to <%s>'))

#TODO: credentials ??
@login_required
@permission_required('persons')
def get_org_addresses(request):
    POST_get = request.POST.get #TODO: '[]' to raise exception instead ??
    verbose_field = POST_get('verbose_field', '')
    addresses = Address.objects.filter(content_type=POST_get('ct_id'), object_id=POST_get('entity_id'))

    return HttpResponse(serializers.serialize('json', addresses, fields=(verbose_field)), mimetype="text/javascript")
