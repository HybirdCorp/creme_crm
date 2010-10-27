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
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from creme_core.views.generic import (view_entity_with_template, list_view,
                                      inner_popup, add_entity, add_to_entity,
                                      view_real_entity_with_template)
                                      
from creme_core.utils import jsonify, get_from_POST_or_404

from crudity.views.email import fetch_emails

#from emails.blocks import mails_history_block
from emails.models.mail import (EntityEmail,
                                MAIL_STATUS_SENT,
                                MAIL_STATUS_SYNCHRONIZED_SPAM,
                                MAIL_STATUS_SYNCHRONIZED,
                                MAIL_STATUS_SYNCHRONIZED_WAITING)

from emails.blocks import SpamSynchronizationMailsBlock, WaitingSynchronizationMailsBlock
from emails.models import LightWeightEmail

from emails.forms.mail import EntityEmailForm

#@login_required
#def reload_block_mails_history(request, entity_id):
    #return mails_history_block.detailview_ajax(request, entity_id)

@login_required
@permission_required('emails')
def view_lightweight_mail(request, mail_id):
    email = get_object_or_404(LightWeightEmail, pk=mail_id)

    #die_status = read_object_or_die(request, email)
    #if die_status:
        #return die_status
    email.sending.campaign.can_view_or_die(request.user)

    template = "emails/view_email.html"
    ctx_dict = {'mail': email, 'title': 'Détails du mail'}#TODO: i18n

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
    return fetch_emails(request, template="emails/synchronize.html",
                        ajax_template="emails/frags/ajax/synchronize.html",
                        extra_tpl_ctx={
                                'entityemail_ct_id': ContentType.objects.get_for_model(EntityEmail).id,
                            }
                       )

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
@permission_required('emails')
def delete(request):
    #TODO: There no verifications because email is not a CremeEntity!!!
    for id in _retrieve_emails_ids(request):
        email = get_object_or_404(EntityEmail, pk=id)
        email.delete()

    return HttpResponse()

@login_required
@permission_required('emails')
def spam(request):
    #TODO: There no verifications because email is not a CremeEntity!!!
    return set_emails_status(request, MAIL_STATUS_SYNCHRONIZED_SPAM)

@login_required
@permission_required('emails')
def validated(request):
    #TODO: There no verifications because email is not a CremeEntity!!!
    return set_emails_status(request, MAIL_STATUS_SYNCHRONIZED)

@login_required
@permission_required('emails')
def waiting(request):
    #TODO: There no verifications because email is not a CremeEntity!!!
    return set_emails_status(request, MAIL_STATUS_SYNCHRONIZED_WAITING)

@jsonify
def reload_sync_blocks(request):
    waiting_block = WaitingSynchronizationMailsBlock()
    spam_block    = SpamSynchronizationMailsBlock()
    ctx = RequestContext(request)
    return [(waiting_block.id_,waiting_block.detailview_display(ctx)),
            (spam_block.id_,spam_block.detailview_display(ctx))
            ]

## END SYNCHRO PART ##

@login_required
@permission_required('emails')
def detailview(request, mail_id):
    return view_entity_with_template(request, mail_id, EntityEmail,
                                     '/emails/mail', 'emails/view_entity_mail.html',
                                     extra_template_dict={'sent_status': MAIL_STATUS_SENT})

@login_required
@permission_required('emails')
def listview(request):
    return list_view(request, EntityEmail)


@login_required
@permission_required('emails')
def create_n_send(request, entity_id):
    return add_to_entity(
                         request,
                         entity_id,
                         EntityEmailForm,
                         title=_(u'Sending an email to <%s>'),
                         initial={'current_user': request.user}
                        )

@jsonify
@login_required
@permission_required('emails')
def resend_mails(request):
    _ids = get_from_POST_or_404(request.POST, 'ids')
    ids = _ids.split(',')

    for id in ids:
        try:
            EntityEmail.objects.get(pk=id).send()
        except EntityEmail.DoesNotExist:
            pass

    return {}
    
@login_required
@permission_required('activities')
def popupview(request, mail_id):
    return view_real_entity_with_template(request, mail_id,
                                          '/emails/mail',
                                          'emails/view_entity_mail_popup.html')

