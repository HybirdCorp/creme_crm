################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2023  Hybird
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

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Iterable, Iterator

from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Model
from django.forms.models import ModelForm, modelform_factory
from django.urls import reverse

from creme.creme_core.core.setting_key import setting_key_registry
from creme.creme_core.forms import CremeModelForm
from creme.creme_core.gui.bricks import Brick, brick_registry

from .bricks import GenericModelBrick

if TYPE_CHECKING:
    from .forms.generics import DeletionForm

logger = logging.getLogger(__name__)


class NotRegisteredInConfig(Exception):
    pass


class RegistrationError(Exception):
    pass


class _ModelConfigAction:
    """Action (creation/edition/deletion) on a configured model."""
    __slots__ = ('_model', '_model_name', '_form_class', 'url_name')

    def __init__(self, *,
                 model: type[Model],
                 model_name: str,
                 ):
        self._model = model
        self._model_name = model_name
        self._form_class: type[ModelForm] | None = None
        self.url_name: str | None = None

    def _default_form_class(self) -> type[ModelForm]:
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
    def form_class(self) -> type[ModelForm]:
        form_class = self._form_class
        return self._default_form_class() if form_class is None else form_class

    @form_class.setter
    def form_class(self, form_cls: type[ModelForm] | None) -> None:
        self._form_class = form_cls

    @property
    def model(self) -> type[Model]:
        return self._model

    @property
    def model_name(self) -> str:
        return self._model_name


class _ModelConfigCreator(_ModelConfigAction):
    __slots__ = (*_ModelConfigAction.__slots__, 'enable_func')

    def __init__(self, *,
                 model: type[Model],
                 model_name: str,
                 ):
        super().__init__(model=model, model_name=model_name)
        # TODO: type when Callable can indicate keyword argument...
        self.enable_func = lambda user: True

    def get_url(self, user) -> str | None:
        if self.enable_func(user=user):
            url_name = self.url_name

            return reverse(
                'creme_config__create_instance',
                args=(
                    self._model._meta.app_label,
                    self._model_name,
                ),
            ) if url_name is None else reverse(url_name)

        return None


class _ModelConfigEditor(_ModelConfigAction):
    __slots__ = (*_ModelConfigAction.__slots__, 'enable_func')

    def __init__(self, *,
                 model: type[Model],
                 model_name: str,
                 ):
        super().__init__(model=model, model_name=model_name)
        self.enable_func = lambda instance, user: True

    def get_url(self, instance: Model, user) -> str | None:
        if self.enable_func(instance=instance, user=user):
            url_name = self.url_name

            return reverse(
                'creme_config__edit_instance',
                args=(
                    self._model._meta.app_label,
                    self.model_name,
                    # 'pk' instead of 'id' because a model could have a different primary key
                    #  (like GeoAddress)
                    instance.pk,
                ),
            ) if url_name is None else reverse(url_name, args=(instance.pk,))

        return None


