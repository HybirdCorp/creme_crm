################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2023  Hybird
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

# import creme.creme_core.models.fields as core_fields
import creme.creme_core.models as core_models


# TODO: uniqueness, OneToOne...
class SoonAnonymized(core_models.CremeModel):
    # entity_content_type = core_fields.EntityCTypeForeignKey(related_name='+', editable=False)
    # entity = models.ForeignKey(
    #     core_models.CremeEntity,
    #     related_name='gdpr_soon_anonymized',
    #     editable=False, on_delete=models.CASCADE,
    # ).set_tags(viewable=False)
    # real_entity = core_fields.RealEntityForeignKey(
    #     ct_field='entity_content_type', fk_field='entity',
    # )
    contact = models.OneToOneField(
        settings.PERSONS_CONTACT_MODEL,
        # related_name='+',  # 'gdpr_soon_anonymized'??
        # editable=False,
        on_delete=models.CASCADE,
    )

    class Meta:
        app_label = 'gdpr'
