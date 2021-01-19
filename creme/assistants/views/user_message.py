# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.assistants.forms.user_message import UserMessageForm
from creme.assistants.models import UserMessage
from creme.creme_core.views import generic


class UserMessageCreation(generic.CremeModelCreationPopup):
    model = UserMessage
    form_class = UserMessageForm
    title = _('New message')


class RelatedUserMessageCreation(generic.AddingInstanceToEntityPopup):
    model = UserMessage
    form_class = UserMessageForm
    title = _('New message about «{entity}»')


class UserMessageDeletion(generic.CremeModelDeletion):
    model = UserMessage

    def check_instance_permissions(self, instance, user):
        if user.id != instance.recipient_id:
            raise PermissionDenied(
                gettext('You are not allowed to delete this message: {}').format(instance)
            )
