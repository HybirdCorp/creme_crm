# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2018  Hybird
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
from sys import argv

from django.apps import AppConfig, apps
from django.core import checks
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from .checks import Tags, check_uninstalled_apps  # NB: it registers other checks too
from .core.reminder import reminder_registry
from .core.setting_key import setting_key_registry, user_setting_key_registry
from .gui import (creme_menu, brick_registry, bulk_update_registry, button_registry,
        fields_config_registry, field_printers_registry, icon_registry, import_form_registry,
        merge_form_registry, quickforms_registry, smart_columns_registry, statistics_registry)
from .registry import creme_registry


logger = logging.getLogger(__name__)


# Hooking of AppConfig ------------------

AppConfig.creme_app = False
AppConfig.extended_app = None  # If you extend an app by swapping its models. Eg: 'persons'
AppConfig._extending_app_configs = None

def __get_extending_app_configs(self):
    ext_app_configs = self._extending_app_configs

    if ext_app_configs is None:
        name = self.name
        ext_app_configs = self._extending_app_configs = [
            app_config
                for app_config in apps.get_app_configs()
                    if app_config.extended_app == name
            ]

    return ext_app_configs

AppConfig.get_extending_app_configs = __get_extending_app_configs


# Hooking of AppConfig [end] ------------

# TODO: remove when MediaGenerator is not used
class MediaGeneratorConfig(AppConfig):
    name = 'mediagenerator'
    verbose_name = 'Media generator'  # _(u'Media generator')

    def ready(self):
        self._build_MEDIA_BUNDLES()
        # self._fix_i18n_filter()

    def _build_MEDIA_BUNDLES(self):
        is_installed = apps.is_installed

        MEDIA_BUNDLES = (settings.CREME_I18N_JS,
                         settings.CREME_LIB_JS + tuple(js for app, js in settings.CREME_OPTLIB_JS if is_installed(app)),
                         settings.CREME_CORE_JS + tuple(js for app, js in settings.CREME_OPT_JS if is_installed(app))
                        )

        if settings.FORCE_JS_TESTVIEW:
            MEDIA_BUNDLES += (settings.TEST_CREME_LIB_JS,
                              settings.TEST_CREME_CORE_JS + tuple(js for app, js in settings.TEST_CREME_OPT_JS if is_installed(app))
                             )

        MEDIA_BUNDLES += settings.CREME_OPT_MEDIA_BUNDLES

        CREME_CSS = settings.CREME_CORE_CSS + tuple(css for app, css in settings.CREME_OPT_CSS if is_installed(app))
        MEDIA_BUNDLES += tuple((theme_dir + CREME_CSS[0], ) +
                               tuple(theme_dir + '/' + css_file if not isinstance(css_file, dict) else css_file
                                        for css_file in CREME_CSS[1:]
                                    )
                                for theme_dir, theme_vb_name in settings.THEMES
                              )

        settings.CREME_CSS = CREME_CSS  # For compatibility (should not be useful)
        settings.MEDIA_BUNDLES = MEDIA_BUNDLES

    # def _fix_i18n_filter(self):
    #     # NB: we do not fix in creme.__init__ because it does not work well (strange loading behaviour).
    #
    #     # Code copied from mediagenerator/filters/i18n.py ----------------------
    #     #  Copyright (c) Waldemar Kornewald, Thomas Wanschik, and all contributors.
    #     #  Copyright 2016 - Hybird
    #     #  BSD License
    #     from django.http import HttpRequest
    #     from django.views.i18n import javascript_catalog
    #
    #     def _generate(self, language):
    #         language_bidi = language.split('-')[0] in settings.LANGUAGES_BIDI
    #         request = HttpRequest()
    #         request.GET['language'] = language
    #         # Add some JavaScript data
    #         content = 'var LANGUAGE_CODE = "%s";\n' % language
    #         content += 'var LANGUAGE_BIDI = ' + \
    #             (language_bidi and 'true' or 'false') + ';\n'
    #
    #         # content += javascript_catalog(request,
    #         #     packages=settings.INSTALLED_APPS).content
    #
    #         # DAT FIX
    #         content += javascript_catalog(
    #                         request,
    #                         packages=[app_config.name for app_config in apps.app_configs.values()],
    #                     ).content
    #
    #         # The hgettext() function just calls gettext() internally, but
    #         # it won't get indexed by makemessages.
    #         content += '\nwindow.hgettext = function(text) { return gettext(text); };\n'
    #         # Add a similar hngettext() function
    #         content += 'window.hngettext = function(singular, plural, count) { return ngettext(singular, plural, count); };\n'
    #         return content
    #
    #     # Code copied from mediagenerator/filters/i18n.py [END]-----------------
    #
    #     from mediagenerator.filters.i18n import I18N
    #     I18N._generate = _generate


