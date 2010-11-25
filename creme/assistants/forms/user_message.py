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

from datetime import datetime

from django.forms import ModelMultipleChoiceField
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from creme_core.forms import CremeModelForm
from creme_core.forms.widgets import UnorderedMultipleChoiceWidget

from assistants.models import UserMessage


class UserMessageForm(CremeModelForm):
    users = ModelMultipleChoiceField(queryset=User.objects.all(),
                                     widget=UnorderedMultipleChoiceWidget,
                                     label=_(u"Recipients"))

    class Meta:
        model = UserMessage
        fields = ('title', 'body', 'priority')

    def __init__(self, entity, *args, **kwargs):
        super(UserMessageForm, self).__init__(*args, **kwargs)
        self.sender = self.initial['user']
        self.entity = entity

        self.fields['priority'].empty_label = None #TODO: generalise this behavior to all forms ???

    def save(self):
        #NB: we do not call super() because we create several instances
        cdata  = self.cleaned_data
        sender = self.sender
        entity = self.entity

        title = cdata['title']
        body = cdata['body']
        priority = cdata['priority']
        now = datetime.now()

        for user in cdata['users']:
            msg = UserMessage(title=title, body=body, creation_date=now, priority=priority,
                              sender=sender, recipient=user, email_sent=False)
            msg.creme_entity = entity
            msg.save()
