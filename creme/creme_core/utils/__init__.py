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

from logging import debug

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.query_utils import Q
from django.http import HttpResponse, Http404

from django.utils.simplejson import JSONEncoder

from creme_core.registry import creme_registry


def creme_entity_content_types():
    get_for_model = ContentType.objects.get_for_model
    return (get_for_model(model) for model in creme_registry.iter_entity_models())

def Q_creme_entity_content_types():
    return ContentType.objects.filter(pk__in=[ct_model.pk for ct_model in creme_entity_content_types()])

def get_ct_or_404(ct_id):
    try:
        ct = ContentType.objects.get_for_id(ct_id)
    except ContentType.DoesNotExist:
        raise Http404('No content type with this id: %s' % ct_id)

    return ct

def create_or_update_models_instance(model, pk=None, **kwargs):
    if pk is not None:
        try:
            instance = model.objects.get(pk=pk)
        except ObjectDoesNotExist:
            instance = model(id=pk)
    else:
        instance = model()

    for key, args in kwargs.iteritems():
        instance.__dict__[key] = args

    instance.save()

    return instance

#TODO: Use DjangoJSONEncoder ?
def jsonify(func): ##
    def _aux(*args, **kwargs):
        rendered = func(*args, **kwargs)
        return HttpResponse(JSONEncoder().encode(rendered), mimetype="text/javascript")
    return _aux

def get_from_GET_or_404(GET, key):
    try:
        return GET[key]
    except KeyError:
        raise Http404('No GET argument with this key: %s' % key)

def get_from_POST_or_404(POST, key):
    try:
        return POST[key]
    except KeyError:
        raise Http404('No POST argument with this key: %s' % key)
