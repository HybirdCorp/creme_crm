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

from django.shortcuts import get_object_or_404

from creme.creme_core.models import CremeEntity
from creme.creme_core.views.generic import add_model_with_popup


def generic_add_related(request, target_id, form, title, submit_label, status_id=None):
    target = get_object_or_404(CremeEntity, pk=target_id).get_real_entity()
    request.user.has_perm_to_change_or_die(target)

    initial = {'target': target}

    if status_id:
        initial['status'] = status_id

    return add_model_with_popup(request, form, title=title % target,
                                initial=initial, submit_label=submit_label,
                               )
