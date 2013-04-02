# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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
from django.contrib.auth.models import User

from creme.crudity.constants import SETTING_CRUDITY_SANDBOX_BY_USER

def post_save_setting_value(sender, instance, **kwargs):
    """Set is_sandbox_by_user value on CreateFromEmailBackend subclasses because they are singletons"""
    from creme.crudity.registry import crudity_registry
    from creme.crudity.models import WaitingAction

    if instance.key_id == SETTING_CRUDITY_SANDBOX_BY_USER:
        fetchers = crudity_registry.get_fetchers()
        inputs = []
        for fetcher in fetchers:
            for inputs_dict in fetcher.get_inputs():
                inputs.extend(inputs_dict.values())

        backends = []
        for input in inputs:
            backends.extend(input.get_backends())

        for backend in backends:
            backend.is_sandbox_by_user = instance.value

        if instance.value:
            WaitingAction.objects.filter(user=None).update(user=User.objects.filter(is_superuser=True).order_by('-pk')[0])
