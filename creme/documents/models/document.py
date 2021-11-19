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
from mimetypes import guess_type
from os.path import basename

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CremeEntity
from creme.creme_core.models.utils import assign_2_charfield

from . import other_models


class AbstractDocument(CremeEntity):
    title = models.CharField(_('Name'), max_length=100, blank=True)
    filedata = models.FileField(
        # _('File'), max_length=500, upload_to='upload/documents',
        _('File'), max_length=500, upload_to='documents',
    )
    linked_folder = models.ForeignKey(
        settings.DOCUMENTS_FOLDER_MODEL, verbose_name=_('Folder'), on_delete=models.PROTECT,
    )
    mime_type = models.ForeignKey(
        other_models.MimeType,
        verbose_name=_('MIME type'), editable=False, on_delete=models.PROTECT, null=True,
    )
    categories = models.ManyToManyField(
        other_models.DocumentCategory, verbose_name=_('Categories'), blank=True,
    ).set_tags(optional=True)

    creation_label = _('Create a document')
    save_label     = _('Save the document')

    class Meta:
        abstract = True
        # manager_inheritance_from_future = True
        app_label = 'documents'
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')
        ordering = ('title',)

    def __str__(self):
        return f'{self.linked_folder} - {self.title}'

    def get_absolute_url(self):
        return reverse('documents__view_document', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('documents__create_document')

    def get_edit_absolute_url(self):
        return reverse('documents__edit_document', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('documents__list_documents')

    # @staticmethod
    # def get_linkeddoc_relations(entity):
    #     warnings.warn(
    #         'AbstractDocument.get_linkeddoc_relations() is deprecated.',
    #         DeprecationWarning,
    #     )
    #
    #     from creme.creme_core.models import Relation
    #
    #     from ..constants import REL_SUB_RELATED_2_DOC
    #
    #     return Relation.objects.filter(subject_entity=entity.id, type=REL_SUB_RELATED_2_DOC)

    def get_download_absolute_url(self):
        return reverse(
            'creme_core__download',
            args=(
                self.entity_type_id,
                self.id,
                'filedata',
            )
        )

    def get_entity_summary(self, user):
        if not user.has_perm_to_view(self):
            return self.allowed_str(user)

        if self.mime_type.is_image:
            return format_html(
                '<img class="entity-summary" src="{url}" alt="{name}" title="{name}"/>',
                url=self.get_download_absolute_url(),
                name=self.title,
            )

        return super().get_entity_summary(user)

    def save(self, *args, **kwargs):
        if not self.pk:  # Creation
            mime_name = guess_type(self.filedata.name)[0]

            if mime_name is not None:
                self.mime_type = other_models.MimeType.objects.get_or_create(name=mime_name)[0]

        if not self.title:
            # TODO: truncate but keep extension if possible ?
            assign_2_charfield(self, 'title', basename(self.filedata.path))

        super().save(*args, **kwargs)


class Document(AbstractDocument):
    class Meta(AbstractDocument.Meta):
        swappable = 'DOCUMENTS_DOCUMENT_MODEL'
