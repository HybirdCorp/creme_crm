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
import re
# import warnings

from django.apps import apps
from django.urls import reverse
from django.db.models import FieldDoesNotExist
from django.forms.models import modelform_factory

from creme.creme_core.core.setting_key import setting_key_registry
from creme.creme_core.forms import CremeModelForm
from creme.creme_core.gui.bricks import brick_registry
from creme.creme_core.utils.imports import import_apps_sub_modules

# from creme.creme_config.utils import generate_portal_url


logger = logging.getLogger(__name__)


class NotRegisteredInConfig(Exception):
    pass


class ModelConfig(object):
    _SHORT_NAME_RE = re.compile(r'^\w+$')

    def __init__(self, model, name_in_url, form_class=None):
        if not self._SHORT_NAME_RE.match(name_in_url):
            raise ValueError('The argument "name_in_url" should only contain alphanumeric characters or _')

        self.model = model
        self.name_in_url = name_in_url
        self._form_class = form_class

    @property
    def model_form(self):
        if self._form_class is None:
            model = self.model
            get_field = model._meta.get_field

            try:
                get_field('is_custom')
            except FieldDoesNotExist:
                exclude = None
            else:
                exclude = ('is_custom',)

            self._form_class = modelform_factory(model, form=CremeModelForm, exclude=exclude)

        return self._form_class

    @property
    def verbose_name(self):
        return self.model._meta.verbose_name


# TODO: __slots__ ???
class AppConfigRegistry(object):
    def __init__(self, name, verbose_name):
        self.name = name
        self.verbose_name = verbose_name
        self._models = {}
        self._excluded_models = set()
        self._bricks_classes = []

    @property
    def portal_url(self):
        # return generate_portal_url(self.name)
        return reverse('creme_config__app_portal', args=(self.name,))

    def register_model(self, model, model_name_in_url, form_class=None):
        # NB: the key is the model & not the ContentType.id, because these IDs
        #     are not always consistent with the test-models.
        if model not in self._excluded_models:
            self._models[model] = ModelConfig(model, model_name_in_url, form_class)

        return self

    def get_model_conf(self, model):
        model_conf = self._models.get(model)

        if model_conf is None:
            raise NotRegisteredInConfig('Model {} is not registered'.format(model))

        return model_conf

    def models(self):
        return self._models.itervalues()

    def register_brick(self, brick_cls):
        self._bricks_classes.append(brick_cls)

    def unregister_model(self, model):
        self._models.pop(model, None)
        self._excluded_models.add(model)

    @property
    def bricks(self):
        for brick_cls in self._bricks_classes:
            yield brick_cls()


