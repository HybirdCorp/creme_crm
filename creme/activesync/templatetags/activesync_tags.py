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
from django.template.defaulttags import TemplateLiteral
from django.template import Library

from creme.activesync.messages import MESSAGE_TYPES_VERBOSE
from creme.activesync.models.active_sync import USER_HISTORY_TYPE_IMG, USER_HISTORY_WHERE_IMG
from creme.creme_core.utils.media import creme_media_themed_url

register = Library()

_MESSAGE_RENDER_RE = compile_re(r'(.*?)$')

@register.tag(name="render_message")
def _do_message_render(parser, token):
    try:
        tag_name, arg = token.contents.split(None, 1) # Splitting by None == splitting by spaces.
    except ValueError:
        raise TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]

    match = _MESSAGE_RENDER_RE.search(arg)
    if not match:
        raise TemplateSyntaxError, "%r tag had invalid arguments" % tag_name

    message_str = match.groups()[0]

    compile_filter = parser.compile_filter

    return MessageRenderNode(message_var=TemplateLiteral(compile_filter(message_str), message_str))

class MessageRenderNode(TemplateNode):
    def __init__(self, message_var):
        self.message_var  = message_var

    def render(self, context):
        return self.message_var.eval(context).render(context)

@register.simple_tag
def get_verbose_message_type(type, count=1):
    return MESSAGE_TYPES_VERBOSE.get(type, lambda count: "")(count)

@register.simple_tag
def get_history_type_img(history_type):
    return creme_media_themed_url(USER_HISTORY_TYPE_IMG.get(history_type, ""))

@register.simple_tag
def get_history_where_img(history_where):
    return creme_media_themed_url(USER_HISTORY_WHERE_IMG.get(history_where, ""))