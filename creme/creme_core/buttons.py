################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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

from typing import Dict, Sequence
from django.utils.translation import gettext_lazy as _

from creme.creme_core.gui.icons import BaseIcon, get_icon_by_name, get_icon_size_px

from .constants import UUID_SANDBOX_SUPERUSERS
from .gui.button_menu import Button


class Restrict2SuperusersButton(Button):
    id = Button.generate_id('creme_core', 'restrict_2_superusers')
    verbose_name = _('Restrict to superusers')
    description = _(
        'This button moves the current entity within a sandbox reserved to the '
        'superusers, so the regular users cannot see it. If the current is '
        'already restricted to superusers, the button can be used to move the '
        'entity out of the sandbox.\n'
        'The button is only viewable by superusers.\n'
        'App: Core'
    )
    dependencies = (Button.CURRENT,)
    template_name = 'creme_core/buttons/restrict-to-superusers.html'

    def get_context(self, *, entity, request):
        context = super().get_context(entity=entity, request=request)
        sandbox = entity.sandbox
        context['sandbox_uuid'] = str(sandbox.uuid) if sandbox else None
        context['UUID_SANDBOX_SUPERUSERS'] = UUID_SANDBOX_SUPERUSERS

        return context


class ActionButtonContext(dict):
    def __init__(self, button: Button, context: dict):
        self.button = button
        self.context = context

    def __getitem__(self, key):
        try:
            prop = getattr(self.button, f'get_action_{key}')
            return prop(self)
        except AttributeError:
            try:
                return getattr(self.button, f'action_{key}')
            except AttributeError:
                return self.context[key]


class ActionButton(Button):
    template_name = 'creme_core/buttons/action.html'

    action_id: str = 'redirect'
    action_url: str = ''

    action_icon_name: str = 'view'
    action_icon_title: str = None
    action_classes: Sequence[str] = ()

    action_context_class: ActionButtonContext = ActionButtonContext

    def get_context(self, *, entity, request):
        context = super().get_context(entity=entity, request=request)
        context['action'] = self.action_context_class(self, context)
        return context

    def get_action_icon(self, context) -> BaseIcon:
        theme = context['request'].user.theme_info[0]
        return get_icon_by_name(
            name=self.action_icon_name, label=self.action_icon_title, theme=theme,
            size_px=get_icon_size_px(theme=theme, size='instance-button'),
        )

    def get_action_props(self, context):
        return {
            "data": context.get('data', {}),
            "options": context.get('options', {})
        }


class ViewButton(ActionButton):
    action_id = 'creme_core-hatmenubar-view'

    def get_action_data(self):
        return {
            'title': self.verbose_name
        }


class FormButton(ActionButton):
    action_id = 'creme_core-hatmenubar-form'
    redirect = True

    def extra_submit_data(self, context):
        return {}

    def get_action_data(self, context):
        return {
            'title': self.verbose_name
        }

    def get_action_options(self, context):
        return {
            'redirectOnSuccess': self.redirect,
            'submitData': self.extra_submit_data(context)
        }


class UpdateButton(ActionButton):
    action_id = 'creme_core-hatmenubar-update'
    method = 'POST'
    confirm = False
    success_message = ''
    show_error_message = True
    reload_on_error = True
    reload_on_success = True

    def get_action_options(self, context):
        return {
            'confirm': self.confirm,
            'action': self.method,
            'warnOnFail': self.show_error_message,
            'warnOnFailTitle': self.verbose_name,
            'messageOnSuccess': self.success_message,
            'reloadOnFail': self.reload_on_error,
            'reloadOnSuccess': self.reload_on_success,
        }
