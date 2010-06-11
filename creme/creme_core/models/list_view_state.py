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

from datetime import date, time, datetime
from logging import debug

from django.db import models
from django.contrib.auth.models import User
from django.db.models import Model, CharField, IntegerField, BooleanField, ForeignKey
from django.db.models import Q
from django.utils.encoding import smart_str
from django.shortcuts import get_object_or_404
from django.db.models.sql.constants import QUERY_TERMS

from django_extensions.db import fields

from header_filter import HeaderFilterItem, HFI_FIELD, HFI_RELATION
from creme_core.models import Relation, CremePropertyType, CremeProperty

#lter/Buyer?filtername=listview_Buyer&filter=&_search=false&nd=1253623028873&rows=100&page=2&sidx=id&sord=desc

#class ListViewState(Model):
#    filtername = CharField(max_length=100)
#    filter     = IntegerField(default=0)
#    model      = CharField(max_length=100)
#    _search    = BooleanField(default=False)
#    nd         = CharField(max_length=300)
#    rows       = IntegerField(default=50)
#    page       = IntegerField(default=1)
#    sidx       = CharField(max_length=100, default='id')
#    sord       = CharField(max_length=4, default='asc')
#    user       = ForeignKey(User)
#
#    #def __init__(self, * args , ** kwargs):
#        #models.Model.__init__ (self, * args , ** kwargs )
#
#    def __unicode__(self):
#        return u''
#
#    class Meta:
#        app_label = 'creme_core'



def simple_value(value):
    if value:
        if hasattr(value, '__iter__') and len(value)==1:
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
            try:
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

def string_value(value):
    if value and isinstance(value, basestring):
        return value
    return '.*'

def bool_value(value):
    return bool(int_value(value))

QUERY_TERMS_FUNC = {
    'exact':       lambda x : x,
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
    query_terms_pattern = QUERY_TERMS.keys()
    patterns = pattern.split('__')
    patterns.reverse()#In general the pattern is at the end

    qterm = None
    for p in patterns:
        if p in query_terms_pattern:
            qterm = p
            break
    return QUERY_TERMS_FUNC.get(qterm, simple_value)(value)

def _map_patterns(custom_pattern):
    MAP_QUERY_PATTERNS = {
        'creme-boolean': 'exact',
    }
    patterns = custom_pattern.split('__')
    i = 0
    for pattern in patterns:
        patterns[i] = MAP_QUERY_PATTERNS.get(pattern, pattern)
        i += 1
    return "__".join(patterns)

class ListViewState(object):
    def __init__(self, **kwargs):
        self.filter_id = kwargs.get('filter')
        self.header_filter_id = kwargs.get('hfilter')
        self.page = kwargs.get('page')
        self.rows = kwargs.get('rows')
        self._search = kwargs.get('_search')
        self.sort_order = kwargs.get('sort_order')
        self.sort_field = kwargs.get('sort_field')
        self.url = kwargs.get('url')
        self.research = None
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
        kwargs = dict((str(k), v,) for k, v in request.GET.items())
        kwargs.update(dict((str(k), v,) for k, v in request.POST.items()))
        kwargs['url'] = request.path
        return ListViewState(**kwargs)

    def handle_research(self, request, queryset_header_filter_item):
        """
        Handle strings to use in order to filter
        (strings are in the request)
        """
        if self._search:
            if not request.POST and self.research:
                return

            REQUEST = request.REQUEST
            list_session = []
            reset_filter = 0

            for item in queryset_header_filter_item:
                if not item.has_a_filter:
                    continue

                attribut = item.name

                if not REQUEST.has_key(attribut):
                    continue

#                attribut_filtered = REQUEST[attribut].strip()
                attribut_filtered = [smart_str(value.strip()) for value in REQUEST.getlist(attribut) or [REQUEST.get(attribut)] if value.strip()]
#                debug("attribut_filtered : %s=|>%s<|", attribut, attribut_filtered)
#                debug("type(attribut_filtered) : %s", type(attribut_filtered))
                if attribut_filtered:
                    list_session.append((attribut, item.pk, item.type, item.filter_string, attribut_filtered)) #TODO: an object instead of a tuple ????
#                    list_session.append((attribut, item.pk, item.type, item.filter_string, smart_str(attribut_filtered))) #TODO: an object instead of a tuple ????
                else:
                    reset_filter += 1

            if len(queryset_header_filter_item) == reset_filter:
                self.research = None
            else:
                self.research = list_session
        else:
            self.research = None

#        debug("self.research : %s", self.research)

    def get_q_with_research(self, model):
        Q_list_total = Q()
        research = self.research
        if research:
            for item in research:
                name_attribut, pk_hf, type_, pattern, value = item
                Q_attribut = None

                if type_ == HFI_FIELD:
#                    Q_attribut = Q(**{str(pattern): value})
#                    debug("Q final : %s : %s", str(_map_patterns(pattern)), _get_value_for_query(pattern, value))
                    Q_attribut = Q(**{str(_map_patterns(pattern)): _get_value_for_query(pattern, value)})
                elif type_ == HFI_RELATION:
                    HF = get_object_or_404(HeaderFilterItem, pk=pk_hf)
                    rct = HF.relation_content_type
                    model_class = rct.model_class() if rct is not None else Relation
                    Q_attribut = model_class.filter_in(model, HF.relation_predicat, value)
                if Q_attribut:
                    Q_list_total &= Q_attribut
        return Q_list_total
