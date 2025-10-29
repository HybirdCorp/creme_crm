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

import json
import logging
from collections import defaultdict
from collections.abc import Iterable, Sequence
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import (
    BadRequest,
    FieldDoesNotExist,
    PermissionDenied,
)
from django.db import IntegrityError
from django.db.models import ProtectedError, Q
from django.db.transaction import atomic
from django.forms.fields import ChoiceField
from django.forms.models import modelform_factory
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.html import escape, format_html
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .. import constants
from ..auth import SUPERUSER_PERM
from ..auth.decorators import login_required
from ..auth.entity_credentials import EntityCredentials
from ..core import sorter
from ..core.cloning import EntityCloner, entity_cloner_registry
from ..core.deletion import EntityDeletor, entity_deletor_registry
from ..core.entity_cell import (
    CELLS_MAP,
    EntityCell,
    EntityCellCustomField,
    EntityCellRegularField,
)
from ..core.exceptions import (
    BadRequestError,
    ConflictError,
    SpecificProtectedError,
)
from ..core.paginator import FlowPaginator
from ..core.workflow import run_workflow_engine
from ..creme_jobs import trash_cleaner_type
from ..forms import CremeEntityForm
from ..forms.listview import ListViewSearchForm
from ..forms.merge import MergeEntitiesBaseForm
from ..forms.merge import form_factory as merge_form_factory
# NB: do no import <bulk_update_registry> to facilitate unit testing
from ..gui import bulk_update
from ..gui.listview import search
from ..gui.merge import merge_form_registry
from ..http import CremeJsonResponse, is_ajax
# from ..models import Relation
from ..models import (
    CremeEntity,
    CremeUser,
    EntityFilter,
    EntityJobResult,
    FieldsConfig,
    HeaderFilter,
    Job,
    Sandbox,
    TrashCleaningCommand,
)
from ..models.fields import UnsafeHTMLField
from ..utils import (
    bool_from_str_extended,
    get_from_GET_or_404,
    get_from_POST_or_404,
)
from ..utils.collections import LimitedList
from ..utils.html import sanitize_html
from ..utils.meta import ModelFieldEnumerator, Order
from ..utils.queries import QSerializer
from ..utils.serializers import json_encode
from ..utils.translation import smart_model_verbose_name
from ..utils.unicode_collation import collator
from . import generic
from .decorators import jsonify, workflow_engine
from .generic import base, detailview, listview

logger = logging.getLogger(__name__)


@login_required
@jsonify
def get_creme_entities_repr(request, entities_ids):
    # With the url regexp we are sure that int() will work
    e_ids = [int(e_id) for e_id in entities_ids.split(',') if e_id]

    entities = CremeEntity.objects.in_bulk(e_ids)
    CremeEntity.populate_real_entities([*entities.values()])

    return [
        {
            'id': e_id,
            'text': entity.get_real_entity().get_entity_summary(request.user),
        }
        for e_id, entity in ((e_id, entities.get(e_id)) for e_id in e_ids)
        if entity is not None
    ]


@method_decorator(xframe_options_sameorigin, name='dispatch')
class HTMLFieldSanitizing(generic.base.EntityRelatedMixin,
                          generic.CheckedView):
    """Used to show an HTML document in an <iframe>."""
    field_name_url_kwarg = 'field_name'

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_view_or_die(entity)

    def get(self, request, *args, **kwargs):
        entity = self.get_related_entity()
        field_name = kwargs[self.field_name_url_kwarg]

        try:
            field = entity._meta.get_field(field_name)
        except FieldDoesNotExist as e:
            raise ConflictError('This field does not exist.') from e

        if not isinstance(field, UnsafeHTMLField):
            raise ConflictError('This field is not an HTMLField.')

        unsafe_value = getattr(entity, field_name)

        return HttpResponse(
            '' if not unsafe_value else
            sanitize_html(
                unsafe_value,
                allow_external_img=request.GET.get('external_img', False),
            )
        )


# TODO: bake the result in HTML instead of ajax view ??
class FieldsInformation(generic.base.EntityCTypeRelatedMixin,
                        generic.CheckedView):
    response_class = CremeJsonResponse

    def get_info(self):
        model = self.get_ctype().model_class()

        # TODO: use django.forms.models.fields_for_model ?
        form = modelform_factory(model, CremeEntityForm)(user=self.request.user)
        required_fields = [
            name
            for name, field in form.fields.items()
            if field.required and name != 'user'
        ]

        kwargs = {}
        if len(required_fields) == 1:
            required_field = required_fields[0]
            kwargs['printer'] = lambda field: (
                str(field.verbose_name)
                if field.name != required_field else
                gettext('{field} [CREATION]').format(field=field.verbose_name)
            )

        is_hidden = FieldsConfig.objects.get_for_model(model).is_field_hidden

        return ModelFieldEnumerator(model).filter(
            viewable=True,
        ).exclude(
            lambda model, field, depth: is_hidden(field)
        ).choices(**kwargs)

    def get(self, *args, **kwargs):
        return self.response_class(
            self.get_info(),
            safe=False,  # Result is not a dictionary
        )


class Clone(base.EntityRelatedMixin, base.CheckedView):
    entity_id_arg = 'id'

    cloner_registry = entity_cloner_registry

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cloner = None

    def get_cloner_for_entity(self, entity: CremeEntity) -> EntityCloner:
        """Gets the cloner for an entity (based of its type).
        @raise ConflictError if this tpe has not registered cloner.
        """
        cloner = self.cloner
        if cloner is None:
            cloner = self.cloner_registry.get(model=type(entity))

            if cloner is None:
                raise ConflictError(gettext(
                    'This model does not use the generic clone view.'
                ))

            self.cloner = cloner

        return cloner

    def check_related_entity_permissions(self, entity, user):
        self.get_cloner_for_entity(entity).check_permissions(user=user, entity=entity)

    def get_related_entity_id(self):
        return get_from_POST_or_404(self.request.POST, self.entity_id_arg)

    def post(self, request, *args, **kwargs):
        entity = self.get_related_entity()
        new_entity = self.get_cloner_for_entity(entity).perform(user=request.user, entity=entity)

        if is_ajax(request):
            return HttpResponse(new_entity.get_absolute_url())

        return redirect(new_entity)


