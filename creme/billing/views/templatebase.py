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

from ... import billing
from .. import gui
from ..constants import DEFAULT_HFILTER_TEMPLATE
from ..custom_forms import BTEMPLATE_EDITION_CFORM

TemplateBase = billing.get_template_base_model()


class TemplateBaseDetail(generic.EntityDetail):
    model = TemplateBase
    template_name = 'billing/view_template.html'
    pk_url_kwarg = 'template_id'


class TemplateBaseEdition(generic.EntityEdition):
    model = TemplateBase
    form_class = BTEMPLATE_EDITION_CFORM
    pk_url_kwarg = 'template_id'


class TemplateBasesList(generic.EntitiesList):
    model = TemplateBase
    default_headerfilter_id = DEFAULT_HFILTER_TEMPLATE

    def get_buttons(self):
        return super().get_buttons().replace(
            old=gui.CreationButton, new=gui.GeneratorCreationButton,
        )
