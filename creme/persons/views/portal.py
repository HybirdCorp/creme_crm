# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from creme_core.views.generic import app_portal
#from creme_core.models import Relation

from creme_config.utils import generate_portal_url

from persons.models import Contact, Organisation
from persons.constants import REL_OBJ_CUSTOMER_SUPPLIER #REL_SUB_CUSTOMER_OF


def portal(request):
    stats = [
                (_('Number of contacts'),      Contact.objects.count()),
                (_("Number of organisations"), Organisation.objects.count()),
            ]

    #relations_qs = Relation.objects.filter(type__id=REL_SUB_CUSTOMER_OF, is_deleted=False)
    #for managed_orga in Organisation.get_all_managed_by_creme():
        ##TODO: le calcul est-il juste ?? (genre si un contact client fait parti d'une organisation cliente --> cumule ou pas ??)
        #customers_count = relations_qs.filter(object_entity=managed_orga).count()
        #stats.append((_(u'Number of customers of %s') % managed_orga, customers_count))

    customers_stats = Organisation.get_all_managed_by_creme() \
                                  .filter(relations__type=REL_OBJ_CUSTOMER_SUPPLIER) \
                                  .annotate(customers_count=Count('relations')) \
                                  .values_list('name', 'customers_count')
    if customers_stats:
        label = _(u'Number of customers of %s')
        stats.extend((label % orga_name, customers_count) for orga_name, customers_count in customers_stats)

    return app_portal(request, 'persons', 'persons/portal.html', (Contact, Organisation),
                      stats, config_url=generate_portal_url('persons'))
