################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
from enum import Enum
from functools import partial
from json import JSONDecodeError
from json import loads as json_load

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import Q, QuerySet
from django.http import HttpResponse
from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.views.generic.list import ListView

import creme.creme_core.gui.listview as lv_gui
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core import sorter
from creme.creme_core.core.entity_cell import EntityCell, EntityCellActions
from creme.creme_core.core.paginator import FlowPaginator
from creme.creme_core.forms.listview import ListViewSearchForm
from creme.creme_core.gui import actions
# from creme.creme_core.gui.actions import ActionRegistry
# from creme.creme_core.gui.actions import (
#     action_registry as global_actions_registry,
# )
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import CremeEntity
from creme.creme_core.models.entity_filter import (
    EntityFilter,
    EntityFilterList,
)
from creme.creme_core.models.header_filter import (
    HeaderFilter,
    HeaderFilterList,
)
from creme.creme_core.utils import get_from_GET_or_404, get_from_POST_or_404
from creme.creme_core.utils.meta import Order
from creme.creme_core.utils.queries import QSerializer
from creme.creme_core.utils.serializers import json_encode

from . import base

logger = logging.getLogger(__name__)


class SelectionMode(Enum):
    NONE = 'none'
    SINGLE = 'single'
    MULTIPLE = 'multiple'


