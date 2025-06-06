################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
import uuid
from itertools import chain

from django.core.exceptions import ValidationError
from django.core.validators import EMPTY_VALUES
from django.db import models
from django.db.models import FileField
from django.db.transaction import atomic
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from .file_ref import FileRef

logger = logging.getLogger(__name__)


class CremeModel(models.Model):
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

    # @staticmethod
    # def _delete_stored_file(field_value):
    def _delete_stored_file(self, field_value):
        max_length = FileRef._meta.get_field('filedata').max_length
        path = str(field_value)
        if len(path) > max_length:
            logger.critical(
                'Error while deleting an instance of <%s>; '
                'the FileRef cannot be created because the path "%s" is longer '
                'than %s. The file will not be cleaned by the cleaner Job, you '
                'have to remove it manually (to free disk space).',
                type(self).__name__, path, max_length,
            )
        else:
            FileRef.objects.create(
                filedata=path,
                description=gettext('Deletion of «{}»').format(self),
            )

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

    def full_clean(self, *args, **kwargs):
        super().full_clean(*args, **kwargs)

        from .fields_config import FieldsConfig

        model = type(self)
        errors = {
            fname: gettext(
                'The field «{}» has been configured as required.'
            ).format(
                model._meta.get_field(fname).verbose_name
            )
            for fname in FieldsConfig.objects.get_for_model(model).required_field_names
            if getattr(self, fname) in EMPTY_VALUES
        }

        if errors:
            raise ValidationError(errors)


class MinionModel(CremeModel):
    """Base model which is great for small models used to represent "choices" in
    entities & which you classically register in creme_config.
    """
    uuid = models.UUIDField(
        unique=True, editable=False, default=uuid.uuid4,
    ).set_tags(viewable=False)

    # Used by creme_config (if is_custom is False, the instance cannot be deleted)
    is_custom = models.BooleanField(editable=False, default=True).set_tags(viewable=False)

    # Can be used by third party code to store the data they want,
    # without having to modify the code.
    extra_data = models.JSONField(editable=False, default=dict).set_tags(viewable=False)

    class Meta:
        abstract = True
