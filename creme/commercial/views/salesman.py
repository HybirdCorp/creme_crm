# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from django.core.urlresolvers import reverse
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic import list_view

from creme.persons import get_contact_model
#from creme.persons.models import Contact
from creme.persons.views.contact import abstract_add_contact

from ..constants import PROP_IS_A_SALESMAN
from ..forms.salesman import SalesManCreateForm


Contact = get_contact_model()


def abstract_add_salesman(request, form=SalesManCreateForm,
                          submit_label=_('Save the salesman'),
                         ):
    return abstract_add_contact(request, form=form, submit_label=submit_label)


# TODO: factorise with generic list_view (list_contacts + property) ??
#       problem: list_view can accept to filter on a property (register a filtered view in the menu etc...)
def abstract_list_salesmen(request, title=_(u'List of salesmen')):
    return list_view(request, Contact,
                     extra_dict={'list_title': title,
                                 # TODO: button registry to change the button label
                                 'add_url': reverse('commercial__create_salesman'),
                                },
                     extra_q=Q(properties__type=PROP_IS_A_SALESMAN),
                    )


@login_required
# @permission_required('persons', 'persons.add_contact')
@permission_required('persons', cperm(Contact))
def add(request):
    return abstract_add_salesman(request)


@login_required
@permission_required('persons')
def listview(request):
    return abstract_list_salesmen(request)
