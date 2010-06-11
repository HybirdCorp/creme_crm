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

from django.template import Library

from sms.blocks import (sendlists_block, recipients_block, contacts_block, sendings_block, messages_block,)


register = Library()

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_sendlists(context):
    return {'blocks': [sendlists_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_manual_recipients(context):
    return {'blocks': [recipients_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_recipient_contacts(context):
    return {'blocks': [contacts_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_sendings(context):
    return {'blocks': [sendings_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_messages(context):
    return {'blocks': [messages_block.detailview_display(context)]}

@register.filter(name="phonenumber")
def phonenumber(value):
    return ''.join(c for c in value if c.isdigit())

@register.filter(name="formatphone")
def formatphone(value):
    if not value:
        return ''
    
    length = len(value)
    
    if length < 6:
        return value
    
    if length%2 > 0:
        return value[:3] + ' ' + ''.join(c if not i%2 else c + ' ' for i, c in enumerate(value[3:]))
    
    return ''.join(c if not i%2 else c + ' ' for i, c in enumerate(value)) if value else ''
