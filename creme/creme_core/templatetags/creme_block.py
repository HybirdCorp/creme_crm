# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from collections import defaultdict
from re import compile as compile_re

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.template import Library, Template, TemplateSyntaxError, Node as TemplateNode
from django.template.defaulttags import TemplateLiteral
from django.template.loader import get_template
from django.utils.translation import ungettext #ugettext

from ..core.entity_cell import EntityCellRegularField, EntityCellCustomField
from ..models import Relation, BlockDetailviewLocation, BlockPortalLocation, BlockMypageLocation
from ..gui.block import Block, block_registry, BlocksManager
from ..gui.bulk_update import bulk_update_registry

register = Library()


_DETAIL_BLOCKS_TOP    = 'detailview_blocks_top'
_DETAIL_BLOCKS_RIGHT  = 'detailview_blocks_right'
_DETAIL_BLOCKS_LEFT   = 'detailview_blocks_left'
_DETAIL_BLOCKS_BOTTOM = 'detailview_blocks_bottom'
_HOME_BLOCKS          = 'home_blocks'
_MYPAGE_BLOCKS        = 'mypage_blocks'
_PORTAL_BLOCKS        = 'portal_blocks'


def _arg_in_quotes_or_die(arg, tag_name):
    first_char = arg[0]
    if not (first_char == arg[-1] and first_char in ('"', "'")):
        raise TemplateSyntaxError("%r tag's argument should be in quotes" % tag_name)

#-------------------------------------------------------------------------------
_COLSPAN_ARG = 'colspan='

@register.tag(name="get_block_header")#TODO: 'templatize' colspan argument
def do_block_header(parser, token):
    """Eg:{% get_block_header colspan=8 %}
            <th class="label">My title</th>
          {% end_get_block_header %}
    """
    try:
        tag_name, arg = token.contents.split(None, 1) # Splitting by None == splitting by spaces.
    except ValueError:
        raise TemplateSyntaxError("%r tag requires arguments" % token.contents.split()[0])

    if not arg.startswith(_COLSPAN_ARG):
        raise TemplateSyntaxError("%r tag argument is on the model: %s12" % (tag_name, _COLSPAN_ARG))

    raw_colspan = arg[len(_COLSPAN_ARG):]

    try:
        colspan = TemplateLiteral(parser.compile_filter(raw_colspan), raw_colspan)
    except Exception as e:
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
        context['colspan'] = self.colspan.eval(context)

        return self.header_tpl.render(context)

#-------------------------------------------------------------------------------

@register.inclusion_tag('creme_core/templatetags/widgets/block_reload_uri.html', takes_context=True)
def get_block_reload_uri(context): #{% include 'creme_core/templatetags/widgets/block_reload_uri.html' %} instead ??
    return context

@register.inclusion_tag('creme_core/templatetags/widgets/block_relation_reload_uri.html', takes_context=True)
def get_block_relation_reload_uri(context):
    "Specific to relation block, it aim to reload all relations blocks on the page at the same time."
    block_id = context['block_name']
    #TODO: move a part in BlocksManager ?? ('_blocks' is private...)
    context['deps'] = ','.join(block.id_ for block in BlocksManager.get(context)._blocks
                                            if (block.dependencies == '*'
                                                or Relation in block.dependencies
                                               ) and block.id_ != block_id
                              )

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
            #'title':       ugettext(title),
            'title':       title,
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


@register.inclusion_tag('creme_core/templatetags/widgets/block_empty_fields_button.html', takes_context=True)
def get_toggle_empty_field_button(context):
    return context

#-------------------------------------------------------------------------------
_LINE_CREATOR_RE = compile_re(r'at_url (.*?) with_label (.*?) with_perms (.*?)$')

