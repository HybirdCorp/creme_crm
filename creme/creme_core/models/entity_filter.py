# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from datetime import date
from itertools import ifilter

from django.db.models import Model, CharField, TextField, PositiveSmallIntegerField, BooleanField, ForeignKey, Q
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.db.models.signals import pre_delete
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.simplejson import loads as jsonloads, dumps as jsondumps
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from creme_core.models import CustomField, RelationType
from creme_core.utils.meta import is_date_field, get_model_field_infos
from creme_core.utils.date_range import date_range_registry


def date_2_dict(d): #move to utils ???
    return {'year': d.year, 'month': d.month, 'day': d.day}


class EntityFilterList(list):
    """Contains all the EntityFilter objects corresponding to a CremeEntity's ContentType.
    Indeed, it's as a cache.
    """
    def __init__(self, content_type):
        super(EntityFilterList, self).__init__(EntityFilter.objects.filter(entity_type=content_type).order_by('name'))
        self._selected = None

    @property
    def selected(self):
        return self._selected

    def select_by_id(self, *ids):
        """Try several EntityFilter ids"""
        #linear search but with few items after all....
        for efilter_id in ids:
            for efilter in self:
                if efilter.id == efilter_id:
                    self._selected = efilter
                    return efilter

        return self._selected


class EntityFilter(Model): #CremeModel ???
    """A model that contains conditions that filter queries on CremeEntity objects.
    They are principally used in the list views.
    Conditions can be :
     - On regular fields (eg: CharField, IntegerField) with a special behaviour for date fields.
     - On related fields (throught ForeignKey or Many2Many).
     - On CustomFields (with a special behaviour for CustomFields with DATE type).
     - An other EntityFilter
     - The existence (or the not existence) of a kind of Relationship.
     - The holding (or the not holding) of a kind of CremeProperty
    """
    id          = CharField(primary_key=True, max_length=100, editable=False)
    name        = CharField(max_length=100, verbose_name=_('Name'))
    user        = ForeignKey(User, verbose_name=_(u'Owner'), blank=True, null=True)
    entity_type = ForeignKey(ContentType, editable=False)
    is_custom   = BooleanField(editable=False, default=True)
    use_or      = BooleanField(verbose_name=_(u'Use "OR"'), default=False)

    _connected_filter_cache = None

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Filter of Entity')
        verbose_name_plural = _(u'Filters of Entity')

    class CycleError(Exception):
        pass

    class DependenciesError(Exception):
        pass

    def __unicode__(self):
        return self.name

    def can_edit_or_delete(self, user):
        if not self.is_custom:
            return (False, ugettext(u"This filter can't be edited/deleted"))

        if not self.user_id: #all users allowed
            return (True, 'OK')

        if user.is_superuser:
            return (True, 'OK')

        if not user.has_perm(self.entity_type.app_label):
            return (False, ugettext(u"You are not allowed to acceed to this app"))

        if not self.user.is_team:
            if self.user_id == user.id:
                return (True, 'OK')
        elif user.team_m2m.filter(teammate=user).exists(): #TODO: move in a User method ??
            return (True, 'OK')

        return (False, ugettext(u"You are not allowed to edit/delete this filter"))

    def check_cycle(self, conditions):
        #Ids of EntityFilters that are referenced by these conditions
        ref_filter_ids = set(ifilter(None, (cond._get_subfilter_id() for cond in conditions)))

        if self.id in ref_filter_ids:
            raise EntityFilter.CycleError(ugettext(u'A condition can not reference its own filter.'))

        if self.get_connected_filter_ids() & ref_filter_ids: #TODO: method intersection not null
            raise EntityFilter.CycleError(ugettext(u'There is a cycle with a subfilter.'))

    @staticmethod
    def create(pk, name, model, is_custom=False, user=None, use_or=False):
        """Creation helper ; useful for populate.py scripts."""
        from creme_core.utils import create_or_update

        ef = create_or_update(EntityFilter, pk=pk,
                              name=name, is_custom=is_custom, user=user, use_or=use_or,
                              entity_type=ContentType.objects.get_for_model(model)
                             )
        #TODO: use set_conditions() ???

        return ef

    def delete(self):
        pk = self.id
        parents = set(unicode(cond.filter)
                        for cond in EntityFilterCondition.objects.filter(type__in=(EntityFilterCondition.EFC_SUBFILTER,
                                                                                   EntityFilterCondition.EFC_RELATION_SUBFILTER
                                                                                  )
                                                                        )
                            if cond._get_subfilter_id() == pk
                     )

        if parents:
            raise EntityFilter.DependenciesError(ugettext(u'You can not delete this filter, because it is used as subfilter by : %s') % \
                                                    u', '.join(parents)
                                                )

        super(EntityFilter, self).delete()

    def filter(self, qs):
        #distinct is useful with condition on m2m that can retrieve several times the same Entity
        return qs.filter(self.get_q()).distinct()

    def get_connected_filter_ids(self):
        #NB: 'level' means a level of filters connected to this filter :
        #  - 1rst level is 'self'.
        #  - 2rst level is filters with a sub-filter conditions relative to 'self'.
        #  - 3rd level  is filters with a sub-filter conditions relative to a filter of the 2nd level.
        # etc....
        if self._connected_filter_cache:
            return self._connected_filter_cache

        self._connected_filter_cache = connected = level_ids = set((self.id,))

        #Sub-filters conditions
        sf_conds = [(cond, cond._get_subfilter_id())
                        for cond in EntityFilterCondition.objects.filter(type__in=(EntityFilterCondition.EFC_SUBFILTER,
                                                                                   EntityFilterCondition.EFC_RELATION_SUBFILTER
                                                                                  )
                                                                        )
                   ]

        while level_ids:
            level_ids = set(cond.filter_id for cond, filter_id in sf_conds if filter_id in level_ids)
            connected.update(level_ids)

        return connected

    def get_q(self):
        query = Q()

        if self.use_or:
            for condition in self.conditions.all():
                query |= condition.get_q()
        else:
            for condition in self.conditions.all():
                query &= condition.get_q()

        return query

    def set_conditions(self, conditions, check_cycles=True):
        if check_cycles:
            self.check_cycle(conditions)

        old_conditions = EntityFilterCondition.objects.filter(filter=self)
        conds2del = []

        for old_condition, condition in map(None, old_conditions, conditions):
            if not condition: #less new conditions that old conditions => delete conditions in excess
                conds2del.append(old_condition.id)
            elif not old_condition:
                condition.filter = self
                condition.save()
            elif old_condition.update(condition):
                old_condition.save()

        if conds2del:
            EntityFilterCondition.objects.filter(pk__in=conds2del).delete()


