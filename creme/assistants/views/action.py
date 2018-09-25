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

from django.shortcuts import get_object_or_404, redirect
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.views import generic

from ..forms.action import ActionForm
from ..models import Action


# @login_required
# def add(request, entity_id):
#     return generic.add_to_entity(request, entity_id, ActionForm, _('New action for «%s»'),
#                                  submit_label=_('Save the action'),
#                                 )
class ActionCreation(generic.add.AddingToEntity):
    model = Action
    form_class = ActionForm
    title_format = _('New action for «{}»')


@login_required
def edit(request, action_id):
    return generic.edit_related_to_entity(request, action_id, Action, ActionForm, _('Action for «%s»'))


@login_required
def validate(request, action_id):
    action = get_object_or_404(Action, pk=action_id)
    entity = action.creme_entity

    request.user.has_perm_to_change_or_die(entity)

    action.is_ok = True
    action.validation_date = now()
    action.save()

    return redirect(entity)