# TODO: factorise with MassExport
class NextEntityVisiting(base.EntityCTypeRelatedMixin, base.CheckedView):
    """View which allows to visit all the detail-views of the entities
     contained by a list-view (including ordering, filtering...).

    To start the visit (see <..gui.listview.buttons.VisitorModeButton>), pass
    the ordering & filtering data in GET arguments (only "sort" & "hfilter" are
    mandatory) but not "index" & "page_info".
    The view will redirect to the next detail-view, with the visit data
    (see <..gui.visit.EntityVisitor>) serialized in a GET argument, so the
    detail-view can build an EntityVisitor instance & link again the visit view
    to continue the visit (see <generic.detailview.EntityDetail>).

    Design notes:
     * no information is stored in the current session (or in a specific Model)
         - you cannot get a UI which list all the current visits.
         - ...even after a crash (but browser are globally reliable to restore
           you tabs).
         + you can pass the current detail-view's URI to another computer (or
           even another user) in order the visit is resumed on another computer.
     * the next detail-view's URL is calculated at the last moment (i.e. the
       current detail-view does not know the URL of the next detail-view), so we
       limit the risk to get a 403/404 during the visit (if entities are deleted
       or modified by another user for example).
    """
    # ct_id_arg = 'ct_id' in mass-export
    headerfilter_id_arg = 'hfilter'
    entityfilter_id_arg = 'efilter'
    # NB: in mass-export
    #   sort_cellkey_arg = 'sort_key'
    #   sort_order_arg = 'sort_order'
    sort_arg = 'sort'

    internal_q_arg = 'internal_q'
    requested_q_arg = 'requested_q'

    page_arg = 'page'
    index_arg = 'index'

    callback_url_arg = 'callback'

    cell_sorter_registry = sorter.cell_sorter_registry
    query_sorter_class   = sorter.QuerySorter

    search_field_registry = search.search_field_registry
    search_form_class     = ListViewSearchForm

    end_template_name = 'creme_core/visit-end.html'
    detail_view = detailview.EntityDetail

    def get_callback_url(self):
        cb_url = self.request.GET.get(self.callback_url_arg)

        if not cb_url:
            raise Http404('Missing callback URL for exploration mode.')

        if not cb_url.startswith('/') or cb_url.startswith('//'):
            raise ConflictError('The callback URL for exploration mode must be an internal URL.')

        return cb_url

    def get_cells(self, header_filter) -> list[EntityCell]:
        return header_filter.filtered_cells

    # NB: in mass-export
    # def get_ctype_id(self):
    #     return get_from_GET_or_404(self.request.GET, self.ct_id_arg, cast=int)

    def get_cell_sorter_registry(self) -> sorter.CellSorterRegistry:
        return self.cell_sorter_registry

    def get_query_sorter_class(self) -> type[sorter.QuerySorter]:
        return self.query_sorter_class

    def get_query_sorter(self) -> sorter.QuerySorter:
        cls = self.get_query_sorter_class()
        return cls(self.get_cell_sorter_registry())

    def get_entity_filter_id(self) -> str | None:
        return self.request.GET.get(self.entityfilter_id_arg)

    def get_entity_filter(self) -> EntityFilter | None:
        efilter_id = self.get_entity_filter_id()

        return get_object_or_404(
            EntityFilter.objects
                        .filter_by_user(self.request.user)
                        .filter(entity_type=self.get_ctype()),
            id=efilter_id,
        ) if efilter_id else None

    def get_header_filter_id(self) -> str:
        return get_from_GET_or_404(self.request.GET, self.headerfilter_id_arg)

    def get_header_filter(self) -> HeaderFilter:
        return get_object_or_404(
            HeaderFilter.objects
                        .filter_by_user(self.request.user)
                        .filter(entity_type=self.get_ctype()),
            id=self.get_header_filter_id(),
        )

    def get_paginator(self, *, queryset, ordering: Sequence[str]) -> FlowPaginator:
        # NB: we use the smartness of FlowPaginator to retrieve only 3 entities
        #  (page size + 1), instead of juste using an index + whole queryset.
        #  it retrieves the value of the key field, & it takes cares about
        #  duplicates (like Organisation with the same name) by adding an OFFSET
        #  but only when it's need.
        #  Maybe, we could recode this to retrieve only 2 entities, but it does
        #  not seem very useful.
        return FlowPaginator(
            queryset=queryset.order_by(*ordering),
            key=ordering[0],
            per_page=2,  # NB: cannot
        )

    def get_index_n_page_info(self) -> tuple[int, dict | None]:
        GET = self.request.GET

        try:
            index_str = GET[self.index_arg]
            page_str = GET[self.page_arg]
        except KeyError as e:
            logger.info(
                'NextEntityVisiting: incomplete page information'
                ' => we start a new visit [%s]', e,
            )
            index = 0
            page_info = None  # NB: means "first page" in FlowPaginator
        else:
            try:
                previous_index = int(index_str)
                page_info = json.loads(page_str)
            except (ValueError, json.JSONDecodeError) as e:
                raise BadRequest(str(e)) from e

            if not 0 <= previous_index < 2:
                raise BadRequest(
                    f'Index must be in [0, 1]: {previous_index}'
                )

            if not isinstance(page_info, dict):
                raise BadRequest(f'Page_info must be a dict: {page_info}')

            # IT'S HERE: we visit the next entity
            index = previous_index + 1

        return index, page_info

    def get_search_field_registry(self) -> search.ListViewSearchFieldRegistry:
        return self.search_field_registry

    def get_search_form_class(self) -> type[ListViewSearchForm]:
        return self.search_form_class

    def get_search_form(self, cells: Sequence[EntityCell]) -> ListViewSearchForm:
        form_cls = self.get_search_form_class()
        request = self.request
        form = form_cls(
            field_registry=self.get_search_field_registry(),
            cells=cells,
            user=request.user,
            data=request.GET,
        )

        form.full_clean()

        return form

    # NB: def get_ordering(self, *, model, cells): in mass export
    def get_sort_info(self, *,
                      model: type[CremeEntity],
                      cells: Iterable[EntityCell],
                      ) -> sorter.QuerySortInfo:
        sort = get_from_GET_or_404(self.request.GET, self.sort_arg)
        sort_asc, sort_cell_key = (False, sort[1:]) if sort.startswith('-') else (True, sort)

        return self.get_query_sorter().get(
            model=model,
            cells=cells,
            cell_key=sort_cell_key,
            order=Order(asc=sort_asc),
            # TODO: only if needed? (to always keep the same ordering than list-view)
            fast_mode=True,
        )

    def get_end_response(self, *,
                         callback_url: str,
                         header_filter: HeaderFilter,
                         sort_order: Order,
                         sort_cell_key: str,
                         entity_filter: EntityFilter | None = None,
                         search_form: ListViewSearchForm,
                         serialized_requested_q=None,
                         ) -> HttpResponse:
        lv = listview.EntitiesList
        params = {
            lv.sort_order_arg:       str(sort_order),
            lv.sort_cellkey_arg:     sort_cell_key,
            lv.header_filter_id_arg: header_filter.id,
            **search_form.filtered_data,
        }

        if entity_filter:
            params[lv.entity_filter_id_arg] = entity_filter.id

        if serialized_requested_q:
            params[lv.requested_q_arg] = serialized_requested_q

        return render(
            self.request,
            template_name=self.end_template_name,
            context={
                'title': _('The exploration is over'),
                'lv_url': f'{callback_url}?{urlencode(params, doseq=True)}',
            },
        )

    def get(self, request, *args, **kwargs):
        ct = self.get_ctype()
        model = ct.model_class()
        callback_url = self.get_callback_url()
        index, page_info = self.get_index_n_page_info()
        hf = self.get_header_filter()
        cells = self.get_cells(header_filter=hf)
        entities_qs = model.objects.filter(is_deleted=False)
        # use_distinct = False

        # ----
        efilter = self.get_entity_filter()

        if efilter is not None:
            entities_qs = efilter.filter(entities_qs)

        # ----
        serialized_internal_q = request.GET.get(self.internal_q_arg)
        if serialized_internal_q is not None:
            try:
                internal_q = QSerializer().loads(serialized_internal_q)
            except Exception as e:
                raise BadRequest(f'Invalid internal Q: {e}')

            entities_qs = entities_qs.filter(internal_q)
            # use_distinct = True  # todo: test + only if needed

        # TODO: factorise
        serialized_requested_q = request.GET.get(self.requested_q_arg)
        if serialized_requested_q is not None:
            try:
                requested_q = QSerializer().loads(serialized_requested_q)
            except Exception as e:
                raise BadRequest(f'Invalid requested Q: {e}')

            entities_qs = entities_qs.filter(requested_q)
            # use_distinct = True  # todo: test + only if needed

        # ----
        # Currently errors are silently ignored
        # TODO: ValidationError => "the header filter may have been modified"?
        search_form = self.get_search_form(cells=cells)
        search_q = search_form.search_q
        if search_q:
            try:
                entities_qs = entities_qs.filter(search_q)
            except Exception as e:
                # TODO: test
                logger.exception(
                    'Error when building the search queryset with Q=%s (%s).',
                    search_q, e,
                )
            # else:
            #     use_distinct = True  # todo: test + only if needed

        # ----
        entities_qs = EntityCredentials.filter(request.user, entities_qs)

        # TODO: <if use_distinct:>
        entities_qs = entities_qs.distinct()

        # ----
        sort_info = self.get_sort_info(model=model, cells=cells)
        ordering = sort_info.field_names

        # ----
        paginator = self.get_paginator(queryset=entities_qs, ordering=ordering)
        current_page = paginator.get_page(page_info)

        def build_end_response():
            return self.get_end_response(
                callback_url=callback_url,
                header_filter=hf,
                sort_cell_key=sort_info.main_cell_key or '',
                sort_order=sort_info.main_order,
                entity_filter=efilter,
                search_form=search_form,
                serialized_requested_q=serialized_requested_q,
            )

        if index < paginator.per_page:
            page = current_page
            fixed_index = index  # No need to fix the index (see below)
        else:
            # The entity from which the view has been called was the last of the
            # page; so the next entity is the first of the next page (if it exists).

            # No next page
            if not current_page.has_next():
                return build_end_response()

            # There's a next page; we reset the index to get the first entity
            # & take the next page.
            index = 0
            page = paginator.get_page(current_page.next_page_info())

            # BEWARE, the behaviour of FlowPaginator can cause a subtile issue:
            #  * If there is an even number of entities, entities are grouped
            #    in the same way whatever the type of page-info ('first', 'forward', 'last').
            #  * If there is an odd number of entities, when we retrieve the last
            #    entity, the page content is retrieved from the "forward" info of
            #    the previous entity (so the entity corresponds to <index == 0>
            #    in this new page). BUT the page type is now "last", and in the
            #    last page, there are the 2 (i.e. page-size) last entities, so
            #    the correct index should be 1.
            #    If we do not fix the index, the last entity will be visited twice.
            fixed_index = 1 if len(page.object_list) < paginator.per_page else 0

        try:
            entity = page.object_list[index]
        except IndexError:
            return build_end_response()

        # TODO: check length of the URI? (4096 limit in HTTP)
        uri_param = {
            self.detail_view.visitor_mode_arg: self.detail_view.visitor_cls(
                model=model,
                callback_url=callback_url,
                hfilter_id=hf.pk,
                sort=f'{sort_info.main_order.prefix}{sort_info.main_cell_key}'
                     if sort_info.main_cell_key else '',
                efilter_id=efilter.pk if efilter else None,
                internal_q=serialized_internal_q or '',
                requested_q=serialized_requested_q or '',
                search_dict=search_form.filtered_data if search_q else None,
                page_info=page.info(),
                index=fixed_index,
            ).to_json(),
        }
        return HttpResponseRedirect(
            f'{entity.get_absolute_url()}?{urlencode(uri_param)}'
        )


