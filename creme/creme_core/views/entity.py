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

from django.db.models import ForeignKey
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.simplejson import JSONEncoder
from django.template.loader import render_to_string
from django.template.context import RequestContext
from django.forms.models import modelform_factory
from django.core import serializers
from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required

from creme_core.models.entity import CremeEntity
from creme_core.forms import CremeEntityForm
from creme_core.utils import get_ct_or_404, jsonify
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


EXCLUDED_FIELDS = frozenset(('id', 'entity_type', 'is_deleted', 'is_actived', 'cremeentity_ptr', 'header_filter_search_field'))

@jsonify
@login_required
def get_info_fields(request, ct_id):
    ct = get_ct_or_404(ct_id)
    model = ct.model_class()

    if not issubclass(model, CremeEntity):
        raise Http404('No a CremeEntity subclass: %s' % model)

    form = modelform_factory(model, CremeEntityForm)(user=request.user)
    required_fields = [name for name, field in form.fields.iteritems() if field.required and name != 'user']

    if len(required_fields) == 1:
        required_field = required_fields[0]
        format  = _(u'%s [CREATION]')
        printer = lambda field: unicode(field.verbose_name) if field.name != required_field else \
                                format % field.verbose_name
    else:
        printer = lambda field: unicode(field.verbose_name)

    return [(field.name, printer(field)) for field in model._meta.fields if field.name not in EXCLUDED_FIELDS and not isinstance(field, ForeignKey)]
