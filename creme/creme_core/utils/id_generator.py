# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from typing import Sequence, Type

from django.db import IntegrityError
from django.db.models import Model
from django.db.transaction import atomic

logger = logging.getLogger(__name__)


def generate_string_id_and_save(model: Type[Model],
                                objects: Sequence[Model],
                                prefix: str) -> None:
    if not objects:
        return

    assert not prefix[-1].isdigit()

    prefix_len = len(prefix)
    # TODO: query with regex instead ?
    id_list = [
        int(suffix)
        for suffix in (
            id_str[prefix_len:]
            for id_str in model.objects.filter(id__startswith=prefix).values_list('id', flat=True)
        )
        if suffix.isdigit()
    ]
    # TODO: do-able in SQL ????
    # TODO: would it be cool to fill the 'holes' in id ranges ???
    index = max(id_list, default=0)
    last_exception: BaseException = RuntimeError('No previous error ?!')

    for obj in objects:
        for i in range(1000):  # Avoid infinite loop
            index += 1
            obj.id = prefix + str(index)

            try:
                # We use transaction because the IntegrityError aborts the
                # current transaction on PGSQL
                with atomic():
                    obj.save(force_insert=True)
            except IntegrityError as e:  # An object with this id already exists
                # TODO: indeed it can be raise if the given object if badly build....
                #       --> improve this (detect the guilty column) ?
                logger.debug(
                    'generate_string_id_and_save(): id "%s" already exists ? (%s)',
                    obj.id, e,
                )
                last_exception = e
                obj.pk = None
            else:
                break
        else:
            raise last_exception
