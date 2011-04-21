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

from django.db.models import Model, CharField, TextField, PositiveSmallIntegerField, BooleanField, ForeignKey, Q
from django.db.models.fields import FieldDoesNotExist
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.simplejson import loads as jsonloads, dumps as jsondumps
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User


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

#TODO: use a JSONField ?

class EntityFilter(Model): #CremeModel ???
    """A model that contains conditions that filter queries on CremeEntity objects.
    They are principally used in the list views.
    Conditions can be :
     - On regular fields (eg: CharField, IntegerField)
     - On related fields (throught ForeignKey or Many2Many)
     - An other EntityFilter
     TODO: COMPLETE
    """
    id          = CharField(primary_key=True, max_length=100, editable=False)
    name        = CharField(max_length=100, verbose_name=_('Name'))
    user        = ForeignKey(User, verbose_name=_(u'Owner'), blank=True, null=True)
    entity_type = ForeignKey(ContentType, editable=False)
    is_custom   = BooleanField(editable=False, default=True)
    use_or      = BooleanField(verbose_name=_(u'Use "OR"'), default=False)

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Filter of Entity')
        verbose_name_plural = _(u'Filters of Entity')

    class CycleError(Exception):
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
        SUBFILTER = EntityFilterCondition.SUBFILTER

        #Ids of Filters that are referenced by these conditions
        ref_filter_ids = set(cond.decoded_value for cond in conditions if cond.type == SUBFILTER)

        if self.id in ref_filter_ids:
            raise EntityFilter.CycleError('A condition can not reference its own filter.')

        if self.get_connected_filter_ids() & ref_filter_ids: #TODO: method intersection not null
            raise EntityFilter.CycleError('There is a cycle with a subfilter')

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

    def filter(self, qs): #TODO: still useful ???
        return qs.filter(self.get_q())

    def get_connected_filter_ids(self):
        #NB: 'level' means a level of filters connected to this filter :
        #  - 1rst level is 'self'.
        #  - 2rst level is filters with a sub-filter conditions relative to 'self'.
        #  - 3rd level  is filters with a sub-filter conditions relative to a filter of the 2nd level.
        # etc....
        connected = level_ids = set((self.id,))

        #Sub-filters conditions
        sf_conds = [(cond, cond.decoded_value)
                        for cond in EntityFilterCondition.objects.filter(type=EntityFilterCondition.SUBFILTER)
                   ]

        while level_ids:
            level_ids = set(cond.filter_id
                                for cond, decoded_value in sf_conds
                                    if cond.decoded_value in level_ids
                           )
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

    def set_conditions(self, conditions, check_cycles=True): #TODO: check_cycles=False in form.save()
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
    __slots__ = ('name', '_key_pattern', '_exclude')

    def __init__(self, name, key_pattern, exclude=False):
        self._key_pattern = key_pattern
        self._exclude     = exclude
        self.name         = name

    @property
    def exclude(self):
        return self._exclude

    @property
    def key_pattern(self):
        return self._key_pattern

    def __unicode__(self):
        return unicode(self.name)


