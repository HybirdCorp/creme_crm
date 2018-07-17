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

# from collections import defaultdict
from itertools import chain
import logging

# from django.contrib.contenttypes.models import ContentType
from django.db.models import Model, FileField  # CharField, BooleanField, Manager
from django.db.transaction import atomic
from django.utils.translation import ugettext_lazy as _

# from ..core.function_field import FunctionFieldsManager
# from .fields import (CreationDateTimeField, ModificationDateTimeField,
#          CremeUserForeignKey, CTypeForeignKey)
from .file_ref import FileRef
# from .manager import LowNullsQuerySet


logger = logging.getLogger(__name__)


class CremeModel(Model):
    creation_label = _(u'Create')
    save_label     = _(u'Save')
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

    def _delete_m2m(self):
        for m2m_field in self._meta.many_to_many:
            getattr(self, m2m_field.name).clear()

        for related_m2m_field in (f for f in self._meta.get_fields(include_hidden=True)
                                    if f.many_to_many and f.auto_created
                                 ):
            getattr(self, related_m2m_field.get_accessor_name()).clear()

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
        self._delete_m2m()
        self._delete_stored_files()
        self._pre_delete()  # TODO: keep_parents ?
        super(CremeModel, self).delete(using=using, keep_parents=keep_parents)

    def delete(self, using=None, keep_parents=False):
        try:
            with atomic():
                self._delete_without_transaction(using=using)
        except:
            logger.exception('Error in CremeModel.delete()')
            raise


# class CremeEntityManager(Manager):
#     def get_query_set(self):
#         return self.even_deleted().filter(is_deleted=False)
#
#     def only_deleted(self):
#         return self.even_deleted().filter(is_deleted=True)
#
#     def even_deleted(self):
#         return super(CremeEntityManager, self).get_query_set()

# _SEARCH_FIELD_MAX_LENGTH = 200


# class CremeAbstractEntity(CremeModel):
#     created  = CreationDateTimeField(_(u'Creation date'), editable=False).set_tags(clonable=False)
#     modified = ModificationDateTimeField(_(u'Last modification'), editable=False).set_tags(clonable=False)
#
#     entity_type = CTypeForeignKey(editable=False).set_tags(viewable=False)
#     header_filter_search_field = CharField(max_length=_SEARCH_FIELD_MAX_LENGTH, editable=False).set_tags(viewable=False)
#
#     is_deleted = BooleanField(default=False, editable=False).set_tags(viewable=False)
#     user       = CremeUserForeignKey(verbose_name=_(u'Owner user'))
#
#     # objects = CremeEntityManager()
#     # objects = Manager()
#     objects = LowNullsQuerySet.as_manager()
#
#     _real_entity = None
#
#     function_fields = FunctionFieldsManager()
#
#     class Meta:
#         app_label = 'creme_core'
#         abstract = True
#         ordering = ('id',)
#
#     def __init__ (self, *args , **kwargs):
#         super(CremeAbstractEntity, self).__init__(*args, **kwargs)
#
#         if self.pk is None:
#             has_arg = kwargs.has_key
#             if not has_arg('entity_type') and not has_arg('entity_type_id'):
#                 self.entity_type = ContentType.objects.get_for_model(self)
#
#     def _get_real_entity(self, base_model):
#         entity = self._real_entity
#
#         if entity is True:
#             return self
#
#         if entity is None:
#             ct = self.entity_type
#             get_ct = ContentType.objects.get_for_model
#
#             if ct == get_ct(base_model) or ct == get_ct(self.__class__):
#                 self._real_entity = True  # Avoid reference to 'self' (cyclic reference)
#                 entity = self
#             else:
#                 entity = self._real_entity = ct.get_object_for_this_type(id=self.id)
#
#         return entity
#
#     def get_real_entity(self):
#         """Overload in child classes"""
#         return self._get_real_entity(CremeAbstractEntity)
#
#     @staticmethod
#     def populate_real_entities(entities):
#         """Faster than call get_real_entity() of each CremeAbstractEntity object,
#         because it groups queries by ContentType.
#         @param entities: Iterable containing CremeAbstractEntity objects.
#                          Beware it can be iterated twice (ie: can't be a generator)
#         """
#         entities_by_ct = defaultdict(list)
#
#         for entity in entities:
#             entities_by_ct[entity.entity_type_id].append(entity.id)
#
#         entities_map = {}
#         get_ct = ContentType.objects.get_for_id
#
#         for ct_id, entity_ids in entities_by_ct.iteritems():
#             entities_map.update(get_ct(ct_id).model_class().objects.in_bulk(entity_ids))
#
#         for entity in entities:
#             entity._real_entity = entities_map[entity.id]
