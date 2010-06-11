# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from billing.models import SimpleBillingAlgo
from billing.registry import Algo


class SimpleAlgo(Algo):
    def generate_number(self, organisation, ct, *args, **kwargs):
        config_algo = SimpleBillingAlgo.objects.filter(organisation=organisation, ct=ct)[:1]

        if config_algo:
            conf = config_algo[0]
            conf.last_number += 1
        else:
            conf = SimpleBillingAlgo()
            conf.organisation = organisation
            conf.ct = ct
            conf.last_number = 1

        last_number = conf.prefix + str(conf.last_number)
        conf.save()

        return last_number
