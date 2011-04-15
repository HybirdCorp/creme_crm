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

    @staticmethod
    def create(pk, name, model, is_custom=False, user=None, use_or=False):
        """Creation helper ; useful for populate.py scripts.
        """
        from creme_core.utils import create_or_update

        ef = create_or_update(EntityFilter, pk=pk,
                              name=name, is_custom=is_custom, user=user, use_or=use_or,
                              entity_type=ContentType.objects.get_for_model(model)
                             )
        #TODO: use set_conditions() ???

        return ef

    def filter(self, qs):
        query = Q()

        for condition in self.conditions.all():
            if self.use_or:
                query |= condition.get_q()
            else:
                query &= condition.get_q()

        return qs.filter(query)

    def set_conditions(self, conditions):
        old_conditions = EntityFilterCondition.objects.filter(filter=self)
        conds2del = []

        for old_condition, condition in map(None, old_conditions, conditions):
            if not condition: #less new conditions that old conditions => delete conditions in excess
                conds2del.append(old_condition.id)
            elif not old_condition:
                condition.filter = self
                condition.save()
            elif old_condition.update(condition): #TODO: test ??
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

    EQUALS          = 1
    IEQUALS         = 2
    EQUALS_NOT      = 3
    IEQUALS_NOT     = 4
    CONTAINS        = 5
    ICONTAINS       = 6
    CONTAINS_NOT    = 7
    ICONTAINS_NOT   = 8
    GT              = 9
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
    ISNULL          = 21
    ISNULL_NOT      = 22
    RANGE           = 23

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

    @staticmethod
    def build(model, type, name, value):
        try:
            field = model._meta.get_field_by_name(name)[0]
            operator = EntityFilterCondition._OPERATOR_MAP[type] #TODO: only raise??

            #TODO: method 'operator.clean()' ??
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

        return EntityFilterCondition(type=type, name=name, value=jsondumps(value))

    @property
    def decoded_value(self):
        return jsonloads(self.value)

    def get_q(self):
        operator = EntityFilterCondition._OPERATOR_MAP[self.type]
        query    = Q(**{operator.key_pattern % self.name: self.decoded_value})

        if operator.exclude:
            query.negate()

        return query

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
