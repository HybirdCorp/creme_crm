# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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
import logging
import warnings

#from django.db import models
from django.db.models import ForeignKey, Q
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, ugettext
#from django.conf import settings
from django.forms.util import flatatt

from ..core.function_field import FunctionField, FunctionFieldResult, FunctionFieldResultsList
from .base import CremeAbstractEntity


logger = logging.getLogger(__name__)


class EntityAction(object):
    def __init__(self, url, text, is_allowed, attrs=None, icon=None):
        self.url = url
        self.text = text
        self.attrs = mark_safe(flatatt(attrs or {}))
        self.icon = icon
        self.is_allowed = is_allowed


class _PrettyPropertiesField(FunctionField):
    name         = "get_pretty_properties"
    verbose_name = _(u'Properties')

    def __call__(self, entity):
        return FunctionFieldResultsList(FunctionFieldResult(unicode(p)) for p in entity.get_properties())

    @classmethod
    def populate_entities(cls, entities):
        CremeEntity.populate_properties(entities)


class CremeEntity(CremeAbstractEntity):
    function_fields = CremeAbstractEntity.function_fields.new(_PrettyPropertiesField())
    allowed_related = set() #Currently used in reports (can be used elsewhere ?) to allow reporting on those related fields #TODO: use tag instead
    creation_label = _('Add an entity')

    class Meta:
        app_label = 'creme_core'
        ordering = ('id',)

    def __init__(self, *args, **kwargs):
        super(CremeEntity, self).__init__(*args, **kwargs)
        self._relations_map = {}
        self._properties = None
        self._cvalues_map = {}

    def delete(self):
        from .history import _get_deleted_entity_ids

        #pre-delete signal is sent to auxiliary _before_, then sent to the entity
        # so it causes problem with aux_deletion line that reference the entity
        # (e.g.:this problem appears when deleting an EmailCampign with Sendings)
        _get_deleted_entity_ids().add(self.id)

        super(CremeEntity, self).delete()

    def __unicode__(self):
        real_entity = self.get_real_entity()

        if self is real_entity:
            return u"Creme entity: %s" % self.id

        return unicode(real_entity)

    def allowed_unicode(self, user):
        return unicode(self) if user.has_perm_to_view(self) else ugettext(u'Entity #%s (not viewable)') % self.id

    #XXX: all deprecated methods commented on 23/01/2014
    #def can_change(self, user):
        #warnings.warn("CremeEntity.can_change() method is deprecated; use User.has_perm_to_change() instead",
                      #DeprecationWarning
                     #)
        #return user.has_perm_to_change(self)

    #def can_change_or_die(self, user):
        #warnings.warn("CremeEntity.can_change_or_die() method is deprecated; use User.has_perm_to_change_or_die() instead",
                      #DeprecationWarning
                     #)
        #user.has_perm_to_change_or_die(self)

    #def can_delete(self, user):
        #warnings.warn("CremeEntity.can_delete() method is deprecated; use User.has_perm_to_delete() instead",
                      #DeprecationWarning
                     #)
        #return user.has_perm_to_delete(self)

    #def can_delete_or_die(self, user):
        #warnings.warn("CremeEntity.can_delete_or_die() method is deprecated; use User.has_perm_to_delete_or_die() instead",
                      #DeprecationWarning
                     #)
        #user.has_perm_to_delete_or_die(self)

    #def can_link(self, user):
        #warnings.warn("CremeEntity.can_link() method is deprecated; use User.has_perm_to_link() instead",
                      #DeprecationWarning
                     #)
        #return user.has_perm_to_link(self)

    #def can_link_or_die(self, user):
        #warnings.warn("CremeEntity.can_link_or_die() method is deprecated; use User.has_perm_to_link_or_die() instead",
                      #DeprecationWarning
                     #)
        #user.has_perm_to_link_or_die(self)

    #def can_unlink(self, user):
        #warnings.warn("CremeEntity.can_unlink() method is deprecated; use User.has_perm_to_unlink() instead",
                      #DeprecationWarning
                     #)
        #return user.has_perm_to_unlink(self)

    #def can_unlink_or_die(self, user):
        #warnings.warn("CremeEntity.can_unlink_or_die() method is deprecated; use User.has_perm_to_unlink_or_die() instead",
                      #DeprecationWarning
                     #)
        #user.has_perm_to_unlink_or_die(self)

    #def can_view(self, user):
        #warnings.warn("CremeEntity.can_view() method is deprecated; use User.has_perm_to_view() instead",
                      #DeprecationWarning
                     #)
        #return user.has_perm_to_view(self)

    #def can_view_or_die(self, user):
        #warnings.warn("CremeEntity.can_view_or_die() method is deprecated; use User.has_perm_to_view_or_die() instead",
                      #DeprecationWarning
                     #)
        #user.has_perm_to_view_or_die(self)

    #@staticmethod
    #def populate_credentials(entities, user):
        #warnings.warn("CremeEntity.populate_credentials() method is deprecated & useless.",
                      #DeprecationWarning
                     #)

    @staticmethod
    def get_real_entity_by_id(pk):
        warnings.warn("CremeEntity.get_real_entity_by_id() method is deprecated (because it is probably useless).",
                      DeprecationWarning
                     )
        return CremeEntity.objects.get(pk=pk).get_real_entity()

    def get_real_entity(self):
        return self._get_real_entity(CremeEntity)

    def get_absolute_url(self):
        real_entity = self.get_real_entity()

        if self is real_entity:
            return "/creme_core/entity/%s" % self.id

        return real_entity.get_absolute_url()

    def get_edit_absolute_url(self):
        """Returns the url of the edition view for this instance.
        If '' (void string) is returned, the model can not be edited directly.
        eg: return "/my_app/my_model/edit/%s" % self.id
        """
        #return "/creme_core/entity/edit/%s" % self.id
        return ''

    def get_delete_absolute_url(self):
        """Returns the url of the deletion view (should use POST method) for this instance.
        If '' (void string) is returned, the model can not be deleted directly.
        """
        return "/creme_core/entity/delete/%s" % self.id

    def get_related_entities(self, relation_type_id, real_entities=True):
        return [relation.object_entity.get_real_entity()
                    for relation in self.get_relations(relation_type_id, real_entities)
               ]

    def get_relations(self, relation_type_id, real_obj_entities=False):
        relations = self._relations_map.get(relation_type_id)

        if relations is None:
            logger.debug('CremeEntity.get_relations(): Cache MISS for id=%s type=%s', self.id, relation_type_id)
            relations = self.relations.filter(type=relation_type_id).order_by('id')

            if real_obj_entities:
                relations = list(relations.select_related('object_entity'))
                Relation.populate_real_object_entities(relations)

            self._relations_map[relation_type_id] = relations
        else:
            logger.debug('CremeEntity.get_relations(): Cache HIT for id=%s type=%s', self.id, relation_type_id)

        return relations

    @staticmethod
    #def populate_relations(entities, relation_type_ids, user):
    def populate_relations(entities, relation_type_ids):
        relations = Relation.objects.filter(subject_entity__in=[e.id for e in entities],
                                            type__in=relation_type_ids,
                                           )\
                                    .select_related('object_entity')
        #Relation.populate_real_object_entities(relations, user)
        Relation.populate_real_object_entities(relations)

        # { Subject_Entity -> { RelationType ->[Relation list] } }
        relations_map = defaultdict(lambda: defaultdict(list))
        for relation in relations:
            relations_map[relation.subject_entity_id][relation.type_id].append(relation)

        for entity in entities:
            for relation_type_id in relation_type_ids:
                entity._relations_map[relation_type_id] = relations_map[entity.id][relation_type_id]
                logger.debug(u'Fill relations cache id=%s type=%s', entity.id, relation_type_id)

    def get_custom_value(self, custom_field):
        cvalue = self._cvalues_map.get(custom_field.id)

        if cvalue is None:
            logger.debug('CremeEntity.get_custom_value(): Cache MISS for id=%s cf_id=%s', self.id, custom_field.id)
            self._cvalues_map[custom_field.id] = cvalue = custom_field.get_pretty_value(self.id)
        else:
            logger.debug('CremeEntity.get_custom_value(): Cache HIT for id=%s cf_id=%s', self.id, custom_field.id)

        return cvalue

    @staticmethod
    def populate_custom_values(entities, custom_fields):
        cvalues_map = CustomField.get_custom_values_map(entities, custom_fields)

        for entity in entities:
            entity_id = entity.id
            for custom_field in custom_fields:
                cf_id = custom_field.id
                entity._cvalues_map[cf_id] = cvalues_map[entity_id].get(cf_id, u'')
                logger.debug(u'Fill custom value cache entity_id=%s cfield_id=%s', entity_id, cf_id)

    def get_entity_summary(self, user):
        return escape(self.allowed_unicode(user))

    def get_entity_m2m_summary(self, user):
        """Return a string summary useful for list (ie: <ul><li>) representation."""
        warnings.warn("CremeEntity.get_entity_m2m_summary() method is deprecated; use CremeEntity.get_entity_summary() instead",
                      DeprecationWarning
                     )

        if not user.has_perm_to_view(self):
            return self.allowed_unicode(user)

        return '<a target="_blank" href="%s">%s</a>' % (self.get_absolute_url(), escape(unicode(self)))

    def get_actions(self, user): #TODO: improve icon/css class management....
        actions = []

        edit_url = self.get_edit_absolute_url()
        if edit_url:
            actions.append(EntityAction(edit_url, ugettext('Edit'),
                                user.has_perm_to_change(self), icon='images/edit_16.png'
                               )
                           )

        delete_url = self.get_delete_absolute_url()
        if delete_url:
            actions.append(EntityAction(delete_url, ugettext('Delete'),
                                        user.has_perm_to_delete(self),
                                        icon='images/delete_16.png',
                                        attrs={'class': 'confirm post ajax lv_reload'},
                                       )
                          )

        return {'default': EntityAction(self.get_absolute_url(), ugettext('See'),
                                        is_allowed=True, icon='images/view_16.png',
                                       ),
                'others':  actions,
               }

    def get_custom_fields_n_values(self):
        cfields = CustomField.objects.filter(content_type=self.entity_type_id) #TODO: in a staticmethod of CustomField ??
        CremeEntity.populate_custom_values([self], cfields)

        return [(cfield, self.get_custom_value(cfield)) for cfield in cfields]

    def get_properties(self):
        if self._properties is None:
            logger.debug('CremeEntity.get_properties(): Cache MISS for id=%s', self.id)
            self._properties = list(self.properties.all().select_related('type'))
        else:
            logger.debug('CremeEntity.get_properties(): Cache HIT for id=%s', self.id)

        return self._properties

    @staticmethod
    def populate_properties(entities):
        properties_map = defaultdict(list)

        #NB1: listify entities in order to avoid subquery (that is not supported by some DB backends)
        #NB2: list of id in order to avoid strange queries that retrieve base CremeEntities (ORM problem ?)
        entities_ids = [entity.id for entity in entities]

        for prop in CremeProperty.objects.filter(creme_entity__in=entities_ids).select_related('type'):
            properties_map[prop.creme_entity_id].append(prop)

        for entity in entities:
            entity_id = entity.id
            logger.debug(u'Fill properties cache entity_id=%s', entity_id)
            entity._properties = properties_map[entity_id]

    @staticmethod
    def populate_fk_fields(entities, field_names):
        """@param entities Sequence of CremeEntity (iterated several times -> not an iterator)
                           with the _same_ ContentType.
        """
        if not entities:
            return

        get_field = entities[0]._meta.get_field_by_name

        for fname in field_names:
            field = get_field(fname)[0]

            if isinstance(field, ForeignKey):
                ids = set()
                for entity in entities:
                    attr_id = getattr(entity, fname + '_id')
                    if attr_id:
                        ids.add(attr_id)

                attr_values = {o.id: o for o in field.rel.to.objects.filter(pk__in=ids)}

                for entity in entities:
                    attr_id = getattr(entity, fname + '_id')
                    if attr_id:
                        setattr(entity, fname, attr_values[attr_id])

    def save(self, *args, **kwargs):
        self.header_filter_search_field = self._search_field_value()

        super(CremeEntity, self).save(*args, **kwargs)
        logger.debug('CremeEntity.save(%s, %s)', args, kwargs)

    def _search_field_value(self):
        """Overload this method if you want to customise the value to search on your CremeEntity type."""
        return unicode(self)

    def _clone_custom_values(self, source):
        for custom_field in CustomField.objects.filter(content_type=source.entity_type_id):
            custom_value_klass = custom_field.get_value_class()
            try:
                value = custom_value_klass.objects.get(custom_field=custom_field.id, entity=source.id).value
            except custom_value_klass.DoesNotExist:
                continue
            else:
                if hasattr(value, 'id'):
                    value = value.id
                elif hasattr(value, 'all'):
                    value = list(value.all())
                CustomFieldValue.save_values_for_entities(custom_field, [self], value)

    def _pre_save_clone(self, source):
        """Called just before saving the entity which is already populated with source attributes (except m2m)"""
        pass

    def _post_save_clone(self, source):
        """Called just after saving the entity (m2m and custom fields are not already cloned & saved)"""
        pass

    def _post_clone(self, source):
        """Called after all clone operations (object cloned with all his m2m, custom values, properties and relations"""
        pass

    def _clone_m2m(self, source):
        """Handle the clone of all many to many fields"""
        for field in source._meta.many_to_many:
            field_name = field.name
            setattr(self, field_name, getattr(source, field_name).all())

    def _clone_object(self):
        """Clone and returns a new saved instance of self
        NB: Clones also customs values
        """
        fields_kv = {}

        for field in self._meta.fields:
            if field.get_tag('clonable'):
                fname = field.name
                fields_kv[fname] = getattr(self, fname)

        new_entity = self.__class__(**fields_kv)
        new_entity._pre_save_clone(self)
        new_entity.save()
        new_entity._post_save_clone(self)

        new_entity._clone_m2m(self)

        new_entity._clone_custom_values(self)
        return new_entity

    def _copy_properties(self, source):
        creme_property_create = CremeProperty.objects.create

        for type_id in source.properties.filter(type__is_copiable=True).values_list('type', flat=True):
            creme_property_create(type_id=type_id, creme_entity=self)

    def _copy_relations(self, source, allowed_internal=()):
        """@param allowed_internal Sequence of RelationTypes pk with is_internal=True.
                                   Relationships with these types will be cloned anyway.
        """
        relation_create = Relation.objects.create

        query = Q(type__in=RelationType.get_compatible_ones(self.entity_type).filter(Q(is_copiable=True)))

        if allowed_internal:
            query |= Q(type__in=allowed_internal)

        for relation in source.relations.filter(query):
            relation_create(user_id=relation.user_id,
                            subject_entity=self,
                            type=relation.type,
                            object_entity_id=relation.object_entity_id,
                           )

    def clone(self):
        """Take an entity and makes it copy.
        @returns : A new entity (with a different pk) with sames values
        """
        self = self.get_real_entity()
        new_entity = self._clone_object()

        new_entity._copy_properties(self)#TODO: Add which properties types to include ?
        new_entity._copy_relations(self)

        new_entity._post_clone(self)
        return new_entity

    def restore(self):
        self.is_deleted = False
        self.save()

    def trash(self):
        self.is_deleted = True
        self.save()


from .relation import Relation, RelationType
from .creme_property import CremeProperty
from .custom_field import CustomField, CustomFieldValue
