# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from copy import deepcopy
from typing import Tuple

from django.forms import ValidationError, fields
from django.forms import models as modelforms
from django.forms.fields import CallableChoiceIterator
from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms.widgets import UnorderedMultipleChoiceWidget
from creme.creme_core.gui import menu

from ..registry import config_registry
from . import widgets


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
    widget = widgets.CreatorModelChoiceWidget

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
    widget = widgets.CreatorModelChoiceWidget

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


class MenuEntriesField(fields.JSONField):
    default_error_messages = {
        'invalid_type': 'Enter a valid JSON list of dictionaries.',
        'invalid_data': _('Enter a valid list of entries: %(error)s.'),
    }
    widget = widgets.MenuEditionWidget

    class EntryCreator:
        def __init__(self, entry_class, label=None):
            self.label = entry_class.creation_label if label is None else label
            self.entry_class = entry_class

        def __eq__(self, other):
            return self.label == other.label and self.entry_class == other.entry_class

        @property
        def url(self):
            return reverse(
                'creme_config__add_menu_special_level1',
                args=(self.entry_class.id,),
            )

    default_extra_entry_creators = [
        EntryCreator(entry_class=menu.Separator1Entry),
        EntryCreator(entry_class=menu.CustomURLEntry),
    ]

    def __init__(self, *,
                 menu_registry=None,
                 entry_level=1,
                 excluded_entry_ids=(),
                 extra_entry_creators=None,
                 **kwargs):
        super().__init__(**kwargs)
        self.menu_registry = menu_registry or menu.menu_registry
        self.entry_level = entry_level
        self.excluded_entry_ids = excluded_entry_ids
        self.extra_entry_creators = (
            deepcopy(self.default_extra_entry_creators)
            if extra_entry_creators is None else
            extra_entry_creators  # TODO: copy too ?
        )

        self._refresh_widget()

    def __deepcopy__(self, memo):
        result = super().__deepcopy__(memo)
        result._refresh_widget()

        return result

    def _get_regular_entries_options(self):
        excluded = {
            *self.excluded_entry_ids,
            *(creator.entry_class.id for creator in self._extra_entry_creators),
        }
        level = self.entry_level

        for cls in self.menu_registry.entry_classes:
            entry_id = cls.id
            if entry_id not in excluded and cls.level == level:
                yield entry_id, cls().label

    def _refresh_widget(self):
        self.widget.regular_entry_choices = CallableChoiceIterator(
            self._get_regular_entries_options
        )

    def prepare_value(self, value):
        if isinstance(value, list) and value:
            def entry_choice(sub_value):
                if isinstance(sub_value, menu.MenuEntry):
                    e_value = {'id': sub_value.id}

                    data = sub_value.data
                    if data:
                        e_value['data'] = data

                    return {'label': str(sub_value.label), 'value': e_value}
                elif isinstance(sub_value, dict):
                    entry_id = sub_value.get('id')
                    if not isinstance(entry_id, str):
                        return sub_value

                    entry_class = self.menu_registry.get_class(entry_id)
                    if entry_class is None:
                        return sub_value

                    entry_data = sub_value.get('data')
                    if entry_data is not None and not isinstance(entry_data, dict):
                        return sub_value

                    # TODO: entry_class.validate(entry_data) ??
                    return {
                        'label': str(entry_class(data=entry_data).label),
                        'value': sub_value,
                    }
                else:
                    return sub_value

            value = [entry_choice(v) for v in value]

        return super().prepare_value(value)

    @property
    def extra_entry_creators(self):
        yield from self._extra_entry_creators

    @extra_entry_creators.setter
    def extra_entry_creators(self, creators):
        self._extra_entry_creators = self.widget.extra_entry_creators = creators

    def _raise_invalid_data(self, error):
        raise ValidationError(
            self.error_messages['invalid_data'],
            code='invalid_data',
            params={'error': error},
        )

    def to_python(self, value):
        decoded_value = super().to_python(value)
        entries = []
        # user = self.user

        if decoded_value:
            if not isinstance(decoded_value, list):
                raise ValidationError(
                    self.error_messages['invalid_type'],
                    code='invalid_type',
                )

            registry = self.menu_registry

            excluded_entry_ids = {*self.excluded_entry_ids}
            for creator in self._extra_entry_creators:
                excluded_entry_ids.discard(creator.entry_class.id)

            for order, entry_dict in enumerate(decoded_value):
                if not isinstance(entry_dict, dict):
                    raise ValidationError(
                        self.error_messages['invalid_type'],
                        code='invalid_type',
                    )

                try:
                    entry_id = entry_dict['id']
                except KeyError:
                    self._raise_invalid_data(gettext('no entry ID'))

                data = entry_dict.get('data', None) or {}
                if not isinstance(data, dict):
                    self._raise_invalid_data('"{}" is not a dictionary'.format(data))

                entry_class = registry.get_class(entry_id)
                if (
                    entry_class is None
                    or entry_id in excluded_entry_ids
                    or entry_class.level != self.entry_level
                ):
                    self._raise_invalid_data(
                        gettext('the entry ID "{}" is invalid.').format(entry_id),
                    )

                try:
                    validated_data = entry_class.validate(data)
                except ValidationError as e:
                    self._raise_invalid_data(
                        gettext('the entry «{entry}» is invalid ({error})').format(
                            entry=str(entry_class.label) or entry_class.__name__,
                            error=', '.join(e.messages),
                        )
                    )

                entries.append(entry_class(data=validated_data))

        return entries


