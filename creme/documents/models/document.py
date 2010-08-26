# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.db.models import CharField, TextField, FileField, ForeignKey
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_unicode
from django.contrib.auth.models import User

from creme_core.models import CremeEntity, Relation

from folder import Folder
from documents.constants import REL_SUB_RELATED_2_DOC


class Document(CremeEntity):
    title       = CharField(_(u'Title'), max_length=100, blank=True , null=True, unique=True)
    description = TextField(_(u'Description'))
    filedata    = FileField(_(u'File'), max_length=500, upload_to='upload/documents')
    folder      = ForeignKey(Folder, verbose_name=_(u'Folder'), blank=False, null=False)

    research_fields = CremeEntity.research_fields + ['title', 'description', 'folder__title']

    class Meta:
        app_label = 'documents'
        verbose_name = _('Document')
        verbose_name_plural = _(u'Documents')

    def __unicode__(self):
        return force_unicode(u'%s - %s' % (self.folder.title, self.title))

    def get_absolute_url(self):
        return "/documents/document/%s" % self.id

    def get_edit_absolute_url(self):
        return "/documents/document/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/documents/documents"

    def get_delete_absolute_url(self):
        return "/documents/document/delete/%s" % self.id

    @staticmethod
    def get_linkeddoc_relations(entity):
        #TODO: return Document(relations__object_entity=entity, relations__type__id=REL_OBJ_RELATED_2_DOC) instead ????
        return Relation.objects.filter(subject_entity=entity, type__id=REL_SUB_RELATED_2_DOC)
