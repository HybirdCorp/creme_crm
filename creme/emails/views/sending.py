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
from django.utils.translation import ugettext as _
from django.template import RequestContext
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import add_to_entity
from creme_core.utils import get_from_POST_or_404

from emails.models import EmailCampaign, EmailSending, LightWeightEmail
from emails.forms.sending import SendingCreateForm
from emails.blocks import mails_block


def add(request, campaign_id):
    return add_to_entity(request, campaign_id, SendingCreateForm,
                         _('New sending for <%s>'), entity_class=EmailCampaign)

#TODO: use generic delete ?? (return url not really used)
@login_required
@permission_required('emails')
def delete(request):
    sending  = get_object_or_404(EmailSending, pk=get_from_POST_or_404(request.POST, 'id'))
    campaign = sending.campaign

    campaign.change_or_die(request.user)

    sending.delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(campaign.get_absolute_url())

@login_required
def detailview(request, sending_id):
    sending  = get_object_or_404(EmailSending, pk=sending_id)
    campaign = sending.campaign

    campaign.view_or_die(request.user)

    return render_to_response('emails/popup_sending.html',
                              {'object': sending},
                              context_instance=RequestContext(request))

@login_required
def delete_mail(request):
    mail     = get_object_or_404(LightWeightEmail, pk=get_from_POST_or_404(request.POST, 'id'))
    campaign = mail.sending.campaign

    campaign.change_or_die(request.user)

    mail.delete()

    if request.is_ajax():
        return HttpResponse("success", mimetype="text/javascript")

    return HttpResponse()

@login_required
def reload_block_mails(request, sending_id):
    return mails_block.detailview_ajax(request, sending_id)
