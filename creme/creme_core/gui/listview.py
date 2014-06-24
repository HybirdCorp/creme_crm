# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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
from functools import partial
import logging

from django.db.models import Q, DateField, DateTimeField, ForeignKey
from django.utils.encoding import smart_str
from django.utils.timezone import now

from ..core.entity_cell import (EntityCellRegularField, EntityCellCustomField,
        EntityCellFunctionField, EntityCellRelation)
from ..models import RelationType, Relation, CustomField
from ..utils import find_first
from ..utils.date_range import CustomRange
from ..utils.dates import get_dt_from_str

NULL_FK = 'NULL'


logger = logging.getLogger(__name__)

def simple_value(value):
    if value:
        if hasattr(value, '__iter__') and len(value) == 1:
            return value[0]
        return value
    return '' #TODO : Verify same semantic than "null" sql


class ListViewState(object):
    def __init__(self, **kwargs):
        get_arg = kwargs.get
        self.entity_filter_id = get_arg('filter')
        self.header_filter_id = get_arg('hfilter')
        self.page = get_arg('page')
        self.rows = get_arg('rows')
        self._search = get_arg('_search') #TODO: rename to search ?? or add property
        self.sort_order = get_arg('sort_order')
        self.sort_field = get_arg('sort_field')
        self._extra_sort_field = ''
        self.url = get_arg('url')
        self.research = ()
        self.extra_q = None

    def __repr__(self):
        return u'<ListViewState(efilter_id=%s, hfilter_id=%s, page=%s, rows=%s, _search=%s, sort=%s%s, url=%s, research=%s)>' % (
                    self.entity_filter_id, self.header_filter_id, self.page, self.rows,
                    self._search, self.sort_order, self.sort_field, self.url, self.research,
                )

    def register_in_session(self, request):
        session = request.session
        current_lvs = session.get(self.url or request.path) #TODO: pop() ??
        if current_lvs is not None:
            try:
                del session[self.url or request.path] #useful ???????
            except KeyError:
                pass
        session[self.url] = self

    @staticmethod
    def get_state(request, url=None):
        return request.session.get(url or request.path)

    @staticmethod
    def build_from_request(request):
        #TODO: use request.REQUEST ??
        kwargs = {str(k): v for k, v in request.GET.items()}
        kwargs.update((str(k), v) for k, v in request.POST.items())
        kwargs['url'] = request.path
        return ListViewState(**kwargs)

    def handle_research(self, request, cells):
        "Handle strings to use in order to filter (strings are in the request)."
        if self._search:
            if not request.POST and self.research:
                return

            getlist = request.REQUEST.getlist
            list_session = []

            for cell in cells:
                if not cell.has_a_filter:
                    continue

                cell_key = cell.key
                values = getlist(cell_key)

                if values:
                    filtered_attr = [smart_str(value.strip()) for value in values]

                    if filtered_attr and any(filtered_attr):
                        list_session.append((cell_key, filtered_attr))

            self.research = list_session
        else:
            self.research = ()

    def _build_condition(self, pattern, value):
        return {pattern.replace('creme-boolean', 'exact'): simple_value(value)}

    def _date_or_None(self, value, index):
        try:
            return get_dt_from_str(value[index]).date()
        except (IndexError, AttributeError):
            pass

    #def _datetime_or_None(self, value, index):
        #try:
            #return get_dt_from_str(value[index]).date()
        #except (IndexError, AttributeError):
            #pass

    def _build_date_range_dict(self, name, value):
        don = partial(self._date_or_None, value=value)
        return CustomRange(don(index=0), don(index=1)).get_q_dict(name, now())

    #def _build_datetime_range_dict(self, name, value):
        #don = partial(self._datetime_or_None, value=value)
        #return CustomRange(don(index=0), don(index=1)).get_q_dict(name, now())

    #TODO: move some parts of code to EntityCell (more object code) ?
    #TODO: 'filter_string' -> remove from Cell, or put all the research logic in Cells...
    def get_q_with_research(self, model, cells):
        query = Q()
        cf_searches = defaultdict(list)

        for item in self.research:
            cell_key, value = item
            cell = find_first(cells, (lambda cell: cell.key == cell_key), None) #TODO: move in EntityCellsList ??

            if cell is None:
                continue

            if isinstance(cell, EntityCellRegularField):
                field = cell.field_info[-1]
                #TODO: Hacks for dates => refactor
                #if isinstance(field, DateTimeField):
                    #condition = self._build_datetime_range_dict(cell.value, value)
                #elif isinstance(field, DateField):
                if isinstance(field, DateField):
                    condition = self._build_date_range_dict(cell.value, value)
                elif isinstance(field, ForeignKey) and value[0] == NULL_FK:
                    condition = {'%s__isnull' % cell.value: True}
                else:
                    condition = self._build_condition(cell.filter_string, value)

                query &= Q(**condition)
            elif isinstance(cell, EntityCellRelation):
                query &= Relation.filter_in(model, cell.relation_type, value[0])
            elif isinstance(cell, EntityCellFunctionField):
                if cell.has_a_filter:
                    query &= cell.function_field.filter_in_result(value[0])
            elif isinstance(cell, EntityCellCustomField):
                cf = cell.custom_field
                cf_searches[cf.field_type].append((cf, cell.filter_string, value))

        for field_type, searches in cf_searches.iteritems():
            if len(searches) == 1:
                cf, pattern, value = searches[0]
                related_name = cf.get_value_class().get_related_name()

                if field_type == CustomField.DATETIME:
                    #condition = self._build_datetime_range_dict('%s__value' % related_name, value)
                    condition = self._build_date_range_dict('%s__value' % related_name, value)
                else:
                    if field_type in (CustomField.ENUM, CustomField.MULTI_ENUM):
                        value = value[0]

                        if value == NULL_FK:
                            query &= Q(**{'%s__isnull' % related_name: True})
                            continue

                    condition = self._build_condition(pattern, value)

                condition.update({'%s__custom_field' % related_name: cf})

                query &= Q(**condition)
            else: #TODO; factorise...
                for cf, pattern, value in searches:
                    pattern = pattern.partition('__')[2] #remove 'tableprefix__'

                    if field_type == CustomField.DATETIME:
                        #condition = self._build_datetime_range_dict('value', value)
                        condition = self._build_date_range_dict('value', value)
                    else:
                        if field_type in (CustomField.ENUM, CustomField.MULTI_ENUM):
                            value = value[0]

                            if value == NULL_FK:
                                query &= ~Q(pk__in=cf.get_value_class()
                                                     .objects
                                                     .filter(custom_field=cf)
                                                     .values_list('entity_id', flat=True)
                                          )
                                continue

                        condition = self._build_condition(pattern, value)

                    query &= Q(pk__in=cf.get_value_class()
                                        .objects
                                        .filter(custom_field=cf, **condition)
                                        .values_list('entity_id', flat=True)
                              )

        return query

    #TODO: factorise with :
    #       - template_tags_creme_listview.get_listview_columns_header
    #       - EntityCell builders
    #TODO: beware, sorting by FK simply sort by id (Civility etc...) => can we improve that ??
    def set_sort(self, model, cells, field_name, order):
        "@param order string '' or '-'(reverse order)."
        sort_field = 'id'
        # extra field that is used to internally create the final query the
        # sort order is toggled by comparing sorting field and column name
        # (if it's the same '' <-> '-'), so we can not merge this extra field
        # in sort_field, or the toggling we never happen
        # (cell.name == sort_field # ==> cell.name != sort_field +'XXX')
        extra_sort_field = ''

        if field_name:
            if field_name != 'id': #avoids annoying log ('id' can not be related to a column)
                for cell in cells:
                    if cell.value == field_name:
                        if cell.sortable:
                            sort_field = field_name

                            if cell.filter_string.endswith('__header_filter_search_field__icontains'):
                                extra_sort_field = '__header_filter_search_field'

                        break
                else:
                    logger.warn('ListViewState.set_sort(): can not sort with field "%s"',
                                field_name
                               )
        else:
            ordering = model._meta.ordering

            if ordering:
                sort_field = ordering[0]

                if sort_field.startswith('-'):
                    order = '-'
                    sort_field = sort_field[1:]

        self.sort_field = sort_field
        self._extra_sort_field = extra_sort_field
        self.sort_order = order if order == '-' else ''

    def sort_query(self, queryset):
        "Beware: you should have called set_sort() before"
        return queryset.order_by(''.join((self.sort_order, self.sort_field, self._extra_sort_field)))


