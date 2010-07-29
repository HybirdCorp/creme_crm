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
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.entities_access.functions_for_permissions import get_view_or_die, add_view_or_die, edit_object_or_die
from creme_core.views.generic import add_entity, edit_entity, view_entity_with_template, list_view, inner_popup

from emails.models import EmailTemplate
from emails.forms.template import TemplateCreateForm, TemplateEditForm, TemplateAddAttachment


@login_required
@get_view_or_die('emails')
@add_view_or_die(ContentType.objects.get_for_model(EmailTemplate), None, 'emails')
def add(request):
    return add_entity(request, TemplateCreateForm)

def edit(request, template_id):
    return edit_entity(request, template_id, EmailTemplate, TemplateEditForm, 'emails')

@login_required
@get_view_or_die('emails')
def detailview(request, template_id):
    return view_entity_with_template(request, template_id, EmailTemplate,
                                     '/emails/template',
                                     'emails/view_template.html')

@login_required
@get_view_or_die('emails')
def listview(request):
    return list_view(request, EmailTemplate, extra_dict={'add_url': '/emails/template/add'})

@login_required
@get_view_or_die('emails')
def add_attachment(request, template_id):
    template = get_object_or_404(EmailTemplate, pk=template_id)

    die_status = edit_object_or_die(request, template)
    if die_status:
        return die_status

    if request.POST:
        attachment_add_form = TemplateAddAttachment(template, request.POST)

        if attachment_add_form.is_valid():
            attachment_add_form.save()
    else:
        attachment_add_form = TemplateAddAttachment(template=template)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':   attachment_add_form,
                        'title': 'Nouveaux fichiers joints pour <%s>' % template,
                       },
                       is_valid=attachment_add_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

@login_required
@get_view_or_die('emails')
def delete_attachment(request, template_id):
    template = get_object_or_404(EmailTemplate, pk=template_id)

    die_status = edit_object_or_die(request, template)
    if die_status:
        return die_status

    template.attachments.remove(request.POST.get('id'))

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(template.get_absolute_url())
