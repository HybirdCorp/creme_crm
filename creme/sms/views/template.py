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

from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import add_entity, edit_entity, view_entity_with_template, list_view

from sms.models import MessageTemplate
from sms.forms.template import TemplateCreateForm, TemplateEditForm


@login_required
@permission_required('sms')
@permission_required('sms.add_messagetemplate')
def add(request):
    return add_entity(request, TemplateCreateForm)

@login_required
@permission_required('sms')
def edit(request, template_id):
    return edit_entity(request, template_id, MessageTemplate, TemplateEditForm)

@login_required
@permission_required('sms')
def detailview(request, template_id):
    return view_entity_with_template(request, template_id, MessageTemplate,
                                     '/sms/template',
                                     'sms/view_template.html')

@login_required
@permission_required('sms')
def listview(request):
    return list_view(request, MessageTemplate, extra_dict={'add_url': '/sms/template/add'})
