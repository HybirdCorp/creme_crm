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

from os.path import basename

from django.conf import settings
from django.forms import ImageField
from django.utils.translation import gettext as _

from creme.creme_core.backends import import_backend_registry
from creme.creme_core.forms.base import CremeEntityQuickForm
from creme.creme_core.models.utils import assign_2_charfield
from creme.creme_core.views.file_handling import handle_uploaded_file

from .. import constants, get_document_model, get_folder_model
from ..utils import get_csv_folder_or_create

Document = get_document_model()


class DocumentQuickForm(CremeEntityQuickForm):
    class Meta:
        model = Document
        fields = ('user', 'filedata', 'linked_folder')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        folder_f = self.fields.get('linked_folder')

        if folder_f:
            folder = get_folder_model().objects.get(uuid=constants.UUID_FOLDER_RELATED2ENTITIES)

            if self.user.has_perm_to_view(folder):
                self.fields['linked_folder'].initial = folder.id

    def save(self, *args, **kwargs):
        instance = self.instance

        instance.filedata = fpath = handle_uploaded_file(
            self.cleaned_data['filedata'],
            # path=['upload', 'documents'],
            path=['documents'],
            # max_length=Document._meta.get_field('filedata').max_length,
            max_length=type(instance)._meta.get_field('filedata').max_length,
        )
        assign_2_charfield(instance, 'title', basename(fpath))

        return super().save(*args, **kwargs)


class DocumentWidgetQuickForm(DocumentQuickForm):
    class Meta:
        model = Document
        fields = ('user', 'filedata')

    def __init__(self, folder=None, user=None, *args, **kwargs):
        super().__init__(user=user, *args, **kwargs)
        self.folder = folder

    def save(self, *args, **kwargs):
        if self.folder is not None:
            self.instance.linked_folder = self.folder

        return super().save(*args, **kwargs)


# TODO: check Mimetype of the uploaded file ?
class CSVDocumentWidgetQuickForm(DocumentWidgetQuickForm):
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(user=user, *args, **kwargs)
        self.fields['filedata'].widget.attrs = {
            'accept': ','.join(
                f'.{ext}' for ext in import_backend_registry.extensions
            ),
        }

    def clean(self):
        self.folder = get_csv_folder_or_create(self.user)
        return super().clean()


# TODO: factorise
class ImageQuickForm(CremeEntityQuickForm):
    image = ImageField(
        label=_('Image file'),
        max_length=Document._meta.get_field('filedata').max_length,
    )

    class Meta:
        model = Document
        fields = ('user', 'image', 'linked_folder')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = self.fields
        fields['linked_folder'].initial = get_folder_model().objects.filter(
            uuid=constants.UUID_FOLDER_IMAGES,
        ).first()
        # TODO: hook django (create our own widget and set it on ImageField ?)
        fields['image'].widget.attrs = {
            'accept': ','.join(
                f'.{ext}'
                for ext in settings.ALLOWED_IMAGES_EXTENSIONS
            ),
        }

    def save(self, *args, **kwargs):
        instance = self.instance

        instance.filedata = fpath = handle_uploaded_file(
            self.cleaned_data['image'],
            # path=['upload', 'documents'],
            path=['documents'],
            # max_length=Document._meta.get_field('filedata').max_length,
            max_length=type(instance)._meta.get_field('filedata').max_length,
        )
        assign_2_charfield(instance, 'title', basename(fpath))

        return super().save(*args, **kwargs)
