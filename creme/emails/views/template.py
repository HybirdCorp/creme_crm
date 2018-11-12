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
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _  # ugettext

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from .. import get_emailtemplate_model
from ..constants import DEFAULT_HFILTER_TEMPLATE
from ..forms import template as tpl_forms


EmailTemplate = get_emailtemplate_model()

# Function views --------------------------------------------------------------


def abstract_add_template(request, form=tpl_forms.EmailTemplateForm,
                          submit_label=EmailTemplate.save_label,
                         ):
    warnings.warn('emails.views.mail.abstract_add_template() is deprecated ; '
                  'use the class-based view EmailTemplateCreation instead.',
                  DeprecationWarning
                 )
    return generic.add_entity(request, form,
                              extra_template_dict={'submit_label': submit_label},
                             )


def abstract_edit_template(request, template_id, form=tpl_forms.EmailTemplateForm):
    warnings.warn('emails.views.mail.abstract_edit_template() is deprecated ; '
                  'use the class-based view EmailTemplateEdition instead.',
                  DeprecationWarning
                 )
    return generic.edit_entity(request, template_id, EmailTemplate, form)


def abstract_view_template(request, template_id,
                           template='emails/view_template.html',
                          ):
    warnings.warn('emails.views.mail.abstract_view_template() is deprecated ; '
                  'use the class-based view EmailTemplateDetail instead.',
                  DeprecationWarning
                 )
    return generic.view_entity(request, template_id, EmailTemplate, template=template)


@login_required
@permission_required(('emails', cperm(EmailTemplate)))
def add(request):
    warnings.warn('emails.views.mail.add() is deprecated.', DeprecationWarning)
    return abstract_add_template(request)


@login_required
@permission_required('emails')
def edit(request, template_id):
    warnings.warn('emails.views.mail.edit() is deprecated.', DeprecationWarning)
    return abstract_edit_template(request, template_id)


@login_required
@permission_required('emails')
def detailview(request, template_id):
    warnings.warn('emails.views.mail.detailview() is deprecated.', DeprecationWarning)
    return abstract_view_template(request, template_id)


@login_required
@permission_required('emails')
def listview(request):
    return generic.list_view(request, EmailTemplate, hf_pk=DEFAULT_HFILTER_TEMPLATE)


# @login_required
# @permission_required('emails')
# def add_attachment(request, template_id):
#     return generic.add_to_entity(
#         request, template_id, tpl_forms.EmailTemplateAddAttachment,
#         ugettext('New attachments for «%s»'),
#         entity_class=EmailTemplate,
#         submit_label=_('Save the attachments'),
#         template='creme_core/generics/blockform/link_popup.html',
#     )


@login_required
@permission_required('emails')
def delete_attachment(request, template_id):
    attachment_id = get_from_POST_or_404(request.POST, 'id')
    template = get_object_or_404(EmailTemplate, pk=template_id)

    request.user.has_perm_to_change_or_die(template)

    template.attachments.remove(attachment_id)

    if request.is_ajax():
        return HttpResponse()

    return redirect(template)


# Class-based views  ----------------------------------------------------------

class EmailTemplateCreation(generic.EntityCreation):
    model = EmailTemplate
    form_class = tpl_forms.EmailTemplateForm


class EmailTemplateDetail(generic.EntityDetail):
    model = EmailTemplate
    template_name = 'emails/view_template.html'
    pk_url_kwarg = 'template_id'


class EmailTemplateEdition(generic.EntityEdition):
    model = EmailTemplate
    form_class = tpl_forms.EmailTemplateForm
    pk_url_kwarg = 'template_id'


class AttachmentsAdding(generic.AddingToEntityPopup):
    # model = Document
    form_class = tpl_forms.EmailTemplateAddAttachment
    template_name = 'creme_core/generics/blockform/link-popup.html'
    title_format = _('New attachments for «{}»')
    submit_label = _('Add the attachments')
    entity_id_url_kwarg = 'template_id'
    entity_classes = EmailTemplate
