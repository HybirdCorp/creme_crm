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

from django.core.validators import validate_email
from django.forms import CharField, ValidationError, FileField
from django.forms.widgets import Textarea
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_unicode
from creme_core.forms.fields import MultiEmailField

from creme_core.utils import chunktools
from creme_core.forms import CremeForm, FieldBlockManager

from emails.models import EmailRecipient


class MailingListAddRecipientsForm(CremeForm):
    recipients = MultiEmailField(label=_(u'Recipients'), help_text=_(u'Write a valid e-mail address per line.'))
#    recipients = CharField(widget=Textarea(), label=_(u'Recipients'), help_text=_(u'Write a valid e-mail address per line.'))

    blocks = FieldBlockManager(('general', _(u'Recipients'), '*'))

    def __init__(self, entity, *args, **kwargs):
        super(MailingListAddRecipientsForm, self).__init__(*args, **kwargs)
        self.ml = entity

#Commented 01 apr 2011
#    def clean_recipients(self):
#        recipients = self.cleaned_data['recipients'].split()
#
#        for address in recipients:
#            validate_email(address)
#
#        return recipients

    def save(self):
        ml = self.ml
        recipients = self.cleaned_data['recipients']
        existing   = frozenset(EmailRecipient.objects.filter(ml=ml, address__in=recipients).values_list('address', flat=True))

        create = EmailRecipient.objects.create

        for address in recipients:
            if address not in existing:
                create(ml=ml, address=address)


class MailingListAddCSVForm(CremeForm):
    recipients = FileField(label=_(u'Recipients'),
                           help_text=_(u'A file containing one e-mail address per line (eg:creme@crm.com without quotation marks).'))

    blocks = FieldBlockManager(('general', _(u'CSV file'), '*'))

    #def __init__(self, entity, *args, **kwargs):
    def __init__(self, instance, *args, **kwargs):
        super(MailingListAddCSVForm, self).__init__(*args, **kwargs)
        #self.ml = entity
        self.ml = instance

    @staticmethod
    def filter_mail_chunk(value):
        result = smart_unicode(value)

        try:
            validate_email(result)
        except ValidationError:
            result = None

        return result

    def save(self): #factorise with MailingListAddRecipientsForm.save() ??
        ml      = self.ml
        create  = EmailRecipient.objects.create
        filter_ = EmailRecipient.objects.filter

        addresses = chunktools.iter_splitchunks(self.cleaned_data['recipients'].chunks(), '\n', self.filter_mail_chunk)

        for recipients in chunktools.iter_as_chunk(addresses, 256):
            recipients = frozenset(recipients)
            existing   = frozenset(filter_(ml=ml, address__in=recipients).values_list('address', flat=True))

            for address in recipients:
                if not address in existing:
                    create(ml=ml, address=address)
