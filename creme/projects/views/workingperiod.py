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
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse

from creme_core.entities_access.functions_for_permissions import get_view_or_die, edit_object_or_die

from projects.forms.workingperiod import PeriodCreateForms, PeriodEditForms
from projects.blocks import working_periods_block
from projects.views.utils import _add_generic, _edit_generic
from projects.models import WorkingPeriod


@login_required
@get_view_or_die('projects')
def add(request, task_id):
    return _add_generic(request, PeriodCreateForms, task_id, u"Ajout d'une nouvelle période travaillée")

@login_required
@get_view_or_die('projects')
def edit(request, period_id):
    """
        @Permissions : Acces or Admin to project & Edit on current object
    """
    return _edit_generic(request, PeriodEditForms, period_id, WorkingPeriod, u"Edition d'une période travaillée")

@login_required
def reload_block_periods(request, task_id):
    return working_periods_block.detailview_ajax(request, task_id)

@login_required
def delete(request):
    period = get_object_or_404(WorkingPeriod, pk=request.POST.get('id'))
    related_task = period.task
    
    die_status = edit_object_or_die(request, related_task)
    if die_status:
        return die_status

    period.delete()

    return HttpResponse("")
#    return HttpResponseRedirect('/projects/task/%s' % related_task.id)
