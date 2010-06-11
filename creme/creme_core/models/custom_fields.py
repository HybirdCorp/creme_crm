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

#from django.db import models
from django.db.models import Model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.auth.models import User
#from django.utils import encoding



class CustomFields(Model):
    pass 

#    name = models.CharField(max_length=100)
#    custom_field_of_model = models.ForeignKey(ContentType)
#    type_champ = models.CharField(max_length=100)
#    list_or_not = models.BooleanField ()
#    default_value = models.CharField(max_length=100, blank=True, null=True)
#    extra_args = models.CharField(max_length=500, blank=True, null=True)
#    
#    def __unicode__(self):
#        return encoding.force_unicode( self.name )
#
#    def get_absolute_url(self):
#        return "/creme_core/custom_fields/%s" % self.id
#        
#        
#    class Meta:
#        app_label = 'creme_core'    
#        ordering = ('id',)  


class ValueOfCustomFieldsList(Model):
    pass
#    custom_field = models.ForeignKey( CustomFields )
#    value_field  = models.CharField(max_length=100)
#
#    class Meta:
#        app_label = 'creme_core'    
#
#
#from entity import CremeEntity

class CustomFieldsValue(Model):
    pass
#    custom_field = models.ForeignKey( CustomFields ) 
#    creme_entity = models.ForeignKey( CremeEntity )
#    value_field  = models.CharField(max_length=100)
#     
#    def __unicode__(self):
#        return encoding.force_unicode( self.id )
#
#    def get_absolute_url(self):
#        return "/creme_core/custom_fields_value/%s" % self.id
#        
#    class Meta:
#        app_label = 'creme_core'    
#        ordering = ('id',)   
