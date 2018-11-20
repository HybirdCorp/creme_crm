# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2018  Hybird
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

import warnings

from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect  # render
from django.utils.translation import ugettext as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.utils import jsonify
from creme.creme_core.views import generic
from creme.creme_core.views.generic.base import EntityRelatedMixin

from .. import get_pollform_model
from ..constants import DEFAULT_HFILTER_PFORM
from ..forms import poll_form as pf_forms
from ..models import PollFormSection, PollFormLine, PollFormLineCondition
from ..utils import StatsTree, NodeStyle  # TODO: templatetag instead ?


PollForm = get_pollform_model()

# Function views --------------------------------------------------------------


def abstract_add_pollform(request, form=pf_forms.PollFormForm,
                          submit_label=PollForm.save_label,
                         ):
    warnings.warn('polls.views.poll_form.abstract_add_pollform() is deprecated ; '
                  'use the class-based view PollFormCreation instead.',
                  DeprecationWarning
                 )
    return generic.add_entity(request, form,
                              extra_template_dict={'submit_label': submit_label},
                             )


def abstract_edit_pollform(request, pform_id, form=pf_forms.PollFormForm):
    warnings.warn('polls.views.poll_form.abstract_edit_pollform() is deprecated ; '
                  'use the class-based view PollFormEdition instead.',
                  DeprecationWarning
                 )
    return generic.edit_entity(request, pform_id, PollForm, form)


def abstract_view_pollform(request, pform_id,
                           template='polls/view_pollform.html',
                          ):
    warnings.warn('polls.views.poll_form.abstract_view_pollform() is deprecated ; '
                  'use the class-based view PollFormDetail instead.',
                  DeprecationWarning
                 )
    return generic.view_entity(request, pform_id, PollForm, template=template)


@login_required
@permission_required(('polls', cperm(PollForm)))
def add(request):
    warnings.warn('polls.views.poll_form.add() is deprecated.', DeprecationWarning)
    return abstract_add_pollform(request)


@login_required
@permission_required('polls')
def edit(request, pform_id):
    warnings.warn('polls.views.poll_form.edit() is deprecated.', DeprecationWarning)
    return abstract_edit_pollform(request, pform_id)


@login_required
@permission_required('polls')
def detailview(request, pform_id):
    warnings.warn('polls.views.poll_form.detailview() is deprecated.', DeprecationWarning)
    return abstract_view_pollform(request, pform_id)


@login_required
@permission_required('polls')
def listview(request):
    return generic.list_view(request, PollForm, hf_pk=DEFAULT_HFILTER_PFORM)


# @login_required
# @permission_required('polls')
# def add_line(request, pform_id):
#     return generic.add_to_entity(request, pform_id,
#                                  pf_forms.PollFormLineCreateForm,
#                                 _('New question for «%s»'),
#                                 entity_class=PollForm,
#                                 submit_label=PollFormLine.save_label,
#                                )

# @login_required
# @permission_required('polls')
# def edit_line(request, line_id):
#     return generic.edit_related_to_entity(request, line_id, PollFormLine,
#                                           pf_forms.PollFormLineEditForm,
#                                           _('Question for «%s»'),
#                                          )
class LineEdition(generic.RelatedToEntityEditionPopup):
    # model = PollFormLine
    queryset = PollFormLine.objects.filter(disabled=False)
    form_class = pf_forms.PollFormLineEditForm
    permissions = 'polls'
    pk_url_kwarg = 'line_id'
    title_format = _('Question for «{}»')


@login_required
@permission_required('polls')
def disable_line(request, line_id):
    if request.method != 'POST':
        raise Http404('This view uses POST method.')

    line = get_object_or_404(PollFormLine, pk=line_id)
    pform = line.pform

    request.user.has_perm_to_change_or_die(pform)

    try:
        line.disable()
    except ProtectedError as e:
        raise PermissionDenied(e.args[0]) from e

    if request.is_ajax():
        return HttpResponse()

    return redirect(pform)


# @login_required
# @permission_required('polls')
# def edit_line_conditions(request, line_id):
#     line = get_object_or_404(PollFormLine, pk=line_id)
#
#     if line.disabled:
#         raise Http404('You can not add condition to a disabled line.')
#
#     return generic.add_to_entity(request, line.pform_id,
#                                  pf_forms.PollFormLineConditionsForm,
#                                  _('Condition for «%s»'),
#                                  entity_class=PollForm,
#                                  initial={'line': line},
#                                  submit_label=PollFormLineCondition.save_label,
#                                 )


# @login_required
# @permission_required('polls')
# def add_section(request, pform_id):
#     return generic.add_to_entity(request, pform_id,
#                                  pf_forms.PollFormSectionCreateForm,
#                                  _('New section for «%s»'),
#                                  entity_class=PollForm,
#                                  submit_label=PollFormSection.save_label,
#                                 )


