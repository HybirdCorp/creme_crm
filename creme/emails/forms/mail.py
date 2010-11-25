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

from itertools import chain

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.forms.fields import EmailField, BooleanField
from django.forms.util import ErrorList
from django.utils.translation import ugettext_lazy as _, ugettext

from creme_core.models.relation import Relation
from creme_core.forms.fields import MultiCremeEntityField, CremeEntityField
from creme_core.forms.base import CremeEntityForm, FieldBlockManager

from documents.models import Document

from emails.constants import REL_SUB_MAIL_RECEIVED, REL_SUB_MAIL_SENDED
from emails.models.mail import EntityEmail

from persons.models import Contact, Organisation


invalid_email_error = ugettext(u'The email address for %(entity)s is invalid')

class EntityEmailForm(CremeEntityForm):
    #On doit relier aux contact et/ou orga séléctionnées + à l'entitée en cours
    #On doit envoyer aux contact et orga séléctionnées

    sender       = EmailField(label=_(u'Sender'))
    c_recipients = MultiCremeEntityField(label=_(u'Contacts'),      required=False, model=Contact,      q_filter={'email__isnull': False})
    o_recipients = MultiCremeEntityField(label=_(u'Organisations'), required=False, model=Organisation, q_filter={'email__isnull': False})

#    body_html    = CharField(label=_(u'Body'), widget=RTEWidget())

    attachments  = MultiCremeEntityField(label=_(u'Attachments'), required=False, model=Document)
    send_me      = BooleanField(label=_(u'Send me a copy of this mail'), required=False)

    blocks = FieldBlockManager(
            ('recipients', _(u'Who'),  ['user', 'sender', 'send_me', 'c_recipients', 'o_recipients']),
            ('content',    _(u'What'), ['subject', 'body_html']),
            ('extra',      _(u'With'), ['signature', 'attachments']),
        )

    class Meta:
        model  = EntityEmail
        fields = ('sender', 'subject', 'body_html', 'signature')#, 'attachments')

    def __init__(self, entity, *args, **kwargs):
        super(EntityEmailForm, self).__init__(*args, **kwargs)
        self.entity = entity

        initial = kwargs.get('initial', {})
        current_user = initial.get('current_user')
        if current_user is not None:
            contact = Contact.objects.get(is_user=current_user)
            if contact.email:
                self.fields['sender'].initial = contact.email


    def clean(self):
        cleaned_data = self.cleaned_data
        errors = self.errors

        contacts      = list(cleaned_data.get('c_recipients', []))
        organisations = list(cleaned_data.get('o_recipients', []))

        c_recipients_errors = []
        for i, entity in enumerate(contacts):
            try:
                validate_email(entity.email)
            except Exception, e:#Better exception ?
                c_recipients_errors.append(invalid_email_error % {'entity': contacts[i]})

        if c_recipients_errors:
            errors['c_recipients'] = ErrorList(c_recipients_errors)


        o_recipients_errors = []
        for i, entity in enumerate(organisations):
            try:
                validate_email(entity.email)
            except Exception, e:#Better exception ?
                o_recipients_errors.append(invalid_email_error % {'entity': organisations[i]})

        if o_recipients_errors:
            errors['o_recipients'] = ErrorList(o_recipients_errors)

        if not contacts and not organisations:
            raise ValidationError(ugettext(u'Select at least a Contact or an Organisation'))

        return cleaned_data

    def save(self):
        cleaned_data = self.cleaned_data
        cleaned_data_get = cleaned_data.get

        sender      = cleaned_data_get('sender')
        subject     = cleaned_data_get('subject')
        body_html   = cleaned_data_get('body_html')
        signature   = cleaned_data_get('signature')
        attachments = cleaned_data_get('attachments')
        user_pk     = cleaned_data_get('user').pk

        entity = self.entity

        if cleaned_data_get('send_me'):
            EntityEmail.create_n_send_mail(sender, sender, subject, user_pk, body_html, signature, attachments)

        Relation_create = Relation.create

        for _entity in chain(cleaned_data_get('c_recipients',[]), cleaned_data_get('o_recipients',[])):
            email = EntityEmail.create_n_send_mail(sender, _entity.email, subject, user_pk, body_html, signature, attachments)

            Relation_create(email, REL_SUB_MAIL_SENDED,   entity,  user_id=user_pk)
            Relation_create(email, REL_SUB_MAIL_RECEIVED, _entity, user_id=user_pk)
