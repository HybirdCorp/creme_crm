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
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required

from creme_core.entities_access.functions_for_permissions import get_view_or_die, edit_object_or_die, read_object_or_die
from creme_core.views.generic import inner_popup

from sms.models import SMSCampaign, Sending, Message
from sms.forms.message import SendingCreateForm
from sms.blocks import messages_block
#from sms.webservice.samoussa import SamoussaBackEnd
#from sms.webservice.backend import WSException


@login_required
@get_view_or_die('sms')
def add(request, id):
    campaign = get_object_or_404(SMSCampaign, pk=id)

    die_status = edit_object_or_die(request, campaign)
    if die_status:
        return die_status

    if request.POST:
        sending_add_form = SendingCreateForm(campaign, request.POST)

        if sending_add_form.is_valid():
            sending_add_form.save()
    else:
        sending_add_form = SendingCreateForm(campaign=campaign)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':   sending_add_form,
                        'title': _('New sending for <%s>') % campaign,
                       },
                       is_valid=sending_add_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

@login_required
@get_view_or_die('sms')
#def delete(request, id):
def delete(request):
    #sending = get_object_or_404(Sending , pk=id)
    sending = get_object_or_404(Sending , pk=request.POST.get('id'))
    campaign_id = sending.campaign_id

    die_status = edit_object_or_die(request, sending)
    if die_status:
        return die_status

    sending.delete()

    if request.is_ajax():
        return HttpResponse("success", mimetype="text/javascript")

    return HttpResponseRedirect('/sms/campaign/%s' % campaign_id)

@login_required
def sync_messages(request, id):
    sending = get_object_or_404(Sending, pk=id)

    die_status = read_object_or_die(request, sending.campaign)
    if die_status:
        return die_status

    Message.sync(sending)

    return HttpResponse('', status=200)

@login_required
def send_messages(request, id):
    sending = get_object_or_404(Sending, pk=id)

    die_status = read_object_or_die(request, sending.campaign)
    if die_status:
        return die_status

    Message.send(sending)

    return HttpResponse('', status=200)

@login_required
def detailview(request, id):
    sending  = get_object_or_404(Sending, pk=id)

    die_status = read_object_or_die(request, sending.campaign)
    if die_status:
        return die_status

    return render_to_response('sms/popup_sending.html',
                              {'object': sending},
                              context_instance=RequestContext(request))

@login_required
def delete_message(request, id):
    message  = get_object_or_404(Message, pk=id)
    campaign = message.sending.campaign

    die_status = edit_object_or_die(request, campaign)
    if die_status:
        return die_status

    try:
        message.sync_delete()
        message.delete()
    except Exception, err:
        return HttpResponse(err, status=500)

    if request.is_ajax():
        return HttpResponse("success", mimetype="text/javascript")

    #TODO: better with a named url.....
    return HttpResponseRedirect('/sms/campaign/sending/%s' % message.sending_id)

@login_required
def reload_block_messages(request, id):
    return messages_block.detailview_ajax(request, id)
