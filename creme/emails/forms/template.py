# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from logging import debug

from django.core.exceptions import PermissionDenied
from django.forms import CharField, ValidationError
from django.forms.widgets import Textarea
from django.template import Template, VariableNode
from django.utils.functional import lazy
from django.utils.translation import ugettext_lazy as _, ugettext

from creme_core.forms import CremeEntityForm, CremeForm, FieldBlockManager
from creme_core.forms.fields import MultiCremeEntityField
from creme_core.forms.widgets import TinyMCEEditor

from documents.models import Document

from emails.models import EmailTemplate
from emails.utils import get_images_from_html, ImageFromHTMLError


_TEMPLATES_VARS = set(['last_name', 'first_name', 'civility', 'name'])
_TEMPLATES_VARS_4_HELP = u' '.join('{{%s}}' % var for var in _TEMPLATES_VARS)

_help_text = lazy((lambda: ugettext(u'You can use variables: %s') % _TEMPLATES_VARS_4_HELP), unicode)


class EmailTemplateForm(CremeEntityForm):
    body        = CharField(label=_(u'Body'), widget=Textarea, help_text=_help_text())
    body_html   = CharField(label=_(u'Body (HTML)'), required=False, widget=TinyMCEEditor(), help_text=_help_text())
    attachments = MultiCremeEntityField(label=_(u'Attachments'), required=False, model=Document)

    class Meta(CremeEntityForm.Meta):
        model = EmailTemplate

    def _create_img_validation_error(self, filename):
         return ValidationError(ugettext(u"The image «%s» no longer exists or isn't valid.") % filename)

    def _clean_body(self, body):
        invalid_vars = []

        for varnode in Template(body).nodelist.get_nodes_by_type(VariableNode):
            varname = varnode.filter_expression.var.var
            if varname not in _TEMPLATES_VARS:
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

        try:
            images = get_images_from_html(body)
        except ImageFromHTMLError as e:
            raise self._create_img_validation_error(e.filename)

        user = self.user

        for finename, (image, src) in images.iteritems():
            if image is None:
                raise self._create_img_validation_error(filename)

            try:
                image.can_view_or_die(user)
            except PermissionDenied as pde:
                raise ValidationError(pde)

        debug('EmailTemplate will be create with images: %s', images)

        return body


class EmailTemplateAddAttachment(CremeForm):
    attachments = MultiCremeEntityField(label=_(u'Attachments'), required=False, model=Document)

    blocks = FieldBlockManager(('general', _(u'Attachments'), '*'))

    def __init__(self, entity, *args, **kwargs):
        super(EmailTemplateAddAttachment, self).__init__(*args, **kwargs)
        self.template = entity

    def save(self):
        attachments = self.template.attachments

        for attachment in self.cleaned_data['attachments']:
            attachments.add(attachment)
