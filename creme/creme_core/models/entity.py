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

from collections import defaultdict
from logging import debug



from django.utils.encoding import force_unicode
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

from base import CremeAbstractEntity

from creme_core.models.utils_for_hf import UserAllowedFuncHF

class FPrettyProperties(UserAllowedFuncHF):
    name ="get_pretty_properties"
    verbose_name =u'Propriétés'
        
    @classmethod
    def has_filter(cls):
        return False


class CremeEntity(CremeAbstractEntity):
    Gestion_Droit = ['Lire', 'Créer', 'Modifier', 'Supprimer', 'Mettre en relation avec'] #beuark....
    header_filter_exclude_fields = CremeAbstractEntity.header_filter_exclude_fields + ['id', 'cremeentity_ptr', 'entity_type', 'is_deleted', 'is_actived', 'header_filter_search_field'] #TODO: use a set() ??
    extra_filter_exclude_fields  = CremeAbstractEntity.extra_filter_exclude_fields + ['id', 'cremeentity_ptr', 'header_filter_search_field']

#    users_allowed_func = CremeAbstractEntity.users_allowed_func + [{'name':'get_pretty_properties', 'verbose_name': u'Propriétés'}]
    users_allowed_func = CremeAbstractEntity.users_allowed_func.copy()  
    users_allowed_func.update ({ FPrettyProperties.name : FPrettyProperties })

    class Meta:
        app_label = 'creme_core'
        ordering = ('id',)

    def __init__(self, *args, **kwargs):
        super(CremeEntity, self).__init__(*args, **kwargs)
        self._relations_map = {}
        self._cvalues_map = {}

    def delete(self):
        for relation in self.relations.all():
            relation.delete()

        for prop in self.properties.all():
            prop.delete()

        CustomFieldValue.delete_all(self)

        if settings.TRUE_DELETE and self.can_be_deleted():
            super(CremeEntity, self).delete()
        else:
            self.is_deleted = True
            self.save()

    def __unicode__(self):
        real_entity = self.get_real_entity()

        if self is real_entity:
            return u"Creme entity: %s" % self.id

        return unicode(real_entity)

    @staticmethod
    def get_real_entity_by_id(pk):
        return CremeEntity.objects.get(pk=pk).get_real_entity()

    def get_real_entity(self):
        return self._get_real_entity(CremeEntity)

    def get_absolute_url(self):
        #TODO : /!\ If the derived class hasn't get_absolute_url error max recursion
        real_entity = self.get_real_entity()

        if self is real_entity:
            return "/creme_core/entity/%s" % self.id

        return real_entity.get_absolute_url()

    def get_edit_absolute_url(self):
        return "/creme_core/entity/edit/%s" % self.id

    def get_delete_absolute_url(self):
        return "/creme_core/entity/delete/%s" % self.id

    ##TODO: improve query (list is paginated later, so don't get all object, and return a queryset if possible)
    #def get_list_object_of_specific_relations(self, relation_type_id):
        ##TODO: regroup entities retrieveing by ct to reduce queries ???
        ##return [rel.object_creme_entity for rel in self.relations.filter(type__id=relation_type_id)]
        #return [rel.object_entity for rel in self.relations.filter(type__id=relation_type_id)]
    def get_related_entities(self, relation_type_id, real_entities=True):
        return [relation.object_entity.get_real_entity()
                    for relation in self.get_relations(relation_type_id, real_entities)]

    def get_relations(self, relation_type_id, real_obj_entities=False):
        relations = self._relations_map.get(relation_type_id)

        if relations is None:
            debug('CremeEntity.get_relations(): Cache MISS for id=%s type=%s', self.id, relation_type_id)
            relations = self.relations.filter(type=relation_type_id)

            if real_obj_entities:
                relations = relations.select_related('object_entity')
                Relation.populate_real_object_entities(relations)

            self._relations_map[relation_type_id] = relations
        else:
            debug('CremeEntity.get_relations(): Cache HIT for id=%s type=%s', self.id, relation_type_id)

        return relations

    @staticmethod
    def populate_relations(entities, relation_type_ids):
        relations = Relation.objects.filter(subject_entity__in=[e.id for e in entities], type__in=relation_type_ids)\
                                    .select_related('object_entity')
        Relation.populate_real_object_entities(relations)

        # { Subject_Entity -> { RelationType ->[Relation list] } }
        relations_map = defaultdict(lambda: defaultdict(list))
        for relation in relations:
            relations_map[relation.subject_entity_id][relation.type_id].append(relation)

        for entity in entities:
            for relation_type_id in relation_type_ids:
                entity._relations_map[relation_type_id] = relations_map[entity.id][relation_type_id]
                debug(u'Fill relations cache id=%s type=%s', entity.id, relation_type_id)

    def get_custom_value(self, custom_field):
        cvalue = self._cvalues_map.get(custom_field.id)

        if cvalue is None:
            debug('CremeEntity.get_custom_value(): Cache MISS for id=%s cf_id=%s', self.id, custom_field.id)
            self._cvalues_map[custom_field.id] = cvalue = custom_field.get_pretty_value(self.id)
        else:
            debug('CremeEntity.get_custom_value(): Cache HIT for id=%s cf_id=%s', self.id, custom_field.id)

        return cvalue

    @staticmethod
    def populate_custom_values(entities, custom_fields):
        cvalues_map = CustomField.get_custom_values_map(entities, custom_fields)

        for entity in entities:
            entity_id = entity.id
            for custom_field in custom_fields:
                cf_id = custom_field.id
                entity._cvalues_map[cf_id] = cvalues_map[entity_id].get(cf_id, u'')
                debug(u'Fill custom value cache entity_id=%s cfield_id=%s', entity_id, cf_id)

    def get_entity_summary(self):
        return escape(unicode(self))

    def get_entity_actions(self):
        return u"""<a href="%s">Voir</a> | <a href="%s">Éditer</a> | <a href="%s" onclick="creme.utils.confirmDelete(event, this);">Effacer</a>""" \
                % (self.get_absolute_url(), self.get_edit_absolute_url(), self.get_delete_absolute_url())

    def get_custom_fields_n_values(self):
        cfields = CustomField.objects.filter(content_type=self.entity_type_id) #TODO: in a staticmethod of CustomField ??
        CremeEntity.populate_custom_values([self], cfields)

        return [(cfield, self.get_custom_value(cfield)) for cfield in cfields]

    #TODO: Improve ?
    def get_properties(self):
        return self.properties.all()

    def get_pretty_properties(self):
        return u"""<ul>%s</ul>""" % "".join([u"<li>%s</li>" % p for p in self.get_properties()])



from custom_field import CustomField, CustomFieldValue
from relation import Relation
