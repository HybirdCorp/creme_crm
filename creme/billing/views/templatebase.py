# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views import generic

from ... import billing
from ..constants import DEFAULT_HFILTER_TEMPLATE
from ..forms.templatebase import TemplateBaseEditForm


TemplateBase = billing.get_template_base_model()
SalesOrder = billing.get_sales_order_model()
Invoice = billing.get_invoice_model()


def abstract_edit_templatebase(request, template_id, form=TemplateBaseEditForm):
    return generic.edit_entity(request, template_id, TemplateBase, form)


@login_required
@permission_required('billing')
def edit(request, template_id):
    return abstract_edit_templatebase(request, template_id)


@login_required
@permission_required('recurrents')
def detailview(request, template_id):
    user = request.user
    has_perm = user.has_perm
    isnt_staff = not user.is_staff

    return generic.view_entity(request, template_id, TemplateBase,
                               template='billing/view_template.html',
                               extra_template_dict={
                                    'can_download':       False,
                                    'can_create_order':   has_perm(cperm(SalesOrder)) and isnt_staff,
                                    'can_create_invoice': has_perm(cperm(Invoice)) and isnt_staff,
                               },
                              )


@login_required
@permission_required('billing')
def listview(request):
    return generic.list_view(request, TemplateBase, hf_pk=DEFAULT_HFILTER_TEMPLATE,
                             extra_dict={'add_url': reverse('recurrents__create_generator')},
                            )
