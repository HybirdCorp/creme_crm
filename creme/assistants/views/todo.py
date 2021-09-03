# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from django.db import IntegrityError
from django.db.transaction import atomic
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from creme.creme_core import utils
from creme.creme_core.auth.decorators import login_required
from creme.creme_core.models import BrickState
from creme.creme_core.views import generic

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

    entity = todo.creme_entity

    request.user.has_perm_to_change_or_die(entity)

    todo.is_ok = True
    todo.save()

    return shortcuts.redirect(entity)


class HideValidatedToDos(generic.CheckedView):
    value_arg = 'value'
    brick_cls = TodosBrick

    def post(self, request, **kwargs):
        value = utils.get_from_POST_or_404(
            request.POST,
            key=self.value_arg,
            cast=utils.bool_from_str_extended,
        )

        # NB: we can still have a race condition because we do not use
        #     select_for_update ; but it's a state related to one user & one brick,
        #     so it would not be a real world problem.
        for _i in range(10):
            state = BrickState.objects.get_for_brick_id(
                brick_id=self.brick_cls.id_, user=request.user,
            )

            try:
                if state.set_extra_data(key=BRICK_STATE_HIDE_VALIDATED_TODOS, value=value):
                    state.save()
            except IntegrityError:
                # logger.exception('Avoid a duplicate.')  TODO
                continue
            else:
                break

        return HttpResponse()
