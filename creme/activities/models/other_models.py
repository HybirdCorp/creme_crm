# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

import logging
from datetime import timedelta

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.models import CremeModel
from creme.creme_core.models.fields import DurationField


# TODO: Rename to ActivityKind ??
class ActivityType(CremeModel):
    id = models.CharField(
        primary_key=True, max_length=100, editable=False,
    ).set_tags(viewable=False)

    name = models.CharField(_('Name'), max_length=100)

    default_day_duration = models.IntegerField(_('Default day duration')).set_tags(viewable=False)
    default_hour_duration = DurationField(
        _('Default hour duration'), max_length=15,
    ).set_tags(viewable=False)

    # Used by creme_config
    is_custom = models.BooleanField(default=True, editable=False).set_tags(viewable=False)

    creation_label = pgettext_lazy('activities-type', 'Create a type')

    class Meta:
        app_label = 'activities'
        verbose_name = _('Type of activity')
        verbose_name_plural = _('Types of activity')
        ordering = ('name',)

    def __str__(self):
        return self.name

    def as_timedelta(self):
        hours, minutes, seconds = self.default_hour_duration.split(':')

        return timedelta(
            days=self.default_day_duration,
            hours=int(hours), minutes=int(minutes), seconds=int(seconds),
        )


class ActivitySubType(CremeModel):
    id = models.CharField(
        primary_key=True, max_length=100, editable=False,
    ).set_tags(viewable=False)

    name = models.CharField(_('Name'), max_length=100)
    type = models.ForeignKey(
        ActivityType, verbose_name=_('Type of activity'), on_delete=models.CASCADE,
    ).set_tags(viewable=False)

    # Used by creme_config
    is_custom = models.BooleanField(default=True, editable=False).set_tags(viewable=False)

    creation_label = pgettext_lazy('activities-type', 'Create a sub-type')

    class Meta:
        app_label = 'activities'
        verbose_name = _('Sub-type of activity')
        verbose_name_plural = _('Sub-types of activity')
        ordering = ('name',)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.is_custom and self.type.is_custom:
            # raise ValueError(...) TODO: in creme2.5
            logging.getLogger(__name__).critical(
                'the ActivitySubType id="%s" is not custom,'
                'so the related ActivityType cannot be custom.',
                self.id,
            )

        super().save(*args, **kwargs)


class Status(CremeModel):
    name = models.CharField(_('Name'), max_length=100)
    description = models.TextField(_('Description'))
    # Used by creme_config
    is_custom = models.BooleanField(default=True).set_tags(viewable=False)

    creation_label = pgettext_lazy('activities-status', 'Create a status')

    class Meta:
        app_label = 'activities'
        verbose_name = pgettext_lazy('activities-singular', 'Status of activity')
        verbose_name_plural = pgettext_lazy('activities-plural', 'Status of activity')
        ordering = ('name',)

    def __str__(self):
        return self.name
