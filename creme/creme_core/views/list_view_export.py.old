# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from ..auth.decorators import login_required
from ..backends import export_backend_registry
from ..core.paginator import FlowPaginator
from ..gui.listview import ListViewState
from ..models import EntityFilter, EntityCredentials
from ..models.header_filter import HeaderFilterList
from ..models.history import _HLTEntityExport
from ..utils import get_ct_or_404, get_from_GET_or_404, bool_from_str_extended
from ..utils.queries import QSerializer


logger = logging.getLogger(__name__)


# TODO: stream response ??
# TODO: factorise with list_view()
# TODO: do not use ListViewState any more => only GET arguments ( + remove 'list_url' arg)
@login_required
def dl_listview(request):
    """ Download the content of a list-view.

    GET arguments are:
      - 'ct_id': the ContentType ID of the model we want. Required (if not given if the URL -- which is deprecated).
      - 'type': the type of file (see export_backend_registry).
      - 'header': True means we download only a simple header file (to manually fill it).
                  Value must be in 0/1/false/true. Optional; default value is '0' (false).
      - 'list_url': the URL of the downloaded list-view (in order to retrieve HeaderFilter/EntityFilter/search).
    """
    GET = request.GET
    ct_id = get_from_GET_or_404(GET, 'ct_id', cast=int)
    doc_type = get_from_GET_or_404(GET, 'type')
    header_only = get_from_GET_or_404(GET, 'header', cast=bool_from_str_extended, default='0')
    hf_id = get_from_GET_or_404(GET, 'hfilter')

    backend = export_backend_registry.get_backend(doc_type)
    if backend is None:
        raise Http404('No such exporter for extension "{}"'.format(doc_type))

    ct    = get_ct_or_404(ct_id)
    model = ct.model_class()
    user  = request.user
    url   = request.GET['list_url']

    user.has_perm_to_export_or_die(model)

    hf = HeaderFilterList(ct, user).select_by_id(hf_id)
    if hf is None:
        raise Http404('Invalid header filter "{}"'.format(hf))

    # TODO: is it possible that session doesn't content the state (eg: url linked and open directly)
    #   => now yes, the GET request doesn't create or update session state.
    current_lvs = ListViewState.get_or_create_state(request, url=url)

    cells = hf.filtered_cells

    writer = backend()
    writerow = writer.writerow
    writerow([smart_str(cell.title) for cell in cells])  # Doesn't accept generator expression... ;(

    if not header_only:
        current_lvs.handle_research(request.GET, cells, merge=True)
        ordering = current_lvs.set_sort(model, cells,
                                        current_lvs.sort_field,
                                        current_lvs.sort_order,
                                       )

        entities_qs = model.objects.filter(is_deleted=False)
        use_distinct = False

        efilter_id = current_lvs.entity_filter_id
        efilter = None
        if efilter_id:
            efilter = EntityFilter.objects.get(pk=efilter_id)
            entities_qs = efilter.filter(entities_qs)

        extra_q = GET.get('extra_q')
        if extra_q is not None:
            entities_qs = entities_qs.filter(QSerializer().loads(extra_q))
            use_distinct = True  # TODO: test + only if needed

        lv_state_q = current_lvs.get_q_with_research(model, cells)
        if lv_state_q:
            entities_qs = entities_qs.filter(lv_state_q)
            use_distinct = True  # TODO: test + only if needed

        entities_qs = EntityCredentials.filter(user, entities_qs)

        if use_distinct:
            entities_qs = entities_qs.distinct()

        paginator = FlowPaginator(queryset=entities_qs.order_by(*ordering),
                                  key=ordering[0], per_page=1024,
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
