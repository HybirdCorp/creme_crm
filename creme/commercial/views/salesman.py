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

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.decorators import login_required, permission_required

from creme.creme_core.views.generic import add_entity, list_view

from creme.persons.models import Contact

from ..forms.salesman import SalesManCreateForm
from ..constants import PROP_IS_A_SALESMAN


@login_required
@permission_required('persons')
@permission_required('persons.add_contact')
def add(request):
    return add_entity(request, SalesManCreateForm, template='persons/add_contact_form.html',
                      extra_template_dict={'submit_label': _('Save the salesman')},
                     )

#TODO: factorise with generic list_view ??
#      problem: list_view can accept to filter on a property (register a filtered view in the menu etc...)
@login_required
@permission_required('persons')
def listview(request):
    return list_view(request, Contact,
                     extra_dict={'list_title': ugettext(u'List of salesmen'),
                                 'add_url':    '/commercial/salesman/add',
                                },
                     extra_q=Q(properties__type=PROP_IS_A_SALESMAN),
                    )
