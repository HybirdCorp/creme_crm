# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.shortcuts import get_object_or_404, render

from creme.creme_core.models import CremeEntity
from creme.creme_core.gui.last_viewed import LastViewedItem


#TODO: remove 'path' arg (use get_edit_absolute_url() etc...) ??
def view_entity(request, object_id, model, path,
                template='creme_core/generics/view_entity.html',
                extra_template_dict=None):
    entity = get_object_or_404(model, pk=object_id)
    #entity = get_object_or_404(model.objects.even_deleted(), pk=object_id)
    entity.can_view_or_die(request.user)

    LastViewedItem(request, entity)

    template_dict = {'object': entity, 'path': path}
    if extra_template_dict is not None:
        template_dict.update(extra_template_dict)

    return render(request, template, template_dict)

def view_real_entity(request, object_id, path, template='creme_core/generics/view_entity.html'):
    entity = get_object_or_404(CremeEntity, pk=object_id).get_real_entity()
    #entity = get_object_or_404(CremeEntity.objects.even_deleted(), pk=object_id).get_real_entity()
    entity.can_view_or_die(request.user)

    LastViewedItem(request, entity)

    return render(request, template, {'object': entity, 'path': path})
