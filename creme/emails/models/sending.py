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

from json import loads as json_load
import logging
from time import sleep

from django.conf import settings
from django.core.mail import send_mail, get_connection
from django.db import IntegrityError
from django.db.models import (ForeignKey, DateTimeField, PositiveSmallIntegerField,
        EmailField, CharField, TextField, ManyToManyField, SET_NULL, CASCADE)
from django.db.transaction import atomic
from django.template import Template, Context
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _, gettext, pgettext, pgettext_lazy

from creme.creme_core.models import CremeModel, CremeEntity

from ..constants import MAIL_STATUS_NOTSENT, MAIL_STATUS_SENDINGERROR
from ..utils import generate_id, EMailSender, ImageFromHTMLError

from .mail import _Email, ID_LENGTH
from .signature import EmailSignature


logger = logging.getLogger(__name__)

# TODO: move to constants.py ???
SENDING_TYPE_IMMEDIATE = 1
SENDING_TYPE_DEFERRED  = 2

SENDING_TYPES = {
    SENDING_TYPE_IMMEDIATE: _('Immediate'),
    SENDING_TYPE_DEFERRED:  pgettext_lazy('emails-sending', 'Deferred'),
}

SENDING_STATE_DONE       = 1
SENDING_STATE_INPROGRESS = 2
SENDING_STATE_PLANNED    = 3
SENDING_STATE_ERROR      = 4

SENDING_STATES = {
    SENDING_STATE_DONE:       pgettext_lazy('emails-sending', 'Done'),
    SENDING_STATE_INPROGRESS: _('In progress'),
    SENDING_STATE_PLANNED:    pgettext_lazy('emails-sending', 'Planned'),
    SENDING_STATE_ERROR:      _('Error during sending'),
}


class EmailSending(CremeModel):
    sender        = EmailField(_('Sender address'), max_length=100)
    campaign      = ForeignKey(settings.EMAILS_CAMPAIGN_MODEL, on_delete=CASCADE,
                               verbose_name=pgettext_lazy('emails', 'Related campaign'),
                               related_name='sendings_set', editable=False,
                              )
    type          = PositiveSmallIntegerField(verbose_name=_('Sending type'),
                                              choices=SENDING_TYPES.items(),
                                              default=SENDING_TYPE_IMMEDIATE,
                                             )
    sending_date  = DateTimeField(_('Sending date'))
    state         = PositiveSmallIntegerField(verbose_name=_('Sending state'),
                                              editable=False,
                                              choices=SENDING_STATES.items(),
                                              default=SENDING_STATE_PLANNED,
                                             )

    subject     = CharField(_('Subject'), max_length=100, editable=False)
    body        = TextField(_('Body'), editable=False)
    body_html   = TextField(_('Body (HTML)'), null=True, editable=False)
    signature   = ForeignKey(EmailSignature, verbose_name=_('Signature'),
                             null=True, editable=False, on_delete=SET_NULL,
                            )
    attachments = ManyToManyField(settings.DOCUMENTS_DOCUMENT_MODEL,
                                  verbose_name=_('Attachments'), editable=False,
                                 )

    creation_label = pgettext_lazy('emails', 'Create a sending')
    save_label     = pgettext_lazy('emails', 'Save the sending')

    class Meta:
        app_label = 'emails'
        verbose_name = _('Email campaign sending')
        verbose_name_plural = _('Email campaign sendings')

    def __str__(self):
        return pgettext('emails', 'Sending of «{campaign}» on {date}').format(
                    campaign=self.campaign,
                    date=date_format(localtime(self.sending_date), 'DATETIME_FORMAT'),
                )

    def get_mails(self):  # TODO: remove
        return self.mails_set.all()

    def get_unsent_mails_count(self):
        return self.mails_set.filter(status__in=[MAIL_STATUS_NOTSENT, MAIL_STATUS_SENDINGERROR]).count()

    def get_absolute_url(self):
        # return self.campaign.get_absolute_url()
        return reverse('emails__view_sending', args=(self.id,))

    def get_related_entity(self):  # For generic views
        return self.campaign

    def send_mails(self):
        try:
            sender = LightWeightEmailSender(sending=self)
        except ImageFromHTMLError as e:
            send_mail(gettext('[CremeCRM] Campaign email sending error.'),
                      gettext("Emails in the sending of the campaign «{campaign}» on {date} weren't sent "
                              "because the image «{image}» is no longer available in the template.").format(
                            campaign=self.campaign,
                            date=self.sending_date,
                            image=e.filename,
                      ),
                      settings.EMAIL_HOST_USER,
                      [self.campaign.user.email or settings.DEFAULT_USER_EMAIL],
                      fail_silently=False,
                     )

            return SENDING_STATE_ERROR

        connection = get_connection(host=settings.EMAILCAMPAIGN_HOST,
                                    port=settings.EMAILCAMPAIGN_PORT,
                                    username=settings.EMAILCAMPAIGN_HOST_USER,
                                    password=settings.EMAILCAMPAIGN_PASSWORD,
                                    use_tls=settings.EMAILCAMPAIGN_USE_TLS,
                                   )

        mails_count   = 0
        one_mail_sent = False
        SENDING_SIZE  = getattr(settings, 'EMAILCAMPAIGN_SIZE', 40)
        SLEEP_TIME    = getattr(settings, 'EMAILCAMPAIGN_SLEEP_TIME', 2)

        for mail in LightWeightEmail.objects.filter(sending=self):
            if sender.send(mail, connection=connection):
                mails_count += 1
                one_mail_sent = True
                logger.debug('Mail sent to %s', mail.recipient)

            if mails_count > SENDING_SIZE:
                logger.debug('Sending: waiting timeout')

                mails_count = 0
                sleep(SLEEP_TIME)  # Avoiding the mail to be classed as spam

        if not one_mail_sent:
            return SENDING_STATE_ERROR

        # TODO: close the connection ??


