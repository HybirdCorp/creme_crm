################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2022-2025  Hybird
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

import logging
from collections import OrderedDict

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Model
from django.forms import models as mforms
from django.forms import widgets
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from ..core import enumerable

logger = logging.getLogger(__name__)

NULL = 'NULL'
NO_LIMIT = -1
DEFAULT_LIMIT = 50


def get_form_enumerable_limit():
    try:
        return int(getattr(settings, 'FORM_ENUMERABLE_LIMIT', DEFAULT_LIMIT))
    except ValueError:
        return DEFAULT_LIMIT


class EnumerableChoice:
    def __init__(self, value, label, *, help='', group=None,
                 disabled=False, selected=False, pinned=False):
        self.value = value
        self.disabled = disabled
        self.selected = selected
        self.help = help
        self.label = label
        self.group = group
        self.pinned = pinned

    def __str__(self):
        # NB: important for django.forms.fields.ChoiceField.valid_value()
        #     to consider the choice as valid
        return str(self.value)

    def as_dict(self):
        return {
            'value': self.value,
            'label': self.label,
            'help': self.help,
            'group': self.group,
            'disabled': self.disabled,
            'selected': self.selected,
            'pinned': self.pinned,
        }


class EnumerableChoiceSet:
    def __init__(self, enumerator: enumerable.Enumerator, *,
                 user=None, empty_label=None,
                 limit: int | None = None,
                 url: str | None = None,  # TODO: useless?
                 ):
        """ Build choices for the EnumerableSelect widget.

        @param enumerator: Enumerator instance.
        @param user: CremeUser instance. Used to check visibility permissions.
        @param limit: Max available choices for initial the widget (no limit: -1).
               Do not limit the selected values.
        @param url: URL used by the client-side widget to get the next choices.
        """
        limit = limit or get_form_enumerable_limit()

        self.user = user
        self.empty_label = empty_label
        self.limit = limit
        self.url = url
        self.enumerator = enumerator

    @property
    def limit(self):
        return self._limit

    @limit.setter
    def limit(self, limit: int | None):
        if limit is not None and limit != NO_LIMIT:
            limit = max(limit, 1)

        self._limit = limit

    def choices(self, selected_values=None, limit=None):
        selected_values = set(selected_values or ())
        selected_count = len(selected_values)

        choices = []
        limit = limit or self.limit

        def pop_selected(value):
            try:
                selected_values.remove(value)
                return True
            except KeyError:
                return False

        if limit == NO_LIMIT:
            # Get all the elements
            more = False
            choices = [
                EnumerableChoice(**choice, selected=pop_selected(choice['value']))
                for choice in self.enumerator.choices(
                    user=self.user,
                )
            ]
        elif selected_count < limit:
            # Get the first "page" with one more item
            choices = [
                EnumerableChoice(**choice, selected=pop_selected(choice['value']))
                for choice in self.enumerator.choices(
                    user=self.user,
                    limit=limit + 1
                )
            ]

            # Check if there is more items than limit
            more = len(choices) > limit

            # If there's more, we should remove the last item but
            # only if it is not selected
            if more and not choices[-1].selected:
                choices.pop()

            # Append the selected items outside range
            if selected_values:
                choices.extend(
                    EnumerableChoice(**choice, selected=True)
                    for choice in self.enumerator.choices(
                        user=self.user,
                        only=selected_values
                    )
                )
        else:
            # The selected items count is greater than the limit, so we obviously need more
            more = True
            choices = [
                EnumerableChoice(**choice, selected=True)
                for choice in self.enumerator.choices(
                    user=self.user,
                    only=selected_values
                )
            ]

        if self.empty_label:
            choices = [EnumerableChoice('', label=self.empty_label), *choices]

        return choices, more

    def groups(self, selected_values=None, limit=None):
        choices, more = self.choices(selected_values=selected_values, limit=limit)
        return self.group_choices(choices), more

    def group_choices(self, choices):
        groups = OrderedDict()

        for choice in choices:
            group_choices = groups.get(choice.group)

            if group_choices is None:
                groups[choice.group] = group_choices = []

            group_choices.append(choice)

        return groups.items()

    def to_python(self, values):
        return self.enumerator.to_python(self.user, values)


class FieldEnumerableChoiceSet(EnumerableChoiceSet):
    enumerable_registry = enumerable.enumerable_registry

    def __init__(self, field, *,
                 user=None, empty_label=None,
                 registry: enumerable.EnumerableRegistry | None = None,
                 enumerator: enumerable.Enumerator | None = None,
                 limit: int | None = None,
                 url: str | None = None,
                 ):
        self.field = field

        if enumerator is None:
            registry = registry or self.enumerable_registry
            enumerator = self.get_field_enumerator(registry, field)

        super().__init__(
            enumerator,
            user=user, empty_label=empty_label, limit=limit, url=url,
        )

    def get_field_enumerator(self, registry, field):
        try:
            return registry.enumerator_by_field(field)
        except ValueError:
            logger.debug(
                'Unable to find an enumerator for the field "%s" '
                "(ignore this if it's at startup)", field
            )
            # TODO : field.related_model.all() ?
            return enumerable.EmptyEnumerator(field)

    @property
    def url(self):
        # Using a lazy property to prevent import loops with default_url at startup.
        return self._url or self.default_url

    @url.setter
    def url(self, url: str | None):
        self._url = url

    @property
    def default_url(self):
        ctype = ContentType.objects.get_for_model(self.field.model)
        return reverse(
            'creme_core__enumerable_choices', args=(ctype.id, self.field.name)
        )


