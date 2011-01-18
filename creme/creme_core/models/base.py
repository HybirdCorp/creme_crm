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

from logging import debug
from collections import defaultdict

from django.core.exceptions  import ObjectDoesNotExist
from django.db.models import Model, ForeignKey, CharField, BooleanField
from django.db.models.fields.related import OneToOneRel
from django.db.models.query_utils import CollectedObjects
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from creme_core.models.function_field import FunctionFieldsManager
from creme_core.models.fields import CreationDateTimeField, ModificationDateTimeField


class CantBeDeleted(Exception):
    pass

def _can_be_deleted(obj, seen_objs, parent=None, nullable=False):
    pk_val = obj._get_pk_val()
    if seen_objs.add(obj.__class__, pk_val, obj, parent, nullable):
        return

    for related in obj._meta.get_all_related_objects():
        rel_opts_name = related.get_accessor_name()

        if isinstance(related.field.rel, OneToOneRel):
            try:
                sub_obj = getattr(obj, rel_opts_name)
            except ObjectDoesNotExist:
                pass
            else:
                sub_obj._can_be_deleted(seen_objs, obj.__class__, related.field.null)
        else:
          # To make sure we can access all elements, we can't use the
            # normal manager on the related object. So we work directly
            # with the descriptor object.
            for cls in obj.__class__.mro():
                if rel_opts_name in cls.__dict__:
                    rel_descriptor = cls.__dict__[rel_opts_name]
                    break
            else:
                raise AssertionError("Should never get here.")

            delete_qs = rel_descriptor.delete_manager(obj).all()

            from creme_core.models.custom_field import _TABLES

            for sub_obj in delete_qs:
                if isinstance(sub_obj, tuple(_TABLES.values())):
                    continue

                target_field = sub_obj._meta.get_field(related.field.name)
                if isinstance(target_field, ForeignKey) and not target_field.null:
                    raise CantBeDeleted("Not null ForeignKey field")

                #sub_obj._collect_sub_objects(seen_objs, self.__class__, related.field.null)

    # Handle any ancestors (for the model-inheritance case). We do this by
    # traversing to the most remote parent classes -- those with no parents
    # themselves -- and then adding those instances to the collection. That
    # will include all the child instances down to "self".
    parent_stack = [p for p in obj._meta.parents.values() if p is not None]
    while parent_stack:
        link = parent_stack.pop()
        parent_obj = getattr(obj, link.name)
        if parent_obj._meta.parents:
            parent_stack.extend(parent_obj._meta.parents.values())
            continue
        # At this point, parent_obj is base class (no ancestor models). So
        # delete it and all its descendents.
        parent_obj._can_be_deleted(seen_objs)

def can_be_deleted(obj):
    try:
        seen_objs = CollectedObjects()
        obj._can_be_deleted(seen_objs)
    except CantBeDeleted:
        return False
    else:
        return True

Model._can_be_deleted = _can_be_deleted
Model.can_be_deleted  = can_be_deleted

class CremeModel(Model):
    
    header_filter_exclude_fields = ['id', 'pk']

    class Meta:
        abstract = True

    def _collect_sub_objects(self, seen_objs, parent=None, nullable=False):
        pk_val = self._get_pk_val()
        if seen_objs.add(self.__class__, pk_val, self, parent, nullable):
            return

        for related in self._meta.get_all_related_objects():
            rel_opts_name = related.get_accessor_name()
            if isinstance(related.field.rel, OneToOneRel):
                try:
                    sub_obj = getattr(self, rel_opts_name)
                except ObjectDoesNotExist:
                    pass
                else:
                    sub_obj._collect_sub_objects(seen_objs, self.__class__, related.field.null)

            else:
              # To make sure we can access all elements, we can't use the
                # normal manager on the related object. So we work directly
                # with the descriptor object.
                for cls in self.__class__.mro():
                    if rel_opts_name in cls.__dict__:
                        rel_descriptor = cls.__dict__[rel_opts_name]
                        break
                else:
                    raise AssertionError("Should never get here.")

                delete_qs = rel_descriptor.delete_manager(self).all()

                for sub_obj in delete_qs:

                    target_field = sub_obj._meta.get_field(related.field.name)
                    if isinstance(target_field, ForeignKey) and target_field.null:
                        setattr(sub_obj, related.field.name, None)
                        sub_obj.save()
                        continue

                    #For cascade deleting
                    #sub_obj._collect_sub_objects(seen_objs, self.__class__, related.field.null)

        # Handle any ancestors (for the model-inheritance case). We do this by
        # traversing to the most remote parent classes -- those with no parents
        # themselves -- and then adding those instances to the collection. That
        # will include all the child instances down to "self".
        parent_stack = [p for p in self._meta.parents.values() if p is not None]
        while parent_stack:
            link = parent_stack.pop()
            parent_obj = getattr(self, link.name)
            if parent_obj._meta.parents:
                parent_stack.extend(parent_obj._meta.parents.values())
                continue
            # At this point, parent_obj is base class (no ancestor models). So
            # delete it and all its descendents.
            parent_obj._collect_sub_objects(seen_objs)


class CremeAbstractEntity(CremeModel):
    created  = CreationDateTimeField(_('Creation date'))
    modified = ModificationDateTimeField(_('Last modification'))

    entity_type = ForeignKey(ContentType, editable=False)
    header_filter_search_field = CharField(max_length=200, editable=False)

    is_deleted = BooleanField(blank=True, default=False)
    is_actived = BooleanField(blank=True, default=False)
    user       = ForeignKey(User, verbose_name=_(u'User'))

    _real_entity = None

    research_fields = []
    function_fields = FunctionFieldsManager()

    excluded_fields_in_html_output = ['id', 'cremeentity_ptr' , 'entity_type', 'header_filter_search_field', 'is_deleted', 'is_actived'] #use a set
    header_filter_exclude_fields = CremeModel.header_filter_exclude_fields + ['password', 'is_superuser', 'is_active', 'is_staff']
    extra_filter_fields = [] #=> Usage: [{'name':'', 'verbose_name':''},...]
    extra_filter_exclude_fields = ['id']

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
        else:
            self.entity_type = ContentType.objects.get_for_id(self.entity_type_id)

    #@classmethod
    #def filter_in_funcfield(cls, func_name, string_filter):
        #f_field = cls.function_fields.get(func_name)

        #if f_field:
            #return f_field.filter_in_result(string_filter)

        #return Q()

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

        return entity

    def get_real_entity(self):
        """Overload in child classes"""
        return self._get_real_entity(CremeAbstractEntity)

    @staticmethod
    def populate_real_entities(entities):
        """Faster than call get_real_entity() of each CremeAbstractEntity object,
        because it groups quries by ContentType.
        @param entities Iterable containing CremeAbstractEntity objects.
                        Beware it can be iterated twice (ie: can't be a generator)
        """
        entities_by_ct = defaultdict(list)

        for entity in entities:
            entities_by_ct[entity.entity_type_id].append(entity.id)

        entities_map = {}
        get_ct = ContentType.objects.get_for_id

        for ct_id in entities_by_ct.iterkeys(): #TODO: use iteritems (entities_by_ct[ct_id]) ??
            entities_map.update(get_ct(ct_id).model_class().objects.in_bulk(entities_by_ct[ct_id]))

        for entity in entities:
            entity._real_entity = entities_map[entity.id]
