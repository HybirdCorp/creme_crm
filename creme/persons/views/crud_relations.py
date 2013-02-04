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

from persons.constants import REL_SUB_CUSTOMER_SUPPLIER, REL_SUB_PROSPECT, REL_SUB_SUSPECT, REL_SUB_INACTIVE, REL_OBJ_CUSTOMER_SUPPLIER
from persons.models import Organisation


#TODO: generalise and move to creme_core ??
@login_required
@permission_required('persons')
def _link(request, entity_id, relation_type_id):
    managed_orga  = get_object_or_404(Organisation, pk=get_from_POST_or_404(request.POST, 'id', int))
    entity        = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()
    relation_type = get_object_or_404(RelationType, pk=relation_type_id)
    user = request.user

    if not relation_type.subject_ctypes.filter(id=entity.entity_type_id).exists(): #TODO: in a Relation type method() ??
        raise Http404('Incompatible relation type for subject') #bof bof

    if not relation_type.object_ctypes.filter(id=managed_orga.entity_type_id).exists(): #TODO: in a Relation type method() ??
        raise Http404('Incompatible relation type for object') #bof bof

    #CremeEntity.populate_credentials([entity, managed_orga], user) #optimisation
    entity.can_link_or_die(user)
    managed_orga.can_link_or_die(user)

    Relation.objects.create(subject_entity=entity, type_id=relation_type_id,
                            object_entity=managed_orga, user=user,
                           )

    return HttpResponseRedirect(entity.get_absolute_url())

def become_customer(request, entity_id):
    return _link(request, entity_id, REL_SUB_CUSTOMER_SUPPLIER)

def become_prospect(request, entity_id):
    return _link(request, entity_id, REL_SUB_PROSPECT)

def become_suspect(request, entity_id):
    return _link(request, entity_id, REL_SUB_SUSPECT)

def become_inactive(request, entity_id):
    return _link(request, entity_id, REL_SUB_INACTIVE)

def become_supplier(request, entity_id):
    return _link(request, entity_id, REL_OBJ_CUSTOMER_SUPPLIER)
