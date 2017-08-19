# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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

import warnings

from django.template import Library, Node as TemplateNode

from creme.creme_core.gui.bricks import BricksManager

from ..registry import config_registry


register = Library()
_USER_SETTINGS_BLOCK = 'user_settings_blocks'


@register.filter(name='is_custom')
def is_custom(obj):
    return getattr(obj, 'is_custom', True)


@register.tag(name='import_usersettings_blocks')
def do_usersettings_blocks_importer(parser, token):
    warnings.warn('{% import_usersettings_blocks %} is deprecated.', DeprecationWarning)

    return UserSettingsBlocksImporterNode()


class UserSettingsBlocksImporterNode(TemplateNode):
    def __init__(self):
        warnings.warn('creme_config_tags.UserSettingsBlocksImporterNode is deprecated.', DeprecationWarning)

    def render(self, context):
        blocks_manager = BricksManager.get(context)
        blocks_manager.add_group(_USER_SETTINGS_BLOCK, *config_registry.userblocks)
        return ''


@register.tag(name='display_usersettings_blocks')
def do_usersettings_blocks_displayer(parser, token):
    warnings.warn('{% do_usersettings_blocks_displayer %} is deprecated.', DeprecationWarning)

    return UserSettingsBlocksDisplayerNode()


class UserSettingsBlocksDisplayerNode(TemplateNode):
    def __init__(self):
        warnings.warn('creme_config_tags.UserSettingsBlocksImporterNode is deprecated.', DeprecationWarning)

    def render(self, context):
        context = context.flatten()
        return ''.join(block.detailview_display(context)
                       for block in BricksManager.get(context).pop_group(_USER_SETTINGS_BLOCK)
                      )
