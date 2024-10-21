################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CremeModel
from creme.creme_core.models.fields import EntityCTypeForeignKey


class NumberGeneratorItem(CremeModel):
    organisation = models.ForeignKey(
        settings.PERSONS_ORGANISATION_MODEL, on_delete=models.CASCADE,
    )
    numbered_type = EntityCTypeForeignKey()
    is_edition_allowed = models.BooleanField(
        verbose_name=_('Editable number'),
        help_text=_('Can the number be manually edited?'),  # TODO "AFTER" ?
        default=False,
    )
    data = models.JSONField(default=dict)

    class Meta:
        app_label = 'billing'
        unique_together = ('organisation', 'numbered_type')

    def __eq__(self, other):
        return (
            isinstance(other, type(self))
            and self.organisation_id == other.organisation_id
            and self.numbered_type == other.numbered_type
            and self.is_edition_allowed == other.is_edition_allowed
            and self.data == other.data
        )

    def __str__(self):
        return (
            f'NumberGenerationItem('
            f'organisation="{self.organisation}", '
            f'numbered_type="{self.numbered_type}", '
            f'data="{self.data}", '
            f')'
        )
