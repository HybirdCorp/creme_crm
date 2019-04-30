# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2019  Hybird
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

from importlib import import_module
import warnings

from django.utils.translation import gettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class CremeConfigConfig(CremeAppConfig):
    name = 'creme.creme_config'
    verbose_name = _('General configuration')
    dependencies = ['creme.creme_core']
    credentials = CremeAppConfig.CRED_REGULAR

    def all_apps_ready(self):
        super().all_apps_ready()

        from .registry import config_registry
        self.populate_config_registry(config_registry)

    def populate_config_registry(self, config_registry):
        from creme.creme_core.apps import creme_app_configs

        for app_config in creme_app_configs():
            config_registry.get_app_registry(app_config.label, create=True)

            register_creme_config = getattr(app_config, 'register_creme_config', None)

            if register_creme_config is not None:
                register_creme_config(config_registry)
            else:
                app_name = app_config.name

                try:
                    config_registry_mod = import_module('{}.{}'.format(app_name, 'creme_config_register'))
                except ImportError:
                    continue

                warnings.warn('The app "{}" still uses a module "creme_config_register", '
                              'which is deprecated ; add a method "register_creme_config()" '
                              'in the AppConfig instead.'.format(app_name),
                              DeprecationWarning
                             )

                from django.core import checks

                from .registry import NotRegisteredInConfig

                for model, model_name, *forms in getattr(config_registry_mod, 'to_register', ()):
                    model_conf = config_registry.register_model(model, model_name)

                    if forms:
                        form = forms[0]
                        model_conf.creation(form_class=form).edition(form_class=form)

                for model in getattr(config_registry_mod, 'to_unregister', ()):
                    app_reg = config_registry.get_app_registry(model._meta.app_label, create=True)

                    try:
                        app_reg.get_model_conf(model)
                    except NotRegisteredInConfig:
                        @checks.register(checks.Tags.compatibility)
                        def check_deps(app_name=app_name, model=model, **kwargs):
                            return [
                                checks.Error(
                                    'The app "{}" uses the out-of-order capability when '
                                    'un-registering the model {} ; this capability has '
                                    'been removed.'.format(app_name, model),
                                    hint='Fix the order of apps in the setting INSTALLED_CREME_APPS '
                                         'in your local_settings.py/project_settings.py (ie: the '
                                         'un-registered model must be registered _before_). '
                                         'Then, you should use the new registration system & call '
                                         'the method unregister_models() on the registry.',
                                    obj=app_name,
                                    id='creme_config.E001',
                                ),
                            ]
                    else:
                        app_reg._unregister_model(model)

                for app_label, brick_cls in getattr(config_registry_mod, 'blocks_to_register', ()):
                    config_registry.register_app_bricks(app_label, brick_cls)

                config_registry.register_user_bricks(*getattr(config_registry_mod, 'userblocks_to_register', ()))
                config_registry.register_portal_bricks(*getattr(config_registry_mod, 'portalbricks_to_register', ()))

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(
            bricks.SettingsBrick,
            bricks.PropertyTypesBrick,
            bricks.RelationTypesBrick,
            bricks.CustomRelationTypesBrick,
            bricks.SemiFixedRelationTypesBrick,
            bricks.CustomFieldsBrick,
            bricks.BrickDetailviewLocationsBrick,
            bricks.BrickHomeLocationsBrick,
            bricks.BrickDefaultMypageLocationsBrick,
            bricks.BrickMypageLocationsBrick,
            bricks.RelationBricksConfigBrick,
            bricks.InstanceBricksConfigBrick,
            bricks.FieldsConfigsBrick,
            bricks.CustomBricksConfigBrick,
            bricks.ButtonMenuBrick,
            bricks.UsersBrick,
            bricks.TeamsBrick,
            bricks.SearchConfigBrick,
            bricks.HistoryConfigBrick,
            bricks.UserRolesBrick,
            bricks.UserSettingValuesBrick,
        )

    def register_menu(self, creme_menu):
        from django.urls import reverse_lazy as reverse

        from creme.creme_core import models as core_models

        from .gui import TimezoneItem, ConfigContainerItem

        URLItem = creme_menu.URLItem
        creme_menu.get('creme', 'user') \
                  .add(TimezoneItem('creme_config-timezone'), priority=5) \
                  .add(URLItem('my_settings', url=reverse('creme_config__user_settings'), label=_('My settings')),
                       priority=30,
                      )
        creme_menu.get('features') \
                  .add(ConfigContainerItem('creme_config')
                           .add(URLItem('creme_config-portal', url=reverse('creme_config__portal'),
                                        label=_('General configuration'), perm='creme_config',
                                       ),
                                priority=10
                               )
                           .add(creme_menu.ItemGroup('creme_config-portals')
                                   .add(URLItem('creme_config-blocks', url=reverse('creme_config__bricks'),
                                                label=_('Blocks'), perm='creme_config',
                                               ),
                                        priority=10
                                       )
                                   .add(URLItem('creme_config-custom_fields',
                                                url=reverse('creme_config__custom_fields'),
                                                label=core_models.CustomField._meta.verbose_name_plural,
                                                perm='creme_config',
                                               ),
                                        priority=20
                                       )
                                   .add(URLItem('creme_config-fields', url=reverse('creme_config__fields'),
                                                label=_('Fields'), perm='creme_config',
                                               ),
                                        priority=30
                                       )
                                   .add(URLItem('creme_config-history', url=reverse('creme_config__history'),
                                                label=_('History'), perm='creme_config',
                                               ),
                                        priority=40
                                       )
                                   .add(URLItem('creme_config-button_menu', url=reverse('creme_config__buttons'),
                                                label=_('Button menu'), perm='creme_config',
                                               ),
                                        priority=50
                                       )
                                   .add(URLItem('creme_config-search', url=reverse('creme_config__search'),
                                                label=_('Search'), perm='creme_config',
                                               ),
                                        priority=70
                                       )
                                   .add(URLItem('creme_config-roles', url=reverse('creme_config__roles'),
                                                label=_('Roles and credentials'), perm='creme_config',
                                               ),
                                        priority=80
                                       )
                                   .add(URLItem('creme_config-property_types', url=reverse('creme_config__ptypes'),
                                                label=core_models.CremePropertyType._meta.verbose_name_plural,
                                                perm='creme_config',
                                               ),
                                        priority=90
                                       )
                                   .add(URLItem('creme_config-relation_types', url=reverse('creme_config__rtypes'),
                                                label=core_models.RelationType._meta.verbose_name_plural,
                                                perm='creme_config',
                                               ),
                                        priority=100
                                       )
                                   .add(URLItem('creme_config-users', url=reverse('creme_config__users'),
                                                label=_('Users'), perm='creme_config',
                                               ),
                                        priority=110
                                       ),
                                priority=20
                               ),
                       priority=10000,
                      )
