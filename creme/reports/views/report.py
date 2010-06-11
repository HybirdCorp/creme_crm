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

from creme_core.entities_access.functions_for_permissions import get_view_or_die
from creme_core.views.generic import view_entity_with_template, list_view

from reports.models import Operation, Report


@login_required
@get_view_or_die('reports')
def add(request):
    return render_to_response('reports/add_report.html',
                              {
                                'cts':          ContentType.objects.all(),
                                'operations':   Operation.objects.all(),
                              },
                              context_instance=RequestContext(request))

#TODO: credentials ???? use edit_entity() ??
def edit(request, report_id):
    return render_to_response('reports/add_report.html',
                              {
                                'report':       get_object_or_404(Report, pk=report_id),
                                'cts':          ContentType.objects.all(),
                                'operations':   Operation.objects.all(),
                              },
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('reports')
def detailview(request, report_id):
    """
        @Permissions : Acces or Admin to document app & Read on current Ticket object
    """
    return view_entity_with_template(request, report_id, Report,
                                     '/reports/report',
                                     'reports/view_report.html')

@login_required
#@get_view_or_die('reports') ??
def view_csv(request, report_id):
    return Report.objects.get(pk=report_id).generateCSV() #get_object_or_404 ? credentials ??

@login_required
def view_odt(request, report_id):
    return Report.objects.get(pk=report_id).generateODT()

@login_required
@get_view_or_die('reports')
def listview(request):
    return list_view(request, Report, extra_dict={'add_url':'/reports/report/add'})