class _ConditionOperator(object):
    __slots__ = ('name', '_accept_subpart', '_exclude', '_key_pattern')

    #Fields for which the subpart of a valid value is not valid
    _NO_SUBPART_VALIDATION_FIELDS = set([models.EmailField, models.IPAddressField])

    def __init__(self, name, key_pattern, exclude=False, accept_subpart=True):
        self._key_pattern    = key_pattern
        self._exclude        = exclude
        self._accept_subpart = accept_subpart
        self.name            = name

    @property
    def exclude(self):
        return self._exclude

    @property
    def key_pattern(self):
        return self._key_pattern

    @property
    def accept_subpart(self):
        return self._accept_subpart

    def __unicode__(self):
        return unicode(self.name)

    def get_q(self, efcondition, values):
        key = self.key_pattern % efcondition.name
        query = Q()

        for value in values:
            query |= Q(**{key: value})

        return query

    def validate_field_values(self, field, values):
        """Raises a ValidationError to notify of a problemn with 'values'."""
        if not field.__class__ in self._NO_SUBPART_VALIDATION_FIELDS or not self.accept_subpart:
            clean = field.formfield().clean

            for value in values:
                clean(value)

        return values


class _ConditionBooleanOperator(_ConditionOperator):
    def validate_field_values(self, field, values):
        if len(values) != 1 or not isinstance(values[0], bool):
            raise ValueError(u'A list with one bool is expected for condition %s' % self.name)

        return values


