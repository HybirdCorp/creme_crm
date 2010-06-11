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

from django.db.models import CharField, TextField, ForeignKey
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity

from other_models import FolderCategory


class Folder(CremeEntity):
    """Folder: contains Documents"""
    title         = CharField(_(u'Titre'), max_length=100, blank=False, null=False, unique=True)
    description   = TextField()

    parent_folder = ForeignKey('self', verbose_name=_(u'Classeur parent'), blank=True, null=True, related_name='parent_folder_set')
    category      = ForeignKey(FolderCategory, verbose_name=_(u'Catégorie'), blank=True, null=True, related_name='folder_category_set')

    research_fields = CremeEntity.research_fields + ['title', 'description', 'parent_folder__title', 'category__name']
    #users_allowed_func = CremeEntity.users_allowed_func + []

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return "/documents/folder/%s" % self.id

    def get_edit_absolute_url(self):
        return "/documents/folder/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/documents/folders"

    class Meta:
        app_label = 'documents'
        verbose_name = _('Classeur')
        verbose_name_plural = _(u'Classeurs')
