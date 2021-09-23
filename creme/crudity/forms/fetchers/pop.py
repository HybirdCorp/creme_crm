################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2022-2023  Hybird
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

from django import forms
from django.forms.widgets import PasswordInput
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeForm


class PopFetcherOptionsForm(CremeForm):
    url = forms.CharField(
        label=_('URL of the POP server'), help_text=_('Eg: pop.mydomain.com'),
    )
    username = forms.CharField(label=_('Username'))
    password = forms.CharField(
        label=_('Password'), strip=False,
        widget=PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    port = forms.IntegerField(label=_('Port'))
    use_ssl = forms.BooleanField(label=_('Use SSL?'))
    # TODO: complete fields?
