# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from django.db.models import CharField, IntegerField, TextField, ForeignKey, BooleanField
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from creme.creme_core.models import CremeModel
from creme.creme_core.models.fields import DurationField


# TODO: Rename to ActivityKind ??
class ActivityType(CremeModel):
    id                    = CharField(primary_key=True, max_length=100, editable=False)\
                                     .set_tags(viewable=False)
    name                  = CharField(_(u'Name'), max_length=100)
    default_day_duration  = IntegerField(_(u'Default day duration')).set_tags(viewable=False)
    default_hour_duration = DurationField(_(u'Default hour duration'), max_length=15)\
                                         .set_tags(viewable=False)
    is_custom             = BooleanField(default=True, editable=False).set_tags(viewable=False) # Used by creme_config

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'activities'
        verbose_name = _(u'Type of activity')
        verbose_name_plural = _(u'Types of activity')
        ordering = ('name',)

    def as_timedelta(self):
        hours, minutes, seconds = self.default_hour_duration.split(':')

        return timedelta(days=self.default_day_duration,
                         hours=int(hours), minutes=int(minutes), seconds=int(seconds)
                        )


class ActivitySubType(CremeModel):
    id        = CharField(primary_key=True, max_length=100, editable=False)\
                         .set_tags(viewable=False)
    name      = CharField(_(u'Name'), max_length=100)
    type      = ForeignKey(ActivityType, verbose_name=_(u'Type of activity'))\
                          .set_tags(viewable=False)
    is_custom = BooleanField(default=True, editable=False).set_tags(viewable=False)  # Used by creme_config

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'activities'
        verbose_name = _(u'Sub-type of activity')
        verbose_name_plural = _(u'Sub-types of activity')
        ordering = ('name',)


class Status(CremeModel):
    name        = CharField(_(u'Name'), max_length=100)
    description = TextField(_(u'Description'))
    is_custom   = BooleanField(default=True).set_tags(viewable=False)  # Used by creme_config

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'activities'
        verbose_name = pgettext_lazy('activities-singular', u'Status of activity')
        verbose_name_plural = pgettext_lazy('activities-plural', u'Status of activity')
        ordering = ('name',)
