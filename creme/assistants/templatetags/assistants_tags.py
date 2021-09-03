# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021  Hybird
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

from django.template import Library
from django.utils.translation import gettext_lazy as _

# TODO: make public ?
from creme.creme_core.templatetags.creme_bricks import _brick_menu_state_action

register = Library()


def _assistants_brick_menu_hide_action(context, *, url, hidden, in_label, out_label):
    return _brick_menu_state_action(
        context,
        url=url,
        action_id='update',
        current_state=not hidden,
        in_label=in_label,
        out_label=out_label,
        __value='false' if hidden else 'true',
    )


@register.inclusion_tag('creme_core/templatetags/bricks/menu-action.html', takes_context=True)
def assistants_brick_menu_hide_validated_alerts_action(context, url, hidden):
    # return _brick_menu_state_action(
    #     context,
    #     url=url,
    #     action_id='update',
    #     current_state=not hidden,
    #     in_label=_('Hide validated alerts'),
    #     out_label=_('Show validated alerts'),
    #     __value='false' if hidden else 'true',
    # )
    return _assistants_brick_menu_hide_action(
        context,
        url=url,
        hidden=hidden,
        in_label=_('Hide validated alerts'),
        out_label=_('Show validated alerts'),
    )


@register.inclusion_tag('creme_core/templatetags/bricks/menu-action.html', takes_context=True)
def assistants_brick_menu_hide_validated_todos_action(context, url, hidden):
    # return _brick_menu_state_action(
    #     context,
    #     url=url,
    #     action_id='update',
    #     current_state=not hidden,
    #     in_label=_('Hide validated todos'),
    #     out_label=_('Show validated todos'),
    #     __value='false' if hidden else 'true',
    # )
    return _assistants_brick_menu_hide_action(
        context,
        url=url,
        hidden=hidden,
        in_label=_('Hide validated todos'),
        out_label=_('Show validated todos'),
    )
