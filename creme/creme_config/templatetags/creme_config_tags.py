# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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


@register.filter(name='config_is_custom')
def is_custom(obj):
    return getattr(obj, 'is_custom', True)


@register.simple_tag
def config_model_creation_url(*, model_config, user):
    return model_config.creator.get_url(user=user)


@register.simple_tag
def config_model_edition_url(*, model_config, instance, user):
    return model_config.editor.get_url(instance=instance, user=user)


@register.simple_tag
def config_model_deletion_url(*, model_config, instance, user):
    return model_config.deletor.get_url(instance=instance, user=user)


@register.inclusion_tag('creme_core/templatetags/bricks/menu-action.html', takes_context=True)
def config_brick_menu_hide_inactive_users_action(context, url, hidden):
    return _brick_menu_state_action(
        context,
        url=url,
        action_id='update',
        current_state=not hidden,
        in_label=_('Hide inactive users'),
        out_label=_('Show inactive users'),
        __value='false' if hidden else 'true',
    )


# TODO: factorise
@register.inclusion_tag('creme_core/templatetags/bricks/menu-action.html', takes_context=True)
def config_brick_menu_hide_deleted_cfields_action(context, url, hidden):
    return _brick_menu_state_action(
        context,
        url=url,
        action_id='update',
        current_state=not hidden,
        in_label=_('Hide deleted custom fields'),
        out_label=_('Show deleted custom fields'),
        __value='false' if hidden else 'true',
    )


@register.inclusion_tag('creme_config/templatetags/buttons_placeholders.html')
def config_render_buttons_placeholders(buttons, empty_label):
    return {'buttons': buttons, 'empty_label': empty_label}
