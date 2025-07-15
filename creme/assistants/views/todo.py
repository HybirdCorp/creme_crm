################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from django import shortcuts
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.views import generic
from creme.creme_core.views.bricks import BrickStateExtraDataSetting

from ..bricks import TodosBrick
from ..constants import BRICK_STATE_HIDE_VALIDATED_TODOS
from ..forms.todo import ToDoForm
from ..models import ToDo


class ToDoCreation(generic.AddingInstanceToEntityPopup):
    model = ToDo
    form_class = ToDoForm
    title = _('New todo for «{entity}»')


class ToDoEdition(generic.RelatedToEntityEditionPopup):
    model = ToDo
    form_class = ToDoForm
    pk_url_kwarg = 'todo_id'
    title = _('Todo for «{entity}»')


@login_required
@require_POST
@atomic
def validate(request, todo_id):
    todo = shortcuts.get_object_or_404(
        ToDo.objects.select_for_update(),
        pk=todo_id,
    )

    entity = todo.real_entity

    user = request.user
    user.has_perm_to_access_or_die('assistants')
    user.has_perm_to_change_or_die(entity)

    todo.is_ok = True
    todo.save()

    return shortcuts.redirect(entity)


class HideValidatedToDos(BrickStateExtraDataSetting):
    brick_cls = TodosBrick
    data_key = BRICK_STATE_HIDE_VALIDATED_TODOS
