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
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import add_entity, add_to_entity, edit_entity, view_entity_with_template, list_view
from creme_core.utils import get_from_POST_or_404

from emails.models import EmailTemplate
from emails.forms.template import TemplateCreateForm, TemplateEditForm, TemplateAddAttachment


@login_required
@permission_required('emails')
@permission_required('emails.add_emailtemplate')
def add(request):
    return add_entity(request, TemplateCreateForm)

def edit(request, template_id):
    return edit_entity(request, template_id, EmailTemplate, TemplateEditForm, 'emails')

@login_required
@permission_required('emails')
def detailview(request, template_id):
    return view_entity_with_template(request, template_id, EmailTemplate,
                                     '/emails/template',
                                     'emails/view_template.html')

@login_required
@permission_required('emails')
def listview(request):
    return list_view(request, EmailTemplate, extra_dict={'add_url': '/emails/template/add'})

def add_attachment(request, template_id):
    return add_to_entity(request, template_id, TemplateAddAttachment,
                         _('New attachments for <%s>'), entity_class=EmailTemplate)

@login_required
@permission_required('emails')
def delete_attachment(request, template_id):
    attachment_id = get_from_POST_or_404(request.POST, 'id')
    template = get_object_or_404(EmailTemplate, pk=template_id)

    template.change_or_die(request.user)

    template.attachments.remove(attachment_id)

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(template.get_absolute_url())
