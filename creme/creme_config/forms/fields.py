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

from django.utils.translation import ugettext as _
from django.forms.models import ModelChoiceField
from django.contrib.contenttypes.models import ContentType

from creme_core.forms.widgets import ActionButtonList, DynamicSelect


class CreatorModelChoiceField(ModelChoiceField):
    def _set_queryset(self, queryset):
        self._queryset = queryset
        self._build_widget() 

    queryset = property(ModelChoiceField._get_queryset, _set_queryset)

    @property
    def create_action_url(self):
        return self._create_action_url

    @create_action_url.setter
    def create_action_url(self, url):
        self._create_action_url = url
        self._build_actions()

    def __init__(self, queryset, create_action_url=None, *args, **kwargs):
        super(CreatorModelChoiceField, self).__init__(queryset=queryset, *args, **kwargs) 
        self.widget = ActionButtonList(delegate=DynamicSelect(options=self._get_choices))
        self.user = None
        self.create_action_url = create_action_url

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user
        self._build_actions()

    def _build_create_action_url(self, app_name, model_name):
        if self._create_action_url:
            return self._create_action_url

        return '/creme_config/%s/%s/add_widget/' % (app_name, model_name)

    def _build_widget(self):
        self.widget = ActionButtonList(delegate=DynamicSelect(options=self._get_choices))
        self._build_actions()

    def _build_actions(self):
        self.widget.clear_actions()

        if not hasattr(self, '_user') or self.user is None:
            return

        user = self.user

        # config_registry import is moved here to prevent many initialisation order issues in unit tests
        #TODO : see if autodiscover can be move
        from creme_config.registry import config_registry

        model = self.queryset.model
        app_name = model._meta.app_label
        model_ct_id = ContentType.objects.get_for_model(model).id
        model_name = config_registry.get_app(app_name).get_model_conf(model_ct_id).name_in_url

        allowed = user.has_perm_to_admin(app_name)
        self.widget.add_action('create', _(u'Add'), enabled=allowed,
                                                    title=_(u'Add') if allowed else _(u"Can't add"),
                                                    url=self._build_create_action_url(app_name, model_name))
