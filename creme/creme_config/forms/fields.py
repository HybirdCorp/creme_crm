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

from django.forms.models import ModelChoiceField, ModelMultipleChoiceField

from creme.creme_core.forms.widgets import UnorderedMultipleChoiceWidget

from .widgets import CreatorModelChoiceWidget

from ..registry import config_registry


class CreatorModelChoiceMixin:
    _create_action_url = None
    _user = None

    @property
    def creation_url_n_allowed(self):
        """Get the creation URL & if the creation is allowed.
        @rtype : tuple (string, boolean)
        """
        allowed = False
        user = self._user
        url = self._create_action_url

        if user:
            model = self.queryset.model

            if url:
                app_name = model._meta.app_label
                allowed = user.has_perm_to_admin(app_name)
            else:
                url, allowed = config_registry.get_model_creation_info(model, user)

        return url, allowed

    def creation_info(self, create_action_url, user):
        self._create_action_url = create_action_url
        self._user = user
        self._update_creation_info()

    @property
    def create_action_url(self):
        return self.creation_url_n_allowed[0]

    @create_action_url.setter
    def create_action_url(self, url):
        self._create_action_url = url
        self._update_creation_info()

    def _update_creation_info(self):
        widget = self.widget
        widget.creation_url, widget.creation_allowed = self.creation_url_n_allowed
        widget.creation_label = getattr(self.queryset.model, 'creation_label', widget.creation_label)

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user
        self._update_creation_info()


class CreatorModelChoiceField(ModelChoiceField, CreatorModelChoiceMixin):
    widget = CreatorModelChoiceWidget

    # def __init__(self, queryset, create_action_url='', user=None, *args, **kwargs):
    def __init__(self, *, queryset, create_action_url='', user=None, **kwargs):
        # super().__init__(queryset, *args, **kwargs)
        super().__init__(queryset, **kwargs)
        self.creation_info(create_action_url, user)


class CreatorModelMultipleChoiceField(ModelMultipleChoiceField, CreatorModelChoiceMixin):
    widget = UnorderedMultipleChoiceWidget

    # def __init__(self, queryset, create_action_url='', user=None, *args, **kwargs):
    def __init__(self, *, queryset, create_action_url='', user=None, **kwargs):
        # super().__init__(queryset, *args, **kwargs)
        super().__init__(queryset, **kwargs)
        self.creation_info(create_action_url, user)
