################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2024  Hybird
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

from django.conf import settings
from django.db import models

from . import CremeEntity
from . import fields as core_fields


class Imprint(models.Model):  # CremeModel ?
    date = models.DateTimeField(auto_now_add=True)

    entity_ctype = core_fields.EntityCTypeForeignKey(related_name='+', editable=False)
    entity = models.ForeignKey(
        CremeEntity, related_name='imprints', on_delete=models.CASCADE,
    )
    real_entity = core_fields.RealEntityForeignKey(
        ct_field='entity_ctype', fk_field='entity',
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='imprints', on_delete=models.CASCADE,
    )

    class Meta:
        app_label = 'creme_core'

    def __str__(self):
        return f'Imprint(date={self.date}, entity={self.entity.id}, user={self.user})'