#-----------------------------------------------------------------------------

class _ModelSmartColumnsRegistry(object):
    __slots__ = ('_cells', '_relationtype')

    def __init__(self):
        self._cells = []
        self._relationtype = None #cache

    #TODO: factorise with json deserialisation of EntityCells
    def _get_cells(self, model):
        cells = []

        for cell_cls, data in self._cells:
            cell = None

            if cell_cls is EntityCellRegularField:
                cell = EntityCellRegularField.build(model=model, name=data)
            elif cell_cls is EntityCellFunctionField:
                cell = EntityCellFunctionField.build(model, func_field_name=data)
            else: #EntityCellRelation
                rtype = self._get_relationtype(data)

                if rtype is False:
                    logger.warn('SmartColumnsRegistry: relation type "%s" does not exist', data)
                else:
                    cell = EntityCellRelation(rtype)

            # Has no sense here:
            #  EntityCellActions : not configurable in HeaderFilter form
            #  EntityCellCustomField : dynamically created by user
            #TODO: other types

            if cell is not None:
                cells.append(cell)

        return cells

    def _get_relationtype(self, rtype_id):
        rtype = self._relationtype

        if rtype is None: #means: not retrieved yet
            try:
                rtype = RelationType.objects.get(pk=rtype_id)
            except RelationType.DoesNotExist:
                rtype = False #means: does not exist
            self._relationtype = rtype

        return rtype

    def register_function_field(self, func_field_name):
        self._cells.append((EntityCellFunctionField, func_field_name))
        return self

    def register_field(self, field_name):
        self._cells.append((EntityCellRegularField, field_name))
        return self

    def register_relationtype(self, rtype_id):
        self._cells.append((EntityCellRelation, rtype_id))
        return self


class SmartColumnsRegistry(object):
    def __init__(self):
        self._model_registries = defaultdict(_ModelSmartColumnsRegistry)

    def get_cells(self, model):
        return self._model_registries[model]._get_cells(model)

    def register_model(self, model):
        return self._model_registries[model]


smart_columns_registry = SmartColumnsRegistry()
