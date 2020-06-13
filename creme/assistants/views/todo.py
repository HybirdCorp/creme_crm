# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

# from django.http import Http404
from django import shortcuts
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from creme.creme_core.auth.decorators import login_required
# from creme.creme_core.views.decorators import POST_only
from creme.creme_core.views import generic

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
    title = _('New todo for «{entity}»')


# @login_required
# def edit(request, todo_id):
#     return generic.edit_related_to_entity(request, todo_id, ToDo, ToDoForm, _('Todo for «%s»'))
class ToDoEdition(generic.RelatedToEntityEditionPopup):
    model = ToDo
    form_class = ToDoForm
    pk_url_kwarg = 'todo_id'
    title = _('Todo for «{entity}»')


@login_required
# @POST_only
@require_POST
@atomic
def validate(request, todo_id):
    # try:
    #     todo = ToDo.objects.select_for_update().get(pk=todo_id)
    # except ToDo.DoesNotExist as e:
    #     raise Http404(str(e)) from e
    todo = shortcuts.get_object_or_404(
        ToDo.objects.select_for_update(),
        pk=todo_id,
    )

    entity = todo.creme_entity

    request.user.has_perm_to_change_or_die(entity)

    todo.is_ok = True
    todo.save()

    return shortcuts.redirect(entity)
