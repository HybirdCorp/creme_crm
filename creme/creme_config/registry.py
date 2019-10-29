# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

# import logging
import re

from django.apps import apps
from django.db.models import FieldDoesNotExist
from django.forms.models import modelform_factory
from django.urls import reverse

from creme.creme_core.core.setting_key import setting_key_registry
from creme.creme_core.forms import CremeModelForm
from creme.creme_core.gui.bricks import brick_registry
# from creme.creme_core.utils.imports import import_apps_sub_modules

from .bricks import GenericModelBrick

# logger = logging.getLogger(__name__)


class NotRegisteredInConfig(Exception):
    pass


class RegistrationError(Exception):
    pass


class _ModelConfigAction:
    """Action (creation/edition/deletion) on a configured model."""
    __slots__ = ('_model', '_model_name', '_form_class', 'url_name')

    def __init__(self, *, model, model_name):
        self._model = model
        self._model_name = model_name
        self._form_class = None
        self.url_name = None

    def _default_form_class(self):
        model = self._model
        get_field = model._meta.get_field

        # TODO: test
        try:
            get_field('is_custom')
        except FieldDoesNotExist:
            exclude = None
        else:
            exclude = ('is_custom',)

        return modelform_factory(model, form=CremeModelForm, exclude=exclude)

    @property
    def form_class(self):
        form_class = self._form_class
        return self._default_form_class() if form_class is None else form_class

    @form_class.setter
    def form_class(self, form_cls):
        self._form_class = form_cls

    @property
    def model(self):
        return self._model

    @property
    def model_name(self):
        return self._model_name


class _ModelConfigCreator(_ModelConfigAction):
    __slots__ = (*_ModelConfigAction.__slots__, 'enable_func')

    def __init__(self, *, model, model_name):
        super().__init__(model=model, model_name=model_name)
        self.enable_func = lambda user: True

    def get_url(self, user):
        if self.enable_func(user=user):
            url_name = self.url_name

            return reverse('creme_config__create_instance',
                           args=(self._model._meta.app_label, self._model_name),
                          ) if url_name is None else \
                   reverse(url_name)


class _ModelConfigEditor(_ModelConfigAction):
    __slots__ = (*_ModelConfigAction.__slots__, 'enable_func')

    def __init__(self, *, model, model_name):
        super().__init__(model=model, model_name=model_name)
        self.enable_func = lambda instance, user: True

    def get_url(self, instance, user):
        if self.enable_func(instance=instance, user=user):
            url_name = self.url_name

            return reverse('creme_config__edit_instance',
                           args=(self._model._meta.app_label,
                                 self.model_name,
                                 instance.id,
                                ),
                          ) if url_name is None else \
                   reverse(url_name, args=(instance.id,))


# TODO: factorise with _ModelConfigEditor
class _ModelConfigDeletor(_ModelConfigAction):
    __slots__ = (*_ModelConfigAction.__slots__, 'enable_func')

    def __init__(self, *, model, model_name):
        super().__init__(model=model, model_name=model_name)
        self.enable_func = lambda instance, user: True

    def _default_form_class(self):
        from .forms.generics import DeletionForm

        return DeletionForm

    def get_url(self, instance, user):
        if self.enable_func(instance=instance, user=user):
            url_name = self.url_name

            return reverse('creme_config__delete_instance',
                           args=(self._model._meta.app_label,
                                 self.model_name,
                                 instance.id,
                                ),
                          ) if url_name is None else \
                   reverse(url_name, args=(instance.id,))


