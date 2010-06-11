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

import re

from django.forms import CharField, ValidationError, FileField
from django.forms.widgets import Textarea
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_unicode

from creme_core.utils import chunktools
from creme_core.forms import CremeForm, FieldBlockManager
#from creme_core.forms.fields import AjaxFileField

from emails.models import EmailRecipient


#TODO: remove in Django1.2
#TODO: use  from django.core.validators import validate_email
# copied from django.core.validators
email_re = re.compile(
     r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"               # dot-atom
     r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' # quoted-string
     r')@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?$',                  # domain
     re.IGNORECASE)

def validate_email(value):
    if not email_re.search(smart_unicode(value)):
        raise ValidationError(_(u"N'est pas une addresse e-mail valide: %s") % value)

def validate_emailv2(value):
    return email_re.search(smart_unicode(value)) is not None


class MailingListAddRecipientsForm(CremeForm):
    #TODO: true multi-emailfield ???
    recipients = CharField(widget=Textarea(), label=_(u'Destinataires'), help_text=_(u'Mettez une addresse e-mail par ligne.'))

    blocks = FieldBlockManager(('general', _(u'Destinataires'), '*'))

    def __init__(self, ml, *args, **kwargs):
        super(MailingListAddRecipientsForm, self).__init__(*args, **kwargs)
        self.ml = ml

    def clean_recipients(self):
        recipients = self.cleaned_data['recipients'].split()

        for address in recipients:
            validate_email(address)

        return recipients

    def save(self):
        ml = self.ml
        recipients = self.cleaned_data['recipients']
        existing   = frozenset(EmailRecipient.objects.filter(ml=ml, address__in=recipients).values_list('address', flat=True))

        create = EmailRecipient.objects.create

        for address in recipients:
            if address not in existing:
                create(ml=ml, address=address)

def filter_mail_chunk(value):
    return value if validate_emailv2(value) else None

class MailingListAddCSVForm(CremeForm):
    recipients = FileField(label=_(u'Destinataires'),
                           help_text=_(u'Un fichier contenant une addresse e-mail par ligne (ex:creme@crm.com sans guillemets).'))
#    recipients = AjaxFileField(label=_(u'Destinataires'),
#                           help_text=_(u'Un fichier contenant une addresse e-mail par ligne (ex:creme@crm.com sans guillemets).'),)

    blocks = FieldBlockManager(('general', _(u'Fichier CSV'), '*'))

    def __init__(self, ml, *args, **kwargs):
        super(MailingListAddCSVForm, self).__init__(*args, **kwargs)
        self.ml = ml

    def save(self): #factorise with MailingListAddRecipientsForm.save() ??
        ml      = self.ml
        create  = EmailRecipient.objects.create
        filter_ = EmailRecipient.objects.filter

        addresses = chunktools.iter_splitchunks(self.cleaned_data['recipients'].chunks(), '\n', filter_mail_chunk)

        for recipients in chunktools.iter_as_chunk(addresses, 256):
            recipients = frozenset(recipients)
            existing   = frozenset(filter_(ml=ml, address__in=recipients).values_list('address', flat=True))
            
            for address in recipients:
                if not address in existing:
                    create(ml=ml, address=address)

#        for chunk in self.cleaned_data['recipients'].chunks():
#            recipients = [address for address in chunk.split() if validate_emailv2(address)]
#            existing   = frozenset(filter_(ml=ml, address__in=recipients).values_list('address', flat=True))
#
#            for address in recipients:
#                if address not in existing:
#                    create(ml=ml, address=address)
