# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

import logging

from django.db import IntegrityError
from django.db.transaction import atomic

from .models import SimpleBillingAlgo
from .registry import Algo

logger = logging.getLogger(__name__)


class SimpleAlgo(Algo):
    def generate_number(self, organisation, ct, *args, **kwargs):
        # We cannot use F() to increment the number,
        # because it's return the number of lines, not the lines themselves
        # ( & we need the line to get the incremented value without race condition)
        while True:
            old_conf = SimpleBillingAlgo.objects.filter(
                organisation=organisation, ct=ct,
            ).order_by('-last_number')[0]
            conf = SimpleBillingAlgo(
                organisation=old_conf.organisation,
                ct=old_conf.ct,
                prefix=old_conf.prefix,
                last_number=old_conf.last_number + 1,
            )

            try:
                with atomic():
                    # Remember the <unique_together = ("organisation", "last_number", "ct")>
                    # in SimpleBillingAlgo.Meta
                    conf.save(force_insert=True)
                    SimpleBillingAlgo.objects.filter(pk=old_conf.id).delete()
            except IntegrityError as e:  # Problem with the 'unique_together' constraint
                logger.debug('SimpleAlgo.generate_number() (save new conf): %s', e)
                continue

            return conf.prefix + str(conf.last_number)
