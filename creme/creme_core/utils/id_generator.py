################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
from collections.abc import Sequence
from random import randint

from django.db import IntegrityError
from django.db.models import CharField, Model
from django.db.transaction import atomic

logger = logging.getLogger(__name__)


# TODO: you should avoid to use this function, and use a classical integer ID + a UUIDField
def generate_string_id_and_save(model: type[Model],
                                objects: Sequence[Model],
                                prefix: str,
                                ) -> None:
    if not objects:
        return

    assert not prefix[-1].isdigit()

    pk_field = model._meta.pk
    assert isinstance(pk_field, CharField)

    # NB: the generated number must fit in the field, & 64bits number should be ok
    max_value = min(2**64, 10**(pk_field.max_length - len(prefix)) - 1)
    last_exception: BaseException = RuntimeError('No previous error ?!')

    for obj in objects:
        for _i in range(100):  # Avoid infinite loop
            obj.pk = f'{prefix}{randint(0, max_value)}'

            try:
                # We use transaction because the IntegrityError aborts the
                # current transaction on PGSQL
                with atomic():
                    obj.save(force_insert=True)
            except IntegrityError as e:  # An object with this id already exists
                # TODO: indeed it can be raise if the given object is badly built
                logger.debug(
                    'generate_string_id_and_save(): pk "%s" already exists ? (%s)',
                    obj.pk, e,
                )
                last_exception = e
                obj.pk = None
            else:
                break
        else:
            raise last_exception
