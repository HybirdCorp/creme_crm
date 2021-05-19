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

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from creme.creme_core.gui.button_menu import Button

from . import get_act_model
from .constants import REL_SUB_COMPLETE_GOAL


class CompleteGoalButton(Button):
    id_ = Button.generate_id('commercial', 'complete_goal')
    verbose_name = _('Completes a goal (Commercial action)')
    description = _(
        'This button links the current entity with a selected commercial action, '
        'using the relationship type «completes a goal of the commercial action».\n'
        'App: Commercial'
    )
    template_name = 'commercial/buttons/complete-goal.html'
    # permission = 'commercial'
    permissions = 'commercial'

    def render(self, context):
        context['predicate_id'] = REL_SUB_COMPLETE_GOAL
        context['act_ct'] = ContentType.objects.get_for_model(get_act_model())

        return super().render(context)
