# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist, PermissionDenied
from django.db.models import IntegerField
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.creme_jobs.deletor import _DeletorType
from creme.creme_core.models import DeletionCommand, Job, JobResult
from creme.creme_core.utils.unicode_collation import collator
from creme.creme_core.views import bricks as bricks_views
from creme.creme_core.views import generic
from creme.creme_core.views.generic.order import ReorderInstances
from creme.creme_core.views.utils import json_update_from_widget_response

from ..bricks import SettingsBrick
from ..registry import config_registry

logger = logging.getLogger(__name__)


class AppRegistryMixin:
    app_name_url_kwarg = 'app_name'
    config_registry = config_registry

    def get_app_registry(self):
        try:
            app_registry = getattr(self, 'app_registry')
        except AttributeError:
            app_name = self.kwargs[self.app_name_url_kwarg]
            self.request.user.has_perm_to_admin_or_die(app_name)

            try:
                app_registry = self.config_registry.get_app_registry(app_name)
            except LookupError as e:
                raise Http404(f'Invalid app [{e}]') from e

            self.app_registry = app_registry

        return app_registry


class ModelConfMixin(AppRegistryMixin):
    model_name_url_kwarg = 'model_name'

    def get_model_conf(self):
        try:
            mconf = getattr(self, 'model_conf')
        except AttributeError:
            model_name = self.kwargs[self.model_name_url_kwarg]

            for modelconf in self.get_app_registry().models():
                if modelconf.model_name == model_name:
                    self.model_conf = mconf = modelconf
                    break
            else:
                raise Http404('Unknown model')

        return mconf


class GenericCreation(ModelConfMixin, generic.CremeModelCreationPopup):
    template_name = 'creme_core/generics/form/add-popup.html'
    submit_label = _('Save')

    def get_form_class(self):
        creator = self.get_model_conf().creator

        if not creator.enable_func(user=self.request.user):
            raise ConflictError('This model has been disabled for creation.')

        if creator.url_name is not None:
            raise ConflictError('This model does not use this creation view.')

        return creator.form_class

    def get_title(self):
        model = self.get_model_conf().model
        title = getattr(model, 'creation_label', None)

        return (
            title
            if title is not None else
            gettext('New value: {model}').format(model=model._meta.verbose_name)
        )

    def get_submit_label(self):
        return (
            getattr(self.get_model_conf().model, 'save_label', None)
            or super().get_submit_label()
        )


class FromWidgetCreation(GenericCreation):
    def form_valid(self, form):
        super().form_valid(form=form)

        return json_update_from_widget_response(
            form.update_from_widget_response_data()
            if callable(getattr(form, 'update_from_widget_response_data', None)) else
            form.instance
        )


