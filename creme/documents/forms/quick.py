# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from os import path

from creme_core.forms.base import CremeModelWithUserForm, CremeEntityForm
from creme_core.views.file_handling import handle_uploaded_file

from documents.models import Document
from documents.utils import get_csv_folder_or_create


class DocumentQuickForm(CremeModelWithUserForm):
    class Meta(CremeEntityForm.Meta):
        model = Document
        exclude = ('description', 'title')

    def clean_filedata(self):
        # TODO : return tuple with a pretty name for uploaded file
        return str(handle_uploaded_file(self.cleaned_data['filedata'], path=['upload', 'documents']))

    def save(self, *args, **kwargs):
        self.instance.title = path.basename(self.cleaned_data['filedata'])
        return super(DocumentQuickForm, self).save(*args, **kwargs)


class DocumentWidgetQuickForm(DocumentQuickForm):
    class Meta(CremeEntityForm.Meta):
        model = Document
        exclude = ('description', 'title', 'folder')

    def __init__(self, folder=None, user=None, *args, **kwargs):
        super(DocumentWidgetQuickForm, self).__init__(user=user, *args, **kwargs)
        self.folder = folder

    def save(self, *args, **kwargs):
        if self.folder is not None:
            self.instance.folder = self.folder

        return super(DocumentWidgetQuickForm, self).save(*args, **kwargs)


class CSVDocumentWidgetQuickForm(DocumentWidgetQuickForm):
    class Meta(CremeEntityForm.Meta):
        model = Document
        exclude = ('description', 'title', 'folder')

    def __init__(self, user=None, *args, **kwargs):
        super(DocumentWidgetQuickForm, self).__init__(user=user, *args, **kwargs)

    def clean(self):
        self.folder = get_csv_folder_or_create(self.user)
        return super(CSVDocumentWidgetQuickForm, self).clean()
