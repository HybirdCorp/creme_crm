# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

# import warnings
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import (
    CremeEntityForm,
    CremeForm,
    FieldBlockManager,
    MultiCreatorEntityField,
)
# from .. import get_emailtemplate_model
from creme.creme_core.forms.widgets import TinyMCEEditor
from creme.documents import get_document_model

# class EmailTemplateForm(CremeEntityForm):
#     class Meta(CremeEntityForm.Meta):
#         model = get_emailtemplate_model()
#         widgets = {
#             'body_html': TinyMCEEditor,
#         }
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('EmailTemplateForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)


class EmailTemplateBaseCustomForm(CremeEntityForm):
    class Meta:
        widgets = {
            'body_html': TinyMCEEditor,
        }


class EmailTemplateAddAttachment(CremeForm):
    attachments = MultiCreatorEntityField(
        label=_('Attachments'), required=False, model=get_document_model(),
    )

    blocks = FieldBlockManager({
        'id': 'general', 'label': _('Attachments'), 'fields': '*',
    })

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.template = entity

    def save(self):
        add = self.template.attachments.add

        for attachment in self.cleaned_data['attachments']:
            add(attachment)
