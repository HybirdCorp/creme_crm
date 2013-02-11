# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.utils.translation import ugettext as _
from django.forms.models import ModelChoiceField
from django.contrib.contenttypes.models import ContentType

from creme_core.forms.widgets import ActionButtonList, DynamicSelect


class CreatorModelChoiceField(ModelChoiceField):
    def __init__(self, queryset, create_action_url=None, *args, **kwargs):
        super(CreatorModelChoiceField, self).__init__(queryset=queryset, *args, **kwargs)
        #self.widget = ActionButtonList(delegate=DynamicSelect(options=self._get_choices))
        self.user = None
        self.create_action_url = create_action_url

    #@ModelChoiceField.queryset.setter
    #def queryset(self, queryset):
        #self._queryset = queryset
        #self._build_widget()

    @property
    def create_action_url(self):
        return self._create_action_url

    @create_action_url.setter
    def create_action_url(self, url):
        self._create_action_url = url
        #self._build_actions()
        self._build_widget()

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        #TODO: if None, use a Select as widget ??
        self._user = user
        #self._build_actions()
        self._build_widget()

    def _build_create_action_url(self, app_name, model_name):
        if self._create_action_url:
            return self._create_action_url

        return '/creme_config/%s/%s/add_widget/' % (app_name, model_name)

    def _build_widget(self):
        #self.widget = ActionButtonList(delegate=DynamicSelect(options=self._get_choices))
        #self._build_actions()

    #def _build_actions(self):
        #if isinstance(self.widget, ActionButtonList):
        #self.widget.clear_actions()

        #if not hasattr(self, '_user') or self.user is None:
            #return

        user = self.user

        if user is None:
            self.widget = ModelChoiceField.widget(choices=self.choices)
            return

        # config_registry import here, in order to avoid  initialisation issues :
        # creme_config's registration could be done before the creme_core's one is over,
        # and so fails because not all apps are registered.
        from creme_config.registry import config_registry, NotRegisteredInConfig

        model = self.queryset.model
        app_name = model._meta.app_label
        model_ct_id = ContentType.objects.get_for_model(model).id

        try:
            model_name = config_registry.get_app(app_name).get_model_conf(model_ct_id).name_in_url
        except (KeyError, NotRegisteredInConfig):
            pass #we will use a classical ModelChoiceField
        else:
            allowed = user.has_perm_to_admin(app_name)
            self.widget = widget = ActionButtonList(delegate=DynamicSelect(options=self._get_choices))
            widget.add_action('create', _(u'Add'), enabled=allowed,
                              title=_(u'Add') if allowed else _(u"Can't add"),
                              url=self._build_create_action_url(app_name, model_name),
                             )
