# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

# from itertools import chain
from json import loads as json_load, dumps as json_dump

import logging
# import warnings

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.db.models.query_utils import Q
from django.http import HttpResponse
# from django.shortcuts import render
# from django.template import Template, Context
# from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _, ugettext
from django.views.generic.list import ListView

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.entity_cell import EntityCellActions
from creme.creme_core.core.paginator import FlowPaginator, LastPage
from creme.creme_core.gui import listview as lv_gui
from creme.creme_core.gui.actions import actions_registry
from creme.creme_core.models import CremeEntity
from creme.creme_core.models.entity_filter import EntityFilterList
from creme.creme_core.models.header_filter import HeaderFilterList
from creme.creme_core.utils import get_from_POST_or_404, get_from_GET_or_404
from creme.creme_core.utils.queries import QSerializer  # get_q_from_dict

from . import base

logger = logging.getLogger(__name__)

# MODE_NORMAL = 0  # TODO ? (no selection)
MODE_SINGLE_SELECTION = 1
MODE_MULTIPLE_SELECTION = 2


# TODO: move as EntitiesList method ?
def str_to_mode(value):
    """Convert a string to list-view mode.
    Useful to convert a GET parameter.
    """
    if value == 'single':
        return MODE_SINGLE_SELECTION

    if value == 'multiple':
        return MODE_MULTIPLE_SELECTION

    raise ValueError('Must be "single" or "multiple"')


# def _clean_value(value, converter, default=None):
#     warnings.warn('creme_core.views.generic.listview._clean_value() is deprecated.',
#                   DeprecationWarning
#                  )
#
#     try:
#         return converter(value)
#     except Exception as e:
#         if default is not None:
#             return default
#
#         raise e


# def _build_entity_queryset(user, model, list_view_state, extra_q, entity_filter, header_filter):
#     filtered = False
#     use_distinct = False
#     queryset = model.objects.filter(is_deleted=False)
#
#     if entity_filter:
#         filtered = True
#         queryset = entity_filter.filter(queryset)
#
#     if extra_q:
#         try:
#             queryset = queryset.filter(extra_q)
#         except Exception as e:
#             logger.exception('Error when building the search queryset: invalid q_filter (%s).', e)
#         else:
#             filtered = True
#             use_distinct = True
#
#     list_view_state.extra_q = extra_q
#
#     lv_state_q = list_view_state.get_q_with_research(model, header_filter.cells)
#     try:
#         queryset = queryset.filter(lv_state_q)
#     except Exception as e:
#         logger.exception('Error when building the search queryset with Q=%s (%s).', lv_state_q, e)
#     else:
#         if lv_state_q:
#             filtered = True
#             use_distinct = True
#
#     queryset = EntityCredentials.filter(user, queryset)
#
#     if use_distinct:
#         queryset = queryset.distinct()
#
#     # If the query does not use the real entities' specific fields to filter,
#     # we perform a query on CremeEntity & so we avoid a JOIN.
#     count = queryset.count() if filtered else \
#             EntityCredentials.filter_entities(
#                     user,
#                     CremeEntity.objects.filter(
#                          is_deleted=False,
#                          entity_type=ContentType.objects.get_for_model(model),
#                         ),
#                     as_model=model,
#                 ).count()
#
#     return queryset, count


# def _build_entities_page(arguments, list_view_state, queryset, size, count, ordering, fast_mode=False):
#     if not fast_mode:
#         paginator = Paginator(queryset, size)
#         paginator.count = count
#
#         try:
#             page = int(arguments['page'])
#         except (KeyError, ValueError, TypeError):
#             page = list_view_state.page or 1
#
#         try:
#             entities_page = paginator.page(page)
#         except (EmptyPage, InvalidPage):
#             entities_page = paginator.page(paginator.num_pages)
#
#         list_view_state.page = entities_page.number
#     else:
#         paginator = FlowPaginator(queryset=queryset, key=ordering[0], per_page=size, count=count)
#         page_str = arguments.get('page') or str(list_view_state.page)
#
#         try:
#             page_info = json_load(page_str)
#         except ValueError:
#             page_info = None
#         else:
#             if not isinstance(page_info, dict):
#                 page_info = None
#
#         try:
#             entities_page = paginator.page(page_info)
#         except LastPage:
#             entities_page = paginator.last_page()
#         except InvalidPage:
#             entities_page = paginator.page()
#
#         list_view_state.page = json_dump(entities_page.info(), separators=(',', ':'))
#
#     return entities_page


