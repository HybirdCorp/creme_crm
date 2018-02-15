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

from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import CremeEntity
from creme.creme_core.views.generic import (add_entity, edit_entity, view_entity,
        list_view, add_model_with_popup)

from .. import get_folder_model, get_document_model
from ..constants import DEFAULT_HFILTER_DOCUMENT
from ..forms.document import DocumentCreateForm, RelatedDocumentCreateForm, DocumentEditForm


Document = get_document_model()


def abstract_add_document(request, form=DocumentCreateForm,
                          submit_label=Document.save_label,
                         ):
    folder = get_folder_model().objects.first()

    return add_entity(request, form,
                      # TODO: uncomment when CreatorEntityField can be initialized with instance..
                      # extra_initial={'folder': Folder.objects.first()},
                      extra_initial={'folder': folder.id if folder else None},
                      extra_template_dict={'submit_label': submit_label},
                     )


def abstract_add_related_document(request, entity_id, form=RelatedDocumentCreateForm,
                                  title=_(u'New document for «%s»'),
                                  submit_label=Document.save_label,
                                 ):
    entity = get_object_or_404(CremeEntity, pk=entity_id)
    user = request.user

    user.has_perm_to_view_or_die(entity)
    user.has_perm_to_link_or_die(entity)
    user.has_perm_to_link_or_die(Document, owner=None)

    return add_model_with_popup(request, form, title % entity,
                                initial={'entity': entity},
                                submit_label=submit_label,
                               )


def abstract_edit_document(request, document_id, form=DocumentEditForm):
    return edit_entity(request, document_id, Document, form)


def abstract_view_document(request, object_id,
                           template='documents/view_document.html',
                          ):
    return view_entity(request, object_id, Document, template=template)


@login_required
@permission_required(('documents', cperm(Document)))
def add(request):
    return abstract_add_document(request)


@login_required
@permission_required(('documents', cperm(Document)))
def add_related(request, entity_id):
    return abstract_add_related_document(request, entity_id)


@login_required
@permission_required('documents')
def edit(request, document_id):
    return abstract_edit_document(request, document_id)


@login_required
@permission_required('documents')
def detailview(request, object_id):
    return abstract_view_document(request, object_id)


@login_required
@permission_required('documents')
def listview(request):
    return list_view(request, Document, hf_pk=DEFAULT_HFILTER_DOCUMENT)
