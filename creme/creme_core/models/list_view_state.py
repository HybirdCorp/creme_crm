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

from collections import defaultdict
from datetime import date, time, datetime
from logging import debug

from django.db.models import Q
from django.db.models.sql.constants import QUERY_TERMS
from django.utils.encoding import smart_str
from django.shortcuts import get_object_or_404

from creme_core.models import Relation, CustomField, CustomFieldEnumValue
from header_filter import HeaderFilterItem, HFI_FIELD, HFI_RELATION, HFI_CUSTOM, HFI_FUNCTION


def simple_value(value):
    if value:
        if hasattr(value, '__iter__') and len(value) == 1:
            return value[0]
        return value
    return ''#TODO : Verify same semantic than "null" sql
#    return value if value and not hasattr(value, '__iter__') else '' #TODO : Verify same semantic than "null" sql

def range_value(value):
    """
        value have to be iterable
        the iterable can contains :
            - numbers
            - datetime
            - str values
        In general iterable may have 2 values for use the sql's "BETWEEN" statement
        works with more than 2 but the result won't be necessarily correct...
    """
    if hasattr(value, '__iter__'):
        if len(value) == 1 or len(value) == 2:
            try: #TODO: use value[-1] ???
                return (datetime.strptime(value[0], "%Y-%m-%d %H:%M:%S"), datetime.strptime(value[len(value)-1], "%Y-%m-%d %H:%M:%S"))
            except ValueError:
                try:
                    return (datetime.strptime(value[0], "%Y-%m-%d"), datetime.strptime(value[len(value)-1], "%Y-%m-%d").replace(hour=23,minute=59,second=59))
                except ValueError:
                    pass
        return value
    return []

def int_value(value):
    try:
        return int(value)
    except ValueError:
        return 0

def string_value(value): #TODO: rename to regex_value ???
    if value and isinstance(value, basestring):
        return value
    return '.*'

def bool_value(value):
    return bool(int_value(value))

QUERY_TERMS_FUNC = {
    'exact':       lambda x: x,
#    'iexact':      simple_value,
#    'contains':    simple_value,
#    'icontains':   simple_value,
#    'gt':          simple_value,
#    'gte':         simple_value,
#    'lt':          simple_value,
#    'lte':         simple_value,
    'in':          lambda x: x if hasattr(x, '__iter__') else [],
#    'startswith':  simple_value,
#    'istartswith': simple_value,
#    'endswith':    simple_value,
#    'iendswith':   simple_value,
    'range':       range_value,
    'year':        int_value,
    'month':       int_value,
    'day':         int_value,
    'week_day':    int_value,
    'isnull':      bool,
#    'search':      simple_value,
    'regex':       string_value,
    'iregex':      string_value,
    'creme-boolean': bool_value,
}

def _get_value_for_query(pattern, value):
    query_terms_pattern = QUERY_TERMS.keys() #TODO: query_terms_pattern = set(QUERY_TERMS.iterkeys()) ????? constant ???
    patterns = pattern.split('__')
    patterns.reverse()#In general the pattern is at the end  #TODO: use reversed() instead

    qterm = None
    for p in patterns:
        if p in query_terms_pattern:
            qterm = p
            break
    return QUERY_TERMS_FUNC.get(qterm, simple_value)(value)

def _map_patterns(custom_pattern):
    MAP_QUERY_PATTERNS = { #TODO: extract from function
        'creme-boolean': 'exact',
    }
    patterns = custom_pattern.split('__')
    i = 0
    for pattern in patterns: #TODO: use enumerate().....  hum modify the list on which we iterate....
        patterns[i] = MAP_QUERY_PATTERNS.get(pattern, pattern)
        i += 1
    return "__".join(patterns)


