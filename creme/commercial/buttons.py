################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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
from creme.creme_core.models import RelationType

from . import get_act_model
from .constants import REL_SUB_COMPLETE_GOAL


class CompleteGoalButton(Button):
    # id_ = Button.generate_id('commercial', 'complete_goal')
    id = Button.generate_id('commercial', 'complete_goal')
    verbose_name = _('Completes a goal (Commercial action)')
    description = _(
        'This button links the current entity with a selected commercial action, '
        'using the relationship type «completes a goal of the commercial action».\n'
        'App: Commercial'
    )
    permissions = 'commercial'

    action = 'creme_core-hatmenubar-addrelationships'
    icon = 'commercial'
    icon_title = _('Commercial Action')

    def eval_is_enabled(self, context) -> bool:
        return context['has_perm'] and context['can_link']

    def eval_description(self, context):
        rtype = RelationType.objects.get(id=REL_SUB_COMPLETE_GOAL)

        if not context['has_perm']:
            return _('You are not allowed to access to the app «Commercial strategy»')
        elif not context['can_link']:
            return _('You are not allowed to link this entity')
        elif not rtype.enabled:
            return _('The relationship type «{predicate}» is disabled').format(
                predicate=rtype.predicate
            )
        else:
            return self.description

    def eval_action_data(self, context):
        return {
            "subject_id": context['object'].id,
            "rtype_id": REL_SUB_COMPLETE_GOAL,
            "ctype_id": ContentType.objects.get_for_model(get_act_model())
        }
