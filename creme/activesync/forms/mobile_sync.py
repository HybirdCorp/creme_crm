# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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
from creme.creme_config.models.setting import SettingValue

from creme.creme_core.forms.base import CremeForm

from creme.activesync.constants import MAPI_SERVER_URL, MAPI_DOMAIN, MAPI_SERVER_SSL, COMMONS_SERVER_URL_CFG

class MobileSyncForm(CremeForm):

    url_examples = ChoiceField(label=_(u"Server url examples"), required=False, help_text=_(u"Some common configurations"), choices=chain((("", ""),), COMMONS_SERVER_URL_CFG), widget=Select(attrs={'onchange':'this.form.url.value=$(this).val();'}) )
    url    = URLField(label=_(u"Server url"),                   required=False)
    domain = CharField(label=_(u"Domain"),                      required=False)
    ssl    = BooleanField(label=_(u"Is secure"),                required=False)

    def save(self):
        clean_get = self.cleaned_data.get

        sv_get = SettingValue.objects.get

        sk_url = sv_get(key__id=MAPI_SERVER_URL)
        sk_url.value=clean_get('url')
        sk_url.save()

        sk_domain = sv_get(key__id=MAPI_DOMAIN)
        sk_domain.value=clean_get('domain')
        sk_domain.save()

        sk_ssl = sv_get(key__id=MAPI_SERVER_SSL)
        sk_ssl.value=clean_get('ssl')
        sk_ssl.save()


