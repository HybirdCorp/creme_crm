# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _


class DateReminder(models.Model):  # CremeModel ?
    date_of_remind = models.DateTimeField(blank=True, null=True)
    ident = models.PositiveIntegerField()

    model_content_type = models.ForeignKey(
        ContentType, related_name='reminders_set', on_delete=models.CASCADE
    )
    model_id = models.PositiveIntegerField()

    object_of_reminder = GenericForeignKey(
        ct_field='model_content_type', fk_field='model_id',
    )

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('Reminder')
        verbose_name_plural = _('Reminders')
