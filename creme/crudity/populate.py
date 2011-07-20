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

from django.utils.translation import ugettext as _

from creme_core.management.commands.creme_populate import BasePopulator

from creme_config.models import SettingKey, SettingValue

from crudity.constants import SETTING_CRUDITY_SANDBOX_BY_USER


class Populator(BasePopulator):
    def populate(self, *args, **kwargs):
        sk = SettingKey.create(pk=SETTING_CRUDITY_SANDBOX_BY_USER,
                               description=_(u"Are waiting actions are by user?"),
                               app_label='crudity', type=SettingKey.BOOL
                              )
        SettingValue.objects.create(key=sk, user=None, value=False)
