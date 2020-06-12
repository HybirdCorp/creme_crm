# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.views import generic

from .. import get_document_model, get_folder_model
from ..constants import DEFAULT_HFILTER_DOCUMENT
from ..forms import document as doc_forms

Document = get_document_model()


class DocumentCreation(generic.EntityCreation):
    model = Document
    form_class = doc_forms.DocumentCreateForm

    def get_initial(self):
        initial = super().get_initial()
        initial['linked_folder'] = get_folder_model().objects.first()

        return initial


class RelatedDocumentCreation(generic.AddingInstanceToEntityPopup):
    model = Document
    form_class = doc_forms.RelatedDocumentCreateForm
    permissions = ['documents', cperm(Document)]
    title = _('New document for «{entity}»')

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_view_or_die(entity)
        user.has_perm_to_link_or_die(entity)

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        user.has_perm_to_link_or_die(Document, owner=None)


class DocumentDetail(generic.EntityDetail):
    model = Document
    template_name = 'documents/view_document.html'
    pk_url_kwarg = 'document_id'


class DocumentEdition(generic.EntityEdition):
    model = Document
    form_class = doc_forms.DocumentEditForm
    pk_url_kwarg = 'document_id'


class DocumentsList(generic.EntitiesList):
    model = Document
    default_headerfilter_id = DEFAULT_HFILTER_DOCUMENT
