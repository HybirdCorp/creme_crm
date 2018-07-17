# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2018  Hybird
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

from django.db.models import Count
from django.utils.translation import ugettext as _

from .constants import REL_OBJ_CUSTOMER_SUPPLIER


class CustomersStatistics:
    def __init__(self, orga_model):
        self.orga_model = orga_model

    def __call__(self):
        data = self.orga_model.get_all_managed_by_creme() \
                              .filter(relations__type=REL_OBJ_CUSTOMER_SUPPLIER) \
                              .annotate(customers_count=Count('relations')) \
                              .values('name', 'customers_count')

        if data:
            msg = _(u'For {name}: {customers_count}')
            return [msg.format(**ctxt) for ctxt in data]

        return []
