################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

import logging
from collections.abc import Iterable
from functools import partial

from django.db import models
from django.db.transaction import atomic
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

import creme.creme_core.models as core_models
from creme.assistants.constants import UUID_CHANNEL_USERMESSAGES
from creme.creme_core.models import fields as creme_fields

logger = logging.getLogger(__name__)


class UserMessagePriority(core_models.MinionModel):
    title = models.CharField(_('Title'), max_length=200)

    creation_label = pgettext_lazy('assistants-message', 'Create a priority')

    class Meta:
        app_label = 'assistants'
        verbose_name = _('Priority of user message')
        verbose_name_plural = _('Priorities of user message')
        ordering = ('title',)

    def __str__(self):
        return self.title


class UserMessageManager(models.Manager):
    @atomic
    def create_for_users(self, *,
                         users: Iterable[core_models.CremeUser],
                         title: str, body: str,
                         priority: UserMessagePriority,
                         sender: core_models.CremeUser,
                         entity: core_models.CremeEntity | None,
                         ) -> None:
        """Create UserMessages instances to sent to several users.
        Notice that teams are treated as several Users.
        @param users: Recipients of the messages; notice that duplicates are removed.
        @param title: Title of the messages.
        @param body: Body of the messages.
        @param priority: Priority of the messages.
        @param sender: User which sent the messages.
        @param entity: optional related entity.
        """
        from creme.assistants.notification import MessageSentContent

        users_map = {}
        for user in users:
            if user.is_team:
                users_map.update(user.teammates)
            else:
                users_map[user.id] = user

        channel = core_models.NotificationChannel.objects.get_for_uuid(UUID_CHANNEL_USERMESSAGES)
        build_msg = partial(
            self.model,
            creation_date=now(),
            title=title,
            body=body,
            priority=priority,
            sender=sender,
            real_entity=entity,
        )
        # NB: bulk_create() does not return instances with PKs
        for user in users_map.values():
            message = build_msg(recipient=user)
            message.save()

            core_models.Notification.objects.send(
                channel=channel,
                users=[user],
                content=MessageSentContent(instance=message),
            )

    create_for_users.alters_data = True


class UserMessage(core_models.CremeModel):
    title = models.CharField(_('Title'), max_length=200)
    body = models.TextField(_('Message body'))
    creation_date = models.DateTimeField(_('Creation date'))
    priority = models.ForeignKey(
        UserMessagePriority, verbose_name=_('Priority'), on_delete=models.PROTECT,
    )

    sender = creme_fields.CremeUserForeignKey(
        verbose_name=pgettext_lazy('assistants-message', 'Sender'),
        related_name='sent_assistants_messages_set',
    )
    recipient = creme_fields.CremeUserForeignKey(
        verbose_name=_('Recipient'), related_name='received_assistants_messages_set',
    )

    entity_content_type = creme_fields.EntityCTypeForeignKey(
        null=True, related_name='+', editable=False,
    )
    entity = models.ForeignKey(
        core_models.CremeEntity,
        null=True,  related_name='assistants_messages',
        editable=False, on_delete=models.CASCADE,
    ).set_tags(viewable=False)
    real_entity = creme_fields.RealEntityForeignKey(
        ct_field='entity_content_type', fk_field='entity',
    )

    objects = UserMessageManager()

    creation_label = _('Create a message')
    save_label     = _('Save the message')

    class Meta:
        app_label = 'assistants'
        verbose_name = _('User message')
        verbose_name_plural = _('User messages')

    def __str__(self):
        return self.title
