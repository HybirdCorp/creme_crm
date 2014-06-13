# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

import logging

from django.core.exceptions import ValidationError
from django.forms.fields import CharField
from django.forms.widgets import Textarea
from django.template import Template, VariableNode
from django.utils.functional import lazy
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.forms import CremeEntityForm, CremeForm, FieldBlockManager
from creme.creme_core.forms.fields import MultiCreatorEntityField
from creme.creme_core.forms.widgets import TinyMCEEditor

from creme.documents.models import Document

from ..models import EmailTemplate
from .utils import validate_images_in_html


logger = logging.getLogger(__name__)

TEMPLATES_VARS = {'last_name', 'first_name', 'civility', 'name'}

_TEMPLATES_VARS_4_HELP = u' '.join('{{%s}}' % var for var in TEMPLATES_VARS)

_help_text = lazy((lambda: ugettext(u'You can use variables: %s') % _TEMPLATES_VARS_4_HELP), unicode)


class EmailTemplateForm(CremeEntityForm):
    body        = CharField(label=_(u'Body'), widget=Textarea, help_text=_help_text())
    body_html   = CharField(label=_(u'Body (HTML)'), required=False, widget=TinyMCEEditor(), help_text=_help_text())
    attachments = MultiCreatorEntityField(label=_(u'Attachments'), required=False, model=Document)

    class Meta(CremeEntityForm.Meta):
        model = EmailTemplate

    def _clean_body(self, body):
        invalid_vars = []

        for varnode in Template(body).nodelist.get_nodes_by_type(VariableNode):
            varname = varnode.filter_expression.var.var
            if varname not in TEMPLATES_VARS:
                invalid_vars.append(varname)

        if invalid_vars:
            raise ValidationError(ugettext(u'The following variables are invalid: %s') % invalid_vars)

    def clean_body(self):
        body = self.cleaned_data['body']
        self._clean_body(body)

        return body

    def clean_body_html(self):
        body = self.cleaned_data['body_html']

        self._clean_body(body)

        #TODO: Add and handle a M2M for embedded images after Document & Image merge
        images = validate_images_in_html(body, self.user)
        logger.debug('EmailTemplate will be created with images: %s', images)

        return body


class EmailTemplateAddAttachment(CremeForm):
    attachments = MultiCreatorEntityField(label=_(u'Attachments'), required=False, model=Document)

    blocks = FieldBlockManager(('general', _(u'Attachments'), '*'))

    def __init__(self, entity, *args, **kwargs):
        super(EmailTemplateAddAttachment, self).__init__(*args, **kwargs)
        self.template = entity

    def save(self):
        attachments = self.template.attachments

        for attachment in self.cleaned_data['attachments']:
            attachments.add(attachment)
