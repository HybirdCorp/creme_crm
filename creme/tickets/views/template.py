################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from creme.creme_core.views import generic

from .. import get_tickettemplate_model
from ..constants import DEFAULT_HFILTER_TTEMPLATE
from ..custom_forms import TTEMPLATE_EDITION_CFORM

TicketTemplate = get_tickettemplate_model()


class TicketTemplateDetail(generic.EntityDetail):
    model = TicketTemplate
    template_name = 'tickets/view_template.html'
    pk_url_kwarg = 'template_id'


class TicketTemplateEdition(generic.EntityEdition):
    model = TicketTemplate
    form_class = TTEMPLATE_EDITION_CFORM
    pk_url_kwarg = 'template_id'


class TicketTemplatesList(generic.EntitiesList):
    model = TicketTemplate
    default_headerfilter_id = DEFAULT_HFILTER_TTEMPLATE


del TicketTemplate
