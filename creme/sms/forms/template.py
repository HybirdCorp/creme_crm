# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from django.forms import CharField, ValidationError, Textarea
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeEntityForm

from .. import get_messagetemplate_model
from ..encoding import gsm_encoded_content, SMS_MAX_LENGTH

_FORBIDDEN = "^ { } \\ [ ~ ] | €"  # TODO: given by the backend ??
_HELP = _("""Message with a maximum of 160 characters.
 Beware, the header matters (+ 3 characters) and the following characters count double: {}""").format(_FORBIDDEN)
MessageTemplate = get_messagetemplate_model()


class TemplateCreateForm(CremeEntityForm):
    body = CharField(label=_('Message'), widget=Textarea(), help_text=_HELP)

    error_messages = {
        'too_long': _('Message is too long (%(length)s > %(max_length)s)'),
    }

    class Meta(CremeEntityForm.Meta):
        model = MessageTemplate

    def clean(self):
        cleaned_data = super().clean()
        subject = cleaned_data.get('subject', '')
        body = cleaned_data.get('body', '')
        content = '{} : {}'.format(subject, body) if subject else body

        encoded_length = len(gsm_encoded_content(content))

        if encoded_length > SMS_MAX_LENGTH:
            raise ValidationError(self.error_messages['too_long'],
                                  params={'length':     encoded_length,
                                          'max_length': SMS_MAX_LENGTH,
                                         },
                                  code='too_long',
                                 )

        return cleaned_data


class TemplateEditForm(TemplateCreateForm):
    pass
