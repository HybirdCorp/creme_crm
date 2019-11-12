# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

# import warnings

from django.db.transaction import atomic
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui.quick_forms import quickforms_registry
from creme.creme_core.models import Relation
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from creme.opportunities import get_opportunity_model
from creme.opportunities.forms.opportunity import OpportunityCreationForm  # OpportunityCreateForm

from .. import get_act_model, get_pattern_model, constants
from ..forms import act as forms
from ..models import ActType, ActObjective, MarketSegment, ActObjectivePatternComponent

Opportunity = get_opportunity_model()
Act = get_act_model()
ActObjectivePattern = get_pattern_model()

# Function views --------------------------------------------------------------


# def abstract_add_act(request, form=forms.ActForm,
#                      submit_label=Act.save_label,
#                     ):
#     warnings.warn('commercial.views.act.abstract_add_act() is deprecated ; '
#                   'use the class-based view ActCreation instead.',
#                   DeprecationWarning
#                  )
#     return generic.add_entity(request, form,
#                               extra_initial={'act_type': ActType.objects.first(),
#                                              'segment':  MarketSegment.objects.first(),
#                                             },
#                               extra_template_dict={'submit_label': submit_label},
#                              )


# def abstract_add_objective_pattern(request, form=forms.ObjectivePatternForm,
#                                    submit_label=ActObjectivePattern.save_label,
#                                   ):
#     warnings.warn('commercial.views.act.abstract_add_objective_pattern() is deprecated ; '
#                   'use the class-based view ActObjectivePatternCreation instead.',
#                   DeprecationWarning
#                  )
#     return generic.add_entity(request, form,
#                               extra_template_dict={'submit_label': submit_label},
#                              )


# def abstract_edit_act(request, act_id, form=forms.ActForm):
#     warnings.warn('commercial.views.act.abstract_edit_act() is deprecated ; '
#                   'use the class-based view ActEdition instead.',
#                   DeprecationWarning
#                  )
#     return generic.edit_entity(request, act_id, Act, form)


# def abstract_edit_objective_pattern(request, objpattern_id, form=forms.ObjectivePatternForm):
#     warnings.warn('commercial.views.act.abstract_edit_objective_pattern() is deprecated ; '
#                   'use the class-based view ActObjectivePatternEdition instead.',
#                   DeprecationWarning
#                  )
#     return generic.edit_entity(request, objpattern_id, ActObjectivePattern, form)


# def abstract_view_act(request, act_id,
#                       template='commercial/view_act.html',
#                      ):
#     warnings.warn('commercial.views.act.abstract_view_act() is deprecated ; '
#                   'use the class-based view ActDetail instead.',
#                   DeprecationWarning
#                  )
#     return generic.view_entity(request, act_id, Act, template=template)


# def abstract_view_objective_pattern(request, objpattern_id,
#                                     template='commercial/view_pattern.html',
#                                    ):
#     warnings.warn('commercial.views.act.abstract_view_objective_pattern() is deprecated ; '
#                   'use the class-based view ActObjectivePatternDetail instead.',
#                   DeprecationWarning
#                  )
#     return generic.view_entity(request, objpattern_id, ActObjectivePattern,
#                                template=template,
#                               )


# def abstract_add_opportunity(request, act_id, form=OpportunityCreateForm,
#                              template='creme_core/generics/blockform/add_popup.html',
#                              title=_('Create a linked opportunity'),
#                              submit_label=Opportunity.save_label,
#                             ):
#     warnings.warn('commercial.views.act.abstract_add_opportunity() is deprecated ; '
#                   'use the class-based view RelatedOpportunityCreation instead.',
#                   DeprecationWarning
#                  )
#
#     act = get_object_or_404(Act, pk=act_id)
#     user = request.user
#
#     has_perm = user.has_perm_to_link_or_die
#     has_perm(act)
#     has_perm(Opportunity)
#
#     if request.method == 'POST':
#         form_instance = form(user=user, data=request.POST)
#
#         if form_instance.is_valid():
#             with atomic():
#                 opp = form_instance.save()
#                 Relation.objects.create(subject_entity=opp,
#                                         type_id=constants.REL_SUB_COMPLETE_GOAL,
#                                         object_entity=act,
#                                         user=user,
#                                        )
#     else:
#         form_instance = form(user=user)
#
#     return generic.inner_popup(request, template,
#                                {'form': form_instance,
#                                 'title': title,
#                                 'submit_label': submit_label,
#                                },
#                                is_valid=form_instance.is_valid(),
#                                reload=False,
#                                delegate_reload=True,
#                               )


# @login_required
# @permission_required(('commercial', cperm(Act)))
# def add(request):
#     warnings.warn('commercial.views.act.add() is deprecated.', DeprecationWarning)
#     return abstract_add_act(request)


