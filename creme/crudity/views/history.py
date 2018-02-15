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

# import warnings

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import render

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.utils import get_ct_or_404, jsonify
from creme.creme_core.views.bricks import bricks_render_info, get_brick_ids_or_404  # build_context

from .. import registry
from ..bricks import CrudityHistoryBrick


@login_required
@permission_required('crudity')
def history(request):
    get_ct = ContentType.objects.get_for_model
    bricks = [CrudityHistoryBrick(get_ct(backend.model))
                  for backend in registry.crudity_registry.get_backends()
                      if backend.model
             ]

    return render(request, 'crudity/history.html',
                  {# 'blocks':            bricks,
                   'bricks':            bricks,
                   'bricks_reload_url': reverse('crudity__reload_history_bricks'),
                  }
                 )


# @jsonify
# @login_required
# @permission_required('crudity')
# def reload(request, ct_id):
#     warnings.warn('crudity.views.history.reload() is deprecated ; '
#                   'use crudity.views.history.reload_bricks() instead.',
#                   DeprecationWarning
#                  )
#
#     brick = CrudityHistoryBrick(get_ct_or_404(ct_id))
#     return [(brick.id_, brick.detailview_display(build_context(request)))]


@login_required
@permission_required('crudity')
@jsonify
def reload_bricks(request):
    brick_ids = get_brick_ids_or_404(request)
    bricks = []
    models = {backend.model for backend in registry.crudity_registry.get_backends() if backend.model}
    prefix = 'block_crudity-'

    for brick_id in brick_ids:
        if not brick_id.startswith(prefix):
            raise Http404('Invalid brick ID (bad prefix): ' + brick_id)

        ct = get_ct_or_404(brick_id[len(prefix):])

        if ct.model_class() in models:
            bricks.append(CrudityHistoryBrick(ct))

    return bricks_render_info(request, bricks=bricks)
