# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from itertools import chain
from logging import debug

from django.db.models import FieldDoesNotExist
from django.forms.models import modelform_factory
from django.contrib.contenttypes.models import ContentType

from creme_core.registry import creme_registry
from creme_core.forms import CremeModelForm
from creme_core.utils.imports import find_n_import

from creme_config.utils import generate_portal_url
from creme_config.models.setting import SettingKey


class NotRegisteredInConfig(Exception):
    pass


class ModelConfig(object):
    def __init__(self, model, name_in_url, form_class=None):
        self.model = model
        self.name_in_url = name_in_url
        self._form_class = form_class

    @property
    def model_form(self):
        if self._form_class is None:
            try:
                self.model._meta.get_field_by_name('is_custom')
            except FieldDoesNotExist:
                exclude = None
            else:
                exclude = ('is_custom',)

            self._form_class = modelform_factory(self.model, form=CremeModelForm, exclude=exclude)

        return self._form_class

    @property
    def verbose_name(self):
        return self.model._meta.verbose_name


#__slots__ ???
class AppConfigRegistry(object):
    def __init__(self, name, verbose_name):
        self.name = name
        self.verbose_name = verbose_name
        self._models = {}
        self._blocks = []

    @property
    def portal_url(self):
        return generate_portal_url(self.name)

    def register_model(self, model, model_name_in_url, form_class=None):
        ct_id = ContentType.objects.get_for_model(model).id
        self._models[ct_id] = ModelConfig(model, model_name_in_url, form_class)

        return self

    def get_model_conf(self, ct_id):
        model_conf = self._models.get(ct_id)

        if model_conf is None:
            raise NotRegisteredInConfig("No model registered with this id: %s" % ct_id)

        return model_conf

    def models(self):
        return self._models.itervalues()

    def register_block(self, block):
        self._blocks.append(block)

    #@property TODO
    def blocks(self):
        return self._blocks


class _ConfigRegistry(object):
    def __init__(self):
        self._apps = _apps = {}
        self._userblocks = []

        #Add app to creme_config if it has at least a visible SettingKey
        for app_label in SettingKey.objects.filter(hidden=False).values_list('app_label', flat=True).distinct():
            _apps[app_label] = AppConfigRegistry(app_label, creme_registry.get_app(app_label).verbose_name)

    def get_app(self, app_name):
        return self._apps[app_name]

    def register(self, *to_register):
        """
        @param to_register Sequence of tuple (DjangoModel, short_name_for_url [, ModelForm])
        """
        app_registries = self._apps

        for args in to_register:
            app_name = args[0]._meta.app_label
            app_conf = app_registries.get(app_name)

            if app_conf is None:
                app_registries[app_name] = app_conf = AppConfigRegistry(app_name, creme_registry.get_app(app_name).verbose_name)

            app_conf.register_model(*args)

    def apps(self):
        return self._apps.itervalues()

    def register_blocks(self, *blocks_to_register): #TODO: factorise with register()
        app_registries = self._apps

        for app_name, block in blocks_to_register:
            app_conf = app_registries.get(app_name)

            if app_conf is None:
                app_registries[app_name] = app_conf = AppConfigRegistry(app_name, creme_registry.get_app(app_name).verbose_name)

            app_conf.register_block(block)

    def register_userblocks(self, *blocks_to_register):
        self._userblocks.extend(blocks_to_register)

    @property
    def userblocks(self):
        return iter(self._userblocks)


config_registry = _ConfigRegistry()

debug('creme_config: populate registry')
for config_import in find_n_import("creme_config_register", ['to_register', 'blocks_to_register', 'userblocks_to_register']):
    config_registry.register(*getattr(config_import, "to_register", ()))
    config_registry.register_blocks(*getattr(config_import, "blocks_to_register", ()))
    config_registry.register_userblocks(*getattr(config_import, "userblocks_to_register", ()))
