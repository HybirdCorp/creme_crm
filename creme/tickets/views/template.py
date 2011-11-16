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

from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import edit_entity, view_entity, list_view

from tickets.models import TicketTemplate
from tickets.forms.template import TicketTemplateForm


@login_required
@permission_required('tickets')
def edit(request, template_id):
    return edit_entity(request, template_id, TicketTemplate, TicketTemplateForm)

@login_required
@permission_required('tickets')
def detailview(request, template_id):
    return view_entity(request, template_id, TicketTemplate, '/tickets/template', 'tickets/view_template.html')

@login_required
@permission_required('tickets')
def listview(request):
    return list_view(request, TicketTemplate)