class BricksConfigField(fields.JSONField):
    widget = widgets.BricksConfigWidget
    zones = widgets.BricksConfigWidget.zones

    default_error_messages = {
        'invalid_format': _("The value doesn't match the expected format."),
        'invalid_choice': (
            fields.ChoiceField.default_error_messages['invalid_choice']
        ),
        'duplicated_brick': _(
            'The following block should be displayed only once: «%(block)s»'
        ),
        'required': _('Your configuration is empty !'),
    }

    def __init__(self, *, choices=(), **kwargs):
        if not kwargs.setdefault("required", True):
            raise NotImplementedError("BricksConfigField is a required field.")

        if 'initial' not in kwargs:
            kwargs['initial'] = {zone: [] for zone in self.zones.values()}

        super().__init__(**kwargs)
        self.choices = choices

    def __deepcopy__(self, memo):
        result = super().__deepcopy__(memo)
        result._choices = deepcopy(self._choices, memo)
        result._valid_choices = deepcopy(self._valid_choices, memo)
        return result

    @property
    def choices(self):
        return self._choices

    @choices.setter
    def choices(self, value):
        # Setting choices also sets the choices on the widget.
        # choices can be any iterable, but we call list() on it because
        # it will be consumed more than once.
        value = list(value)

        self._choices = self.widget.choices = value
        self._valid_choices = {
            choice_id for choice_id, choice_label in value
        }

    def clean(self, value: str):
        value = super().clean(value)

        if not isinstance(value, dict):
            raise ValidationError(
                self.error_messages['invalid_format'],
                code='invalid_format',
            )

        errors = []
        invalid_choices = set()
        duplicates = set()
        bricks = set()

        cleaned_value = {}
        for zone in self.zones.values():
            zone_value = value.get(zone, [])
            if not isinstance(zone_value, list):
                raise ValidationError(
                    self.error_messages['invalid_format'],
                    code='invalid_format',
                )

            for brick_id in zone_value:
                if brick_id not in self._valid_choices:
                    invalid_choices.add(brick_id)
                    continue

                if brick_id in bricks:
                    duplicates.add(brick_id)

                bricks.add(brick_id)

            cleaned_value[zone] = zone_value

        if invalid_choices:
            errors.extend(
                ValidationError(
                    self.error_messages['invalid_choice'],
                    code='invalid_choice',
                    params={'value': value},
                )
                for value in invalid_choices
            )

        if duplicates:
            errors.extend(
                ValidationError(
                    self.error_messages['duplicated_brick'],
                    params={'block': brick.verbose_name},
                    code='duplicated_brick',
                )
                for brick_id, brick in self.choices
                if brick_id in duplicates
            )

        if errors:
            raise ValidationError(errors)

        if not bricks:
            raise ValidationError(
                self.error_messages['required'],
                code='required')

        return cleaned_value