def _do_line_creator(parser, token, template_path):
    try:
        tag_name, arg = token.contents.split(None, 1) # Splitting by None == splitting by spaces.
    except ValueError:
        raise TemplateSyntaxError("%r tag requires arguments" % token.contents.split()[0])

    match = _LINE_CREATOR_RE.search(arg)
    if not match:
        raise TemplateSyntaxError("%r tag had invalid arguments" % tag_name)

    url, label_str, perm_str = match.groups()

    first_char = url[0]
    if not (first_char == url[-1] and first_char in ('"', "'")):
        raise TemplateSyntaxError("%r tag's url argument should be in quotes" % tag_name)

    compile_filter = parser.compile_filter

    return LineCreatorNode(url=url[1:-1],
                           label_var=TemplateLiteral(compile_filter(label_str), label_str),
                           perm_var=TemplateLiteral(compile_filter(perm_str), perm_str),
                           template_path=template_path
                          )

class LineCreatorNode(TemplateNode):
    def __init__(self, url,  label_var, perm_var, template_path):
        self.template  = get_template(template_path)
        self.url_tpl   = Template(url)
        self.perm_var  = perm_var
        self.label_var = label_var

    def render(self, context):
        context['action_url'] = self.url_tpl.render(context)
        context['label']      = self.label_var.eval(context)
        context['line_perm']  = self.perm_var.eval(context)

        return self.template.render(context)

@register.tag(name="get_line_adder")
def do_line_adder(parser, token):
    """Eg: {% get_line_adder at_url '/app/model/add/{{object.id}}/' with_label _("New Stuff") with_perms has_perm %}"""
    return _do_line_creator(parser, token, 'creme_core/templatetags/widgets/block_line_adder.html')

@register.tag(name="get_line_linker")
def do_line_linker(parser, token):
    """Eg: {% get_line_linker at_url '/assistants/action/link/{{object.id}}/' with_label _("Link to existing Stuffs") with_perms has_perm %}"""
    return _do_line_creator(parser, token, 'creme_core/templatetags/widgets/block_line_linker.html')

@register.tag(name="get_line_viewer")
def do_line_viewer(parser, token):
    """Eg: {% get_line_viewer at_url '/assistants/action/link/{{object.id}}/' with_label _("View this object") with_perms has_perm %}"""
    return _do_line_creator(parser, token, 'creme_core/templatetags/widgets/block_line_viewer.html')

#-------------------------------------------------------------------------------
_LINE_RELATOR_RE = compile_re(r'to_subject (.*?) with_rtype_id (.*?) with_ct_id (.*?) with_label (.*?) with_perms (.*?)(\ssimple|\smultiple)?$')

@register.tag(name="get_line_relator")
def do_line_relator(parser, token):
    """Eg: {% get_line_relator to_object object with_rtype_id predicate_id with_ctype ct with_label _("Link to an existing Stuff") with_perms has_perm %}"""
    try:
        tag_name, arg = token.contents.split(None, 1) # Splitting by None == splitting by spaces.
    except ValueError:
        raise TemplateSyntaxError("%r tag requires arguments" % token.contents.split()[0])

    match = _LINE_RELATOR_RE.search(arg)
    if not match:
        raise TemplateSyntaxError("%r tag had invalid arguments" % tag_name)

    subject_str, type_id_str, ctype_id_str, label_str, perm_str, is_multiple = match.groups()
    compile_filter = parser.compile_filter

    if is_multiple is not None:
        is_multiple = (is_multiple.strip() == "multiple")
    else:
        is_multiple = True

    return LineRelatorNode(subject_var=TemplateLiteral(compile_filter(subject_str), subject_str),
                           rtype_id_var=TemplateLiteral(compile_filter(type_id_str), type_id_str),
                           ctype_id_var=TemplateLiteral(compile_filter(ctype_id_str), ctype_id_str),
                           label_var=TemplateLiteral(compile_filter(label_str), label_str),
                           perm_var=TemplateLiteral(compile_filter(perm_str), perm_str),
                           is_multiple=is_multiple
                          )

class LineRelatorNode(TemplateNode):
    def __init__(self, subject_var, rtype_id_var, ctype_id_var, label_var, perm_var, is_multiple):
        self.template = get_template('creme_core/templatetags/widgets/block_line_relator.html')
        self.subject_var  = subject_var
        self.rtype_id_var = rtype_id_var
        self.ctype_id_var = ctype_id_var
        self.label_var    = label_var
        self.perm_var     = perm_var
        self.is_multiple  = is_multiple

    def render(self, context):
        context['subject_id']   = self.subject_var.eval(context).id
        context['rtype_id']     = self.rtype_id_var.eval(context)
        context['ct_id']        = self.ctype_id_var.eval(context)
        context['label']        = self.label_var.eval(context)
        context['line_perm']    = self.perm_var.eval(context)
        context['is_multiple']  = self.is_multiple

        return self.template.render(context)


