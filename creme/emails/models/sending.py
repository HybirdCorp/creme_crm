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

from __future__ import annotations

import logging
from json import loads as json_load
from time import sleep

from django.conf import settings
from django.core.mail import get_connection, send_mail
from django.db import IntegrityError, models
from django.db.transaction import atomic
from django.template import Context, Template
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.timezone import localtime
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext, pgettext_lazy

import creme.creme_core.models.fields as core_fields
from creme.creme_core.models import CremeEntity, CremeModel
from creme.creme_core.utils.crypto import SymmetricEncrypter

from ..utils import EMailSender, ImageFromHTMLError, generate_id
from .mail import ID_LENGTH, _Email
from .signature import EmailSignature

logger = logging.getLogger(__name__)


class LightWeightEmailSender(EMailSender):
    def __init__(self, sending: EmailSending):
        super().__init__(
            sender_address=sending.sender,
            body=sending.body,
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

        return (
            self._body_template.render(context),
            self._body_html_template.render(context),
        )


# TODO: factorise with EmailSyncConfigItem
class EmailSendingConfigItem(CremeModel):
    name = models.CharField(
        _('Name'),
        max_length=100,
        help_text=_('Name displayed to users when selecting a configuration'),
        unique=True,
    )
    host = models.CharField(_('Server URL'), max_length=100, help_text=_('E.g. smtp.mydomain.org'))
    username = models.CharField(
        # max_length=254 to be compliant with RFCs 3696 and 5321
        _('Username'), max_length=254, blank=True, help_text=_('E.g. me@mydomain.org'),
    )
    encoded_password = models.CharField(
        ('Password'), max_length=128, editable=False,
    )
    port = models.PositiveIntegerField(
        _('Port'),
        null=True, blank=True,
        help_text=_('Leave empty to use the default port'),
    )
    use_tls = models.BooleanField(_('Use TLS'), default=True)
    default_sender = models.EmailField(
        _('Default sender'),
        blank=True,
        help_text=_(
            'If you fill this field with an email address, this address will be '
            'used as the default value in the form for the field «Sender» when '
            'sending a campaign.'
        ),
    )

    creation_label = pgettext_lazy('emails', 'Create a server configuration')
    save_label = _('Save the configuration')

    class Meta:
        app_label = 'emails'
        verbose_name = _('SMTP configuration')  # Used for uniqueness errors
        # verbose_name_plural = _('...')
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_edit_absolute_url(self):
        return reverse('emails__edit_sending_config_item', args=(self.id,))

    def _password_encrypter(self):
        return SymmetricEncrypter(salt=self.password_salt)

    @property
    def password(self):
        encoded_password = self.encoded_password

        if encoded_password:
            try:
                return self._password_encrypter().decrypt(
                    self.encoded_password.encode()
                ).decode()
            except SymmetricEncrypter.Error as e:
                logger.critical(
                    'issue with password of EmailSendingConfigItem with id=%s: %s',
                    self.id, e,
                )

        return ''

    @password.setter
    def password(self, password):
        self.encoded_password = self._password_encrypter().encrypt(
            password.encode()
        ).decode() if password else ''

    @property
    def password_salt(self):
        cls = self.__class__
        return f'{cls.__module__}.{cls.__name__}'


class EmailSending(CremeModel):
    class Type(models.IntegerChoices):
        IMMEDIATE = 1, _('Immediate'),
        DEFERRED  = 2, pgettext_lazy('emails-sending', 'Deferred'),

    class State(models.IntegerChoices):
        DONE        = 1, pgettext_lazy('emails-sending', 'Done'),
        IN_PROGRESS = 2, _('In progress'),
        PLANNED     = 3, pgettext_lazy('emails-sending', 'Planned'),
        ERROR       = 4, _('Error during sending'),

    # Not viewable by users, For administrators currently.
    created = core_fields.CreationDateTimeField().set_tags(viewable=False)
    modified = core_fields.ModificationDateTimeField().set_tags(viewable=False)

    config_item = models.ForeignKey(
        EmailSendingConfigItem,
        verbose_name=_('SMTP server'), null=True, on_delete=models.SET_NULL,
    )
    sender = models.EmailField(_('Sender address'), max_length=100)
    campaign = models.ForeignKey(
        settings.EMAILS_CAMPAIGN_MODEL,
        verbose_name=pgettext_lazy('emails', 'Related campaign'),
        on_delete=models.CASCADE, related_name='sendings_set', editable=False,
    )
    type = models.PositiveSmallIntegerField(
        verbose_name=_('Sending type'),
        choices=Type, default=Type.IMMEDIATE,
    )
    sending_date = models.DateTimeField(_('Sending date'))
    state = models.PositiveSmallIntegerField(
        verbose_name=_('Sending state'), editable=False,
        choices=State, default=State.PLANNED,
    )

    subject   = models.CharField(_('Subject'), max_length=100, editable=False)
    body      = models.TextField(_('Body'), editable=False)
    body_html = models.TextField(_('Body (HTML)'), null=True, editable=False)

    signature = models.ForeignKey(
        EmailSignature,
        verbose_name=_('Signature'),
        null=True, editable=False, on_delete=models.SET_NULL,
    )
    attachments = models.ManyToManyField(
        settings.DOCUMENTS_DOCUMENT_MODEL,
        verbose_name=_('Attachments'), editable=False,
    )

    creation_label = pgettext_lazy('emails', 'Create a sending')
    save_label     = pgettext_lazy('emails', 'Save the sending')

    email_sender_cls = LightWeightEmailSender

    class Meta:
        app_label = 'emails'
        verbose_name = _('Email campaign sending')
        verbose_name_plural = _('Email campaign sendings')

    def __str__(self):
        return pgettext('emails', 'Sending of «{campaign}» on {date}').format(
            campaign=self.campaign,
            date=date_format(localtime(self.sending_date), 'DATETIME_FORMAT'),
        )

    def get_absolute_url(self):
        return reverse('emails__view_sending', args=(self.id,))

    def get_edit_absolute_url(self):
        return reverse('emails__edit_sending', args=(self.id,))

    def get_related_entity(self):  # For generic views
        return self.campaign

    def send_mails(self):
        config_item = self.config_item
        if config_item is None:
            logger.warning('It seems the config of an active EmailSending has been removed.')
            return self.State.ERROR

        try:
            sender_obj = self.email_sender_cls(sending=self)
        except ImageFromHTMLError as e:
            send_mail(
                gettext('[{software}] Campaign email sending error.').format(
                    software=settings.SOFTWARE_LABEL,
                ),
                gettext(
                    "Emails in the sending of the campaign «{campaign}» on {date} weren't sent "
                    "because the image «{image}» is no longer available in the template."
                ).format(
                    campaign=self.campaign,
                    date=self.sending_date,
                    image=e.filename,
                ),
                settings.EMAIL_HOST_USER,
                [self.campaign.user.email or settings.DEFAULT_USER_EMAIL],
                fail_silently=False,
            )

            return self.State.ERROR

        connection = get_connection(
            host=config_item.host,
            port=config_item.port,
            username=config_item.username,
            password=config_item.password,
            use_tls=config_item.use_tls,
        )

        mails_count = 0
        one_mail_sent = False
        SENDING_SIZE = getattr(settings, 'EMAILCAMPAIGN_SIZE', 40)
        SLEEP_TIME = getattr(settings, 'EMAILCAMPAIGN_SLEEP_TIME', 2)

        for mail in LightWeightEmail.objects.filter(sending=self):
            if sender_obj.send(mail, connection=connection):
                mails_count += 1
                one_mail_sent = True
                logger.debug('Mail sent to %s', mail.recipient)

            if mails_count > SENDING_SIZE:
                logger.debug('Sending: waiting timeout')

                mails_count = 0
                sleep(SLEEP_TIME)  # Avoiding the mail to be classed as spam

        if not one_mail_sent:
            return self.State.ERROR

        # TODO: close the connection ??

    send_mails.alters_data = True

    @property
    def unsent_mails(self):
        Status = _Email.Status

        return self.mails_set.filter(status__in=[Status.NOT_SENT, Status.SENDING_ERROR])


class LightWeightEmail(_Email):
    """Used by campaigns.
    id is a uniquely generated string in order to avoid stats hacking.
    """
    id = models.CharField(_('Email ID'), primary_key=True, max_length=ID_LENGTH, editable=False)
    sending = models.ForeignKey(
        EmailSending, verbose_name=_('Related sending'),
        related_name='mails_set', editable=False, on_delete=models.CASCADE,
    )

    recipient_ctype = core_fields.EntityCTypeForeignKey(
        null=True, related_name='+', editable=False,
    )
    recipient_entity = models.ForeignKey(
        CremeEntity,
        null=True, on_delete=models.CASCADE,
        related_name='received_lw_mails', editable=False,
    )
    real_recipient = core_fields.RealEntityForeignKey(
        ct_field='recipient_ctype', fk_field='recipient_entity',
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
            except IntegrityError:
                logger.debug('Mail ID already exists: %s', self.id)
                self.pk = None
            else:
                return

    genid_n_save.alters_data = True
