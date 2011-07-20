# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.template import Library, Node as TemplateNode

#from creme_core.models import BlockConfigItem
from creme_core.gui.block import  block_registry, BlocksManager

from creme_config.constants import USER_SETTINGS_BLOCK_PREFIX

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
        #TODO: use a registry
        #bc_items = BlockConfigItem.objects.filter(Q(content_type=ContentType.objects.get_for_model(User)) & Q(id__startswith=USER_SETTINGS_BLOCK_PREFIX)) \
                                          #.order_by('order')
        #blocks_manager.add_group(_USER_SETTINGS_BLOCK , *block_registry.get_blocks([bc_item.block_id for bc_item in bc_items if bc_item.block_id]))
        return ''

@register.tag(name="display_usersettings_blocks")
def do_usersettings_blocks_displayer(parser, token):
    return UserSettingsBlocksDisplayerNode()

class UserSettingsBlocksDisplayerNode(TemplateNode):
    def block_outputs(self, context):
        for block in BlocksManager.get(context).pop_group(_USER_SETTINGS_BLOCK ):
             yield block.detailview_display(context)

    def render(self, context):
        return ''.join(op for op in self.block_outputs(context)) #TODO: use a generator expression
