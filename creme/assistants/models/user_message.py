# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from functools import partial
import logging

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import (CharField, BooleanField, TextField, DateTimeField,
        ForeignKey, PositiveIntegerField, PROTECT, CASCADE)
from django.db.transaction import atomic
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext_lazy

from creme.creme_core.models import CremeModel, JobResult  # CremeEntity
from creme.creme_core.models.fields import CremeUserForeignKey


logger = logging.getLogger(__name__)


class UserMessagePriority(CremeModel):
    title     = CharField(_(u'Title'), max_length=200)
    is_custom = BooleanField(default=True).set_tags(viewable=False)  # Used by creme_config

    creation_label = pgettext_lazy('assistants-messaqe_priority', u'Create a priority')

    class Meta:
        app_label = 'assistants'
        verbose_name = _(u'Priority of user message')
        verbose_name_plural = _(u'Priorities of user message')
        ordering = ('title',)

    def __str__(self):
        return self.title


class UserMessage(CremeModel):
    title         = CharField(_(u'Title'), max_length=200)
    body          = TextField(_(u'Message body'))
    creation_date = DateTimeField(_(u'Creation date'))
    priority      = ForeignKey(UserMessagePriority, verbose_name=_(u'Priority'), on_delete=PROTECT)
    sender        = CremeUserForeignKey(verbose_name=_(u'Sender'),
                                        related_name='sent_assistants_messages_set',
                                       )
    recipient     = CremeUserForeignKey(verbose_name=_(u'Recipient'),
                                        related_name='received_assistants_messages_set',
                                       )

    email_sent = BooleanField(default=False)

    # TODO: use a True ForeignKey to CremeEntity (do not forget to remove the signal handlers)
    entity_content_type = ForeignKey(ContentType, null=True, on_delete=CASCADE)
    entity_id           = PositiveIntegerField(null=True)
    creme_entity        = GenericForeignKey(ct_field="entity_content_type", fk_field="entity_id")

    class Meta:
        app_label = 'assistants'
        verbose_name = _(u'User message')
        verbose_name_plural = _(u'User messages')

    def __str__(self):
        return self.title

    @staticmethod
    def get_messages(entity, user):
        return UserMessage.objects.filter(entity_id=entity.id, recipient=user).select_related('sender')

    @staticmethod
    def get_messages_for_home(user):
        return UserMessage.objects.filter(recipient=user).select_related('sender')

    @staticmethod
    def get_messages_for_ctypes(ct_ids, user):
        return UserMessage.objects.filter(entity_content_type__in=ct_ids, recipient=user).select_related('sender')

    @staticmethod
    @atomic
    def create_messages(users, title, body, priority_id, sender, entity):
        """Create UserMessages instances to sent to several users.
        Notice that teams are treated as several Users.
        @param users A sequence of CremeUser objects ; duplicates are removed.
        """
        users_map = {}
        for user in users:
            if user.is_team:
                users_map.update(user.teammates)
            else:
                users_map[user.id] = user

        build_msg = partial(UserMessage, creation_date=now(),
                            title=title, body=body,
                            priority_id=priority_id,
                            sender=sender, creme_entity=entity,
                           )
        UserMessage.objects.bulk_create(build_msg(recipient=user)
                                            for user in users_map.values()
                                       )

        from ..creme_jobs import usermessages_send_type

        usermessages_send_type.refresh_job()

    @staticmethod
    # def send_mails():
    def send_mails(job):
        from django.conf import settings
        from django.core.mail import EmailMessage, get_connection

        usermessages = list(UserMessage.objects.filter(email_sent=False))

        if not usermessages:
            return

        subject_format = ugettext(u'User message from Creme: {}')
        body_format    = ugettext(u'{user} sent you the following message:\n{body}')
        EMAIL_SENDER   = settings.EMAIL_SENDER

        messages = [EmailMessage(subject_format.format(msg.title),
                                 body_format.format(user=msg.sender, body=msg.body),
                                 EMAIL_SENDER, [msg.recipient.email]
                                )
                        for msg in usermessages if msg.recipient.email
                   ]

        try:
            with get_connection() as connection:
                connection.send_messages(messages)
        except Exception as e:
            logger.critical('Error while sending user-messages emails (%s)', e)
            JobResult.objects.create(job=job,
                                     messages=[ugettext(u'An error occurred while sending emails'),
                                               ugettext(u'Original error: {}').format(e),
                                              ],
                                    )

        # for msg in usermessages:
        #     msg.email_sent = True
        #     msg.save()
        UserMessage.objects.filter(pk__in=[m.id for m in usermessages]) \
                           .update(email_sent=True)