class _ConfigRegistry(object):
    def __init__(self, block_registry=brick_registry):
        self._brick_registry = block_registry
        self._apps = _apps = {}
        self._user_brick_classes = []
        self._portal_brick_classes = []

        # Add an app to creme_config if it has at least a visible SettingKey
        # (to be sure that even app without registered models appear)
        for app_label in {skey.app_label for skey in setting_key_registry if not skey.hidden}:
            _apps[app_label] = self._build_app_conf_registry(self._get_app_name(app_label))

    def _build_app_conf_registry(self, app_name):
        return AppConfigRegistry(app_name, apps.get_app_config(app_name).verbose_name)

    def get_app(self, app_label):
        return self._apps[self._get_app_name(app_label)]

    def _get_app_name(self, app_label):
        """app_label is the key of the app in django apps registry
        app_name corresponds to the app_label for an app, excepted when this app
        'extends' (see creme_registry) another app. In this case, the app_name
        is the app_label of the extended app.
        So we get only one AppConfigRegistry for an app & all its extending apps.
        """
        ext_app_name = apps.get_app_config(app_label).extended_app

        if ext_app_name is not None:
            for app_config in apps.app_configs.itervalues():
                if app_config.name == ext_app_name:
                    return app_config.label

        return app_label

    def register(self, *to_register):
        """
        @param to_register: Sequence of tuples (DjangoModel, short_name_for_url [, ModelForm])
        """
        app_registries = self._apps

        for args in to_register:
            app_name = self._get_app_name(args[0]._meta.app_label)
            app_conf = app_registries.get(app_name)

            if app_conf is None:
                app_registries[app_name] = app_conf = self._build_app_conf_registry(app_name)

            app_conf.register_model(*args)

    def apps(self):
        return self._apps.itervalues()

    def register_bricks(self, *bricks_to_register):  # TODO: factorise with register()
        app_registries = self._apps

        for app_label, brick_cls in bricks_to_register:
            assert hasattr(brick_cls, 'detailview_display'), \
                  'brick with id="{}" has no detailview_display() method'.format(brick_cls.id_)
            # TODO: need a method is_registered() ?
            assert brick_cls.id_ in self._brick_registry._brick_classes, \
                   'brick with id="{}" is not registered'.format(brick_cls.id_)

            app_name = self._get_app_name(app_label)
            app_conf = app_registries.get(app_name)

            if app_conf is None:
                app_registries[app_name] = app_conf = self._build_app_conf_registry(app_name)

            app_conf.register_brick(brick_cls)

    def register_portal_bricks(self, *bricks_to_register):
        for brick_cls in bricks_to_register:
            assert hasattr(brick_cls, 'detailview_display'), \
                   'brick with id="{}" has no detailview_display() method'.format(brick_cls.id_)
            assert brick_cls.id_ in self._brick_registry._brick_classes, \
                   'brick with id="{}" is not registered'.format(brick_cls.id_)

        self._portal_brick_classes.extend(bricks_to_register)

    def register_user_bricks(self, *bricks_to_register):
        for brick_cls in bricks_to_register:
            assert hasattr(brick_cls, 'detailview_display'), \
                   'brick with id="{}" has no detailview_display() method'.format(brick_cls.id_)
            assert brick_cls.id_ in self._brick_registry._brick_classes, \
                   'brick with id="{}" is not registered'.format(brick_cls.id_)

            self._user_brick_classes.append(brick_cls)

    def unregister(self, *to_unregister):  # TODO: factorise with register()
        """
        @param to_unregister: Sequence of DjangoModels.
        """
        app_registries = self._apps

        for model in to_unregister:
            app_name = self._get_app_name(model._meta.app_label)
            app_conf = app_registries.get(app_name)

            if app_conf is None:
                app_registries[app_name] = app_conf = self._build_app_conf_registry(app_name)

            app_conf.unregister_model(model)

    @property
    def portal_bricks(self):
        for brick_cls in self._portal_brick_classes:
            yield brick_cls()

    @property
    def user_bricks(self):
        for brick_cls in self._user_brick_classes:
            yield brick_cls()

    def get_model_creation_info(self, model, user):
        app_name = model._meta.app_label
        allowed = user.has_perm_to_admin(app_name)
        url = None

        try:
            model_name = self.get_app(app_name)\
                             .get_model_conf(model=model) \
                             .name_in_url
        except (KeyError, NotRegisteredInConfig):
            allowed = False
        else:
            url = reverse('creme_config__create_instance_from_widget', args=(app_name, model_name))

        return url, allowed


config_registry = _ConfigRegistry()

logger.debug('creme_config: populate registry')

for config_import in import_apps_sub_modules('creme_config_register'):
    config_registry.register(*getattr(config_import, 'to_register', ()))
    config_registry.unregister(*getattr(config_import, 'to_unregister', ()))
    config_registry.register_bricks(*getattr(config_import, 'blocks_to_register', ()))  # TODO: rename 'bricks'
    config_registry.register_user_bricks(*getattr(config_import, 'userblocks_to_register', ()))  # TODO: rename 'userbricks_to_register'
    config_registry.register_portal_bricks(*getattr(config_import, 'portalbricks_to_register', ()))
