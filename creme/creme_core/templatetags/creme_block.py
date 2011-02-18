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

from re import compile as compile_re

from django.db.models import Q
from django.template import TemplateSyntaxError, Node as TemplateNode
from django.template.defaulttags import TemplateLiteral
from django.template.loader import get_template
from django.template import Library, Template
from django.utils.translation import ugettext, ungettext
from django.contrib.contenttypes.models import ContentType

from creme_core.models import BlockConfigItem
from creme_core.gui.block import Block, block_registry, BlocksManager
from creme_core.blocks import properties_block, relations_block


register = Library()


#-------------------------------------------------------------------------------
_COLSPAN_ARG = 'colspan='

@register.tag(name="get_block_header")
def do_block_header(parser, token):
    """Eg:{% get_block_header colspan=8 %}
            <th style="width: 80%;" class="collapser">My title</th>
          {% end_get_block_header %}
    """
    try:
        tag_name, arg = token.contents.split(None, 1) # Splitting by None == splitting by spaces.
    except ValueError:
        raise TemplateSyntaxError("%r tag requires arguments" % token.contents.split()[0])

    if not arg.startswith(_COLSPAN_ARG):
        raise TemplateSyntaxError("%r tag argument is on the model: %s12" % (tag_name, _COLSPAN_ARG))

    try:
        colspan = int(arg[len(_COLSPAN_ARG):])
    except Exception, e:
        raise TemplateSyntaxError(str(e))

    nodelist = parser.parse(('end_get_block_header',))
    parser.delete_first_token()

    return HeaderNode(nodelist, colspan)

class HeaderNode(TemplateNode):
    def __init__(self, nodelist, colspan):
        self.header_tpl = get_template('creme_core/templatetags/widgets/block_header.html')
        self.nodelist = nodelist
        self.colspan  = colspan

    def render(self, context):
        context['content'] = self.nodelist.render(context)
        context['colspan'] = self.colspan

        return self.header_tpl.render(context)

#-------------------------------------------------------------------------------

@register.inclusion_tag('creme_core/templatetags/widgets/block_reload_uri.html', takes_context=True)
def get_block_reload_uri(context): #{% include 'creme_core/templatetags/widgets/block_reload_uri.html' %} instead ??
    return context

@register.inclusion_tag('creme_core/templatetags/widgets/block_title.html', takes_context=True)
def get_block_title(context, singular_title, plural_title, icon='', short_title='', count=None):
    if count is None:
        count = context['page'].paginator.count

    context.update({
            'title':       ungettext(singular_title, plural_title, count) % count,
            'icon':        icon,
            'short_title': short_title,
           })

    return context

@register.inclusion_tag('creme_core/templatetags/widgets/block_title.html', takes_context=True)
def get_basic_block_header(context, title, icon='', short_title=''):
    context.update({
            'title':       ugettext(title),
            'icon':        icon,
            'short_title': short_title,
           })

    return context


@register.inclusion_tag('creme_core/templatetags/widgets/block_column_header.html', takes_context=True)
def get_column_header(context, column_name, field_name):
    order_by = context['order_by']

    if order_by.startswith('-'):
        order = order_by[1:]
        asc   = False
    else:
        order = order_by
        asc   = True

    context.update({
            'order':       order,
            'asc':         asc,
            'field_name':  field_name,
            'column_name': column_name,
           })

    return context


#-------------------------------------------------------------------------------
_line_adder_re = compile_re(r'at_url (.*?) with_label (.*?) with_perms (.*?)$')

@register.tag(name="get_line_adder")
def do_line_adder(parser, token):
    """Eg: {% get_line_adder at_url '/assistants/action/add/{{object.id}}/' with_label _("New action") with_perms has_perm %}"""
    try:
        tag_name, arg = token.contents.split(None, 1) # Splitting by None == splitting by spaces.
    except ValueError:
        raise TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]

    match = _line_adder_re.search(arg)
    if not match:
        raise TemplateSyntaxError, "%r tag had invalid arguments" % tag_name

    add_url, label_str, perm_str = match.groups()

    first_char = add_url[0]
    if not (first_char == add_url[-1] and first_char in ('"', "'")):
        raise TemplateSyntaxError, "%r tag's url argument should be in quotes" % tag_name

    compile_filter = parser.compile_filter
    return LineAdderNode(add_url[1:-1],
                         TemplateLiteral(compile_filter(label_str), label_str),
                         TemplateLiteral(compile_filter(perm_str), perm_str),
                        )

class LineAdderNode(TemplateNode):
    def __init__(self, add_url,  label_var, perm_var):
        self.adder_tpl = get_template('creme_core/templatetags/widgets/block_line_adder.html')
        self.url_tpl   = Template(add_url)
        self.perm_var = perm_var
        self.label_var = label_var

    def render(self, context):
        context['add_url'] = self.url_tpl.render(context)
        context['label'] = self.label_var.eval(context)
        context['add_line_perm'] = self.perm_var.eval(context)

        return self.adder_tpl.render(context)

#-------------------------------------------------------------------------------
_line_deletor_re = compile_re(r'at_url (.*?) with_args (.*?)$')

@register.tag(name="get_line_deletor") #TODO: deprecated (use get_line_deletor2 that manages credentials)
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


