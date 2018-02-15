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

import warnings

from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.views.generic import inner_popup
from creme.creme_core.views.utils import json_update_from_widget_response

from .. import get_document_model
from ..forms.quick import CSVDocumentWidgetQuickForm, ImageQuickForm


Document = get_document_model()


def abstract_add_doc_from_widget(request, count=None, form=CSVDocumentWidgetQuickForm,
                                 template='creme_core/generics/form/add_innerpopup.html',
                                 submit_label=_('Save the document'),
                                 title=Document.creation_label,
                                ):
    if count is not None:
        warnings.warn('abstract_add_doc_from_widget(): the argument "count" is deprecated.',
                      DeprecationWarning
                     )

    user = request.user

    if not user.has_perm_to_create(Document):
        raise PermissionDenied('You are not allowed to create a document')

    # TODO: see for permission issues

    if request.method == 'POST':
        form_instance = form(user=user, data=request.POST,
                             files=request.FILES or None,
                            )

        if form_instance.is_valid():
            form_instance.save()
            return json_update_from_widget_response(form_instance.instance)
    else:
        form_instance = form(user=user)

    return inner_popup(request, template,
                       {'form':         form_instance,
                        'title':        title,
                        'submit_label': submit_label,
                       },
                       is_valid=form_instance.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )


@login_required
def add_csv_from_widget(request, count=None):
# def add_csv_from_widget(request):  TODO: in creme 1.8
    if count is not None:
        warnings.warn('add_csv_from_widget(): the argument "count" is deprecated.',
                      DeprecationWarning
                     )

    return abstract_add_doc_from_widget(request)


@login_required
def add_image(request):
    return abstract_add_doc_from_widget(request,
                                        form=ImageQuickForm,
                                        submit_label=_('Save the image'),
                                        title=_('Create an image'),
                                       )