class GenericEdition(ModelConfMixin, generic.CremeModelEditionPopup):
    template_name = 'creme_core/generics/form/edit-popup.html'

    def get_form_class(self):
        editor = self.get_model_conf().editor

        if not editor.enable_func(instance=self.object, user=self.request.user):
            raise ConflictError('This model has been disabled for edition.')

        if editor.url_name is not None:
            raise ConflictError('This model does not use this edition view.')

        return editor.form_class

    def get_queryset(self):
        return self.get_model_conf().model._default_manager.all()


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
                for order, instance in enumerate(
                    model._default_manager.order_by('order', 'pk'),
                    start=1,
                ):
                    if order != instance.order:
                        logger.warning(
                            'Fix an order problem in model %s (%s)',
                            model, instance,
                        )
                        instance.order = order
                        instance.save(force_update=True, update_fields=('order',))

    def get_bricks(self):
        model_conf = self.get_model_conf()

        return [model_conf.get_brick()]

    def get_bricks_reload_url(self):
        return reverse(
            'creme_config__reload_model_brick',
            args=(
                self.get_app_registry().name,
                self.get_model_conf().model_name,
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


class GenericDeletion(ModelConfMixin, generic.CremeModelEditionPopup):
    template_name = 'creme_core/generics/blockform/delete-popup.html'
    job_template_name = 'creme_config/deletion-job-popup.html'

    title = _('Replace & delete «{object}»')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['help_message'] = _(
            'The deleted value can be replaced in existing entities by another value. '
            'If a field cannot be empty, you must chose a replacing value.'
        )

        return context

    def check_instance_permissions(self, instance, user):
        if not getattr(instance, 'is_custom', True):
            raise ConflictError('Can not delete (is not custom)')

        dcom = DeletionCommand.objects.filter(
            content_type=ContentType.objects.get_for_model(type(instance)),
        ).first()

        if dcom is not None:
            if dcom.job.status == Job.STATUS_OK:
                dcom.job.delete()
            else:
                # TODO: if STATUS_ERROR, show a popup with the errors ?
                raise ConflictError(
                    gettext(
                        'A deletion process for an instance of «{model}» already exists.'
                    ).format(
                        model=type(instance)._meta.verbose_name,
                    )
                )

    def get_form_class(self):
        deletor = self.get_model_conf().deletor

        if not deletor.enable_func(instance=self.object, user=self.request.user):
            raise ConflictError('This model has been disabled for deletion.')

        if deletor.url_name is not None:
            raise ConflictError('This model does not use this deletion view.')

        return deletor.form_class

    def form_valid(self, form):
        self.object = form.save()

        return render(
            request=self.request,
            template_name=self.job_template_name,
            context={'job': self.object.job},
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = None
        kwargs['instance_to_delete'] = self.object

        return kwargs

    def get_queryset(self):
        return self.get_model_conf().model._default_manager.all()


class DeletorEnd(generic.CheckedView):
    job_id_url_kwarg = 'job_id'

    def post(self, request, *args, **kwargs):
        job = get_object_or_404(
            Job,
            id=kwargs[self.job_id_url_kwarg],
            type_id=_DeletorType.id,
        )

        if job.user != request.user:
            raise PermissionDenied('You can only terminate your deletion jobs.')

        if not job.is_finished:
            raise ConflictError('A non finished job cannot be terminated.')

        jresult = JobResult.objects.filter(job=job).first()

        if jresult is not None:
            messages = jresult.messages

            raise ConflictError(
                gettext('Error. Please contact your administrator.')
                if messages is None else
                '\n'.join(messages)
            )

        job.delete()

        return HttpResponse()


class Reorder(ModelConfMixin, ReorderInstances):
    def get_queryset(self):
        return self.get_model_conf().model._default_manager.all()


class AppPortal(AppRegistryMixin, generic.BricksView):
    template_name = 'creme_config/generics/app-portal.html'

    def get_bricks(self):
        return [*self.get_app_registry().bricks]  # Get config registered bricks

    def get_bricks_reload_url(self):
        return reverse(
            'creme_config__reload_app_bricks',
            args=(self.get_app_registry().name,),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        app_registry = self.get_app_registry()
        context['app_name'] = app_registry.name
        context['app_verbose_name'] = app_registry.verbose_name
        context['app_config'] = self.get_model_configs(app_registry)

        return context

    def get_model_configs(self, app_registry):
        # NB: list -> get the length in the template
        model_configs = [*app_registry.models()]
        sort_key = collator.sort_key

        model_configs.sort(
            key=lambda model_conf: sort_key(str(model_conf.verbose_name)),
        )

        return model_configs


class ModelBrickReloading(ModelConfMixin, bricks_views.BricksReloading):
    check_bricks_permission = False

    def get_bricks(self):
        return [self.get_model_conf().get_brick()]


class AppBricksReloading(AppRegistryMixin, bricks_views.BricksReloading):
    check_bricks_permission = False

    def get_bricks(self):
        bricks = []
        app_registry = self.get_app_registry()

        for brick_id in self.get_brick_ids():
            if brick_id == SettingsBrick.id_:
                brick = SettingsBrick()
            else:
                for registered_brick in app_registry.bricks:
                    if brick_id == registered_brick.id_:
                        brick = registered_brick
                        break
                else:
                    raise Http404(f'Invalid brick id "{brick_id}"')

            bricks.append(brick)

        return bricks

    def get_bricks_context(self):
        context = super().get_bricks_context()
        context['app_name'] = self.get_app_registry().name

        return context
