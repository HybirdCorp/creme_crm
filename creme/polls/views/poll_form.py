# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2013  Hybird
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

from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.translation import ugettext as _
#from django.utils.encoding import smart_unicode
from django.contrib.auth.decorators import login_required, permission_required

from creme.creme_core.views.generic import add_entity, add_to_entity, edit_entity, edit_related_to_entity, view_entity, list_view
from creme.creme_core.utils import jsonify

from ..models import PollForm, PollFormSection, PollFormLine
from ..forms.poll_form import (PollFormForm, PollFormLineCreateForm, PollFormLineEditForm,
                               PollFormSectionCreateForm, PollFormSectionEditForm,
                               PollFormLineConditionsForm)
from ..utils import StatsTree, NodeStyle #TODO: templatetag instead ?


@login_required
@permission_required('polls')
@permission_required('polls.add_pollform')
def add(request):
    return add_entity(request, PollFormForm)

@login_required
@permission_required('polls')
def edit(request, pform_id):
    return edit_entity(request, pform_id, PollForm, PollFormForm)

@login_required
@permission_required('polls')
def detailview(request, pform_id):
    return view_entity(request, pform_id, PollForm,
                       '/polls/poll_form', 'polls/view_pollform.html'
                      )

@login_required
@permission_required('polls')
def listview(request):
    return list_view(request, PollForm, extra_dict={'add_url': '/polls/poll_form/add'})

@login_required
@permission_required('polls')
def add_line(request, pform_id):
    return add_to_entity(request, pform_id, PollFormLineCreateForm, _(u'New question for <%s>'))

@login_required
@permission_required('polls')
def edit_line(request, line_id):
    return edit_related_to_entity(request, line_id, PollFormLine,
                                  PollFormLineEditForm, _(u'Question for <%s>')
                                 )

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
        raise PermissionDenied(e.args[0])

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return redirect(pform)

@login_required
@permission_required('polls')
def edit_line_conditions(request, line_id):
    line = get_object_or_404(PollFormLine, pk=line_id)

    if line.disabled:
        raise Http404('You can not add condition to a disabled line.')

    return add_to_entity(request, line.pform_id, PollFormLineConditionsForm,
                         _(u'Condition for <%s>'), entity_class=PollForm,
                         initial={'line': line}
                        )

@login_required
@permission_required('polls')
def add_section(request, pform_id):
    return add_to_entity(request, pform_id, PollFormSectionCreateForm, _(u'New section for <%s>'))

@login_required
@permission_required('polls')
def edit_section(request, section_id):
    return edit_related_to_entity(request, section_id, PollFormSection,
                                  PollFormSectionEditForm, _(u'Section for <%s>')
                                 )

@login_required
@permission_required('polls')
def add_section_child(request, section_id):
    parent_section = get_object_or_404(PollFormSection, pk=section_id)

    return add_to_entity(request, parent_section.pform_id, PollFormSectionCreateForm,
                         _(u'New section for <%s>'), entity_class=PollForm,
                         initial={'parent': parent_section}
                        )

@login_required
@permission_required('polls')
def add_line_to_section(request, section_id):
    section = get_object_or_404(PollFormSection, pk=section_id)

    return add_to_entity(request, section.pform_id, PollFormLineCreateForm,
                         _(u'New question for <%s>'), entity_class=PollForm,
                         initial={'section': section}
                        )

@login_required
@permission_required('polls')
def stats(request, pform_id):
    pform = get_object_or_404(PollForm, pk=pform_id)

    return render(request, 'polls/stats.html',
                  {'nodes': StatsTree(pform),
                   'style': NodeStyle(),
                  }
                 )

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