class EntitiesList(base.PermissionsMixin, base.TitleMixin, ListView):
    """Base class for list-view of CremeEntities with a given type.

    List of features saved in session :
     - Choice of HeaderFilters (i.e. columns of the list).
     - Choice of EntityFilters (i.e. which entities to display).
     - Pagination, with a fast pagination mode when there is a lot of entities
       Related settings: PAGE_SIZES, DEFAULT_PAGE_SIZE_IDX, FAST_QUERY_MODE_THRESHOLD.
     - Ordering: some columns can be used to order the list ; the chosen column
       is used as main order criterion, the model's meta ordering information are used
       as secondary criteria.
     - Search: some columns can be used to search within the entities and so filter
       the list content.

    Other features :
     - Single & multi UIActions (e.g. 'view', 'edit', ...). See the method
       'get_action_registry()' to override the list of actions in a view inheriting this class.
     - Buttons (e.g. creation of an entity, CSV export...). See the method
       'get_buttons(self)' to override the displayed button in a view inheriting this class.
     - Additional queries to filter the rows/content (i.e. entities displayed):
        - from the HTTP request with the parameter "q_filter" (see the class
          attribute "requested_q_arg", & the method 'get_requested_q()' for examples).
        - customised by a view inheriting this class (see the attribute 'internal_q'
          & the method 'get_internal_q()').
    """
    model = CremeEntity  # TODO: CremeModel ??
    template_name = 'creme_core/generics/entities.html'
    content_template_name = 'creme_core/listview/content.html'

    title = _('List of {models}')

    view_tag = ViewTag.HTML_LIST
    mode: SelectionMode | None = None
    default_selection_mode: SelectionMode = SelectionMode.MULTIPLE

    # GET/POST parameters
    header_filter_id_arg: str = 'hfilter'
    entity_filter_id_arg: str = 'filter'
    selection_arg: str = 'selection'
    page_arg: str = 'page'
    page_size_arg: str = 'rows'
    sort_cellkey_arg: str = 'sort_key'
    sort_order_arg: str = 'sort_order'
    requested_q_arg: str = 'q_filter'
    search_arg: str = 'search'
    transient_arg: str = 'transient'

    is_popup_view: bool = False
    # actions_registry: ActionRegistry = global_actions_registry
    action_registry: actions.ActionRegistry = actions.action_registry
    reload_url_name: str = ''

    state_class: type[lv_gui.ListViewState] = lv_gui.ListViewState

    cell_sorter_registry: sorter.CellSorterRegistry = sorter.cell_sorter_registry
    query_sorter_class: type[sorter.QuerySorter] = sorter.QuerySorter

    search_field_registry: lv_gui.ListViewSearchFieldRegistry = lv_gui.search_field_registry
    search_form_class: type[ListViewSearchForm] = ListViewSearchForm

    aggregator_registry: lv_gui.ListViewAggregatorRegistry = lv_gui.aggregator_registry

    default_headerfilter_id: str | None = None
    default_entityfilter_id: str | None = None

    # NB: see get_buttons()
    button_classes: list[type[lv_gui.ListViewButton]] = [
        lv_gui.CreationButton,
        lv_gui.MassExportButton,
        lv_gui.MassExportHeaderButton,
        lv_gui.MassImportButton,
        lv_gui.BatchProcessButton,
        lv_gui.VisitorModeButton,
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
        self.search_form = None

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
        self.search_form = self.get_search_form()

        unordered_queryset, self.count = self.get_unordered_queryset_n_count()
        self.fast_mode = self.get_fast_mode()
        self.ordering = ordering = self.get_ordering()
        self.queryset = unordered_queryset.order_by(*ordering)

    def get(self, request, *args, **kwargs):
        self.arguments = request.GET

        self._build()

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.arguments = POST = request.POST
        self.transient = transient = POST.get(self.transient_arg) in {'1', 'true'}

        self._build()

        response = super().get(request, *args, **kwargs)

        if not transient:
            self.state.register_in_session(request)

        return response

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        # user.has_perm_to_access_or_die(self.model._meta.app_label)
        user.has_perm_to_list_or_die(self.model)

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

        logger.critical(
            'No HeaderFilter is available for <%s>; '
            'the developer should have created one in "populate.py" script',
            model,
        )

        class EmergencyHeaderFilterCreation(HeaderFilterCreation):
            def get_context_data(self, **kwargs):
                context = super().get_context_data(**kwargs)
                context['help_message'] = _(
                    'The desired list does not have any view, please create one.'
                )

                return context

            def get_success_url(self):
                return self.request.path

        return EmergencyHeaderFilterCreation.as_view()(
            request,
            ct_id=ContentType.objects.get_for_model(model).id,
        )

    # def get_actions_registry(self) -> ActionRegistry:
    def get_action_registry(self) -> actions.ActionRegistry:
        """Get the registry of UIActions."""
        # return self.actions_registry
        return self.action_registry

    def get_cells(self, hfilter: HeaderFilter) -> list[EntityCell]:
        cells = hfilter.cells

        if self.get_show_actions():
            cells.insert(
                0,
                EntityCellActions(
                    model=self.model,
                    # actions_registry=self.get_actions_registry(),
                    action_registry=self.get_action_registry(),
                )
            )

        return cells

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view_tag'] = self.view_tag
        context['content_template'] = self.content_template_name

        context['model'] = self.model
        context['list_view_state'] = self.state

        context['list_title'] = self.get_title()
        context['sub_title'] = self.get_sub_title()

        context['header_filters'] = self.header_filters
        context['entity_filters'] = self.entity_filters

        context['extra_q'] = self.extra_q
        context['search_form'] = self.search_form

        # NB: cannot set it within the template because the reloading case needs it too
        context['is_popup_view'] = self.is_popup_view
        context['reload_url'] = self.get_reload_url()

        context['selection_mode'] = self.mode.value
        context['is_selection_enabled'] = (self.mode is not SelectionMode.NONE)
        context['is_selection_multiple'] = (self.mode is SelectionMode.MULTIPLE)
        context['buttons'] = self.get_buttons()
        context['page_sizes'] = settings.PAGE_SIZES

        # TODO: pass the bulk_update_registry in a list-view context
        #  (see listview_td_action_for_cell)
        # TODO: regroup registries ??
        context['cell_sorter_registry'] = self.get_cell_sorter_registry()

        context['aggregations'] = (
            {} if self.is_popup_view else
            self.aggregator_registry.aggregation_for_cells(
                queryset=self.queryset,
                cells=self.header_filters.selected.filtered_cells,
            )
        )

        return context

    def get_buttons(self) -> lv_gui.ListViewButtonList:
        return lv_gui.ListViewButtonList(self.button_classes)

    def get_entity_filter(self, entity_filters: EntityFilterList) -> EntityFilter:
        return self.state.set_entityfilter(
            entity_filters=entity_filters,
            filter_id=self.arguments.get(self.entity_filter_id_arg),
            default_id=self.default_entityfilter_id,
        )

    def get_entity_filters(self) -> EntityFilterList:
        return EntityFilterList(
            # TODO: cache? argument? method? both?
            content_type=ContentType.objects.get_for_model(self.model),
            user=self.request.user,
            extra_filter_id=self.arguments.get(self.entity_filter_id_arg),
        )

    def get_reload_url(self) -> str:
        """Return custom listview reload url."""
        name = self.reload_url_name
        return reverse(name) if name else ''

    def get_internal_q(self) -> Q:
        """Return a Q instance corresponding to an extra-filtering specific to the view."""
        return self.internal_q

    def get_requested_q(self) -> Q:
        """Build a Q instance (used to filter the entities' Queryset) from GET data.

        The name of the GET argument used is given by the attribute 'requested_q_arg'.
        The value of the argument use the format of 'creme_core.utils.queries.QSerializer.dumps()'
        Example:
            my_uri = '{url}?{arg}={value}'.format(
                url=Contact.get_lv_absolute_url(),
                arg=EntitiesList.requested_q_arg,
                value=QSerializer.dumps(Q(last_name='Smith')),
            )

        Hint: in templates, you can use the templatetag 'listview_q_argument'
              (from the library 'creme_listview') to generate this argument.
        """
        arg_name = self.requested_q_arg
        json_q_filter = self.arguments.get(arg_name)

        # TODO: better validation (e.g. corresponding EntityCell allowed + searchable ?) ?
        #  - limit the max depth of sub-fields chain ?
        #  - do not allow all fields ?
        if json_q_filter:
            try:
                return QSerializer().loads(json_q_filter)
            except JSONDecodeError:
                logger.exception(
                    'Error when decoding the argument "%s": %s',
                    arg_name, json_q_filter,
                )

        return Q()

    def get_fast_mode(self) -> bool:
        return self.count >= settings.FAST_QUERY_MODE_THRESHOLD

    def get_header_filter(self, header_filters: HeaderFilterList) -> HeaderFilter:
        return self.state.set_headerfilter(
            header_filters,
            id=self.arguments.get(self.header_filter_id_arg, ''),
            default_id=self.default_headerfilter_id,
        )

    def get_header_filters(self) -> HeaderFilterList:
        return HeaderFilterList(
            # TODO: cache ? argument ? method ? both ?
            content_type=ContentType.objects.get_for_model(self.model),
            user=self.request.user,
        )

    def get_mode(self) -> SelectionMode:
        """Get the selection mode.
        @return: Value in (SelectionMode.NONE, SelectionMode.SINGLE, SelectionMode.MULTIPLE).
        """
        func = get_from_POST_or_404 if self.request.method == 'POST' else get_from_GET_or_404
        return func(
            self.arguments, key=self.selection_arg,
            cast=SelectionMode, default=self.default_selection_mode,
        )

    def get_cell_sorter_registry(self) -> sorter.CellSorterRegistry:
        return self.cell_sorter_registry

    def get_query_sorter_class(self) -> type[sorter.QuerySorter]:
        return self.query_sorter_class

    def get_query_sorter(self) -> sorter.QuerySorter:
        cls = self.get_query_sorter_class()

        return cls(self.get_cell_sorter_registry())

    def get_ordering(self) -> tuple[str, ...]:
        state = self.state
        get = self.arguments.get
        sort_info = self.get_query_sorter().get(
            model=self.model,
            cells=self.cells,
            cell_key=get(self.sort_cellkey_arg, state.sort_cell_key),
            order=Order.from_string(
                get(self.sort_order_arg, state.sort_order),
                required=False,
            ),
            fast_mode=self.fast_mode,
        )
        state.sort_cell_key = sort_info.main_cell_key
        state.sort_order = str(sort_info.main_order)

        return sort_info.field_names

    def get_paginate_by(self, queryset) -> int:
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
            paginator = Paginator(
                queryset,
                per_page=per_page, orphans=orphans,
                allow_empty_first_page=allow_empty_first_page,
            )
            paginator.count = self.count
        else:
            paginator = FlowPaginator(
                queryset=queryset, key=self.ordering[0],
                per_page=per_page, count=self.count,
            )

        return paginator

    def get_queryset(self):
        # assert self.queryset is not None TODO ?
        return self.queryset

    def get_unordered_queryset_n_count(self) -> tuple[QuerySet, int]:
        # Cannot use this because it uses get_ordering() too early
        qs = self.model._default_manager.filter(is_deleted=False)
        # state = self.state

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
                logger.exception(
                    'Error when building the search queryset: invalid q_filter (%s).',
                    e,
                )
            else:
                filtered = True
                use_distinct = True

        # state.extra_q = extra_q

        # ----
        search_q = self.search_form.search_q
        if search_q:
            try:
                qs = qs.filter(search_q)
            except Exception as e:
                logger.exception(
                    'Error when building the search queryset with Q=%s (%s).',
                    search_q, e,
                )
            else:
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
        if filtered:
            count = qs.count()
        else:
            model = self.model
            try:
                count = EntityCredentials.filter_entities(
                    user,
                    CremeEntity.objects.filter(
                        is_deleted=False,
                        entity_type=ContentType.objects.get_for_model(model),
                    ),
                    as_model=model,
                ).count()
            except EntityCredentials.FilteringError as e:
                logger.debug(
                    '%s.get_unordered_queryset_n_count() : fast count is not possible (%s)',
                    type(self).__name__, e,
                )
                count = qs.count()

        return qs, count

    def get_search_field_registry(self) -> lv_gui.ListViewSearchFieldRegistry:
        return self.search_field_registry

    def get_search_form(self) -> ListViewSearchForm:
        arguments = self.arguments
        state = self.state

        form_builder = partial(
            self.get_search_form_class(),
            field_registry=self.get_search_field_registry(),
            cells=self.cells,
            user=self.request.user,
        )

        if arguments.get(self.search_arg, '') == 'clear':
            form = form_builder(data={})
            form.full_clean()
        else:
            form = form_builder(data=arguments)
            form.full_clean()

            if not form.filtered_data:
                stored_search = state.search

                if stored_search:
                    form = form_builder(data=stored_search)
                    form.full_clean()

        state.search = form.filtered_data

        return form

    def get_search_form_class(self) -> type[ListViewSearchForm]:
        return self.search_form_class

    def get_show_actions(self) -> bool:
        return not self.is_popup_view

    def get_state_class(self) -> type[lv_gui.ListViewState]:
        return self.state_class

    def get_state_id(self) -> str:
        return self.request.path

    def get_state(self) -> lv_gui.ListViewState:
        return self.get_state_class().get_or_create_state(
            self.request, url=self.get_state_id(),
        )

    def get_sub_title(self):
        return ''

    def get_template_names(self):
        if self.arguments.get('content'):
            return self.content_template_name
        else:
            return self.template_name

    def get_title_format_data(self) -> dict:
        data = super().get_title_format_data()
        data['models'] = self.model._meta.verbose_name_plural

        return data

    def page_builder_for_paginator(self, paginator):
        state = self.state

        try:
            page_number = int(self.arguments[self.page_arg])
        except (KeyError, ValueError, TypeError):
            page_number = state.page or 1

        page_obj = paginator.get_page(page_number)
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

        page_obj = paginator.get_page(page_info)
        state.page = json_encode(page_obj.info())

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
    template_name = 'creme_core/generics/entities-popup.html'
    is_popup_view = True
    view_tag = ViewTag.HTML_FORM
    reload_url_name = 'creme_core__listview_popup'

    # TODO: true HeaderFilter creation in inner popup
    def handle_no_header_filter(self, request):
        # TODO: title ('ERROR' ?)
        # TODO: remove the second button (selection button)
        return HttpResponse(
            gettext('The desired list does not have any view, please create one.'),
        )
