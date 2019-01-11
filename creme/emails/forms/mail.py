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
from itertools import chain
import logging
import warnings

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.transaction import atomic
from django.forms.fields import EmailField, BooleanField, IntegerField, CharField
from django.forms.widgets import HiddenInput
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext_lazy

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.forms.base import CremeForm, CremeEntityForm, FieldBlockManager
from creme.creme_core.forms.fields import MultiCreatorEntityField, CreatorEntityField
from creme.creme_core.forms.widgets import Label
from creme.creme_core.models import Relation, FieldsConfig

from creme.documents import get_document_model

from creme import persons, emails

from ..constants import REL_SUB_MAIL_RECEIVED, REL_SUB_MAIL_SENDED, MAIL_STATUS_SENDINGERROR
from ..creme_jobs import entity_emails_send_type


logger = logging.getLogger(__name__)
Document      = get_document_model()
Contact       = persons.get_contact_model()
Organisation  = persons.get_organisation_model()
EntityEmail   = emails.get_entityemail_model()
EmailTemplate = emails.get_emailtemplate_model()


class EntityEmailForm(CremeEntityForm):
    """Mails are related to the selected contacts/organisations & the 'current' entity.
    Mails are send to selected contacts/organisations.
    """
    sender = EmailField(label=_('Sender'))

    c_recipients = MultiCreatorEntityField(label=_('Contacts'),      required=False, model=Contact,      q_filter={'email__gt': ''})
    o_recipients = MultiCreatorEntityField(label=_('Organisations'), required=False, model=Organisation, q_filter={'email__gt': ''})

    send_me = BooleanField(label=_('Send me a copy of this mail'), required=False)

    error_messages = {
        'no_person': _('Select at least a Contact or an Organisation'),
    }

    blocks = FieldBlockManager(
            ('recipients', _('Who'),  ['user', 'sender', 'send_me', 'c_recipients', 'o_recipients']),
            ('content',    _('What'), ['subject', 'body', 'body_html']),
            ('extra',      _('With'), ['signature', 'attachments']),
        )

    class Meta:
        model  = EntityEmail
        fields = ('sender', 'subject', 'body', 'body_html', 'signature', 'attachments')

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entity = entity

        if isinstance(entity, (Contact, Organisation)):
            fn, msg = ('c_recipients', _('Beware: the contact «{}» has no email address!')) \
                      if isinstance(entity, Contact) else \
                      ('o_recipients', _('Beware: the organisation «{}» has no email address!'))
            field = self.fields[fn]

            if entity.email:
                field.initial = [entity.pk]
            else:
                field.help_text = msg.format(entity)

        self.user_contact = contact = self.user.linked_contact

        if contact.email:
            self.fields['sender'].initial = contact.email

        def finalize_recipient_field(name, model):
            if FieldsConfig.get_4_model(model).is_fieldname_hidden('email'):
                self.fields[name] = CharField(
                        label=self.fields[name].label,
                        required=False, widget=Label,
                        initial=ugettext('Beware: the field «Email address» is hidden ;'
                                         ' please contact your administrator.'
                                        ),
                    )

        finalize_recipient_field('c_recipients', Contact)
        finalize_recipient_field('o_recipients', Organisation)

    def _clean_recipients(self, field_name):
        if isinstance(self.fields[field_name].widget, Label):
            return []

        recipients = self.cleaned_data.get(field_name) or []
        bad_entities = []

        for entity in recipients:
            try:
                validate_email(entity.email)
            except ValidationError:
                bad_entities.append(entity)

        if bad_entities:
            msg_format = ugettext('The email address for {} is invalid')
            user = self.user

            for entity in bad_entities:
                self.add_error(field_name, msg_format.format(entity.allowed_str(user)))

        return recipients

    def clean_c_recipients(self):
        return self._clean_recipients('c_recipients')

    def clean_o_recipients(self):
        return self._clean_recipients('o_recipients')

    def clean(self):
        cdata = super().clean()

        if not self._errors and not cdata['c_recipients'] and not cdata['o_recipients']:
            raise ValidationError(self.error_messages['no_person'], code='no_person')

        return cdata

    def save(self):
        cdata    = self.cleaned_data
        get_data = cdata.get

        sender      = get_data('sender')
        subject     = get_data('subject')
        body        = get_data('body')
        body_html   = get_data('body_html')
        signature   = get_data('signature')
        attachments = get_data('attachments')
        user        = get_data('user')

        sending_error = False

        def create_n_send_mail(recipient_address):
            nonlocal sending_error

            email = EntityEmail.create_n_send_mail(sender=sender, recipient=recipient_address,
                                                   subject=subject, user=user,
                                                   body=body, body_html=body_html,
                                                   signature=signature, attachments=attachments,
                                                  )

            if email.status == MAIL_STATUS_SENDINGERROR:
                sending_error = True

            return email

        with atomic():
            if get_data('send_me'):
                create_n_send_mail(sender)

            user_contact = self.user_contact
            create_relation = partial(Relation.objects.create, user=user)

            for recipient in chain(cdata['c_recipients'], cdata['o_recipients']):
                email = create_n_send_mail(recipient.email)

                create_relation(subject_entity=email, type_id=REL_SUB_MAIL_SENDED,   object_entity=user_contact)
                create_relation(subject_entity=email, type_id=REL_SUB_MAIL_RECEIVED, object_entity=recipient)

        if sending_error:
            entity_emails_send_type.refresh_job()


class TemplateSelectionForm(CremeForm):
    step     = IntegerField(widget=HiddenInput, initial=1)
    template = CreatorEntityField(label=pgettext_lazy('emails', 'Template'), model=EmailTemplate,
                                  credentials=EntityCredentials.VIEW,
                                 )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warnings.warn('emails.forms.mail.TemplateSelectionForm is deprecated.',
                      DeprecationWarning
                     )


class TemplateSelectionFormStep(CremeForm):
    template = CreatorEntityField(label=pgettext_lazy('emails', 'Template'),
                                  model=EmailTemplate,
                                  credentials=EntityCredentials.VIEW,
                                 )

    step_submit_label = _('Select this template')

    def save(self):
        pass


class EntityEmailFromTemplateForm(EntityEmailForm):
    step = IntegerField(widget=HiddenInput, initial=2)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warnings.warn('emails.forms.mail.EntityEmailFromTemplateForm is deprecated.',
                      DeprecationWarning
                     )
