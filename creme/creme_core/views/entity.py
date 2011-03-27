# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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
from django.db.models.fields import FieldDoesNotExist
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.utils.simplejson import JSONEncoder
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string
from django.template.context import RequestContext
from django.core import serializers
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required

from creme_core.models import CremeEntity, EntityCredentials
from creme_core.utils import get_from_GET_or_404
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

#TODO: use jsonify ??
@login_required
def get_creme_entity_repr(request, entity_id):
    entity = get_object_or_404(CremeEntity, pk=entity_id)
    entity.can_view_or_die(request.user)

    return HttpResponse(entity.get_real_entity().get_entity_summary(), mimetype="text/javascript")

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

@login_required
def search_and_view(request):
    GET = request.GET
    model_ids = get_from_GET_or_404(GET, 'models').split(',')
    fields    = get_from_GET_or_404(GET, 'fields').split(',')
    value     = get_from_GET_or_404(GET, 'value')

    if not value: #avoid useless queries
        raise Http404(u'Void "value" arg')

    #TODO: creds.... (use apps creds too)

    models = []
    for model_id in model_ids:
        try:
            model = ContentType.objects.get_by_natural_key(*model_id.split('-')).model_class()
        except (ContentType.DoesNotExist, TypeError):
            raise Http404(u'These model does not exist: %s' % model_id)

        if issubclass(model, CremeEntity):
            models.append(model)

    if not models:
        raise Http404(u'No valid models')

    user = request.user

    for model in models:
        query = Q()

        for field in fields:
            try:
                model._meta.get_field_by_name(field)
            except FieldDoesNotExist, e:
                pass
            else:
                query |= Q(**{str(field): value})

        if query: #avoid useless query
            #found = model.objects.filter(query)[:1]
            found = EntityCredentials.filter(user, model.objects.filter(query))[:1]
            if found:
                return HttpResponseRedirect(found[0].get_absolute_url())

    raise Http404(_(u'No entity corresponding to your search was found.'))
