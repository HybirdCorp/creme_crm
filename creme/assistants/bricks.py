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

from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from creme.creme_core.gui.bricks import BrickManager, QuerysetBrick

from . import constants
from .models import Action, Alert, Memo, ToDo, UserMessage


class _AssistantsBrick(QuerysetBrick):
    permissions = 'assistants'

    def _get_queryset_for_detailview(self, entity, context):
        """OVERRIDE ME"""
        pass

    def _get_queryset_for_home(self, context):
        """OVERRIDE ME"""
        pass

    def detailview_display(self, context):
        entity = context['object']
        btc = self.get_template_context(
            context, self._get_queryset_for_detailview(entity, context),
        )

        # NB: optimisation; it avoids the retrieving of the entity during
        #     template rendering.
        for assistant in btc['page'].object_list:
            assistant.real_entity = entity

        return self._render(btc)

    def home_display(self, context):
        return self._render(self.get_template_context(
            context,
            self._get_queryset_for_home(context).prefetch_related('real_entity'),
        ))


class TodosBrick(_AssistantsBrick):
    id = QuerysetBrick.generate_id('assistants', 'todos')
    verbose_name = _('Todos')
    description = _(
        'Allows to add Todos to the current entity, which help you to remind '
        'some things to achieve.\n'
        'Hint #1: Todos can have a deadline; emails are sent to the owners of the '
        'Todos which are not marked as done and near of their deadline (see the '
        'job «Reminders»).\n'
        'Hint #2: if the owner of a Todo is a team, emails are sent to all the '
        'teammates.\n'
        'App: Assistants'
    )
    dependencies = (ToDo,)
    order_by = '-creation_date'
    template_name = 'assistants/bricks/todos.html'
    default_hide_validated = False

    # TODO: factorise (is_ok renamed 'is_validated'?)
    def _improve_queryset(self, qs, context):
        hide_validated = BrickManager.get(context).get_state(
            brick_id=self.id,
            user=context['user'],
        ).get_extra_data(
            constants.BRICK_STATE_HIDE_VALIDATED_TODOS,
            default=self.default_hide_validated,
        )
        context['hide_validated'] = hide_validated

        if hide_validated:
            qs = qs.exclude(is_ok=True)

        return qs.select_related('user')

    def _get_queryset_for_detailview(self, entity, context):
        return self._improve_queryset(
            self.dependencies[0].objects.filter(entity_id=entity.id),
            context=context,
        )

    def _get_queryset_for_home(self, context):
        return self._improve_queryset(
            self.dependencies[0].objects
                                .filter_by_user(context['user'])
                                .filter(entity__is_deleted=False),
            context=context,
        )


class MemosBrick(_AssistantsBrick):
    id = QuerysetBrick.generate_id('assistants', 'memos')
    verbose_name = _('Memos')
    description = _(
        'Allows to add Memos to the current entity, which help you to note '
        'extra-information about it.\n'
        'App: Assistants'
    )
    dependencies = (Memo,)
    order_by = '-creation_date'
    template_name = 'assistants/bricks/memos.html'

    def _get_queryset_for_detailview(self, entity, context):
        return self.dependencies[0].objects.filter(
            entity_id=entity.id,
        ).select_related('user')

    def _get_queryset_for_home(self, context):
        return self.dependencies[0].objects.filter_by_user(
            context['user']
        ).filter(
            on_homepage=True, entity__is_deleted=False,
        ).select_related('user')


