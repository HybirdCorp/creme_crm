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

from django.db.models.signals import post_save

from billing.models import Quote

from opportunities.constants import REL_SUB_CURRENT_DOC


def update_estimated_sales(sender, instance, **kwargs):
    relations = instance.get_relations(REL_SUB_CURRENT_DOC, True)
    for rel in relations:
        opp = rel.object_entity.get_real_entity()
        if opp.use_current_quote:
            opp.update_estimated_sales(instance)

def connect_to_signals():
    # Adding "current" feature to other billing document (sales order, invoice) does not really make sense.
    # If one day it does we will only have to add senders to the signal
    post_save.connect(update_estimated_sales, sender=Quote)