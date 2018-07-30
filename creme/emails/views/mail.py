# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template import Template, Context
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import CremeEntity
from creme.creme_core.utils import jsonify, get_from_POST_or_404
from creme.creme_core.utils.html import sanitize_html
from creme.creme_core.views import generic

from .. import get_entityemail_model
from ..constants import MAIL_STATUS_SENT, DEFAULT_HFILTER_EMAIL
from ..forms.mail import EntityEmailForm, TemplateSelectionForm, EntityEmailFromTemplateForm
from ..forms.template import TEMPLATES_VARS
from ..models import LightWeightEmail


EntityEmail = get_entityemail_model()

# Function views --------------------------------------------------------------


@login_required
@permission_required('emails')
def get_lightweight_mail_body(request, mail_id):
    """Used to show an html document in an iframe """
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

    template = 'emails/view_email.html'  # TODO: rename (lw-mail-popup.html ?)
    ctx_dict = {'mail': email, 'title': _('Details of the mail')}

    if request.is_ajax():
        return generic.inner_popup(request, template, ctx_dict,
                                   is_valid=False, reload=False,
                                  )

    return render(request, template, ctx_dict)


def abstract_view_email(request, mail_id, template='emails/view_entity_mail.html'):
    warnings.warn('emails.views.mail.abstract_view_email() is deprecated ; '
                  'use the class-based view EntityEmailDetail instead.',
                  DeprecationWarning
                 )
    return generic.view_entity(request, mail_id, EntityEmail,
                               template=template,
                               # NB: not used...
                               extra_template_dict={'sent_status': MAIL_STATUS_SENT},
                              )


def abstract_popupview(request, mail_id, template='emails/view_entity_mail_popup.html'):
    warnings.warn('emails.views.mail.abstract_popupview() is deprecated ; '
                  'use the class-based view EntityEmailPopup instead.',
                  DeprecationWarning
                 )
    return generic.view_entity(request, mail_id, EntityEmail, template=template)


def abstract_create_n_send(request, entity_id, form=EntityEmailForm,
                           title=_(u'Sending an email to «%s»'),
                           submit_label=EntityEmail.sending_label,
                          ):
    return generic.add_to_entity(request, entity_id, form, title=title,
                                 link_perm=True, submit_label=submit_label,
                                )


# TODO: use a wizard. It seems hackish to work with inner popup & django.contrib.formtools.wizard.FormWizard
def abstract_create_from_template_n_send(request, entity_id,
                                         selection_form=TemplateSelectionForm,
                                         email_form=EntityEmailFromTemplateForm,
                                         template='creme_core/generics/blockform/add_popup.html',
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
                submit_label = EntityEmail.sending_label
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
                                'title':  ugettext(u'Sending an email to «{entity}» (step {step}/2)').format(
                                                entity=entity,
                                                step=step,
                                            ),
                                'submit_label': submit_label,
                               },
                               is_valid=form.is_valid(),
                               reload=False,
                               delegate_reload=True,
                              )


@login_required
@permission_required('emails')
def detailview(request, mail_id):
    warnings.warn('emails.views.mail.detailview() is deprecated.', DeprecationWarning)
    return abstract_view_email(request, mail_id)


@login_required
@permission_required('emails')
def popupview(request, mail_id):
    warnings.warn('emails.views.mail.popupview() is deprecated.', DeprecationWarning)
    return abstract_popupview(request, mail_id)


@login_required
@permission_required('emails')
def listview(request):
    return generic.list_view(request, EntityEmail, hf_pk=DEFAULT_HFILTER_EMAIL)


@login_required
@permission_required(('emails', cperm(EntityEmail)))
def create_n_send(request, entity_id):
    return abstract_create_n_send(request, entity_id)


@login_required
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


# Class-based views  ----------------------------------------------------------


class EntityEmailDetail(generic.detailview.EntityDetail):
    model = EntityEmail
    template_name = 'emails/view_entity_mail.html'
    pk_url_kwarg = 'mail_id'


class EntityEmailPopup(EntityEmailDetail):
    template_name = 'emails/view_entity_mail_popup.html'
