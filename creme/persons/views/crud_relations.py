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
from django.contrib.auth.decorators import login_required

from creme_core.models import CremeEntity, Relation, RelationType

from persons.constants import REL_SUB_CUSTOMER_OF, REL_SUB_PROSPECT, REL_SUB_SUSPECT, REL_SUB_INACTIVE, REL_SUB_SUPPLIER
from persons.models import Organisation


#TODO: generalise and move to creme_core ??
@login_required
def _link(request, entity_id, relation_type_id, mngd_orga_id):
    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()

    relation_type = get_object_or_404(RelationType, pk=relation_type_id)
    managed_orga  = get_object_or_404(Organisation, pk=mngd_orga_id)

    if not relation_type.subject_ctypes.filter(id=entity.entity_type_id)[:1]:
        raise Http404('Imcompatible relation type') #bof bof

    Relation.create_relation_with_object(entity, relation_type_id, managed_orga)

    return HttpResponseRedirect(entity.get_absolute_url())

def become_customer(request, entity_id, mngd_orga_id):
    return _link(request, entity_id, REL_SUB_CUSTOMER_OF, mngd_orga_id)

def become_prospect(request, entity_id, mngd_orga_id):
    return _link(request, entity_id, REL_SUB_PROSPECT, mngd_orga_id)

def become_suspect(request, entity_id, mngd_orga_id):
    return _link(request, entity_id, REL_SUB_SUSPECT, mngd_orga_id)

def become_inactive(request, entity_id, mngd_orga_id):
    return _link(request, entity_id, REL_SUB_INACTIVE, mngd_orga_id)

def become_supplier(request, entity_id, mngd_orga_id):
    return _link(request, entity_id, REL_SUB_SUPPLIER, mngd_orga_id)