# @login_required
# @permission_required(('commercial', cperm(ActObjectivePattern)))
# def add_objective_pattern(request):
#     warnings.warn('commercial.views.act.add_objective_pattern() is deprecated.', DeprecationWarning)
#     return abstract_add_objective_pattern(request)


# @login_required
# @permission_required('commercial')
# def edit(request, act_id):
#     warnings.warn('commercial.views.act.edit() is deprecated.', DeprecationWarning)
#     return abstract_edit_act(request, act_id)


# @login_required
# @permission_required('commercial')
# def edit_objective_pattern(request, objpattern_id):
#     warnings.warn('commercial.views.act.edit_objective_pattern() is deprecated.', DeprecationWarning)
#     return abstract_edit_objective_pattern(request, objpattern_id)


# @login_required
# @permission_required('commercial')
# def detailview(request, act_id):
#     warnings.warn('commercial.views.act.detailview() is deprecated.', DeprecationWarning)
#     return abstract_view_act(request, act_id)


# @login_required
# @permission_required('commercial')
# def objective_pattern_detailview(request, objpattern_id):
#     warnings.warn('commercial.views.act.objective_pattern_detailview() is deprecated.', DeprecationWarning)
#     return abstract_view_objective_pattern(request, objpattern_id)


# Class-based views  ----------------------------------------------------------

class ActCreation(generic.EntityCreation):
    model = Act
    form_class = forms.ActForm

    def get_initial(self):
        initial = super().get_initial()
        initial['act_type'] = ActType.objects.first()
        initial['segment']  = MarketSegment.objects.first()

        return initial


class ActObjectivePatternCreation(generic.EntityCreation):
    model = ActObjectivePattern
    form_class = forms.ObjectivePatternForm


class RelatedOpportunityCreation(generic.AddingInstanceToEntityPopup):
    model = Opportunity
    form_class = OpportunityCreationForm
    permissions = ['opportunities', cperm(Opportunity)]
    title = _('Create a linked opportunity')
    entity_id_url_kwarg = 'act_id'
    entity_classes = Act
    entity_form_kwarg = None

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        user.has_perm_to_link_or_die(Opportunity)

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_link_or_die(entity)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['forced_relations'] = [
            Relation(type_id=constants.REL_SUB_COMPLETE_GOAL,
                     object_entity=self.related_entity,
                    ),
        ]

        return kwargs

    # # @atomic
    # def form_valid(self, form):
    #     response = super().form_valid(form=form)
    #     Relation.objects.create(subject_entity=form.instance,
    #                             type_id=constants.REL_SUB_COMPLETE_GOAL,
    #                             object_entity=self.related_entity,
    #                             user=self.request.user,
    #                            )
    #
    #     return response


class ActDetail(generic.EntityDetail):
    model = Act
    template_name = 'commercial/view_act.html'
    pk_url_kwarg = 'act_id'


class ActObjectivePatternDetail(generic.EntityDetail):
    model = ActObjectivePattern
    template_name = 'commercial/view_pattern.html'
    pk_url_kwarg = 'objpattern_id'


class ActEdition(generic.EntityEdition):
    model = Act
    form_class = forms.ActForm
    pk_url_kwarg = 'act_id'


class ActObjectivePatternEdition(generic.EntityEdition):
    model = ActObjectivePattern
    form_class = forms.ObjectivePatternForm
    pk_url_kwarg = 'objpattern_id'


class ActsList(generic.EntitiesList):
    model = Act
    default_headerfilter_id = constants.DEFAULT_HFILTER_ACT


class ActObjectivePatternsList(generic.EntitiesList):
    model = ActObjectivePattern
    default_headerfilter_id = constants.DEFAULT_HFILTER_PATTERN


# Other views  ----------------------------------------------------------------


# @login_required
# @permission_required('commercial')
# def listview(request):
#     return generic.list_view(request, Act, hf_pk=constants.DEFAULT_HFILTER_ACT)


# @login_required
# @permission_required('commercial')
# def listview_objective_pattern(request):
#     return generic.list_view(request, ActObjectivePattern, hf_pk=constants.DEFAULT_HFILTER_PATTERN)


# @login_required
# @permission_required(('opportunities', cperm(Opportunity)))
# def add_opportunity(request, act_id):
#     warnings.warn('commercial.views.act.add_opportunity() is deprecated.', DeprecationWarning)
#     return abstract_add_opportunity(request, act_id)


class ObjectiveCreation(generic.AddingInstanceToEntityPopup):
    model = ActObjective
    form_class = forms.ObjectiveForm
    title = _('New objective for «{entity}»')
    entity_id_url_kwarg = 'act_id'
    entity_classes = Act


