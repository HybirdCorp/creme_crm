# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

import warnings

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template import Template, Context
#from django.template.context import RequestContext
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import CremeEntity
from creme.creme_core.utils import jsonify, get_from_POST_or_404
from creme.creme_core.utils.html import sanitize_html
from creme.creme_core.views import generic, blocks as blocks_views

from creme.crudity.views.actions import fetch

from .. import get_entityemail_model
from ..blocks import mail_waiting_sync_block, mail_spam_sync_block
from ..constants import (MAIL_STATUS_SENT, MAIL_STATUS_SYNCHRONIZED_SPAM,
        MAIL_STATUS_SYNCHRONIZED, MAIL_STATUS_SYNCHRONIZED_WAITING,
        DEFAULT_HFILTER_EMAIL)
from ..forms.mail import EntityEmailForm, TemplateSelectionForm, EntityEmailFromTemplateForm
from ..forms.template import TEMPLATES_VARS
from ..models import LightWeightEmail  # EntityEmail


EntityEmail = get_entityemail_model()


@login_required
@permission_required('emails')
def get_lightweight_mail_body(request, mail_id):
    """Used to show an html document in an iframe """
    # email = get_object_or_404(LightWeightEmail, pk=mail_id)
    # request.user.has_perm_to_view_or_die(email.sending.campaign)
    # return HttpResponse(email.get_body_html())
    email = get_object_or_404(LightWeightEmail, pk=mail_id)
    request.user.has_perm_to_view_or_die(email.sending.campaign)

    return HttpResponse(sanitize_html(email.rendered_body_html,
                                      # TODO: ? allow_external_img=request.GET.get('external_img', False),
                                      allow_external_img=True,
                                     )
                       )


@login_required
@permission_required('emails')
def view_lightweight_mail(request, mail_id):
    email = get_object_or_404(LightWeightEmail, pk=mail_id)

    # TODO: disable the link in the template if view is not allowed
    request.user.has_perm_to_view_or_die(email.sending.campaign)

    template = "emails/view_email.html"
    ctx_dict = {'mail': email, 'title': _(u'Details of the mail')}

    if request.is_ajax():
        return generic.inner_popup(request, template, ctx_dict,
                                   is_valid=False, reload=False,
                                  )

    return render(request, template, ctx_dict)


# TODO: credentials (don't forget templates)
## SYNCHRO PART ##
@login_required
@permission_required('emails')
def synchronisation(request):
    # TODO: Apply permissions?
    return fetch(request, template="emails/synchronize.html",
                 ajax_template="emails/frags/ajax/synchronize.html",
                 extra_tpl_ctx={
                        'entityemail_ct_id': ContentType.objects.get_for_model(EntityEmail).id,
                    }
                )


def set_emails_status(request, status):
    user = request.user
    errors = []
    has_perm = user.has_perm_to_change

    for email in EntityEmail.objects.filter(id__in=request.POST.getlist('ids')):
        if not has_perm(email):
            errors.append(ugettext(u'You are not allowed to edit this entity: %s') %
                            email.allowed_unicode(user)
                         )
        else:
            email.status = status
            email.save()

    if errors:
        message = ",".join(errors)
        status  = 400
    else:
        status = 200
        message = ugettext(u"Operation successfully completed")

    return HttpResponse(message, content_type="text/javascript", status=status)


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
#    ctx = RequestContext(request)
    ctx = blocks_views.build_context(request)

    return [(mail_waiting_sync_block.id_, mail_waiting_sync_block.detailview_display(ctx)),
            (mail_spam_sync_block.id_,    mail_spam_sync_block.detailview_display(ctx))
           ]

## END SYNCHRO PART ##


def abstract_view_email(request, mail_id, template='emails/view_entity_mail.html'):
    return generic.view_entity(request, mail_id, EntityEmail,
                               # path='/emails/mail',
                               template=template,
                               extra_template_dict={'sent_status': MAIL_STATUS_SENT},
                              )


def abstract_popupview(request, mail_id,
                       template='emails/view_entity_mail_popup.html'
                      ):
