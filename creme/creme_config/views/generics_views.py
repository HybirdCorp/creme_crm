# -*- coding: utf-8 -*-

from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required

from creme_core.constants  import DROIT_MODULE_EST_ADMIN
from creme_core.entities_access.functions_for_permissions import get_view_or_die
from creme_core.views.generic import add_entity

from creme_config.registry import config_registry
from creme_config.blocks import generic_models_block


def _get_modelconf(app_name, model_name):
    try:
        app_config = config_registry.get_app(app_name)
    except KeyError:
        raise Http404

    #TODO: use only ct instead of model_name ???
    for modelconf in app_config.models():
        if modelconf.name_in_url == model_name:
            return modelconf

    raise Http404

def _get_model_portal_url(app_name, model_name):
    return '/creme_config/%s/%s/portal/' % (app_name, model_name)

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def add_model(request, app_name, model_name):
    """
        @Permissions : Admin to creme_config app
    """
    return add_entity(request,
                      _get_modelconf(app_name, model_name).model_form,
                      _get_model_portal_url(app_name, model_name),
                      'creme_core/generics/form/add.html')

@login_required
@get_view_or_die('creme_config')
def portal_model(request, app_name, model_name):
    """
        @Permissions : Acces OR Admin to creme_config app
    """
    model = _get_modelconf(app_name, model_name).model

    return render_to_response('creme_config/generics/model_portal.html',
                             {
                              'model':      model,
                              'app_name':   app_name,
                              'model_name': model_name,
                             },
                             context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
#def delete_model(request, app_name, model_name, object_id):
def delete_model(request, app_name, model_name):
    """
        @Permissions : Admin to creme_config app
    """
    model = _get_modelconf(app_name, model_name).model

#    object = get_object_or_404(model, pk=object_id)
    object = get_object_or_404(model, pk=request.POST.get('id'))
    object.delete()

#    return HttpResponseRedirect(_get_model_portal_url(app_name, model_name))
    return HttpResponse()

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def edit_model(request, app_name, model_name, object_id):
    """
        @Permissions : Admin to creme_config app
    """
    modelconf = _get_modelconf(app_name, model_name)
    model_form = modelconf.model_form

    object = get_object_or_404(modelconf.model, pk=object_id)

    if request.POST:
        object_form = model_form(request.POST, instance=object)

        if object_form.is_valid():
            object_form.save()
            return HttpResponseRedirect(_get_model_portal_url(app_name, model_name))
    else:
        object_form = model_form(instance=object)

    return render_to_response('creme_core/generics/form/edit.html',
                              {'form': object_form},
                              context_instance=RequestContext(request))


@login_required
@get_view_or_die('creme_config')
def portal_app(request, app_name):
    """
        @Permissions : Acces OR Admin to creme_config app
    """
    return render_to_response('creme_config/generics/app_portal.html',
                              {
                                'app_name':   app_name,
                                'app_config': list(config_registry.get_app(app_name).models()), #list-> have the length in the template
                              },
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config')
def reload_block(request, ct_id):
    return generic_models_block.detailview_ajax(request, ct_id)
