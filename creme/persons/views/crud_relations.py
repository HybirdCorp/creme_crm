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

import logging

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404  # redirect

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import CremeEntity, Relation, RelationType
from creme.creme_core.utils import get_from_POST_or_404

from .. import get_organisation_model, constants

logger = logging.getLogger(__name__)


# TODO: generalise and move to creme_core ??
@login_required
@permission_required('persons')
def _link(request, entity_id, relation_type_id):
    managed_orga  = get_object_or_404(get_organisation_model(),
                                      pk=get_from_POST_or_404(request.POST, 'id', int),
                                     )
    entity        = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()
    relation_type = get_object_or_404(RelationType, pk=relation_type_id)
    user = request.user

    # TODO: in a Relation type method() ??
    if not relation_type.subject_ctypes.filter(id=entity.entity_type_id).exists():
        raise Http404('Incompatible relation type for subject')  # TODO: ConflictError

    # TODO: in a Relation type method() ??
    if not relation_type.object_ctypes.filter(id=managed_orga.entity_type_id).exists():
        raise Http404('Incompatible relation type for object')  # TODO: ConflictError

    has_perm_or_die = user.has_perm_to_link_or_die
    has_perm_or_die(entity)
    has_perm_or_die(managed_orga)

    try:
        Relation.objects.get_or_create(subject_entity=entity, type_id=relation_type_id,
                                       object_entity=managed_orga,
                                       defaults={'user': user},
                                      )
    except Relation.MultipleObjectsReturned:
        logger.warning('_link(): duplicated Relation <subject=%s type=%s object=%s>',
                       entity.id, relation_type_id, managed_orga.id,
                      )

    # return redirect(entity)
    return HttpResponse()


def become_customer(request, entity_id):
    return _link(request, entity_id, constants.REL_SUB_CUSTOMER_SUPPLIER)


def become_prospect(request, entity_id):
    return _link(request, entity_id, constants.REL_SUB_PROSPECT)


def become_suspect(request, entity_id):
    return _link(request, entity_id, constants.REL_SUB_SUSPECT)


def become_inactive(request, entity_id):
    return _link(request, entity_id, constants.REL_SUB_INACTIVE)


def become_supplier(request, entity_id):
    return _link(request, entity_id, constants.REL_OBJ_CUSTOMER_SUPPLIER)