#    return generic.view_real_entity(request, mail_id, path='/emails/mail',
#                                    template=template,
#                                   )
    return generic.view_entity(request, mail_id, EntityEmail,
                               template=template,
                               # path='/emails/mail',
                              )


def abstract_create_n_send(request, entity_id, form=EntityEmailForm,
                           title=_(u'Sending an email to «%s»'),
                           submit_label=_('Send the email'),
                          ):
    return generic.add_to_entity(request, entity_id, form, title=title,
                                 link_perm=True, submit_label=submit_label,
                                )


# TODO: use a wizard. It seems hackish to work with inner popup & django.contrib.formtools.wizard.FormWizard
def abstract_create_from_template_n_send(request, entity_id,
                                         selection_form=TemplateSelectionForm,
                                         email_form=EntityEmailFromTemplateForm,
                                         template='creme_core/generics/blockform/add_popup2.html',
                                        ):
    entity = get_object_or_404(CremeEntity, pk=entity_id)
    user = request.user

    user.has_perm_to_link_or_die(entity)

    entity = entity.get_real_entity()
    submit_label = _('Next step')

    if request.method == 'POST':
        POST = request.POST
        step = int(POST.get('step', 1))

        if step == 1:
            step = 2
            form = selection_form(user=user, data=POST)

            if form.is_valid():
                email_template = form.cleaned_data['template']
                ctx = {varname: getattr(entity, varname, '') for varname in TEMPLATES_VARS}
                form = email_form(user=user, entity=entity,
                                  initial={'subject':     email_template.subject,
                                           'body':        Template(email_template.body).render(Context(ctx)),
                                           'body_html':   Template(email_template.body_html).render(Context(ctx)),
                                           'signature':   email_template.signature_id,
                                           'attachments': list(email_template.attachments.values_list('id', flat=True)),
                                          }
                                 )
                submit_label = _('Send the email')
        else:
            assert step == 2
            form = email_form(user=user, entity=entity, data=POST)

            if form.is_valid():
                form.save()
    else:
        step = 1
        form = selection_form(user=user)

    return generic.inner_popup(request, template,
                               {'form':   form,
                                'title':  ugettext(u'Sending an email to «%(entity)s» (step %(step)s/2)') % {
                                                'entity': entity,
                                                'step':   step,
                                            },
                                'submit_label': submit_label,
                               },
                               is_valid=form.is_valid(),
                               reload=False,
                               delegate_reload=True,
                              )


@login_required
@permission_required('emails')
def detailview(request, mail_id):
    return abstract_view_email(request, mail_id)


@login_required
@permission_required('emails')
def popupview(request, mail_id):
    return abstract_popupview(request, mail_id)


@login_required
@permission_required('emails')
def listview(request):
    return generic.list_view(request, EntityEmail, hf_pk=DEFAULT_HFILTER_EMAIL)


@login_required
# @permission_required(('emails', 'emails.add_entityemail'))
@permission_required(('emails', cperm(EntityEmail)))
def create_n_send(request, entity_id):
    return abstract_create_n_send(request, entity_id)


@login_required
# @permission_required(('emails', 'emails.add_entityemail'))
@permission_required(('emails', cperm(EntityEmail)))
def create_from_template_n_send(request, entity_id):
    return abstract_create_from_template_n_send(request, entity_id)


@login_required
@permission_required('emails')
@jsonify
def resend_mails(request):  # TODO: unit test
    ids = get_from_POST_or_404(request.POST, 'ids').split(',')

    for email in EntityEmail.objects.filter(pk__in=ids):
        email.send()

    return {}


# @login_required
# @permission_required('emails')
def get_entity_mail_body(request, entity_id):
    """Used to show an html document in an iframe """
    warnings.warn("The view emails.get_entity_mail_body is deprecated ; "
                  "use the core view get_sanitized_html instead.",
                  DeprecationWarning
                 )

    # email = get_object_or_404(EntityEmail, pk=entity_id)
    # request.user.has_perm_to_view_or_die(email)
    # return HttpResponse(email.get_body())

    from creme.creme_core.views.entity import get_sanitized_html_field

    return get_sanitized_html_field(request, entity_id, 'body_html')
