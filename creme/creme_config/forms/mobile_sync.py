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

from django.forms.fields import URLField, CharField, BooleanField
from django.utils.translation import ugettext_lazy as _

from creme_core.forms.base import CremeForm

from creme_config.constants import MAPI_SERVER_URL, MAPI_DOMAIN, MAPI_SERVER_SSL
from creme_config.models.config_models import CremeKVConfig

#TODO: Move to active_sync & make a registry in creme_config for non-model forms
class MobileSyncForm(CremeForm):

    url    = URLField(label=_(u"Server url"), required=False)
    domain = CharField(label=_(u"Domain"), required=False)
    ssl    = BooleanField(label=_(u"Is secure"), required=False)

    def __init__(self, *args, **kwargs):
        super(MobileSyncForm, self).__init__(*args, **kwargs)

    def save(self):
        clean_get = self.cleaned_data.get

        server_url = CremeKVConfig.objects.get(pk=MAPI_SERVER_URL)
        server_url.value = clean_get('url')
        server_url.save()

        server_domain = CremeKVConfig.objects.get(pk=MAPI_DOMAIN)
        server_domain.value = clean_get('domain')
        server_domain.save()

        server_ssl = CremeKVConfig.objects.get(pk=MAPI_SERVER_SSL)
        server_ssl.value = int(clean_get('ssl'))
        server_ssl.save()