class LightWeightEmail(_Email):
    """Used by campaigns.
    id is a unique generated string in order to avoid stats hacking.
    """
    id               = CharField(_('Email ID'), primary_key=True, max_length=ID_LENGTH, editable=False)
    sending          = ForeignKey(EmailSending, verbose_name=_('Related sending'),
                                  related_name='mails_set', editable=False,
                                  on_delete=CASCADE,
                                 )
    recipient_entity = ForeignKey(CremeEntity, null=True, related_name='received_lw_mails',
                                  editable=False, on_delete=CASCADE,
                                 )

    class Meta:
        app_label = 'emails'
        verbose_name = _('Email of campaign')
        verbose_name_plural = _('Emails of campaign')

    def _render_body(self, sending_body):
        body = self.body

        try:
            return Template(sending_body).render(Context(json_load(body) if body else {}))
        except Exception as e:
            logger.debug('Error in LightWeightEmail._render_body(): %s', e)
            return ''

    @property
    def rendered_body(self):
        return self._render_body(self.sending.body)

    @property
    def rendered_body_html(self):
        return self._render_body(self.sending.body_html)

    def get_related_entity(self):  # For generic views
        return self.sending.campaign

    def genid_n_save(self):
        while True:
            self.id = generate_id()

            try:
                with atomic():
                    self.save(force_insert=True)
            except IntegrityError:  # A mail with this id already exists
                logger.debug('Mail id already exists: %s', self.id)
                self.pk = None
            else:
                return


class LightWeightEmailSender(EMailSender):
    def __init__(self, sending):
        super().__init__(body=sending.body,
                         body_html=sending.body_html,
                         signature=sending.signature,
                         attachments=sending.attachments.all(),
                        )
        self._sending = sending
        self._body_template = Template(self._body)
        self._body_html_template = Template(self._body_html)

    def get_subject(self, mail):
        return self._sending.subject

    def _process_bodies(self, mail):
        body = mail.body
        context = Context(json_load(body) if body else {})

        return self._body_template.render(context), self._body_html_template.render(context)
