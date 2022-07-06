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

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.functional import lazy
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.models import CremeEntity

from ..encoding import SMS_MAX_LENGTH, gsm_encoded_content

SPECIAL_CHARS = '^ { } \\ [ ~ ] | €'  # TODO: given by the backend ?


class AbstractMessageTemplate(CremeEntity):
    name = models.CharField(_('Name'), max_length=100)
    subject = models.CharField(_('Subject'), max_length=100)
    body = models.TextField(
        # _('Body'),
        pgettext_lazy('sms', 'Message body'),
        help_text=lazy(
            (lambda: gettext(
                'Message with a maximum of 160 characters.\n'
                'Beware, the header matters (+ 3 characters) '
                'and the following characters count double: {}'
            ).format(SPECIAL_CHARS)),
            str
        )()
    )

    error_messages = {
        'too_long': _('Message is too long (%(length)s > %(max_length)s)'),
    }

    creation_label = pgettext_lazy('sms-template', 'Create a template')
    save_label     = pgettext_lazy('sms-template', 'Save the template')

    class Meta:
        abstract = True
        app_label = 'sms'
        verbose_name = _('SMS Message template')
        verbose_name_plural = _('SMS Messages templates')
        ordering = ('name',)

    def __str__(self):
        return self.name

    def clean(self):
        subject = self.subject
        # TODO: factorise
        content = f'{subject} : {self.body}' if subject else self.body
        encoded_length = len(gsm_encoded_content(content))

        if encoded_length > SMS_MAX_LENGTH:
            raise ValidationError(
                self.error_messages['too_long'],
                params={
                    'length':     encoded_length,
                    'max_length': SMS_MAX_LENGTH,
                },
                code='too_long',
            )

    def get_absolute_url(self):
        return reverse('sms__view_template', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('sms__create_template')

    def get_edit_absolute_url(self):
        return reverse('sms__edit_template', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('sms__list_templates')

    # def resolve(self, date):
    #     return self.subject + ' : ' + self.body


class MessageTemplate(AbstractMessageTemplate):
    class Meta(AbstractMessageTemplate.Meta):
        swappable = 'SMS_TEMPLATE_MODEL'
