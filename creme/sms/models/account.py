################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CremeModel

from ..webservice.backend import WSException
from ..webservice.samoussa import SamoussaBackEnd


class SMSAccount(CremeModel):
    name = models.CharField(_('Name'), max_length=200, null=True)
    credit = models.IntegerField(_('Credit'), null=True)
    groupname = models.CharField(_('Group'), max_length=200, null=True)

    class Meta:
        app_label = 'sms'
        verbose_name = _('SMS account')
        verbose_name_plural = _('SMS accounts')

    def __str__(self):
        return self.name

    def sync(self):
        ws = SamoussaBackEnd()

        try:
            ws.connect()
            res = ws.get_account()

            parent = res.get('parent', {})

            self.name = res.get('name', self.name)
            self.credit = int(res.get('credit', '0')) + int(parent.get('credit', '0'))
            self.groupname = parent.get('name', '')
            self.save()

            ws.close()
        except WSException:
            pass

        return self

    sync.alters_data = True