class CremeAppConfig(AppConfig):
    creme_app = True   # True => App can be used by some services
                       #        (urls.py automatically used, 'creme_populate command' etc...)
    dependencies = ()  # Names of the apps on which this app depends ;
                       # an error is raised if the dependencies are not installed.
                       # Eg: ['creme.persons']

    CRED_NONE    = 0b00
    CRED_REGULAR = 0b01
    CRED_ADMIN   = 0b10
    credentials = CRED_REGULAR|CRED_ADMIN

    # Lots of problems with ContentType table which can be not created yet.
    # MIGRATION_MODE = ('migrate' in argv)
    MIGRATION_MODE = any(cmd in argv for cmd in settings.NO_SQL_COMMANDS)  # TODO: rename

    @property
    def url_root(self):
        return self.label + '/'

    def ready(self):
        # NB: it seems we cannot transform this a check_deps(self, **kwargs) method
        # because we get an error from django [AttributeError: 'instancemethod' object has no attribute 'tags']
        @checks.register(Tags.settings)
        def check_deps(**kwargs):
            return [checks.Error("depends on the app '%s' which is not installed." % dep,
                                 hint='Check the INSTALLED_CREME_APPS setting in your'
                                      ' local_settings.py/project_settings.py',
                                 obj=self.name,
                                 id='creme.E001',
                                )
                        for dep in self.dependencies
                            if not apps.is_installed(dep)
                   ]

        @checks.register(Tags.settings)
        def check_extended_app(**kwargs):
            errors = []
            app_name = self.extended_app

            if app_name is not None:
                if not apps.is_installed(app_name):
                    errors.append(checks.Error("extends the app '%s' which is not installed." % app_name,
                                               hint='Check the INSTALLED_CREME_APPS setting in your'
                                                    ' local_settings.py/project_settings.py',
                                               obj=self.name,
                                               id='creme.E006',
                                              )
                                 )

                if self.credentials != self.CRED_NONE:
                    errors.append(checks.Error("The app '%s' is an extending app & "
                                               "so it cannot have its own credentials." % self.name,
                                               hint='Set "credentials = CremeAppConfig.CRED_NONE" in the AppConfig.',
                                               obj=self.name,
                                               id='creme.E007',
                                              )
                                 )

            return errors

    def all_apps_ready(self):
        if not self.MIGRATION_MODE:
            if hasattr(self, 'register_creme_app'):
                logger.critical('The AppConfig for "%s" has a method register_creme_app() which is now useless.', self.name)

            self.register_entity_models(creme_registry)

            self.register_bricks(brick_registry)
            # if hasattr(self, 'register_blocks'):
            #     warnings.warn('The AppConfig for "%s" has a method "register_blocks()" which is now deprecated ; '
            #                   'you should rename it register_bricks().' % self.name,
            #                   DeprecationWarning
            #                  )
            #     self.register_blocks(brick_registry)

            self.register_bulk_update(bulk_update_registry)
            self.register_buttons(button_registry)
            self.register_fields_config(fields_config_registry)
            self.register_field_printers(field_printers_registry)
            self.register_icons(icon_registry)
            self.register_mass_import(import_form_registry)
            self.register_menu(creme_menu)
            self.register_merge_forms(merge_form_registry)
            self.register_quickforms(quickforms_registry)
            self.register_reminders(reminder_registry)
            self.register_setting_key(setting_key_registry)
            self.register_statistics(statistics_registry)
            self.register_user_setting_keys(user_setting_key_registry)
            self.register_smart_columns(smart_columns_registry)

    def register_entity_models(self, creme_registry):
        pass

    def register_bricks(self, brick_registry):
        pass

    def register_bulk_update(self, bulk_update_registry):
        pass

    def register_buttons(self, button_registry):
        pass

    def register_fields_config(self, fields_config_registry):
        pass

    def register_field_printers(self, field_printers_registry):
        pass

    def register_icons(self, icon_registry):
        pass

    def register_mass_import(self, import_form_registry):
        pass

    def register_menu(self, creme_menu):
        pass

    def register_merge_forms(self, merge_form_registry):
        pass

    def register_quickforms(self, quickforms_registry):
        pass

    def register_reminders(self, reminder_registry):
        pass

    def register_setting_key(self, setting_key_registry):
        pass

    def register_smart_columns(self, smart_columns_registry):
        pass

    def register_statistics(self, statistics_registry):
        pass

    def register_user_setting_keys(self, user_setting_key_registry):
        pass


