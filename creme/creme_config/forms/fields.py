# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from typing import Tuple

from django.forms import fields
from django.forms import models as modelforms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms.widgets import UnorderedMultipleChoiceWidget

from ..registry import config_registry
from .widgets import CreatorModelChoiceWidget


class CreatorChoiceMixin:
    _create_action_url = ''
    _user = None

    creation_label = 'Create'

    @property
    def creation_url_n_allowed(self) -> Tuple[str, bool]:
        """Get the creation URL & if the creation is allowed."""
        return self._create_action_url, False

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
        widget.creation_label = self.creation_label

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user
        self._update_creation_info()


class CreatorModelChoiceMixin(CreatorChoiceMixin):
    # _create_action_url = None

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

    @property
    def creation_label(self):
        return getattr(self.queryset.model, 'creation_label', self.widget.creation_label)


class CreatorModelChoiceField(modelforms.ModelChoiceField,
                              CreatorModelChoiceMixin):
    widget = CreatorModelChoiceWidget

    def __init__(self, *, queryset, create_action_url='', user=None, **kwargs):
        super().__init__(queryset, **kwargs)
        self.creation_info(create_action_url, user)


class CreatorModelMultipleChoiceField(modelforms.ModelMultipleChoiceField,
                                      CreatorModelChoiceMixin):
    widget = UnorderedMultipleChoiceWidget

    def __init__(self, *, queryset, create_action_url='', user=None, **kwargs):
        super().__init__(queryset, **kwargs)
        self.creation_info(create_action_url, user)


class CreatorCustomEnumChoiceMixin(CreatorChoiceMixin):
    _custom_field = None

    creation_label = _('Create a choice')

    @property
    def creation_url_n_allowed(self):
        user = self._user
        cfield = self._custom_field
        url = self._create_action_url

        if user and cfield:
            if not url:
                url = reverse('creme_config__add_custom_enum', args=(cfield.id,))

            allowed = user.has_perm_to_admin('creme_core')
        else:
            # url = ''
            allowed = False

        return url, allowed

    @property
    def custom_field(self):
        return self._custom_field

    @custom_field.setter
    def custom_field(self, cfield):
        self._custom_field = cfield
        self._update_creation_info()


class CustomEnumChoiceField(CreatorCustomEnumChoiceMixin,
                            fields.TypedChoiceField):
    widget = CreatorModelChoiceWidget

    def __init__(self, *, custom_field=None, user=None, **kwargs):
        super().__init__(coerce=int, **kwargs)
        self.custom_field = custom_field
        self.user = user


class CustomMultiEnumChoiceField(CreatorCustomEnumChoiceMixin,
                                 fields.TypedMultipleChoiceField):
    # widget = UnorderedMultipleChoiceWidget

    def __init__(self, *, custom_field=None, user=None, **kwargs):
        super().__init__(coerce=int, **kwargs)
        self.custom_field = custom_field
        self.user = user