class SearchAndView(base.CheckedView):
    allowed_classes = CremeEntity
    value_arg = 'value'
    field_names_arg = 'fields'
    model_ids_arg = 'models'

    def build_q(self, *, model, value, field_names, fields_configs):
        query = Q()

        for field_name in field_names:
            try:
                field = model._meta.get_field(field_name)
            except FieldDoesNotExist:
                pass
            else:
                if fields_configs[model].is_field_hidden(field):
                    raise ConflictError(gettext('This field is hidden.'))

                query |= Q(**{field.name: value})

        return query

    def build_response(self, entity):
        return redirect(entity)

    def get_field_names(self):
        return get_from_GET_or_404(self.request.GET, self.field_names_arg).split(',')

    def get_model_ids(self):
        return get_from_GET_or_404(self.request.GET, self.model_ids_arg).split(',')

    def get_models(self):
        model_ids = self.get_model_ids()

        check_app = self.request.user.has_perm_to_access_or_die
        models = []
        get_ct = ContentType.objects.get_by_natural_key

        for model_id in model_ids:
            try:
                ct = get_ct(*model_id.split('-'))
            except (ContentType.DoesNotExist, TypeError) as e:
                raise Http404(f'This model does not exist: {model_id}') from e

            check_app(ct.app_label)

            model = ct.model_class()

            if self.is_model_allowed(model):
                models.append(model)

        if not models:
            raise Http404('No valid model')

        return models

    def get_value(self):
        value = get_from_GET_or_404(self.request.GET, self.value_arg)

        if not value:  # Avoid useless queries
            raise Http404('Void "value" arg')

        return value

    def get(self, request, *args, **kwargs):
        value = self.get_value()
        field_names = self.get_field_names()
        models = self.get_models()
        fconfigs = FieldsConfig.objects.get_for_models(models)
        user = request.user

        for model in models:
            query = self.build_q(
                model=model, value=value,
                field_names=field_names, fields_configs=fconfigs,
            )

            if query:  # Avoid useless query
                # TODO: what about entities with <is_deleted=True>?
                found = EntityCredentials.filter(user, model.objects.filter(query)).first()

                if found:
                    return self.build_response(found)

        raise Http404(gettext('No entity corresponding to your search was found.'))

    def is_model_allowed(self, model):
        return issubclass(model, self.allowed_classes)