# def _build_extrafilter(arguments, extra_filter=None):
#     json_q_filter = arguments.get('q_filter')
#     q_filter = Q()
#     serializer = QSerializer()
#
#     if json_q_filter:
#         try:
#             q_filter = serializer.loads(json_q_filter)
#         except:
#             try:
#                 q_filter = get_q_from_dict(_clean_value(json_q_filter, json_load, {}))
#             except:
#                 raise
#             else:
#                 warnings.warn('Old format for "q_filter" is deprecated is used : {}'.format(json_q_filter),
#                               DeprecationWarning
#                              )
#
#     return (serializer.dumps(q_filter),
#             q_filter if extra_filter is None else q_filter & extra_filter
#            )


# def _select_entityfilter(arguments, entity_filters, default_filter):
#     efilter_id = arguments.get('filter', default_filter)
#     return entity_filters.select_by_id(efilter_id)


# def _build_rowscount(arguments, list_view_state):
#     PAGE_SIZES = settings.PAGE_SIZES
#
#     try:
#         rows = int(arguments.get('rows'))
#     except (ValueError, TypeError):
#         rows = list_view_state.rows or PAGE_SIZES[settings.DEFAULT_PAGE_SIZE_IDX]
#     else:
#         if rows not in PAGE_SIZES:
#             rows = PAGE_SIZES[settings.DEFAULT_PAGE_SIZE_IDX]
#
#         list_view_state.rows = rows
#
#     return rows


# def list_view_content(request, model, hf_pk='', extra_dict=None,
#                       template='creme_core/generics/list_entities.html',
#                       show_actions=True, extra_q=None, mode=MODE_MULTIPLE_SELECTION, post_process=None,
#                       content_template='creme_core/frags/list_view_content.html',
#                       lv_state_id=None
#                      ):
#     """ Generic list_view wrapper / generator
#     Accepts only CremeEntity model and subclasses.
#     @param post_process: Function that takes the template context and the
#                          request as parameters (so you can modify the context).
#     """
#     assert issubclass(model, CremeEntity), '{} is not a subclass of CremeEntity'.format(model)
#
#     PAGE_SIZES = settings.PAGE_SIZES
#
#     is_GET = request.method == 'GET'
#     arguments = request.GET if is_GET else request.POST
#     lv_state_id = lv_state_id or request.path
#     current_lvs = lv_gui.ListViewState.get_or_create_state(request, url=lv_state_id)
#
#     rows = _build_rowscount(arguments, current_lvs)
#
#     transient = is_GET or (arguments.get('transient') in {'1', 'true'})
#     ct = ContentType.objects.get_for_model(model)
#     user = request.user
#     header_filters = HeaderFilterList(ct, user)
#
#     hf = current_lvs.set_headerfilter(header_filters, arguments.get('hfilter', -1), hf_pk)
#     cells = hf.cells
#
#     if show_actions:
#         cells.insert(0, EntityCellActions(model=model, actions_registry=actions_registry))
#
#     if arguments.get('search', '') == 'clear':
#         current_lvs.clear_research()
#     else:
#         current_lvs.handle_research(arguments, cells, merge=transient)
#
#     entity_filters = EntityFilterList(ct, user)
#     efilter = _select_entityfilter(arguments, entity_filters, current_lvs.entity_filter_id)
#     current_lvs.entity_filter_id = efilter.id if efilter else None
#
#     json_q_filter, extra_filter = _build_extrafilter(arguments, extra_q)
#
#     entities, count = _build_entity_queryset(user, model, current_lvs, extra_filter, efilter, hf)
#     fast_mode = (count >= settings.FAST_QUERY_MODE_THRESHOLD)
#     ordering = current_lvs.set_sort(model, cells,
#                                     cell_key=arguments.get('sort_field', current_lvs.sort_field),
#                                     order=arguments.get('sort_order', current_lvs.sort_order),
#                                     fast_mode=fast_mode,
#                                    )
#
#     entities_page = _build_entities_page(arguments, current_lvs, entities.order_by(*ordering),
#                                          size=rows, count=count, ordering=ordering, fast_mode=fast_mode,
#                                         )
#
#     if not transient:
#         current_lvs.register_in_session(request)
#
#     template_dict = {
#         'model':              model,
#         'list_title':         ugettext('List of {models}').format(models=model._meta.verbose_name_plural),
#         'sub_title':          '',
#         'header_filters':     header_filters,
#         'entity_filters':     entity_filters,
#         'entities':           entities_page,
#         'list_view_state':    current_lvs,
#         'content_type':       ct,
#         'content_type_id':    ct.id,
#         'search':             len(current_lvs.research) > 0,
#         'content_template':   content_template,
#         'page_sizes':         PAGE_SIZES,
#         'o2m':                (mode == MODE_SINGLE_SELECTION),
#         'add_url':            model.get_create_absolute_url(),
#         'extra_bt_templates': None,
#         'show_actions':       show_actions,
#         'extra_filter':       QSerializer().dumps(extra_filter),
#         'q_filter':           json_q_filter,
#         'research_cellkeys':  {cell_key for cell_key, _value in current_lvs.research},
#         'is_popup_view':      False,
#     }
#
#     if extra_dict:
#         template_dict.update(extra_dict)
#
#     if request.is_ajax():
#         template = template_dict['content_template']
#
#     if post_process:
#         post_process(template_dict, request)
#
#     # Optimisation time !!
#     hf.populate_entities(entities_page.object_list, user)
#
#     return template, template_dict


