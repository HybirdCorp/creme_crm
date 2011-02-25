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

from django.core.exceptions import PermissionDenied
from django.utils.encoding import force_unicode
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, ugettext
from django.conf import settings
from django.forms.util import flatatt
from django.contrib.contenttypes.models import ContentType
from django.template.loader import render_to_string

from base import CremeAbstractEntity
from function_field import FunctionField


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

    @classmethod
    def populate_entities(cls, entities):
        CremeEntity.populate_properties(entities)


class CremeEntity(CremeAbstractEntity):
    header_filter_exclude_fields = CremeAbstractEntity.header_filter_exclude_fields + ['cremeentity_ptr', 'entity_type', 'is_deleted', 'is_actived', 'header_filter_search_field'] #TODO: use a set() ??
    extra_filter_exclude_fields  = CremeAbstractEntity.extra_filter_exclude_fields + ['id', 'cremeentity_ptr', 'header_filter_search_field']

    function_fields = CremeAbstractEntity.function_fields.new(_PrettyPropertiesField)

    class Meta:
        app_label = 'creme_core'
        ordering = ('id',)

    class CanNotBeDeleted(Exception):
        pass

    def __init__(self, *args, **kwargs):
        super(CremeEntity, self).__init__(*args, **kwargs)
        self._relations_map = {}
        self._properties = None
        self._cvalues_map = {}
        self._credentials_map = {}

    def delete(self):
        from auth import EntityCredentials

        if settings.TRUE_DELETE:
            if not self.can_be_deleted():
                raise CremeEntity.CanNotBeDeleted(ugettext(u'%s can not be deleted because of its dependencies.') % self)

            for relation in self.relations.all():
                relation.delete()

            for prop in self.properties.all():
                prop.delete()

            CustomFieldValue.delete_all(self)
            EntityCredentials.objects.filter(entity=self).delete()

            super(CremeEntity, self).delete()
        else:
            self.is_deleted = True #TODO: custom_fields and credentials are deleted anyway ??
            self.save()

    def __unicode__(self):
        real_entity = self.get_real_entity()

        if self is real_entity:
            return u"Creme entity: %s" % self.id

        return unicode(real_entity)

    def allowed_unicode(self, user):
        return unicode(self) if self.can_view(user) else ugettext(u'Entity #%s (not viewable)') % self.id

    def can_change(self, user):
        return self.get_credentials(user).can_change()

    def can_change_or_die(self, user):
        if not self.can_change(user):
            raise PermissionDenied(ugettext(u'You are not allowed to edit this entity: %s') % self.allowed_unicode(user))

    def can_delete(self, user):
        return self.get_credentials(user).can_delete()

    def can_delete_or_die(self, user):
        if not self.can_delete(user):
            raise PermissionDenied(ugettext(u'You are not allowed to delete this entity: %s') % self.allowed_unicode(user))

    def can_link(self, user):
        return self.get_credentials(user).can_link()

    def can_link_or_die(self, user):
        if not self.can_link(user):
            raise PermissionDenied(ugettext(u'You are not allowed to link this entity: %s') % self.allowed_unicode(user))

    def can_unlink(self, user):
        return self.get_credentials(user).can_unlink()

    def can_unlink_or_die(self, user):
        if not self.can_unlink(user):
            raise PermissionDenied(ugettext(u'You are not allowed to unlink this entity: %s') % self.allowed_unicode(user))

    def can_view(self, user):
        return self.get_credentials(user).can_view()

    def can_view_or_die(self, user):
        if not self.can_view(user):
            raise PermissionDenied(ugettext(u'You are not allowed to view this entity: %s') % self.allowed_unicode(user))

    def get_credentials(self, user): #private ??
        from auth import EntityCredentials

        creds_map = self._credentials_map

        creds = creds_map.get(user.id)

        if creds is None:
            debug('CremeEntity.get_credentials(): Cache MISS for id=%s user=%s', self.id, user)
            creds = EntityCredentials.get_creds(user, self)
            creds_map[user.id] = creds
        else:
            debug('CremeEntity.get_credentials(): Cache HIT for id=%s user=%s', self.id, user)

        return creds

    @staticmethod
    def populate_credentials(entities, user): #TODO: unit test...
        """ @param entities Sequence of CremeEntity (iterated several times -> not an iterator)
        """
        from auth import EntityCredentials
        creds_map = EntityCredentials.get_creds_map(user, entities)
        user_id   = user.id

        for entity in entities:
            entity._credentials_map[user_id] = creds_map[entity.id]

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

    def get_actions(self, user): #TODO: improve icon/css class management....
        return {
                'default': EntityAction(self.get_absolute_url(), ugettext(u"See"), True, icon="images/view_16.png"),
                'others':  [EntityAction(self.get_edit_absolute_url(),   ugettext(u"Edit"),   self.can_change(user), icon="images/edit_16.png"),
                            EntityAction(self.get_delete_absolute_url(), ugettext(u"Delete"), self.can_delete(user), icon="images/delete_16.png", attrs={'class': 'confirm post ajax lv_reload'}),
                           ]
               }

    def get_custom_fields_n_values(self):
        cfields = CustomField.objects.filter(content_type=self.entity_type_id) #TODO: in a staticmethod of CustomField ??
        CremeEntity.populate_custom_values([self], cfields)

        return [(cfield, self.get_custom_value(cfield)) for cfield in cfields]

    def get_properties(self):
        if self._properties is None:
            debug('CremeEntity.get_properties(): Cache MISS for id=%s', self.id)
            self._properties = list(self.properties.all().select_related('type'))
        else:
            debug('CremeEntity.get_properties(): Cache HIT for id=%s', self.id)

        return self._properties

    def get_pretty_properties(self):
        return u"""<ul>%s</ul>""" % "".join([u"<li>%s</li>" % p for p in self.get_properties()])

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
            debug(u'Fill properties cache entity_id=%s', entity_id)
            entity._properties = properties_map[entity_id]

    def save(self, *args, **kwargs):
        created = bool(self.pk is None)

        super(CremeEntity, self).save(*args, **kwargs)
        debug('CremeEntity.save(%s, %s)', args, kwargs)

        #signal instead ??
        from auth import EntityCredentials
        EntityCredentials.create(self, created)


from relation import Relation
from creme_property import CremeProperty
from custom_field import CustomField, CustomFieldValue

