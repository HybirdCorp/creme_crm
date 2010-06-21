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

from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, CremePropertyType, CremeProperty
from creme_core.entities_access.functions_for_permissions import edit_object_or_die
from creme_core.blocks import properties_block


#login_required ???
def add_to_creme_entity(request):
    """
        @Permissions : Edit on current creme entity
    """
    post_get = request.POST.get
    entity_id    = post_get('entity')
    property_id  = post_get('property')
    callback_url = post_get('callback_url', '/')

    if entity_id and property_id:
        entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()

        die_status = edit_object_or_die(request, entity)
        if die_status:
            return die_status

        property_type = get_object_or_404(CremePropertyType, pk=property_id)
        entity_ct = entity.entity_type

        property_ = CremeProperty(type=property_type, subject_ct=entity_ct, subject_id=entity.pk)
        property_.save()

    return HttpResponseRedirect(callback_url)

def list_for_entity_ct(request, creme_entity_id):
    """
        @Permissions : None (CremePropertyType has no user)
    """
    entity = get_object_or_404(CremeEntity, pk=creme_entity_id)
    entity_ct = entity.entity_type
    entity = entity_ct.model_class().objects.get(pk=creme_entity_id)

    property_types = CremePropertyType.objects.filter(Q(subject_ctypes=entity_ct)|Q(subject_ctypes__isnull=True))

    return render_to_response('creme_core/properties.html',
                              {
                                'property_types': property_types,
                                'entity':         entity,
                                'callback_url':   request.REQUEST.get('callback_url')
                              },
                              context_instance=RequestContext(request))

@login_required
def delete(request):
    """
        @Permissions : Edit on property's linked object
    """
    POST = request.POST
    entity = get_object_or_404(CremeEntity, pk=POST.get('object_id')).get_real_entity()

    die_status = edit_object_or_die(request, entity)
    if die_status:
        return die_status

    property_ = get_object_or_404(CremeProperty, pk=POST.get('id'))
    property_.delete()

    return HttpResponse("")

@login_required
def reload_block(request, entity_id):
    return properties_block.detailview_ajax(request, entity_id)
