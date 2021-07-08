# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2021  Hybird
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

from django.db.models import Count, FilteredRelation, Q
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from creme.creme_core.models import FieldsConfig

from .constants import REL_OBJ_EMIT_ORGA


class CurrentYearStatistics:
    label = _('Opportunities (current year)')
    relation_type_id = REL_OBJ_EMIT_ORGA
    invalid_message = _(
        'The field «Actual closing date» is hidden ; '
        'these statistics are not available.'
    )
    message_format = _('For {organisation}: {won_stats} / {lost_stats}')

    def __init__(self, opp_model, orga_model):
        self.opp_model = opp_model
        self.orga_model = orga_model

    def __call__(self):
        stats = []
        opp_model = self.opp_model

        if FieldsConfig.objects.get_for_model(opp_model).is_fieldname_hidden('closing_date'):
            stats.append(str(self.invalid_message))
        else:
            # TODO: use this previous code when there is only one managed organisation ??
            # for orga in self.orga_model.get_all_managed_by_creme():
            #     agg = opp_model.objects \
            #              .annotate(relations_w_orga=FilteredRelation(
            #                             'relations',
            #                             condition=Q(relations__object_entity_id=orga.id)
            #                         )
            #                       ) \
            #              .filter(relations_w_orga__type_id=self.relation_type_id,
            #                      closing_date__gte=date.today().replace(month=1, day=1),
            #                     )\
            #              .aggregate(
            #                 won=Count('pk', filter=Q(sales_phase__won=True)),
            #                 lost=Count('pk', filter=Q(sales_phase__lost=True)),
            #              )
            #     won_count = agg['won']
            #     lost_count = agg['lost']
            #
            #     if won_count or lost_count:
            #         stats.append(
            #             self.message_format.format(
            #                 organisation=orga,
            #                 won_stats=ungettext('{count} won opportunity',
            #                                     '{count} won opportunities',
            #                                     won_count
            #                                    ).format(count=won_count),
            #                 lost_stats=ungettext('{count} lost opportunity',
            #                                      '{count} lost opportunities',
            #                                      lost_count
            #                                     ).format(count=lost_count),
            #             )
            #         )
            # TODO: query by chunks if there are lots of managed Organisation ?
            mngd_orgas = [*self.orga_model.objects.filter_managed_by_creme()]
            mngd_orga_ids = [o.id for o in mngd_orgas]

            agg_kwargs = {}
            for orga_id in mngd_orga_ids:
                agg_kwargs[f'won_{orga_id}'] = Count(
                    'relations_w_orga__object_entity_id',
                    filter=Q(
                        relations_w_orga__object_entity=orga_id,
                        sales_phase__won=True,
                    ),
                )
                agg_kwargs[f'lost_{orga_id}'] = Count(
                    'relations_w_orga__object_entity_id',
                    filter=Q(
                        relations_w_orga__object_entity=orga_id,
                        sales_phase__lost=True,
                    ),
                )

            agg = opp_model.objects.annotate(
                relations_w_orga=FilteredRelation(
                    'relations',
                    condition=Q(relations__object_entity_id__in=mngd_orga_ids),
                ),
            ).filter(
                relations_w_orga__type_id=self.relation_type_id,
                closing_date__gte=date.today().replace(month=1, day=1),
            ).aggregate(**agg_kwargs)

            for orga in mngd_orgas:
                orga_id = orga.id
                won_count = agg[f'won_{orga_id}']
                lost_count = agg[f'lost_{orga_id}']

                if won_count or lost_count:
                    stats.append(
                        self.message_format.format(
                            organisation=orga,
                            won_stats=ngettext(
                                '{count} won opportunity',
                                '{count} won opportunities',
                                won_count
                            ).format(count=won_count),
                            lost_stats=ngettext(
                                '{count} lost opportunity',
                                '{count} lost opportunities',
                                lost_count,
                            ).format(count=lost_count),
                        )
                    )

        return stats
