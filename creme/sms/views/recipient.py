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

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required

from creme_core.entities_access.functions_for_permissions import get_view_or_die, edit_object_or_die
from creme_core.views.generic import inner_popup

from sms.models import SendList, Recipient
from sms.forms.recipient import SendListAddRecipientsForm, SendListAddCSVForm
from sms.blocks import recipients_block


@login_required
@get_view_or_die('sms')
def add(request, id):
    sendlist = get_object_or_404(SendList, pk=id)

    die_status = edit_object_or_die(request, sendlist)
    if die_status:
        return die_status

    if request.POST:
        recip_add_form = SendListAddRecipientsForm(sendlist, request.POST)

        if recip_add_form.is_valid():
            recip_add_form.save()
    else:
        recip_add_form = SendListAddRecipientsForm(sendlist=sendlist)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':   recip_add_form,
                        'title': 'Nouveaux destinataires pour <%s>' % sendlist,
                       },
                       is_valid=recip_add_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

@login_required
@get_view_or_die('sms')
def add_from_csv(request, id):
    sendlist = get_object_or_404(SendList, pk=id)

    die_status = edit_object_or_die(request, sendlist)
    if die_status:
        return die_status

    if request.method == 'POST':
        recip_add_form = SendListAddCSVForm(sendlist, request.POST, request.FILES)

        if recip_add_form.is_valid():
            recip_add_form.save()
    else:
        recip_add_form = SendListAddCSVForm(sendlist=sendlist)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':   recip_add_form,
                        'title': 'Nouveaux destinataires pour <%s>' % sendlist,
                       },
                       is_valid=recip_add_form.is_valid(),
                       context_instance=RequestContext(request))

@login_required
@get_view_or_die('sms')
def delete(request):
    recipient = get_object_or_404(Recipient , pk=request.POST.get('id'))
    sendlist  = recipient.sendlist

    die_status = edit_object_or_die(request, sendlist)
    if die_status:
        return die_status

    recipient.delete()

    if request.is_ajax():
        return HttpResponse("success", mimetype="text/javascript")

    return HttpResponseRedirect(sendlist.get_absolute_url())

@login_required
def reload_block_recipients(request, id):
    return recipients_block.detailview_ajax(request, id)
