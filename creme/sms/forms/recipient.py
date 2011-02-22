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

from django.forms import FileField
from django.forms.widgets import Textarea
from django.utils.translation import ugettext_lazy as _
#from django.utils.encoding import smart_unicode

from creme_core.utils import chunktools
from creme_core.forms import CremeForm, FieldBlockManager
#from creme_core.forms.fields import AjaxFileField

from sms.models.recipient import Recipient
from sms.forms.fields import PhoneListField, PhoneField


class MessagingListAddRecipientsForm(CremeForm):
    # TODO : see for phonelist widget
    recipients = PhoneListField(widget=Textarea(), label=_(u'Recipients'), help_text=_(u'One phone number per line'))

    blocks = FieldBlockManager(('general', _(u'Recipients'), '*'))

    def __init__(self, entity, *args, **kwargs):
        super(MessagingListAddRecipientsForm, self).__init__(*args, **kwargs)
        self.messaging_list = entity

    def save(self):
        messaging_list = self.messaging_list
        recipients = self.cleaned_data['recipients']
        existing   = frozenset(Recipient.objects.filter(messaging_list=messaging_list, phone__in=recipients).values_list('phone', flat=True))

        create = Recipient.objects.create

        for number in recipients:
            if number not in existing:
                create(messaging_list=messaging_list, phone=number)

_HELP = _(u"A text file where each line contains digits (which can be separated by space characters).\n"
"Only digits are used and empty lines are ignored.\n"
"Examples: '00 56 87 56 45' => '0056875645'; 'abc56def' => '56'")

class MessagingListAddCSVForm(CremeForm):
    recipients = FileField(label=_(u'Recipients'), help_text=_HELP)

    def __init__(self, entity, *args, **kwargs):
        super(MessagingListAddCSVForm, self).__init__(*args, **kwargs)
        self.messaging_list = entity

    def save(self):
        targets = chunktools.iter_splitchunks(self.cleaned_data['recipients'].chunks(), '\n', PhoneField.filternumbers)

        for numbers in chunktools.iter_as_chunk(targets, 256):
            self._save_numbers(numbers)

    def _save_numbers(self, numbers):
        if not numbers:
            return

        messaging_list = self.messaging_list
        create  = Recipient.objects.create
        duplicates = frozenset(Recipient.objects.filter(phone__in=numbers, messaging_list=messaging_list).values_list('phone', flat=True))

        for number in numbers:
            if number not in duplicates and number:
                create(messaging_list=messaging_list, phone=number)
