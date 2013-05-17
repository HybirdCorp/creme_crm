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

from datetime import datetime

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required

from creme.creme_core.views.generic import add_to_entity, edit_related_to_entity

from ..models import Action
from ..forms.action import ActionCreateForm, ActionEditForm


@login_required
def add(request, entity_id):
    return add_to_entity(request, entity_id, ActionCreateForm, _(u'New action for <%s>'))

@login_required
def edit(request, action_id):
    return edit_related_to_entity(request, action_id, Action, ActionEditForm, _(u"Action for <%s>"))

@login_required
def validate(request, action_id):
    action = get_object_or_404(Action, pk=action_id)
    entity = action.creme_entity

    request.user.has_perm_to_change_or_die(entity)

    action.is_ok = True
    action.validation_date = datetime.today()
    action.save()

    return HttpResponseRedirect(entity.get_absolute_url())
