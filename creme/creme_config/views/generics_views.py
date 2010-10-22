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

from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import add_entity
from creme_core.utils import get_from_POST_or_404

from creme_config.registry import config_registry
from creme_config.blocks import generic_models_block


def _get_appconf(app_name):
    try:
        app_config = config_registry.get_app(app_name)
    except KeyError:
        raise Http404('Unknown app')

    return  app_config

def _get_modelconf(app_config, model_name):
    #TODO: use only ct instead of model_name ???
    for modelconf in app_config.models():
        if modelconf.name_in_url == model_name:
            return modelconf

    raise Http404('Unknown model')

def _get_model_portal_url(app_name, model_name):
    return '/creme_config/%s/%s/portal/' % (app_name, model_name)

@login_required
@permission_required('creme_config.can_admin')
def add_model(request, app_name, model_name):
    return add_entity(request,
                      _get_modelconf(_get_appconf(app_name), model_name).model_form,
                      _get_model_portal_url(app_name, model_name),
                      'creme_core/generics/form/add.html')

@login_required
@permission_required('creme_config')
def portal_model(request, app_name, model_name):
    app_config = _get_appconf(app_name)
    model      = _get_modelconf(app_config, model_name).model

    return render_to_response('creme_config/generics/model_portal.html',
                              {
                                'model':            model,
                                'app_name':         app_name,
                                'app_verbose_name': app_config.verbose_name,
                                'model_name':       model_name,
                              },
                              context_instance=RequestContext(request))

@login_required
@permission_required('creme_config.can_admin')
def delete_model(request, app_name, model_name):
    model   = _get_modelconf(_get_appconf(app_name), model_name).model
    object_ = get_object_or_404(model, pk=get_from_POST_or_404(request.POST, 'id'))

    if not getattr(object_, 'is_custom', True):
        raise Http404 #403 ??

    object_.delete()

    return HttpResponse()

@login_required
@permission_required('creme_config.can_admin')
def edit_model(request, app_name, model_name, object_id):
    modelconf  = _get_modelconf(_get_appconf(app_name), model_name)
    model_form = modelconf.model_form

    object_ = get_object_or_404(modelconf.model, pk=object_id)

    if request.POST:
        object_form = model_form(request.POST, instance=object_)

        if object_form.is_valid():
            object_form.save()
            return HttpResponseRedirect(_get_model_portal_url(app_name, model_name))
    else:
        object_form = model_form(instance=object_)

    return render_to_response('creme_core/generics/form/edit.html',
                              {'form': object_form},
                              context_instance=RequestContext(request))

@login_required
@permission_required('creme_config')
def portal_app(request, app_name):
    app_config = _get_appconf(app_name)

    return render_to_response('creme_config/generics/app_portal.html',
                              {
                                'app_name':         app_name,
                                'app_verbose_name': app_config.verbose_name,
                                'app_config':       list(app_config.models()), #list-> have the length in the template
                              },
                              context_instance=RequestContext(request))

@login_required
@permission_required('creme_config')
def reload_block(request, ct_id):
    return generic_models_block.detailview_ajax(request, ct_id)