# class ModelConfig:
class _ModelConfig:
    """ Contains the configuration information for a model :
     - Creation form/URL  (the creation can be disabled too).
     - Edition form/URL  (the creation can be disabled too).
     - Brick.

     These different information are created automatically, but you can
     customise them.
    """
    __slots__ = ('creator', 'editor', 'deletor', 'brick_cls')

    _SHORT_NAME_RE = re.compile(r'^\w+$')

    # def __init__(self, model, name_in_url, form_class=None):
    def __init__(self, model, model_name):
        """ Constructor.

        @param model: Class inheriting django.db.Model
        @param model_name: Short name for the model, used in URLs (String).
        """
        # if not self._SHORT_NAME_RE.match(name_in_url):
        #     raise ValueError('The argument "name_in_url" should only contain alphanumeric characters or _')
        if not self._SHORT_NAME_RE.match(model_name):
            raise ValueError('The argument "model_name" should only contain alphanumeric characters or _')

        # self.model = model
        # self.name_in_url = name_in_url
        # self._form_class = form_class
        self.creator = _ModelConfigCreator(model=model, model_name=model_name)
        self.editor  = _ModelConfigEditor(model=model, model_name=model_name)
        self.deletor = _ModelConfigDeletor(model=model, model_name=model_name)
        self.brick_cls = GenericModelBrick

    # @property
    # def model_form(self):
    #     if self._form_class is None:
    #         model = self.model
    #         get_field = model._meta.get_field
    #
    #         try:
    #             get_field('is_custom')
    #         except FieldDoesNotExist:
    #             exclude = None
    #         else:
    #             exclude = ('is_custom',)
    #
    #         self._form_class = modelform_factory(model, form=CremeModelForm, exclude=exclude)
    #
    #     return self._form_class

    def brick_class(self, brick_cls):
        """ Set the Brick class to use ; can be used in a fluent way.

        @param brick_cls: Class inheriting GenericModelBrick.
        @return: The ModelConfig instance.
        """
        self.brick_cls = brick_cls

        return self

    def get_brick(self):
        """ Get the instance of brick to use for the configuration of the model. """
        model = self.model

        return self.brick_cls(app_name=model._meta.app_label, model_config=self)

    def creation(self, *, form_class=None, url_name=None, enable_func=None):
        """ Set the creation behaviour ; can be used in a fluent way.

        @param form_class: Class inheriting django.forms.ModelForm
               (tips: use creme.creme_core.forms.CremeModelForm) ;
               None means a form is generated.
        @param url_name: Name of an URL (without argument)
               None means "creme_config__create_instance" will be used.
        @param enabled: Boolean ; False means the user cannot create new
               instance of the model (default: True)
        @param enable_func: Function which takes 1 argument (the user doing the request)
               & return a boolean (False means the user cannot create an instance of the model).
               <None> means the user can always create.
        @return: The ModelConfig instance.
        """
        creator = self.creator
        creator.form_class = form_class
        creator.url_name = url_name

        if enable_func is not None:
            creator.enable_func = enable_func

        return self

    # TODO: factorise with creation()
    def edition(self, *, form_class=None, url_name=None, enable_func=None):
        """ Set the edition behaviour ; can be used in a fluent way.

        @param form_class: Class inheriting django.forms.ModelForm
               (tips: use creme.creme_core.forms.CremeModelForm) ;
               None means a form is generated.
        @param url_name: Name of an URL (without 1 argument, the edited instance's ID)
               None means "creme_config__edit_instance" will be used.
        @param enable_func: Function which takes 2 arguments (an instance of the
               configured model & the user doing the request) & return a boolean
               (False means the user cannot edit existing instances of the model).
               <None> means the instance can always be edited.
        @return: The ModelConfig instance.
        """
        editor = self.editor
        editor.form_class = form_class
        editor.url_name = url_name

        if enable_func is not None:
            editor.enable_func = enable_func

        return self

    # TODO: factorise
    def deletion(self, *, form_class=None, url_name=None, enable_func=None):
        """ Set the deletion behaviour ; can be used in a fluent way.

        @param form_class: Class "inheriting" <creme_config.forms.generics.DeletionForm>.
               None means that <DeletionForm> will be used.
        @param url_name: Name of an URL (without 1 argument, the deleted instance's ID)
               None means "creme_config__delete_instance" will be used.
        @param enable_func: Function which takes 2 arguments (an instance of the
               configured model & the user doing the request) & return a boolean
               (False means the user cannot delete existing instances of the model).
               <None> means the instance can always be edited.
        @return: The ModelConfig instance.
        """
        deletor = self.deletor
        deletor.form_class = form_class
        deletor.url_name = url_name

        if enable_func is not None:
            deletor.enable_func = enable_func

        return self

    @property
    def model(self):
        return self.creator.model

    @property
    def model_name(self):
        return self.creator.model_name

    @model_name.setter
    def model_name(self, name):
        self.creator._model_name = name
        self.editor._model_name = name
        self.deletor._model_name = name

    @property
    def verbose_name(self):
        """Verbose name of the related name."""
        return self.model._meta.verbose_name


