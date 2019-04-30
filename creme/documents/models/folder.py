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

from random import randint

from django.db.models import CharField, TextField, ForeignKey, SET_NULL, PROTECT
from django.urls import reverse
from django.utils.translation import gettext_lazy as _, gettext

from creme.creme_core.core.exceptions import SpecificProtectedError
from creme.creme_core.models import CremeEntity
from creme.creme_core.utils import truncate_str

from .. import constants
from .other_models import FolderCategory

MAXINT = 100000


class AbstractFolder(CremeEntity):
    """Folder: contains Documents"""
    title         = CharField(_('Title'), max_length=100)
    description   = TextField(_('Description'), blank=True).set_tags(optional=True)
    parent_folder = ForeignKey('self', verbose_name=_('Parent folder'),
                               blank=True, null=True,
                               related_name='children',
                               on_delete=PROTECT,
                              )
    category      = ForeignKey(FolderCategory, verbose_name=_('Category'),
                               blank=True, null=True, on_delete=SET_NULL,
                               related_name='folder_category_set',
                              )

    allowed_related = CremeEntity.allowed_related | {'document'}

    not_deletable_UUIDs = {constants.UUID_FOLDER_RELATED2ENTITIES,
                           constants.UUID_FOLDER_IMAGES,
                          }

    creation_label = _('Create a folder')
    save_label     = _('Save the folder')

    class Meta:
        abstract = True
        manager_inheritance_from_future = True
        app_label = 'documents'
        unique_together = ('title', 'parent_folder', 'category')
        verbose_name = _('Folder')
        verbose_name_plural = _('Folders')
        ordering = ('title',)

    def __str__(self):
        return self.title

    def _check_deletion(self):
        if str(self.uuid) in self.not_deletable_UUIDs:
            raise SpecificProtectedError(gettext('This folder is a system folder.'), [self])

    def get_absolute_url(self):
        return reverse('documents__view_folder', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('documents__create_folder')

    def get_edit_absolute_url(self):
        return reverse('documents__edit_folder', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('documents__list_folders')

    def _pre_save_clone(self, source):
        max_length = self._meta.get_field('title').max_length
        self.title = truncate_str(source.title, max_length,
                                  suffix=' ({} {:08x})'.format(gettext('Copy'),
                                                               randint(0, MAXINT),
                                                              ),
                                 )

        # TODO: atomic
        while Folder.objects.filter(title=self.title).exists():
            self._pre_save_clone(source)

    def already_in_children(self, other_folder_id):
        children = self.children.all()

        for child in children:
            if child.id == other_folder_id:
                return True

        for child in children:
            if child.already_in_children(other_folder_id):
                return True

        return False

    def delete(self, *args, **kwargs):
        self._check_deletion()  # Should not be useful (trashing should be blocked too)
        super().delete(*args, **kwargs)

    def get_parents(self):
        parents = []
        parent = self.parent_folder

        if parent:
            parents.append(parent)
            parents.extend(parent.get_parents())

        return parents

    def trash(self):
        self._check_deletion()
        super().trash()


class Folder(AbstractFolder):
    class Meta(AbstractFolder.Meta):
        swappable = 'DOCUMENTS_FOLDER_MODEL'
