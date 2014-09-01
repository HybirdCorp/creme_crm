# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from itertools import chain

from django.forms.fields import URLField, CharField, BooleanField, ChoiceField
from django.forms.widgets import Select
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms.base import CremeForm
from creme.creme_core.models import SettingValue

from ..constants import MAPI_SERVER_URL, MAPI_DOMAIN, MAPI_SERVER_SSL, COMMONS_SERVER_URL_CFG


class MobileSyncForm(CremeForm):
    url_examples = ChoiceField(label=_(u"Server URL examples"), required=False,
                               help_text=_(u"Some common configurations"),
                               choices=chain((("", ""),), COMMONS_SERVER_URL_CFG),
                               widget=Select(attrs={'onchange':'this.form.url.value=$(this).val();'})
                              )
    url    = URLField(label=_(u"Server URL"), required=False)
    domain = CharField(label=_(u"Domain"), required=False)
    ssl    = BooleanField(label=_(u"Is secure"), required=False)

    def __init__(self, *args, **kwargs):
        get_sv = SettingValue.objects.get #TODO: group queries ?
        #self.server_url    = url    = get_sv(key__id=MAPI_SERVER_URL)
        #self.server_domain = domain = get_sv(key__id=MAPI_DOMAIN)
        #self.server_ssl    = ssl    = get_sv(key__id=MAPI_SERVER_SSL)
        self.server_url    = url    = get_sv(key_id=MAPI_SERVER_URL)
        self.server_domain = domain = get_sv(key_id=MAPI_DOMAIN)
        self.server_ssl    = ssl    = get_sv(key_id=MAPI_SERVER_SSL)

        initial = kwargs['initial'] or {}
        initial.update(url=url.value, domain=domain.value, ssl=ssl.value)
        kwargs['initial'] = initial

        super(MobileSyncForm, self).__init__(*args, **kwargs)

    def save(self):
        clean_get = self.cleaned_data.get

        def upgrade_svalue(svalue, value):
            if svalue.value != value:
                svalue.value = value
                svalue.save()

        upgrade_svalue(self.server_url, clean_get('url'))
        upgrade_svalue(self.server_domain, clean_get('domain'))
        upgrade_svalue(self.server_ssl, clean_get('ssl'))