# TODO: __slots__ ???
# class AppConfigRegistry:
class _AppConfigRegistry:
    """ Contains the configuration information for an app :
     - Models to configure.
     - Extra Bricks.
    """
    # def __init__(self, name, verbose_name):
    def __init__(self, name, verbose_name, config_registry):
        self.name = name
        self.verbose_name = verbose_name
        self._models = {}
        # self._excluded_models = set()
        self._config_registry = config_registry
        # self._bricks_classes = []
        self._brick_ids = []

    @property
    def portal_url(self):
        return reverse('creme_config__app_portal', args=(self.name,))

    # def register_model(self, model, model_name_in_url, form_class=None):
    #     # NB: the key is the model & not the ContentType.id, because these IDs
    #     #     are not always consistent with the test-models.
    #     if model not in self._excluded_models:
    #         self._models[model] = ModelConfig(model, model_name_in_url, form_class)
    #
    #     return self
    def _register_model(self, model, model_name):
        # NB: the key is the model & not the ContentType.id, because these IDs
        #     are not always consistent with the test-models.
        models = self._models

        if model in models:
            raise RegistrationError('Duplicated model: {}'.format(model))

        conf = models[model] = _ModelConfig(model=model, model_name=model_name)

        return conf

    def get_model_conf(self, model):
        """ Get the ModelConfig related to a model.

        @param model: Class inheriting django.db.Model.
        @return: ModelConfig instance.
        @raise NotRegisteredInConfig.
        """
        model_conf = self._models.get(model)

        if model_conf is None:
            raise NotRegisteredInConfig('Model {} is not registered'.format(model))

        return model_conf

    def models(self):
        return iter(self._models.values())

    # def register_brick(self, brick_cls):
    #     self._bricks_classes.append(brick_cls)
    def _register_bricks(self, brick_ids):
        self._brick_ids.extend(brick_ids)

    # def unregister_model(self, model):
    #     self._models.pop(model, None)
    #     self._excluded_models.add(model)
    def _unregister_model(self, model):
        self._models.pop(model, None)

    @property
    def bricks(self):
        """Generator yielding the extra-bricks to configure the app."""
        # for brick_cls in self._bricks_classes:
        #     yield brick_cls()
        return self._config_registry._brick_registry.get_bricks(self._brick_ids)

    @property
    def is_empty(self):
        """Is the configuration portal of the app empty."""
        return not bool(
            self._models or
            self._brick_ids or
            # TODO: factorise with SettingsBrick ; pass the _ConfigRegistry to SettingsBrick
            #       everywhere  => need Class-Based reloading views
            any(skey.app_label == self.name and not skey.hidden
                    for skey in self._config_registry._skey_registry
               )
        )


