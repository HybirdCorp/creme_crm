# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.utils.translation import ugettext as _

from creme_core.models import SearchConfigItem, HeaderFilterItem, HeaderFilter
from creme_core.management.commands.creme_populate import BasePopulator

from sms.models import MessagingList, SMSCampaign, MessageTemplate


class Populator(BasePopulator):
    dependencies = ['creme.creme_core']

    def populate(self, *args, **kwargs):
        hf = HeaderFilter.create(pk='sms-hf_mlist', name=_(u'Messaging list view'), model=MessagingList)
        hf.set_items([HeaderFilterItem.build_4_field(model=MessagingList, name='name')])

        hf = HeaderFilter.create(pk='sms-hf_campaign', name=_(u'Campaign view'), model=SMSCampaign)
        hf.set_items([HeaderFilterItem.build_4_field(model=SMSCampaign, name='name')])

        hf = HeaderFilter.create(pk='sms-hf_template', name=_(u'Message template view'), model=MessageTemplate)
        hf.set_items([HeaderFilterItem.build_4_field(model=MessageTemplate, name='name')])

        SearchConfigItem.create(SMSCampaign, ['name'])
        SearchConfigItem.create(MessagingList, ['name'])
