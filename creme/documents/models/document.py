# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.db.models import CharField, TextField, FileField, ForeignKey, PROTECT
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity, Relation

from folder import Folder
from documents.constants import REL_SUB_RELATED_2_DOC


class Document(CremeEntity):
    title       = CharField(_(u'Title'), max_length=100)
    description = TextField(_(u'Description'), blank=True, null=True)
    filedata    = FileField(_(u'File'), max_length=500, upload_to='upload/documents')
    folder      = ForeignKey(Folder, verbose_name=_(u'Folder'), on_delete=PROTECT)

    #research_fields = CremeEntity.research_fields + ['title', 'description', 'folder__title']
    creation_label = _('Add a document')

    class Meta:
        app_label = 'documents'
        verbose_name = _('Document')
        verbose_name_plural = _(u'Documents')

    def __unicode__(self):
        return u'%s - %s' % (self.folder, self.title)

    def get_absolute_url(self):
        return "/documents/document/%s" % self.id

    def get_edit_absolute_url(self):
        return "/documents/document/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/documents/documents"

    @staticmethod
    def get_linkeddoc_relations(entity):
        return Relation.objects.filter(subject_entity=entity.id, type=REL_SUB_RELATED_2_DOC)
