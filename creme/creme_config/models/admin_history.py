################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2025  Hybird
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

from creme.creme_core.models import fields as core_fields


class AdminHistoryLine(models.Model):
    content_type = core_fields.CTypeForeignKey()
    date = core_fields.CreationDateTimeField(_('Date'))

    # Not a FK to a User object because we want to keep the same line after the
    # deletion of a User.
    username = models.CharField(max_length=30)

    class Meta:
        app_label = 'creme_config'
        # verbose_name = _('Line of history')
        # verbose_name_plural = _('Lines of history')
        # indexes = [
        #     models.Index(fields=['entity_id', '-id'], name='hline__entity_detailview')
        # ]
        ordering = ('id',)
