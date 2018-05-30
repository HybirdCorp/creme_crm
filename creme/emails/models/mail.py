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

import logging

from django.conf import settings
from django.db import IntegrityError
from django.db.models import (PositiveIntegerField, PositiveSmallIntegerField,
        CharField, TextField, DateTimeField, ForeignKey, ManyToManyField, CASCADE)
from django.db.transaction import atomic
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.models import CremeModel, CremeEntity
from creme.creme_core.models.fields import UnsafeHTMLField

from .. import constants
from ..utils import generate_id, EMailSender
from .signature import EmailSignature


logger = logging.getLogger(__name__)
ID_LENGTH = 32


class _Email(CremeModel):
    reads          = PositiveIntegerField(_(u'Number of reads'), null=True,
                                          default=0, editable=False,
                                         )
    status         = PositiveSmallIntegerField(_(u'Status'), editable=False,
                                               default=constants.MAIL_STATUS_NOTSENT,
                                               choices=constants.MAIL_STATUS.items(),
                                              )

    sender         = CharField(_(u'Sender'), max_length=100)
    recipient      = CharField(_(u'Recipient'), max_length=100)
    subject        = CharField(_(u'Subject'), max_length=100, blank=True)
    body           = TextField(_(u'Body'))
    sending_date   = DateTimeField(_(u'Sending date'), null=True, editable=False)
    reception_date = DateTimeField(_(u'Reception date'), null=True, editable=False)

    class Meta:
        abstract = True
        manager_inheritance_from_future = True
        app_label = 'emails'

    def __unicode__(self):
        return u"Mail<from: %s> <to: %s> <sent: %s> <id: %s>" % (
                    self.sender, self.recipient, self.sending_date, self.id,
                )

    @property
    def sent(self):
        return self.status == constants.MAIL_STATUS_SENT

    @property
    def synchronised(self):
        return self.status in constants.MAIL_SYNC_STATUSES


class AbstractEntityEmail(_Email, CremeEntity):
    identifier  = CharField(_(u'Email ID'), unique=True, max_length=ID_LENGTH,
                            editable=False,
                            default=generate_id,  # TODO: lambda for this
                           )
    body_html   = UnsafeHTMLField(_(u'Body (HTML)'))
    signature   = ForeignKey(EmailSignature, verbose_name=_(u'Signature'), blank=True, null=True, on_delete=CASCADE) ##merge with body ????
    attachments = ManyToManyField(settings.DOCUMENTS_DOCUMENT_MODEL, verbose_name=_(u'Attachments'), blank=True)

    creation_label = _(u'Create an email')
    save_label     = _(u'Save the email')
    sending_label  = _(u'Send the email')

    class Meta:
        abstract = True
        manager_inheritance_from_future = True
        app_label = 'emails'
        verbose_name = _(u'Email')
        verbose_name_plural = _(u'Emails')
        ordering = ('-sending_date',)

    def genid_n_save(self):
        while True:  # TODO: xrange(10000) to avoid infinite loop ??
            self.identifier = generate_id()

            try:
                with atomic():
                    self.save(force_insert=True)
            except IntegrityError:  # A mail with this id already exists
                logger.debug('Mail id already exists: %s', self.identifier)
                self.pk = None
            else:
                return

    def __unicode__(self):
        return ugettext(u'EMail <from: %(from)s> <to: %(to)s> <status: %(status)s>') % {
                                'from':   self.sender,
                                'to':     self.recipient,
                                'status': self.get_status_display(),
                            }

    def get_absolute_url(self):
        return reverse('emails__view_email', args=(self.pk,))

    @staticmethod
    def get_clone_absolute_url():
        return ''  # Cannot be cloned

    @staticmethod
    def get_lv_absolute_url():
        return reverse('emails__list_emails')

    # TODO: in a manager ?
    @classmethod
    def create_n_send_mail(cls, sender, recipient, subject, user, body, body_html=u'', signature=None, attachments=None):
        email = cls(sender=sender,
                    recipient=recipient,
                    subject=subject,
                    body=body,
                    body_html=body_html,
                    signature=signature,
                    user=user,
                   )
        email.genid_n_save()

        if attachments:
            email.attachments.set(attachments)

        email.send()

        return email

    def _pre_save_clone(self, source):
        self.genid_n_save()

    def restore(self):
        CremeEntity.restore(self)

        # TODO: in a signal handler instead ?
        #       (we need a restore signal, or an official "backup" feature -- see HistoryLine)
        if self.status in (constants.MAIL_STATUS_NOTSENT, constants.MAIL_STATUS_SENDINGERROR):
            # TODO: regroup the 'refresh' message, to avoid flooding the job manager
            from ..creme_jobs import entity_emails_send_type

            entity_emails_send_type.refresh_job()

    def send(self):
        sender = EntityEmailSender(body=self.body,
                                   body_html=self.body_html,
                                   signature=self.signature,
                                   attachments=self.attachments.all(),
                                  )

        if sender.send(self):
            logger.debug("Mail sent to %s", self.recipient)


class EntityEmail(AbstractEntityEmail):
    class Meta(AbstractEntityEmail.Meta):
        swappable = 'EMAILS_EMAIL_MODEL'


class EntityEmailSender(EMailSender):
    def get_subject(self, mail):
        return mail.subject

