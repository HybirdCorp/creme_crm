# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013  Hybird
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

from django.db.models import (CharField, TextField, DateField,
                              PositiveIntegerField, ForeignKey, PROTECT)
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeEntity

from creme.commercial.models import MarketSegment


class PollCampaign(CremeEntity):
    name = CharField(_(u'Name'), max_length=100)
    goal           = TextField(_(u'Goal of the campaign'), blank=True, null=True)
    start          = DateField(_(u'Start'), null=True, blank=True)
    due_date       = DateField(_(u'Due date'), null=True, blank=True)
    segment        = ForeignKey(MarketSegment, verbose_name=_(u'Related segment'),
                                null=True, blank=True, on_delete=PROTECT,
                               )
    expected_count = PositiveIntegerField(_('Expected replies number'), default=1)

    creation_label = _('Add a campaign')

    class Meta:
        app_label = 'polls'
        verbose_name = _(u'Campaign of polls')
        verbose_name_plural = _(u'Campaigns of polls')

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return '/polls/campaign/%s' % self.id

    def get_edit_absolute_url(self):
        return '/polls/campaign/edit/%s' % self.id

    @staticmethod
    def get_lv_absolute_url():
        return '/polls/campaigns' 