#TAGS: "get_line_deletor" & "get_line_unlinker" ----------------------------------
_LINE_SUPPR_RE = compile_re(r'at_url (.*?) with_args (.*?) with_perms (.*?)$')

def _do_line_suppr(parser, token, template_path):
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise TemplateSyntaxError("%r tag requires arguments" % token.contents.split()[0])

    match = _LINE_SUPPR_RE.search(arg)
    if not match:
        raise TemplateSyntaxError("%r tag had invalid arguments" % tag_name)

    suppr_url, post_args, perm_str = match.groups()

    for group in (suppr_url, post_args):
        first_char = group[0]
        if not (first_char == group[-1] and first_char in ('"', "'")):
            raise TemplateSyntaxError("%r tag's argument should be in quotes" % tag_name)

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

@register.tag(name="get_line_deletor")
def do_line_deletor(parser, token):
    """Eg: {% get_line_deletor at_url '/app/model/delete' with_args "{'id' : {{object.id}} }" with_perms boolean_variable %}"""
    return _do_line_suppr(parser, token, 'creme_core/templatetags/widgets/block_line_deletor.html')

@register.tag(name="get_line_unlinker")
def do_line_unlinker(parser, token):
    """Eg: {% get_line_unlinker at_url '/app/model/unlink' with_args "{'id' : {{object.id}} }" with_perms boolean_variable %}"""
    return _do_line_suppr(parser, token, 'creme_core/templatetags/widgets/block_line_unlinker.html')


#TAG: "get_field_editor" -----------------------------------------------------
_FIELD_EDITOR_RE = compile_re(r'on (.*?) (.*?) for (.*?)$')

@register.tag(name="get_field_editor")
def do_get_field_editor(parser, token):
    """Eg: {% get_field_editor on custom|regular|entity_cell field|'field_name'|"field_name" for object %}"""
    try:
        tag_name, arg = token.contents.split(None, 1) # Splitting by None == splitting by spaces.
    except ValueError:
        raise TemplateSyntaxError("%r tag requires arguments" % token.contents.split()[0])

    match = _FIELD_EDITOR_RE.search(arg)
    if not match:
        raise TemplateSyntaxError("%r tag had invalid arguments" % tag_name)

    field_type_str, field_str, object_str = match.groups()

    field_editor_node = _FIELD_EDITOR_NODES.get(field_type_str)

    if not field_editor_node:
        raise TemplateSyntaxError("%r invalid field category tag: %r" % (tag_name, field_type_str))

    return field_editor_node(TemplateLiteral(parser.compile_filter(field_str), field_str),
                             TemplateLiteral(parser.compile_filter(object_str), object_str))

class RegularFieldEditorNode(TemplateNode):
    template_name = 'creme_core/templatetags/widgets/block_field_editor.html'

    def __init__(self, field_var, object_var):
        self.field_var  = field_var
        self.object_var = object_var

    def _update_context(self, context, field, instance):
        model = instance.__class__
        field_eval = model._meta.get_field(field) if isinstance(field, basestring) else field
        field_name = field_eval.name

        context['field']     = field_name
        context['updatable'] = bulk_update_registry.is_bulk_updatable(model, field_name, exclude_unique=False)

    def render(self, context):
        instance = self.object_var.eval(context)
        field    = self.field_var.eval(context)

        #TODO: factorise with other code that manage auxiliary entities
        owner = instance.get_related_entity() if hasattr(instance, 'get_related_entity') else instance

        context['object']    = instance
        context['ct_id']     = ContentType.objects.get_for_model(instance).pk #TODO: instance.entity_type_id ??
        context['edit_perm'] = context['user'].has_perm_to_change(owner)

        self._update_context(context, field, instance)

        return get_template(self.template_name).render(context)

class CustomFieldEditorNode(RegularFieldEditorNode):
    def _update_context(self, context, field, instance):
        context['field']     = field.id
        context['updatable'] = True

