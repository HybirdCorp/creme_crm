# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import list_view, add_entity, edit_entity, view_entity_with_template
from creme_core.gui.last_viewed import change_page_for_last_item_viewed

from commercial.models import Act
from commercial.forms.act import CreateForm, EditForm


@login_required
@permission_required('commercial')
@permission_required('commercial.add_act')
def add(request):
    return add_entity(request, CreateForm)

def edit(request, act_id):
    return edit_entity(request, act_id, Act, EditForm, 'commercial')

@login_required
@permission_required('commercial')
def detailview(request, object_id):
    return view_entity_with_template(request, object_id, Act, '/commercial/act',
                                     'commercial/view_act.html'
                                    )

@login_required
@permission_required('commercial')
@change_page_for_last_item_viewed #WTF ???
def listview(request):
    return list_view(request, Act, extra_dict={'add_url':'/commercial/act/add'})
