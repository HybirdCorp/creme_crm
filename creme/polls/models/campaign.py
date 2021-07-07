# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2021  Hybird
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
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.commercial.models import MarketSegment
from creme.creme_core.models import CremeEntity


class AbstractPollCampaign(CremeEntity):
    name = models.CharField(_('Name'), max_length=100)
    goal = models.TextField(_('Goal of the campaign'), blank=True)

    start = models.DateField(_('Start'), null=True, blank=True)
    due_date = models.DateField(_('Due date'), null=True, blank=True)

    segment = models.ForeignKey(
        MarketSegment,
        verbose_name=_('Related segment'),
        null=True, blank=True, on_delete=models.PROTECT,
    )
    expected_count = models.PositiveIntegerField(_('Expected replies number'), default=1)

    creation_label = pgettext_lazy('polls', 'Create a campaign')
    save_label     = pgettext_lazy('polls', 'Save the campaign of polls')

    class Meta:
        abstract = True
        # manager_inheritance_from_future = True
        app_label = 'polls'
        verbose_name = _('Campaign of polls')
        verbose_name_plural = _('Campaigns of polls')
        ordering = ('name',)

    def __str__(self):
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
