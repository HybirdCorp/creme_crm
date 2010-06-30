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
    ENUM  = 100

    FIELD_TYPES = OrderedDict([(INT,   _(u'Nombre entier')),
                               (FLOAT, _(u'Nombre à virgule')),
                               (STR,   _(u'Chaîne de caractère')),
                               (ENUM,  _(u'Liste de choix')),
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

    def delete(self):
        self.customfieldvalue_set.all().delete()
        self.customfieldenumvalue_set.all().delete()
        super(CustomField, self).delete()

    def type_verbose_name(self):
        return CustomField.FIELD_TYPES[self.field_type]

    @staticmethod
    def get_custom_fields_n_values(entity):
        cfields = CustomField.objects.filter(content_type=entity.entity_type)

        if not cfields:
            return ()

        #useful to avoid many lazy loading of CustomField object
        # (with attribute 'custom_field' of CustomFieldValue objects)
        # We do not use in_bulk() method in order to keep CustomField objects' order.
        cfields_dict = dict((cfield.id, cfield) for cfield in cfields)

        values = {} #key: custom_field.id  value: string value for this custom_field
        enums  = [] #ids of CustomFieldEnumValue objects to retrieve

        ENUM = CustomField.ENUM

        for cfv in CustomFieldValue.objects.filter(custom_field__in=cfields, entity=entity.id):
            cf_id = cfv.custom_field_id

            if cfields_dict[cf_id].field_type == ENUM:
                enums.append(cfv.value)
            else:
                values[cf_id] = cfv.value

        if enums:
            for cfev in CustomFieldEnumValue.objects.filter(pk__in=enums):
                values[cfev.custom_field_id] = cfev.value

        return [(cfield, values.get(cfield.id, '')) for cfield in cfields]


class CustomFieldValue(CremeModel):
   custom_field = ForeignKey(CustomField, related_name='customfieldvalue_set')
   entity       = ForeignKey(CremeEntity, related_name='customvalues')
   value        = CharField(max_length=100)

   class Meta:
       app_label = 'creme_core'
       ordering = ('id',)

   def __unicode__(self):
        return self.value


class CustomFieldEnumValue(CremeModel):
   custom_field = ForeignKey(CustomField, related_name='customfieldenumvalue_set')
   value        = CharField(max_length=100)

   class Meta:
       app_label = 'creme_core'

   def __unicode__(self):
        return self.value
