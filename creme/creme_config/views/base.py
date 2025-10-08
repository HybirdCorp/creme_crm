################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2025  Hybird
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

from collections.abc import Sequence

from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.gui.bricks import Brick
from creme.creme_core.views import generic

_PERM = 'creme_core.can_admin'


class ConfigPortal(generic.BricksView):
    template_name = 'creme_config/portals/base.html'
    brick_classes: list[type[Brick]] = []

    def get_bricks(self):
        # return [brick_cls() for brick_cls in self.brick_classes]
        return {'main': [brick_cls() for brick_cls in self.brick_classes]}


class ConfigCreation(generic.CremeFormPopup):
    permissions: str | Sequence[str] = _PERM
    submit_label = _('Save the configuration')


class ConfigModelCreation(generic.CremeModelCreationPopup):
    permissions: str | Sequence[str] = _PERM


class ConfigModelCreationWizard(generic.CremeModelCreationWizardPopup):
    permissions: str | Sequence[str] = _PERM


class ConfigModelEditionWizard(generic.CremeModelEditionWizardPopup):
    permissions: str | Sequence[str] = _PERM


class ConfigEdition(generic.CremeEditionPopup):
    permissions: str | Sequence[str] = _PERM


class ConfigModelEdition(generic.CremeModelEditionPopup):
    permissions: str | Sequence[str] = _PERM


class ConfigDeletion(generic.CheckedView):
    permissions: str | Sequence[str] = _PERM

    def perform_deletion(self, request):
        raise NotImplementedError

    def post(self, request, **kwargs):
        self.perform_deletion(request)

        return HttpResponse()
