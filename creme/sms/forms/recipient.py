################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

from django.forms import FileField, Textarea
from django.utils.encoding import smart_str
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeForm, FieldBlockManager
from creme.creme_core.utils import chunktools

from ..forms.fields import PhoneField, PhoneListField
from ..models.recipient import Recipient


class MessagingListAddRecipientsForm(CremeForm):
    # TODO: see for phonelist widget
    recipients = PhoneListField(
        widget=Textarea, label=_('Recipients'),
        help_text=_('One phone number per line'),
    )

    blocks = FieldBlockManager({
        'id': 'general', 'label': _('Recipients'), 'fields': '*',
    })

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.messaging_list = entity

    def save(self):
        messaging_list = self.messaging_list
        recipients = self.cleaned_data['recipients']
        existing = frozenset(
            Recipient.objects.filter(
                messaging_list=messaging_list,
                phone__in=recipients,
            ).values_list('phone', flat=True)
        )

        create = Recipient.objects.create

        for number in recipients:
            if number not in existing:
                create(messaging_list=messaging_list, phone=number)


class MessagingListAddCSVForm(CremeForm):
    recipients = FileField(
        label=_('Recipients'),
        help_text=_(
            "A text file where each line contains digits "
            "(which can be separated by space characters).\n"
            "Only digits are used and empty lines are ignored.\n"
            "Examples: '00 56 87 56 45' => '0056875645'; 'abc56def' => '56'"
        ),
    )

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.messaging_list = entity

    def save(self):
        mlist = self.messaging_list
        create = Recipient.objects.create
        filter_recipient = Recipient.objects.filter

        uploaded_file = self.cleaned_data['recipients']

        # TODO: genexpr
        def phones():
            for line in uploaded_file:
                phone = PhoneField.filternumbers(smart_str(line.strip()))
                if phone:
                    yield phone

        for phones in chunktools.iter_as_chunk(phones(), 256):
            phones = frozenset(phones)
            existing = frozenset(
                filter_recipient(
                    messaging_list=mlist, phone__in=phones,
                ).values_list('phone', flat=True)
            )

            for phone in phones:
                if phone not in existing:
                    create(messaging_list=mlist, phone=phone)
