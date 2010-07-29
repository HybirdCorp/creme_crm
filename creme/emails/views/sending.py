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

from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required

from creme_core.entities_access.functions_for_permissions import get_view_or_die, edit_object_or_die, read_object_or_die
from creme_core.views.generic import inner_popup

from emails.models import EmailCampaign, EmailSending, Email
from emails.models.sending import SENDING_STATE_PLANNED
from emails.forms.sending import SendingCreateForm
from emails.blocks import mails_block


@login_required
@get_view_or_die('emails')
def add(request, campaign_id):
    campaign = get_object_or_404(EmailCampaign, pk=campaign_id)

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
                        'title': 'Nouvel envoi pour <%s>' % campaign,
                       },
                       is_valid=sending_add_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

#TODO: use generic delete ?? (return url not really used)
@login_required
@get_view_or_die('emails')
def delete(request):
    sending  = get_object_or_404(EmailSending, pk=request.POST.get('id'))
    campaign = sending.campaign

    die_status = edit_object_or_die(request, campaign)
    if die_status:
        return die_status

    sending.delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(campaign.get_absolute_url())

@login_required
def detailview(request, sending_id):
    sending  = get_object_or_404(EmailSending, pk=sending_id)
    campaign = sending.campaign

    die_status = read_object_or_die(request, campaign)
    if die_status:
        return die_status

    return render_to_response('emails/popup_sending.html',
                              {'object': sending},
                              context_instance=RequestContext(request))

@login_required
def delete_mail(request):
    mail     = get_object_or_404(Email, pk=request.POST.get('id'))
    campaign = mail.sending.campaign

    die_status = edit_object_or_die(request, campaign)
    if die_status:
        return die_status

    mail.delete()

    if request.is_ajax():
        return HttpResponse("success", mimetype="text/javascript")

    #TODO: better with a named url.....
#    return HttpResponseRedirect('/emails/campaign/sending/%s' % mail.sending_id)
    return HttpResponse()

@login_required
def reload_block_mails(request, sending_id):
    return mails_block.detailview_ajax(request, sending_id)
