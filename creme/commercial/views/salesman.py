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

from logging import debug

from django.db.models import Q
from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required

from creme_core.gui.last_viewed import change_page_for_last_item_viewed
from creme_core.entities_access.functions_for_permissions import add_view_or_die, get_view_or_die
from creme_core.views.generic import add_entity, list_view

from persons.models import Contact

from commercial.forms.salesman import SalesManCreateForm
from commercial.constants import PROP_IS_A_SALESMAN


@login_required
@get_view_or_die('commercial')
@add_view_or_die(ContentType.objects.get_for_model(Contact), None, 'persons')
def add(request):
    return add_entity(request, SalesManCreateForm, template='persons/add_contact_form.html')

#TODO: factorise with generic list_view (ticket 194)
#      problem: list_view can accept to filter on a property (register a filtered view in the menu etc...)
@login_required
@get_view_or_die('commercial')
@change_page_for_last_item_viewed
def listview(request):
    return list_view(request, Contact,
                     extra_dict={
                                    'list_title': _(u'List of salesmen'),
                                    'add_url':    '/commercial/salesman/add',
                                 },
                     extra_q=Q(properties__type=PROP_IS_A_SALESMAN))
