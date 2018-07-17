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

from mimetypes import guess_type

from django.conf import settings
from django.db.models import CharField, TextField, FileField, ForeignKey, ManyToManyField, PROTECT
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeEntity, Relation

from ..constants import REL_SUB_RELATED_2_DOC
from .other_models import DocumentCategory, MimeType


class AbstractDocument(CremeEntity):
    title       = CharField(_(u'Name'), max_length=100)
    description = TextField(_(u'Description'), blank=True).set_tags(optional=True)
    filedata    = FileField(_(u'File'), max_length=500, upload_to='upload/documents')
    linked_folder = ForeignKey(settings.DOCUMENTS_FOLDER_MODEL,
                               verbose_name=_(u'Folder'), on_delete=PROTECT,
                              )
    mime_type   = ForeignKey(MimeType, verbose_name=_(u'MIME type'),
                             editable=False, on_delete=PROTECT,
                             null=True,
                            )
    categories  = ManyToManyField(DocumentCategory, verbose_name=_(u'Categories'),
                                  # related_name='+',
                                  blank=True,
                                 ).set_tags(optional=True)

    creation_label = _(u'Create a document')
    save_label     = _(u'Save the document')

    class Meta:
        abstract = True
        manager_inheritance_from_future = True
        app_label = 'documents'
        verbose_name = _(u'Document')
        verbose_name_plural = _(u'Documents')
        ordering = ('title',)

    def __str__(self):
        return u'{} - {}'.format(self.linked_folder, self.title)

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

    @staticmethod
    def get_linkeddoc_relations(entity):
        return Relation.objects.filter(subject_entity=entity.id, type=REL_SUB_RELATED_2_DOC)

    def get_dl_url(self):
        import os

        return settings.MEDIA_URL + str(self.filedata).replace(os.sep, '/')

    def get_entity_summary(self, user):
        if not user.has_perm_to_view(self):
            return self.allowed_unicode(user)

        if self.mime_type.is_image:
            return format_html(u'<img class="entity-summary" src="{url}" alt="{name}" title="{name}"/>',
                               url=self.get_dl_url(),
                               name=self.title,
                              )

        return super(AbstractDocument, self).get_entity_summary(user)

    def save(self, *args, **kwargs):
        if not self.pk:  # Creation
            mime_name = guess_type(self.filedata.name)[0]

            if mime_name is not None:
                self.mime_type = MimeType.objects.get_or_create(name=mime_name)[0]

        super(AbstractDocument, self).save(*args, **kwargs)


class Document(AbstractDocument):
    class Meta(AbstractDocument.Meta):
        swappable = 'DOCUMENTS_DOCUMENT_MODEL'
