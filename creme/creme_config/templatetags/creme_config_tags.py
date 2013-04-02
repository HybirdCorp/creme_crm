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

from django.template import Library, Node as TemplateNode

from creme.creme_core.gui.block import BlocksManager

from ..registry import config_registry
#from creme.creme_config.constants import USER_SETTINGS_BLOCK_PREFIX

register = Library()

_USER_SETTINGS_BLOCK = 'user_settings_blocks'

@register.filter(name="is_custom")
def is_custom(obj):
    return getattr(obj, 'is_custom', True)

@register.tag(name="import_usersettings_blocks")
def do_usersettings_blocks_importer(parser, token):
    return UserSettingsBlocksImporterNode()

class UserSettingsBlocksImporterNode(TemplateNode):
    def render(self, context):
        blocks_manager = BlocksManager.get(context)
        blocks_manager.add_group(_USER_SETTINGS_BLOCK, *config_registry.userblocks)
        return ''


@register.tag(name="display_usersettings_blocks")
def do_usersettings_blocks_displayer(parser, token):
    return UserSettingsBlocksDisplayerNode()

class UserSettingsBlocksDisplayerNode(TemplateNode):
    def render(self, context):
        return ''.join(block.detailview_display(context)
                          for block in BlocksManager.get(context).pop_group(_USER_SETTINGS_BLOCK)
                      )
