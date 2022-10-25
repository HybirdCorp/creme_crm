################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2022  Hybird
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

from .base import CremeModel
from .fields import EntityCTypeForeignKey


class FlagsConfigItem(CremeModel):
    name = models.CharField(_('Name'), max_length=100)
    entity_type = EntityCTypeForeignKey(editable=False)
    value = models.PositiveSmallIntegerField(editable=False)

    # TODO: JSON metadata?
    # TODO: unique together
