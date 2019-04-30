# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from django.contrib.auth import get_user_model
from django.forms.widgets import Select
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms.base import CremeModelForm


User = get_user_model()


def _build_select():
    return Select(attrs={'onchange': 'creme.ajax.json.ajaxFormSubmit($(this.form), '
                                                                    'function() {creme.utils.reload(window);}'
                                                                   ');'
                        },
                 )


class UserThemeForm(CremeModelForm):
    class Meta:
        model = User
        fields = ('theme',)
        widgets = {'theme': _build_select()}
        labels = {'theme': _('Choose your theme')}


class UserTimeZoneForm(CremeModelForm):
    class Meta:
        model = User
        fields = ('time_zone',)
        widgets = {'time_zone': _build_select()}
        labels = {'time_zone': _('Choose your time zone')}
