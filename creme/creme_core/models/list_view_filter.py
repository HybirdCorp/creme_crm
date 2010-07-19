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

import logging

from django.db.models import Model, CharField, BooleanField, ForeignKey, ManyToManyField
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

#TODO: a FilterList class like the HeaderFilterList ???

class ConditionChildType(Model):
    type = CharField(max_length=100)

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        return self.type
    

class FilterValue(Model):
    value = CharField(max_length=100)

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        return self.value


class FilterType(Model):
    name             = CharField(max_length=50)
    pattern_key      = CharField(max_length=100)
    pattern_value    = CharField(max_length=100)
    is_exclude       = BooleanField(default=False)
    type_champ       = CharField(max_length=100)
    value_field_type = CharField(max_length=100)

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        #Dev
#        return '| FilterType / %s %s %s %s %s %s |' % (self.name,self.pattern_key,self.pattern_value,self.is_exclude,self.type_champ,self.value_field_type)
        #Prod
        return self.name


class FilterCondition(Model):
    type  = ForeignKey(FilterType)
#    is_or = BooleanField(default = False)
    champ = CharField(max_length=100)
#    value = CharField(max_length=100)
    values = ManyToManyField(FilterValue, related_name='FilterConditionValues_set')
    childs = ManyToManyField("self", related_name='FilterConditionChilds_set', blank=True, null=True, symmetrical=False)
    child_type = ForeignKey(ConditionChildType, blank=True, null=True)

    #def old_get_q(self):
        #config = {}
        #config[str(self.type.pattern_key % self.champ)] = str(self.type.pattern_value % self.value)
        #petit_q = Q(**config)
        #if self.type.is_exclude:
            #petit_q.negate()
        #return petit_q

    def get_q(self):
        result = Q()
        _type = self.type
        key = str(_type.pattern_key % self.champ)
        pattern_value = _type.pattern_value

        for value in self.values.all():
            q = Q(**{key: pattern_value % value})

            if _type.is_exclude:
                q.negate()
                result &= q
            else :
                result |= q
        return result

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        return u'%s %s %s' % (self.type, self.champ, self.values.all())


class Filter(Model):
    # Parent filter
    #To merge parent filter and self
#    parent_filter = ForeignKey('self', blank = True, null = True)
    parent_filters = ManyToManyField('self', blank=True, null=True, symmetrical=False)
    name           = CharField(max_length=50)
    conditions     = ManyToManyField(FilterCondition)#, related_name='filter_conditions')
    model_ct       = ForeignKey(ContentType)
    is_or_for_all  = BooleanField(default=False)


#    def add_condition(self, champ, type, value):
#        obj_type = FilterType.objects.get(pk = type)
#        cond = FilterCondition(parent_filter = self, champ = champ, type = obj_type, value = value)
#        cond.save()

#    def old_get_all_conditions (self):
#        if self.parent_filter is not None :
#            pcondition = self.parent_filter.get_all_conditions()
#        else :
#            pcondition = []
#        return list(self.conditions.all()) + pcondition

#    def old_get_q(self):
#        maxi_q = None
#        for cond in self.conditions.all():
#            if maxi_q is not None :
#                if cond.is_or :
#                    maxi_q |= cond.get_q()
#                else:
#                    maxi_q &= cond.get_q()
#            else :
#                maxi_q = cond.get_q()
#        logging.debug('retour : %s' % maxi_q)
#        return maxi_q

#    def old_get_q2(self):
#        maxi_q = None
#        logging.debug('\ntoutes les cond : %s ' % self.get_all_conditions())
#        for cond in self.get_all_conditions():
#            if maxi_q is not None :
#                if cond.is_or :
##                    maxi_q |= cond.get_q()
#                    maxi_q = maxi_q._combine(cond.get_q(),Q.OR)
#                else:
##                    maxi_q &= cond.get_q()
#                    maxi_q = maxi_q._combine(cond.get_q(),Q.AND)
#            else :
#                maxi_q = cond.get_q()
#        logging.debug('retour : %s' % maxi_q)
#        return maxi_q

    def get_q(self):
        maxi_q = Q()
        for cond in self.conditions.all():
            if self.is_or_for_all:
                maxi_q |= cond.get_q()
            else :
                maxi_q &= cond.get_q()
#            if self.is_or_for_all and not cond.type.is_exclude:
#                maxi_q |= cond.get_q()
#            elif self.is_or_for_all and cond.type.is_exclude:
#                maxi_q &= cond.get_q()
#            elif not self.is_or_for_all and cond.type.is_exclude:
#                maxi_q |= cond.get_q()
#            else :
#                maxi_q &= cond.get_q()
        for parent in self.parent_filters.all():
            if parent == self:
                continue
            if self.is_or_for_all :
                maxi_q |= parent.get_q()
            else :
                maxi_q &= parent.get_q()
        return maxi_q

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'creme_core'
