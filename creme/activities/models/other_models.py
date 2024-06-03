################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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

from datetime import timedelta

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.models import MinionModel
from creme.creme_core.models import fields as core_fields


# TODO: rename to ActivityKind ??
class ActivityType(MinionModel):
    name = models.CharField(_('Name'), max_length=100)

    # TODO: improve the values in save() (ex: <62 minutes> => <1 hour, 2 minutes>)?
    default_day_duration = models.IntegerField(
        _('Default day duration'), default=0,
    ).set_tags(viewable=False)
    default_hour_duration = core_fields.DurationField(
        _('Default hour duration'), max_length=15,  # TODO: default='0:15:0',
    ).set_tags(viewable=False)

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


class ActivitySubType(MinionModel):
    name = models.CharField(_('Name'), max_length=100)
    type = models.ForeignKey(
        ActivityType, verbose_name=_('Type of activity'), on_delete=models.CASCADE,
    ).set_tags(viewable=False)

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
            raise ValueError(
                f'The ActivitySubType id="{self.id}" is not custom, '
                f'so the related ActivityType cannot be custom.'
            )

        super().save(*args, **kwargs)


class Status(MinionModel):
    name = models.CharField(_('Name'), max_length=100)
    description = models.TextField(_('Description'))
    color = core_fields.ColorField(default=core_fields.ColorField.random)

    creation_label = pgettext_lazy('activities-status', 'Create a status')

    class Meta:
        app_label = 'activities'
        verbose_name = pgettext_lazy('activities-singular', 'Status of activity')
        verbose_name_plural = pgettext_lazy('activities-plural', 'Status of activity')
        ordering = ('name',)

    def __str__(self):
        return self.name
