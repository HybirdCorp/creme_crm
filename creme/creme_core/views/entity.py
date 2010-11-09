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

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.simplejson import JSONEncoder
from django.template.loader import render_to_string
from django.template.context import RequestContext
from django.core import serializers
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required

from creme_core.models.entity import CremeEntity
from creme_core.utils.meta import get_field_infos


#TODO: seems useless (used only by one unused js function)
#      if not: rename (url too) ; use ContentType id ; unit test as others views
@login_required
def get_entity_repr(request):
    POST = request.POST

    model = POST.get('model')
    pk    = POST.get('pk')
    field = POST.get('field')

    entity = get_object_or_404(get_object_or_404(ContentType, model=model).model_class(), pk=pk)
    entity.can_view_or_die(request.user)

    return HttpResponse(JSONEncoder().encode({field: get_field_infos(entity, field)[1]}), mimetype="text/javascript")

@login_required
def get_creme_entity_repr(request, creme_entity_id):
    entity = get_object_or_404(CremeEntity, pk=creme_entity_id).get_real_entity()
    entity.can_view_or_die(request.user)

    return HttpResponse(entity.get_entity_summary(), mimetype="text/javascript")

#TODO: seems useless (used only by one unused js function)
#      if not unit tests (+ templates todo below) ; use ContentType id
@login_required
def render_entity(request):
    POST = request.POST
    model    = POST.get('model')
    pk       = POST.get('pk')
    template = POST.get('template') #TODO: check in a list of allowed templates ??

    entity = get_object_or_404(get_object_or_404(ContentType, model=model).model_class(), pk=pk)
    entity.can_view_or_die(request.user)

    data = render_to_string(template, RequestContext(request, {'object':entity}))

    return HttpResponse(JSONEncoder().encode(data), mimetype="text/javascript")

@login_required
def get_creme_entity_as_json(request):
    POST   = request.POST
    pk     = POST.get('pk')
    fields = POST.getlist('fields') or None

    data   = []
    status = 404

    if pk:
        try:
            entity = CremeEntity.objects.get(pk=pk).get_real_entity()
        except CremeEntity.DoesNotExist:
            pass
        else:
            if entity.can_view(request.user):
                data = [entity]
                status = 200

    return HttpResponse(serializers.serialize('json', data, fields=fields), mimetype="text/javascript", status=status)
