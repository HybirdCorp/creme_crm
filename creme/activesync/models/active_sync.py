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

from django.db import models
from django.contrib.auth.models import User

from creme_core.models.base import CremeModel
from activesync.utils import generate_guid

class CremeExchangeMapping(CremeModel):
    creme_entity_id    = models.IntegerField(u'Creme entity pk', unique=True)
    exchange_entity_id = models.CharField(u'Exchange entity pk', max_length=64, unique=True)
    synced             = models.BooleanField(u'Already synced on server', default=False)

    def __unicode__(self):
        return u"<CremeExchangeMapping ce_id: <%s>, ex_id: <%s> >" % (self.creme_entity_id, self.exchange_entity_id)

    class Meta:
        app_label = 'activesync'
        verbose_name = u""
        verbose_name_plural = u""


class CremeClient(CremeModel):
    user       = models.ForeignKey(User, verbose_name=u'Assigned to')
    client_id  = models.CharField(u'Creme Client ID', max_length=32,  default=generate_guid())
    policy_key = models.CharField(u'Last policy key', max_length=200, default=0)
    sync_key   = models.CharField(u'Last sync key',   max_length=200, default=None, blank=True, null=True)

    def __unicode__(self):
        return u"<CremeClient for <%s> >" % self.user

    class Meta:
        app_label = 'activesync'
        verbose_name = u""
        verbose_name_plural = u""