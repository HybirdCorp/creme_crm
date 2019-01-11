# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from creme.creme_core.models import Relation

from . import constants


def transform_target_into_prospect(source, target, user):
    """Transform the target into a source prospect. Use REL_SUB_PROSPECT for it.
    Be careful target is subject of REL_SUB_PROSPECT relation and source is
    object of relation.
    """
    Relation.objects.safe_get_or_create(
        subject_entity=target,
        type_id=constants.REL_SUB_PROSPECT,
        object_entity=source,
        user=user,
    )


def transform_target_into_customer(source, target, user):
    """Transform the target into a source customer. Use REL_SUB_CUSTOMER_SUPPLIER for it.
    Be careful target is subject of REL_SUB_CUSTOMER_SUPPLIER relation and
    source is object of relation.
    """
    Relation.objects.safe_get_or_create(
        subject_entity=target,
        type_id=constants.REL_SUB_CUSTOMER_SUPPLIER,
        object_entity=source,
        user=user,
    )
