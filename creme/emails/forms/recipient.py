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

from django.core.validators import validate_email
from django.forms import FileField, ValidationError
from django.utils.encoding import smart_str
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeForm, FieldBlockManager
from creme.creme_core.forms.fields import MultiEmailField
from creme.creme_core.utils import chunktools

from ..models import EmailRecipient


# TODO: move to creme_core.utils ? remove ?
def _detect_end_line(uploaded_file):
    """Returns the end of line sequence (Unix/Windows/Mac ar handled).
    @param uploaded_file: instance with a method chunks() which yields strings
           (like Django's UploadedFile).
    """
    split_end = False  # '\r' at the end of a chunk, '\n' at the start of the next one.

    for chunk in uploaded_file.chunks():
        if split_end:
            return '\r\n' if chunk.startswith('\n') else '\r'

        if '\r\n' in chunk:
            return '\r\n'

        idx = chunk.find('\r')
        if idx != -1:
            if idx < len(chunk) - 1:
                return '\r'

            split_end = True

    return '\n'  # TODO: 'default' argument ?


class MailingListAddRecipientsForm(CremeForm):
    recipients = MultiEmailField(
        label=_('Recipients'),
        help_text=_('Write a valid email address per line.'),
    )

    blocks = FieldBlockManager({
        'id': 'general', 'label': _('Recipients'), 'fields': '*',
    })

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ml = entity

    def save(self):
        ml = self.ml
        recipients = self.cleaned_data['recipients']
        existing = frozenset(
            EmailRecipient.objects.filter(ml=ml, address__in=recipients)
                                  .values_list('address', flat=True)
        )

        create = EmailRecipient.objects.create

        for address in recipients:
            if address not in existing:
                create(ml=ml, address=address)


class MailingListAddCSVForm(CremeForm):
    recipients = FileField(
        label=_('Recipients'),
        help_text=_(
            'A file containing one email address per line '
            '(e.g. "creme@crm.com" without quotation marks).'
        )
    )

    blocks = FieldBlockManager({
        'id': 'general', 'label': _('CSV file'), 'fields': '*',
    })

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ml = entity

    @staticmethod
    def filter_mail_chunk(value):
        result = smart_str(value.strip())

        try:
            validate_email(result)
        except ValidationError:
            result = None

        return result

    def save(self):  # TODO: factorise with MailingListAddRecipientsForm.save() ??
        ml = self.ml
        create  = EmailRecipient.objects.create
        filter_ = EmailRecipient.objects.filter

        uploaded_file = self.cleaned_data['recipients']

        def addresses():
            for line in uploaded_file:
                address = self.filter_mail_chunk(line)
                if address:
                    yield address

        for recipients in chunktools.iter_as_chunk(addresses(), 256):
            recipients = frozenset(recipients)
            existing = frozenset(
                filter_(ml=ml, address__in=recipients).values_list('address', flat=True)
            )

            for address in recipients:
                if address not in existing:
                    create(ml=ml, address=address)