class EntityCellEditorNode(RegularFieldEditorNode):
    def _update_context(self, context, cell, instance):
        if isinstance(cell, EntityCellRegularField):
            #model = instance.entity_type.model_class()
            #field_name = cell.value.partition('__')[0]
            field_name = cell.field_info[0].name
            context['field'] = field_name
            #context['updatable'] = bulk_update_registry.is_bulk_updatable(model, field_name, exclude_unique=False)
            context['updatable'] = bulk_update_registry.is_bulk_updatable(instance.__class__,
                                                                          field_name,
                                                                          exclude_unique=False,
                                                                         )
        elif isinstance(cell, EntityCellCustomField):
            context['field'] = cell.value
            context['updatable'] = True
        else:
            context['updatable'] = False

_FIELD_EDITOR_NODES = {'regular':       RegularFieldEditorNode,
                       'custom':        CustomFieldEditorNode,
                       'entity_cell':   EntityCellEditorNode,
                      }

#-------------------------------------------------------------------------------
_LINE_EDITOR_RE = compile_re(r'at_url (.*?) with_perms (.*?)$')

@register.tag(name="get_line_editor")
def do_line_editor(parser, token):
    """Eg: {% get_line_editor at_url '/assistants/action/edit/{{action.id}}/' with_perms has_perm %}"""
    try:
        tag_name, arg = token.contents.split(None, 1) # Splitting by None == splitting by spaces.
    except ValueError:
        raise TemplateSyntaxError("%r tag requires arguments" % token.contents.split()[0])

    match = _LINE_EDITOR_RE.search(arg)
    if not match:
        raise TemplateSyntaxError("%r tag had invalid arguments" % tag_name)

    edit_url, perm_str = match.groups()

    first_char = edit_url[0]
    if not (first_char == edit_url[-1] and first_char in ('"', "'")):
        raise TemplateSyntaxError("%r tag's url argument should be in quotes" % tag_name)

    return LineEditorNode(edit_url[1:-1], TemplateLiteral(parser.compile_filter(perm_str), perm_str))

class LineEditorNode(TemplateNode):
    def __init__(self, edit_url, perm_var):
        self.template = get_template('creme_core/templatetags/widgets/block_line_editor.html')
        self.url_tpl = Template(edit_url)
        self.perm_var = perm_var

    def render(self, context):
        context['edit_url'] = self.url_tpl.render(context)
        context['edit_line_perm'] = self.perm_var.eval(context)

        return self.template.render(context)

#-------------------------------------------------------------------------------
_LISTVIEW_BUTTON_RE = compile_re(r'with_ct_id (.*?) with_label (.*?) with_q_filter (.*?)$')

@register.tag(name="get_listview_button")
def do_line_lister(parser, token):
    """Eg: {% get_listview_button with_ct_id ct_id with_label _("List of related products") with_q_filter q_filter %}"""
    try:
        tag_name, arg = token.contents.split(None, 1) # Splitting by None == splitting by spaces.
    except ValueError:
        raise TemplateSyntaxError("%r tag requires arguments" % token.contents.split()[0])

    match = _LISTVIEW_BUTTON_RE.search(arg)
    if not match:
        raise TemplateSyntaxError("%r tag had invalid arguments" % tag_name)

    ctype_id_str, label_str, q_filter_str = match.groups()
    compile_filter = parser.compile_filter

    return ListViewButtonNode(ctype_id_var=TemplateLiteral(compile_filter(ctype_id_str), ctype_id_str),
                              label_var=TemplateLiteral(compile_filter(label_str), label_str),
                              q_filter_var=TemplateLiteral(compile_filter(q_filter_str), q_filter_str),
                             )

class ListViewButtonNode(TemplateNode):
    def __init__(self, ctype_id_var, label_var, q_filter_var):
        self.template = get_template('creme_core/templatetags/widgets/block_listview_button.html')
        self.ctype_id_var = ctype_id_var
        self.label_var    = label_var
        self.q_filter_var = q_filter_var

    def render(self, context):
        context['ct_id']    = self.ctype_id_var.eval(context)
        context['label']    = self.label_var.eval(context)
        context['q_filter'] = self.q_filter_var.eval(context) or {}

        return self.template.render(context)

