################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2022-2024  Hybird
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

from django.http import Http404
from django.utils.translation import gettext_lazy as _

from creme.creme_core import get_world_settings_model
from creme.creme_core.auth import SUPERUSER_PERM
from creme.creme_core.views import generic

from ..bricks import WorldSettingsBrick
from ..forms import world_settings as world_forms
from .base import ConfigPortal


class Portal(ConfigPortal):
    template_name = 'creme_config/portals/world-settings.html'
    brick_classes = [WorldSettingsBrick]


class WorldSettingEdition(generic.CremeModelEditionPopup):
    # model = WorldSettings
    # TODO: change the title dynamically?
    title = _("Edit the instance's settings")
    permissions = SUPERUSER_PERM

    form_classes = {
        'menu_icon': world_forms.MenuIconForm,
        'password':  world_forms.PasswordFeaturesForm,
        'displayed_name': world_forms.UserDisplayedNameForm,
    }

    def get_object(self, *args, **kwargs):
        request = self.request

        queryset = get_world_settings_model().objects.all()

        if request.method == 'POST':
            queryset = queryset.select_for_update()

        instance = queryset.first()
        if instance is None:
            raise Http404(
                'No instance of WorldSettings has been found ; '
                'have you run the command "creme_populate"?'
            )

        # NB: for child classes
        self.check_instance_permissions(instance, request.user)

        return instance

    def get_form_class(self):
        try:
            return self.form_classes[self.kwargs['field_name']]
        except KeyError:
            raise Http404('The requested field name does not exist.')
