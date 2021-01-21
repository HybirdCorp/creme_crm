# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.encoding import smart_str

from ..backends import export_backend_registry
from ..core import sorter
from ..core.paginator import FlowPaginator
from ..forms.listview import ListViewSearchForm
from ..gui.listview import search_field_registry
from ..models import EntityCredentials, EntityFilter, HeaderFilter
from ..models.history import _HLTEntityExport
from ..utils import bool_from_str_extended, get_from_GET_or_404
from ..utils.meta import Order
from ..utils.queries import QSerializer
from .generic import base

logger = logging.getLogger(__name__)


# TODO: stream response ??
# TODO: factorise with generic.listview.EntitiesList ?
class MassExport(base.EntityCTypeRelatedMixin, base.CheckedView):
    ct_id_arg = 'ct_id'
    doc_type_arg = 'type'
    header_only_arg = 'header'
    headerfilter_id_arg = 'hfilter'
    entityfilter_id_arg = 'efilter'
    sort_cellkey_arg = 'sort_key'
    sort_order_arg = 'sort_order'
    extra_q_arg = 'extra_q'

    page_size = 1024

    cell_sorter_registry = sorter.cell_sorter_registry
    query_sorter_class   = sorter.QuerySorter

    search_field_registry = search_field_registry
    search_form_class     = ListViewSearchForm

    def check_related_ctype(self, ctype):
        super().check_related_ctype(ctype=ctype)

        self.request.user.has_perm_to_export_or_die(ctype.model_class())

    def get_backend_class(self):
        doc_type = get_from_GET_or_404(self.request.GET, self.doc_type_arg)

        backend_class = export_backend_registry.get_backend_class(doc_type)
        if backend_class is None:
            raise Http404(f'No such exporter for extension "{doc_type}"')

        return backend_class

    def get_cells(self, header_filter):
        return header_filter.filtered_cells

    def get_ctype_id(self):
        return get_from_GET_or_404(self.request.GET, self.ct_id_arg, cast=int)

    def get_entity_filter_id(self):
        return self.request.GET.get(self.entityfilter_id_arg)

    def get_entity_filter(self):
        efilter_id = self.get_entity_filter_id()

        return get_object_or_404(EntityFilter, id=efilter_id) if efilter_id else None

    def get_header_filter_id(self):
        return get_from_GET_or_404(self.request.GET, self.headerfilter_id_arg)

    def get_header_filter(self):
        return get_object_or_404(
            HeaderFilter.objects
                        .filter_by_user(self.request.user)
                        .filter(entity_type=self.get_ctype()),
            id=self.get_header_filter_id(),
        )

    def get_header_only(self):
        return get_from_GET_or_404(
            self.request.GET,
            key=self.header_only_arg,
            cast=bool_from_str_extended,
            default='0',
        )

    def get_paginator(self, *, queryset, ordering):
        return FlowPaginator(
            queryset=queryset.order_by(*ordering),
            key=ordering[0],
            per_page=self.page_size,
        )

    def get_search_field_registry(self):
        return self.search_field_registry

    def get_search_form_class(self):
        return self.search_form_class

    def get_search_form(self, cells):
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

    def get_cell_sorter_registry(self):
        return self.cell_sorter_registry

    def get_query_sorter_class(self):
        return self.query_sorter_class

    def get_query_sorter(self):
        cls = self.get_query_sorter_class()

        return cls(self.get_cell_sorter_registry())

    def get_ordering(self, *, model, cells):
        get = self.request.GET.get
        sort_info = self.get_query_sorter().get(
            model=model,
            cells=cells,
            cell_key=get(self.sort_cellkey_arg),
            order=Order.from_string(get(self.sort_order_arg), required=False),
        )

        return sort_info.field_names

    def get(self, request, *args, **kwargs):
        user = request.user

        header_only = self.get_header_only()
        backend_cls = self.get_backend_class()
        ct = self.get_ctype()
        model = ct.model_class()
        hf = self.get_header_filter()

        cells = self.get_cells(header_filter=hf)

        writer = backend_cls()
        writerow = writer.writerow
        # Doesn't accept generator expression... ;(
        writerow([smart_str(cell.title) for cell in cells])

        if not header_only:
            ordering = self.get_ordering(model=model, cells=cells)

            entities_qs = model.objects.filter(is_deleted=False)
            use_distinct = False

            # ----
            efilter = self.get_entity_filter()
            if efilter is not None:
                entities_qs = efilter.filter(entities_qs)

            # ----
            extra_q = request.GET.get(self.extra_q_arg)
            if extra_q is not None:
                entities_qs = entities_qs.filter(QSerializer().loads(extra_q))
                use_distinct = True  # TODO: test + only if needed

            # ----
            search_form = self.get_search_form(cells=cells)
            search_q = search_form.search_q
            if search_q:
                try:
                    entities_qs = entities_qs.filter(search_q)
                except Exception as e:
                    logger.exception(
                        'Error when building the search queryset with Q=%s (%s).',
                        search_q, e,
                    )
                else:
                    use_distinct = True  # TODO: test + only if needed

            # ----
            entities_qs = EntityCredentials.filter(user, entities_qs)

            if use_distinct:
                entities_qs = entities_qs.distinct()

            paginator = self.get_paginator(queryset=entities_qs, ordering=ordering)

            total_count = 0

            for entities_page in paginator.pages():
                entities = entities_page.object_list

                hf.populate_entities(entities, user)  # Optimisation time !!!

                for entity in entities:
                    total_count += 1
                    line = []

                    for cell in cells:
                        try:
                            res = cell.render_csv(entity, user)
                        except Exception as e:
                            logger.debug('Exception in CSV export: %s', e)
                            res = ''

                        line.append(smart_str(res) if res else '')

                    writerow(line)

            _HLTEntityExport.create_line(
                ctype=ct, user=user, count=total_count, hfilter=hf, efilter=efilter,
            )

        writer.save(ct.model, user)

        return writer.response
