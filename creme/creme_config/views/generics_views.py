# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

import logging  # warnings

from django.db.models import FieldDoesNotExist, IntegerField
from django.db.models.deletion import ProtectedError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.utils import get_from_POST_or_404, jsonify
from creme.creme_core.utils.db import reorder_instances
from creme.creme_core.views import bricks as bricks_views, generic
from creme.creme_core.views.decorators import POST_only
from creme.creme_core.views.utils import json_update_from_widget_response

from ..bricks import GenericModelBrick, SettingsBrick


logger = logging.getLogger(__name__)


def _get_appconf(user, app_name):  # TODO: get_appconf_or_404() ?
    from ..registry import config_registry

    user.has_perm_to_admin_or_die(app_name)

    try:
        app_config = config_registry.get_app(app_name)
    except LookupError as e:
        raise Http404('Unknown app') from e

    return app_config


def _get_modelconf(app_config, model_name):  # TODO: get_modelconf_or_404() ?
    # TODO: use only ct instead of model_name ???
    for modelconf in app_config.models():
        if modelconf.name_in_url == model_name:
            return modelconf

    raise Http404('Unknown model')


def _popup_title(model_conf):
    model = model_conf.model
    title = getattr(model, 'creation_label', None)

    return title if title is not None else _('New value: {model}').format(model=model._meta.verbose_name)


# @login_required
# def add_model(request, app_name, model_name):
#     model_conf = _get_modelconf(_get_appconf(request.user, app_name), model_name)
#
#     return generic.add_model_with_popup(request, model_conf.model_form, _popup_title(model_conf),
#                                         template='creme_core/generics/form/add_innerpopup.html',
#                                        )
class GenericCreation(generic.add.CremeModelCreationPopup):
    template_name = 'creme_core/generics/form/add_innerpopup.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_conf = None

    def get_model_conf(self):
        mconf = self.model_conf

        if mconf is None:
            self.model_conf = mconf = \
                _get_modelconf(app_config=_get_appconf(user=self.request.user,
                                                       app_name=self.kwargs['app_name'],
                                                      ),
                               model_name=self.kwargs['model_name'],
                              )

        return mconf

    def get_form_class(self):
        return self.get_model_conf().model_form

    def get_title(self):
        return _popup_title(self.get_model_conf())

    def get_submit_label(self):
        return getattr(self.get_model_conf().model, 'save_label', None) or _('Save')


@login_required
def add_model_from_widget(request, app_name, model_name):
    model_conf = _get_modelconf(_get_appconf(request.user, app_name), model_name)

    if request.method == 'GET':
        initial = request.GET.dict()
        return generic.add_model_with_popup(request, model_conf.model_form, _popup_title(model_conf),
                                            template='creme_core/generics/form/add_innerpopup.html',
                                            initial=initial
                                           )

    form = model_conf.model_form(user=request.user, data=request.POST, files=request.FILES or None)

    if not form.is_valid():
        return generic.inner_popup(request, 'creme_core/generics/form/add_innerpopup.html',
                                   {'form':  form,
                                    'title': _popup_title(model_conf),
                                   },
                                   is_valid=form.is_valid(),  # TODO: already computed -> variable
                                   reload=False,
                                   delegate_reload=True,
                                  )

    form.save()

    if callable(getattr(form, 'update_from_widget_response_data', None)):
        data = form.update_from_widget_response_data()
    else:
        data = form.instance

    return json_update_from_widget_response(data)


@login_required
def portal_model(request, app_name, model_name):
    app_config = _get_appconf(request.user, app_name)
    model      = _get_modelconf(app_config, model_name).model
    meta = model._meta

    try:
        order_field = meta.get_field('order')
    except FieldDoesNotExist:
        pass
    else:
        if meta.ordering and meta.ordering[0] == 'order' and isinstance(order_field, IntegerField):
            for order, instance in enumerate(model.objects.order_by('order', 'pk'), start=1):
                if order != instance.order:
                    logger.warning('Fix an order problem in model %s (%s)', model, instance)
                    instance.order = order
                    instance.save()

    return render(request, 'creme_config/generics/model_portal.html',
                  {'model':             model,
                   'app_name':          app_name,
                   'app_verbose_name':  app_config.verbose_name,
                   'bricks_reload_url': reverse('creme_config__reload_model_brick', args=(app_name, model_name)),
                   'model_brick':       GenericModelBrick(app_name=app_name, model_name=model_name, model=model),
                  }
                 )


@login_required
def delete_model(request, app_name, model_name):
    model = _get_modelconf(_get_appconf(request.user, app_name), model_name).model
    instance = get_object_or_404(model, pk=get_from_POST_or_404(request.POST, 'id'))

    if not getattr(instance, 'is_custom', True):
        raise Http404('Can not delete (is not custom)')

    try:
        instance.delete()
    except ProtectedError as e:
        msg = _('{} can not be deleted because of its dependencies.').format(instance)

        # TODO: factorise ??
        if request.is_ajax():
            return HttpResponse(msg, status=400)

        raise Http404(msg) from e

    return HttpResponse()


@login_required
def edit_model(request, app_name, model_name, object_id):
    modelconf = _get_modelconf(_get_appconf(request.user, app_name), model_name)

    return generic.edit_model_with_popup(request,
                                         {'pk': object_id},
                                         modelconf.model,
                                         modelconf.model_form,
                                         template='creme_core/generics/form/edit_innerpopup.html',
                                        )


@login_required
@POST_only
def reorder(request, app_name, model_name, object_id):
    new_order = get_from_POST_or_404(request.POST, 'target', int)
    model = _get_modelconf(_get_appconf(request.user, app_name), model_name).model
    instance = get_object_or_404(model, pk=object_id)

    try:
        reorder_instances(moved_instance=instance, new_order=new_order)
    except Exception as e:
        return HttpResponse(e, status=409)

    return HttpResponse()


@login_required
def portal_app(request, app_name):
    app_config = _get_appconf(request.user, app_name)

    return render(request, 'creme_config/generics/app_portal.html',
                  {'app_name':          app_name,
                   'app_verbose_name':  app_config.verbose_name,
                   'app_config':        list(app_config.models()),  # list-> have the length in the template
                   'app_config_bricks': list(app_config.bricks),  # Get config registered bricks
                   'bricks_reload_url': reverse('creme_config__reload_app_bricks', args=(app_name,)),
                  }
                 )


@login_required
@jsonify
def reload_model_brick(request, app_name, model_name):
    app_config = _get_appconf(request.user, app_name)
    model      = _get_modelconf(app_config, model_name).model

    request.user.has_perm_to_admin_or_die(app_name)

    return bricks_views.bricks_render_info(
        request,
        context=bricks_views.build_context(request),
        bricks=[GenericModelBrick(app_name=app_name, model_name=model_name, model=model)],
    )


@login_required
@jsonify
def reload_app_bricks(request, app_name):
    brick_ids = bricks_views.get_brick_ids_or_404(request)
    app_config = _get_appconf(request.user, app_name)
    bricks = []

    for b_id in brick_ids:
        if b_id == SettingsBrick.id_:
            brick = SettingsBrick()
        else:
            for registered_brick in app_config.bricks:
                if b_id == registered_brick.id_:
                    brick = registered_brick
                    break
            else:
                raise Http404('Invalid brick id "{}"'.format(b_id))

        bricks.append(brick)

    return bricks_views.bricks_render_info(
        request,
        bricks=bricks,
        context=bricks_views.build_context(request, app_name=app_name),
    )
