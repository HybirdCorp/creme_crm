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
from decimal import Decimal, InvalidOperation

from django.utils.formats import number_format
from django.utils.translation import gettext as _

from creme.persons import get_address_model

from .constants import ROUND_POLICY

logger = logging.getLogger(__name__)


def round_to_2(decimal_instance):
    try:
        return Decimal(decimal_instance).quantize(Decimal('.01'), rounding=ROUND_POLICY)
    except InvalidOperation as e:
        logger.debug('round_to_2: InvalidOperation : %s', e)
        return Decimal()


def print_discount(entity, fval, user, field):
    # TODO: print 'None' only on detail views => we need this info in printers
    return _('{} %').format(number_format(fval, use_l10n=True))


# TODO: move to persons ??
def copy_or_create_address(address, owner, name):
    if address is None:
        name = str(name)
        return get_address_model().objects.create(name=name, owner=owner, address=name)

    return address.clone(owner)
