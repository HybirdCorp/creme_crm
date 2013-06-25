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

import os
from itertools import chain
from collections import defaultdict
import logging

from django.db import transaction
from django.db.models import Model, CharField, BooleanField, FileField #ForeignKey, Manager
from django.db.models.query_utils import Q
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from ..core.function_field import FunctionFieldsManager
from .fields import CreationDateTimeField, ModificationDateTimeField, CremeUserForeignKey, CTypeForeignKey


logger = logging.getLogger(__name__)


class CremeModel(Model):
    #header_filter_exclude_fields = ['id', 'pk']
    _delete_files = True #Delegate the deletion of the file on system when a model has one or more FileField subclasses
    creation_label = _('Add')

    class Meta:
        abstract = True

    def _pre_delete(self):
        """Called just before deleting the model.
            Could be useful for cleaning, with transaction management, your inherited model as nested transactions
            doesn't work.
        """
        pass

    def _delete_without_transaction(self):
        for m2m_field in self._meta.many_to_many:
            getattr(self, m2m_field.name).clear()

        for related_m2m_field in self._meta.get_all_related_many_to_many_objects():
            getattr(self, related_m2m_field.get_accessor_name()).clear()

        self._pre_delete()
        super(CremeModel, self).delete()

    def delete(self):
        file_fields = []
        _delete_files = self._delete_files

        with transaction.commit_manually(): #TODO: commit_on_success
            try:
                if _delete_files:
                    file_fields = [(field.name, getattr(self, field.name).path, unicode(getattr(self, field.name))) \
                                   for field in chain(self._meta.fields, self._meta.many_to_many) \
                                   if issubclass(field.__class__, FileField)]

                self._delete_without_transaction()
                transaction.commit()
            #except Exception as e:
            except:
                transaction.rollback()
                #NB: logger.whatever() breaks the functioning of commit/rollback feature...
                #logger.debug('Error in CremeModel.delete(): %s', e)
                raise

        if _delete_files:
            obj_filter = self._default_manager.filter
            os_remove = os.remove

            for field_name, full_path, chrooted_path in file_fields:
                if not obj_filter(Q(**{field_name: chrooted_path})).exists():
                    os_remove(full_path)#TODO: Catch OSError ?


#class CremeEntityManager(Manager):
    #def get_query_set(self):
        #return self.even_deleted().filter(is_deleted=False)

    #def only_deleted(self):
        #return self.even_deleted().filter(is_deleted=True)

    #def even_deleted(self):
        #return super(CremeEntityManager, self).get_query_set()


class CremeAbstractEntity(CremeModel):
    created  = CreationDateTimeField(_('Creation date'), editable=False).set_tags(clonable=False)
    modified = ModificationDateTimeField(_('Last modification'), editable=False).set_tags(clonable=False)

    #entity_type = ForeignKey(ContentType, editable=False).set_tags(viewable=False)
    entity_type = CTypeForeignKey(editable=False).set_tags(viewable=False)
    header_filter_search_field = CharField(max_length=200, editable=False).set_tags(viewable=False)

    is_deleted = BooleanField(default=False, editable=False).set_tags(viewable=False)
    is_actived = BooleanField(default=False, editable=False).set_tags(viewable=False)
    user       = CremeUserForeignKey(verbose_name=_('User'))

    #objects = CremeEntityManager()

    _real_entity = None

    #research_fields = []
    function_fields = FunctionFieldsManager()

    #excluded_fields_in_html_output = ['id', 'cremeentity_ptr' , 'entity_type', 'header_filter_search_field', 'is_deleted', 'is_actived'] #use a set
    #header_filter_exclude_fields = CremeModel.header_filter_exclude_fields + ['password', 'is_superuser', 'is_active', 'is_staff']
    #extra_filter_fields = [] #=> Usage: [{'name':'', 'verbose_name':''},...]
    #extra_filter_exclude_fields = ['id']

    class Meta:
        app_label = 'creme_core'
        abstract = True
        ordering = ('id',)

    def __init__ (self, *args , **kwargs):
        super(CremeAbstractEntity, self).__init__(*args , **kwargs)

        if self.pk is None:
            has_arg = kwargs.has_key
            if not has_arg('entity_type') and not has_arg('entity_type_id'):
                self.entity_type = ContentType.objects.get_for_model(self)
        #else:
            #self.entity_type = ContentType.objects.get_for_id(self.entity_type_id)

    def _get_real_entity(self, base_model):
        entity = self._real_entity

        if entity is True:
            return self

        if entity is None:
            ct = self.entity_type
            get_ct = ContentType.objects.get_for_model

            if ct == get_ct(base_model) or ct == get_ct(self.__class__):
                self._real_entity = True #avoid reference to 'self' (cyclic reference)
                entity = self
            else:
                entity = self._real_entity = ct.get_object_for_this_type(id=self.id)
                #entity = self._real_entity = ct.model_class().objects.even_deleted().get(id=self.id)

        return entity

    def get_real_entity(self):
        """Overload in child classes"""
        return self._get_real_entity(CremeAbstractEntity)

    @staticmethod
    def populate_real_entities(entities):
        """Faster than call get_real_entity() of each CremeAbstractEntity object,
        because it groups queries by ContentType.
        @param entities Iterable containing CremeAbstractEntity objects.
                        Beware it can be iterated twice (ie: can't be a generator)
        """
        entities_by_ct = defaultdict(list)

        for entity in entities:
            entities_by_ct[entity.entity_type_id].append(entity.id)

        entities_map = {}
        get_ct = ContentType.objects.get_for_id

        for ct_id, entity_ids in entities_by_ct.iteritems():
            entities_map.update(get_ct(ct_id).model_class().objects.in_bulk(entity_ids))
            #entities_map.update(get_ct(ct_id).model_class().objects.even_deleted().in_bulk(entity_ids))

        for entity in entities:
            entity._real_entity = entities_map[entity.id]
