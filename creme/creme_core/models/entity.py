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

    def as_p(self):
        return mark_safe("%s%s%s" % (self.object_as_p(), self.relations_as_p(), self.properties_as_p()))

    def object_as_p(self):
        from creme_core.templatetags.creme_core_tags import get_html_field_value

        html_output = ""
        exclude = set(self.excluded_fields_in_html_output)

        for field in self._meta.fields:
            if field.name not in exclude:
                try:
                    value = get_html_field_value(self, field.name)
                except Exception:
                    value = self.__getattribute__(field.name)

                html_output += " <br />%s: %s" % (force_unicode(field.name), force_unicode(value))

        return mark_safe(html_output)

    def relations_as_p(self):
        html_output = "<br /><br /><h2>Relations:</h2><br />"
        for relation in self.relations.all():
            if relation.type.display_with_other:
                try:
                    #Url doesn't match anymore but relations_as_p and as_p still used ?
                    html_output += '%s  <a href="/creme_core/relation/delete/%s?pk_entity=%s">Supprimer</a><br />' % \
                                    (force_unicode(relation), relation.pk, self.pk)
                except:
                    html_output += "problème sur l'affichage d'une relation. <br />"

        return mark_safe(html_output)

    def properties_as_p(self):
        html_output = u"<br /><br /><h2>Propriétés: </h2><br />"

        for prop in self.properties.all():
            html_output += u' %s  <a href="/creme_core/property/delete/%s/%s" >Supprimer</a> <br />' % \
                            (force_unicode(prop), self.pk, prop.pk)

        return mark_safe(html_output)

    def get_entity_summary(self):
        return escape(unicode(self))

    def get_entity_actions(self):
        return u"""<a href="%s">Voir</a> | <a href="%s">Éditer</a> | <a href="%s" onclick="creme.utils.confirmDelete(event, this);">Effacer</a>""" \
                % (self.get_absolute_url(), self.get_edit_absolute_url(), self.get_delete_absolute_url())

    #TODO: move to CustomField ???
    #TODO: property + cache ???
    def get_custom_fields(self):
        cfields = CustomField.objects.filter(content_type=self.entity_type)

        if not cfields:
            return ()

        values = dict((cfv.custom_field_id, cfv) for cfv in CustomFieldValue.objects.filter(custom_field__in=cfields, entity=self.id))

        return [(cfield, values.get(cfield.id, '')) for cfield in cfields]


from custom_field import CustomField, CustomFieldValue
