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
import re
import os

from django.conf import settings
from django.core.exceptions import PermissionDenied

from django.forms import CharField, ValidationError
from django.forms.widgets import Textarea
from django.template import Template, VariableNode
from django.utils.translation import ugettext_lazy as _, ugettext

from creme_core.models.entity import CremeEntity

from creme_core.forms import CremeEntityForm, CremeForm, FieldBlockManager
from creme_core.forms.fields import MultiCremeEntityField
from creme_core.forms.widgets import TinyMCEEditor

from documents.models import Document

from emails.models import EmailTemplate


_TEMPLATES_VARS = set(['last_name', 'first_name', 'civility', 'name'])

def _get_vars_help():
    return u' '.join('{{%s}}' % var for var in _TEMPLATES_VARS)


class TemplateEditForm(CremeEntityForm):
    body        = CharField(label=_(u'Body'), widget=TinyMCEEditor(), help_text=_(u'You can use variables: %s') % _get_vars_help())
    attachments = MultiCremeEntityField(label=_(u'Attachments'), required=False, model=Document)

    class Meta(CremeEntityForm.Meta):
        model   = EmailTemplate
        exclude = CremeEntityForm.Meta.exclude + ('use_rte',)

#TODO: Plain text needed ?
#    def __init__(self, *args, **kwargs):
#        super(TemplateEditForm, self).__init__(*args, **kwargs)
#
#        instance = self.instance
#        if instance.id and not instance.use_rte:
#            self.fields['body'].widget = Textarea()

    def clean_body(self):
        body = self.cleaned_data['body']
        user = self.user
        invalid_vars = []

        for varnode in Template(body).nodelist.get_nodes_by_type(VariableNode):
            varname = varnode.filter_expression.var.var
            if varname not in _TEMPLATES_VARS:
                invalid_vars.append(varname)

        if invalid_vars:
            raise ValidationError(ugettext(u'The following variables are invalid: %s') % invalid_vars)

        ####  Image credentials ####
        #TODO: Add and handle a M2M for embedded images after Document & Image merge
        
        img_pattern = re.compile(r'<img.*src[\s]*[=]{1,1}["\']{1,1}(?P<img_src>[\d\w:/?\=.]*)["\']{1,1}')
        sources     = re.findall(img_pattern, body)

        doesnt_exist_ve = lambda f: ValidationError(ugettext(u"The image «%s» no longer exists or isn't valid.") % f)
        
        path_exists = os.path.exists
        path_join   = os.path.join
        MEDIA_ROOT  = settings.MEDIA_ROOT
        creme_entity_get = CremeEntity.objects.get
        
        for src in sources:
            filename = src.rpartition('/')[2]
            if not path_exists(path_join(MEDIA_ROOT, "upload", "images", filename)):
                raise doesnt_exist_ve(filename)

            names = filename.split('_')
            if names:
                try:
                    img = creme_entity_get(pk=int(names[0]))
                    img.can_view_or_die(user)
                except (ValueError, CremeEntity.DoesNotExist):
                    raise doesnt_exist_ve(filename)
                except PermissionDenied, pde:
                    raise ValidationError(pde)
                
        ####  End image credentials ####

        return body


class TemplateCreateForm(TemplateEditForm):
#TODO: Plain text needed ?
#    def save(self):
#        #TODO: hackish --> create a real RTEField that return (boolean, string) ? indicates to the widget an hidden input's id ??
#        self.instance.use_rte = self.data.has_key('body_is_rte_enabled')
#        super(TemplateCreateForm, self).save()
    pass



class TemplateAddAttachment(CremeForm):
    attachments = MultiCremeEntityField(label=_(u'Attachments'), required=False, model=Document)

    blocks = FieldBlockManager(('general', _(u'Attachments'), '*'))

    def __init__(self, entity, *args, **kwargs):
        super(TemplateAddAttachment, self).__init__(*args, **kwargs)
        self.template = entity

    def save(self):
        attachments = self.template.attachments

        for attachment in self.cleaned_data['attachments']:
            attachments.add(attachment)
