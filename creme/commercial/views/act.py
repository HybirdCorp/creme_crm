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

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views import generic
from creme_core.gui.last_viewed import change_page_for_last_item_viewed
from creme_core.utils import get_from_POST_or_404

from commercial.models import Act, ActObjective
from commercial.forms.act import ActForm, ObjectiveForm, RelationObjectiveForm


@login_required
@permission_required('commercial')
@permission_required('commercial.add_act')
def add(request):
    return generic.add_entity(request, ActForm)

@login_required
@permission_required('commercial')
def edit(request, act_id):
    return generic.edit_entity(request, act_id, Act, ActForm)

@login_required
@permission_required('commercial')
def detailview(request, act_id):
    return generic.view_entity(request, act_id, Act, '/commercial/act',
                               template='commercial/view_act.html'
                              )

@login_required
@permission_required('commercial')
@change_page_for_last_item_viewed #WTF ???
def listview(request):
    return generic.list_view(request, Act, extra_dict={'add_url': '/commercial/act/add'})

@login_required
@permission_required('commercial')
def add_custom_objective(request, act_id):
    return generic.add_to_entity(request, act_id, ObjectiveForm,
                                 _(u'New objective for <%s>'), entity_class=Act
                                )

#TODO: factorise
@login_required
@permission_required('commercial')
def add_relation_objective(request, act_id):
    return generic.add_to_entity(request, act_id, RelationObjectiveForm,
                                 _(u'New objective for <%s>'), entity_class=Act
                                )

@login_required
@permission_required('commercial')
def edit_objective(request, objective_id):
    return generic.edit_related_to_entity(request, objective_id, ActObjective, ObjectiveForm,
                                          _(u'Objective for <%s>')
                                         )

@login_required
@permission_required('commercial')
def delete_objective(request):
    return generic.delete_related_to_entity(request, ActObjective)

@login_required
@permission_required('commercial')
def incr_objective_counter(request, objective_id): #TODO: test if relation Objective ???
    objective = get_object_or_404(ActObjective, pk=objective_id)
    objective.act.can_change_or_die(request.user)

    objective.counter += get_from_POST_or_404(request.POST, 'diff', int)
    objective.save()

    return HttpResponse()

__B2S_MAP = {
        'true':  True,
        'false': False,
    }

#TODO: move in creme_core ??
def bool_from_str(string):
    b = __B2S_MAP.get(string)

    if b is not None:
        return b

    raise ValueError('Can not be coerce to a boolean value: %s' % str(string))

@login_required
@permission_required('commercial')
def reach_objective(request, objective_id): #TODO: test if relation Objective ???
    objective = get_object_or_404(ActObjective, pk=objective_id)
    objective.act.can_change_or_die(request.user)

    objective.reached = get_from_POST_or_404(request.POST, 'reached', bool_from_str)
    objective.save()

    return HttpResponse()