# TODO: remove when bulk_update_registry has been rework to manage different
#       types of cells (e.g. RelationType => LINK)
def _bulk_has_perm(entity, user):  # NB: indeed 'entity' can be a simple model...
    try:
        return user.has_perm_to_change(entity)
    except TypeError as e:
        logger.critical(
            'Cannot resolve CHANGE permission for inner/bulk edition '
            '(original error: %s)', e,
        )

    return False


class InnerEdition(base.EntityCTypeRelatedMixin,
                   generic.CremeModelEditionPopup):
    # model = ...
    # form_class = ...
    pk_url_kwarg = 'id'
    cell_key_arg = 'cell'

    bulk_update_registry = bulk_update.bulk_update_registry

    def check_instance_permissions(self, instance, user):
        super().check_instance_permissions(instance=instance, user=user)

        if not _bulk_has_perm(instance, user):
            raise PermissionDenied(gettext('You are not allowed to edit this entity'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        cb_url = context['callback_url']
        if cb_url:
            context['help_message'] = format_html(
                '<a href="{url}">{label}</a>',
                url=f'{self.object.get_edit_absolute_url()}?callback_url={cb_url}',
                label=gettext('Full edition form'),
            )

        return context

    def get_form_class(self):
        model = self.object.__class__

        # TODO: always GET?
        cells, errors = CELLS_MAP.build_cells_from_keys(
            model=model, keys=self.request.GET.getlist(self.cell_key_arg),
        )
        if errors:
            raise Http404('A cell key is invalid')

        registry = self.bulk_update_registry
        try:
            return registry.build_form_class(model, cells)
        except registry.Error as e:
            raise Http404(str(e)) from e

    def get_queryset(self):
        return self.get_ctype().model_class()._default_manager.all()


class BulkUpdate(base.EntityCTypeRelatedMixin, generic.CremeEditionPopup):
    # form_class = ...  => generated dynamically
    title = _('Multiple update')

    cell_key_url_kwarg = 'cell_key'
    bulk_update_registry = bulk_update.bulk_update_registry

    results_template_name = 'creme_core/bulk-update-results.html'
    max_errors = 100

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        count = len(self.entity_ids)
        # TODO: select_label in model instead (e.g. gender issue)?
        context['help_message'] = ngettext(
            '{count} «{model}» has been selected.',
            '{count} «{model}» have been selected.',
            count
        ).format(
            count=count,
            model=smart_model_verbose_name(model=self.get_ctype().model_class(), count=count),
        )

        return context

    def get_form_class(self):
        model = self.get_ctype().model_class()
        registry = self.bulk_update_registry

        cell = None
        cell_key = self.kwargs.get(self.cell_key_url_kwarg)
        if cell_key:
            cell = CELLS_MAP.build_cell_from_key(
                model=model, key=self.kwargs.get(self.cell_key_url_kwarg),
            )
            if cell is None:
                raise Http404(f'The cell "{cell_key}" is invalid')

        config = registry.config(model)
        if config is None:
            raise Http404(f'The model "{model}" is not registered for bulk-update.')

        sort_key = collator.sort_key

        rfield_cells = sorted(
            (
                EntityCellRegularField.build(model, field.name)
                for field in config.regular_fields(exclude_unique=True)
            ),
            key=lambda cell: sort_key(cell.title),
        )
        cfield_cells = sorted(
            (EntityCellCustomField(cfield) for cfield in config.custom_fields),
            key=lambda cell: sort_key(cell.title),
        )

        if not rfield_cells and not cfield_cells:
            raise Http404(f'The model "{model}" has not inner-editable field.')

        if cell is None:
            cell = rfield_cells[0] if rfield_cells else cfield_cells[0]

        try:
            form_cls = registry.build_form_class(model, cells=[cell], exclude_unique=True)
        except registry.Error as e:
            raise Http404(str(e)) from e

        build_url = self._bulk_field_url
        choices = [(build_url(cell), cell.title) for cell in rfield_cells]
        if cfield_cells:
            choices.append((
                gettext('Custom fields'),
                [(build_url(cell), cell.title) for cell in cfield_cells]
            ))

        class BulkEditionForm(form_cls):
            # TODO: change field name (beware of JavaScript)
            # TODO: we could easily bulk-edit several fields with a multi-selector...
            _bulk_fieldname = ChoiceField(
                choices=choices,
                label=_('Field to update'),
                initial=self._bulk_field_url(cell),
                required=False,
            )

            # TODO: (management of '*' in field list is needed)
            # blocks = FieldBlockManager({
            #     'id': 'general', 'label': _('Field & value'), 'fields': ('_bulk_fieldname', '*'),
            # })

            field_order = ['_bulk_fieldname']  # NB: set the field as first one

            # TODO: call super()._post_clean only if instance.pk?
            # def _post_clean(this):

        return BulkEditionForm

    def _bulk_field_url(self, cell):
        # TODO: cell_key as GET argument?
        #       We could store the base URL + GET argument's name in HTML attributes,
        #       & choices values would be the cell keys.
        return reverse(
            'creme_core__bulk_update',
            kwargs={
                'ct_id': ContentType.objects.get_for_model(cell.model).id,
                'cell_key': cell.key,
            },
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        entities = self.entities
        kwargs['instances'] = entities

        if entities:
            # NB:
            #  - if we let an empty instance of <self.get_ctype().model_class()>
            #    as form.instance, the method clean() of this instance can raise
            #    an annoying ValidationError due to the emptiness (because only
            #    the fields of this form are filled).
            #  - if we build empty CremeEntity, we avoid this clean() method,
            #    but the TypeOverriders have to manage a special case in their
            #    method post_clean_instance()
            #  So we use entities[0]; this way can lead to get ValidationErrors
            #  about info which do not concern other entities (& so stop all the
            #  editions), but it seems to be the less annoying solution.
            kwargs['instance'] = entities[0]

        return kwargs

    def form_valid(self, form):
        # Here only an instance of our form bound to an empty instance has been
        # validated ; so we can still get ValidationErrors with our concrete
        # instances, but we do not stop the process when an error happens, we
        # just keep statistics about them.
        form_cls = type(form)
        user = form.user
        success_count = 0
        errors = LimitedList(max_size=self.max_errors)
        entities = self.entities

        for entity in entities:
            # TODO: files=request.FILES?
            instance_form = form_cls(
                user=user, instance=entity, instances=entities, data=self.request.POST,
            )

            if instance_form.is_valid():
                instance_form.save()
                success_count += 1
            else:
                errors.append((entity, instance_form.errors))

        initial_count = len(self.entity_ids)

        return render(
            self.request,
            template_name=self.results_template_name,
            context={
                'title': self.get_title(),
                # 'ctype': ContentType.objects.get_for_model(type(form.instance)), TODO?

                'initial_count': initial_count,
                'success_count': success_count,
                'forbidden_count': initial_count - success_count - len(errors),

                'errors': errors,
            },
        )

    @cached_property
    def entity_ids(self):
        if self.request.method == 'POST':
            return self.request.POST.getlist('entities', [])
        else:
            raw_ids = self.request.GET.get('entities')
            return raw_ids.split('.') if raw_ids else []

    @cached_property
    def entities(self):
        entity_ids = self.entity_ids

        # NB (#60): 'SELECT FOR UPDATE' in a query using an 'OUTER JOIN' and
        #    nullable ids will fail with postgresql (both 9.6 & 10.x).
        # TODO: This bug may be fixed in django>=2.0
        #       (see https://code.djangoproject.com/ticket/28010)
        # entities = self.get_queryset().select_for_update().filter(pk__in=entity_ids)
        qs = self.get_queryset()
        entities = qs.filter(pk__in=entity_ids)

        filtered = EntityCredentials.filter(
            self.request.user, queryset=entities, perm=EntityCredentials.CHANGE,
        )

        # NB: Move 'SELECT FOR UPDATE' here for now.
        #     It could cause performance issues with a large amount of
        #     selected entities, but this never happens with common use cases.
        # return filtered
        if self.request.method == 'POST':
            if not filtered:
                raise PermissionDenied(_('You are not allowed to edit these entities'))

            # TODO: remove .select_for_update() here & perform it in form_valid()
            #       on chunks of the global query (+ separated transaction?)
            return qs.select_for_update().filter(pk__in=filtered)
        else:
            return qs.filter(pk__in=filtered)

    def get_queryset(self):
        return self.get_ctype().model_class()._default_manager.all()


class MergeFormMixin:
    merge_form_registry = merge_form_registry

    def get_merge_form_class(self, model):
        form_cls = merge_form_factory(
            model=model,
            merge_form_registry=self.get_merge_form_registry(),
        )

        if form_cls is None:
            raise ConflictError('This type of entity cannot be merged')

        return form_cls

    def get_merge_form_registry(self):
        return self.merge_form_registry


class EntitiesToMergeSelection(base.EntityRelatedMixin,
                               MergeFormMixin,
                               listview.BaseEntitiesListPopup):
    """List-view to select a second entity to merge with a given entity.

    The second entity must have the same type as the first one, and cannot
    have the same ID.
    """
    mode = listview.SelectionMode.SINGLE
    entity1_id_arg = 'id1'

    reload_url_name = 'creme_core__select_entity_for_merge'

    def check_related_entity_permissions(self, entity, user):
        self.get_merge_form_class(type(entity))  # NB: can raise exception

        user.has_perm_to_view_or_die(entity)
        super().check_related_entity_permissions(entity=entity, user=user)

    def get_related_entity_id(self):
        return get_from_GET_or_404(self.request.GET, self.entity1_id_arg, cast=int)

    def get_reload_url(self):
        return super().get_reload_url() + (
            f'?{self.entity1_id_arg}={self.get_related_entity_id()}'
        )

    @property
    def model(self):
        return type(self.get_related_entity())

    def get_internal_q(self):
        return ~Q(pk=self.get_related_entity().id)


class Merge(MergeFormMixin, generic.CremeFormView):
    template_name = 'creme_core/forms/merge.html'
    title = _('Merge «{entity1}» with «{entity2}»')
    submit_label = _('Merge')

    entity1_id_arg = 'id1'
    entity2_id_arg = 'id2'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entity1 = self.entity2 = None

    def check_entity1_permissions(self, entity1, user):
        user.has_perm_to_view_or_die(entity1)
        user.has_perm_to_change_or_die(entity1)

    def check_entity2_permissions(self, entity2, user):
        user.has_perm_to_view_or_die(entity2)
        user.has_perm_to_delete_or_die(entity2)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['help_message'] = _(
            'You are going to merge two entities into a new one.\n'
            'Choose which information you want the old entities give to the new entity.\n'
            'The relationships, the properties and the other links with any of '
            'old entities will be automatically available in the new merged entity.'
        )

        return context

    # TODO: use POST for POST request ?
    def get_entity1_id(self, request):
        return get_from_GET_or_404(request.GET, self.entity1_id_arg, cast=int)

    def get_entity2_id(self, request):
        return get_from_GET_or_404(request.GET, self.entity2_id_arg, cast=int)

    def get_entities(self):
        if self.entity1 is None:
            request = self.request

            entity1_id = self.get_entity1_id(request)
            entity2_id = self.get_entity2_id(request)

            if entity1_id == entity2_id:
                raise ConflictError('You can not merge an entity with itself.')

            entities = CremeEntity.objects.all()

            if request.method == 'POST':
                entities = entities.select_for_update()

            entities_per_id = entities.in_bulk((entity1_id, entity2_id))

            try:
                entity1 = entities_per_id[entity1_id]
                entity2 = entities_per_id[entity2_id]
            except KeyError as e:
                raise Http404(gettext(
                    'One entity you want to merge does not exist anymore '
                    '(have you already performed the merge?)'
                )) from e

            if entity1.entity_type_id != entity2.entity_type_id:
                raise ConflictError('You can not merge entities of different types.')

            user = request.user
            self.check_entity1_permissions(entity1=entity1, user=user)
            self.check_entity2_permissions(entity2=entity2, user=user)

            # TODO: try to swap 1 & 2

            CremeEntity.populate_real_entities([entity1, entity2])
            self.entity1 = entity1.get_real_entity()
            self.entity2 = entity2.get_real_entity()

        return self.entity1, self.entity2

    def get_form(self, *args, **kwargs):
        try:
            return super().get_form(*args, **kwargs)
        except MergeEntitiesBaseForm.CanNotMergeError as e:
            raise ConflictError(e) from e

    def get_form_class(self):
        return self.get_merge_form_class(type(self.get_entities()[0]))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['entity1'], kwargs['entity2'] = self.get_entities()

        return kwargs

    def form_valid(self, form):
        form.save()

        # NB: we get the entity1 attribute (i.e. not the attribute),
        #     because the entities can be swapped in the form (but form.entity1
        #     is always kept & form.entity2 deleted).
        return redirect(form.entity1)

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['entity2'], data['entity1'] = self.get_entities()

        return data


class Trash(generic.BricksView):
    template_name = 'creme_core/trash.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ENTITIES_DELETION_ALLOWED'] = settings.ENTITIES_DELETION_ALLOWED

        return context


# TODO: disable the button "Empty the trash" while the job is active
class TrashCleaning(generic.base.TitleMixin, generic.CheckedView):
    title = _('Empty the trash')
    job_type = trash_cleaner_type
    command_model = TrashCleaningCommand
    conflict_msg = _('A job is already cleaning the trash.')
    confirmation_template_name = 'creme_core/forms/confirmation.html'
    job_template_name = 'creme_core/job/trash-cleaning-popup.html'

    def dispatch(self, request, *args, **kwargs):
        if not settings.ENTITIES_DELETION_ALLOWED:
            raise ConflictError(
                gettext('The definitive deletion has been disabled by the administrator.')
            )

        return super().dispatch(request, *args, **kwargs)

    # TODO: add a new brick action type (with confirmation + display of a result form)
    #       and remove these get() method ??
    def get(self, request, *args, **kwargs):
        return render(
            request=request,
            template_name=self.confirmation_template_name,
            context={
                'title': self.get_title(),
                'message': gettext(
                    'Are you sure you want to delete definitely '
                    'all the entities in the trash?'
                ),
            },
        )

    def post(self, request, *args, **kwargs):
        user = request.user
        cmd_model = self.command_model

        cmd = cmd_model.objects.filter(user=user).first()
        if cmd is not None:
            if cmd.job.status == Job.STATUS_OK:
                with atomic():
                    # NB: we do not recycle the instances :
                    #    - of job, to start the job correctly
                    #    - of command, to avoid race conditions
                    cmd.job.delete()
            else:
                raise ConflictError(self.conflict_msg)

        try:
            # TODO: workflow?
            with atomic():
                job = Job.objects.create(type_id=self.job_type.id, user=user)
                cmd_model.objects.create(user=user, job=job)
        except IntegrityError as e:  # see TrashCleaningCommand uniqueness
            raise ConflictError(self.conflict_msg) from e

        return render(
            request=self.request,
            template_name=self.job_template_name,
            context={'job': job},
        )


class TrashCleanerEnd(generic.CheckedView):
    job_type = trash_cleaner_type
    job_id_url_kwarg = 'job_id'

    def post(self, request, *args, **kwargs):
        job = get_object_or_404(
            Job,
            id=kwargs[self.job_id_url_kwarg],
            type_id=self.job_type.id,
        )

        if job.user != request.user:
            raise PermissionDenied('You can only terminate your cleaner jobs.')

        if not job.is_finished:
            raise ConflictError('A non finished job cannot be terminated.')

        if EntityJobResult.objects.filter(job=job).exists():
            if is_ajax(request):
                return HttpResponse(job.get_absolute_url(), content_type='text/plain')

            return redirect(job)

        job.delete()

        return HttpResponse()


class EntityRestoration(base.EntityRelatedMixin, base.CheckedView):
    entity_select_for_update = True

    def build_related_entity_queryset(self, model):
        return super().build_related_entity_queryset(model=model).filter(is_deleted=True)

    # TODO: should the deletors registry manage the perm to restore too?
    def check_related_entity_permissions(self, entity, user):
        if not entity.is_deleted:
            raise ConflictError('Can not restore an entity which is not in the trash')

        user.has_perm_to_delete_or_die(entity)

    @atomic
    @method_decorator(workflow_engine)
    def post(self, request, *args, **kwargs):
        entity = self.get_related_entity()
        entity.restore()

        return HttpResponse() if is_ajax(request) else redirect(entity)


class EntityDeletionMixin(generic.CremeDeletionMixin):
    deletor_registry = entity_deletor_registry

    def get_deletor_for_entity(self, entity: CremeEntity) -> EntityDeletor:
        """Gets the deletor for an entity (based of its type).
        @raise ConflictError if this tpe has not registered deletor.
        """
        deletor = self.deletor = self.deletor_registry.get(model=type(entity))
        if deletor is None:
            raise ConflictError(gettext(
                'This type of entity does not use the generic deletion view.'
            ))

        return deletor

    def delete_entity(self, *,
                      entity: CremeEntity, user: CremeUser, deletor: EntityDeletor,
                      ) -> None:
        """Performs the deletion of a CremeEntity instance.
        @raise ConflictError.
        """
        try:
            deletor.perform(entity=entity, user=user)
        except SpecificProtectedError as e:
            raise ConflictError(
                gettext('This entity can not be deleted ({reason})').format(reason=e.args[0]),
            ) from e
        except ProtectedError as e:
            raise ConflictError(
                format_html(
                    '<span>{message}</span>{dependencies}',
                    message=gettext(
                        'This entity can not be deleted because of its links '
                        'with other entities:'
                    ),
                    dependencies=self.dependencies_to_html(
                        instance=entity, dependencies=e.args[1], user=user,
                    ),
                )
            ) from e
        except Exception as e:
            logger.exception('Error when trying delete "%s" (id=%s)', entity, entity.id)
            raise ConflictError(
                gettext('The deletion caused an unexpected error [{error}].').format(error=e),
            ) from e


class EntitiesDeletion(EntityDeletionMixin, base.CheckedView):
    "Delete several CremeEntities, with an Ajax call (POST method)."

    def get_entity_ids(self) -> list[int]:
        try:
            entity_ids = [
                int(e_id)
                for e_id in get_from_POST_or_404(self.request.POST, 'ids').split(',')
                if e_id
            ]
        except ValueError as e:
            raise BadRequestError(f'Bad POST argument ({e})') from e

        if not entity_ids:
            raise BadRequestError('Empty "ids" argument.')

        logger.debug('delete_entities() -> ids: %s ', entity_ids)

        return entity_ids

    def post(self, request, *args, **kwargs):
        entity_ids = self.get_entity_ids()
        user = request.user
        errors = defaultdict(list)

        # TODO: test workflow
        with atomic(), run_workflow_engine(user=user):
            entities = [*CremeEntity.objects.select_for_update().filter(pk__in=entity_ids)]

            len_diff = len(entity_ids) - len(entities)
            if len_diff:
                errors[404].append(
                    ngettext(
                        "{count} entity doesn't exist or has been removed.",
                        "{count} entities don't exist or have been removed.",
                        len_diff
                    ).format(count=len_diff)
                )

            CremeEntity.populate_real_entities(entities)

            error_msg = gettext('{entity}: {error}')

            def format_error(entity, message):
                return error_msg.format(entity=escape(entity.allowed_str(user)), error=message)

            for entity in entities:
                real_entity = entity.get_real_entity()

                try:
                    deletor = self.get_deletor_for_entity(entity=real_entity)
                    deletor.check_permissions(entity=real_entity, user=user)
                    self.delete_entity(entity=real_entity, user=user, deletor=deletor)
                except PermissionDenied as e:
                    errors[403].append(format_error(entity=real_entity, message=e.args[0]))
                except ConflictError as e:
                    errors[409].append(format_error(entity=real_entity, message=e.args[0]))

        if not errors:
            status = 200
            message = gettext('Operation successfully completed')
            content_type = None
        else:
            status = min(errors)
            message = json_encode({
                'count': len(entity_ids),
                'errors': [msg for error_messages in errors.values() for msg in error_messages],
            })
            content_type = 'application/json'

        return HttpResponse(message, content_type=content_type, status=status)


class EntityDeletion(EntityDeletionMixin,
                     base.CallbackMixin,
                     base.EntityRelatedMixin,
                     generic.CremeDeletion):
    entity_select_for_update = True
    dependencies_limit = 10

    def check_related_entity_permissions(self, entity, user):
        # self.check_entity_for_deletion(entity, user)
        pass  # The permission are delegated to the deletor (& it needs the entity).

    # TODO: should the deletor be used to compute the URL?
    def get_url_for_entity(self):
        entity = self.get_related_entity()

        if hasattr(entity, 'get_lv_absolute_url'):
            return entity.get_lv_absolute_url()

        if hasattr(entity, 'get_related_entity'):
            return entity.get_related_entity().get_absolute_url()

        return reverse('creme_core__home')

    def get_ajax_success_url(self):
        # NB: we redirect because this view can be used from the detail-view
        #     (if it's a definitive deletion, we MUST go to a new page anyway)
        # Hint: example of use in template
        #   <div class='bar-action'>
        #       {% brick_bar_button
        #          action='creme_core-detailview-delete'
        #          label=_('Delete')
        #          url=object.get_delete_absolute_url
        #          __callback_url='creme_core__my_page'|url
        #          icon='delete'
        #          confirm=_('Are you sure?')
        #          enabled=True
        #        %}
        #   </div>
        return self.get_callback_url() or self.get_url_for_entity()

    def get_success_url(self):
        return self.get_callback_url() or self.get_url_for_entity()

    def perform_deletion(self, request):
        user = request.user

        # TODO: test workflow
        with atomic(), run_workflow_engine(user=user):
            # When the flag 'entity_select_for_update' is enabled the related entity query
            # will need to be within a transaction.
            entity = self.get_related_entity()
            deletor = self.get_deletor_for_entity(entity)
            deletor.check_permissions(entity=entity, user=user)

            self.delete_entity(entity=entity, user=user, deletor=deletor)


class RelatedToEntityDeletion(generic.base.ContentTypeRelatedMixin,
                              generic.CremeModelDeletion):
    def check_instance_permissions(self, instance, user):
        user.has_perm_to_access_or_die(instance._meta.app_label)

        try:
            entity = instance.get_related_entity()
        except AttributeError:
            raise ConflictError('This is not an auxiliary model.')

        user.has_perm_to_change_or_die(entity)

    @property
    def model(self):
        model = self.get_ctype().model_class()
        if issubclass(model, CremeEntity):
            raise ConflictError('This view can not delete CremeEntities.')

        return model

    def get_success_url(self):
        return self.object.get_related_entity().get_absolute_url()


class SuperusersRestriction(base.CheckedView):
    permissions = SUPERUSER_PERM
    enable_sandbox_arg = 'set'
    entity_id_arg = 'id'
    sandbox_uuid = constants.UUID_SANDBOX_SUPERUSERS

    def get_enable_sandbox(self):
        return get_from_POST_or_404(
            self.request.POST,
            key=self.enable_sandbox_arg,
            cast=bool_from_str_extended,
            default='1',
        )

    def get_entity_id(self):
        return get_from_POST_or_404(
            self.request.POST,
            key=self.entity_id_arg,
            cast=int,
        )

    def get_entity(self):
        return get_object_or_404(
            CremeEntity.objects.select_for_update(),
            id=self.get_entity_id(),
        )

    @atomic
    @method_decorator(workflow_engine)
    def post(self, request, *args, **kwargs):
        set_sandbox = self.get_enable_sandbox()
        entity = self.get_entity()

        if set_sandbox:
            if entity.sandbox_id:
                raise ConflictError('This entity is already in a sandbox.')

            entity.sandbox = Sandbox.objects.get(uuid=self.sandbox_uuid)
            entity.save()
        else:
            sandbox = entity.sandbox

            if not sandbox or str(sandbox.uuid) != self.sandbox_uuid:
                raise ConflictError(
                    'This entity is not in the "Restricted to superusers" sandbox.'
                )

            entity.sandbox = None
            entity.save()

        return HttpResponse()


# TODO: only GET ?
class EntitiesListPopup(base.EntityCTypeRelatedMixin, listview.BaseEntitiesListPopup):
    """ Displays a list-view selector in an inner popup, to select one or more
    entities of a given type.

    New GET/POST parameter:
      - 'ct_id': the ContentType's ID of the model we want. Required.
    """
    def get_ctype_id(self):
        request = self.request

        return (
            get_from_POST_or_404(request.POST, self.ctype_id_url_kwarg)
            if request.method == 'POST' else
            get_from_GET_or_404(request.GET, self.ctype_id_url_kwarg)
        )

    @property
    def model(self):
        return self.get_ctype().model_class()

    def get_state_id(self):
        return f'{self.get_ctype().id}#{super().get_state_id()}'
