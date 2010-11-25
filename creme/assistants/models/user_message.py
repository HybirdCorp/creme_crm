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

from django.db.models import CharField, BooleanField, TextField, DateTimeField, BooleanField, ForeignKey, PositiveIntegerField
from django.db.models.signals import pre_delete
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.auth.models import User

from creme_core.models import CremeModel, CremeEntity


class UserMessagePriority(CremeModel):
    title     = CharField(_(u'Title'), max_length=200)
    is_custom = BooleanField(default=True) #used by creme_config

    class Meta:
        app_label = 'assistants'
        verbose_name = _(u'Priority of user message')
        verbose_name_plural = _(u'Priorities of user message')

    def __unicode__(self):
        return self.title


class UserMessage(CremeModel):
    title         = CharField(_(u'Title'), max_length=200)
    body          = TextField(_(u'Message body'))
    creation_date = DateTimeField(_(u"Creation date"))
    priority      = ForeignKey(UserMessagePriority, verbose_name=_(u'Priority'))
    sender        = ForeignKey(User, verbose_name=_(u'Sender'), related_name='sent_assistants_messages_set')
    recipient     = ForeignKey(User, verbose_name=_(u'Recipient'), related_name='received_assistants_messages_set') #, null=True

    email_sent = BooleanField()

    entity_content_type = ForeignKey(ContentType, null=True)
    entity_id           = PositiveIntegerField(null=True)
    creme_entity        = GenericForeignKey(ct_field="entity_content_type", fk_field="entity_id")

    class Meta:
        app_label = 'assistants'
        verbose_name = _(u'User message')
        verbose_name_plural = _(u'User messages')

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
    def send_mails():
        from django.core.mail import EmailMessage, SMTPConnection
        from creme_settings import CREME_EMAIL, CREME_EMAIL_PASSWORD, CREME_EMAIL_SERVER, CREME_EMAIL_PORT, CREME_EMAIL_USERNAME

        usermessages = list(UserMessage.objects.filter(email_sent=False))
        subject_format = ugettext(u'User message from Creme: %s')
        body_format    = ugettext(u'%(user)s send you the following message:\n%(body)s')
        messages = [EmailMessage(subject_format % msg.title,
                                 body_format % {'user': msg.sender, 'body': msg.body},
                                 CREME_EMAIL, [msg.recipient.email]
                                )
                        for msg in usermessages if msg.recipient.email
                   ]

        try:
            SMTPConnection(host=CREME_EMAIL_SERVER,
                           port=CREME_EMAIL_PORT,
                           username=CREME_EMAIL_USERNAME,
                           password=CREME_EMAIL_PASSWORD,
                           use_tls=True
                          ).send_messages(messages)
        except Exception, e:
            raise e

        for msg in usermessages:
            msg.email_sent = True
            msg.save()


#TODO: can delete this with  a WeakForeignKey ??
def dispose_entity_mesages(sender, instance, **kwargs):
    UserMessage.objects.filter(entity_id=instance.id).delete()

pre_delete.connect(dispose_entity_mesages, sender=CremeEntity)
