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

from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.models import CremeEntity, Relation, RelationType
from creme_core.utils import get_from_POST_or_404

from persons.constants import REL_SUB_CUSTOMER_OF, REL_SUB_PROSPECT, REL_SUB_SUSPECT, REL_SUB_INACTIVE, REL_SUB_SUPPLIER
from persons.models import Organisation


#TODO: credentials ??
#TODO: generalise and move to creme_core ??
@login_required
@permission_required('persons')
def _link(request, entity_id, relation_type_id):
    mngd_orga_id = get_from_POST_or_404(request.POST, 'id', int)

    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()

    relation_type = get_object_or_404(RelationType, pk=relation_type_id)
    managed_orga  = get_object_or_404(Organisation, pk=mngd_orga_id)

    if not relation_type.subject_ctypes.filter(id=entity.entity_type_id).exists(): #TODO: in a Relation type method() ??
        raise Http404('Incompatible relation type') #bof bof

    Relation.create(entity, relation_type_id, managed_orga)

    return HttpResponseRedirect(entity.get_absolute_url())

def become_customer(request, entity_id):
    return _link(request, entity_id, REL_SUB_CUSTOMER_OF)

def become_prospect(request, entity_id):
    return _link(request, entity_id, REL_SUB_PROSPECT)

def become_suspect(request, entity_id):
    return _link(request, entity_id, REL_SUB_SUSPECT)

def become_inactive(request, entity_id):
    return _link(request, entity_id, REL_SUB_INACTIVE)

def become_supplier(request, entity_id):
    return _link(request, entity_id, REL_SUB_SUPPLIER)
