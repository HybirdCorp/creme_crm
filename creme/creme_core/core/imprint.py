# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2020  Hybird
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

from datetime import timedelta
from typing import Dict, Optional, Type

# from django.db.models.functions import Now
from django.utils.timezone import now

from creme.creme_core.models import CremeEntity, Imprint


class _ImprintManager:
    class RegistrationError(Exception):
        pass

    def __init__(self):
        self._granularities: Dict[Type[CremeEntity], timedelta] = {}

    def register(self, model: Type[CremeEntity], **timedelta_kwargs) -> '_ImprintManager':
        granularity = timedelta(**timedelta_kwargs)

        if self._granularities.setdefault(model, granularity) is not granularity:
            raise self.RegistrationError(f'Duplicated imprint model: {model}')

        return self

    def get_granularity(self, model: Type[CremeEntity]) -> Optional[timedelta]:
        return self._granularities.get(model)

    def create_imprint(self, entity: CremeEntity, user) -> Optional[Imprint]:
        # NB: there can be some data race, & so create 2 lines when only 1
        #     should be better, but it's not a real issue (we could fix the data
        #     it in the brick, to avoid additional query here).
        granularity = self.get_granularity(entity.__class__)

        if (
            granularity is not None
            and not Imprint.objects.filter(
                entity=entity,
                user=user,
                # NB: date__gt=Now() - granularity
                #   => does not work on MySQL ? (PG not tested)
                date__gt=now() - granularity,
            ).exists()
        ):
            return Imprint.objects.create(entity=entity, user=user)

        return None


imprint_manager = _ImprintManager()
