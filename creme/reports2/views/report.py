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

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext

from creme_core.entities_access.functions_for_permissions import add_view_or_die, get_view_or_die, edit_view_or_die
from creme_core.views.generic import add_entity, view_entity_with_template, list_view
from creme.creme_core.views.generic.edit import edit_entity

from reports2.models import Report2, report_prefix_url, report_template_dir
from reports2.forms.report import CreateForm, EditForm

report_app = Report2._meta.app_label
report_ct  = ContentType.objects.get_for_model(Report2)

@login_required
@get_view_or_die(report_app)
@add_view_or_die(report_ct, None, report_app)
def add(request):
    tpl_dict = {
        'help_messages' : []
    }
    return add_entity(request, CreateForm, template="%s/add_report.html" % report_template_dir, extra_template_dict=tpl_dict)

@login_required
@get_view_or_die(report_app)
@edit_view_or_die(report_ct, None, report_app)
def edit(request, report_id):
    return edit_entity(request, report_id, Report2, EditForm, report_app, template='%s/add_report.html' % report_template_dir)

@login_required
@get_view_or_die('reports')
def detailview(request, report_id):
    """
        @Permissions : Acces or Admin to document app & Read on current Report2 object
    """
    return view_entity_with_template(request, report_id, Report2,
                                     '%s/report' % report_prefix_url,
                                     'reports/view_report.html')

@login_required
@get_view_or_die('reports')
def listview(request):
    return list_view(request, Report2, extra_dict={'add_url':'%s/report/add' % report_prefix_url})