#-------------------------------------------------------------------------------
#TODO: Django 1.4 => can use keyword :)
@register.inclusion_tag('creme_core/templatetags/widgets/block_footer.html', takes_context=True)
def get_block_footer(context, colspan):
    assert 'page' in context, 'Use the templatetag <get_block_footer> only on paginated blocks (problem with: %s)' % context.get('block_name', 'Unknown block id')
    context['colspan'] = colspan
    return context


#-------------------------------------------------------------------------------
_BLOCK_IMPORTER_RE = compile_re(r'from_app (.*?) named (.*?) as (.*?)$')

@register.tag(name="import_block")
def do_block_importer(parser, token):
    """Eg: {% import_block from_app 'creme_core' named 'relations' as 'relations_block' %}"""
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise TemplateSyntaxError("%r tag requires arguments" % token.contents.split()[0])

    match = _BLOCK_IMPORTER_RE.search(arg)
    if not match:
        raise TemplateSyntaxError("%r tag had invalid arguments" % tag_name)

    groups = match.groups()

    if len(groups) != 3:
        raise TemplateSyntaxError("%r tag's takes 3 arguments" % tag_name)

    for group in groups:
        first_char = group[0]
        if not (first_char == group[-1] and first_char in ('"', "'")):
            raise TemplateSyntaxError("%r tag's argument should be in quotes" % tag_name)

    app_name, block_name, alias = groups

    return BlockImporterNode(app_name[1:-1], block_name[1:-1], alias[1:-1])

class BlockImporterNode(TemplateNode):
    def __init__(self, app_name, block_name, alias):
        self.block = block_registry[Block.generate_id(app_name, block_name)]
        self.alias = alias #name of the block in this template

    def render(self, context):
        BlocksManager.get(context).add_group(self.alias, self.block)
        return ''


# UTILS ------------------------------------------------------------------------

def _parse_block_alias(tag_name, block_alias):
    first_char = block_alias[0]
    if not (first_char == block_alias[-1] and first_char in ('"', "'")):
        raise TemplateSyntaxError("%r tag's argument should be in quotes" % tag_name)

    block_alias = block_alias[1:-1]

    if any(not char.isalnum() and char not in ('-', '_') for char in block_alias):
        raise TemplateSyntaxError("%r tag's argument should be be composed with chars in {[A-Za-z][0-9]-_}" % tag_name)

    return block_alias

# DETAILVIEW BLOCKS ------------------------------------------------------------

@register.tag(name="display_block_detailview")
def do_block_detailviewer(parser, token):
    """Eg: {% display_block_detailview 'relations_block' %}"""
    try:
        # Splitting by None == splitting by spaces.
        tag_name, block_alias = token.contents.split(None, 1)
    except ValueError:
        raise TemplateSyntaxError("%r tag requires one argument" % token.contents.split()[0])

    return BlockDetailViewerNode(_parse_block_alias(tag_name, block_alias))

class BlockDetailViewerNode(TemplateNode):
    def __init__(self, block_alias):
        self.alias = block_alias #name of the block in this template

    def render(self, context):
        block = BlocksManager.get(context).pop_group(self.alias)[0]

        return block.detailview_display(context)
        #detailview_display = getattr(block, 'detailview_display', None)
        #return detailview_display(context) if detailview_display else \
               #"THIS BLOCK CAN'T BE DISPLAY ON DETAILVIEW (YOU HAVE A CONFIG PROBLEM): %s" % block.id_


@register.tag(name="import_object_block")
def do_object_block_importer(parser, token):
    """Eg: {% import_object_block object=object as 'object_block' %}"""
    split = token.contents.split()
    tag_name = split[0]

    if len(split) != 3:
        raise TemplateSyntaxError("%r tag requires 2 arguments" % tag_name)

    if split[1] != 'as':
        raise TemplateSyntaxError("%r tag had invalid arguments" % tag_name)

    alias = split[2]
    _arg_in_quotes_or_die(alias, tag_name)

    return ObjectBlockImporterNode(alias=alias[1:-1])

