################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.assistants import models
from creme.creme_core.core import notification as core_notif


class AlertReminderContent(core_notif.RelatedToModelBaseContent):
    id = core_notif.NotificationContent.generate_id('assistants', 'alert_reminder')
    subject_template_name = 'assistants/notifications/alert/subject.txt'
    body_template_name = 'assistants/notifications/alert/body.txt'
    html_body_template_name = 'assistants/notifications/alert/body.html'

    model = models.Alert


class TodoReminderContent(core_notif.RelatedToModelBaseContent):
    id = core_notif.NotificationContent.generate_id('assistants', 'todo_reminder')
    subject_template_name = 'assistants/notifications/todo/subject.txt'
    body_template_name = 'assistants/notifications/todo/body.txt'
    html_body_template_name = 'assistants/notifications/todo/body.html'

    model = models.ToDo


class UserMessagesChannelType(core_notif.NotificationChannelType):
    id = core_notif.NotificationChannelType.generate_id('assistants', 'user_messages')
    verbose_name = _('User messages')
    description = _('A user message has been received (app: Assistants)')


class MessageSentContent(core_notif.RelatedToModelBaseContent):
    id = core_notif.RelatedToModelBaseContent.generate_id('assistants', 'message_sent')
    subject_template_name = 'assistants/notifications/user_message/subject.txt'
    body_template_name = 'assistants/notifications/user_message/body.txt'
    html_body_template_name = 'assistants/notifications/user_message/body.html'

    model = models.UserMessage