class _ConfigRegistry:
    """ Registry to customise the app 'creme_config'.

    You can register:
        - 'Small' models ; their will be grouped by app, & you can created/edit/delete instances.
        - Bricks for the global portal of configuration.
        - Bricks for the portal of configuration of a specific app.
        - Bricks for the personal configuration of users.
    """
    def __init__(self, brick_registry=brick_registry, setting_key_registry=setting_key_registry):
        self._brick_registry = brick_registry
        self._skey_registry = setting_key_registry
        self._apps = _apps = {}
        # self._user_brick_classes = []
        self._user_brick_ids = []
        # self._portal_brick_classes = []
        self._portal_brick_ids = []

        # # Add an app to creme_config if it has at least a visible SettingKey
        # # (to be sure that even app without registered models appear)
        # for app_label in {skey.app_label for skey in setting_key_registry if not skey.hidden}:
        #     _apps[app_label] = self._build_app_conf_registry(self._get_app_name(app_label))

    # def _build_app_conf_registry(self, app_name):
    #     return AppConfigRegistry(app_name, apps.get_app_config(app_name).verbose_name)
    #
    # def get_app(self, app_label):
    #     return self._apps[self._get_app_name(app_label)]
    def get_app_registry(self, app_label, create=False):
        """ Get the instance of AppConfigRegistry related to a specific app.

        @param app_label: String (eg: 'creme_core').
        @param create: If True, the AppConfigRegistry is created if needed.
        @return: Instance of <AppConfigRegistry>.
        @raise LookupError: If the app does not exist or does not have a registry.
        """
        app_name = self._get_app_name(app_label)

        app_registries = self._apps
        app_registry = app_registries.get(app_name)

        if app_registry is None:
            if create:
                app_registries[app_name] = app_registry = \
                    _AppConfigRegistry(name=app_name,
                                       verbose_name=apps.get_app_config(app_name)
                                       .verbose_name,
                                       config_registry=self,
                                       )
            else:
                raise KeyError('No AppConfigRegistry for this app: {}.'.format(app_label))

        return app_registry

    def _get_app_name(self, app_label):
        """app_label is the key of the app in django apps registry
        app_name corresponds to the app_label for an app, excepted when this app
        'extends' (see creme_registry) another app. In this case, the app_name
        is the app_label of the extended app.
        So we get only one AppConfigRegistry for an app & all its extending apps.

        @param app_label: String (eg: 'creme_core').
        @raise LookupError: If the app does not exist.
        @return String.
        """
        ext_app_name = apps.get_app_config(app_label).extended_app

        if ext_app_name is not None:
            for app_config in apps.app_configs.values():
                if app_config.name == ext_app_name:
                    return app_config.label

        return app_label

    # def register(self, *to_register):
    #     """
    #     @param to_register: Sequence of tuples (DjangoModel, short_name_for_url [, ModelForm])
    #     """
    #     app_registries = self._apps
    #
    #     for args in to_register:
    #         app_name = self._get_app_name(args[0]._meta.app_label)
    #         app_conf = app_registries.get(app_name)
    #
    #         if app_conf is None:
    #             app_registries[app_name] = app_conf = self._build_app_conf_registry(app_name)
    #
    #         app_conf.register_model(*args)
    def register_model(self, model, model_name=None):
        """ Register a model in order to make it available in the configuration.
        @param model: Class inheriting <django.db.Model>.
        @param model_name: String (only alphanumerics & _ are allowed) use in the
               configuration URLs to identify this model among the app models.
               <None> (default value) means an automatic name will will generated.
        @return: A ModelConfig instance (tips so you can call creation()/edition()
                directly on the result, in a fluent way).
        """
        return self.get_app_registry(app_label=model._meta.app_label, create=True) \
                   ._register_model(
                        model=model,
                        model_name=model_name or model.__name__.lower(),
                   )

    def apps(self):
        """Iterator on all AppConfigRegistries."""
        return iter(self._apps.values())

    def _get_brick_id(self, brick_cls):
        brick_id = brick_cls.id_

        if not hasattr(brick_cls, 'detailview_display'):
            raise ValueError('_ConfigRegistry: brick with id="{}" has no '
                             'detailview_display() method'.format(brick_id)
                            )

        return brick_id

    # def register_bricks(self, *bricks_to_register):
    #     app_registries = self._apps
    #
    #     for app_label, brick_cls in bricks_to_register:
    #         assert hasattr(brick_cls, 'detailview_display'), \
    #               'brick with id="{}" has no detailview_display() method'.format(brick_cls.id_)
    #         # todo: need a method is_registered() ?
    #         assert brick_cls.id_ in self._brick_registry._brick_classes, \
    #                'brick with id="{}" is not registered'.format(brick_cls.id_)
    #
    #         app_name = self._get_app_name(app_label)
    #         app_conf = app_registries.get(app_name)
    #
    #         if app_conf is None:
    #             app_registries[app_name] = app_conf = self._build_app_conf_registry(app_name)
    #
    #         app_conf.register_brick(brick_cls)
    def register_app_bricks(self, app_label, *brick_classes):
        """ Register some Brick classes which will be used in the configuration
        portal of a specific app.

        @param app_label: String ('eg :'creme_core').
        @param brick_classes: Classes inheriting <creme_core.gui.Brick> with a
               method detailview_display().
        """
        self.get_app_registry(app_label=app_label, create=True) \
            ._register_bricks(map(self._get_brick_id, brick_classes))

    # def register_portal_bricks(self, *bricks_to_register):
    #    for brick_cls in bricks_to_register:
    #        assert hasattr(brick_cls, 'detailview_display'), \
    #               'brick with id="{}" has no detailview_display() method'.format(brick_cls.id_)
    #        assert brick_cls.id_ in self._brick_registry._brick_classes, \
    #               'brick with id="{}" is not registered'.format(brick_cls.id_)
    #
    #    self._portal_brick_classes.extend(bricks_to_register)
    def register_portal_bricks(self, *brick_classes):
        """Register the extra Brick classes to display of the portal of
        creme_config ("General configuration").

        @param brick_classes: Classes inheriting <creme_core.gui.Brick> with a
               method detailview_display().
        """
        self._portal_brick_ids.extend(map(self._get_brick_id, brick_classes))

    # def register_user_bricks(self, *bricks_to_register):
    #    for brick_cls in bricks_to_register:
    #        assert hasattr(brick_cls, 'detailview_display'), \
    #               'brick with id="{}" has no detailview_display() method'.format(brick_cls.id_)
    #        assert brick_cls.id_ in self._brick_registry._brick_classes, \
    #               'brick with id="{}" is not registered'.format(brick_cls.id_)
    #
    #        self._user_brick_classes.append(brick_cls)
    def register_user_bricks(self, *brick_classes):
        """Register the extra Brick classes to display of the configuration page
        of each user ("My configuration").

        @param brick_classes: Classes inheriting <creme_core.gui.Brick> with a
               method detailview_display().
        """
        self._user_brick_ids.extend(map(self._get_brick_id, brick_classes))

    # def unregister(self, *to_unregister):
    #     """
    #     @param to_unregister: Sequence of DjangoModels.
    #     """
    #     app_registries = self._apps
    #
    #     for model in to_unregister:
    #         app_name = self._get_app_name(model._meta.app_label)
    #         app_conf = app_registries.get(app_name)
    #
    #         if app_conf is None:
    #             app_registries[app_name] = app_conf = self._build_app_conf_registry(app_name)
    #
    #         app_conf.unregister_model(model)
    def unregister_models(self, *models):
        """Un-register some models which have been registered.

        @param models: Classes inheriting django.db.Model
        @raise: NotRegisteredInConfig.
        """
        get_app_registry = self.get_app_registry

        for model in models:
            app_conf = get_app_registry(model._meta.app_label)

            if app_conf is not None:
                app_conf._unregister_model(model)

    @property
    def portal_bricks(self):
        """Get the instances of extra Bricks to display on "General configuration" page."""
        # for brick_cls in self._portal_brick_classes:
        #     yield brick_cls()
        return self._brick_registry.get_bricks(self._portal_brick_ids)

    @property
    def user_bricks(self):
        """Get the instances of extra Bricks to display on "My configuration" page."""
        # for brick_cls in self._user_brick_classes:
        #     yield brick_cls()
        return self._brick_registry.get_bricks(self._user_brick_ids)

    # TODO: find a better name ?
    def get_model_creation_info(self, model, user):
        """ Get the following information about the on-the-fly creation of instances :
         - URL of the creation view.
         - Is the user allowed to create ?

        It's used by form widgets which can create instances directly in the form.

        @param model: Class inheriting 'django.db.models.Model'.
        @param user: Instance of 'django.contrib.auth.get_user_model()'.
        @return: Tuple (URL, allowed) ; 'URL' is a string or None ; allowed is a boolean.
        """
        # app_label = model._meta.app_label
        # allowed = user.has_perm_to_admin(app_label)
        # url = None
        #
        # try:
        #     model_name = self.get_app(app_label) \
        #                      .get_model_conf(model=model) \
        #                      .name_in_url
        # except (KeyError, NotRegisteredInConfig):
        #     allowed = False
        # else:
        #     url = reverse('creme_config__create_instance_from_widget',
        #                   args=(app_label, model_name),
        #                  )
        #
        # return url, allowed
        app_label = model._meta.app_label
        allowed = user.has_perm_to_admin(app_label)
        url = None

        try:
            creator = self.get_app_registry(app_label) \
                          .get_model_conf(model=model) \
                          .creator
        except (KeyError, NotRegisteredInConfig):
            allowed = False
        else:
            if creator.url_name is None and creator.enable_func(user=user):  # Is URL customised ?
                url = reverse('creme_config__create_instance_from_widget',
                              args=(app_label, creator.model_name),
                             )
            else:
                allowed = False

        return url, allowed


config_registry = _ConfigRegistry()

# logger.debug('creme_config: populate registry')

# for config_import in import_apps_sub_modules('creme_config_register'):
#     config_registry.register(*getattr(config_import, 'to_register', ()))
#     config_registry.unregister(*getattr(config_import, 'to_unregister', ()))
#     config_registry.register_bricks(*getattr(config_import, 'blocks_to_register', ()))  # todo: rename 'bricks'
#     config_registry.register_user_bricks(*getattr(config_import, 'userblocks_to_register', ()))  # todo: rename 'userbricks_to_register'
#     config_registry.register_portal_bricks(*getattr(config_import, 'portalbricks_to_register', ()))
