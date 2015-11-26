# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

# from django.core.urlresolvers import reverse
from django.db.models.query_utils import Q
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic import add_entity, add_model_with_popup, edit_entity, view_entity
from creme.creme_core.views.generic.listview import list_view

from .. import get_folder_model
from ..constants import DEFAULT_HFILTER_FOLDER
from ..forms.folder import FolderForm, ChildFolderForm
#from ..models import Folder


logger = logging.getLogger(__name__)
Folder = get_folder_model()


def abstract_add_folder(request, form=FolderForm,
                        submit_label=_('Save the folder'),
                       ):
    return add_entity(request, form,
                      extra_template_dict={'submit_label': submit_label},
                     )


def abstract_add_child_folder(request, folder_id, form=ChildFolderForm,
                              title=_(u'New child folder for «%s»'),
                              submit_label=_('Save the folder'),
                            ):
    parent_folder = get_object_or_404(Folder, id=folder_id)
    user = request.user

    user.has_perm_to_link_or_die(parent_folder)

    return add_model_with_popup(request, form,
                                title=title % parent_folder.allowed_unicode(user),
                                initial={'parent': parent_folder},
                                submit_label=submit_label,
                               )


def abstract_edit_folder(request, folder_id, form=FolderForm):
    return edit_entity(request, folder_id, Folder, form)


def abstract_view_folder(request, folder_id,
                         template='documents/view_folder.html',
                        ):
    return view_entity(request, folder_id, Folder, template=template,
                       # path='/documents/folder',
                      )


def abstract_list_folders(request, **extra_kwargs):
#    REQUEST_get = request.REQUEST.get
#    parent_id   = REQUEST_get('parent_id')
    parent_id   = request.POST.get('parent_id') or request.GET.get('parent_id')
    extra_q     = Q(parent_folder__isnull=True)
    previous_id = None
    folder      = None

    if parent_id is not None:
        try:
            parent_id = int(parent_id)
        except (ValueError, TypeError):
            logger.warn('Folder.listview(): invalid "parent_id" parameter: %s', parent_id)
        else:
            folder = get_object_or_404(Folder, pk=parent_id)
            request.user.has_perm_to_view_or_die(folder)
            extra_q = Q(parent_folder=folder)
            previous_id = folder.parent_folder_id

    def post_process(template_dict, request):
        if folder is not None:
            parents = folder.get_parents()
            parents.insert(0, folder)
            parents.reverse()
            template_dict['list_title'] = _(u"List sub-folders of %s") % folder
            template_dict['list_sub_title'] = u" > ".join(f.title for f in parents)

    return list_view(request, Folder,
                     hf_pk=DEFAULT_HFILTER_FOLDER,
                     extra_q=extra_q,
#                     extra_dict={'add_url': '/documents/folder/add',
                     extra_dict={#'add_url': reverse('documents__create_folder'),
                                 'parent_id': parent_id or "",
                                 'extra_bt_templates': ('documents/frags/previous.html', ),
                                 'previous_id': previous_id,
                                },
                     post_process=post_process,
                     **extra_kwargs
                    )

@login_required
# @permission_required(('documents', 'documents.add_folder'))
@permission_required(('documents', cperm(Folder)))
def add(request):
    return abstract_add_folder(request)


@login_required
# @permission_required(('documents', 'documents.add_folder'))
@permission_required(('documents', cperm(Folder)))
def add_child(request, folder_id):
    return abstract_add_child_folder(request, folder_id)


@login_required
@permission_required('documents')
def edit(request, folder_id):
    return abstract_edit_folder(request, folder_id)


@login_required
@permission_required('documents')
def detailview(request, folder_id):
    return abstract_view_folder(request, folder_id)


@login_required
@permission_required('documents')
def listview(request):
    return abstract_list_folders(request)
