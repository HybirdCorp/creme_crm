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

from django.forms import CharField
from django.forms.util import ValidationError
from django.forms.widgets import Textarea
from django.utils.translation import ugettext_lazy as _, ugettext

from creme_core.forms import CremeEntityForm

from sms.encoding import gsm_encoded_content, SMS_MAX_LENGTH
from sms.models import MessageTemplate


_FORBIDEN = u"^ { } \\ [ ~ ] | €" #TODO: given by the backend ??
_HELP = _(u"""Message with a maximum of 160 characters.
 Beware, the header matters (+ 3 characters) and the following characters count double: %s""") % _FORBIDEN


class TemplateCreateForm(CremeEntityForm):
    body = CharField(label=_(u'Message'), widget=Textarea(), help_text=_HELP)

    class Meta(CremeEntityForm.Meta):
        model = MessageTemplate

    def clean(self):
        cleaned_data = self.cleaned_data
        subject = cleaned_data.get('subject', '')
        body = cleaned_data.get('body', '')
        content = subject + ' : ' + body if subject else body

        encoded_length = len(gsm_encoded_content(content))

        if encoded_length > SMS_MAX_LENGTH:
            raise ValidationError(ugettext('Message is too long (%(length)s > %(max_length)s)') % {
                                    'length': encoded_length, 'max_length': SMS_MAX_LENGTH})

        return cleaned_data


class TemplateEditForm(TemplateCreateForm):
    pass
    #class Meta:
        #model   = MessageTemplate
