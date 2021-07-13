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

import logging

from django.conf import settings
from django.db import models
from django.db.transaction import atomic
from django.db.utils import IntegrityError
from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.models import CremeEntity, CremeModel
from creme.creme_core.models.fields import UnsafeHTMLField

from .. import utils  # constants
from .signature import EmailSignature

logger = logging.getLogger(__name__)
ID_LENGTH = 32


class _Email(CremeModel):
    class Status(models.IntegerChoices):
        SENT                 = 1, pgettext_lazy('emails', 'Sent'),
        NOT_SENT             = 2, pgettext_lazy('emails', 'Not sent'),
        SENDING_ERROR        = 3, _('Sending error'),
        SYNCHRONIZED         = 4, pgettext_lazy('emails', 'Synchronized'),
        SYNCHRONIZED_SPAM    = 5, _('Synchronized - Marked as SPAM'),
        SYNCHRONIZED_WAITING = 6, _('Synchronized - Untreated'),

    SYNCHRONIZATION_STATUSES = {
        Status.SYNCHRONIZED,
        Status.SYNCHRONIZED_SPAM,
        Status.SYNCHRONIZED_WAITING,
    }

    reads = models.PositiveIntegerField(
        _('Number of reads'), null=True, default=0, editable=False,
    )
    status = models.PositiveSmallIntegerField(
        _('Status'), editable=False,
        # choices=constants.MAIL_STATUS.items(), default=constants.MAIL_STATUS_NOTSENT,
        choices=Status.choices, default=Status.NOT_SENT,
    )

    sender    = models.CharField(_('Sender'), max_length=100)
    recipient = models.CharField(_('Recipient'), max_length=100)
    subject   = models.CharField(_('Subject'), max_length=100, blank=True)
    body      = models.TextField(_('Body'))

    sending_date   = models.DateTimeField(_('Sending date'), null=True, editable=False)
    reception_date = models.DateTimeField(_('Reception date'), null=True, editable=False)

    class Meta:
        abstract = True
        # manager_inheritance_from_future = True
        app_label = 'emails'

    def __str__(self):
        return (
            f'Mail<from: {self.sender}> '
            f'<to: {self.recipient}> '
            f'<sent: {self.sending_date}> '
            f'<id: {self.id}>'
        )

    @property
    def sent(self):
        # return self.status == constants.MAIL_STATUS_SENT
        return self.status == self.Status.SENT

    @property
    def synchronised(self):
        # return self.status in constants.MAIL_SYNC_STATUSES
        return self.status in self.SYNCHRONIZATION_STATUSES


class AbstractEntityEmail(_Email, CremeEntity):
    identifier = models.CharField(
        _('Email ID'), unique=True, max_length=ID_LENGTH, editable=False,
        default=utils.generate_id,  # TODO: lambda for this
    )
    body_html = UnsafeHTMLField(_('Body (HTML)'))
    signature = models.ForeignKey(
        EmailSignature, verbose_name=_('Signature'),
        blank=True, null=True, on_delete=models.SET_NULL,
    )  # TODO: merge with body ????
    attachments = models.ManyToManyField(
        settings.DOCUMENTS_DOCUMENT_MODEL, verbose_name=_('Attachments'), blank=True,
    )

    creation_label = _('Create an email')
    save_label     = _('Save the email')
    sending_label  = _('Send the email')

    class Meta:
        abstract = True
        # manager_inheritance_from_future = True
        app_label = 'emails'
        verbose_name = pgettext_lazy('emails', 'Email')
        verbose_name_plural = pgettext_lazy('emails', 'Emails')
        ordering = ('-sending_date',)

    def genid_n_save(self):
        for __ in range(10000):  # NB: avoid infinite loop
            self.identifier = utils.generate_id()

            try:
                with atomic():
                    self.save(force_insert=True)
            except IntegrityError:  # A mail with this id already exists
                logger.debug('Mail id already exists: %s', self.identifier)
                self.pk = None
            else:
                return

    def __str__(self):
        return gettext('EMail <from: {sender}> <to: {to}> <status: {status}>').format(
            sender=self.sender,
            to=self.recipient,
            status=self.get_status_display(),
        )

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
    def create_n_send_mail(cls, sender, recipient, subject, user, body,
                           body_html='', signature=None, attachments=None):
        email = cls(
            sender=sender,
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
        # if self.status in (constants.MAIL_STATUS_NOTSENT, constants.MAIL_STATUS_SENDINGERROR):
        if self.status in (self.Status.NOT_SENT, self.Status.SENDING_ERROR):
            # TODO: regroup the 'refresh' message, to avoid flooding the job manager
            from ..creme_jobs import entity_emails_send_type

            entity_emails_send_type.refresh_job()

    def send(self):
        sender = EntityEmailSender(
            body=self.body,
            body_html=self.body_html,
            signature=self.signature,
            attachments=self.attachments.all(),
        )

        if sender.send(self):
            logger.debug('Mail sent to %s', self.recipient)


class EntityEmail(AbstractEntityEmail):
    class Meta(AbstractEntityEmail.Meta):
        swappable = 'EMAILS_EMAIL_MODEL'


class EntityEmailSender(utils.EMailSender):
    def get_subject(self, mail):
        return mail.subject
