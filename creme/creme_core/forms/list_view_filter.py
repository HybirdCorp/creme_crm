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
from itertools import chain

from django import forms
from django.forms.util import ErrorList
from django.contrib.contenttypes.models import ContentType
from django.forms.util import ValidationError
from django.utils.translation import ugettext_lazy as _

from creme_core.models import RelationType, CremePropertyType, FilterType, FilterCondition, FilterValue, Filter, ConditionChildType
from creme_core.utils import Q_creme_entity_content_types
from creme_core.utils.meta import get_flds_with_fk_flds, get_date_fields
from creme_core.forms.widgets import DateFilterWidget, CalendarWidget
from creme_core.populate import DATE_RANGE_FILTER, DATE_RANGE_FILTER_VOLATILE#Waiting for filters refactor
from creme_core.date_filters_registry import date_filters_registry

class ListViewFilterForm(forms.Form):

    parent_filters = forms.ModelChoiceField(Filter.objects.none(), required=False)
    nom = forms.CharField(required=True)
    champs = forms.ChoiceField(choices=[])
    champsfk = forms.ChoiceField(choices=[])
    tests = forms.ChoiceField(choices=[])
    value = forms.CharField(required=False)
    global_test = forms.ChoiceField(choices=[('0','ET'),('1','OU')])

    has_predicate = forms.ChoiceField(choices=[('0','A'),('1','N\'A PAS')])
    #predicates = forms.ModelChoiceField(RelationPredicate.objects.all(), required=False)
    predicates = forms.ModelChoiceField(RelationType.objects.all(), required=False)

    has_property = forms.ChoiceField(choices=[('0','A'),('1','N\'A PAS')])
    properties = forms.ModelChoiceField(CremePropertyType.objects.all(), required=False)

    content_types = forms.ModelChoiceField(Q_creme_entity_content_types(), required=False, widget=forms.Select(attrs={'onchange':'creme.filters.getListViewFromCt(this);'}))

    date_fields  = forms.ChoiceField(choices=())
    date_filters = forms.ChoiceField(label=_(u'Filter'), required=False, choices=(), widget=DateFilterWidget(attrs={'id': 'id_date_filters_model'}))
    begin_date   = forms.DateField(label=_(u'Begin date'), required=False)
    end_date     = forms.DateField(label=_(u'End date'), required=False)

    def __init__(self, data=None, files=None, auto_id='id_%s_model', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False):

        super (ListViewFilterForm , self ).__init__(data, files, auto_id, prefix,
                 initial, error_class, label_suffix,
                 empty_permitted)
                 
        ct_id = initial.get('content_type_id')
        if ct_id is not None :
            #klass = ContentType.objects.get_for_id(pk=ct_id).model_class()
            self.ct = ContentType.objects.get_for_id(ct_id)
            klass = self.ct.model_class()

#            champs = []
#            for field in klass._meta.fields:
#
#                if field.get_internal_type() == 'ForeignKey' :
#                    champs +=[('%s__%s' % (field.name,f.name), u'%s - %s' % (field.verbose_name,f.verbose_name)) for f in field.rel.to._meta.fields]
#                else:
#                    champs.append((field.name, field.verbose_name))

            fields = self.fields

#            fields['champs'].choices = [(f.name, f.verbose_name) for f in klass._meta.fields]
#            fields['champs'].choices = champs
            date_fields = get_date_fields(klass)
            fields['champs'].choices = [(f.name,'%s%s' % (f.verbose_name[0].upper(),f.verbose_name[1:])) for f in get_flds_with_fk_flds(klass, 0) if f not in date_fields]
#            fields['champs'].choices.append(('relations','Relations'))
            fields['champs'].choices.sort()

            fields['tests'].choices = [(f.id, f.name) for f in FilterType.objects.exclude(pk=DATE_RANGE_FILTER)]
            fields['parent_filters'].queryset = Filter.objects.filter(model_ct__id=ct_id)

            fields['date_fields'].choices  = [(f.name, f.verbose_name)for f in get_date_fields(klass)]
            fields['date_filters'].choices = date_filters_registry.itervalues()

        filter_id = initial.get('filter_id')
        if filter_id is not None:
            self.filter_id = filter_id
            

    def full_clean(self):
        super (ListViewFilterForm , self ).full_clean()
