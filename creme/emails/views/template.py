################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.workflow import run_workflow_engine
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from .. import custom_forms, get_emailtemplate_model
from ..constants import DEFAULT_HFILTER_TEMPLATE
from ..forms import template as tpl_forms

EmailTemplate = get_emailtemplate_model()


class EmailTemplateCreation(generic.EntityCreation):
    model = EmailTemplate
    form_class = custom_forms.TEMPLATE_CREATION_CFORM


class EmailTemplateDetail(generic.EntityDetail):
    model = EmailTemplate
    template_name = 'emails/view_template.html'
    pk_url_kwarg = 'template_id'


class EmailTemplateEdition(generic.EntityEdition):
    model = EmailTemplate
    form_class = custom_forms.TEMPLATE_EDITION_CFORM
    pk_url_kwarg = 'template_id'


class AttachmentsAdding(generic.RelatedToEntityFormPopup):
    form_class = tpl_forms.EmailTemplateAddAttachment
    template_name = 'creme_core/generics/blockform/link-popup.html'
    title = _('New attachments for «{entity}»')
    submit_label = _('Add the attachments')
    entity_id_url_kwarg = 'template_id'
    entity_classes = EmailTemplate


class AttachmentRemoving(generic.base.EntityRelatedMixin, generic.CremeDeletion):
    permissions = 'emails'
    entity_classes = EmailTemplate
    entity_id_url_kwarg = 'template_id'

    doc_id_arg = 'id'

    def perform_deletion(self, request):
        attachment_id = get_from_POST_or_404(request.POST, self.doc_id_arg, cast=int)

        with atomic(), run_workflow_engine(user=request.user):
            self.get_related_entity().attachments.remove(attachment_id)


class EmailTemplatesList(generic.EntitiesList):
    model = EmailTemplate
    default_headerfilter_id = DEFAULT_HFILTER_TEMPLATE
