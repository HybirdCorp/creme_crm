################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import SettingValue
from creme.creme_core.views.generic import CremeModelEditionPopup

from ..forms.setting import SettingForm


# TODO: move to generic_views.py ??
class SettingValueEdition(CremeModelEditionPopup):
    model = SettingValue
    form_class = SettingForm
    pk_url_kwarg = 'svalue_id'
    title = _('Edit «{key}»')

    def get_object(self, *args, **kwargs):
        svalue = super().get_object(*args, **kwargs)

        if svalue.key.hidden:
            raise ConflictError('You can not edit a SettingValue which is hidden.')

        self.request.user.has_perm_to_admin_or_die(svalue.key.app_label)

        return svalue

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['key'] = self.object.key.description

        return data
