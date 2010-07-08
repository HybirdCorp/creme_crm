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

from django import template
from django.template.loader import get_template
from django.template import Library, Template
from django.utils.translation import ugettext, ungettext
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

from creme_core.models import BlockConfigItem
from creme_core.gui.block import block_registry
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

@register.tag(name="get_line_deletor3")
def do_line_deletor(parser, token):
    """Eg: {% get_line_deletor3 at_url '/app/model/delete' with_args "{'id' : {{object.id}} }" %}"""
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]

    match = _line_deletor_re.search(arg)
    if not match:
        raise template.TemplateSyntaxError, "%r tag had invalid arguments" % tag_name

    groups = match.groups()

    for group in groups:
        first_char = group[0]
        if not (first_char == group[-1] and first_char in ('"', "'")):
            raise template.TemplateSyntaxError, "%r tag's argument should be in quotes" % tag_name

    delete_url, post_args = groups

    return LineDeletorNode(delete_url[1:-1], post_args[1:-1])


class LineDeletorNode(template.Node):
    def __init__(self, delete_url, post_args):
        self.deletor_tpl = get_template('creme_core/templatetags/widgets/block_line_deletor.html')
        self.url_tpl     = Template(delete_url)
        self.args_tpl    = Template(post_args)

    def render(self, context):
        context['delete_url'] = self.url_tpl.render(context)
        context['post_args']  = self.args_tpl.render(context)
        return self.deletor_tpl.render(context)


@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_properties(context):
    return {'blocks': [properties_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_relations(context):
    return {'blocks': [relations_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_detailview_blocks(context):
    BCI_filter = BlockConfigItem.objects.filter

    block_ids = BCI_filter(content_type=context['object'].entity_type).order_by('order').values_list('block_id', flat=True)

    if not block_ids:
        block_ids = BCI_filter(content_type=None).order_by('order').values_list('block_id', flat=True)

    get_block = block_registry.get_block

    return {'blocks': [get_block(id_).detailview_display(context) for id_ in block_ids if id_]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_portal_blocks(context, ct_ids):
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

    blocks = []
    for id_ in block_ids:
        portal_display = getattr(get_block(id_), 'portal_display', None)

        if portal_display is not None:
            blocks.append(portal_display(context, ct_ids))
        else:
            blocks.append("THIS BLOCK CAN'T BE DISPLAY ON PORTAL (YOU HAVE A CONFIG PROBLEM): %s" % id_)

    return {'blocks': blocks}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_home_blocks(context):
    block_ids = BlockConfigItem.objects.filter(content_type=None, on_portal=True).order_by('order').values_list('block_id', flat=True)
    get_block = block_registry.get_block

    blocks = []
    for id_ in block_ids:
        home_display = getattr(get_block(id_), 'home_display', None)

        if home_display is not None:
            blocks.append(home_display(context))
        else:
            blocks.append("THIS BLOCK CAN'T BE DISPLAY ON HOME (YOU HAVE A CONFIG PROBLEM): %s" % id_)

    return {'blocks': blocks}