# def list_view(request, model, **kwargs):
#     """See list_view_content() for arguments"""
#
#     if request.method == 'POST':
#         mode = get_from_POST_or_404(request.POST, 'selection', cast=str_to_mode, default='multiple')
#     else:
#         mode = get_from_GET_or_404(request.GET, 'selection', cast=str_to_mode, default='multiple')
#
#     try:
#         template_name, template_dict = list_view_content(request, model, mode=mode, **kwargs)
#     except lv_gui.NoHeaderFilterAvailable:
#         from ..header_filter import HeaderFilterCreation
#
#         logger.critical('No HeaderFilter is available for <%s> ; '
#                         'the developer should have created one in "populate.py" script',
#                         model
#                        )
#
#         class EmergencyHeaderFilterCreation(HeaderFilterCreation):
#             def get_context_data(self, **kwargs):
#                 context = super().get_context_data(**kwargs)
#                 context['help_message'] = _('The desired list does not have any view, please create one.')
#
#                 return context
#
#             def get_success_url(self):
#                 return self.request.path
#
#         return EmergencyHeaderFilterCreation.as_view()(request, ct_id=ContentType.objects.get_for_model(model).id)
#
#     return render(request, template_name, template_dict)


# __inner_popup = Template(
# """<div class="in-popup" force-reload>
#     <div id="inner_header" style="display: none;">
#         <input name="inner_header_from_url" value="{{from_url}}" type="hidden"/>
#     </div>
#     <div name="inner_body">
#         <input type="hidden" name="whoami" value="{{whoami}}"/>
#         {% for persist_key, persist_values in persisted.items %}
#             {% for persist_value in persist_values %}
#                 <input type="hidden" name="{{persist_key}}" value="{{persist_value}}"/>
#                 <input type="hidden" name="persist" value="{{persist_key}}"/>
#             {% endfor %}
#         {% endfor %}
#         {{html}}
#     </div>
# </div>
# """)