class EnumerableSelect(widgets.Select):
    template_name = 'creme_core/forms/widgets/enumerable.html'
    option_template_name = 'creme_core/forms/widgets/enhanced-option.html'
    create_url = None

    # Set the default debounce delay to 300ms to reduce the number of API calls.
    # The default value in the JS component is 100ms.
    ENUMERABLE_DEFAULT_DEBOUNCE_DELAY = 300

    def __init__(self,
                 enumerable: EnumerableChoiceSet | None = None,
                 attrs=None, create_url=None,
                 ):
        super().__init__(attrs=attrs, choices=())  # TODO: options or ()
        self.enumerable = enumerable
        self.create_url = create_url or self.create_url

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        enumerable = self.enumerable

        choices, more = enumerable.groups(
            selected_values=[value] if value else None
        ) if enumerable is not None else ((), False)

        context['widget']['choices'] = choices
        self.build_enum_attrs(context['widget']['attrs'], more)

        return context

    def build_enum_attrs(self, attrs, more):
        if more:
            attrs.update({
                'data-enum-url': self.enumerable.url,
                'data-enum-limit': self.enumerable.limit,
            })
            attrs.setdefault('data-enum-cache', 'true')
            attrs.setdefault('data-enum-debounce', self.ENUMERABLE_DEFAULT_DEBOUNCE_DELAY)

        attrs['data-allow-clear'] = str(not self.is_required).lower()

        if self.enumerable.empty_label:
            attrs['data-placeholder'] = self.enumerable.empty_label

        if self.create_url:
            attrs['data-create-url'] = self.create_url

        return attrs


class EnumerableSelectMultiple(EnumerableSelect):
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        try:
            getter = data.getlist
        except AttributeError:
            getter = data.get
        return getter(name)

    def value_omitted_from_data(self, data, files, name):
        # An unselected <select multiple> doesn't appear in POST data, so it's
        # never known if the value is actually omitted.
        return False


class EnumerableChoiceField(mforms.ChoiceField):
    widget: type[EnumerableSelect] = EnumerableSelect

    default_error_messages = {
        'invalid_choice': _(
            'Select a valid choice. That choice is not one of the available choices.'
        ),
    }

    def __init__(self, enum: EnumerableChoiceSet, *, empty_label="---------",
                 required=True, label=None, initial=None, help_text='',
                 **kwargs):
        # Call Field instead of ChoiceField __init__() because we don't need
        # ChoiceField.__init__(). See ModelChoiceField implementation.
        mforms.Field.__init__(
            self, required=required, label=label,
            initial=initial, help_text=help_text,
            **kwargs
        )

        self.enum = enum

        if required and initial is not None:
            self.empty_label = None
        else:
            self.empty_label = empty_label

    def __deepcopy__(self, memo):
        result = mforms.Field.__deepcopy__(self, memo)
        # Deepcopy do not work with EnumerableChoiceSet, so we have to build
        # a new one.
        result.enum = self.enumerable(
            field=self._enum.field,
            user=self._enum.user,
            limit=self._enum.limit,
            empty_label=self._enum.empty_label
        )

        return result

    @property
    def enum(self):
        return self._enum

    @enum.setter
    def enum(self, enum: EnumerableChoiceSet):
        self.widget.enumerable = self._enum = enum

    @property
    def limit(self):
        return self._enum.limit

    @limit.setter
    def limit(self, limit: int | None):
        self._enum.limit = limit

    @property
    def choices(self):
        return self._enum.choices()[0]

    @property
    def user(self):
        return self._enum.user

    @user.setter
    def user(self, user):
        self._enum.user = user

    @property
    def empty_label(self):
        return self._enum.empty_label

    @empty_label.setter
    def empty_label(self, label):
        self._enum.empty_label = label

    def prepare_value(self, value):
        if hasattr(value, '_meta'):
            return value.pk

        return super().prepare_value(value)

    def to_python(self, value):
        if value in self.empty_values:
            return None

        try:
            return self._enum.to_python([value])[0]
        except (ValueError, TypeError, IndexError) as e:
            raise ValidationError(
                self.error_messages['invalid_choice'],
                code='invalid_choice',
            ) from e

    def validate(self, value):
        return mforms.Field.validate(self, value)

    def has_changed(self, initial, data):
        if self.disabled:
            return False
        initial_value = initial if initial is not None else ''
        data_value = data if data is not None else ''
        return str(self.prepare_value(initial_value)) != str(data_value)


class EnumerableModelChoiceField(EnumerableChoiceField):
    enumerable: type[FieldEnumerableChoiceSet] = FieldEnumerableChoiceSet
    widget: type[EnumerableSelect] = EnumerableSelect

    def __init__(self, model: type[Model], field_name: str, *, user=None, initial=None,
                 limit=None, **kwargs):
        field = model._meta.get_field(field_name)

        # Handles the model field default value. See ForeignKey.formfield implementation.
        if field.has_default() and initial is None:
            # get_default is a PROPERTY -_-'
            initial = field._get_default
            kwargs.setdefault('show_hidden_initial', callable(initial))

        enum = self.enumerable(
            field=field,
            user=user,
            limit=limit,
        )

        super().__init__(enum, initial=initial, **kwargs)