class CremeCoreConfig(CremeAppConfig):
    name = 'creme.creme_core'
    verbose_name = _(u'Core')

    @property
    def url_root(self):
        return ''  # We want to catch some URLs which do not start by 'creme_core/'

    def ready(self):
        super(CremeCoreConfig, self).ready()

        if self.MIGRATION_MODE:
            return

        checks.register(Tags.settings)(check_uninstalled_apps)  # Crashes in migrate mode.
        self.hook_fk_formfield()
        self.hook_m2m_formfield()
        self.hook_datetime_widgets()
        self.hook_multiselection_widgets()
        self.hook_widget_render()

        if settings.TESTS_ON:
            from .tests.fake_apps import ready
            ready()

    def register_menu(self, creme_menu):
        from django.core.urlresolvers import reverse_lazy as reverse

        if settings.OLD_MENU:
            reg_app = creme_menu.register_app
            reg_app('creme_core', reverse('creme_core__home'),    _(u'Home'),    force_order=0)
            reg_app('my_page',    reverse('creme_core__my_page'), _(u'My page'), force_order=1)  # HACK: see creme_core/auth/backend.py
        else:
            from .gui.menu import (ItemGroup, ContainerItem, URLItem, TrashItem, LastViewedEntitiesItem,
                    QuickCreationItemGroup, CreationFormsItem)
            from .gui.quick_forms import quickforms_registry

            creme_menu.add(ContainerItem('creme', label='Creme')
                              .add(URLItem('home', url=reverse('creme_core__home'), label=_(u'Home')), priority=10)
                              .add(TrashItem('trash'), priority=20)  # TODO: icon ?
                              .add(ItemGroup('user', label=_(u'User'))
                                      .add(URLItem('my_page', url=reverse('creme_core__my_page'), label=_(u'My page')),
                                           priority=10,
                                          )
                                      .add(URLItem('my_jobs', url=reverse('creme_core__my_jobs'), label=_(u'My jobs')),
                                           priority=20,
                                          ),
                                   priority=30,
                                  )
                              .add(URLItem('logout', url=reverse('creme_logout'), label=_(u'Log out')), priority=40),
                           priority=10,
                          ) \
                      .add(ItemGroup('features')
                                .add(ContainerItem('tools', label=_(u'Tools'))
                                        .add(URLItem('creme_core-jobs', url=reverse('creme_core__jobs'),
                                                     label=_(u'Jobs'), perm=lambda user: user.is_superuser  # TODO: '*superuser*'' ?
                                                    ),
                                             priority=5,
                                            ),
                                     priority=100,
                                    ),
                           priority=20,
                          ) \
                      .add(ContainerItem('creation', label=_(u'+ Creation'))
                               .add(ItemGroup('main_entities', label=_(u'Main entities')), priority=10)
                               .add(QuickCreationItemGroup('quick_forms', registry=quickforms_registry), priority=20)
                               .add(CreationFormsItem('any_forms', label=_(u'Other type of entity')), priority=30),
                           priority=30,
                          ) \
                      .add(LastViewedEntitiesItem('recent_entities', label=_(u'Recent entities')), priority=40)

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(bricks.PropertiesBrick,
                                bricks.RelationsBrick,
                                bricks.CustomFieldsBrick,
                                bricks.HistoryBrick,
                                bricks.TrashBrick,
                                bricks.StatisticsBrick,
                                bricks.JobBrick,
                                bricks.JobsBrick,
                                bricks.MyJobsBrick,
                               )

    def register_bulk_update(self, bulk_update_registry):
        from .models import CremeProperty

        bulk_update_registry.register(CremeProperty, exclude=('type', 'creme_entity'))  # TODO: tags modifiable=False ??

    def register_setting_key(self, setting_key_registry):
        from .setting_keys import block_opening_key, block_showempty_key, currency_symbol_key

        setting_key_registry.register(block_opening_key, block_showempty_key,
                                      currency_symbol_key,
                                     )

    # TODO: better API + move some code to creme_config ??
    @staticmethod
    def hook_fk_formfield():
        from django.db.models import ForeignKey

        from .forms.fields import CreatorEntityField
        from .models import CremeEntity

        from creme.creme_config.forms.fields import CreatorModelChoiceField

        original_fk_formfield = ForeignKey.formfield

        def new_fk_formfield(self, **kwargs):
            if issubclass(self.rel.to, CremeEntity):
                return CreatorEntityField(label=self.verbose_name,
                                          model=self.rel.to,
                                          required=not self.blank,
                                          q_filter=self.rel.limit_choices_to,
                                         )

            defaults = {'form_class': CreatorModelChoiceField}
            defaults.update(kwargs)

            return original_fk_formfield(self, **defaults)

        ForeignKey.formfield = new_fk_formfield

    # TODO: see hook_fk_formfield()
    @staticmethod
    def hook_m2m_formfield():
        from django.db.models import ManyToManyField

        from .forms.fields import MultiCreatorEntityField
        from .models import CremeEntity

        from creme.creme_config.forms.fields import CreatorModelMultipleChoiceField

        original_m2m_formfield = ManyToManyField.formfield

        def new_m2m_formfield(self, **kwargs):
            if issubclass(self.rel.to, CremeEntity):
                return MultiCreatorEntityField(label=self.verbose_name,
                                               model=self.rel.to,
                                               required=not self.blank,
                                               q_filter=self.rel.limit_choices_to,
                                              )

            defaults = {'form_class': CreatorModelMultipleChoiceField}
            defaults.update(kwargs)

            return original_m2m_formfield(self, **defaults)

        ManyToManyField.formfield = new_m2m_formfield

    @staticmethod
    def hook_datetime_widgets():
        from django import forms

        from creme.creme_core.forms import widgets

        forms.DateField.widget     = widgets.CalendarWidget
        forms.DateTimeField.widget = widgets.DateTimeWidget
        forms.TimeField.widget     = widgets.TimeWidget

    @staticmethod
    def hook_multiselection_widgets():
        from django import forms

        from creme.creme_core.forms import widgets

        forms.MultipleChoiceField.widget = forms.ModelMultipleChoiceField.widget = \
             widgets.UnorderedMultipleChoiceWidget

    @staticmethod
    def hook_widget_render():
        from django.forms.widgets import Widget

        def build_attrs(self, extra_attrs=None, **kwargs):
            attrs = dict(self.attrs, **kwargs)

            if self.is_required:
                attrs['required'] = ''

            if extra_attrs:
                attrs.update(extra_attrs)

            return attrs


        Widget.build_attrs = build_attrs


def creme_app_configs():
    for app_config in apps.get_app_configs():
        if app_config.creme_app:
            yield app_config


def extended_app_configs(app_labels):
    """Get the AppConfigs corresponding to given labels, & their extending AppConfigs.
    @param app_labels: Iterable of app labels (eg: ['persons', documents']).
    @return: Set of AppConfig instances.
    """
    get_app_config = apps.get_app_config
    app_configs = set()

    for label in app_labels:
        try:
            app_config = get_app_config(label)
        except LookupError:
            logger.warn('The app "%s" seems not installed.', label)
        else:
            app_configs.add(app_config)
            app_configs.update(app_config.get_extending_app_configs())

    return app_configs
