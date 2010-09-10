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
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.template import RequestContext

from creme_core.entities_access.functions_for_permissions import (add_view_or_die, 
                                                    edit_view_or_die, edit_object_or_die, delete_object_or_die)
from creme_core.views.generic import add_entity, inner_popup
from creme_core.models import CremeEntity


from persons.models import Address
from persons.forms.address import AddressWithEntityForm
from persons.models.organisation import Organisation


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
                      AddressWithEntityForm,
                      callback_url,
                      template,
                      extra_initial={'organisation_id': req_get('organisation_id')})


@login_required
@edit_view_or_die(ContentType.objects.get_for_model(Address), app_name="all_creme_apps")
def edit(request, address_id):
    address = get_object_or_404(Address, pk=address_id)
    entity = address.owner

    die_status = edit_object_or_die(request, address)
    if die_status:
        return die_status

    if request.POST:
        edit_form = AddressWithEntityForm( request.POST,  initial={'entity_id': entity.id}, instance=address)

        if edit_form.is_valid():
            edit_form.save()
    else: # return page on GET request
        edit_form = AddressWithEntityForm(initial={'entity_id': entity.id}, instance=address)

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
@edit_view_or_die(ContentType.objects.get_for_model(Address), app_name="all_creme_apps")
def delete(request, pk_key='id'):
    address = get_object_or_404(Address, pk=request.POST.get(pk_key))
    address.delete()
    
    die_status = delete_object_or_die(request, address)
    if die_status:
        return die_status

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")
    else:
        return HttpResponseRedirect(address.owner.get_absolute_url())


@login_required
@add_view_or_die(ContentType.objects.get_for_model(Address), app_name="all_creme_apps")
def ipopup_add_adress(request, entity_id):
    entity = get_object_or_404(CremeEntity, pk=entity_id)
    POST = request.POST
    
    if POST:
        add_address_form = AddressWithEntityForm(POST, initial={'entity_id': entity.id})

        if add_address_form.is_valid():
            add_address_form.save()
    else:
        add_address_form = AddressWithEntityForm(initial={'entity_id': entity.id})

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':   add_address_form,
                        'title': _(u'Adding Address to <%s>') % entity,
                       },
                       is_valid=add_address_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))


@login_required
def get_org_addresses(request):
    POST_get = request.POST.get
    verbose_field = POST_get('verbose_field', '')
    addresses = Address.objects.filter(content_type__id=POST_get('ct_id'), object_id=POST_get('entity_id'))

    return HttpResponse(serializers.serialize('json', addresses, fields=(verbose_field)), mimetype="text/javascript")
