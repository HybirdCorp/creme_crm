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

import logging

from django.http import Http404
from django.utils.encoding import smart_str
from django.shortcuts import get_object_or_404

from ..backends import export_backend_registry
from ..core.paginator import FlowPaginator
from ..forms.listview import ListViewSearchForm
from ..gui.listview import ListViewState, search_field_registry
from ..models import EntityFilter, EntityCredentials, HeaderFilter
from ..models.history import _HLTEntityExport
from ..utils import get_from_GET_or_404, bool_from_str_extended
from ..utils.queries import QSerializer

from .generic import base

logger = logging.getLogger(__name__)


# TODO: stream response ??
# TODO: factorise with generic.listview.EntitiesList ?
# TODO: do not use ListViewState any more => only GET arguments ( + remove 'list_url' arg)
class MassExport(base.EntityCTypeRelatedMixin, base.CheckedView):
    ct_id_arg = 'ct_id'
    doc_type_arg = 'type'
    header_only_arg = 'header'
    headerfilter_id_arg = 'hfilter'
    entityfilter_id_arg = 'efilter'

    page_size = 1024

    search_field_registry = search_field_registry
    search_form_class     = ListViewSearchForm

    def check_related_ctype(self, ctype):
        super().check_related_ctype(ctype=ctype)

        self.request.user.has_perm_to_export_or_die(ctype.model_class())

    def get_backend(self):
        doc_type = get_from_GET_or_404(self.request.GET, self.doc_type_arg)

        backend = export_backend_registry.get_backend(doc_type)
        if backend is None:
            raise Http404('No such exporter for extension "{}"'.format(doc_type))

        return backend

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
            HeaderFilter.get_for_user(user=self.request.user,
                                      content_type=self.get_ctype(),
                                     ),
            id=self.get_header_filter_id(),
        )

    def get_header_only(self):
        return get_from_GET_or_404(self.request.GET,
                                   key=self.header_only_arg,
                                   cast=bool_from_str_extended,
                                   default='0',
                                  )

    def get_paginator(self, *, queryset, ordering):
        return FlowPaginator(queryset=queryset.order_by(*ordering),
                             key=ordering[0],
                             per_page=self.page_size,
                            )

    def get_search_field_registry(self):
        return self.search_field_registry

    def get_search_form_class(self):
        return self.search_form_class

    def get_search_form(self, cells, state):
        form_cls = self.get_search_form_class()
        form = form_cls(
            field_registry=self.get_search_field_registry(),
            cells=cells,
            user=self.request.user,
            data=state.search,
        )

        form.full_clean()

        return form

    def get(self, request, *args, **kwargs):
        GET = request.GET
        user = request.user

        header_only = self.get_header_only()
        backend = self.get_backend()
        ct = self.get_ctype()
        model = ct.model_class()
        hf = self.get_header_filter()

        # TODO: is it possible that session doesn't content the state (eg: url linked and open directly)
        #   => now yes, the GET request doesn't create or update session state.
        current_lvs = ListViewState.get_or_create_state(request, url=request.GET['list_url'])

        cells = self.get_cells(header_filter=hf)

        writer = backend()
        writerow = writer.writerow
        writerow([smart_str(cell.title) for cell in cells])  # Doesn't accept generator expression... ;(

        if not header_only:
            ordering = current_lvs.set_sort(model, cells,
                                            current_lvs.sort_field,
                                            current_lvs.sort_order,
                                           )

            entities_qs = model.objects.filter(is_deleted=False)
            use_distinct = False

            # ----
            efilter = self.get_entity_filter()
            if efilter is not None:
                entities_qs = efilter.filter(entities_qs)

            # ----
            extra_q = GET.get('extra_q')
            if extra_q is not None:
                entities_qs = entities_qs.filter(QSerializer().loads(extra_q))
                use_distinct = True  # TODO: test + only if needed

            # ----
            search_form = self.get_search_form(cells=cells, state=current_lvs)
            search_q = search_form.search_q
            if search_q:
                try:
                    entities_qs = entities_qs.filter(search_q)
                except Exception as e:
                    logger.exception('Error when building the search queryset with Q=%s (%s).', search_q, e)
                else:
                    use_distinct = True  # TODO: test + only if needed

            # ----
            entities_qs = EntityCredentials.filter(user, entities_qs)

            if use_distinct:
                entities_qs = entities_qs.distinct()

            paginator = self.get_paginator(queryset=entities_qs,
                                           ordering=ordering,
                                          )

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

            _HLTEntityExport.create_line(ctype=ct, user=user, count=total_count, hfilter=hf, efilter=efilter)

        writer.save(ct.model)

        return writer.response
