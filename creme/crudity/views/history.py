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

from django.contrib.contenttypes.models import ContentType
from django.http import Http404

from creme.creme_core.utils.content_type import get_ctype_or_404
from creme.creme_core.views.bricks import BricksReloading
from creme.creme_core.views.generic import BricksView

from .. import registry
from ..bricks import CrudityHistoryBrick


class History(BricksView):
    template_name = 'crudity/history.html'
    permissions = 'crudity'
    bricks_reload_url_name = 'crudity__reload_history_bricks'

    def get_bricks(self):
        get_ct = ContentType.objects.get_for_model

        return [
            CrudityHistoryBrick(get_ct(backend.model))
            for backend in registry.crudity_registry.get_backends()
            if backend.model
        ]


class HistoryBricksReloading(BricksReloading):
    check_bricks_permission = False
    permissions = 'crudity'

    def get_bricks(self):
        bricks = []
        models = {
            backend.model
            for backend in registry.crudity_registry.get_backends()
            if backend.model
        }
        prefix = 'block_crudity-'

        for brick_id in self.get_brick_ids():
            if not brick_id.startswith(prefix):
                raise Http404('Invalid brick ID (bad prefix): ' + brick_id)

            ct = get_ctype_or_404(brick_id[len(prefix):])

            if ct.model_class() in models:
                bricks.append(CrudityHistoryBrick(ct))

        return bricks
