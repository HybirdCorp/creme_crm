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

import logging

from django.db.models import FieldDoesNotExist, IntegerField
from django.db.models.deletion import ProtectedError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import bricks as bricks_views, generic
from creme.creme_core.views.decorators import jsonify
from creme.creme_core.views.generic.order import ReorderInstances
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


class AppRegistryMixin:
    app_name_url_kwarg = 'app_name'

    def get_app_registry(self):
        try:
            app_registry = getattr(self, 'app_registry')
        except AttributeError:
            self.app_registry = app_registry = _get_appconf(
                user=self.request.user,
                app_name=self.kwargs[self.app_name_url_kwarg],
            )

        return app_registry


class ModelConfMixin(AppRegistryMixin):
    model_name_url_kwarg = 'model_name'

    def get_model_conf(self):
        try:
            mconf = getattr(self, 'model_conf')
        except AttributeError:
            self.model_conf = mconf = \
                _get_modelconf(app_config=self.get_app_registry(),
                               model_name=self.kwargs[self.model_name_url_kwarg],
                              )

        return mconf


class GenericCreation(ModelConfMixin, generic.CremeModelCreationPopup):
    template_name = 'creme_core/generics/form/add-popup.html'
    submit_label = _('Save')

    def get_form_class(self):
        return self.get_model_conf().model_form

    def get_title(self):
        model = self.get_model_conf().model
        title = getattr(model, 'creation_label', None)

        return title if title is not None else \
               ugettext('New value: {model}').format(model=model._meta.verbose_name)

    def get_submit_label(self):
        return getattr(self.get_model_conf().model, 'save_label', None) or \
               super().get_submit_label()


class FromWidgetCreation(GenericCreation):
    def form_valid(self, form):
        super().form_valid(form=form)

        return json_update_from_widget_response(
            form.update_from_widget_response_data()
            if callable(getattr(form, 'update_from_widget_response_data', None)) else
            form.instance
        )


class ModelPortal(ModelConfMixin, generic.BricksView):
    template_name = 'creme_config/generics/model-portal.html'

    def fix_orders(self):
        model = self.get_model_conf().model
        meta = model._meta

        try:
            order_field = meta.get_field('order')
        except FieldDoesNotExist:
            pass
        else:
            ordering = meta.ordering

            if ordering and ordering[0] == 'order' and \
               isinstance(order_field, IntegerField):
                for order, instance in enumerate(model._default_manager
                                                      .order_by('order', 'pk'),
                                                 start=1):
                    if order != instance.order:
                        logger.warning('Fix an order problem in model %s (%s)',
                                       model, instance
                                      )
                        instance.order = order
                        instance.save(force_update=True, update_fields=('order',))

    def get_bricks(self):
        model_conf = self.get_model_conf()

        return [
            GenericModelBrick(app_name=self.get_app_registry().name,
                              model_name=model_conf.name_in_url,
                              model=model_conf.model,
                             ),
        ]

    def get_bricks_reload_url(self):
        return reverse('creme_config__reload_model_brick',
                       args=(self.get_app_registry().name,
                             self.get_model_conf().name_in_url,
                            ),
                      )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        self.fix_orders()

        app_registry = self.get_app_registry()
        model_conf = self.get_model_conf()

        context['model'] = model_conf.model
        context['app_name'] = app_registry.name
        context['app_verbose_name'] = app_registry.verbose_name

        return context


@login_required
def delete_model(request, app_name, model_name):
    model = _get_modelconf(_get_appconf(request.user, app_name), model_name).model
    instance = get_object_or_404(model, pk=get_from_POST_or_404(request.POST, 'id'))

    if not getattr(instance, 'is_custom', True):
        raise Http404('Can not delete (is not custom)')

    try:
        instance.delete()
    except ProtectedError as e:
        msg = ugettext('{} can not be deleted because of its dependencies.').format(instance)

        # TODO: factorise ??
        if request.is_ajax():
            return HttpResponse(msg, status=400)

        raise Http404(msg) from e

    return HttpResponse()


class GenericEdition(ModelConfMixin, generic.CremeModelEditionPopup):
    template_name = 'creme_core/generics/form/edit-popup.html'

    def get_form_class(self):
        return self.get_model_conf().model_form

    def get_queryset(self):
        return self.get_model_conf().model._default_manager.all()


class Reorder(ModelConfMixin, ReorderInstances):
    def get_queryset(self):
        return self.get_model_conf().model._default_manager.all()


class AppPortal(AppRegistryMixin, generic.BricksView):
    template_name = 'creme_config/generics/app-portal.html'

    def get_bricks(self):
        return list(self.get_app_registry().bricks)  # Get config registered bricks

    def get_bricks_reload_url(self):
        return reverse('creme_config__reload_app_bricks',
                       args=(self.get_app_registry().name,),
                      )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        app_registry = self.get_app_registry()
        context['app_name'] = app_registry.name
        context['app_verbose_name'] = app_registry.verbose_name
        context['app_config'] = list(app_registry.models())  # list-> have the length in the template

        return context


@login_required
@jsonify
def reload_model_brick(request, app_name, model_name):
    user = request.user
    app_registry = _get_appconf(user, app_name)
    model = _get_modelconf(app_registry, model_name).model

    user.has_perm_to_admin_or_die(app_name)

    return bricks_views.bricks_render_info(
        request,
        context=bricks_views.build_context(request),
        bricks=[GenericModelBrick(app_name=app_name, model_name=model_name, model=model)],
    )


@login_required
@jsonify
def reload_app_bricks(request, app_name):
    brick_ids = bricks_views.get_brick_ids_or_404(request)
    app_registry = _get_appconf(request.user, app_name)
    bricks = []

    for b_id in brick_ids:
        if b_id == SettingsBrick.id_:
            brick = SettingsBrick()
        else:
            for registered_brick in app_registry.bricks:
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
