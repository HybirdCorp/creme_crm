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
from django.template import Template
from django.template.loader import get_template

_BASE    = 'base'
_INFO    = 'info'
_ERROR   = 'error'
_SUCCESS = 'success'

class Message(object):
    template = "activesync/messages/message_base.html"
    type     = _BASE

    def __init__(self, **msg):
        self.msg = msg

    def render(self, context):
        template = self.template
        context.update(self.msg)
        return get_template(template).render(context)


class MessageSucceed(Message):
    template = "activesync/messages/message_succeed.html"
    type     = _SUCCESS

class MessageInfo(Message):
    template = "activesync/messages/message_info.html"
    type     = _INFO

class MessageError(Message):
    template = "activesync/messages/message_error.html"
    type     = _ERROR


class MessageContact(MessageSucceed):
    def __init__(self, contact, message="", **kwargs):
        super(MessageContact, self).__init__(contact=contact, message=message, **kwargs)

class MessageInfoContactAdd(MessageContact):
    template = "activesync/messages/message_info_contact_add.html"

class MessageSucceedContactAdd(MessageContact):
    template = "activesync/messages/message_succeed_contact_add.html"

class MessageSucceedContactUpdate(MessageContact):
    template = "activesync/messages/message_succeed_contact_update.html"

    def __init__(self, contact, message="", data=None, **kwargs):
        super(MessageSucceedContactUpdate, self).__init__(contact, message, data=data, **kwargs)

    
