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

from django.db.models import ForeignKey, CharField, PositiveSmallIntegerField
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict as OrderedDict #use python2.6 OrderedDict later.....
from django.contrib.contenttypes.models import ContentType

from base import CremeModel
from entity import CremeEntity


class CustomField(CremeModel):
    INT   = 1
    FLOAT = 2
    #BOOL  = 3 ??
    STR   = 10
    #DATE  = 20 ??
    #ENUM  = 100

    FIELD_TYPES = OrderedDict([(INT,   _(u'Nombre entier')),
                               (FLOAT, _(u'Nombre à virgule')),
                               (STR,   _(u'Chaîne de caractère')),
                              ])

    name          = CharField(_(u'Nom du champ'), max_length=100)
    content_type  = ForeignKey(ContentType, verbose_name=_(u'Resource associée'))
    field_type    = PositiveSmallIntegerField(_(u'Type du champ')) #see INT, FLOAT etc...
    #list_or_not   = BooleanField()
    #default_value = CharField(_(u'Valeur par defaut'), max_length=100, blank=True, null=True)
    #extra_args    = CharField(max_length=500, blank=True, null=True)
    #required      = BooleanField(defaut=False) ????

    class Meta:
       app_label = 'creme_core'
       verbose_name = _(u'Champ personnalisé')
       verbose_name_plural = _(u'Champs personnalisés')
       ordering = ('id',)

    def __unicode__(self):
        return self.name

   #def get_absolute_url(self):
       #return "/creme_core/custom_fields/%s" % self.id

    def delete(self):
        self.customfieldvalue_set.all().delete()
        super(CustomField, self).delete()

    def type_verbose_name(self):
        return CustomField.FIELD_TYPES[self.field_type]


#class ValueOfCustomFieldsList(Model):
#    custom_field = models.ForeignKey( CustomFields )
#    value_field  = models.CharField(max_length=100)
#
#    class Meta:
#        app_label = 'creme_core'    


class CustomFieldValue(CremeModel):
   custom_field = ForeignKey(CustomField, related_name='customfieldvalue_set')
   entity       = ForeignKey(CremeEntity, related_name='customvalues')
   value        = CharField(max_length=100)

   class Meta:
       app_label = 'creme_core'
       ordering = ('id',)

   def __unicode__(self):
        return self.value

   #def get_absolute_url(self):
       #return "/creme_core/custom_fields_value/%s" % self.id
