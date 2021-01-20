# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver

from creme.creme_core.models import SettingValue

from .constants import SETTING_CRUDITY_SANDBOX_BY_USER
from .models import WaitingAction


@receiver(post_save, sender=SettingValue)
def post_save_setting_value(sender, instance, **kwargs):
    """Set is_sandbox_by_user value on CreateFromEmailBackend subclasses
    because they are singletons.
    """
    if instance.key_id == SETTING_CRUDITY_SANDBOX_BY_USER:
        # TODO: do not modify existing instances, just check on-the-fly, so we
        #       can change SettingValue as <False -> True -> False> without
        #       losing information.
        if instance.value:
            WaitingAction.objects.filter(
                user=None,
            ).update(
                user=get_user_model().objects.get_admin(),
            )