# def list_view_popup(request, model, mode=MODE_SINGLE_SELECTION, lv_state_id=None, **kwargs):
#     """ Displays a list-view selector in an inner popup.
#     @param model: Class inheriting CremeEntity.
#     @param mode: Selection mode, in (MODE_SINGLE_SELECTION, MODE_MULTIPLE_SELECTION).
#     @param kwargs: See list_view_content().
#     """
#     assert mode in (MODE_SINGLE_SELECTION, MODE_MULTIPLE_SELECTION)
#
#     request.user.has_perm_to_access_or_die(model._meta.app_label)
#
#     # NB: we have duplicated the code of popup.inner_popup() in order to deprecate it without having
#     #     some annoying deprecation messages. This function will probably be removed in Creme 2.1
#     #     because of the big rework of the list-view code (class-based views, ...)
#
#     GET = request.GET
#     POST = request.POST
#     kwargs['show_actions'] = bool(int(GET.get('sa', False)))
#     whoami = POST.get('whoami') or GET.get('whoami')
#     extra_dict = {
#         'whoami':        whoami,
#         'is_popup_view': True,
#     }
#     tpl_persist = {
#         persist_key: POST.getlist(persist_key) + GET.getlist(persist_key)
#             for persist_key in chain(POST.getlist('persist'),
#                                      GET.getlist('persist'),
#                                     )
#     }
#
#     extra_dict.update(kwargs.pop('extra_dict', None) or {})
#
#     extra_q = kwargs.pop('extra_q', None)
#
#     try:
#         template_name, template_dict = list_view_content(
#             request, model=model, extra_dict=extra_dict,
#             template='creme_core/frags/list_view.html',
#             extra_q=extra_q,
#             mode=mode,
#             lv_state_id=lv_state_id,
#             **kwargs
#         )
#     except lv_gui.NoHeaderFilterAvailable:
#         html = ugettext('The desired list does not have any view, please create one.')
#     else:
#         template_dict['persisted'] = tpl_persist
#         template_dict['is_inner_popup'] = True
#         html = render_to_string(template_name, template_dict, request=request)
#
#     return HttpResponse(
#         __inner_popup.render(Context({
#             'html':      html,
#             'from_url':  request.path,
#             'whoami':    whoami,
#             'persisted': tpl_persist,
#         })),
#         content_type='text/html',
#     )


