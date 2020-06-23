# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2020  Hybird
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


# TODO: + ForeignKey to ContentType ? (takes more space but less queries)
class Imprint(models.Model):  # CremeModel ?
    date = models.DateTimeField(auto_now_add=True)
    entity = models.ForeignKey(
        CremeEntity, related_name='imprints', on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='imprints', on_delete=models.CASCADE,
    )

    class Meta:
        app_label = 'creme_core'

    def __str__(self):
        return f'Imprint(date={self.date}, entity={self.entity.id}, user={self.user})'
