################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

import creme.creme_core.models as core_models
import creme.creme_core.models.fields as core_fields


class CommercialApproach(core_models.CremeModel):
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    creation_date = core_fields.CreationDateTimeField(_('Creation date'), editable=False)

    related_activity = models.ForeignKey(
        settings.ACTIVITIES_ACTIVITY_MODEL, null=True,
        editable=False, on_delete=models.CASCADE,
    )

    entity_content_type = core_fields.EntityCTypeForeignKey(related_name='+', editable=False)
    entity = models.ForeignKey(
        core_models.CremeEntity, related_name='commercial_approaches',
        editable=False, on_delete=models.CASCADE,
    )  # .set_tags(viewable=False) uncomment if it becomes an auxiliary (get_related_entity())
    creme_entity = core_fields.RealEntityForeignKey(
        ct_field='entity_content_type', fk_field='entity',
    )

    creation_label = _('Create a commercial approach')
    save_label     = _('Save the commercial approach')

    class Meta:
        app_label = 'commercial'
        verbose_name = _('Commercial approach')
        verbose_name_plural = _('Commercial approaches')

    def __str__(self):
        return self.title

    @staticmethod
    def get_approaches(entity_pk=None):
        queryset = CommercialApproach.objects.select_related('related_activity')

        return (
            queryset.filter(entity_id=entity_pk)
            if entity_pk else
            queryset.exclude(entity__is_deleted=True)
        )
