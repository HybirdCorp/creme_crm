# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

# import logging

from django.core.exceptions import ValidationError
from django.forms.fields import CharField
from django.forms.widgets import Textarea
from django.template.base import Template, VariableNode
from django.utils.functional import lazy
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.forms import CremeEntityForm, CremeForm, FieldBlockManager, MultiCreatorEntityField
from creme.creme_core.forms.widgets import TinyMCEEditor

from creme.documents import get_document_model

from .. import get_emailtemplate_model


# logger = logging.getLogger(__name__)
Document = get_document_model()

TEMPLATES_VARS = {'last_name', 'first_name', 'civility', 'name'}
_TEMPLATES_VARS_4_HELP = ' '.join('{{%s}}' % var for var in TEMPLATES_VARS)
_help_text = lazy((lambda: ugettext('You can use variables: {}').format(_TEMPLATES_VARS_4_HELP)), str)


class EmailTemplateForm(CremeEntityForm):
    body        = CharField(label=_('Body'), widget=Textarea, help_text=_help_text())
    body_html   = CharField(label=_('Body (HTML)'), required=False, widget=TinyMCEEditor(), help_text=_help_text())
    attachments = MultiCreatorEntityField(label=_('Attachments'), required=False, model=Document)

    error_messages = {
        'invalid_vars': _('The following variables are invalid: %(vars)s'),
    }

    class Meta(CremeEntityForm.Meta):
        model = get_emailtemplate_model()

    def _clean_body(self, body):
        invalid_vars = []

        for varnode in Template(body).nodelist.get_nodes_by_type(VariableNode):
            varname = varnode.filter_expression.var.var
            if varname not in TEMPLATES_VARS:
                invalid_vars.append(varname)

        if invalid_vars:
            raise ValidationError(self.error_messages['invalid_vars'],
                                  params={'vars': invalid_vars},
                                  code='invalid_vars',
                                 )

        # TODO: return body

    def clean_body(self):
        body = self.cleaned_data['body']
        self._clean_body(body)

        return body

    def clean_body_html(self):
        body = self.cleaned_data['body_html']

        self._clean_body(body)

        return body


class EmailTemplateAddAttachment(CremeForm):
    attachments = MultiCreatorEntityField(label=_('Attachments'), required=False, model=Document)

    blocks = FieldBlockManager(('general', _('Attachments'), '*'))

    # def __init__(self, entity, *args, **kwargs):
    def __init__(self, entity, instance=None, *args, **kwargs):
        # super(EmailTemplateAddAttachment, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)
        self.template = entity

    def save(self):
        attachments = self.template.attachments

        for attachment in self.cleaned_data['attachments']:
            attachments.add(attachment)