class ObjectBlockImporterNode(TemplateNode):
    def __init__(self, alias):
        self.alias = alias

    def render(self, context):
        BlocksManager.get(context).add_group(self.alias, block_registry.get_block_4_object(context['object']))
        return ''


@register.tag(name="import_detailview_blocks")
def do_detailview_blocks_importer(parser, token):
    return DetailviewBlocksImporterNode()

class DetailviewBlocksImporterNode(TemplateNode):
    _GROUPS = ((_DETAIL_BLOCKS_TOP,    BlockDetailviewLocation.TOP),
               (_DETAIL_BLOCKS_LEFT,   BlockDetailviewLocation.LEFT),
               (_DETAIL_BLOCKS_RIGHT,  BlockDetailviewLocation.RIGHT),
               (_DETAIL_BLOCKS_BOTTOM, BlockDetailviewLocation.BOTTOM),
              )

    def render(self, context):
        blocks_manager = BlocksManager.get(context)
        entity = context['object']
        locs = BlockDetailviewLocation.objects.filter(Q(content_type=None) | Q(content_type=entity.entity_type)) \
                                              .order_by('order')

        #we fallback to the default config is there is no config for this content type.
        locs = [loc for loc in locs if loc.content_type_id is not None] or locs
        loc_map = defaultdict(list)

        for loc in locs:
            block_id = loc.block_id

            if block_id: #populate scripts can leave void block ids
                if BlockDetailviewLocation.id_is_4_model(block_id):
                    block_id = block_registry.get_block_4_object(entity).id_

                loc_map[loc.zone].append(block_id)

        add_group  = blocks_manager.add_group
        get_blocks = block_registry.get_blocks

        for group_name, zone in self._GROUPS:
            add_group(group_name, *get_blocks(loc_map[zone], entity=entity))

        return ''


_ZONES_MAP = {
        'top':    _DETAIL_BLOCKS_TOP,
        'left':   _DETAIL_BLOCKS_LEFT,
        'right':  _DETAIL_BLOCKS_RIGHT,
        'bottom': _DETAIL_BLOCKS_BOTTOM,
    }

@register.tag(name="display_detailview_blocks")
def do_detailview_blocks_displayer(parser, token):
    """{% display_detailview_blocks right %}"""
    split = token.contents.split()
    tag_name = split[0]

    if len(split) != 2:
        raise TemplateSyntaxError("%r tag requires 1 arguments" % tag_name)

    group_name = _ZONES_MAP.get(split[1])
    if not group_name:
        raise TemplateSyntaxError("%r argument must be in: %s" % (tag_name, '/'.join(_ZONES_MAP.iterkeys())))

    return DetailviewBlocksDisplayerNode(group_name)

class DetailviewBlocksDisplayerNode(TemplateNode):
    def __init__(self, group_name):
        self.group_name = group_name

    def block_outputs(self, context):
        model = context['object'].__class__

        for block in BlocksManager.get(context).pop_group(self.group_name):
            detailview_display = getattr(block, 'detailview_display', None)
            if not detailview_display:
                yield "THIS BLOCK CAN'T BE DISPLAY ON DETAILVIEW (YOU HAVE A CONFIG PROBLEM): %s" % (block.id_ or block.__class__.__name__)
                continue

            target_ctypes = block.target_ctypes
            if target_ctypes and not model in target_ctypes:
                yield "THIS BLOCK CAN'T BE DISPLAY ON THIS CONTENT TYPE (YOU HAVE A CONFIG PROBLEM): %s" % block.id_
                continue

            yield detailview_display(context)

    def render(self, context):
        return ''.join(op for op in self.block_outputs(context))

# PORTAL BLOCKS ----------------------------------------------------------------

@register.tag(name="display_block_portal")
def do_block_portalviewer(parser, token):
    """Eg: {% display_block_portal 'stuffs_block' ct_ids %}"""
    try:
        # Splitting by None == splitting by spaces.
        tag_name, block_alias, ct_ids_varname = token.contents.split(None)
    except ValueError:
        raise TemplateSyntaxError("%r tag requires two arguments" % token.contents.split()[0])

    return BlockPortalViewerNode(_parse_block_alias(tag_name, block_alias), ct_ids_varname)

