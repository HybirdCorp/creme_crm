# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from re import compile as compile_re

from django.template import TemplateSyntaxError, Node as TemplateNode
from django.template.loader import get_template
from django.template import Library, Template
from django.utils.translation import ugettext, ungettext
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

from creme_core.models import BlockConfigItem
from creme_core.gui.block import Block, block_registry, BlocksManager
from creme_core.blocks import properties_block, relations_block


register = Library()

@register.inclusion_tag('creme_core/templatetags/widgets/block_header.html', takes_context=True)
def get_block_header(context, singular_title, plural_title, icon='', short_title='', count=None):
    if count is None:
        count = context['page'].paginator.count

    return {
            'title':       ungettext(singular_title, plural_title, count) % count,
            'icon':        icon,
            'short_title': short_title,
            'MEDIA_URL':   settings.MEDIA_URL
           }

@register.inclusion_tag('creme_core/templatetags/widgets/block_header.html')
def get_basic_block_header(title, icon='', short_title=''):
    return {
            'title':       ugettext(title),
            'icon':        icon,
            'short_title': short_title,
            'MEDIA_URL':   settings.MEDIA_URL
           }

#TODO: modify/copy context instead of creating a new dict ??
@register.inclusion_tag('creme_core/templatetags/widgets/block_column_header.html', takes_context=True)
def get_column_header(context, column_name, field_name):
    order_by = context['order_by']

    if order_by.startswith('-'):
        order = order_by[1:]
        asc   = False
    else:
        order = order_by
        asc   = True

    return {
            'object':      context.get('object'), #portal has not object...
            'block_name':  context['block_name'],
            'update_url':  context['update_url'],
            'base_url':    context['base_url'],
            'order':       order,
            'asc':         asc,
            'field_name':  field_name,
            'column_name': column_name,
            'MEDIA_URL':   settings.MEDIA_URL
           }

_line_deletor_re = compile_re(r'at_url (.*?) with_args (.*?)$')

@register.tag(name="get_line_deletor")
def do_line_deletor(parser, token):
    """Eg: {% get_line_deletor at_url '/app/model/delete' with_args "{'id' : {{object.id}} }" %}"""
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]

    match = _line_deletor_re.search(arg)
    if not match:
        raise TemplateSyntaxError, "%r tag had invalid arguments" % tag_name

    groups = match.groups()

    for group in groups:
        first_char = group[0]
        if not (first_char == group[-1] and first_char in ('"', "'")):
            raise TemplateSyntaxError, "%r tag's argument should be in quotes" % tag_name

    delete_url, post_args = groups

    return LineDeletorNode(delete_url[1:-1], post_args[1:-1])

class LineDeletorNode(TemplateNode):
    def __init__(self, delete_url, post_args):
        self.deletor_tpl = get_template('creme_core/templatetags/widgets/block_line_deletor.html')
        self.url_tpl     = Template(delete_url)
        self.args_tpl    = Template(post_args)

    def render(self, context):
        context['delete_url'] = self.url_tpl.render(context)
        context['post_args']  = self.args_tpl.render(context)
        return self.deletor_tpl.render(context)


_block_importer_re = compile_re(r'from_app (.*?) named (.*?) as (.*?)$')

@register.tag(name="import_block")
def do_block_importer(parser, token):
    """Eg: {% import_block from_app 'creme_core' named 'relations' as 'relations_block' %}"""
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]

    match = _block_importer_re.search(arg)
    if not match:
        raise TemplateSyntaxError, "%r tag had invalid arguments" % tag_name

    groups = match.groups()

    if len(groups) != 3:
        raise TemplateSyntaxError, "%r tag's takes 3 arguments" % tag_name

    for group in groups:
        first_char = group[0]
        if not (first_char == group[-1] and first_char in ('"', "'")):
            raise TemplateSyntaxError, "%r tag's argument should be in quotes" % tag_name

    app_name, block_name, alias = groups

    return BlockImporterNode(app_name[1:-1], block_name[1:-1], alias[1:-1])

class BlockImporterNode(TemplateNode):
    def __init__(self, app_name, block_name, alias):
        self.block = block_registry[Block.generate_id(app_name, block_name)]
        self.alias = alias #name of the block in this template

    def render(self, context):
        BlocksManager.get(context).add_group(self.alias, self.block)
        return ''


@register.tag(name="display_block_detailview")
def do_block_detailviewer(parser, token):
    """Eg: {% display_block_detailview 'relations_block' %} %}"""
    try:
        # Splitting by None == splitting by spaces.
        tag_name, block_alias = token.contents.split(None, 1)
    except ValueError:
        raise TemplateSyntaxError, "%r tag requires one argument" % token.contents.split()[0]

    first_char = block_alias[0]
    if not (first_char == block_alias[-1] and first_char in ('"', "'")):
        raise TemplateSyntaxError, "%r tag's argument should be in quotes" % tag_name

    block_alias = block_alias[1:-1]

    if any(not char.isalnum() and char not in ('-', '_') for char in block_alias):
        raise TemplateSyntaxError, "%r tag's argument should be be composed with chars in {[A-Za-z][0-9]-_}" % tag_name

    return BlockDetailviewerNode(block_alias)

class BlockDetailviewerNode(TemplateNode):
    def __init__(self, block_alias):
        self.alias = block_alias #name of the block in this template

    def render(self, context):
        block = BlocksManager.get(context).pop_group(self.alias)[0]

        return block.detailview_display(context)


@register.tag(name="import_detailview_blocks")
def do_detailview_blocks_importer(parser, token):
    return DetailviewBlocksImporterNode()