# TODO: factorise with _ModelConfigEditor
class _ModelConfigDeletor(_ModelConfigAction):
    __slots__ = (*_ModelConfigAction.__slots__, 'enable_func')

    def __init__(self, *,
                 model: type[Model],
                 model_name: str,
                 ):
        super().__init__(model=model, model_name=model_name)
        self.enable_func = lambda instance, user: True

    def _default_form_class(self):
        from .forms.generics import DeletionForm

        return DeletionForm

    def get_url(self, instance, user) -> str | None:
        if self.enable_func(instance=instance, user=user):
            url_name = self.url_name

            return reverse(
                'creme_config__delete_instance',
                args=(
                    self._model._meta.app_label,
                    self.model_name,
                    instance.pk,
                ),
            ) if url_name is None else reverse(url_name, args=(instance.pk,))

        return None


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

    def __init__(self, model: type[Model], model_name: str):
        """ Constructor.

        @param model: Class inheriting django.db.Model
        @param model_name: Short name for the model, used in URLs (String).
        """
        if not self._SHORT_NAME_RE.match(model_name):
            raise ValueError(
                'The argument "model_name" should only contain alphanumeric characters or _'
            )

        self.creator = _ModelConfigCreator(model=model, model_name=model_name)
        self.editor  = _ModelConfigEditor(model=model, model_name=model_name)
        self.deletor = _ModelConfigDeletor(model=model, model_name=model_name)
        self.brick_cls: type[GenericModelBrick] = GenericModelBrick

    def brick_class(self, brick_cls: type[GenericModelBrick]) -> _ModelConfig:
        """ Set the Brick class to use ; can be used in a fluent way.

        @param brick_cls: Class inheriting GenericModelBrick.
        @return: The ModelConfig instance.
        """
        self.brick_cls = brick_cls

        return self

    def get_brick(self) -> GenericModelBrick:
        """ Get the instance of brick to use for the configuration of the model. """
        model = self.model

        return self.brick_cls(app_name=model._meta.app_label, model_config=self)

    def creation(self, *,
                 form_class: type[ModelForm] | None = None,
                 url_name: str | None = None,
                 enable_func=None,
                 ) -> _ModelConfig:
        """ Set the creation behaviour ; can be used in a fluent way.

        @param form_class: Class inheriting <django.forms.ModelForm>
               (tips: use creme.creme_core.forms.CremeModelForm) ;
               None means a form is generated.
        @param url_name: Name of a URL (without argument)
               None means "creme_config__create_instance" will be used.
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
    def edition(self, *,
                form_class: type[ModelForm] | None = None,
                url_name: str | None = None,
                enable_func=None,
                ) -> _ModelConfig:
        """ Set the edition behaviour ; can be used in a fluent way.

        @param form_class: Class inheriting <django.forms.ModelForm>
               (tips: use creme.creme_core.forms.CremeModelForm) ;
               None means a form is generated.
        @param url_name: Name of a URL (without 1 argument, the edited instance's ID)
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
    def deletion(self, *,
                 form_class: type[DeletionForm] | None = None,
                 url_name: str | None = None,
                 enable_func=None,
                 ) -> _ModelConfig:
        """ Set the deletion behaviour ; can be used in a fluent way.

        @param form_class: Class "inheriting" <creme_config.forms.generics.DeletionForm>.
               None means that <DeletionForm> will be used.
        @param url_name: Name of a URL (without 1 argument, the deleted instance's ID)
               None means "creme_config__delete_instance" will be used.
        @param enable_func: Function which takes 2 arguments (an instance of the
               configured model & the user doing the request) & return a boolean
               (False means the user cannot delete existing instances of the model).
               <None> means the instance can always be deleted.
        @return: The ModelConfig instance.
        """
        deletor = self.deletor
        deletor.form_class = form_class
        deletor.url_name = url_name

        if enable_func is not None:
            deletor.enable_func = enable_func

        return self

    @property
    def model(self) -> type[Model]:
        return self.creator.model

    @property
    def model_name(self) -> str:
        return self.creator.model_name

    @model_name.setter
    def model_name(self, name: str):
        self.creator._model_name = name
        self.editor._model_name = name
        self.deletor._model_name = name

    @property
    def verbose_name(self) -> str:
        """Verbose name of the related name."""
        return self.model._meta.verbose_name


# TODO: __slots__ ???
class _AppConfigRegistry:
    """ Contains the configuration information for an app :
     - Models to configure.
     - Extra Bricks.
    """
    def __init__(self,
                 name: str,
                 verbose_name: str,
                 config_registry: _ConfigRegistry,
                 ):
        self.name = name
        self.verbose_name = verbose_name
        self._models: dict[type[Model], _ModelConfig] = {}
        self._config_registry = config_registry
        self._brick_ids: list[str] = []

    @property
    def portal_url(self) -> str:
        return reverse('creme_config__app_portal', args=(self.name,))

    def _register_model(self,
                        model: type[Model],
                        model_name: str,
                        ) -> _ModelConfig:
        # NB: the key is the model & not the ContentType.id, because these IDs
        #     are not always consistent with the test-models.
        models = self._models

        if model in models:
            raise RegistrationError(f'Duplicated model: {model}')

        conf = models[model] = _ModelConfig(model=model, model_name=model_name)

        return conf

    def get_model_conf(self, model: type[Model]) -> _ModelConfig:
        """ Get the ModelConfig related to a model.

        @param model: Class inheriting <django.db.Model>.
        @return: _ModelConfig instance.
        @raise NotRegisteredInConfig.
        """
        model_conf = self._models.get(model)

        if model_conf is None:
            raise NotRegisteredInConfig(f'Model {model} is not registered')

        return model_conf

    def models(self) -> Iterator[_ModelConfig]:
        return iter(self._models.values())

    def _register_bricks(self, brick_ids: Iterable[str]) -> None:
        self._brick_ids.extend(brick_ids)

    def _unregister_model(self, model: type[Model]) -> None:
        self._models.pop(model, None)

    @property
    def bricks(self) -> Iterator[Brick]:
        """Generator yielding the extra-bricks to configure the app."""
        return self._config_registry._brick_registry.get_bricks(self._brick_ids)

    @property
    def is_empty(self) -> bool:
        """Is the configuration portal of the app empty."""
        return not bool(
            self._models
            or self._brick_ids
            # TODO: factorise with SettingsBrick ;
            #       pass the _ConfigRegistry to SettingsBrick everywhere
            or any(
                skey.app_label == self.name and not skey.hidden
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
    def __init__(self,
                 brick_registry=brick_registry,
                 setting_key_registry=setting_key_registry,
                 ):
        self._brick_registry = brick_registry
        self._skey_registry = setting_key_registry
        self._apps: dict[str, _AppConfigRegistry] = {}
        self._user_brick_ids: list[str] = []
        self._portal_brick_ids: list[str] = []

    def get_app_registry(self, app_label: str, create=False) -> _AppConfigRegistry:
        """ Get the instance of AppConfigRegistry related to a specific app.

        @param app_label: String (e.g. 'creme_core').
        @param create: If True, the AppConfigRegistry is created if needed.
        @return: Instance of <AppConfigRegistry>.
        @raise LookupError: If the app does not exist or does not have a registry.
        """
        app_name = self._get_app_name(app_label)

        app_registries = self._apps
        app_registry = app_registries.get(app_name)

        if app_registry is None:
            if create:
                app_registries[app_name] = app_registry = _AppConfigRegistry(
                    name=app_name,
                    verbose_name=apps.get_app_config(app_name).verbose_name,
                    config_registry=self,
                )
            else:
                raise KeyError(f'No AppConfigRegistry for this app: {app_label}.')

        return app_registry

    def _get_app_name(self, app_label: str) -> str:
        """app_label is the key of the app in django apps registry
        app_name corresponds to the app_label for an app, excepted when this app
        'extends' (see creme_registry) another app. In this case, the app_name
        is the app_label of the extended app.
        So we get only one AppConfigRegistry for an app & all its extending apps.

        @param app_label: String (e.g. 'creme_core').
        @raise LookupError: If the app does not exist.
        @return String.
        """
        ext_app_name = apps.get_app_config(app_label).extended_app

        if ext_app_name is not None:
            for app_config in apps.app_configs.values():
                if app_config.name == ext_app_name:
                    return app_config.label

        return app_label

    def register_model(self,
                       model: type[Model],
                       model_name: str | None = None,
                       ) -> _ModelConfig:
        """ Register a model in order to make it available in the configuration.
        @param model: Class inheriting <django.db.Model>.
        @param model_name: String (only alphanumerics & _ are allowed) use in the
               configuration URLs to identify this model among the app models.
               <None> (default value) means an automatic name will be generated.
        @return: A ModelConfig instance (so you can call creation()/edition()
                 directly on the result, in a fluent way).
        """
        return self.get_app_registry(
            app_label=model._meta.app_label,
            create=True,
        )._register_model(
            model=model,
            model_name=model_name or model.__name__.lower(),
        )

    def apps(self) -> Iterator[_AppConfigRegistry]:
        """Iterator on all AppConfigRegistries."""
        return iter(self._apps.values())

    def _get_brick_id(self, brick_cls: type[Brick]) -> str:
        # brick_id = brick_cls.id_
        brick_id = brick_cls.id

        # TODO: remove in creme 2.6
        if not brick_id:
            try:
                brick_id = brick_cls.id_
            except AttributeError:
                pass
            else:
                logger.critical(
                    'The brick class %s uses the old "id_" attribute; '
                    'use an attribute "id" instead (brick is ignored).',
                    brick_cls,
                )

        if not hasattr(brick_cls, 'detailview_display'):
            raise ValueError(
                '_ConfigRegistry: brick with id="{}" has no '
                'detailview_display() method'.format(brick_id)
            )

        return brick_id

    # TODO: prototype for detailview_display() ?
    def register_app_bricks(self,
                            app_label: str,
                            *brick_classes: type[Brick],
                            ) -> None:
        """ Register some Brick classes which will be used in the configuration
        portal of a specific app.

        @param app_label: String ('eg :'creme_core').
        @param brick_classes: Classes inheriting <creme_core.gui.Brick> with a
               method detailview_display().
        """
        self.get_app_registry(
            app_label=app_label,
            create=True,
        )._register_bricks(
            map(self._get_brick_id, brick_classes)
        )

    def register_portal_bricks(self, *brick_classes: type[Brick]) -> None:
        """Register the extra Brick classes to display of the portal of
        creme_config ("General configuration").

        @param brick_classes: Classes inheriting <creme_core.gui.Brick> with a
               method detailview_display().
        """
        self._portal_brick_ids.extend(map(self._get_brick_id, brick_classes))

    def register_user_bricks(self, *brick_classes: type[Brick]) -> None:
        """Register the extra Brick classes to display of the configuration page
        of each user ("My configuration").

        @param brick_classes: Classes inheriting <creme_core.gui.Brick> with a
               method detailview_display().
        """
        self._user_brick_ids.extend(map(self._get_brick_id, brick_classes))

    def unregister_models(self, *models: type[Model]) -> None:
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
    def portal_bricks(self) -> Iterator[Brick]:
        """Get the instances of extra Bricks to display on
        "General configuration" page.
        """
        return self._brick_registry.get_bricks(self._portal_brick_ids)

    @property
    def user_bricks(self) -> Iterator[Brick]:
        """Get the instances of extra Bricks to display on
        "My configuration" page.
        """
        return self._brick_registry.get_bricks(self._user_brick_ids)

    # TODO: find a better name ?
    def get_model_creation_info(self,
                                model: type[Model],
                                user,
                                ) -> tuple[str | None, bool]:
        """ Get the following information about the on-the-fly creation of instances :
         - URL of the creation view.
         - Is the user allowed to create ?

        It's used by form widgets which can create instances directly in the form.

        @param model: Class inheriting 'django.db.models.Model'.
        @param user: Instance of 'django.contrib.auth.get_user_model()'.
        @return: Tuple (URL, allowed) ; 'URL' is a string or None ; allowed is a boolean.
        """
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
                url = reverse(
                    'creme_config__create_instance_from_widget',
                    args=(app_label, creator.model_name),
                )
            else:
                allowed = False

        return url, allowed


config_registry = _ConfigRegistry()
