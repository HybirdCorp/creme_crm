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

from __future__ import annotations

import logging
import uuid
from itertools import chain

from django.core.exceptions import ValidationError
from django.core.validators import EMPTY_VALUES
from django.db import models
from django.db.models import FileField, Model
from django.db.transaction import atomic
from django.dispatch import receiver
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from . import fields as core_fields
from .file_ref import FileRef

logger = logging.getLogger(__name__)


# Contribute -------------------------------------------------------------------
# get_m2m_values() ---
_M2M_CACHE_NAME = '_creme_m2m_values_cache'


# TODO: accept field instance?
# TODO: add a size limit?
def _get_m2m_values(self: Model, field_name: str) -> list[Model]:
    """Get the instances related to a ManyToManyField as a list.
    The important thing is that the list is kept in a cache:
        - Only the first call will perform a query
          (hint: you can avoid it with 'prefetch_related()).
        - The cache is cleared if the field is modified
          (see the signal handler '_update_m2m_cache()' below).

    NB: using 'get_m2m_values' allows a code to work with an instance built by
        'Snapshot.get_initial_instance()'.

    @param field_name: Name of a ManyToManyField.
    @return: List of instances linked by the M2M.
    """
    field = type(self)._meta.get_field(field_name)
    if not field.many_to_many:
        raise TypeError(f'"{field_name}" is not a ManyToManyField')

    cache = getattr(self, _M2M_CACHE_NAME, None)
    if cache is None:
        cache = {}
        setattr(self, _M2M_CACHE_NAME, cache)

    values = cache.get(field_name)
    if values is None:
        values = [*getattr(self, field_name).all()]
        cache[field_name] = values
    # TODO: keep the cache up-to-date instead? (see signal handler too)
    #   else:
    #     from django.utils.functional import partition
    #     field_obj = type(self)._meta.get_field(field_name)
    #     rel_model = field_obj.related_model
    #     pks, instances = partition(
    #         lambda value: isinstance(value, rel_model), values,
    #     )
    #     if pks:
    #         values = [*instances, *rel_model.objects.filter(pk__in=pks)]
    #         # todo: empty ordering?
    #         # toto: separated function (+ several fields, unicode...)
    #         ordering = rel_model._meta.ordering[0]
    #         values.sort(key=lambda o: getattr(o, ordering))
    #         cache[field_name] = values

    return values


# That's patching time baby!
assert not hasattr(Model, 'get_m2m_values')
Model.get_m2m_values = _get_m2m_values


@receiver(models.signals.m2m_changed, dispatch_uid='creme_core-update_m2m_cache')
def _update_m2m_cache(sender, instance, action, pk_set, **kwargs):
    if action == 'post_add':
        setattr(instance, _M2M_CACHE_NAME, None)
        # TODO: keep the cache up to date instead?
        #   cache = getattr(instance, _M2M_CACHE_NAME, None)
        #   if cache is not None:
        #       values = cache.get(field_name)
        #       if values is not None:
        #           values.extend(pk_set)
    elif action == 'post_remove':
        setattr(instance, _M2M_CACHE_NAME, None)
        # TODO: keep the cache up to date instead?
        #   cache = getattr(instance, _M2M_CACHE_NAME, None)
        #   if cache is not None:
        #       values = cache.get(field_name)
        #       if values is not None:
        #           cache[field_name] = [
        #               # todo: manage simple PKs (added just before)
        #               value for value in values if value.pk not in pk_set
        #           ]
    elif action == 'post_clear':
        cache = getattr(instance, _M2M_CACHE_NAME, None)
        if cache is not None:
            for field in type(instance)._meta.many_to_many:
                if sender is field.remote_field.through:
                    cache[field.attname].clear()
                    break
            else:
                logger.critical('ManyToManyField not found: %s', sender)


# is_referenced ---

# TODO: another method ("populate_is_referenced"?) to group queries for several instances
def _is_referenced(self: Model) -> bool:
    """Is this instance referenced by a ForeignKey or A ManyToManyField?"""
    # TODO: store a (limited) list of referencing instance in order
    #       to build message error indicating which instances are concerned.
    meta = self._meta

    for rel_objects in (f for f in meta.get_fields() if f.one_to_many):
        if getattr(self, rel_objects.get_accessor_name()).exists():
            return True

    for rel_objects in (
        f for f in meta.get_fields(include_hidden=True) if f.many_to_many
    ):
        if getattr(self, rel_objects.get_accessor_name()).exists():
            return True

    return False


# That's patching time baby!
assert not hasattr(Model, 'is_referenced')
Model.is_referenced = property(_is_referenced)

# Contribute [end] ----------------------------------------------------------------


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


class MinionManager(models.Manager):
    def get_by_portable_key(self, key: str) -> MinionModel:
        return self.get(uuid=key)


class MinionModel(CremeModel):
    """Base model which is great for small models used to represent "choices" in
    entities & which you classically register in creme_config.
    """
    uuid = models.UUIDField(
        unique=True, editable=False, default=uuid.uuid4,
    ).set_tags(viewable=False)

    # Not viewable by users, For administrators currently.
    created = core_fields.CreationDateTimeField(_('Creation date')).set_tags(viewable=False)
    modified = core_fields.ModificationDateTimeField(
        _('Last modification'),
    ).set_tags(viewable=False)

    # Used by creme_config (if is_custom is False, the instance cannot be deleted)
    is_custom = models.BooleanField(editable=False, default=True).set_tags(viewable=False)

    # Can be used by third party code to store the data they want,
    # without having to modify the code.
    extra_data = models.JSONField(editable=False, default=dict).set_tags(viewable=False)

    objects = MinionManager()

    class Meta:
        abstract = True

    def portable_key(self) -> str:
        """See CremeEntity.portable_key()."""
        return str(self.uuid)
