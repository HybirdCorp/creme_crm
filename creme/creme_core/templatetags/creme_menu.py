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

from collections import OrderedDict

from django.db.models import Q
from django.template import Library

from ..gui import button_menu
# from ..gui.menu import creme_menu
from ..gui.menu import menu_registry
from ..models import ButtonMenuItem, MenuConfigItem

register = Library()


# @register.simple_tag(takes_context=True)
# def menu_display(context):
#     return creme_menu.render(context)
@register.inclusion_tag('creme_core/templatetags/menu.html', takes_context=True)
def menu_display(context):
    context['entries'] = [
        (entry, entry.render(context))
        for entry in menu_registry.get_entries(MenuConfigItem.objects.all())
    ]

    return context


# TODO: rename template file (menu-buttons.html ? detailview-buttons.html ? menu/buttons.html ?)
@register.inclusion_tag(
    'creme_core/templatetags/menu_buttons.html', takes_context=True,
)
def menu_buttons_display(context):
    entity = context['object']
    bmi = ButtonMenuItem.objects.filter(
        Q(content_type=entity.entity_type)
        | Q(content_type__isnull=True)
    ).exclude(
        button_id='',
    ).order_by(
        'order',
    ).values_list(
        'button_id', flat=True,
    )

    button_ctxt = context.flatten()
    # TODO: pass the registry in the context ?
    buttons = OrderedDict()

    for button in button_menu.button_registry.get_buttons(bmi, entity):
        buttons[button.id_] = button.render(button_ctxt)

    context['buttons'] = [*buttons.values()]

    return context