# @login_required
# @permission_required('polls')
# def edit_section(request, section_id):
#     return generic.edit_related_to_entity(request, section_id, PollFormSection,
#                                           pf_forms.PollFormSectionEditForm,
#                                           _('Section for «%s»'),
#                                          )
class SectionEdition(generic.RelatedToEntityEditionPopup):
    model = PollFormSection
    form_class = pf_forms.PollFormSectionEditForm
    permissions = 'polls'
    pk_url_kwarg = 'section_id'
    title_format = _('Section for «{}»')

# @login_required
# @permission_required('polls')
# def add_section_child(request, section_id):
#     parent_section = get_object_or_404(PollFormSection, pk=section_id)
#
#     return generic.add_to_entity(request, parent_section.pform_id,
#                                  pf_forms.PollFormSectionCreateForm,
#                                  _('New section for «%s»'),
#                                  entity_class=PollForm,
#                                  initial={'parent': parent_section},
#                                  submit_label=PollFormSection.save_label,
#                                 )


# @login_required
# @permission_required('polls')
# def add_line_to_section(request, section_id):
#     section = get_object_or_404(PollFormSection, pk=section_id)
#
#     return generic.add_to_entity(request, section.pform_id,
#                                  pf_forms.PollFormLineCreateForm,
#                                  _('New question for «%s»'),
#                                  entity_class=PollForm,
#                                  initial={'section': section},
#                                  submit_label=PollFormLine.save_label,
#                                 )


# @login_required
# @permission_required('polls')
# def stats(request, pform_id):
#     pform = get_object_or_404(PollForm, pk=pform_id)
#
#     return render(request, 'polls/stats.html',
#                   {'nodes': StatsTree(pform),
#                    'style': NodeStyle(),
#                   }
#                  )
class Statistics(generic.EntityDetail):
    model = PollForm
    pk_url_kwarg = 'pform_id'
    template_name = 'polls/stats.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nodes'] = StatsTree(self.object)
        context['style'] = NodeStyle()

        return context


@login_required
@permission_required('polls')
@jsonify
def get_choices(request, line_id):
    line = get_object_or_404(PollFormLine, pk=line_id)
    request.user.has_perm_to_view_or_die(line.pform)

    choices = line.poll_line_type.get_choices()

    if choices is None:
        raise Http404('This line type has no choices.')

    return choices

# Class-based views  ----------------------------------------------------------


class PollFormCreation(generic.EntityCreation):
    model = PollForm
    form_class = pf_forms.PollFormForm


class PollFormDetail(generic.EntityDetail):
    model = PollForm
    template_name = 'polls/view_pollform.html'
    pk_url_kwarg = 'pform_id'


class PollFormEdition(generic.EntityEdition):
    model = PollForm
    form_class = pf_forms.PollFormForm
    pk_url_kwarg = 'pform_id'


class _LineCreationBase(generic.AddingInstanceToEntityPopup):
    model = PollFormLine
    form_class = pf_forms.PollFormLineCreateForm
    title_format = _('New question for «{}»')
    entity_classes = PollForm


class _RelatedSectionMixin(EntityRelatedMixin):
    section_id_url_kwarg = 'section_id'
    section_form_kwarg = 'section'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs[self.section_form_kwarg] = self.get_related_section()

        return kwargs

    def get_related_entity_id(self):
        return self.get_related_section().pform_id

    def get_related_section(self):
        try:
            section = getattr(self, 'related_section')
        except AttributeError:
            self.related_section = section = get_object_or_404(
                PollFormSection,
                pk=self.kwargs[self.section_id_url_kwarg],
            )

        return section


class LineCreation(_LineCreationBase):
    entity_id_url_kwarg = 'pform_id'


class AddingLineToSection(_RelatedSectionMixin, _LineCreationBase):
    def get_title(self):
        return self.title_format.format(self.get_related_section())


class _SectionCreationBase(generic.AddingInstanceToEntityPopup):
    model = PollFormSection
    form_class = pf_forms.PollFormSectionCreateForm
    entity_classes = PollForm


class SectionCreation(_SectionCreationBase):
    title_format = _('New section for «{}»')
    entity_id_url_kwarg = 'pform_id'


class ChildSectionCreation(_RelatedSectionMixin, _SectionCreationBase):
    title_format = _('New sub-section for «{}»')
    section_form_kwarg = 'parent'

    def get_title(self):
        return self.title_format.format(self.get_related_section())


class ConditionsEdition(generic.RelatedToEntityFormPopup):
    # model = PollFormLineCondition
    form_class = pf_forms.PollFormLineConditionsForm
    title_format = _('Conditions for «{}»')
    submit_label = _('Save the conditions')
    # entity_id_url_kwarg = 'pform_id'
    entity_classes = PollForm
    line_id_url_kwarg = 'line_id'
    line_form_kwarg = 'line'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs[self.line_form_kwarg] = self.get_related_line()

        return kwargs

    def get_related_entity_id(self):
        return self.get_related_line().pform_id

    def get_related_line(self):
        try:
            line = getattr(self, 'related_line')
        except AttributeError:
            self.related_line = line = get_object_or_404(
                PollFormLine,
                pk=self.kwargs[self.line_id_url_kwarg],
            )

            if line.disabled:
                raise Http404('You can not add condition to a disabled line.')

        return line
