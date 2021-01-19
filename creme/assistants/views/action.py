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
from django.db.transaction import atomic
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.views import generic

from ..forms.action import ActionForm
from ..models import Action


class ActionCreation(generic.AddingInstanceToEntityPopup):
    model = Action
    form_class = ActionForm
    title = _('New action for «{entity}»')


class ActionEdition(generic.RelatedToEntityEditionPopup):
    model = Action
    form_class = ActionForm
    pk_url_kwarg = 'action_id'
    title = _('Action for «{entity}»')


@login_required
@require_POST
@atomic
def validate(request, action_id):
    action = shortcuts.get_object_or_404(
        Action.objects.select_for_update(),
        pk=action_id,
    )

    entity = action.creme_entity
    request.user.has_perm_to_change_or_die(entity)

    action.is_ok = True
    action.validation_date = now()
    action.save()

    return shortcuts.redirect(entity)
