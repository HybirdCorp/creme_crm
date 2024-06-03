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
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import HistoryConfigItem
from creme.creme_core.utils import get_from_POST_or_404

from ..bricks import HistoryConfigBrick
from ..forms.history import HistoryConfigForm
from . import base


class HistoryConfigCreation(base.ConfigCreation):
    model = HistoryConfigItem
    form_class = HistoryConfigForm
    title = _('New relation types')


class Portal(base.ConfigPortal):
    template_name = 'creme_config/portals/history.html'
    brick_classes = [HistoryConfigBrick]


class HistoryItemDeletion(base.ConfigDeletion):
    id_arg = 'id'

    def perform_deletion(self, request):
        get_object_or_404(
            HistoryConfigItem,
            pk=get_from_POST_or_404(request.POST, self.id_arg),
        ).delete()
