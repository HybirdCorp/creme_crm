# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018  Hybird
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

from datetime import date
from functools import partial

from django.utils.translation import ugettext_lazy as _, ungettext

from creme.creme_core.models import FieldsConfig

from .constants import REL_OBJ_EMIT_ORGA


class CurrentYearStatistics:
    label = _('Opportunities (current year)')
    relation_type_id = REL_OBJ_EMIT_ORGA
    invalid_message = _('The field «Actual closing date» is hidden ; '
                        'these statistics are not available.'
                       )
    message_format = _('For {organisation}: {won_stats} / {lost_stats}')

    def __init__(self, opp_model, orga_model):
        self.opp_model = opp_model
        self.orga_model = orga_model

    def __call__(self):
        stats = []
        opp_model = self.opp_model

        if FieldsConfig.get_4_model(opp_model).is_fieldname_hidden('closing_date'):
            stats.append(str(self.invalid_message))
        else:
            filter_opp = partial(
                opp_model.objects.filter,
                relations__type_id=self.relation_type_id,
                closing_date__gte=date.today().replace(month=1, day=1),
            )

            for orga in self.orga_model.get_all_managed_by_creme():
                won_count = filter_opp(sales_phase__won=True,
                                       relations__object_entity_id=orga.id,
                                      ).count()
                lost_count = filter_opp(sales_phase__lost=True,
                                        relations__object_entity_id=orga.id,
                                       ).count()

                if won_count or lost_count:
                    stats.append(
                        self.message_format.format(
                            organisation=orga,
                            won_stats=ungettext('{count} won opportunity',
                                                '{count} won opportunities',
                                                won_count
                                               ).format(count=won_count),
                            lost_stats=ungettext('{count} lost opportunity',
                                                 '{count} lost opportunities',
                                                 lost_count
                                                ).format(count=lost_count),
                        )
                    )

        return stats
