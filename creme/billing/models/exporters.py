################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020  Hybird
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
from django.utils.translation import gettext as _

from creme.creme_core.models.fields import CTypeOneToOneField


class ExporterConfigItem(models.Model):
    content_type = CTypeOneToOneField()
    engine_id = models.CharField(max_length=80)
    flavour_id = models.CharField(max_length=80, blank=True)

    class Meta:
        app_label = 'billing'

    def __str__(self):
        return _('Export configuration of: {}').format(self.content_type)
