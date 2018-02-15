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

from itertools import chain
import logging

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.forms.fields import EmailField, BooleanField, IntegerField, CharField
from django.forms.widgets import HiddenInput
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext_lazy

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.forms.base import CremeForm, CremeEntityForm, FieldBlockManager
from creme.creme_core.forms.fields import MultiCreatorEntityField, CreatorEntityField
from creme.creme_core.forms.widgets import Label
from creme.creme_core.models import Relation, FieldsConfig

from creme.documents import get_document_model

from creme.persons import get_contact_model, get_organisation_model

from .. import get_entityemail_model, get_emailtemplate_model
from ..constants import REL_SUB_MAIL_RECEIVED, REL_SUB_MAIL_SENDED, MAIL_STATUS_SENDINGERROR
from ..creme_jobs import entity_emails_send_type


logger = logging.getLogger(__name__)
Document      = get_document_model()
Contact       = get_contact_model()
Organisation  = get_organisation_model()
EntityEmail   = get_entityemail_model()
EmailTemplate = get_emailtemplate_model()


class EntityEmailForm(CremeEntityForm):
    """Mails are related to the selected contacts/organisations & the 'current' entity.
    Mails are send to selected contacts/organisations.
    """
    sender = EmailField(label=_(u'Sender'))

    c_recipients = MultiCreatorEntityField(label=_(u'Contacts'),      required=False, model=Contact,      q_filter={'email__gt': ''})
    o_recipients = MultiCreatorEntityField(label=_(u'Organisations'), required=False, model=Organisation, q_filter={'email__gt': ''})

    send_me = BooleanField(label=_(u'Send me a copy of this mail'), required=False)

    error_messages = {
        'no_person': _(u'Select at least a Contact or an Organisation'),
    }

    blocks = FieldBlockManager(
            ('recipients', _(u'Who'),  ['user', 'sender', 'send_me', 'c_recipients', 'o_recipients']),
            ('content',    _(u'What'), ['subject', 'body', 'body_html']),
            ('extra',      _(u'With'), ['signature', 'attachments']),
        )

    class Meta:
        model  = EntityEmail
        fields = ('sender', 'subject', 'body', 'body_html', 'signature', 'attachments')

    def __init__(self, entity, *args, **kwargs):
        super(EntityEmailForm, self).__init__(*args, **kwargs)
        self.entity = entity

        if isinstance(entity, (Contact, Organisation)):
            fn, msg = ('c_recipients', _(u'Beware: the contact «%s» has no email address!')) \
                      if isinstance(entity, Contact) else \
                      ('o_recipients', _(u'Beware: the organisation «%s» has no email address!'))
            field = self.fields[fn]

            if entity.email:
                field.initial = [entity.pk]
            else:
                field.help_text = msg % entity

        self.user_contact = contact = self.user.linked_contact

        if contact.email:
            self.fields['sender'].initial = contact.email

        def finalize_recipient_field(name, model):
            if FieldsConfig.get_4_model(model).is_fieldname_hidden('email'):
                self.fields[name] = CharField(
                        label=self.fields[name].label,
                        required=False, widget=Label,
                        initial=ugettext(u'Beware: the field «Email address» is hidden ;'
                                         u' please contact your administrator.'
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
            msg_format = ugettext(u'The email address for %s is invalid')
            user = self.user

            for entity in bad_entities:
                self.add_error(field_name, msg_format % entity.allowed_unicode(user))

        return recipients

    def clean_c_recipients(self):
        return self._clean_recipients('c_recipients')

    def clean_o_recipients(self):
        return self._clean_recipients('o_recipients')

    def clean(self):
        cdata = super(EntityEmailForm, self).clean()

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

        # TODO use "sending_error = False" + "nonlocal sending_error" in python3
        sending_errors = []

        def create_n_send_mail(recipient_address):
            email = EntityEmail.create_n_send_mail(sender=sender, recipient=recipient_address,
                                                   subject=subject, user=user,
                                                   body=body, body_html=body_html,
                                                   signature=signature, attachments=attachments,
                                                  )

            if email.status == MAIL_STATUS_SENDINGERROR:
                sending_errors.append(True)

            return email

        if get_data('send_me'):
            create_n_send_mail(sender)

        user_contact = self.user_contact
        create_relation = Relation.objects.create

        for recipient in chain(cdata['c_recipients'], cdata['o_recipients']):
            email = create_n_send_mail(recipient.email)

            create_relation(subject_entity=email, type_id=REL_SUB_MAIL_SENDED,   object_entity=user_contact, user=user)
            create_relation(subject_entity=email, type_id=REL_SUB_MAIL_RECEIVED, object_entity=recipient,    user=user)

        if sending_errors:
            entity_emails_send_type.refresh_job()


class TemplateSelectionForm(CremeForm):
    step     = IntegerField(widget=HiddenInput, initial=1)
    template = CreatorEntityField(label=pgettext_lazy('emails', u'Template'), model=EmailTemplate,
                                  credentials=EntityCredentials.VIEW,
                                 )


class EntityEmailFromTemplateForm(EntityEmailForm):
    step = IntegerField(widget=HiddenInput, initial=2)
