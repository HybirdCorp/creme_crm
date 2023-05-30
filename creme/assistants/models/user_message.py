################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2023  Hybird
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
from functools import partial

from django.db import models
from django.db.transaction import atomic
from django.utils.timezone import now
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

import creme.creme_core.models as core_models
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
    email_sent = models.BooleanField(default=False)

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

    creation_label = _('Create a message')
    save_label     = _('Save the message')

    class Meta:
        app_label = 'assistants'
        verbose_name = _('User message')
        verbose_name_plural = _('User messages')

    def __str__(self):
        return self.title

    @classmethod
    @atomic
    def create_messages(cls, users, title, body, priority_id, sender, entity):
        """Create UserMessages instances to sent to several users.
        Notice that teams are treated as several Users.
        @param users: A sequence of CremeUser objects ; duplicates are removed.
        """
        users_map = {}
        for user in users:
            if user.is_team:
                users_map.update(user.teammates)
            else:
                users_map[user.id] = user

        build_msg = partial(
            cls,
            creation_date=now(),
            title=title,
            body=body,
            priority_id=priority_id,
            sender=sender,
            real_entity=entity,
        )
        cls.objects.bulk_create(
            build_msg(recipient=user) for user in users_map.values()
        )

        from ..creme_jobs import usermessages_send_type

        usermessages_send_type.refresh_job()

    # TODO: move code to Job?
    @classmethod
    def send_mails(cls, job):
        from django.conf import settings
        from django.core.mail import EmailMessage, get_connection

        user_messages = [*cls.objects.filter(email_sent=False)]

        if not user_messages:
            return

        subject_format = gettext('User message from {software}: {title}')
        body_format    = gettext('{user} sent you the following message:\n{body}')
        EMAIL_SENDER   = settings.EMAIL_SENDER

        messages = [
            EmailMessage(
                subject_format.format(software=settings.SOFTWARE_LABEL, title=msg.title),
                body_format.format(user=msg.sender, body=msg.body),
                EMAIL_SENDER,
                [msg.recipient.email],
            ) for msg in user_messages if msg.recipient.email
        ]

        try:
            with get_connection() as connection:
                connection.send_messages(messages)
        except Exception as e:
            logger.critical('Error while sending user-messages emails (%s)', e)
            core_models.JobResult.objects.create(
                job=job,
                messages=[
                    gettext('An error occurred while sending emails'),
                    gettext('Original error: {}').format(e),
                ],
            )

        cls.objects.filter(
            pk__in=[m.id for m in user_messages],
        ).update(email_sent=True)