class EntitiesList(base.PermissionsMixin, base.TitleMixin, ListView):
    """Base class for list-view of CremeEntities with a given type.

    List of features saved in session :
     - Choice of HeaderFilters (ie: columns of the list).
     - Choice of EntityFilters (ie: which entities to display).
     - Pagination, with a fast pagination mode when there is a lot of entities
       Related settings : PAGE_SIZES, DEFAULT_PAGE_SIZE_IDX, FAST_QUERY_MODE_THRESHOLD.
     - Ordering: some columns can be used to order the list ; the chosen column
       is used as main order criterion, the model's meta ordering information are used
       as secondary criteria.
     - Search: some columns can be used to serach within the entities and so filter
       the list content.

    Other features :
     - Single & multi UIActions (eg: 'view', 'edit', ...). See the method
       'get_actions_registry()' to override the list of actions in a view inheriting this class.
     - Buttons (eg: creation of an entity, CSV export...). See the method
       'get_buttons(self)' to override the displayed button in a view inheriting this class.
     - Additional queries to filter the rows/content (ie: entities displayed):
        - from the HTTP request with the parameter "q_filter".
        - customised by a view inheriting this class (see the method 'get_internal_q()')
    """
    model = CremeEntity  # TODO: CremeModel ??
    template_name = 'creme_core/generics/entities.html'
    content_template_name = 'creme_core/listview/content.html'

    title = _('List of {models}')

    mode = None
    default_selection_mode = 'multiple'

    # GET/POST parameters
    header_filter_id_arg = 'hfilter'
    entity_filter_id_arg = 'filter'
    selection_arg = 'selection'
    page_arg = 'page'
    page_size_arg = 'rows'
    sort_field_arg = 'sort_field'
    sort_order_arg = 'sort_order'
    requested_q_arg = 'q_filter'
    search_arg = 'search'
    transient_arg = 'transient'

    is_popup_view = False
    actions_registry = actions_registry

    default_headerfilter_id = None
    default_entityfilter_id = None

    # NB: see get_buttons()
    button_classes = [
        lv_gui.CreationButton,
        lv_gui.MassExportButton,
        lv_gui.MassExportHeaderButton,
        lv_gui.MassImportButton,
        lv_gui.BatchProcessButton,
    ]

    internal_q = Q()

    def __init__(self):
        super().__init__()
        self.state = None

        self.header_filters = None
        self.header_filter = None

        self.entity_filters = None
        self.entity_filter = None

        self.arguments = None
        self.transient = True

        self.cells = None

        self.extra_q = None
        self.search = None

        self.queryset = None  # We hide voluntarily the class attribute which SHOULD not be used.
        self.count = None
        self.fast_mode = None
        self.ordering = None  # Idem

    def _build(self):
        self.mode = self.get_mode()
        self.state = self.get_state()

        self.header_filters = hfilters = self.get_header_filters()
        self.header_filter = hfilter = self.get_header_filter(hfilters)

        self.entity_filters = efilters = self.get_entity_filters()
        self.entity_filter = self.get_entity_filter(efilters)

        self.cells = self.get_cells(hfilter=hfilter)

        internal_extra_q = self.get_internal_q()
        requested_extra_q = self.get_requested_q()
        self.extra_q = {
            'internal': internal_extra_q,
            'requested': requested_extra_q,
            'total': internal_extra_q & requested_extra_q,
        }
        self.search = self.get_search()

        unordered_queryset, self.count = self.get_unordered_queryset_n_count()
        self.fast_mode = self.get_fast_mode()
        self.ordering = ordering = self.get_ordering()
        self.queryset = unordered_queryset.order_by(*ordering)

    def get(self, request, *args, **kwargs):
        self.arguments = request.GET

        self._build()

        return super(EntitiesList, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.arguments = POST = request.POST
        self.transient = transient = POST.get(self.transient_arg) in {'1', 'true'}

        self._build()

        response = super(EntitiesList, self).get(request, *args, **kwargs)

        if not transient:
            self.state.register_in_session(request)

        return response

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)

        model = self.model
        user.has_perm_to_access_or_die(model._meta.app_label)

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return self.handle_not_logged()

        self.check_view_permissions(user=user)

        try:
            return super().dispatch(request, *args, **kwargs)
        except lv_gui.NoHeaderFilterAvailable:
            return self.handle_no_header_filter(request)

    def handle_no_header_filter(self, request):
        from ..header_filter import HeaderFilterCreation

        model = self.model

        logger.critical('No HeaderFilter is available for <%s> ; '
                        'the developer should have created one in "populate.py" script',
                        model
                       )

        class EmergencyHeaderFilterCreation(HeaderFilterCreation):
            def get_context_data(self, **kwargs):
                context = super().get_context_data(**kwargs)
                context['help_message'] = _('The desired list does not have any view, please create one.')

                return context

            def get_success_url(self):
                return self.request.path

        return EmergencyHeaderFilterCreation.as_view()(request, ct_id=ContentType.objects.get_for_model(model).id)

    def get_actions_registry(self):
        """ Get the registry of UIActions.

        @return: Instance of <creme_core.gui.actions.ActionsRegistry>.
        """
        return self.actions_registry

    def get_cells(self, hfilter):
        cells = hfilter.cells

        if self.get_show_actions():
            cells.insert(0,
                         EntityCellActions(model=self.model,
                                           actions_registry=self.get_actions_registry(),
                                          )
                        )

        return cells

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['content_template'] = self.content_template_name

        context['model'] = self.model
        context['list_view_state'] = self.state

        context['list_title'] = self.get_title()
        context['sub_title'] = self.get_sub_title()

        context['header_filters'] = self.header_filters
        context['entity_filters'] = self.entity_filters

        context['extra_q'] = self.extra_q
        context['search'] = self.search

        # NB: cannot set it within the template because the reloading case needs it too
        context['is_popup_view'] = self.is_popup_view

        # TODO: rename/manage better in template  => context['mode'] (friendly class ?)
        context['o2m'] = (self.mode == MODE_SINGLE_SELECTION)
        context['buttons'] = self.get_buttons()
        context['page_sizes'] = settings.PAGE_SIZES

        # TODO: pass the bulk_update_registry in a list-view context (see listview_td_action_for_cell)

        return context

    def get_buttons(self):
        return lv_gui.ListViewButtonList(self.button_classes)

    def get_entity_filter(self, entity_filters):
        return self.state.set_entityfilter(
            entity_filters,
            filter_id=self.arguments.get(self.entity_filter_id_arg),
            default_id=self.default_entityfilter_id,
        )

    def get_entity_filters(self):
        return EntityFilterList(
            content_type=ContentType.objects.get_for_model(self.model),  # TODO: cache ? argument ? method ? both ?
            user=self.request.user,
        )

    def get_internal_q(self):
        return self.internal_q

    def get_requested_q(self):
        json_q_filter = self.arguments.get(self.requested_q_arg)

        # TODO: better validation (eg: corresponding EntityCell allowed + searchable ?) ?
        #  - limit the max depth of sub-fields chain ?
        #  - do no allow all fields ?
        return QSerializer().loads(json_q_filter) if json_q_filter else Q()

    def get_fast_mode(self):
        return self.count >= settings.FAST_QUERY_MODE_THRESHOLD

    def get_header_filter(self, header_filters):
        return self.state.set_headerfilter(
            header_filters,
            id=self.arguments.get(self.header_filter_id_arg, -1),
            default_id=self.default_headerfilter_id,
        )

    def get_header_filters(self):
        return HeaderFilterList(
            content_type=ContentType.objects.get_for_model(self.model),  # TODO: cache ? argument ? method ? both ?
            user=self.request.user,
        )

    def get_mode(self):
        """ @return: Value in (MODE_SINGLE_SELECTION, MODE_MULTIPLE_SELECTION)."""
        func = get_from_POST_or_404 if self.request.method == 'POST' else get_from_GET_or_404

        return func(self.arguments, key=self.selection_arg,
                    cast=str_to_mode, default=self.default_selection_mode,
                   )

    def get_ordering(self):
        state = self.state
        get = self.arguments.get

        return state.set_sort(self.model, self.cells,
                              cell_key=get(self.sort_field_arg, state.sort_field),
                              order=get(self.sort_order_arg, state.sort_order),
                              fast_mode=self.fast_mode,
                             )

    def get_paginate_by(self, queryset):
        PAGE_SIZES = settings.PAGE_SIZES
        state = self.state

        try:
            rows = int(self.arguments.get(self.page_size_arg))
        except (ValueError, TypeError):
            rows = state.rows or PAGE_SIZES[settings.DEFAULT_PAGE_SIZE_IDX]
        else:
            if rows not in PAGE_SIZES:
                rows = PAGE_SIZES[settings.DEFAULT_PAGE_SIZE_IDX]

            state.rows = rows

        return rows

    def get_paginator(self, queryset, per_page, orphans=0,
                      allow_empty_first_page=True, **kwargs):
        # NB: self.paginator_class is not used...

        if not self.fast_mode:
            paginator = Paginator(queryset, per_page=per_page, orphans=orphans,
                                  allow_empty_first_page=allow_empty_first_page,
                                 )
            paginator.count = self.count
        else:
            paginator = FlowPaginator(queryset=queryset, key=self.ordering[0],
                                      per_page=per_page, count=self.count,
                                     )

        return paginator

    def get_queryset(self):
        # assert self.queryset is not None TODO ?
        return self.queryset

    def get_unordered_queryset_n_count(self):
        # Cannot use this because it use get_ordering() too early
        # qs = super().get_queryset().filter(is_deleted=False)
        qs = self.model._default_manager.filter(is_deleted=False)
        state = self.state

        filtered = False
        use_distinct = False

        # ----
        entity_filter = self.entity_filter

        if entity_filter:
            filtered = True
            qs = entity_filter.filter(qs)

        # ----
        extra_q = self.extra_q['total']

        if extra_q:
            try:
                qs = qs.filter(extra_q)
            except Exception as e:
                logger.exception('Error when building the search queryset: invalid q_filter (%s).', e)
            else:
                filtered = True
                use_distinct = True

        state.extra_q = extra_q   # TODO: only if valid ?

        # ----
        # TODO: method in ListViewState that returns the improved queryset ?
        lv_state_q = state.get_q_with_research(self.model, self.cells)
        try:
            qs = qs.filter(lv_state_q)
        except Exception as e:
            logger.exception('Error when building the search queryset with Q=%s (%s).', lv_state_q, e)
        else:
            if lv_state_q:
                filtered = True
                use_distinct = True

        # ----
        user = self.request.user
        qs = EntityCredentials.filter(user, qs)

        if use_distinct:
            qs = qs.distinct()

        # ----
        # If the query does not use the real entities' specific fields to filter,
        # we perform a query on CremeEntity & so we avoid a JOIN.
        model = self.model
        count = qs.count() if filtered else \
                EntityCredentials.filter_entities(
                        user,
                        CremeEntity.objects.filter(
                             is_deleted=False,
                             entity_type=ContentType.objects.get_for_model(model),
                            ),
                        as_model=model,
                    ).count()

        return qs, count

    # TODO: rework search API of ListViewState ; it's currently ugly
    def get_search(self):
        arguments = self.arguments
        state = self.state

        if arguments.get(self.search_arg, '') == 'clear':
            state.clear_research()
        else:
            state.handle_research(arguments, self.cells, merge=self.transient)

        return dict(state.research)  # TODO: rename

    def get_show_actions(self):
        return not self.is_popup_view

    def get_state_id(self):
        return self.request.path

    def get_state(self):
        return lv_gui.ListViewState.get_or_create_state(self.request, url=self.get_state_id())

    def get_sub_title(self):
        return ''

    # TODO: DO NOT WORK CORRECTLY with the popup view (is_ajax() always true, so "entities-popup.html" is never used)
    def get_template_names(self):
        return self.content_template_name if self.request.is_ajax() else self.template_name

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['models'] = self.model._meta.verbose_name_plural

        return data

    def page_builder_for_paginator(self, paginator):
        state = self.state

        try:
            page_number = int(self.arguments[self.page_arg])
        except (KeyError, ValueError, TypeError):
            page_number = state.page or 1

        try:
            page_obj = paginator.page(page_number)
        except (EmptyPage, InvalidPage):
            page_obj = paginator.page(paginator.num_pages)

        state.page = page_obj.number

        return page_obj

    def page_builder_for_flowpaginator(self, paginator):
        state = self.state
        page_str = self.arguments.get(self.page_arg) or str(state.page)

        try:
            page_info = json_load(page_str)
        except ValueError:
            page_info = None
        else:
            if not isinstance(page_info, dict):
                page_info = None

        try:
            page_obj = paginator.page(page_info)
        except LastPage:
            page_obj = paginator.last_page()
        except InvalidPage:
            page_obj = paginator.page()

        state.page = json_dump(page_obj.info(), separators=(',', ':'))

        return page_obj

    PAGE_BUILDERS = {
        Paginator:     page_builder_for_paginator,
        FlowPaginator: page_builder_for_flowpaginator,
    }

    def paginate_queryset(self, queryset, page_size):
        paginator = self.get_paginator(
            queryset, per_page=page_size,
            orphans=self.get_paginate_orphans(),
            allow_empty_first_page=self.get_allow_empty(),
        )
        page = self.PAGE_BUILDERS[type(paginator)](self, paginator=paginator)

        # Optimisation time !!
        self.header_filter.populate_entities(page.object_list, self.request.user)

        is_paginated = page.has_other_pages()

        return paginator, page, queryset, is_paginated


class BaseEntitiesListPopup(EntitiesList):
    """Base class for list-view in inner-popup."""
    # TODO: use it (see EntitiesList.get_template_names())
    # TODO: improve title display => move it to the popup header
    template_name = 'creme_core/generics/entities-popup.html'
    is_popup_view = True

    # TODO: true HeaderFilter creation in inner popup
    def handle_no_header_filter(self, request):
        # TODO: title ('ERROR' ?)
        # TODO: remove the second button (selection button)
        return HttpResponse(ugettext('The desired list does not have any view, please create one.'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # TODO: remove (remove in JS too)
        request = self.request
        context['whoami'] = request.POST.get('whoami') or request.GET.get('whoami')

        return context
