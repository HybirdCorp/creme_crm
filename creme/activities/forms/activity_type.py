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

from functools import partial

from django.core.exceptions import ValidationError
from django.forms.fields import CallableChoiceIterator, CharField
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from creme.creme_core.forms import CremeModelForm
from creme.creme_core.forms.bulk import BulkDefaultEditForm
from creme.creme_core.forms.fields import DurationField, JSONField
from creme.creme_core.forms.widgets import ChainedInput, Label
from creme.creme_core.utils.id_generator import generate_string_id_and_save
from creme.creme_core.utils.url import TemplateURLBuilder

from ..constants import ACTIVITYTYPE_INDISPO
from ..models import ActivitySubType, ActivityType


class ActivityTypeForm(CremeModelForm):
    default_hour_duration = DurationField(label=_('Duration'))

    class Meta(CremeModelForm.Meta):
        model = ActivityType

    def save(self):  # TODO: *args, **kwargs
        instance = self.instance

        if not instance.id:
            super().save(commit=False)
            generate_string_id_and_save(ActivityType, [instance],
                                        'creme_config-useractivitytype',
                                       )
        else:
            super().save()

        return instance


class ActivitySubTypeForm(CremeModelForm):
    class Meta(CremeModelForm.Meta):
        model = ActivitySubType

    def save(self, *args, **kwargs):
        instance = self.instance

        if not instance.id:
            super().save(commit=False, *args, **kwargs)
            generate_string_id_and_save(ActivitySubType, [instance],
                                        'creme_config-useractivitydetailesubtype',
                                       )
        else:
            super().save(*args, **kwargs)

        return instance


class ActivityTypeWidget(ChainedInput):
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


class ActivityTypeField(JSONField):
    widget = ActivityTypeWidget  # Should have a 'types' attribute
    default_error_messages = {
        'typenotallowed':  _('This type causes constraint error.'),
        'subtyperequired': _('Sub-type is required.'),
    }
    value_type = dict

    def __init__(self, *, types=ActivityType.objects.all(), empty_label='---------', **kwargs):
        self.empty_label = empty_label

        # super().__init__(*args, **kwargs)
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
            raise ValidationError(self.error_messages['typenotallowed'], code='typenotallowed') from e

        related_types = ActivitySubType.objects.filter(type=atype)
        subtype = None

        if subtype_pk:
            try:
                subtype = related_types.get(pk=subtype_pk)
            except ActivitySubType.DoesNotExist as e:
                raise ValidationError(self.error_messages['subtyperequired'],
                                      code='subtyperequired',
                                     ) from e
        elif self.required and related_types.exists():
            raise ValidationError(self.error_messages['subtyperequired'],
                                  code='subtyperequired',
                                 )

        return (atype, subtype)

    @property
    def types(self):
        return self._types.all()

    @types.setter
    def types(self, types):
        self._types = types
        self.widget.types = CallableChoiceIterator(self._get_types_options)

    def _get_types_options(self):
        types = self._types  # TODO: self.types ??

        if len(types) > 1 or not self.required:
            yield None, self.empty_label

        for instance in types:
            yield instance.id, str(instance)


class BulkEditTypeForm(BulkDefaultEditForm):
    error_messages = {
        'immutable_indispo': _('The type of an indisponibility cannot be changed.'),
    }

    def __init__(self, model, field, user, entities, is_bulk=False, **kwargs):
        super().__init__(model, field, user, entities, is_bulk=is_bulk, **kwargs)
        self.fields['field_value'] = type_selector = ActivityTypeField(
            label=_('Type'),
            types=ActivityType.objects.exclude(pk=ACTIVITYTYPE_INDISPO),
        )
        self._mixed_indispo = False
        indispo_count = sum(a.type_id == ACTIVITYTYPE_INDISPO for a in entities)

        if indispo_count:
            if indispo_count == len(entities):
                # All entities are indisponibilities, so we propose to change the sub-type.
                type_selector.types = ActivityType.objects.filter(pk=ACTIVITYTYPE_INDISPO)
            else:
                self._mixed_indispo = True
                # TODO: remove when old view entity.bulk_edit_field() has been removed
                self.fields['beware'] = CharField(
                    label=_('Beware !'),
                    required=False, widget=Label,
                    initial=ngettext(
                        'The type of {count} activity cannot be changed because it is an indisponibility.',
                        'The type of {count} activities cannot be changed because they are indisponibilities.',
                        indispo_count
                    ).format(count=indispo_count),
                )

        if not is_bulk:
            first = entities[0]
            type_selector.initial = (first.type_id, first.sub_type_id)

    def _bulk_clean_entity(self, entity, values):
        if self._mixed_indispo and entity.type_id == ACTIVITYTYPE_INDISPO:
            raise ValidationError(self.error_messages['immutable_indispo'],
                                  code='immutable_indispo',
                                 )

        entity.type, entity.sub_type = values.get(self.field_name)

        return entity
