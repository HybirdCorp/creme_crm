# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from creme.creme_core.views import generic
from creme.creme_core.views.utils import json_update_from_widget_response

from .. import get_document_model
from ..forms import quick as q_forms

Document = get_document_model()


class BaseQuickDocumentCreation(generic.EntityCreationPopup):
    model = Document
    # form_class = ...
    template_name = 'creme_core/generics/form/add-popup.html'

    def form_valid(self, form):
        super().form_valid(form=form)
        return json_update_from_widget_response(form.instance)


class QuickDocumentCreation(BaseQuickDocumentCreation):
    form_class = q_forms.CSVDocumentWidgetQuickForm


class QuickImageCreation(BaseQuickDocumentCreation):
    form_class = q_forms.ImageQuickForm
    title = _('Create an image')
    submit_label = _('Save the image')
