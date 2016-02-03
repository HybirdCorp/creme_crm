# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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
# import warnings
import re

# from django.contrib.contenttypes.models import ContentType
from django.db.models import FieldDoesNotExist  # Max
from django.forms.models import modelform_factory

from creme.creme_core.core.setting_key import setting_key_registry
from creme.creme_core.forms import CremeModelForm
from creme.creme_core.gui.block import block_registry
# from creme.creme_core.models.fields import BasicAutoField
from creme.creme_core.registry import creme_registry
from creme.creme_core.utils.imports import find_n_import

from creme.creme_config.utils import generate_portal_url


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

    # @staticmethod
    # def _manage_order(form):
    #     instance = form.instance
    #
    #     if not instance.pk:
    #         aggr = instance.__class__.objects.aggregate(Max('order'))
    #         instance.order = (aggr['order__max'] or 0) + 1

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

            self._form_class = form_class = modelform_factory(model, form=CremeModelForm, exclude=exclude)

            # try:
            #     order_field = get_field('order')
            # except FieldDoesNotExist:
            #     pass
            # else:
            #     if not isinstance(order_field, BasicAutoField):
            #         warnings.warn("creme_config.registry: 'order' field should be a "
            #                       "BasicAutoField if you want to keep the auto-order feature.",
            #                       DeprecationWarning
            #                      )
            #         form_class.add_post_clean_callback(self._manage_order)

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
        self._blocks = []

    @property
    def portal_url(self):
        return generate_portal_url(self.name)

    def register_model(self, model, model_name_in_url, form_class=None):
        # NB: the key is the model & not the ContentType.id, because these IDs
        #     are not always consistent with the test-models.
        if model not in self._excluded_models:
            self._models[model] = ModelConfig(model, model_name_in_url, form_class)

        return self

    # def get_model_conf(self, ct_id=None, model=None):
    def get_model_conf(self, model):
        # if model is None:
        #     assert ct_id is not None
        #     warnings.warn("AppConfigRegistry.get_model_conf(): 'ct_id' argument "
        #                   "is deprecated ; use the 'model' argument instead.",
        #                   DeprecationWarning
        #                  )
        #
        #     model = ContentType.objects.get_for_id(ct_id).model_class()

        model_conf = self._models.get(model)

        if model_conf is None:
            raise NotRegisteredInConfig('Model %s is not registered' % model)

        return model_conf

    def models(self):
        return self._models.itervalues()

    def register_block(self, block):
        self._blocks.append(block)

    def unregister_model(self, model):
        self._models.pop(model, None)
        self._excluded_models.add(model)

    # @property TODO: + return a iterator
    def blocks(self):
        return self._blocks


class _ConfigRegistry(object):
    def __init__(self, block_registry=block_registry):
        self._block_registry = block_registry
        self._apps = _apps = {}
        self._userblocks = []

        # Add an app to creme_config if it has at least a visible SettingKey
        # (to be sure that even app without registered models appear)
        for app_label in {skey.app_label for skey in setting_key_registry if not skey.hidden}:
#            _apps[app_label] = AppConfigRegistry(app_label, creme_registry.get_app(app_label).verbose_name)
            #_apps[app_label] = self._build_app_conf_registry(app_label)
            _apps[app_label] = self._build_app_conf_registry(self._get_app_name(app_label))

    def _build_app_conf_registry(self, app_name):
        return AppConfigRegistry(app_name, creme_registry.get_app(app_name).verbose_name)

#    def get_app(self, app_name):
    def get_app(self, app_label):
#        return self._apps[app_name]
        return self._apps[self._get_app_name(app_label)]

    def _get_app_name(self, app_label):
        """app_label is the key of the app in creme_registry/django apps registry
        app_name corresponds to the app_label for an app, excepted when this app
        'extends' (see creme_registry) another app. In this case, the app_name
        is the app_label of the extended app.
        So we get only one AppConfigRegistry for an app & all its extending apps.
        """
        return creme_registry.get_app(app_label).extended_app or app_label

    def register(self, *to_register):
        """
        @param to_register Sequence of tuples (DjangoModel, short_name_for_url [, ModelForm])
        """
        app_registries = self._apps

        for args in to_register:
#            app_name = args[0]._meta.app_label
            app_name = self._get_app_name(args[0]._meta.app_label)
            app_conf = app_registries.get(app_name)

            if app_conf is None:
#                app_registries[app_name] = app_conf = AppConfigRegistry(app_name, creme_registry.get_app(app_name).verbose_name)
                app_registries[app_name] = app_conf = self._build_app_conf_registry(app_name)

            app_conf.register_model(*args)

    def apps(self):
        return self._apps.itervalues()

    def register_blocks(self, *blocks_to_register):  # TODO: factorise with register()
        app_registries = self._apps

#        for app_name, block in blocks_to_register:
        for app_label, block in blocks_to_register:
            assert hasattr(block, 'detailview_display'), 'block with id="%s" has no detailview_display() method' % block.id_
            # TODO: need a method is_registered() ?
            assert block.id_ in self._block_registry._blocks, 'block with id="%s" is not registered' % block.id_

            app_name = self._get_app_name(app_label)
            app_conf = app_registries.get(app_name)

            if app_conf is None:
#                app_registries[app_name] = app_conf = AppConfigRegistry(app_name, creme_registry.get_app(app_name).verbose_name)
                app_registries[app_name] = app_conf = self._build_app_conf_registry(app_name)

            app_conf.register_block(block)

    def register_userblocks(self, *blocks_to_register):
        for block in blocks_to_register:
            assert hasattr(block, 'detailview_display'), 'block with id="%s" has no detailview_display() method' % block.id_
            assert block.id_ in self._block_registry._blocks, 'block with id="%s" is not registered' % block.id_

        self._userblocks.extend(blocks_to_register)

    def unregister(self, *to_unregister):  # TODO: factorise with register()
        """
        @param to_unregister Sequence of DjangoModels.
        """
        app_registries = self._apps

        for model in to_unregister:
            app_name = self._get_app_name(model._meta.app_label)
            app_conf = app_registries.get(app_name)

            if app_conf is None:
                app_registries[app_name] = app_conf = self._build_app_conf_registry(app_name)

            app_conf.unregister_model(model)

    @property
    def userblocks(self):
        return iter(self._userblocks)


config_registry = _ConfigRegistry()

logger.debug('creme_config: populate registry')
for config_import in find_n_import('creme_config_register',
                                   ['to_register', 'to_unregister',
                                    'blocks_to_register', 'userblocks_to_register',
                                   ]
                                  ):
    config_registry.register(*getattr(config_import, "to_register", ()))
    config_registry.unregister(*getattr(config_import, "to_unregister", ()))
    config_registry.register_blocks(*getattr(config_import, "blocks_to_register", ()))
    config_registry.register_userblocks(*getattr(config_import, "userblocks_to_register", ()))
