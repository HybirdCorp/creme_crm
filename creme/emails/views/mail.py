# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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
from django.utils.translation import ugettext as _, ugettext
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity
from creme_core.views import generic
from creme_core.utils import jsonify, get_from_POST_or_404

from crudity.views.actions import fetch

from emails.models import LightWeightEmail, EntityEmail
from emails.constants import MAIL_STATUS_SENT, MAIL_STATUS_SYNCHRONIZED_SPAM, MAIL_STATUS_SYNCHRONIZED, MAIL_STATUS_SYNCHRONIZED_WAITING
from emails.blocks import SpamSynchronizationMailsBlock, WaitingSynchronizationMailsBlock, mail_waiting_sync_block, mail_spam_sync_block
from emails.forms.mail import EntityEmailForm


@login_required
@permission_required('emails')
def get_lightweight_mail_body(request, mail_id):
    """Used to show an html document in an iframe """
    email = get_object_or_404(LightWeightEmail, pk=mail_id)
    email.sending.campaign.can_view_or_die(request.user)
    return HttpResponse(email.get_body_html())

@login_required
@permission_required('emails')
def view_lightweight_mail(request, mail_id):
    email = get_object_or_404(LightWeightEmail, pk=mail_id)

    #TODO: disable the link in the template if view is not allowed
    email.sending.campaign.can_view_or_die(request.user)

    template = "emails/view_email.html"
    ctx_dict = {'mail': email, 'title': _(u'Details of the mail')}

    if request.is_ajax():
        return generic.inner_popup(request, template, ctx_dict,
                                   is_valid=False, reload=False,
                                   context_instance=RequestContext(request)
                                  )

    return render_to_response(template, ctx_dict, context_instance=RequestContext(request))

#TODO: credentials (don't forget templates)
## SYNCHRO PART ##
@login_required
@permission_required('emails')
def synchronisation(request):
    #TODO: Apply permissions?
    return fetch(request, template="emails/synchronize.html",
                 ajax_template="emails/frags/ajax/synchronize.html",
                 extra_tpl_ctx={
                        'entityemail_ct_id': ContentType.objects.get_for_model(EntityEmail).id,
                    }
                )

def set_emails_status(request, status):
    user = request.user
    errors = []
    emails = EntityEmail.objects.filter(id__in=request.POST.getlist('ids'))
    CremeEntity.populate_credentials(emails, user)

    for email in emails:
        if not email.can_change(user):
            errors.append(ugettext(u'You are not allowed to edit this entity: %s') % email.allowed_unicode(user))
        else:
            email.status = status
            email.save()

    if errors:
        message = ",".join(errors)
        status  = 400
    else:
        status = 200
        message = _(u"Operation successfully completed")

    return HttpResponse(message, mimetype="text/javascript", status=status)

@login_required
@permission_required('emails')
def spam(request):
    return set_emails_status(request, MAIL_STATUS_SYNCHRONIZED_SPAM)

@login_required
@permission_required('emails')
def validated(request):
    return set_emails_status(request, MAIL_STATUS_SYNCHRONIZED)

@login_required
@permission_required('emails')
def waiting(request):
    return set_emails_status(request, MAIL_STATUS_SYNCHRONIZED_WAITING)

@jsonify
@permission_required('emails')
def reload_sync_blocks(request):
    waiting_block = mail_waiting_sync_block#WaitingSynchronizationMailsBlock()
    spam_block    = mail_spam_sync_block#SpamSynchronizationMailsBlock()
    ctx = RequestContext(request)
    return [(waiting_block.id_, waiting_block.detailview_display(ctx)),
            (spam_block.id_, spam_block.detailview_display(ctx))
            ]

## END SYNCHRO PART ##

@login_required
@permission_required('emails')
def detailview(request, mail_id):
    return generic.view_entity(request, mail_id, EntityEmail, '/emails/mail',
                               'emails/view_entity_mail.html',
                               extra_template_dict={'sent_status': MAIL_STATUS_SENT}
                              )

@login_required
@permission_required('emails')
def listview(request):
    return generic.list_view(request, EntityEmail)

@login_required
@permission_required('emails')
@permission_required('emails.add_entityemail')
def create_n_send(request, entity_id):
    return generic.add_to_entity(request, entity_id, EntityEmailForm,
                                 title=_(u'Sending an email to <%s>'),
                                )

@jsonify
@login_required
@permission_required('emails')
def resend_mails(request):
    ids = get_from_POST_or_404(request.POST, 'ids').split(',')

    emails = EntityEmail.objects.get(pk__in=ids)
    for email in emails:
        try:
            email.send()
        except EntityEmail.DoesNotExist: #TODO: wtf ??
            pass

    return {}

@login_required
@permission_required('emails')
def popupview(request, mail_id):
    return generic.view_real_entity(request, mail_id, '/emails/mail', 'emails/view_entity_mail_popup.html')

@login_required
@permission_required('emails')
def get_entity_mail_body(request, entity_id): #TODO: rename entity_id -> mail_id
    """Used to show an html document in an iframe """
    email = get_object_or_404(EntityEmail, pk=entity_id)
    email.can_view_or_die(request.user)
    return HttpResponse(email.get_body())
