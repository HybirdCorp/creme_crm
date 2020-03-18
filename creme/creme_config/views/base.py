# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2020  Hybird
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

from typing import Optional

from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.views import generic

_PERM = 'creme_core.can_admin'


class ConfigCreation(generic.CremeFormPopup):
    permissions: Optional[str] = _PERM
    submit_label = _('Save the configuration')


class ConfigModelCreation(generic.CremeModelCreationPopup):
    permissions: Optional[str] = _PERM


class ConfigModelCreationWizard(generic.CremeModelCreationWizardPopup):
    permissions: Optional[str] = _PERM


class ConfigModelEditionWizard(generic.CremeModelEditionWizardPopup):
    permissions: Optional[str] = _PERM


class ConfigEdition(generic.CremeEditionPopup):
    permissions: Optional[str] = _PERM


class ConfigModelEdition(generic.CremeModelEditionPopup):
    permissions: Optional[str] = _PERM


class ConfigDeletion(generic.CheckedView):
    permissions = _PERM

    def perform_deletion(self, request):
        raise NotImplementedError

    def post(self, request, **kwargs):
        self.perform_deletion(request)

        return HttpResponse()
