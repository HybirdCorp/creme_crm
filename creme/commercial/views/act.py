# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from django.db.transaction import commit_on_success
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui.quick_forms import quickforms_registry
from creme.creme_core.models import Relation
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.utils.queries import get_first_or_None
from creme.creme_core.views import generic

from creme.opportunities.forms.opportunity import OpportunityCreateForm
from creme.opportunities.models import Opportunity

from ..constants import REL_SUB_COMPLETE_GOAL
from ..forms import act as forms
from ..models import (ActType, Act, ActObjective, MarketSegment,
        ActObjectivePattern, ActObjectivePatternComponent)


@login_required
@permission_required('commercial')
@permission_required('commercial.add_act')
def add(request):
    return generic.add_entity(request, forms.ActForm,
                              extra_initial={'act_type': get_first_or_None(ActType),
                                             'segment':  get_first_or_None(MarketSegment),
                                            },
                              extra_template_dict={'submit_label': _('Save the commercial action')},
                             )

@login_required
@permission_required('commercial')
@permission_required('commercial.add_actobjectivepattern')
def add_objective_pattern(request):
    return generic.add_entity(request, forms.ObjectivePatternForm,
                              extra_template_dict={'submit_label': _('Save the objective pattern')},
                             )

@login_required
@permission_required('commercial')
def edit(request, act_id):
    return generic.edit_entity(request, act_id, Act, forms.ActForm)

@login_required
@permission_required('commercial')
def edit_objective_pattern(request, objpattern_id):
    return generic.edit_entity(request, objpattern_id, ActObjectivePattern, forms.ObjectivePatternForm)

@login_required
@permission_required('commercial')
def detailview(request, act_id):
    return generic.view_entity(request, act_id, Act, '/commercial/act',
                               template='creme_core/generics/view_entity.html'
                              )

@login_required
@permission_required('commercial')
def objective_pattern_detailview(request, objpattern_id):
    return generic.view_entity(request, objpattern_id, ActObjectivePattern,
                               '/commercial/objective_pattern',
                               template='commercial/view_pattern.html'
                              )

@login_required
@permission_required('commercial')
def listview(request):
    return generic.list_view(request, Act, extra_dict={'add_url': '/commercial/act/add'})

@login_required
@permission_required('commercial')
def listview_objective_pattern(request):
    return generic.list_view(request, ActObjectivePattern,
                             extra_dict={'add_url': '/commercial/objective_pattern/add'},
                            )

@login_required
@permission_required('opportunities')
@permission_required('opportunities.add_opportunity')
def add_opportunity(request, act_id):
    act = get_object_or_404(Act, pk=act_id)
    user = request.user

    user.has_perm_to_link_or_die(act)
    user.has_perm_to_link_or_die(Opportunity)

    if request.method == 'POST':
        form = OpportunityCreateForm(user=user, data=request.POST)

        if form.is_valid():
            with commit_on_success():
                opp = form.save()
                Relation.objects.create(subject_entity=opp,
                                        type_id=REL_SUB_COMPLETE_GOAL,
                                        object_entity=act,
                                        user=user,
                                       )
    else:
        form = OpportunityCreateForm(user=user)

    return generic.inner_popup(request,
                               'creme_core/generics/blockform/add_popup2.html',
                               {'form':   form,
                                'title':  _(u'Add a linked opportunity'),
                               },
                               is_valid=form.is_valid(),
                               reload=False,
                               delegate_reload=True,
                              )

@login_required
@permission_required('commercial')
def _add_objective(request, act_id, form_class):
    return generic.add_to_entity(request, act_id, form_class,
                                 ugettext(u'New objective for <%s>'), entity_class=Act
                                )

def add_objective(request, act_id):
    return _add_objective(request, act_id, forms.ObjectiveForm)

def add_objectives_from_pattern(request, act_id):
    return _add_objective(request, act_id, forms.ObjectivesFromPatternForm)

@login_required
@permission_required('commercial')
def add_pattern_component(request, objpattern_id):
    return generic.add_to_entity(request, objpattern_id, forms.PatternComponentForm,
                                 ugettext(u'New objective for <%s>'), entity_class=ActObjectivePattern
                                )

@login_required
@permission_required('commercial')
def _add_subpattern_component(request, component_id, form_class, title):
    related_comp = get_object_or_404(ActObjectivePatternComponent, pk=component_id)
    user = request.user

    user.has_perm_to_change_or_die(related_comp.pattern)

    if request.method == 'POST':
        form = form_class(related_comp, user=user, data=request.POST)

        if form.is_valid():
            form.save()
    else:
        form = form_class(related_comp, user=user)

    return generic.inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                               {'form':  form,
                                'title': title % related_comp,
                               },
                               is_valid=form.is_valid(),
                               reload=False,
                               delegate_reload=True,
                              )

def add_child_pattern_component(request, component_id):
    return _add_subpattern_component(request, component_id,
                                     forms.PatternChildComponentForm,
                                     ugettext('New child objective for <%s>'),
                                    )

def add_parent_pattern_component(request, component_id):
    return _add_subpattern_component(request, component_id,
                                     forms.PatternParentComponentForm,
                                     ugettext('New parent objective for <%s>'),
                                    )

@login_required
@permission_required('commercial')
def edit_objective(request, objective_id):
    return generic.edit_related_to_entity(request, objective_id, ActObjective, forms.ObjectiveForm,
                                          ugettext(u'Objective for <%s>'),
                                         )

@login_required
@permission_required('commercial')
def incr_objective_counter(request, objective_id): #TODO: test if relation Objective ???
    objective = get_object_or_404(ActObjective, pk=objective_id)
    request.user.has_perm_to_change_or_die(objective.act)

    objective.counter += get_from_POST_or_404(request.POST, 'diff', int)
    objective.save()

    return HttpResponse()

@login_required
@permission_required('commercial')
def create_objective_entity(request, objective_id):
    objective = get_object_or_404(ActObjective, pk=objective_id)
    user = request.user
    user.has_perm_to_link_or_die(objective.act)

    ctype = objective.ctype
    if ctype is None:
        raise ConflictError('This objective is not a relationship counter.')

    if objective.filter_id is not None:
        raise ConflictError('This objective has a filter, so you cannot build a related entity.')

    model = ctype.model_class()
    user.has_perm_to_create_or_die(model)
    user.has_perm_to_link_or_die(model)

    form_class = quickforms_registry.get_form(model)
    if form_class is None:
        raise ConflictError('This type of resource has no quick form.')

    if request.method == 'POST':
        form = form_class(user=user, data=request.POST)

        if form.is_valid():
            with commit_on_success():
                entity = form.save()
                Relation.objects.create(subject_entity=entity,
                                        type_id=REL_SUB_COMPLETE_GOAL,
                                        object_entity=objective.act,
                                        user=user,
                                       )
    else: #return page on GET request
        form = form_class(user=user)

    return generic.inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {'form':  form,
                        'title': model.creation_label,
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )
