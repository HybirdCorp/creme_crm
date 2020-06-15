# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

import logging
from itertools import chain

from django.db.models import FileField, Model
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _

from .file_ref import FileRef

logger = logging.getLogger(__name__)


class CremeModel(Model):
    creation_label = _('Create')
    save_label     = _('Save')
    # TODO: do a complete refactor for _CremeModel.selection_label
    # selection_label = _('Select')

    # TODO: objects = LowNullsQuerySet.as_manager() ??

    class Meta:
        abstract = True

    def _pre_delete(self):
        """Called just before deleting the model.
        It is useful for cleaning, within the delete() transaction.
        """
        pass

    @staticmethod
    def _delete_stored_file(field_value):
        FileRef.objects.create(filedata=str(field_value))

    def _delete_stored_files(self):
        for field in chain(self._meta.fields, self._meta.many_to_many):
            if isinstance(field, FileField):
                fname = field.name
                file_instance = getattr(self, fname)

                if file_instance:
                    self._delete_stored_file(file_instance)

    def _delete_without_transaction(self, using=None, keep_parents=False):
        self._delete_stored_files()
        self._pre_delete()  # TODO: keep_parents ?
        super().delete(using=using, keep_parents=keep_parents)

    def delete(self, using=None, keep_parents=False):
        try:
            with atomic():
                self._delete_without_transaction(using=using)
        except Exception:
            logger.exception('Error in CremeModel.delete()')
            raise
