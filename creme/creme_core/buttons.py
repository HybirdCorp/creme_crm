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

from django.utils.translation import gettext_lazy as _

from .constants import UUID_SANDBOX_SUPERUSERS
from .gui.button_menu import Button


class Restrict2SuperusersButton(Button):
    # id_ = Button.generate_id('creme_core', 'restrict_2_superusers')
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
    template_name = 'creme_core/buttons/restrict-to-superusers.html'

    def render(self, context):
        sandbox = context['object'].sandbox
        context['sandbox_uuid'] = str(sandbox.uuid) if sandbox else None
        context['UUID_SANDBOX_SUPERUSERS'] = UUID_SANDBOX_SUPERUSERS

        return super().render(context)


class ActionButton(Button):
    template_name = 'creme_core/buttons/action.html'

    action = ''
    action_url = ''
    action_data = {}
    action_options = {}

    icon = 'view'
    icon_title = None
    classes = ()

    def eval_is_enabled(self, context) -> bool:
        return self.has_perm(context)

    def eval_action_context(self, context) -> dict:
        return {
            'data': context['action_data'],
            'options': context['action_options']
        }


class ViewButton(ActionButton):
    action = 'creme_core-hatmenubar-view'

    def eval_action_data(self):
        return {
            'title': self.verbose_name
        }


class FormButton(ActionButton):
    action = 'creme_core-hatmenubar-form'
    redirect = True

    def extra_submit_data(self, context):
        return {}

    def eval_action_data(self, context):
        return {
            'title': self.verbose_name
        }

    def eval_action_options(self, context):
        return {
            'redirectOnSuccess': self.redirect,
            'submitData': self.extra_submit_data(context)
        }


class UpdateButton(ActionButton):
    action = 'creme_core-hatmenubar-update'
    method = 'POST'
    confirm = False
    success_message = ''
    show_error_message = True
    reload_on_error = True
    reload_on_success = True

    def eval_action_options(self, context):
        return {
            'confirm': self.confirm,
            'action': self.method,
            'warnOnFail': self.show_error_message,
            'warnOnFailTitle': self.verbose_name,
            'messageOnSuccess': self.success_message,
            'reloadOnFail': self.reload_on_error,
            'reloadOnSuccess': self.reload_on_success,
        }
