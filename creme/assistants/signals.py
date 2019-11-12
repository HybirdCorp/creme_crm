# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2018  Hybird
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

from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver

from . import models


@receiver(post_save, sender=models.Alert)
@receiver(post_save, sender=models.ToDo)
def _refresh_alert_reminder_job(sender, instance, **kwargs):
    from creme.creme_core.creme_jobs import reminder_type

    if instance.to_be_reminded:
        reminder_type.refresh_job()