class ObjectivesCreationFromPattern(generic.RelatedToEntityFormPopup):
    form_class = forms.ObjectivesFromPatternForm
    title = _('New objectives for «{entity}»')
    submit_label = _('Save the objectives')
    entity_id_url_kwarg = 'act_id'
    entity_classes = Act


class PatternComponentCreation(generic.AddingInstanceToEntityPopup):
    model = ActObjectivePatternComponent
    form_class = forms.PatternComponentForm
    title = _('New objective for «{entity}»')
    submit_label = _('Save the objective')
    entity_id_url_kwarg = 'objpattern_id'
    entity_classes = ActObjectivePattern


class SubPatternComponentCreation(generic.AddingInstanceToEntityPopup):
    model = ActObjectivePatternComponent
    # form_class = ....
    # title = 'Objective for «{component}»'
    submit_label = _('Save the objective')  # TODO: ActObjectivePatternComponent.save_label ?
    # entity_id_url_kwarg = ''
    entity_classes = ActObjectivePattern
    entity_form_kwarg = None

    component_id_url_kwarg = 'component_id'
    # component_form_kwarg = ...

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.related_component = None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs[self.component_form_kwarg] = self.get_related_component()

        return kwargs

    def get_related_entity_id(self):
        return self.get_related_component().pattern_id

    def get_related_component(self):
        comp = self.related_component

        if comp is None:
            self.related_component = comp = get_object_or_404(
                ActObjectivePatternComponent,
                id=self.kwargs[self.component_id_url_kwarg],
            )

        return comp

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['component'] = self.get_related_component()

        return data


class ChildPatternComponentCreation(SubPatternComponentCreation):
    form_class = forms.PatternChildComponentForm
    title = _('New child objective for «{component}»')
    component_form_kwarg = 'parent'


class ParentPatternComponentCreation(SubPatternComponentCreation):
    form_class = forms.PatternParentComponentForm
    title = _('New parent objective for «{component}»')
    component_form_kwarg = 'child'


class ObjectiveEdition(generic.RelatedToEntityEditionPopup):
    model = ActObjective
    form_class = forms.ObjectiveForm
    pk_url_kwarg = 'objective_id'
    title = _('Objective for «{entity}»')


@login_required
@permission_required('commercial')
def incr_objective_counter(request, objective_id):
    incr = get_from_POST_or_404(request.POST, 'diff', int)

    with atomic():
        try:
            objective = ActObjective.objects.select_for_update().get(pk=objective_id)
        except ActObjective.DoesNotExist as e:
            raise Http404(str(e)) from e

        request.user.has_perm_to_change_or_die(objective.act)

        if objective.ctype:
            raise ConflictError('This objective is a relationship counter.')

        objective.counter += incr
        objective.save()

    return HttpResponse()


class RelatedEntityCreation(generic.AddingInstanceToEntityPopup):
    # model = ...
    # form_class = ....
    # title = ...
    # submit_label = ...
    # entity_id_url_kwarg = ''
    entity_classes = Act
    entity_form_kwarg = None

    objective_id_url_kwarg = 'objective_id'
    forms_registry = quickforms_registry

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.related_objective = None
        self.created_model = None

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_link_or_die(entity)

    def get_created_model(self):
        model = self.created_model

        if model is None:
            objective = self.get_related_objective()
            ctype = objective.ctype

            if ctype is None:
                raise ConflictError('This objective is not a relationship counter.')

            if objective.filter_id is not None:
                raise ConflictError('This objective has a filter, so you cannot build a related entity.')

            model = ctype.model_class()
            user = self.request.user
            user.has_perm_to_create_or_die(model)
            user.has_perm_to_link_or_die(model)

            self.created_model = model

        return model

    def get_form_class(self):
        form_class = self.forms_registry.get_form(self.get_created_model())

        if form_class is None:
            raise ConflictError('This type of resource has no quick form.')

        return form_class

    def form_valid(self, form):
        response = super().form_valid(form=form)
        Relation.objects.create(subject_entity=form.instance,
                                type_id=constants.REL_SUB_COMPLETE_GOAL,
                                object_entity=self.related_entity,
                                user=self.request.user,
                               )

        return response

    def get_related_entity_id(self):
        return self.get_related_objective().act_id

    def get_related_objective(self):
        objective = self.related_objective

        if objective is None:
            self.related_objective = objective = get_object_or_404(
                ActObjective,
                id=self.kwargs[self.objective_id_url_kwarg],
            )

        return objective

    def get_title(self):
        return self.get_created_model().creation_label

    def get_submit_label(self):
        return self.get_created_model().save_label
