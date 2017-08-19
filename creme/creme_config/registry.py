# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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

import logging, re
import warnings

from django.apps import apps
from django.core.urlresolvers import reverse
# from django.contrib.contenttypes.models import ContentType
from django.db.models import FieldDoesNotExist  # Max
from django.forms.models import modelform_factory

from creme.creme_core.core.setting_key import setting_key_registry
from creme.creme_core.forms import CremeModelForm
from creme.creme_core.gui.bricks import brick_registry, Brick
# from creme.creme_core.models.fields import BasicAutoField
# from creme.creme_core.registry import creme_registry
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
        # self._blocks = []
        self._bricks_classes = []

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

    def register_brick(self, brick_cls):
        self._bricks_classes.append(brick_cls)

    def register_block(self, block):
        warnings.warn('AppConfigRegistry.register_block() is deprecated ; use register_brick() instead.',
                      DeprecationWarning
                     )

        self.register_brick(block.__class__)

    def unregister_model(self, model):
        self._models.pop(model, None)
        self._excluded_models.add(model)

    @property
    def bricks(self):
        # return iter(self._bricks_classes)
        for brick_cls in self._bricks_classes:
            yield brick_cls()

    def blocks(self):
        warnings.warn('AppConfigRegistry.blocks() is deprecated ; '
                      'use bricks() instead (beware it returns an iterator).',
                      DeprecationWarning
                     )
        # return self._blocks
        return list(self.bricks)


class _ConfigRegistry(object):
    def __init__(self, block_registry=brick_registry):
        # self._block_registry = block_registry
        self._brick_registry = block_registry
        self._apps = _apps = {}
        # self._userblocks = []
        self._user_brick_classes = []
        self._portal_brick_classes = []

        # Add an app to creme_config if it has at least a visible SettingKey
        # (to be sure that even app without registered models appear)
        for app_label in {skey.app_label for skey in setting_key_registry if not skey.hidden}:
            _apps[app_label] = self._build_app_conf_registry(self._get_app_name(app_label))

    def _build_app_conf_registry(self, app_name):
        # return AppConfigRegistry(app_name, creme_registry.get_app(app_name).verbose_name)
        return AppConfigRegistry(app_name, apps.get_app_config(app_name).verbose_name)

    def get_app(self, app_label):
        return self._apps[self._get_app_name(app_label)]

    def _get_app_name(self, app_label):
        # """app_label is the key of the app in creme_registry/django apps registry
        """app_label is the key of the app in django apps registry
        app_name corresponds to the app_label for an app, excepted when this app
        'extends' (see creme_registry) another app. In this case, the app_name
        is the app_label of the extended app.
        So we get only one AppConfigRegistry for an app & all its extending apps.
        """
        # return creme_registry.get_app(app_label).extended_app or app_label
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
            if isinstance(brick_cls, Brick):
                warnings.warn('_ConfigRegistry.register_bricks(): registered brick instance is deprecated ;'
                              'register brick class instead (brick ID=%s)' % brick_cls.id_,
                              DeprecationWarning
                             )
                brick_cls = brick_cls.__class__

            assert hasattr(brick_cls, 'detailview_display'), 'brick with id="%s" has no detailview_display() method' % brick_cls.id_
            # TODO: need a method is_registered() ?
            assert brick_cls.id_ in self._brick_registry._brick_classes, 'brick with id="%s" is not registered' % brick_cls.id_

            app_name = self._get_app_name(app_label)
            app_conf = app_registries.get(app_name)

            if app_conf is None:
                app_registries[app_name] = app_conf = self._build_app_conf_registry(app_name)

            app_conf.register_brick(brick_cls)

    def register_blocks(self, *blocks_to_register):
        warnings.warn('_ConfigRegistry.register_blocks() is deprecated ; use register_bricks() instead.',
                      DeprecationWarning
                     )

        self.register_bricks(*blocks_to_register)

    def register_portal_bricks(self, *bricks_to_register):
        for brick_cls in bricks_to_register:
            assert hasattr(brick_cls, 'detailview_display'), 'brick with id="%s" has no detailview_display() method' % brick_cls.id_
            assert brick_cls.id_ in self._brick_registry._brick_classes, 'brick with id="%s" is not registered' % brick_cls.id_

        self._portal_brick_classes.extend(bricks_to_register)

    def register_user_bricks(self, *bricks_to_register):
        for brick_cls in bricks_to_register:
            if isinstance(brick_cls, Brick):
                warnings.warn('_ConfigRegistry.register_user_bricks(): registered brick instance is deprecated ;'
                              'register brick class instead (brick ID=%s)' % brick_cls.id_,
                              DeprecationWarning
                             )
                brick_cls = brick_cls.__class__

            assert hasattr(brick_cls, 'detailview_display'), 'brick with id="%s" has no detailview_display() method' % brick_cls.id_
            assert brick_cls.id_ in self._brick_registry._brick_classes, 'brick with id="%s" is not registered' % brick_cls.id_

            self._user_brick_classes.append(brick_cls)

        # self._user_bricks.extend(bricks_to_register)

    def register_userblocks(self, *blocks_to_register):
        warnings.warn('_ConfigRegistry.register_userblocks() is deprecated ; use register_user_bricks() instead.',
                      DeprecationWarning
                     )
        self.register_user_bricks(*blocks_to_register)

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
        # return iter(self._user_bricks)
        for brick_cls in self._user_brick_classes:
            yield brick_cls()

    @property
    def userblocks(self):
        warnings.warn('_ConfigRegistry.userblocks() is deprecated ; use user_bricks() instead.',
                      DeprecationWarning
                     )

        # return iter(self._userblocks)
        return self.user_bricks

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
            #url = '/creme_config/%s/%s/add_widget/' % (app_name, model_name)
            url = reverse('creme_config__create_instance_from_widget', args=(app_name, model_name))

        return url, allowed

config_registry = _ConfigRegistry()

logger.debug('creme_config: populate registry')
for config_import in find_n_import('creme_config_register',
                                   ['to_register', 'to_unregister',
                                    'blocks_to_register', 'userblocks_to_register',
                                   ]
                                  ):
    config_registry.register(*getattr(config_import, 'to_register', ()))
    config_registry.unregister(*getattr(config_import, 'to_unregister', ()))
    config_registry.register_bricks(*getattr(config_import, 'blocks_to_register', ()))  # TODO: rename 'bricks'
    config_registry.register_user_bricks(*getattr(config_import, 'userblocks_to_register', ()))  # TODO: rename 'userbricks_to_register'
    config_registry.register_portal_bricks(*getattr(config_import, 'portalbricks_to_register', ()))