class BlockPortalViewerNode(TemplateNode):
    def __init__(self, block_alias, ct_ids_varname):
        self.alias = block_alias #name of the block in this template
        self.ct_ids_varname = ct_ids_varname

    def render(self, context):
        block = BlocksManager.get(context).pop_group(self.alias)[0]

        return block.portal_display(context, context[self.ct_ids_varname])


def _parse_one_var_tag(token): #TODO: move in creme_core.utils
    try:
        # Splitting by None == splitting by spaces.
        tag_name, var_name = token.contents.split(None, 1)
    except ValueError:
        raise TemplateSyntaxError("%r tag requires one argument" % token.contents.split()[0])

    if any(not char.isalnum() and char not in ('-', '_') for char in var_name):
        raise TemplateSyntaxError("%r tag's argument should be composed with chars in {[A-Za-z][0-9]-_}" % tag_name)

    return var_name


@register.tag(name="import_portal_blocks")
def do_portal_blocks_importer(parser, token):
    """Eg: {% import_portal_blocks app_name %}"""
    split = token.contents.split()

    if len(split) != 2:
        raise TemplateSyntaxError("%r tag requires 1 arguments" % split[0])

    appname_str = split[1]

    return PortalBlocksImporterNode(TemplateLiteral(parser.compile_filter(appname_str), appname_str))

class PortalBlocksImporterNode(TemplateNode):
    def __init__(self, appname_var):
        self.appname_var = appname_var

    def render(self, context):
        blocks_manager = BlocksManager.get(context)
        app_name = self.appname_var.eval(context)
        locs = BlockPortalLocation.objects.filter(Q(app_name='') | Q(app_name=app_name)) \
                                          .order_by('order')

        #we fallback to the default config is there is no config for this app.
        block_ids = [loc.block_id for loc in locs if loc.app_name] or [loc.block_id for loc in locs]

        blocks_manager.add_group(_PORTAL_BLOCKS, *block_registry.get_blocks([id_ for id_ in block_ids if id_]))

        return ''

#TODO: use TemplateLiteral
@register.tag(name="display_portal_blocks")
def do_portal_blocks_displayer(parser, token):
    """Eg: {% display_portal_blocks ct_ids %}"""
    return PortalBlocksDisplayerNode(_parse_one_var_tag(token))

class PortalBlocksDisplayerNode(TemplateNode):
    def __init__(self, ct_ids_varname):
        self.ct_ids_varname = ct_ids_varname

    def block_outputs(self, context):
        blocks = BlocksManager.get(context).pop_group(_PORTAL_BLOCKS)
        ct_ids = context[self.ct_ids_varname]

        for block in blocks:
            portal_display = getattr(block, 'portal_display', None)

            if portal_display is not None:
                yield portal_display(context, ct_ids)
            else:
                yield "THIS BLOCK CAN'T BE DISPLAY ON PORTAL (YOU HAVE A CONFIG PROBLEM): %s" % block.id_

    def render(self, context):
        return ''.join(op for op in self.block_outputs(context))

# HOME & MYPAGE BLOCKS ---------------------------------------------------------

@register.tag(name="import_home_blocks")
def do_home_blocks_importer(parser, token):
    return HomeBlocksImporterNode()

class HomeBlocksImporterNode(TemplateNode):
    def render(self, context):
        blocks_manager = BlocksManager.get(context)
        block_ids = BlockPortalLocation.objects.filter(app_name='creme_core') \
                                                .order_by('order') \
                                                .values_list('block_id', flat=True)
        blocks_manager.add_group(_HOME_BLOCKS, *block_registry.get_blocks([id_ for id_ in block_ids if id_]))

        return ''


@register.tag(name="import_mypage_blocks")
def do_mypage_blocks_importer(parser, token):
    return MypageBlocksImporterNode()

class MypageBlocksImporterNode(TemplateNode):
    def render(self, context):
        blocks_manager = BlocksManager.get(context)
        block_ids = BlockMypageLocation.objects.filter(user=context['user']) \
                                               .order_by('order') \
                                               .values_list('block_id', flat=True)
        blocks_manager.add_group(_MYPAGE_BLOCKS, *block_registry.get_blocks([id_ for id_ in block_ids if id_]))

        return ''


