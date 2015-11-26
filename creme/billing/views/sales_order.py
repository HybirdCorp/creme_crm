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

# from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _ #ugettext

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic import add_entity, edit_entity, list_view, view_entity

from .. import get_sales_order_model, get_invoice_model
from ..constants import DEFAULT_HFILTER_ORDER
from ..forms.sales_order import SalesOrderCreateForm, SalesOrderEditForm
#from ..models import SalesOrder
from ..views.workflow import generic_add_related #_add_with_relations


SalesOrder = get_sales_order_model()
Invoice = get_invoice_model()


def abstract_add_salesorder(request, form=SalesOrderCreateForm,
                            initial_status=1,
                            submit_label=_('Save the sales order'),
                           ):
    return add_entity(request, form, extra_initial={'status': initial_status},
                      extra_template_dict={'submit_label': submit_label},
                     )


def abstract_add_related_salesorder(request, target_id,
                                    form=SalesOrderCreateForm, initial_status=1,
                                    title=_(u'Add a sales order for «%s»'),
                                    submit_label=_('Save the sales order'),
                                   ):
    return generic_add_related(request, target_id, form=form,
                               title=title, status_id=initial_status,
                               submit_label=submit_label,
                              )


def abstract_edit_salesorder(request, order_id, form=SalesOrderEditForm):
    return edit_entity(request, order_id, SalesOrder, form)


def abstract_view_salesorder(request, order_id, template='billing/view_sales_order.html'):
    user = request.user

    return view_entity(request, order_id, SalesOrder,
                       # '/billing/sales_order',
                       template=template,
                       extra_template_dict={
                            'can_download':       True,
                            'can_create_invoice': user.has_perm(cperm(Invoice)) and not user.is_staff,
                       }
                      )


@login_required
# @permission_required(('billing', 'billing.add_salesorder'))
@permission_required(('billing', cperm(SalesOrder)))
def add(request):
    return abstract_add_salesorder(request)


#@login_required
#@permission_required(('billing', 'billing.add_salesorder'))
#def add_with_relations(request, target_id, source_id):
#    return _add_with_relations(request, target_id, source_id, SalesOrderCreateForm,
#                               ugettext(u"Add a sales order for <%s>"), status_id=1,
#                              )
@login_required
@permission_required(('billing', cperm(SalesOrder)))
def add_related(request, target_id):
    return abstract_add_related_salesorder(request, target_id)


@login_required
@permission_required('billing')
def edit(request, order_id):
    return abstract_edit_salesorder(request, order_id)


@login_required
@permission_required('billing')
def detailview(request, order_id):
    return abstract_view_salesorder(request, order_id)


@login_required
@permission_required('billing')
def listview(request):
    return list_view(request, SalesOrder, hf_pk=DEFAULT_HFILTER_ORDER,
                     # extra_dict={'add_url': reverse('billing__create_order')}
                    )
