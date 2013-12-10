# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.views.generic import add_entity, edit_entity, list_view, view_entity

from creme.billing.models import SalesOrder
from creme.billing.views.workflow import _add_with_relations
from creme.billing.forms.sales_order import SalesOrderCreateForm, SalesOrderEditForm


@login_required
@permission_required('billing')
@permission_required('billing.add_salesorder')
def add(request):
    return add_entity(request, SalesOrderCreateForm, extra_initial={'status': 1},
                      extra_template_dict={'submit_label': _('Save the sales order')},
                     )

@login_required
@permission_required('billing')
@permission_required('billing.add_salesorder')
def add_with_relations(request, target_id, source_id):
    return _add_with_relations(request, target_id, source_id, SalesOrderCreateForm,
                               ugettext(u"Add a sales order for <%s>"), status_id=1,
                              )

@login_required
@permission_required('billing')
def edit(request, order_id):
    return edit_entity(request, order_id, SalesOrder, SalesOrderEditForm)

@login_required
@permission_required('billing')
def detailview(request, order_id):
    user = request.user
    has_perm = user.has_perm
    isnt_staff = not user.is_staff

    return view_entity(request, order_id, SalesOrder, '/billing/sales_order',
                       'billing/view_sales_order.html',
                       {'can_download':       True,
                        'can_create_invoice': has_perm('billing.add_invoice') and isnt_staff,
                       }
                      )

@login_required
@permission_required('billing')
def listview(request):
    return list_view(request, SalesOrder, extra_dict={'add_url':'/billing/sales_order/add'})