#        ids = self.data.get('ids')
#        logging.debug(ids)
#        if ids is None or ids == '':
#            self._errors['ids'] = 'Veuillez créer au moins un critère'
#            raise ValidationError
#        logging.debug('error : %s ' % self.errors)

    def save(self):
        logging.debug('self : %s ' % self.__dict__)

        data = self.data
        ids = data.get('ids')
        ids_filter = data.get('ids_filter')
        ids_relation = data.get('ids_relations')
        ids_properties = data.get('ids_properties')
        ids_date_fields = data.get('ids_date_fields')
        
        if not ids and not ids_filter and not ids_relation and not ids_properties and not ids_date_fields:
            return
        
        ids = ids.split(',')
        ids_filter=ids_filter.split(',')
        ids_relation=ids_relation.split(',')
        ids_properties=ids_properties.split(',')
        ids_date_fields=ids_date_fields.split(',')
        
        if hasattr(self,'filter_id') and self.filter_id is not None:
            try :
                f = Filter.objects.get(pk=self.filter_id)
            except Filter.DoesNotExist:
                f = Filter()
        else:
            f = Filter()
            
        f.name = data['nom']
        
        try :
            f.is_or_for_all = True if int(data['global_test'])==1 else False
            f.model_ct = self.ct
            f.save()
            f.parent_filters = []
            for id in ids_filter :
                if not id:
                    continue
                try:
#                    parents.append(Filter.objects.get(pk=data['parent_filters_%s' % id]))
                    f.parent_filters.add(Filter.objects.get(pk=data['parent_filters_%s' % id]))
                except Filter.DoesNotExist:
                    continue
        except Exception, e:
            logging.debug('Erreur lors du save de filtre : %s' % e)

        conditions = []

        for id in ids :
            if not id:
                continue

            try:
                condition = FilterCondition()
                condition.champ = data['champs_%s' % id]

                champfk = data.get('champsfk_%s' % id)
                if champfk:
                    condition.champ += "__"+data['champsfk_%s' % id]
                    
                condition.type = FilterType.objects.get(pk=data['tests_%s' % id])
                values = []
                get_filtervalue = FilterValue.objects.get
                for value in data['value_%s' % id].split(','):
                    if value:
                        try:
                            #values.append(FilterValue.objects.get(value=value))
                            values.append(get_filtervalue(value=value))
                        except:
                            value = FilterValue(value=value)
                            value.save()
                            values.append(value)
                condition.save()
                condition.values = values
                condition.save()
                conditions.append(condition)
            except Exception, e:
                logging.debug("###\nException : %s" % e)
                continue

        filter_type_getter = FilterType.objects.get
        filter_value_getter = FilterValue.objects.get_or_create
        condition_child_type_getter = ConditionChildType.objects.get_or_create
        
        for id_rel in ids_relation:
            if not id_rel:
                continue
            try:
                logging.debug('###\n\nA na PA : %s' % bool(int(data['has_predicate_%s' % id_rel])))
                logging.debug('###\n\nA na PA : %s' % data['has_predicate_%s' % id_rel])
#                has_or_not = False
#                if int(data['has_predicate_%s' % id_rel])==1:
#                    has_or_not=True

                condition = FilterCondition()
                condition.champ = 'relations__type__id'
                condition.type = filter_type_getter(pattern_key='%s__exact',is_exclude=bool(int(data['has_predicate_%s' % id_rel])))
