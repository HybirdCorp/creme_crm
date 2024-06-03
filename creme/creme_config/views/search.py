################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import SearchConfigItem
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views.generic.base import EntityCTypeRelatedMixin

from ..bricks import SearchConfigBrick
from ..forms import search as search_forms
from . import base


class Portal(base.ConfigPortal):
    template_name = 'creme_config/portals/search.html'
    brick_classes = [SearchConfigBrick]


class SearchConfigCreation(EntityCTypeRelatedMixin,
                           base.ConfigModelCreation,
                           ):
    model = SearchConfigItem
    form_class = search_forms.SearchConfigCreationForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ctype'] = self.get_ctype()

        return kwargs

    def get_title(self):
        return _('New search configuration for «{model}»').format(
            model=self.get_ctype(),
        )


class SearchConfigEdition(base.ConfigModelEdition):
    model = SearchConfigItem
    form_class = search_forms.SearchConfigEditionForm
    pk_url_kwarg = 'search_config_id'


class SearchConfigDeletion(base.ConfigDeletion):
    id_arg = 'id'

    def perform_deletion(self, request):
        sci = get_object_or_404(
            SearchConfigItem,
            id=get_from_POST_or_404(request.POST, self.id_arg),
        )

        if sci.is_default:
            raise ConflictError('You cannot delete the default configuration')

        sci.delete()