class _IsEmptyOperator(_ConditionBooleanOperator):
    def __init__(self, name):
        super(_IsEmptyOperator, self).__init__(name, '', exclude=False, accept_subpart=False)

    def get_q(self, efcondition, values):
        field_name = efcondition.name
        query = Q(**{'%s__isnull' % field_name: True})

        if isinstance(efcondition.filter.entity_type.model_class()._meta.get_field(field_name), (CharField, TextField)):
            query |= Q(**{field_name: ''})

        if not values[0]:
            query.negate()

        return query


class _RangeOperator(_ConditionOperator):
    def __init__(self, name):
        super(_RangeOperator, self).__init__(name, '%s__range')

    def validate_field_values(self, field, values):
        if len(values) != 2:
            raise ValueError(u'A list with 2 elements is expected for condition %s' % self.name)

        return [super(_RangeOperator, self).validate_field_values(field, values)]


class EntityFilterCondition(Model):
    """Tip: Use the helper methods build_4_* instead of calling constructor."""
    filter = ForeignKey(EntityFilter, related_name='conditions')
    type   = PositiveSmallIntegerField() #NB: see EFC_*
    name   = CharField(max_length=100)
    value  = TextField() #TODO: use a JSONField ?

    EFC_SUBFILTER          = 1
    EFC_FIELD              = 5
    EFC_DATEFIELD          = 6
    EFC_RELATION           = 10
    EFC_RELATION_SUBFILTER = 11
    EFC_PROPERTY           = 15
    EFC_CUSTOMFIELD        = 20
    EFC_DATECUSTOMFIELD    = 21

    #OPERATORS (fields, custom_fields)
    EQUALS          =  1
    IEQUALS         =  2
    EQUALS_NOT      =  3
    IEQUALS_NOT     =  4
    CONTAINS        =  5
    ICONTAINS       =  6
    CONTAINS_NOT    =  7
    ICONTAINS_NOT   =  8
    GT              =  9
    GTE             = 10
    LT              = 11
    LTE             = 12
    STARTSWITH      = 13
    ISTARTSWITH     = 14
    STARTSWITH_NOT  = 15
    ISTARTSWITH_NOT = 16
    ENDSWITH        = 17
    IENDSWITH       = 18
    ENDSWITH_NOT    = 19
    IENDSWITH_NOT   = 20
    ISEMPTY         = 21
    RANGE           = 22

    _OPERATOR_MAP = {
            EQUALS:          _ConditionOperator(_(u'Equals'),                                 '%s__exact', accept_subpart=False),
            IEQUALS:         _ConditionOperator(_(u'Equals (case insensitive)'),              '%s__iexact', accept_subpart=False),
            EQUALS_NOT:      _ConditionOperator(_(u"Does not equal"),                         '%s__exact', exclude=True, accept_subpart=False),
            IEQUALS_NOT:     _ConditionOperator(_(u"Does not equal (case insensitive)"),      '%s__iexact', exclude=True, accept_subpart=False),
            CONTAINS:        _ConditionOperator(_(u"Contains"),                               '%s__contains'),
            ICONTAINS:       _ConditionOperator(_(u"Contains (case insensitive)"),            '%s__icontains'),
            CONTAINS_NOT:    _ConditionOperator(_(u"Does not contain"),                       '%s__contains', exclude=True),
            ICONTAINS_NOT:   _ConditionOperator(_(u"Does not contain (case insensitive)"),    '%s__icontains', exclude=True),
            GT:              _ConditionOperator(_(u">"),                                      '%s__gt'),
            GTE:             _ConditionOperator(_(u">="),                                     '%s__gte'),
            LT:              _ConditionOperator(_(u"<"),                                      '%s__lt'),
            LTE:             _ConditionOperator(_(u"<="),                                     '%s__lte'),
            STARTSWITH:      _ConditionOperator(_(u"Starts with"),                            '%s__startswith'),
            ISTARTSWITH:     _ConditionOperator(_(u"Starts with (case insensitive)"),         '%s__istartswith'),
            STARTSWITH_NOT:  _ConditionOperator(_(u"Does not start with"),                    '%s__startswith', exclude=True),
            ISTARTSWITH_NOT: _ConditionOperator(_(u"Does not start with (case insensitive)"), '%s__istartswith', exclude=True),
            ENDSWITH:        _ConditionOperator(_(u"Ends with"),                              '%s__endswith'),
            IENDSWITH:       _ConditionOperator(_(u"Ends with (case insensitive)"),           '%s__iendswith'),
            ENDSWITH_NOT:    _ConditionOperator(_(u"Does not end with"),                      '%s__endswith', exclude=True),
            IENDSWITH_NOT:   _ConditionOperator(_(u"Does not end with (case insensitive)"),   '%s__iendswith', exclude=True),
            ISEMPTY:         _IsEmptyOperator(_(u"Is empty")),
            RANGE:           _RangeOperator(_(u"Range")),
        }

    class Meta:
        app_label = 'creme_core'

    class ValueError(Exception):
        pass

    def __repr__(self):
        return u'EntityFilterCondition(filter_id=%(filter)s, type=%(type)s, name=%(name)s, value=%(value)s)' % {
                    'filter': self.filter_id,
                    'type':   self.type,
                    'name':   self.name or 'None',
                    'value':  self.value,
                }

    @staticmethod
    def build_4_customfield(custom_field, operator, value):
        if not EntityFilterCondition._OPERATOR_MAP.get(operator):
            raise EntityFilterCondition.ValueError('build_4_customfield(): unknown operator: %s', operator)

        if custom_field.field_type == CustomField.DATE:
            raise EntityFilterCondition.ValueError('build_4_customfield(): does not manage DATE CustomFields')

        if custom_field.field_type == CustomField.BOOL and operator != EntityFilterCondition.EQUALS:
            raise EntityFilterCondition.ValueError('build_4_customfield(): BOOL type is only compatible with EQUALS operator')

        cf_value_class = custom_field.get_value_class()

        try:
            cf_value_class.get_formfield(custom_field, None).clean(value)
        except ValidationError, e:
            raise EntityFilterCondition.ValueError(str(e))

        value = {'operator': operator,
                 'value':    value,
                 'rname':    cf_value_class.get_related_name(),
                }

        return EntityFilterCondition(type=EntityFilterCondition.EFC_CUSTOMFIELD,
                                     name=str(custom_field.id),
                                     value=EntityFilterCondition.encode_value(value)
                                    )

    @staticmethod
    def _build_daterange_dict(date_range=None, start=None, end=None):
        range_dict = {}

        if date_range:
            if not date_range_registry.get_range(date_range):
                raise EntityFilterCondition.ValueError('build_4_date(): invalid date range.')

            range_dict['name'] = date_range
        else:
            if start: range_dict['start'] = date_2_dict(start)
            if end:   range_dict['end']   = date_2_dict(end)

        if not range_dict:
            raise EntityFilterCondition.ValueError('date_range or start/end must be given.')

        return range_dict

    @staticmethod
    def build_4_date(model, name, date_range=None, start=None, end=None):
        try:
            field = model._meta.get_field(name)
        except FieldDoesNotExist, e:
            raise EntityFilterCondition.ValueError(str(e))

        if not is_date_field(field):
            raise EntityFilterCondition.ValueError('build_4_date(): field must be a date field.')

        return EntityFilterCondition(type=EntityFilterCondition.EFC_DATEFIELD, name=name,
                                     value=EntityFilterCondition.encode_value(EntityFilterCondition._build_daterange_dict(date_range, start, end))
                                    )

    @staticmethod
    def build_4_datecustomfield(custom_field, date_range=None, start=None, end=None):
        if not custom_field.field_type == CustomField.DATE:
            raise EntityFilterCondition.ValueError('build_4_datecustomfield(): not a date custom field.')

        value = EntityFilterCondition._build_daterange_dict(date_range, start, end)
        value['rname'] = custom_field.get_value_class().get_related_name()

        return EntityFilterCondition(type=EntityFilterCondition.EFC_DATECUSTOMFIELD,
                                     name=str(custom_field.id),
                                     value=EntityFilterCondition.encode_value(value),
                                    )

    #TODO multivalue is stupid for some operator (LT, GT etc...) => improve checking ???
    @staticmethod
    def build_4_field(model, name, operator, values):
        """Search in the values of a model field.
        @param name Name of the field
        @param operator Operator ID ; see EntityFilterCondition.EQUALS and friends.
        @param values List of searched values (logical OR between them).
                      Exceptions: - RANGE: 'values' is always a list of 2 elements
                                  - ISEMPTY: 'values' is a list containing one boolean.
        """
        operator_obj = EntityFilterCondition._OPERATOR_MAP.get(operator)
        if not operator_obj:
            raise EntityFilterCondition.ValueError('Unknown operator: %s' % operator)

        finfo = get_model_field_infos(model, name)
        if not finfo:
            raise EntityFilterCondition.ValueError('%s: no field named: %s', model, name)

        try:
            values = operator_obj.validate_field_values(finfo[-1]['field'], values)
        except Exception, e:
            raise EntityFilterCondition.ValueError(str(e))

        return EntityFilterCondition(type=EntityFilterCondition.EFC_FIELD,
                                     name=name, value=EntityFilterCondition.encode_value({'operator': operator, 'values': values})
                                    )

    @staticmethod
    def build_4_property(ptype, has=True):
        return EntityFilterCondition(type=EntityFilterCondition.EFC_PROPERTY, name=ptype.id,
                                     value=EntityFilterCondition.encode_value(bool(has))
                                    )

    @staticmethod
    def build_4_relation(rtype, has=True, ct=None, entity=None):
        value = {'has': bool(has)}

        if entity:
            value['entity_id'] = entity.id
        elif ct:
            value['ct_id'] = ct.id

        return EntityFilterCondition(type=EntityFilterCondition.EFC_RELATION,
                                     name=rtype.id,
                                     value=EntityFilterCondition.encode_value(value)
                                    )

    @staticmethod
    def build_4_relation_subfilter(rtype, subfilter, has=True):
        return EntityFilterCondition(type=EntityFilterCondition.EFC_RELATION_SUBFILTER,
                                     name=rtype.id,
                                     value=EntityFilterCondition.encode_value({'has': bool(has), 'filter_id': subfilter.id})
                                    )

    @staticmethod
    def build_4_subfilter(subfilter):
        assert isinstance(subfilter, EntityFilter)
        return EntityFilterCondition(type=EntityFilterCondition.EFC_SUBFILTER, name=subfilter.id)

    @property
    def decoded_value(self):
        return jsonloads(self.value)

    @staticmethod
    def encode_value(value):
        return jsondumps(value)

    def _get_q_customfield(self):
        #NB: Sadly we retrieve the ids of the entity that match with this condition
        #    instead of use a 'JOIN', in order to avoid the interaction between
        #    several conditions on the same type of CustomField (ie: same table).
        search_info = self.decoded_value
        operator = EntityFilterCondition._OPERATOR_MAP[search_info['operator']]
        related_name = search_info['rname']
        fname = '%s__value' % related_name
        query = Q(**{'%s__custom_field' % related_name: int(self.name),
                     operator.key_pattern % fname:      search_info['value'],
                    }
                 )

        if operator.exclude:
            query.negate()

        return Q(pk__in=self.filter.entity_type.model_class().objects.filter(query).values_list('id', flat=True))

    def _load_daterange(self, decoded_value):
        get = decoded_value.get
        kwargs = {'name': get('name')}

        for key in ('start', 'end'):
            date_kwargs = get(key)
            if date_kwargs:
                kwargs[key] = date(**date_kwargs)

        return date_range_registry.get_range(**kwargs)

    def _get_q_datecustomfield(self):
        #NB: see _get_q_customfield() remark
        search_info = self.decoded_value
        related_name = search_info['rname']
        fname = '%s__value' % related_name

        q_dict = self._load_daterange(search_info).get_q_dict(field=fname, today=date.today())
        q_dict['%s__custom_field' % related_name] = int(self.name)

        return Q(pk__in=self.filter.entity_type.model_class().objects.filter(**q_dict).values_list('id', flat=True))

    def _get_q_field(self):
        search_info = self.decoded_value
        operator = EntityFilterCondition._OPERATOR_MAP[search_info['operator']]
        query = operator.get_q(self, search_info['values'])

        if operator.exclude:
            query.negate()

        return query

    def _get_q_relation(self):
        kwargs = {'relations__type': self.name}
        value = self.decoded_value

        for key, query_key in (('entity_id', 'relations__object_entity'), ('ct_id', 'relations__object_entity__entity_type')):
            arg = value.get(key)

            if arg:
                kwargs[query_key] = arg
                break

        query = Q(**kwargs)

        if not value['has']:
            query.negate()

        return query

    def _get_q_relation_subfilter(self):
        #TODO: can the filter be deleted ???
        value = self.decoded_value
        subfilter = EntityFilter.objects.get(pk=value['filter_id'])
        excluded = subfilter.filter(subfilter.entity_type.model_class().objects.all()).values_list('id', flat=True)
        query = Q(relations__type=self.name, relations__object_entity__in=excluded)

        if not value['has']:
            query.negate()

        return query

    def _get_q_property(self):
        query = Q(properties__type=self.name)

        if not self.decoded_value: #is a boolean indicating if got or has not got the property type
            query.negate()

        return query

    _GET_Q_FUNCS = {
            EFC_SUBFILTER:          (lambda self: EntityFilter.objects.get(id=self.name).get_q()),
            EFC_FIELD:              _get_q_field,
            EFC_RELATION:           _get_q_relation,
            EFC_RELATION_SUBFILTER: _get_q_relation_subfilter,
            EFC_PROPERTY:           _get_q_property,
            EFC_DATEFIELD:          (lambda self: Q(**self._load_daterange(self.decoded_value).get_q_dict(field=self.name, today=date.today()))),
            EFC_CUSTOMFIELD:        _get_q_customfield,
            EFC_DATECUSTOMFIELD:    _get_q_datecustomfield,
        }

    def get_q(self):
        return EntityFilterCondition._GET_Q_FUNCS[self.type](self)

    def _get_subfilter_id(self):
        type = self.type

        if type == self.EFC_SUBFILTER:
            return self.name
        elif type == self.EFC_RELATION_SUBFILTER:
            return self.decoded_value['filter_id']

    def update(self, other_condition):
        """Fill a condition with the content a another one (in order to reuse the old instance if possible).
        @return True if there is at least one change, else False.
        """
        changed = False

        for attr in ('type', 'name', 'value'):
            other = getattr(other_condition, attr)

            if getattr(self, attr) != other:
                setattr(self, attr, other)
                changed = True

        return changed


def _delete_relationtype_efc(sender, instance, **kwargs):
    EntityFilterCondition.objects.filter(type__in=(EntityFilterCondition.EFC_RELATION,
                                                   EntityFilterCondition.EFC_RELATION_SUBFILTER
                                                  ),
                                         name=instance.id
                                        )\
                                 .delete()

def _delete_customfield_efc(sender, instance, **kwargs):
    EntityFilterCondition.objects.filter(type=EntityFilterCondition.EFC_CUSTOMFIELD, name=instance.id).delete()

pre_delete.connect(_delete_relationtype_efc, sender=RelationType)
pre_delete.connect(_delete_customfield_efc,  sender=CustomField)