@register.tag(name="display_home_blocks")
def do_home_blocks_displayer(parser, token):
    return HomeBlocksDisplayerNode()

class HomeBlocksDisplayerNode(TemplateNode):
    GROUP_NAME   = _HOME_BLOCKS
    BAD_CONF_MSG = "THIS BLOCK CAN'T BE DISPLAY ON HOME (YOU HAVE A CONFIG PROBLEM): %s"

    def block_outputs(self, context):
        for block in BlocksManager.get(context).pop_group(self.GROUP_NAME):
            home_display = getattr(block, 'home_display', None)

            if home_display is not None:
                yield home_display(context)
            else:
                yield self.BAD_CONF_MSG % block.id_

    def render(self, context):
        return ''.join(op for op in self.block_outputs(context))


@register.tag(name="display_mypage_blocks")
def do_mypage_blocks_displayer(parser, token):
    return MypageBlocksDisplayerNode()

class MypageBlocksDisplayerNode(HomeBlocksDisplayerNode):
    GROUP_NAME   = _MYPAGE_BLOCKS
    BAD_CONF_MSG = "THIS BLOCK CAN'T BE DISPLAY ON MYPAGE (YOU HAVE A CONFIG PROBLEM): %s"


# BLOCKS DEPENDENCIES ------------------------------------------------------------------

@register.inclusion_tag('creme_core/templatetags/blocks_dependencies.html', takes_context=True)
def get_blocks_dependencies(context):
    blocks_manager = BlocksManager.get(context)

    return {'deps_map':         blocks_manager.get_dependencies_map(),
            'remaining_groups': blocks_manager.get_remaining_groups(),
           }

#-------------------------------------------------------------------------------
_BLOCKS_IMPORTER_RE = compile_re(r'(.*?) as (.*?)$')

@register.tag(name="import_blocks")
def do_blocks_importer(parser, token):
    #{% import_blocks blocks as 'my_blocks' %} with blocks a list of registered blocks
    try:
        tag_name, arg = token.contents.split(None, 1) # Splitting by None == splitting by spaces.
    except ValueError:
        raise TemplateSyntaxError("%r tag requires arguments" % token.contents.split()[0])

    match = _BLOCKS_IMPORTER_RE.search(arg)
    if not match:
        raise TemplateSyntaxError("%r tag had invalid arguments" % tag_name)

    blocks_str, alias =  match.groups()

    _arg_in_quotes_or_die(alias, tag_name)

    return BlocksImporterNode(blocks_var=TemplateLiteral(parser.compile_filter(blocks_str), blocks_str),
                              alias=alias[1:-1]
                             )


class BlocksImporterNode(TemplateNode):
    def __init__(self, blocks_var, alias):
        self.blocks_var = blocks_var
        self.alias      = alias

    def render(self, context):
        BlocksManager.get(context).add_group(self.alias, *self.blocks_var.eval(context))
        return ""

#-------------------------------------------------------------------------------
_BLOCKS_DISPLAYER_RE = compile_re(r'(.*?)$')

@register.tag(name="display_blocks")
def do_blocks_displayer(parser, token):
    #{% display_blocks 'my_blocks' %} #Nb my_blocks previously imported with import_blocks
    try:
        tag_name, arg = token.contents.split(None, 1) # Splitting by None == splitting by spaces.
    except ValueError:
        raise TemplateSyntaxError("%r tag requires arguments" % token.contents.split()[0])

    match = _BLOCKS_DISPLAYER_RE.search(arg)
    if not match:
        raise TemplateSyntaxError("%r tag had invalid arguments" % tag_name)

    alias =  match.groups()[0]

    _arg_in_quotes_or_die(alias, tag_name)

    return BlocksDisplayerNode(alias=alias[1:-1])


class BlocksDisplayerNode(TemplateNode):
    def __init__(self, alias):
        self.alias = alias

    def block_outputs(self, context): #TODO: useless (inline the call)
        for block in BlocksManager.get(context).pop_group(self.alias):
            yield block.detailview_display(context)

    def render(self, context):
        return ''.join(op for op in self.block_outputs(context))