class EntityFilterCondition(Model):
    filter = ForeignKey(EntityFilter, related_name='conditions')
    type   = PositiveSmallIntegerField()
    name   = CharField(max_length=100)
    value  = TextField()

    SUBFILTER       = 1
    RELATION        = 2
    PROPERTY        = 3

    EQUALS          = 10
    IEQUALS         = 11
    EQUALS_NOT      = 12
    IEQUALS_NOT     = 13
    CONTAINS        = 14
    ICONTAINS       = 15
    CONTAINS_NOT    = 16
    ICONTAINS_NOT   = 17
    GT              = 18
    GTE             = 19
    LT              = 20
    LTE             = 21
    STARTSWITH      = 22
    ISTARTSWITH     = 23
    STARTSWITH_NOT  = 24
    ISTARTSWITH_NOT = 25
    ENDSWITH        = 26
    IENDSWITH       = 27
    ENDSWITH_NOT    = 28
    IENDSWITH_NOT   = 29
    ISNULL          = 30
    ISNULL_NOT      = 31
    RANGE           = 32

    _OPERATOR_MAP = {
            #value means (exclude_mode, query_key_pattern)
            EQUALS:          _ConditionOperator(_(u'Equals'),                                 '%s__exact'),
            IEQUALS:         _ConditionOperator(_(u'Equals (case insensitive)'),              '%s__iexact'),
            EQUALS_NOT:      _ConditionOperator(_(u"Does not equal"),                         '%s__exact', exclude=True),
            IEQUALS_NOT:     _ConditionOperator(_(u"Does not equal (case insensitive)"),      '%s__iexact', exclude=True),
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
            ISNULL:          _ConditionOperator(_(u"Is empty"),                               '%s__isnull'),
            ISNULL_NOT:      _ConditionOperator(_(u"Is not empty"),                           '%s__isnull', exclude=True),
            RANGE:           _ConditionOperator(_(u"Range"),                                  '%s__range'),
        }

    class Meta:
        app_label = 'creme_core'

    class ValueError(Exception):
        pass

    def __repr__(self):
        return u'EntityFilterCondition(filter=%(filter)s, type=%(type)s, name=%(name)s, value=%(value)s)' % {
                    'filter': self.filter_id,
                    'type':   self.type,
                    'name':   self.name or 'None',
                    'value':  self.value,
                }

    @staticmethod
    def build(model, type, name=None, value=None):
        try:
            #TODO: method 'operator.clean()' ??
            if type == EntityFilterCondition.SUBFILTER: #TODO: build_4_subfilter method ???
                name = ''

                if not isinstance(value, EntityFilter):
                    raise TypeError('Subfilter need an EntityFilter instance')

                value = value.id
            elif type == EntityFilterCondition.PROPERTY: #TODO: build_4_property method ???
                assert isinstance(value, bool)
            else:
                operator = EntityFilterCondition._OPERATOR_MAP[type] #TODO: only raise??
                field = model._meta.get_field_by_name(name)[0]

                if type in (EntityFilterCondition.ISNULL, EntityFilterCondition.ISNULL_NOT):
                    if not isinstance(value, bool): raise ValueError('A bool is expected for ISNULL(_NOT) condition')
                elif type == EntityFilterCondition.RANGE:
                    clean = field.formfield().clean
                    clean(value[0])
                    clean(value[1])
                else:
                    field.formfield().clean(value)
        except Exception, e:
            raise EntityFilterCondition.ValueError(str(e))

        return EntityFilterCondition(type=type, name=name, value=EntityFilterCondition.encode_value(value))

    @staticmethod
    def build_4_relation(model, rtype, has=True, ct=None, entity=None): #, object
        value = {'has': bool(has)}

        if entity:
            value['entity_id'] = entity.id
        elif ct:
            value['ct_id'] = ct.id

        return EntityFilterCondition(type=EntityFilterCondition.RELATION,
                                     name=rtype.id,
                                     value=EntityFilterCondition.encode_value(value)
                                    )

    @property
    def decoded_value(self):
        return jsonloads(self.value)

    @staticmethod
    def encode_value(value):
        return jsondumps(value)

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

    def _get_q_property(self):
        query = Q(properties__type=self.name)

        if not self.decoded_value: #is a boolean indicating if got or has not got the property type
            query.negate()

        return query

    def _get_q_regularfields(self):
        operator = EntityFilterCondition._OPERATOR_MAP[self.type]
        query    = Q(**{operator.key_pattern % self.name: self.decoded_value})

        if operator.exclude:
            query.negate()

        return query

    _GET_Q_FUNCS = {
            SUBFILTER: lambda self: EntityFilter.objects.get(id=self.decoded_value).get_q(),
            RELATION:  _get_q_relation,
            PROPERTY:  _get_q_property,
        }

    def get_q(self):
        func = EntityFilterCondition._GET_Q_FUNCS.get(self.type, EntityFilterCondition._get_q_regularfields)
        return func(self)

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
