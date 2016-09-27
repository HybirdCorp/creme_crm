# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2016  Hybird
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

from django.core.urlresolvers import reverse
from django.db.models import (CharField, TextField, DateField,
        PositiveIntegerField, ForeignKey, PROTECT)
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeEntity

from creme.commercial.models import MarketSegment


class AbstractPollCampaign(CremeEntity):
    name           = CharField(_(u'Name'), max_length=100)
    goal           = TextField(_(u'Goal of the campaign'), blank=True)
    start          = DateField(_(u'Start'), null=True, blank=True)
    due_date       = DateField(_(u'Due date'), null=True, blank=True)
    segment        = ForeignKey(MarketSegment, verbose_name=_(u'Related segment'),
                                null=True, blank=True, on_delete=PROTECT,
                               )
    expected_count = PositiveIntegerField(_('Expected replies number'), default=1)

    creation_label = _('Add a campaign')

    class Meta:
        abstract = True
        app_label = 'polls'
        verbose_name = _(u'Campaign of polls')
        verbose_name_plural = _(u'Campaigns of polls')
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('polls__view_campaign', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('polls__create_campaign')

    def get_edit_absolute_url(self):
        return reverse('polls__edit_campaign', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('polls__list_campaigns')


class PollCampaign(AbstractPollCampaign):
    class Meta(AbstractPollCampaign.Meta):
        swappable = 'POLLS_CAMPAIGN_MODEL'
