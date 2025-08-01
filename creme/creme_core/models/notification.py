################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025  Hybird
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

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable, Iterator, Sequence
from typing import Literal

from django.conf import settings
from django.db import IntegrityError, models
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ..core import notification
from ..core.notification import NotificationChannelType
from ..global_info import get_per_request_cache
from ..utils.dates import dt_to_ISO8601
from . import CremeUser

logger = logging.getLogger(__name__)


class NotificationChannelManager(models.Manager):
    def get_for_uuid(self, uid: str | uuid.UUID) -> NotificationChannel:
        cached_chans = get_per_request_cache().setdefault('creme_core-channels', {})
        str_uid = str(uid)
        chan = cached_chans.get(str_uid)

        if chan is None:
            try:
                chan = self.get(uuid=uid)
            except self.model.DoesNotExist:
                logger.critical(
                    f'the Channel with uuid="{uid}" does not exist; '
                    f'have you run the command "creme_populate"?!'
                )

                raise

            cached_chans[str_uid] = chan

        return chan


class NotificationChannel(models.Model):
    """All Notifications get a related channel when they are created & sent.
    A channel indicated the kind of information its notifications are about
    (e.g. about system, about jobs...).

    - Some channels are populated by Creme; they got a type (which contains their
      translatable verbose name & description), & their cannot be deleted.
    - Some channels are created by superusers; in this case, the name & the
      description are stored in DataBase. These type of channel can be marked
      as "deleted", & they can be definitively deleted when they have no related
      Notification anymore (see creme_config).
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(verbose_name=_('Name'), max_length=48)
    description = models.TextField(verbose_name=_('Description'), blank=True)
    # TODO: check the length in generate_id()?
    type_id = models.CharField(max_length=48, editable=False)
    required = models.BooleanField(
        verbose_name=_('Is required?'), default=True,
        help_text=_(
            'When a channel is required, users have to chose at least one output '
            '(in-app, email) in their personal configuration.'
        ),
    )
    deleted = models.DateTimeField(null=True, editable=False)
    default_outputs = models.JSONField(
        verbose_name=_('Default outputs'), default=list, editable=False,
    )

    objects = NotificationChannelManager()

    creation_label = _('Create a channel')
    save_label     = _('Save the channel')

    _channel_type: NotificationChannelType | None | Literal[False] = False

    class Meta:
        app_label = 'creme_core'
        # verbose_name = _('Notification channel')
        # verbose_name_plural = _('Notification channels')
        ordering = ('id',)

    def __str__(self):
        return self.final_name

    @property
    def final_name(self):
        chan_type = self.type

        return self.name if chan_type is None else str(chan_type.verbose_name)

    @property
    def final_description(self):
        chan_type = self.type

        return self.description if chan_type is None else str(chan_type.description)

    @property
    def type(self) -> NotificationChannelType | None:
        chan_type = self._channel_type
        if chan_type is False:
            type_id = self.type_id
            self._channel_type = chan_type = (
                notification.notification_registry.get_channel_type(type_id)
                if type_id else
                None
            )

        return chan_type

    @type.setter
    def type(self, value):
        self.type_id = value.id if value else None
        self._channel_type = False

    def save(self, *args, **kwargs):
        if not self.default_outputs:
            raise ValueError('The field "default_outputs" cannot be empty.')

        super().save(*args, **kwargs)


class NotificationChannelConfigItemManager(models.Manager):
    def smart_create(self, *,
                     channel: NotificationChannel,
                     user: CremeUser,
                     ) -> NotificationChannelConfigItem:
        """Create a fresh channel configuration for a user.
        It copies the outputs configuration indicated by the channel.
        It does not fail if a concurrent creation appears.
        """
        try:
            with atomic():
                return self.create(
                    channel=channel, user=user, outputs=channel.default_outputs,
                )
        except IntegrityError:
            logger.exception(
                'Avoid a NotificationChannelConfigItem duplicate <channel="%s" user="%s">.',
                channel.uuid, user.username,
            )
            return self.get(channel=channel, user=user)

    smart_create.alters_data = True

    def bulk_get(self, *,
                 channels: Sequence[NotificationChannel],
                 users: Sequence[CremeUser],
                 ) -> Iterator[NotificationChannelConfigItem]:
        """Retrieve the configuration of several channels & users in an optimized way.
        Items are created if needed.
        Note: the result are cached for the duration of the request.
        """
        all_cached_items = get_per_request_cache().setdefault('creme_core-channels_config', {})

        # NB: we build a list because of MySQL:
        #     1235, "This version of MySQL doesn't yet support 'LIMIT & IN/ALL/ANY/SOME subquery'"
        channels = [*channels]

        if all_cached_items:
            items = {}
            to_retrieve = models.Q()

            for chan in channels:
                for user in users:
                    key = (chan.id, user.id)
                    item = all_cached_items.get(key)
                    if item is None:
                        to_retrieve |= models.Q(channel=chan, user=user)
                    else:
                        items[key] = item

            if to_retrieve:
                for item in self.filter(to_retrieve):
                    items[(item.channel_id, item.user_id)] = item
        else:
            items = {
                (item.channel_id, item.user_id): item
                for item in self.filter(channel__in=channels, user__in=users)
            }

        for chan in channels:
            for user in users:
                key = (chan.id, user.id)
                item = all_cached_items[key] = (
                    items.get(key) or self.smart_create(channel=chan, user=user)
                )

                yield item


class NotificationChannelConfigItem(models.Model):
    """Stores the personal configuration of a user for a given channel.
    It indicates which output(s) to use when sending a notification to this user
    on the channel.
    """
    channel = models.ForeignKey(NotificationChannel, on_delete=models.PROTECT, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, editable=False)
    outputs = models.JSONField(default=list, editable=False)

    objects = NotificationChannelConfigItemManager()

    class Meta:
        app_label = 'creme_core'
        unique_together = ('channel', 'user')

    def __str__(self):
        return str(self.channel)


class NotificationManager(models.Manager):
    def send(self, *,
             channel: str | uuid.UUID | NotificationChannel,
             users: Iterable[CremeUser],
             content: notification.NotificationContent,
             level: Notification.Level | None = None,
             extra_data: dict | None = None,
             ) -> list[Notification]:
        """Create as much as needed Notification instances for some Users,
        by respecting their own configuration for the given channel.

        @return The created Notification instances.
                BEWARE: the IDs/PKs are only set on database engine which manage it
                (currently only PostgreSQL); see the documentation of bulk_create().
        """
        if isinstance(channel, str | uuid.UUID):
            channel = NotificationChannel.objects.get_for_uuid(channel)

        unique_users = {}
        for user in users:
            if user.is_team:
                unique_users.update(user.teammates)
            else:
                unique_users[user.id] = user

        config_items = {
            config_item.user_id: config_item
            for config_item in NotificationChannelConfigItem.objects.bulk_get(
                channels=[channel], users=unique_users.values(),
            )
        }

        level = level or self.model.Level.NORMAL
        notifications = self.bulk_create([
            self.model(
                channel=channel, user=user, output=output, content=content,
                level=level, extra_data=extra_data or {},
            )
            for user in unique_users.values()
            for output in config_items[user.id].outputs
        ])

        # NB: even if the job is run before the SQL transaction is finished
        #     (& so no notification with emails to send is found), the wake-up
        #     date is computed again just after the execution, so the SQL server
        #     should have enough time to finish the transaction (so we'll probably
        #     avoid to wait <settings.PSEUDO_PERIOD> before the emails are sent).
        OUTPUT_EMAIL = notification.OUTPUT_EMAIL
        if any(
            OUTPUT_EMAIL in config_item.outputs
            for config_item in config_items.values()
        ):
            from .. import creme_jobs
            creme_jobs.notification_emails_sender_type.refresh_job()

        return notifications

    send.alters_data = True


class Notification(models.Model):
    """Contains the notification for a User on an output."""
    class Level(models.IntegerChoices):
        LOW    = 1, pgettext_lazy('creme_core-notif', 'Low'),
        NORMAL = 2, pgettext_lazy('creme_core-notif', 'Normal'),
        HIGH   = 3, pgettext_lazy('creme_core-notif', 'High'),

    id = models.BigAutoField(primary_key=True)
    channel = models.ForeignKey(
        NotificationChannel,
        verbose_name=_('Channel'), on_delete=models.PROTECT, related_name='notifications',
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created = models.DateTimeField(verbose_name=_('Creation date'), auto_now_add=True)
    output = models.CharField(max_length=32)
    content_id = models.CharField(max_length=48)  # TODO: check the length in generate_id()?
    content_data = models.JSONField(default=dict)
    level = models.PositiveSmallIntegerField(
        verbose_name=_('Level'), choices=Level, default=Level.NORMAL,
    )
    discarded = models.DateTimeField(null=True)
    extra_data = models.JSONField(default=dict)

    objects = NotificationManager()

    creation_label = _('Create a notification')
    save_label     = _('Send the notification')

    class Meta:
        app_label = 'creme_core'
        # verbose_name = _('Notification')
        # verbose_name_plural = _('Notifications')
        ordering = ('-id',)

    def __repr__(self):
        return (
            f'Notification('
            f'channel={self.channel.id}, '
            f'output="{self.output}", '
            f'content_id="{self.content_id}", '
            f'content_data={self.content_data}, '
            f'level={self.level}, '
            f'discarded={self.discarded}, '
            f'extra_data={self.extra_data}'
            f')'
        )

    @property
    def content(self) -> notification.NotificationContent:
        if not self.content_id:
            raise ValueError('No content ID is set.')

        return notification.notification_registry.get_content_class(
            content_id=self.content_id, output=self.output,
        ).from_dict(self.content_data)

    @content.setter
    def content(self, value: notification.NotificationContent):
        self.content_id = value.id
        self.content_data = value.as_dict()

    def to_dict(self, user: CremeUser) -> dict:
        content = self.content

        return {
            'id': self.id,
            'channel': str(self.channel),
            'created': dt_to_ISO8601(self.created),
            'level': self.level,
            'subject': content.get_subject(user=user),
            'body': content.get_html_body(user=user) or content.get_body(user=user),
        }
