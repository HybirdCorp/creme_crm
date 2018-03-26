# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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
# import warnings

from django.template import Library, TemplateSyntaxError, Node as TemplateNode
from django.template.defaulttags import TemplateLiteral

from ..messages import MESSAGE_TYPES_VERBOSE
from ..models import active_sync


register = Library()

_MESSAGE_RENDER_RE = compile_re(r'(.*?)$')


# TODO: rename 'activesync_...'
# TODO: 'simpletag' seems sufficient
@register.tag(name='render_message')
def _do_message_render(parser, token):
    try:
        tag_name, arg = token.contents.split(None, 1)  # Splitting by None == splitting by spaces.
    except ValueError:
        raise TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]

    match = _MESSAGE_RENDER_RE.search(arg)
    if not match:
        raise TemplateSyntaxError, "%r tag had invalid arguments" % tag_name

    message_str = match.groups()[0]

    return MessageRenderNode(message_var=TemplateLiteral(parser.compile_filter(message_str), message_str))


class MessageRenderNode(TemplateNode):
    def __init__(self, message_var):
        self.message_var = message_var

    def render(self, context):
        return self.message_var.eval(context).render(context)


@register.simple_tag
def get_verbose_message_type(type, count=1):  # TODO: rename 'activesync_...'
    return MESSAGE_TYPES_VERBOSE.get(type, lambda count: '')(count)


# @register.simple_tag
# def get_history_type_img(history_type):
#     warnings.warn('Active sync tag {% get_history_type_img %} is deprecated ; '
#                   'use {% activesync_history_type_icon_name %} instead.',
#                   DeprecationWarning
#                  )
#     from creme.creme_core.utils.media import creme_media_themed_url
#
#     return creme_media_themed_url(active_sync.USER_HISTORY_TYPE_IMG.get(history_type, ''))


_HISTORY_TYPE_ICONS = {
    active_sync.CREATE: 'add',
    active_sync.UPDATE: 'edit',
    active_sync.DELETE: 'delete',
}


# @register.assignment_tag
@register.simple_tag
def activesync_history_type_icon_name(history_type):
    return _HISTORY_TYPE_ICONS.get(history_type, '')


# @register.simple_tag
# def get_history_where_img(history_where):
#     warnings.warn('Active sync tag {% get_history_where_img %} is deprecated ; '
#                   'use {% activesync_history_where_icon_name %} instead.',
#                   DeprecationWarning
#                  )
#     from creme.creme_core.utils.media import creme_media_themed_url
#
#     return creme_media_themed_url(active_sync.USER_HISTORY_WHERE_IMG.get(history_where, ''))


_HISTORY_WHERE_ICONS = {
    active_sync.IN_CREME:  'creme',
    active_sync.ON_SERVER: 'organisation',  # TODO: Change this icon for a server icon
}


# @register.assignment_tag
@register.simple_tag
def activesync_history_where_icon_name(history_where):
    return _HISTORY_WHERE_ICONS.get(history_where, '')
