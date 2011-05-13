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

from django.template.loader import get_template
from django.utils.translation import ugettext_lazy as _, ungettext

_BASE    = 'base'
_INFO    = 'info'
_ERROR   = 'error'
_SUCCESS = 'success'

MESSAGE_TYPES_VERBOSE = {
    _BASE:    lambda count: u"",
    _INFO:    lambda count: ungettext(u"Information", u"Information", count),
    _ERROR:   lambda count: ungettext(u"Error", u"Errors", count),
    _SUCCESS: lambda count: ungettext(u"Success", u"Successes", count),
}

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


#TODO: %s/Contact/Entity & %s/contact=/entity=
class MessageContact(MessageSucceed):
    def __init__(self, contact, message=u"", **kwargs):
        super(MessageContact, self).__init__(contact=contact, message=message, **kwargs)

class MessageInfoContactAdd(MessageContact):
    template = "activesync/messages/message_info_contact_add.html"
    type     = _INFO

class MessageSucceedContactAdd(MessageContact):
    template = "activesync/messages/message_succeed_contact_add.html"

class MessageSucceedContactUpdate(MessageContact):
    template = "activesync/messages/message_succeed_contact_update.html"

    def __init__(self, contact, message=u"", data=None, **kwargs):
        super(MessageSucceedContactUpdate, self).__init__(contact, message, data=data, **kwargs)

    
