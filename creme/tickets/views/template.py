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

# import warnings

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views import generic

from .. import get_tickettemplate_model
from ..constants import DEFAULT_HFILTER_TTEMPLATE
from ..forms.template import TicketTemplateForm


TicketTemplate = get_tickettemplate_model()


# def abstract_edit_ticket_template(request, template_id, form=TicketTemplateForm):
#     warnings.warn('tickets.views.template.abstract_edit_ticket_template() is deprecated ; '
#                   'use the class-based view TicketTemplateEdition instead.',
#                   DeprecationWarning
#                  )
#     return generic.edit_entity(request, template_id, TicketTemplate, form)


# def abstract_view_ticket_template(request, template_id,
#                                   template='tickets/view_template.html',
#                                  ):
#     warnings.warn('tickets.views.template.abstract_view_ticket_template() is deprecated ; '
#                   'use the class-based view TicketTemplateDetail instead.',
#                   DeprecationWarning
#                  )
#     return generic.view_entity(request, template_id, TicketTemplate, template=template)


# @login_required
# @permission_required('tickets')
# def edit(request, template_id):
#     warnings.warn('tickets.views.template.edition() is deprecated.', DeprecationWarning)
#     return abstract_edit_ticket_template(request, template_id)


# @login_required
# @permission_required('tickets')
# def detailview(request, template_id):
#     warnings.warn('tickets.views.template.detailview() is deprecated.', DeprecationWarning)
#     return abstract_view_ticket_template(request, template_id)


@login_required
@permission_required('tickets')
def listview(request):
    return generic.list_view(request, TicketTemplate, hf_pk=DEFAULT_HFILTER_TTEMPLATE)


# Class-based views  ----------------------------------------------------------

class TicketTemplateDetail(generic.EntityDetail):
    model = TicketTemplate
    template_name = 'tickets/view_template.html'
    pk_url_kwarg = 'template_id'


class TicketTemplateEdition(generic.EntityEdition):
    model = TicketTemplate
    form_class = TicketTemplateForm
    pk_url_kwarg = 'template_id'
