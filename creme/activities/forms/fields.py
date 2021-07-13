# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2021  Hybird
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

from functools import partial

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import widgets
from django.forms.fields import CallableChoiceIterator
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import fields as core_fields
from creme.creme_core.forms import validators
from creme.creme_core.forms import widgets as core_widgets
from creme.creme_core.utils.url import TemplateURLBuilder
from creme.persons import get_contact_model

from ..models import ActivitySubType, ActivityType, Calendar


class ActivityTypeWidget(core_widgets.ChainedInput):
    def __init__(self, types=(), attrs=None, creation_allowed=True):
        super().__init__(attrs)
        self.creation_allowed = creation_allowed  # TODO: useless at the moment ...
        self.types = types

    def get_context(self, name, value, attrs):
        add_dselect = partial(self.add_dselect, attrs={'auto': False})
        add_dselect('type', options=self.types)
        add_dselect(
            'sub_type',
            options=TemplateURLBuilder(
                type_id=(TemplateURLBuilder.Word, '${type}'),
            ).resolve('activities__get_types'),
        )

        return super().get_context(name=name, value=value, attrs=attrs)


class ActivityTypeField(core_fields.JSONField):
    widget = ActivityTypeWidget  # Should have a 'types' attribute
    default_error_messages = {
        'typenotallowed':  _('This type causes constraint error.'),
        'subtyperequired': _('Sub-type is required.'),
    }
    value_type = dict

    def __init__(self, *,
                 types=ActivityType.objects.all(),
                 empty_label='---------',
                 **kwargs):
        self.empty_label = empty_label

        super().__init__(**kwargs)
        self.types = types

    def __deepcopy__(self, memo):
        result = super().__deepcopy__(memo)

        # Need to force a fresh iterator to be created.
        result.types = result.types

        return result

    def widget_attrs(self, widget):  # See Field.widget_attrs()
        return {'reset': not self.required}

    def _value_to_jsonifiable(self, value):
        if isinstance(value, ActivitySubType):
            type_id = value.type_id
            subtype_id = value.id
        else:
            type_id, subtype_id = value

        return {'type': type_id, 'sub_type': subtype_id}

    def _value_from_unjsonfied(self, data):
        clean = self.clean_value
        type_pk  = clean(data, 'type', str)
        subtype_pk = clean(data, 'sub_type', str, required=False)

        if not type_pk and self.required:
            raise ValidationError(self.error_messages['required'], code='required')

        try:
            atype = self.types.get(pk=type_pk)
        except ActivityType.DoesNotExist as e:
            raise ValidationError(
                self.error_messages['typenotallowed'],
                code='typenotallowed',
            ) from e

        related_types = ActivitySubType.objects.filter(type=atype)
        subtype = None

        if subtype_pk:
            try:
                subtype = related_types.get(pk=subtype_pk)
            except ActivitySubType.DoesNotExist as e:
                raise ValidationError(
                    self.error_messages['subtyperequired'],
                    code='subtyperequired',
                ) from e
        elif self.required and related_types.exists():
            raise ValidationError(
                self.error_messages['subtyperequired'],
                code='subtyperequired',
            )

        return atype, subtype

    @property
    def types(self):
        return self._types.all()

    @types.setter
    def types(self, types):
        self._types = types
        self.widget.types = CallableChoiceIterator(self._get_types_options)

    def _get_types_options(self):
        types = self._types

        if len(types) > 1 or not self.required:
            yield None, self.empty_label

        for instance in types:
            yield instance.id, str(instance)


class DateWithOptionalTimeWidget(widgets.MultiWidget):
    template_name = 'activities/forms/widgets/datetime.html'

    def __init__(self, attrs=None):
        super().__init__(
            widgets=(core_widgets.CalendarWidget, core_widgets.TimeWidget),
            attrs=attrs,
        )

    def decompress(self, value):
        return (value[0], value[1]) if value else (None, None)


class DateWithOptionalTimeField(forms.MultiValueField):
    widget = DateWithOptionalTimeWidget

    def __init__(self, *, required=True, **kwargs):
        super().__init__(
            fields=(
                forms.DateField(required=required),
                forms.TimeField(required=False),
            ),
            require_all_fields=False,
            required=required,
            **kwargs
        )

    def compress(self, data_list):
        return (data_list[0], data_list[1]) if data_list else (None, None)


class UserParticipationField(core_fields.OptionalModelChoiceField):
    def __init__(self, *, user=None, sub_label=_('Appears on the calendar:'), **kwargs):
        super().__init__(
            sub_label=sub_label,
            queryset=Calendar.objects.none(),
            **kwargs
        )
        self.user = user

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user

        if user is not None:
            calendars_field = self.fields[1]
            calendars_field.queryset = Calendar.objects.filter(user=user)

            self.widget.sub_widget.choices = calendars_field.choices

    def clean(self, value):
        user = self._user
        assert user is not None

        value = super().clean(value=value)
        validators.validate_linkable_entity(user.linked_contact, user)

        return value


class ParticipatingUsersField(forms.ModelMultipleChoiceField):
    def __init__(self, *,
                 user=None,
                 queryset=get_user_model().objects.filter(is_staff=False),
                 **kwargs):
        super().__init__(queryset=queryset, **kwargs)
        self.user = user

    def clean(self, value):
        user = self.user
        assert user is not None

        users = set()

        for part_user in super().clean(value=value):
            if not part_user.is_team:
                users.add(part_user)
            else:
                users.update(part_user.teammates.values())

        return validators.validate_linkable_entities(
            get_contact_model().objects.filter(is_user__in=users).select_related('is_user'),
            self.user,
        )
