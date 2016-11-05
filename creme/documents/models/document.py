# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models import CharField, TextField, FileField, ForeignKey, PROTECT
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeEntity, Relation

from ..constants import REL_SUB_RELATED_2_DOC


class AbstractDocument(CremeEntity):
    title       = CharField(_(u'Title'), max_length=100)
    description = TextField(_(u'Description'), blank=True).set_tags(optional=True)
    filedata    = FileField(_(u'File'), max_length=500, upload_to='upload/documents')
    folder      = ForeignKey(settings.DOCUMENTS_FOLDER_MODEL,
                             verbose_name=_(u'Folder'), on_delete=PROTECT,
                            )

    creation_label = _('Add a document')
    save_label     = _('Save the document')

    class Meta:
        abstract = True
        app_label = 'documents'
        verbose_name = _('Document')
        verbose_name_plural = _(u'Documents')
        ordering = ('title',)

    def __unicode__(self):
        return u'%s - %s' % (self.folder, self.title)

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


class Document(AbstractDocument):
    class Meta(AbstractDocument.Meta):
        swappable = 'DOCUMENTS_DOCUMENT_MODEL'