#                condition.type = filter_type_getter(pattern_key='%s__exact',is_exclude=has_or_not)
                condition.save()
                condition.values = [filter_value_getter(value=data['predicates_%s' % id_rel])[0]]
                condition.save()

                target_entity = data.get('relation_entity_id_%s' % id_rel)
                target_entity_ct = data.get('content_types_%s' % id_rel)
                if(target_entity is not None and target_entity != "" and target_entity_ct is not None and target_entity_ct != ""):
                    condition_entity_ct = FilterCondition()
                    #condition_entity_ct.champ = 'new_relations__object_content_type__id'
                    condition_entity_ct.champ = 'relations__object_entity__entity_type__id'
                    condition_entity_ct.type = filter_type_getter(pattern_key='%s__exact',is_exclude=bool(int(data['has_predicate_%s' % id_rel])))
                    condition_entity_ct.child_type = condition_child_type_getter(type="content_type")[0]
                    condition_entity_ct.save()
                    condition_entity_ct.values = [filter_value_getter(value=target_entity_ct)[0]]
                    condition_entity_ct.save()

                    condition_entity = FilterCondition()
                    #condition_entity.champ = 'new_relations__object_id'
                    condition_entity.champ = 'relations__object_entity__id'
                    condition_entity.type = filter_type_getter(pattern_key='%s__exact',is_exclude=bool(int(data['has_predicate_%s' % id_rel])))
                    condition_entity.child_type = condition_child_type_getter(type="object_id")[0]
                    condition_entity.save()
                    condition_entity.values = [filter_value_getter(value=target_entity)[0]]
                    condition_entity.save()

                    conditions.append(condition_entity)
                    conditions.append(condition_entity_ct)

                    condition.childs = [condition_entity_ct, condition_entity]

                conditions.append(condition)
            except Exception, e:
                logging.debug("###\nException : %s" % e)
                continue
                
        logging.debug("conditions : %s" % conditions)

        logging.debug('#{#{#{ids_properties:%s' % ids_properties)
        for id_p in ids_properties:
            
            logging.debug('#{#{#{id_p:%s' % id_p)

            if not id_p:
                continue
            try:

                condition = FilterCondition()
                condition.champ = 'properties__type__id'
                condition.type = filter_type_getter(pattern_key='%s__exact',is_exclude=bool(int(data['has_property_%s' % id_p])))
                logging.debug('#{#{#{# condition.type : %s' % condition.type)

                condition.save()
                condition.values = [filter_value_getter(value=data['properties_%s' % id_p])[0]]
                
                logging.debug('#{#{#{#{ condition.values : %s' % condition.values)

                condition.save()
                conditions.append(condition)
            except Exception, e:
                logging.debug("###\n\n\nException : %s" % e)
                continue


        get_date_filter = date_filters_registry.get_filter
        for id in ids_date_fields :
            if not id:
                continue

            try:
                date_filter = get_date_filter(data['date_filters_%s' % id])
                filtertype_pk = DATE_RANGE_FILTER_VOLATILE if date_filter.is_volatile else DATE_RANGE_FILTER

                condition = FilterCondition()
                condition.champ = data['date_fields_%s' % id]

                condition.type = FilterType.objects.get(pk=filtertype_pk)
                values = []
                get_filtervalue = FilterValue.objects.get

                if not date_filter.is_volatile:
                    for value in [data['begin_date_%s' % id], data['end_date_%s' % id]]:
                        if value:
                            try:
                                #values.append(FilterValue.objects.get(value=value))
                                values.append(get_filtervalue(value=value))
                            except:
                                value = FilterValue(value=value)
                                value.save()
                                values.append(value)
                else:
                   value = date_filter.name
                   try:
                        values.append(get_filtervalue(value=value))
                   except:
                        value = FilterValue(value=value)
                        value.save()
                        values.append(value)
                condition.save()
                condition.values = values
                condition.save()
                conditions.append(condition)
            except Exception, e:
                logging.debug("###\nException : %s" % e)
                continue


        try:
            f.save()
            f.conditions = conditions
            f.save()
        except Exception, e:
            logging.debug('#{#{#{#{#{#Exception sur la sauvegarde : %s' % e)

        
        
    