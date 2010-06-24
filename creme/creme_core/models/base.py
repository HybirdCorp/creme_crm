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

from django.core.exceptions  import ObjectDoesNotExist
from django.db.models import Model, ForeignKey, CharField, BooleanField
from django.db.models.fields.related import OneToOneRel
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from django_extensions.db.models import TimeStampedModel


class CremeModel(Model):
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


class CremeAbstractEntity(CremeModel, TimeStampedModel):
    entity_type = ForeignKey(ContentType, editable=False)
    header_filter_search_field = CharField(max_length=200, editable=False)

    is_deleted = BooleanField(blank=True, default=False)
    is_actived = BooleanField(blank=True, default=False)
    user       = ForeignKey(User, verbose_name=_(u'Utilisateur'))

    _real_entity = None

    research_fields = []
    users_allowed_func = [] #=> Usage: [{'name':'', 'verbose_name':''},...]
    excluded_fields_in_html_output = ['id', 'cremeentity_ptr' , 'entity_type', 'header_filter_search_field', 'is_deleted', 'is_actived'] #use a set
    header_filter_exclude_fields = []
    extra_filter_fields = [] #=> Usage: [{'name':'', 'verbose_name':''},...]
    extra_filter_exclude_fields = ['id']

    class Meta:
        app_label = 'creme_core'
        abstract = True
        ordering = ('id',)

    def __init__ (self, *args , **kwargs):
        super(CremeAbstractEntity, self).__init__(*args , **kwargs)

        #correction d'un bug dont il faut créer le ticket
        if self.pk is None and not kwargs.has_key('entity_type') and not kwargs.has_key('entity_type_id'):
            self.entity_type = ContentType.objects.get_for_model(self)

    @classmethod
    def get_users_func_verbose_name(cls, func_name):
        func_name = str(func_name) #??
        for dic in cls.users_allowed_func:
            if str(dic['name']) == func_name:
                return dic['verbose_name']
        return ''

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