class AlertsBrick(_AssistantsBrick):
    id = QuerysetBrick.generate_id('assistants', 'alerts')
    verbose_name = _('Alerts')
    description = _(
        'Allows to add Alerts to the current entity, which help you to remind '
        'some important things to achieve before a trigger date.\n'
        'Emails are sent to the owners of the Alerts which are not marked as validated and '
        'near of their deadline (see the job «Reminders»).\n'
        'Hint: if the owner of an Alert is a team, emails are sent to all the '
        'teammates.\n'
        'App: Assistants'
    )
    dependencies = (Alert,)
    order_by = '-trigger_date'
    template_name = 'assistants/bricks/alerts.html'
    default_hide_validated = True

    def _improve_queryset(self, qs, context):
        hide_validated = BrickManager.get(context).get_state(
            brick_id=self.id,
            user=context['user'],
        ).get_extra_data(
            constants.BRICK_STATE_HIDE_VALIDATED_ALERTS,
            default=self.default_hide_validated,
        )
        context['hide_validated'] = hide_validated

        if hide_validated:
            qs = qs.exclude(is_validated=True)

        return qs.select_related('user')

    def _get_queryset_for_detailview(self, entity, context):
        return self._improve_queryset(
            self.dependencies[0].objects.filter(entity_id=entity.id),
            context=context,
        )

    def _get_queryset_for_home(self, context):
        return self._improve_queryset(
            self.dependencies[0].objects
                                .filter_by_user(context['user'])
                                .filter(entity__is_deleted=False),
            context=context,
        )


# TODO: possibility to show validated ones...
class _ActionsBrick(_AssistantsBrick):
    dependencies = (Action,)
    order_by = 'deadline'

    def _get_queryset_for_detailview(self, entity, context):
        return self.dependencies[0].objects.filter(
            entity_id=entity.id, is_ok=False,
        ).select_related('user')

    def _get_queryset_for_home(self, context):
        return self.dependencies[0].objects.filter_by_user(
            context['user'],
        ).filter(
            is_ok=False, entity__is_deleted=False,
        ).select_related('user')


class ActionsOnTimeBrick(_ActionsBrick):
    id = QuerysetBrick.generate_id('assistants', 'actions_it')
    verbose_name = _('Actions on time')
    description = _(
        'Allows to add Actions to the current entity; Actions expect a re-action '
        'to be done by another user before a given deadline.\n'
        'This block displays Actions which have no re-action yet & with a deadline '
        'which has not been reached.\n'
        'App: Assistants'
    )
    template_name = 'assistants/bricks/actions-on-time.html'

    def _get_queryset_for_detailview(self, entity, context):
        return super()._get_queryset_for_detailview(
            entity, context,
        ).filter(deadline__gt=context['today'])

    def _get_queryset_for_home(self, context):
        return super()._get_queryset_for_home(
            context,
        ).filter(deadline__gt=context['today'])


class ActionsNotOnTimeBrick(_ActionsBrick):
    id = QuerysetBrick.generate_id('assistants', 'actions_nit')
    verbose_name = _('Reactions not on time')
    description = _(
        'Allows to add Actions to the current entity; Actions expect a re-action '
        'to be done by another user before a given deadline.\n'
        'This block displays Actions which have no re-action yet & with a deadline '
        'which has been exceeded.\n'
        'App: Assistants'
    )
    template_name = 'assistants/bricks/actions-not-on-time.html'

    def _get_queryset_for_detailview(self, entity, context):
        return super()._get_queryset_for_detailview(
            entity, context,
        ).filter(deadline__lte=context['today'])

    def _get_queryset_for_home(self, context):
        return super()._get_queryset_for_home(
            context,
        ).filter(deadline__lte=context['today'])


class UserMessagesBrick(_AssistantsBrick):
    id = QuerysetBrick.generate_id('assistants', 'messages')
    verbose_name = _('User messages')
    description = _(
        'Allows to send internal messages to other users, and see the messages '
        'which other users sent to you.\n'
        'App: Assistants'
    )
    dependencies = (UserMessage,)
    order_by = '-creation_date'
    template_name = 'assistants/bricks/messages.html'

    def _get_queryset_for_detailview(self, entity, context):
        return self.dependencies[0].objects.filter(
            entity_id=entity.id, recipient=context['user'],
        ).select_related('sender')

    def _get_queryset_for_home(self, context):
        return self.dependencies[0].objects.filter(
            recipient=context['user'],
        ).filter(
            Q(entity=None) | Q(entity__is_deleted=False),
        ).select_related('sender')