_line_suppr_re = compile_re(r'at_url (.*?) with_args (.*?) with_perms (.*?)$')

def _do_line_suppr(parser, token, template_path):
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]

    match = _line_suppr_re.search(arg)
    if not match:
        raise TemplateSyntaxError, "%r tag had invalid arguments" % tag_name

    suppr_url, post_args, perm_str = match.groups()

    for group in (suppr_url, post_args):
        first_char = group[0]
        if not (first_char == group[-1] and first_char in ('"', "'")):
            raise TemplateSyntaxError, "%r tag's argument should be in quotes" % tag_name

    return LineSuppressorNode(url=suppr_url[1:-1], post_args=post_args[1:-1],
                              perm_var=TemplateLiteral(parser.compile_filter(perm_str), perm_str),
                              template_path=template_path
                             )

class LineSuppressorNode(TemplateNode):
    def __init__(self, url, post_args, perm_var, template_path):
        self.template = get_template(template_path)
        self.url_tpl  = Template(url)
        self.args_tpl = Template(post_args)
        self.perm_var = perm_var

    def render(self, context):
        context['action_url'] = self.url_tpl.render(context)
        context['post_args']  = self.args_tpl.render(context)
        context['line_perm']  = self.perm_var.eval(context)

        return self.template.render(context)

@register.tag(name="get_line_deletor2")
def do_line_deletor2(parser, token):
    """Eg: {% get_line_deletor2 at_url '/app/model/delete' with_args "{'id' : {{object.id}} }" with_perms boolean_variable %}"""
    return _do_line_suppr(parser, token, 'creme_core/templatetags/widgets/block_line_deletor2.html')

@register.tag(name="get_line_unlinker")
def do_line_unlinker(parser, token):
    """Eg: {% get_line_unlinker at_url '/app/model/unlink' with_args "{'id' : {{object.id}} }" with_perms boolean_variable %}"""
    return _do_line_suppr(parser, token, 'creme_core/templatetags/widgets/block_line_unlinker.html')

#-------------------------------------------------------------------------------
_line_editor_re = compile_re(r'at_url (.*?) with_perms (.*?)$')

@register.tag(name="get_line_editor")
def do_line_editor(parser, token):
    """Eg: {% get_line_editor at_url '/assistants/action/edit/{{action.id}}/' with_perms has_perm %}"""
    try:
        tag_name, arg = token.contents.split(None, 1) # Splitting by None == splitting by spaces.
    except ValueError:
        raise TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]

    match = _line_editor_re.search(arg)
    if not match:
        raise TemplateSyntaxError, "%r tag had invalid arguments" % tag_name

    edit_url, perm_str = match.groups()

    first_char = edit_url[0]
    if not (first_char == edit_url[-1] and first_char in ('"', "'")):
        raise TemplateSyntaxError, "%r tag's url argument should be in quotes" % tag_name

    return LineEditorNode(edit_url[1:-1], TemplateLiteral(parser.compile_filter(perm_str), perm_str))

class LineEditorNode(TemplateNode):
    def __init__(self, edit_url, perm_var):
        self.editor_tpl = get_template('creme_core/templatetags/widgets/block_line_editor.html')
        self.url_tpl = Template(edit_url)
        self.perm_var = perm_var

    def render(self, context):
        context['edit_url'] = self.url_tpl.render(context)
        context['edit_line_perm'] = self.perm_var.eval(context)

        return self.editor_tpl.render(context)


#-------------------------------------------------------------------------------
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


#-------------------------------------------------------------------------------
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
        bc_items = BlockConfigItem.objects.filter(Q(content_type=None) | Q(content_type=context['object'].entity_type)) \
                                          .order_by('order')
        block_ids = [bc_item.block_id for bc_item in bc_items if bc_item.content_type_id is not None]

        if not block_ids:
            block_ids = [bc_item.block_id for bc_item in bc_items] #we fallback to the default config.

        blocks_manager.add_group('detailview_blocks', *block_registry.get_blocks([id_ for id_ in block_ids if id_])) #TODO: use CONSTANT

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
        bc_items = BlockConfigItem.objects.filter(Q(content_type=None) | Q(content_type__in=ct_ids), on_portal=True) \
                                          .order_by('order')

        ctypes_filter     = set(ct_ids)
        configured_ctypes = set(bci.content_type_id for bci in bc_items)
        if not all(ct_id in configured_ctypes for ct_id in ct_ids):
            ctypes_filter.add(None) #NB: at least one ContentType has no specific configuration => we use default config too.

        #Blocks for all ContentTypes are merged (merging algo is quite stupid but it is satisfactory)
        block_ids   = []
        used_blocks = set()

        for bc_item in bc_items:
            block_id = bc_item.block_id

            if (block_id not in used_blocks) and (bc_item.content_type_id in ctypes_filter):
                used_blocks.add(block_id)
                block_ids.append(block_id)

        blocks_manager.add_group('portal_blocks', *block_registry.get_blocks([id_ for id_ in block_ids if id_])) #TODO: use CONSTANT

        return ''


@register.tag(name="display_portal_blocks")
def do_portal_blocks_displayer(parser, token):
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
        blocks_manager.add_group('home_blocks', *block_registry.get_blocks([id_ for id_ in block_ids if id_])) #TODO: use CONSTANT

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
