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

from django.utils.encoding import force_unicode
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

from base import CremeAbstractEntity


class CremeEntity(CremeAbstractEntity):
    Gestion_Droit = ['Lire', 'Créer', 'Modifier', 'Supprimer', 'Mettre en relation avec'] #beuark....
    header_filter_exclude_fields = CremeAbstractEntity.header_filter_exclude_fields + ['id', 'cremeentity_ptr'] #TODO: use a set() ??
    extra_filter_exclude_fields  = CremeAbstractEntity.extra_filter_exclude_fields + ['id', 'cremeentity_ptr', 'header_filter_search_field']

    class Meta:
        app_label = 'creme_core'
        ordering = ('id',)

    def delete(self):
        for relation in self.relations.all():
            relation.delete()

        for prop in self.properties.all():
            prop.delete()

        for cv in self.customvalues.all():
            cv.delete()

        if settings.TRUE_DELETE:
            super(CremeEntity, self).delete()
        else:
            self.is_deleted = True
            self.save()

    def __unicode__(self):
        real_entity = self.get_real_entity()

        if self is real_entity:
            return u"Creme entity: %s" % self.id

        return unicode(real_entity)

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

    #TODO: improve query (list is paginated later, so don't get all object, and return a queryset if possible)
    def get_list_object_of_specific_relations(self, relation_type_id):
        #TODO: regroup entities retrieveing by ct to reduce queries ???
        #return [rel.object_creme_entity for rel in self.relations.filter(type__id=relation_type_id)]
        return [rel.object_entity for rel in self.relations.filter(type__id=relation_type_id)]

    def get_entity_summary(self):
        return escape(unicode(self))

    def get_entity_actions(self):
        return u"""<a href="%s">Voir</a> | <a href="%s">Éditer</a> | <a href="%s" onclick="creme.utils.confirmDelete(event, this);">Effacer</a>""" \
                % (self.get_absolute_url(), self.get_edit_absolute_url(), self.get_delete_absolute_url())

    #TODO: property + cache ???
    def get_custom_fields(self):
        return CustomField.get_custom_fields_n_values(self)


from custom_field import CustomField
