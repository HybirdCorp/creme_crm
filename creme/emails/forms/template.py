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

from django.forms import CharField, ValidationError
from django.forms.widgets import Textarea
from django.template import Template, VariableNode
from django.utils.translation import ugettext_lazy as _

from creme_core.forms import CremeModelForm, CremeForm, FieldBlockManager
from creme_core.forms.fields import MultiCremeEntityField
from creme_core.forms.widgets import RTEWidget

from documents.models import Document

from emails.models import EmailTemplate


_TEMPLATES_VARS = set(['last_name', 'first_name', 'civility', 'name'])

def _get_vars_help():
    return u' '.join('{{%s}}' % var for var in _TEMPLATES_VARS)


class TemplateEditForm(CremeModelForm):
    body        = CharField(label=_(u'Corps'), widget=RTEWidget(),
                            help_text=_(u'Vous pouvez utiliser des variables: %s' % _get_vars_help()))
    attachments = MultiCremeEntityField(label=_(u'Fichiers attachés'),
                                        required=False, model=Document)
                                        

    class Meta:
        model   = EmailTemplate
        exclude = CremeModelForm.exclude + ('use_rte',)

    def __init__(self, *args, **kwargs):
        super(TemplateEditForm, self).__init__(*args, **kwargs)

        instance = self.instance
        if instance.id and not instance.use_rte:
            self.fields['body'].widget = Textarea()

    def clean_body(self):
        body = self.cleaned_data['body']
        invalid_vars = []

        for varnode in Template(body).nodelist.get_nodes_by_type(VariableNode):
            varname = varnode.filter_expression.var.var
            if varname not in _TEMPLATES_VARS:
                invalid_vars.append(varname)

        if invalid_vars:
            raise ValidationError(u'Les variables suivantes sont invalides: %s ' % invalid_vars)

        return body


class TemplateCreateForm(TemplateEditForm):
    def save(self):
        #TODO: hackish --> create a real RTEField that return (boolean, string) ? indicates to the widget an hidden input's id ??
        self.instance.use_rte = self.data.has_key('body_is_rte_enabled')
        super(TemplateCreateForm, self).save()


class TemplateAddAttachment(CremeForm):
    attachments = MultiCremeEntityField(label=_(u'Fichiers attachés'),
                                        required=False, model=Document)

    blocks = FieldBlockManager(('general', _(u'Pièces jointes'), '*'))

    def __init__(self, template, *args, **kwargs):
        super(TemplateAddAttachment, self).__init__(*args, **kwargs)
        self.template = template

    def save(self):
        attachments = self.template.attachments

        for attachment in self.cleaned_data['attachments']:
            attachments.add(attachment)
