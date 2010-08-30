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

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.entities_access.functions_for_permissions import get_view_or_die, read_object_or_die
from creme_core.views.generic import view_entity_with_template, list_view, inner_popup

#from emails.blocks import mails_history_block
from emails.models.mail import (EntityEmail, 
                                MAIL_STATUS_SYNCHRONIZED_SPAM,
                                MAIL_STATUS_SYNCHRONIZED,
                                MAIL_STATUS_SYNCHRONIZED_WAITING)
from emails.models import LightWeightEmail

#@login_required
#def reload_block_mails_history(request, entity_id):
    #return mails_history_block.detailview_ajax(request, entity_id)

@login_required
def view_lightweight_mail(request, mail_id):
    email = get_object_or_404(LightWeightEmail, pk=mail_id)
    die_status = read_object_or_die(request, email)

    if die_status:
        return die_status

    template = "emails/view_email.html"
    ctx_dict = {'mail': email, 'title': 'Détails du mail'}

    if request.is_ajax():
        return inner_popup(request, template,
                           ctx_dict,
                           is_valid=False,
                           reload=False,
                           context_instance=RequestContext(request))

    return render_to_response(template, ctx_dict,
                              context_instance=RequestContext(request))


## SYNCHRO PART ##
@login_required
def synchronisation(request):
    #TODO: Apply permissions? 
    new_messages_count = EntityEmail.fetch_mails(request.user.id)

    context_dict = {'entityemail_ct_id': ContentType.objects.get_for_model(EntityEmail).id,
                    'new_messages_count': new_messages_count}

    context_instance =  RequestContext(request)

    if request.is_ajax():
        return HttpResponse(render_to_string("emails/frags/ajax/synchronize.html", context_dict, context_instance=context_instance))

    return render_to_response("emails/synchronize.html",
                              context_dict,
                              context_instance=context_instance)

def _retrieve_emails_ids(request):
    return request.POST.getlist('ids')

def _set_email_status(id, status):
    email = get_object_or_404(EntityEmail, pk=id)
    email.status = status
    email.save()

#TODO: use the update() method of querysets ??
def _set_emails_status(request, status):
    for id in _retrieve_emails_ids(request):
        _set_email_status(id, status)

def set_emails_status(request, status):
    _set_emails_status(request, status)
    return HttpResponse()

@login_required
def delete(request):
    #TODO: There no verifications because email is not a CremeEntity!!!
    for id in _retrieve_emails_ids(request):
        email = get_object_or_404(EntityEmail, pk=id)
        email.delete()

    return HttpResponse()

@login_required
def spam(request):
    #TODO: There no verifications because email is not a CremeEntity!!!
    return set_emails_status(request, MAIL_STATUS_SYNCHRONIZED_SPAM)

@login_required
def validated(request):
    #TODO: There no verifications because email is not a CremeEntity!!!
    return set_emails_status(request, MAIL_STATUS_SYNCHRONIZED)

@login_required
def waiting(request):
    #TODO: There no verifications because email is not a CremeEntity!!!
    return set_emails_status(request, MAIL_STATUS_SYNCHRONIZED_WAITING)

## END SYNCHRO PART ##

@login_required
@get_view_or_die('emails')
def detailview(request, mail_id):
    return view_entity_with_template(request, mail_id, EntityEmail,
                                     '/emails/mail', 'emails/view_entity_mail.html')

@login_required
@get_view_or_die('emails')
def listview(request):
    return list_view(request, EntityEmail)
