################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2022-2025  Hybird
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

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core import models as core_models
from creme.creme_core.models import fields as core_fields
from creme.creme_core.utils.crypto import SymmetricEncrypter
from creme.emails.constants import SUBJECT_LENGTH

logger = logging.getLogger(__name__)


class EmailSyncConfigItem(core_models.CremeModel):
    class Type(models.IntegerChoices):
        POP  = 1, 'POP',
        IMAP = 2, 'IMAP',

    type = models.PositiveSmallIntegerField(choices=Type, default=Type.POP)

    default_user = core_fields.CremeUserForeignKey(
        verbose_name=_('Default owner'), null=True, blank=True,
        help_text=_(
            'If no user corresponding to an email address is found (in the '
            'fields "From", "To", "CC" or "BCC") to be the owner of the email, '
            'this user is used as default one.\n'
            'Beware: if *No default user* is selected, emails with no address '
            'related to a user are just dropped.'
        ),
    )

    host = models.CharField(_('Server URL'), max_length=100, help_text=_('E.g. pop.mydomain.org'))
    username = models.CharField(  # TODO: EmailField?
        # max_length=254 to be compliant with RFCs 3696 and 5321
        _('Username'), max_length=254, help_text=_('E.g. me@mydomain.org'),
    )
    encoded_password = models.CharField(_('Password'), max_length=128, editable=False)
    port = models.PositiveIntegerField(
        _('Port'),
        null=True, blank=True,
        help_text=_('Leave empty to use the default port'),
    )
    use_ssl = models.BooleanField(_('Use SSL'), default=True)

    keep_attachments = models.BooleanField(
        _('Keep the attachments'),
        default=True,
        help_text=_('Attachments are converted to real Documents when the email is accepted.'),
    )

    creation_label = pgettext_lazy('emails', 'Create a server configuration')
    save_label = _('Save the configuration')

    class Meta:
        app_label = 'emails'
        # verbose_name = _('...')
        # verbose_name_plural = _('...')

    def get_edit_absolute_url(self):
        return reverse('emails__edit_sync_config_item', args=(self.id,))

    def _password_encrypter(self):
        return SymmetricEncrypter(salt=self.password_salt)

    @property
    def password(self) -> str:
        try:
            return self._password_encrypter().decrypt(
                self.encoded_password.encode()
            ).decode()
        except SymmetricEncrypter.Error as e:
            logger.critical(
                'creme.emails.models.synchronization: '
                'issue with password of EmailSyncConfigItem with id=%s: %s',
                self.id, e,
            )
            return ''

    @password.setter
    def password(self, password: str):
        self.encoded_password = self._password_encrypter().encrypt(
            password.encode()
        ).decode()

    @property
    def password_salt(self):
        cls = self.__class__
        return f'{cls.__module__}.{cls.__name__}'


class EmailToSync(core_models.CremeModel):
    user = core_fields.CremeUserForeignKey(verbose_name=_('Owner'))

    subject   = models.CharField(_('Subject'), max_length=SUBJECT_LENGTH)
    body      = models.TextField(_('Body'))
    body_html = core_fields.UnsafeHTMLField(_('Body (HTML)'))
    date      = models.DateTimeField(_('Reception date'), null=True, editable=False)

    attachments = models.ManyToManyField(core_models.FileRef, verbose_name=_('Attachments'))

    class Meta:
        app_label = 'emails'
        # verbose_name = _('...')
        # verbose_name_plural = _('...')


class EmailToSyncPerson(core_models.CremeModel):
    class Type(models.IntegerChoices):
        SENDER    = 1, 'Sender',
        RECIPIENT = 2, 'Recipient',

    type = models.PositiveSmallIntegerField(
        choices=Type, default=Type.RECIPIENT, editable=False,
    )
    email_to_sync = models.ForeignKey(
        EmailToSync,
        related_name='related_persons', on_delete=models.CASCADE, editable=False,
    )
    email = models.EmailField(editable=False)
    # NB: only one instance is mark as "main" ; it's email address is used in
    #     the created EntityEmail (see the view 'EmailToSyncAcceptation').
    is_main = models.BooleanField(default=False, editable=False)

    entity_ctype = core_fields.EntityCTypeForeignKey(
        null=True, related_name='+', editable=False,
    )
    entity = models.ForeignKey(
        core_models.CremeEntity,
        null=True, on_delete=models.SET_NULL, related_name='+', editable=False,
    )
    person = core_fields.RealEntityForeignKey(
        ct_field='entity_ctype', fk_field='entity',
    )

    class Meta:
        app_label = 'emails'
        verbose_name = _('Sender/recipient to synchronize')
        verbose_name_plural = _('Senders/recipients to synchronize')

    def __str__(self):
        return self.email

    def get_edit_absolute_url(self):
        return reverse('emails__edit_email_to_sync_person', args=(self.id,))
