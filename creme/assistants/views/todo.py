# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.db.transaction import atomic
from django.http import Http404
from django.shortcuts import redirect  # get_object_or_404
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.views import generic
from creme.creme_core.views.decorators import POST_only

from ..forms.todo import ToDoForm
from ..models import ToDo


# @login_required
# def add(request, entity_id):
#     return generic.add_to_entity(request, entity_id, ToDoForm, _('New Todo for «%s»'),
#                                  submit_label=_('Save the todo'),
#                                 )
class ToDoCreation(generic.AddingInstanceToEntityPopup):
    model = ToDo
    form_class = ToDoForm
    title_format = _('New todo for «{}»')


# @login_required
# def edit(request, todo_id):
#     return generic.edit_related_to_entity(request, todo_id, ToDo, ToDoForm, _('Todo for «%s»'))
class ToDoEdition(generic.RelatedToEntityEditionPopup):
    model = ToDo
    form_class = ToDoForm
    pk_url_kwarg = 'todo_id'
    title_format = _('Todo for «{}»')


@login_required
@POST_only
@atomic
def validate(request, todo_id):
    # todo = get_object_or_404(ToDo, pk=todo_id)
    try:
        todo = ToDo.objects.select_for_update().get(pk=todo_id)
    except ToDo.DoesNotExist as e:
        raise Http404(str(e)) from e

    entity = todo.creme_entity

    request.user.has_perm_to_change_or_die(entity)

    todo.is_ok = True
    todo.save()

    return redirect(entity)
