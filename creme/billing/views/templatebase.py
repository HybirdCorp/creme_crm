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

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect

from creme_core.entities_access.functions_for_permissions import get_view_or_die, delete_object_or_die
from creme_core.views.generic import edit_entity, list_view

from billing.models import TemplateBase
from billing.forms.templatebase import TemplateBaseEditForm
from billing.views.base import view_billing_entity


def edit(request, template_id):
    return edit_entity(request, template_id, TemplateBase, TemplateBaseEditForm, 'billing')

@login_required
@get_view_or_die('recurrents')
def detailview(request, template_id):
    template = get_object_or_404(TemplateBase, pk=template_id)
    return view_billing_entity(request, template_id, template, '/billing/template', 'billing/view_template.html')

@login_required
@get_view_or_die('billing')
def listview(request):
    return list_view(request, TemplateBase, extra_dict={'add_url':'/recurrents/generator/add'})

@login_required
@get_view_or_die('recurrents')
def delete(request, template_id):
    template = get_object_or_404(TemplateBase, pk=template_id)

    die_status = delete_object_or_die(request, template)

    if die_status:
        return die_status

    generator = template.get_generator()

    die_status = delete_object_or_die(request, template)

    if die_status:
        return die_status

    if generator:
        generator.delete()
    template.delete()
    
    return HttpResponseRedirect('/recurrents/generators')
