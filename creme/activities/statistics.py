# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2022  Hybird
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

from dateutil.relativedelta import relativedelta
from django.utils.formats import number_format
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy

from . import constants


class AveragePerMonthStatistics:
    label = _('Activities (since one year)')
    items = [
        {
            'type_id': constants.ACTIVITYTYPE_MEETING,
            'empty': _('No meeting since one year'),
            'messages': ngettext_lazy(
                '{count} meeting per month',
                '{count} meetings per month',
            ),
            'months': 12,
        },
        {
            'type_id': constants.ACTIVITYTYPE_PHONECALL,
            'empty': _('No phone call since one year'),
            'messages': ngettext_lazy(
                '{count} phone call per month',
                '{count} phone calls per month',
            ),
            'months': 12,
        },
    ]

    def __init__(self, activity_model):
        self.activity_model = activity_model

    def _get_stat(self, item, now_value):
        months = item['months']
        count = self.activity_model .objects.filter(
            type_id=item['type_id'],
            start__gte=(
                now_value - relativedelta(months=months)
            ).replace(hour=0, minute=0),
        ).count()

        if count:
            average = count / months
            # NB: ngettext() warns if you pass a float ;
            #     is round() always the right plural rules in all languages??
            stat = (item['messages'] % round(average)).format(
                count=number_format(average, decimal_pos=1, use_l10n=True),
            )
        else:
            stat = item['empty']

        return stat

    def __call__(self):
        now_value = now()
        get_stat = self._get_stat

        return [get_stat(item, now_value) for item in self.items]