class DetailviewBlocksImporterNode(TemplateNode):
    def render(self, context):
        blocks_manager = BlocksManager.get(context)

        BCI_filter = BlockConfigItem.objects.filter

        block_ids = BCI_filter(content_type=context['object'].entity_type).order_by('order').values_list('block_id', flat=True)

        if not block_ids:
            block_ids = BCI_filter(content_type=None).order_by('order').values_list('block_id', flat=True)

        get_block = block_registry.get_block
        blocks    = [get_block(id_) for id_ in block_ids if id_]

        blocks_manager.add_group('detailview_blocks', *blocks) #TODO: use CONSTANT

        return ''


@register.tag(name="display_detailview_blocks")
def do_detailview_blocks_displayer(parser, token):
    return DetailviewBlocksDisplayerNode()

class DetailviewBlocksDisplayerNode(TemplateNode):
    def render(self, context):
        blocks = BlocksManager.get(context).pop_group('detailview_blocks')

        return ''.join(block.detailview_display(context) for block in blocks)


def _parse_one_var_tag(token): #TODO: move in creme_core.utils
    try:
        # Splitting by None == splitting by spaces.
        tag_name, var_name = token.contents.split(None, 1)
    except ValueError:
        raise TemplateSyntaxError, "%r tag requires one argument" % token.contents.split()[0]

    if any(not char.isalnum() and char not in ('-', '_') for char in var_name):
        raise TemplateSyntaxError, "%r tag's argument should be composed with chars in {[A-Za-z][0-9]-_}" % tag_name

    return var_name

@register.tag(name="import_portal_blocks")
def do_portal_blocks_importer(parser, token):
    """Eg: {% import_portal_blocks ct_ids %}"""
    return PortalBlocksImporterNode(_parse_one_var_tag(token))

class PortalBlocksImporterNode(TemplateNode):
    def __init__(self, ct_ids_varname):
        self.ct_ids_varname = ct_ids_varname

    def render(self, context):
        blocks_manager = BlocksManager.get(context)
        ct_ids = context[self.ct_ids_varname]

        #blocks from all ct are merged (merge algo is quite stupid but it is satisfactory)
        BCI_filter    = BlockConfigItem.objects.filter
        block_ids     = []
        block_ids_set = set() #ordered set would be cool....

        for ct_id in ct_ids:
            ct_id_filter = ct_id if BCI_filter(content_type__id=ct_id)[:1] else None  #TODO: use exists() in django 1.2
            ct_block_ids = BCI_filter(content_type__id=ct_id_filter, on_portal=True).order_by('order').values_list('block_id', flat=True)

            for block_id in ct_block_ids:
                if block_id not in block_ids_set:
                    block_ids_set.add(block_id)
                    block_ids.append(block_id)

        get_block = block_registry.get_block
        blocks = [get_block(id_) for id_ in block_ids]

        blocks_manager.add_group('portal_blocks', *blocks) #TODO: use CONSTANT

        return ''

@register.tag(name="display_portal_blocks")
def do_detailview_blocks_displayer(parser, token):
    """Eg: {% display_portal_blocks ct_ids %}"""
    return PortalBlocksDisplayerNode(_parse_one_var_tag(token))

class PortalBlocksDisplayerNode(TemplateNode):
    def __init__(self, ct_ids_varname):
        self.ct_ids_varname = ct_ids_varname

    def render(self, context):
        blocks = BlocksManager.get(context).pop_group('portal_blocks')
        ct_ids = context[self.ct_ids_varname]

        blocks_output = []
        for block in blocks:
            portal_display = getattr(block, 'portal_display', None)

            if portal_display is not None:
                blocks_output.append(portal_display(context, ct_ids))
            else:
                blocks_output.append("THIS BLOCK CAN'T BE DISPLAY ON PORTAL (YOU HAVE A CONFIG PROBLEM): %s" % block.id_)

        return ''.join(blocks_output)


@register.tag(name="import_home_blocks")
def do_home_blocks_importer(parser, token):
    return HomeBlocksImporterNode()

class HomeBlocksImporterNode(TemplateNode):
    def render(self, context):
        blocks_manager = BlocksManager.get(context)

        block_ids = BlockConfigItem.objects.filter(content_type=None, on_portal=True).order_by('order').values_list('block_id', flat=True)
        get_block = block_registry.get_block
        blocks    = [get_block(id_) for id_ in block_ids if id_]

        blocks_manager.add_group('home_blocks', *blocks) #TODO: use CONSTANT

        return ''


@register.tag(name="display_home_blocks")
def do_home_blocks_displayer(parser, token):
    return HomeBlocksDisplayerNode()

class HomeBlocksDisplayerNode(TemplateNode):
    def render(self, context):
        blocks = BlocksManager.get(context).pop_group('home_blocks') #TODO: use CONSTANT

        blocks_output = []
        for block in blocks:
            home_display = getattr(block, 'home_display', None)

            if home_display is not None:
                blocks_output.append(home_display(context))
            else:
                blocks_output.append("THIS BLOCK CAN'T BE DISPLAY ON HOME (YOU HAVE A CONFIG PROBLEM): %s" % block.id_)

        return ''.join(blocks_output)


@register.inclusion_tag('creme_core/templatetags/blocks_dependencies.html', takes_context=True)
def get_blocks_dependencies(context):
    blocks_manager = BlocksManager.get(context)

    return {
            'deps_map':         blocks_manager.get_dependencies_map(),
            'remaining_groups': blocks_manager.get_remaining_groups(),
           }
