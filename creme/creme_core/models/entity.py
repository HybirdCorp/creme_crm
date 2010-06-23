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

from django.db.models import ForeignKey, CharField, BooleanField, ManyToManyField
from django.utils.encoding import force_unicode
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.conf import settings

from django_extensions.db.models import TimeStampedModel

from creme_model import CremeModel

#from customfields  import *


class CremeEntityWithoutRelation(CremeModel, TimeStampedModel):
    entity_type = ForeignKey(ContentType, editable=False)
    header_filter_search_field = CharField(max_length=200, editable=False)

    is_deleted = BooleanField(blank=True, default=False)
    user = ForeignKey(User, verbose_name=_(u'Utilisateur'))
    is_actived = BooleanField(blank=True, default=False)

    research_fields = []
    users_allowed_func = [] #=> Use [{'name':'', 'verbose_name':''},...]
    excluded_fields_in_html_output = ['id', 'cremeentity_ptr' , 'entity_type', 'header_filter_search_field', 'is_deleted', 'is_actived'] #use a set
    header_filter_exclude_fields = []
    extra_filter_fields = [] #=> Use [{'name':'', 'verbose_name':''},...]
    extra_filter_exclude_fields = ['id']

    def __init__ (self, *args , **kwargs):
        super(CremeEntityWithoutRelation, self).__init__(*args , **kwargs)

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

    class Meta:
        app_label = 'creme_core'
        abstract = True
        ordering = ('id',)


#from relation import Relation


class CremeEntity(CremeEntityWithoutRelation):
    Gestion_Droit = ['Lire', 'Créer', 'Modifier', 'Supprimer', 'Mettre en relation avec'] #beuark....
    header_filter_exclude_fields = CremeEntityWithoutRelation.header_filter_exclude_fields + ['id', 'cremeentity_ptr'] #TODO: use a set() ??
    extra_filter_exclude_fields  = CremeEntityWithoutRelation.extra_filter_exclude_fields + ['id', 'cremeentity_ptr', 'header_filter_search_field']

    class Meta:
        app_label = 'creme_core'
        ordering = ('id',)

    def __init__(self, *args, **kwargs):
        super(CremeEntity, self).__init__(*args, **kwargs)

        self.build_custom_fields()

    def build_custom_fields(self):
        pass
#        self._meta.custom_fields = {}
#        content_type = ContentType.objects.get_for_model ( self )
#        self.content_type =  content_type
#        List_Custom_Fields =  CustomFields.objects.all().filter ( custom_field_of_model = content_type.id )
#        for CF in List_Custom_Fields:
#            List_CFV =  CustomFieldsValue.objects.all().filter(custom_field= CF , creme_entity = self)
#            
#            if List_CFV.count() > 0:
#                self.__dict__[ str(CF.name) ] = List_CFV[0].value_field
#            else :
#                 self.__dict__[ str(CF.name) ] = CF.default_value
#            self._meta.custom_fields[ str(CF.name) ] = models.CharField(max_length=100, default = CF.default_value)

    def save(self, *args, **kwargs):
        super(CremeEntity, self).save(*args, **kwargs)

#        if not self.pk : 
#            for key, value in self._meta.custom_fields.iteritems():
#                CFV =  CustomFieldsValue ( custom_field= CustomFields.objects.get ( name=key , custom_field_of_model = self.content_type ) , creme_entity=self , value_field=self.__dict__[ key ] )
#                CFV.save ()
#        else :
#            for key, value in self._meta.custom_fields.iteritems():
#                current_custom_field= CustomFields.objects.get ( name=key , custom_field_of_model = self.content_type )
#                queryset_cfv =   CustomFieldsValue.objects.filter(creme_entity=self , custom_field=current_custom_field  )
#                if  queryset_cfv.count () > 0 :
#                    CFV = queryset_cfv[0]
#                    CFV.value_field=self.__dict__[ key ]
#                    CFV.save ()
#                else : 
#                    if value.default ==  self.__dict__[ key ]:
#                        pass
#                    else:
#                        CFV =  CustomFieldsValue ( custom_field= CustomFields.objects.get ( name=key , custom_field_of_model = self.content_type ) , creme_entity=self , value_field=self.__dict__[ key ] )
#                        CFV.save ()

    def delete(self):
        #TODO: don't forget to delete custom fields
        for relation in self.relations.all():
            relation.delete()

        for prop in self.properties.all():
            prop.delete()

        if settings.TRUE_DELETE:
            super(CremeEntity, self).delete()
        else:
            self.is_deleted = True
            self.save()

    def __unicode__(self):
        if self.entity_type == ContentType.objects.get_for_model(CremeEntity):
            return u"Creme entity: %s" % self.id
        else:
            return unicode(self.entity_type.get_object_for_this_type(id=self.id))

    def get_real_entity(self):
        entity = self
        if self.entity_type != ContentType.objects.get_for_model(CremeEntity):
            entity = self.entity_type.get_object_for_this_type(id=self.id)
        return entity

    def get_absolute_url(self):
        #TODO : /!\ If the derived class hasn't get_absolute_url error max recursion
        if self.entity_type == ContentType.objects.get_for_model(CremeEntity):
            return "/creme_core/entity/%s" % self.id

        return self.entity_type.get_object_for_this_type(id=self.id).get_absolute_url()

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
