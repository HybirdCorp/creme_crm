# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required

from creme.creme_core.views.generic import add_to_entity, edit_related_to_entity

from ..models import ToDo
from ..forms.todo import ToDoCreateForm, ToDoEditForm


@login_required
def add(request, entity_id):
    return add_to_entity(request, entity_id, ToDoCreateForm, _(u'New Todo for <%s>'))

@login_required
def edit(request, todo_id):
    return edit_related_to_entity(request, todo_id, ToDo, ToDoEditForm, _(u"Todo for <%s>"))

@login_required
def validate(request, todo_id):
    todo = get_object_or_404(ToDo, pk=todo_id)
    entity = todo.creme_entity

    request.user.has_perm_to_change_or_die(entity)

    todo.is_ok = True
    todo.save()

    return redirect(entity)
