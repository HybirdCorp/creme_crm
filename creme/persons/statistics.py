################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2025  Hybird
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
from django.utils.translation import gettext_lazy as _

from . import constants


class _RelationsStatistics:
    relation_type_id = 'persons-override_me'
    message_format = _('For {name}: {related_count}')

    def __init__(self, orga_model):
        self.orga_model = orga_model

    def __call__(self) -> list[str]:
        data = self.orga_model.objects \
                              .filter_managed_by_creme() \
                              .filter(relations__type=self.relation_type_id) \
                              .annotate(related_count=Count('relations')) \
                              .values('name', 'related_count') \
                              .order_by('name')

        if data:
            msg = str(self.message_format)
            return [msg.format(**ctxt) for ctxt in data]

        return []


class CustomersStatistics(_RelationsStatistics):
    relation_type_id = constants.REL_OBJ_CUSTOMER_SUPPLIER


class ProspectsStatistics(_RelationsStatistics):
    relation_type_id = constants.REL_OBJ_PROSPECT


class SuspectsStatistics(_RelationsStatistics):
    relation_type_id = constants.REL_OBJ_SUSPECT
