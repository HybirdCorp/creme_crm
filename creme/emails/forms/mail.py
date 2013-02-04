# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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
from logging import debug

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.forms.fields import EmailField, BooleanField, IntegerField #CharField
from django.forms.widgets import HiddenInput
from django.forms.util import ErrorList
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext_lazy

from creme_core.models.relation import Relation
from creme_core.forms.base import CremeForm, CremeEntityForm, FieldBlockManager
from creme_core.forms.fields import MultiCremeEntityField, CremeEntityField
#from creme_core.forms.widgets import TinyMCEEditor
from creme_core.forms.validators import validate_linkable_entities

from documents.models import Document

from persons.models import Contact, Organisation

from emails.models import EntityEmail, EmailTemplate
from emails.constants import REL_SUB_MAIL_RECEIVED, REL_SUB_MAIL_SENDED
from emails.forms.utils import validate_images_in_html


class EntityEmailForm(CremeEntityForm):
    """Mails are related to the selected contacts/organisations & the 'current' entity.
    Mails are send to selected contacts/organisations.
    """
    sender       = EmailField(label=_(u'Sender'))

    #TODO: use the new GenericEntityField ?? When it manages q_filter
    c_recipients = MultiCremeEntityField(label=_(u'Contacts'),      required=False, model=Contact,      q_filter={'email__isnull': False})
    o_recipients = MultiCremeEntityField(label=_(u'Organisations'), required=False, model=Organisation, q_filter={'email__isnull': False})

#    body_html    = CharField(label=_(u'Body'), widget=TinyMCEEditor())

    attachments  = MultiCremeEntityField(label=_(u'Attachments'), required=False, model=Document)
    send_me      = BooleanField(label=_(u'Send me a copy of this mail'), required=False)

    blocks = FieldBlockManager(
            ('recipients', _(u'Who'),  ['user', 'sender', 'send_me', 'c_recipients', 'o_recipients']),
            ('content',    _(u'What'), ['subject', 'body', 'body_html']),
            ('extra',      _(u'With'), ['signature', 'attachments']),
        )

    class Meta:
        model  = EntityEmail
        fields = ('sender', 'subject', 'body', 'body_html', 'signature')#, 'attachments')

    def __init__(self, entity, *args, **kwargs):
        super(EntityEmailForm, self).__init__(*args, **kwargs)
        self.entity = entity

        if isinstance(entity, (Contact, Organisation)):
            fn, msg = ('c_recipients', _(u'Beware: the contact «%s» has no email address!')) if isinstance(entity, Contact) else \
                      ('o_recipients', _(u'Beware: the organisation «%s» has no email address!'))
            field = self.fields[fn]

            if entity.email:
                field.initial = [entity.pk]
            else:
                field.help_text = msg % entity

        self.user_contact = contact = Contact.objects.get(is_user=self.user)

        if contact.email:
            self.fields['sender'].initial = contact.email

    def _clean_recipients(self, field_name):
        recipients = self.cleaned_data.get(field_name) or []
        user = self.user

        validate_linkable_entities(recipients, user)

        bad_entities = []

        for entity in recipients:
            try:
                validate_email(entity.email)
            except ValidationError:
                bad_entities.append(entity)

        if bad_entities:
            msg_format = ugettext(u'The email address for %s is invalid')
            self.errors[field_name] = ErrorList([msg_format % entity.allowed_unicode(user)
                                                     for entity in bad_entities
                                                ]
                                               )

        return recipients

    def clean_body_html(self):
        body = self.cleaned_data['body_html']
        images = validate_images_in_html(body, self.user)

        debug('EntityEmail will be created with images: %s', images)

        return body

    def clean_c_recipients(self):
        return self._clean_recipients('c_recipients')

    def clean_o_recipients(self):
        return self._clean_recipients('o_recipients')

    def clean(self):
        cdata = self.cleaned_data

        if not self._errors and not cdata['c_recipients'] and not cdata['o_recipients']:
            raise ValidationError(ugettext(u'Select at least a Contact or an Organisation'))

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

        if get_data('send_me'):
            EntityEmail.create_n_send_mail(sender, sender, subject, user, body, body_html, signature, attachments)

        user_contact = self.user_contact
        create_relation = Relation.objects.create

        for recipient in chain(cdata['c_recipients'], cdata['o_recipients']):
            email = EntityEmail.create_n_send_mail(sender, recipient.email, subject, user, body, body_html, signature, attachments)

            create_relation(subject_entity=email, type_id=REL_SUB_MAIL_SENDED,   object_entity=user_contact, user=user)
            create_relation(subject_entity=email, type_id=REL_SUB_MAIL_RECEIVED, object_entity=recipient,    user=user)


class TemplateSelectionForm(CremeForm):
    step     = IntegerField(widget=HiddenInput, initial=1)
    template = CremeEntityField(label=pgettext_lazy('emails', 'Template'), model=EmailTemplate)


class EntityEmailFromTemplateForm(EntityEmailForm):
    step = IntegerField(widget=HiddenInput, initial=2)