class ListViewState(object):
    def __init__(self, **kwargs):
        get_arg = kwargs.get
        self.filter_id = get_arg('filter')
        self.header_filter_id = get_arg('hfilter')
        self.page = get_arg('page')
        self.rows = get_arg('rows')
        self._search = get_arg('_search') #TODO: rename to search ??
        self.sort_order = get_arg('sort_order')
        self.sort_field = get_arg('sort_field')
        self.url = get_arg('url')
        self.research = ()
        self.extra_q = None

    def register_in_session(self, request):
        session = request.session
        current_lvs = session.get(self.url or request.path)
        if current_lvs is not None:
            try:
                del session[self.url or request.path] #useful ???????
            except KeyError, ke:
                pass
        session[self.url] = self

    def __repr__(self):
        return u'<ListViewState: (filter_id=%s, header_filter_id=%s, page=%s, rows=%s, _search=%s, sort=%s%s, url=%s, research=%s)>' % \
               (self.filter_id, self.header_filter_id, self.page, self.rows, self._search, self.sort_order, self.sort_field, self.url, self.research)

    @staticmethod
    def get_state(request, url=None):
        return request.session.get(url or request.path)

    @staticmethod
    def build_from_request(request):
        #TODO: use request.REQUEST ??
        kwargs = dict((str(k), v) for k, v in request.GET.items())
        kwargs.update(dict((str(k), v) for k, v in request.POST.items()))
        kwargs['url'] = request.path
        return ListViewState(**kwargs)

    def handle_research(self, request, header_filter_items):
        """
        Handle strings to use in order to filter
        (strings are in the request)
        """
        if self._search:
            if not request.POST and self.research:
                return

            REQUEST = request.REQUEST
            list_session = []

            for hfi in header_filter_items:
                if not hfi.has_a_filter:
                    continue

                name = hfi.name

                if not REQUEST.has_key(name):
                    continue

                filtered_attr = [smart_str(value.strip()) for value in REQUEST.getlist(name) or [REQUEST.get(name)] if value.strip()]

                if filtered_attr:
                    list_session.append((name, hfi.pk, hfi.type, hfi.filter_string, filtered_attr)) #TODO: an object instead of a tuple ????

            self.research = list_session
        else:
            self.research = ()

    #TODO: move some parts of code to HeaderFilter ????
    #TODO: avoid query with a cache (HeaderFilterItem/CustomField/etc retrieved to build listview....)
    def get_q_with_research(self, model):
        query = Q()
        cf_searches = defaultdict(list)

        for item in self.research:
            name, pk_hf, type_, pattern, value = item

            if type_ == HFI_FIELD:
                query &= Q(**{str(_map_patterns(pattern)): _get_value_for_query(pattern, value)})
            elif type_ == HFI_RELATION:
                HF = get_object_or_404(HeaderFilterItem, pk=pk_hf)
                rct = HF.relation_content_type #TODO: remove ?? (see header_filter)
                model_class = rct.model_class() if rct is not None else Relation

                query &= model_class.filter_in(model, HF.relation_predicat, value[0])
            elif type_ == HFI_FUNCTION:
                HF = get_object_or_404(HeaderFilterItem, pk=pk_hf)
                if HF.has_a_filter:
                    query &= model.filter_users_func (name, value[0] )               
            elif type_ == HFI_CUSTOM:
                cf = CustomField.objects.get(pk=name)
                cf_searches[cf.field_type].append((cf, pattern, value))

        for field_type, searches in cf_searches.iteritems():
            if len(searches) == 1:
                cf, pattern, value = searches[0]
                related_name = cf.get_value_class().get_related_name()

                if cf.field_type in (CustomField.ENUM, CustomField.MULTI_ENUM):
                    value = CustomFieldEnumValue.objects.get(custom_field=cf, value=value[0]).id

                query &= Q(**{
                            '%s__custom_field' % related_name:  cf,
                            str(_map_patterns(pattern)):        _get_value_for_query(pattern, value),
                        })
            else:
                for cf, pattern, value in searches:
                    pattern = pattern.partition('__')[2] #remove 'tableprefix__'

                    if field_type in (CustomField.ENUM, CustomField.MULTI_ENUM):
                        value = CustomFieldEnumValue.objects.get(custom_field=cf, value=value[0]).id #TODO: group the queries on CustomFieldEnumValue

                    kwargs = {str(_map_patterns(pattern)): _get_value_for_query(pattern, value)}

                    query &= Q(pk__in=cf.get_value_class().objects.filter(custom_field=cf, **kwargs).values_list('entity_id', flat=True))

        return query
