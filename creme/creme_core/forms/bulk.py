# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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
import re

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.fields.related import ForeignKey, RelatedField, ManyToManyField
from django.db.models.query_utils import Q
from django.forms.fields import ChoiceField
from django.forms.forms import NON_FIELD_ERRORS
from django.forms.models import ModelMultipleChoiceField
from django.forms.widgets import Select
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_config.forms.fields import CreatorModelChoiceField

from ..gui.bulk_update import bulk_update_registry
from ..models import fields, CremeEntity
from ..models.custom_field import CustomField, CustomFieldValue

from .base import CremeForm
from .fields import CreatorEntityField, MultiCreatorEntityField
from .widgets import DateTimeWidget, CalendarWidget, UnorderedMultipleChoiceWidget


# TODO : should remove this list and use some hooks in model fields or in bulk registry to retrieve bulk widgets
_BULK_FIELD_WIDGETS = {
#     models.DateField:                 CalendarWidget(),
#     models.DateTimeField:             DateTimeWidget(),
#     fields.CreationDateTimeField:     DateTimeWidget(),
#     fields.ModificationDateTimeField: DateTimeWidget(),
}

_CUSTOMFIELD_PATTERN = re.compile('^customfield-(?P<id>[0-9]+)')
_CUSTOMFIELD_FORMAT = 'customfield-%d'


class BulkFieldSelectWidget(Select):
    def build_attrs(self, extra_attrs=None, **kwargs):
        attrs = super(BulkFieldSelectWidget, self).build_attrs(extra_attrs, **kwargs)
        attrs['onchange'] = 'creme.dialog.redirect($(this).val(), $(this));'
        return attrs


class BulkForm(CremeForm):
    def __init__(self, model, field, user, entities, is_bulk, parent_field=None, **kwargs):
        super(BulkForm, self).__init__(user, **kwargs)
        self.is_bulk = is_bulk
        self.is_subfield = is_subfield = parent_field is not None
        self.is_custom = is_custom = isinstance(field, CustomField)

        self.field_name = field.name if not is_custom else _CUSTOMFIELD_FORMAT % field.pk
        self.model = model
        self.model_field = field
        self.model_parent_field = parent_field
        self.entities = entities

        if is_bulk:
            choices = self._bulk_model_choices(model, entities)
            initial = self._bulk_url(model,
                                     parent_field.name + '__' + self.field_name if is_subfield else self.field_name,
                                     entities,
                                    )

            self.fields['_bulk_fieldname'] = ChoiceField(choices=choices,
                                                         label=_(u"Field to update"),
                                                         initial=initial,
                                                         widget=BulkFieldSelectWidget,
                                                         required=False,
                                                        )

    def _bulk_url(self, model, fieldname, entities):
        return '/creme_core/entity/update/bulk/%s/field/%s' % (
                    ContentType.objects.get_for_model(model).pk,
                    fieldname,
                )

    def _bulk_formfield(self, user, instance=None):
        if self.is_custom:
            return self._bulk_custom_formfield(self.model_field, instance)

        return self._bulk_updatable_formfield(self.model_field, user, instance)

    def _bulk_model_choices(self, model, entities):
        regular_fields = bulk_update_registry.regular_fields(model, expand=True)
        custom_fields = bulk_update_registry.custom_fields(model)

        url = self._bulk_url(model, '%s', entities)

        choices = []
        sub_choices = []

        for field, subfields in regular_fields:
            if not subfields:
                choices.append((url % unicode(field.name), unicode(field.verbose_name)))
            else:
                sub_choices.append((unicode(field.verbose_name),
                                    [(url % unicode(field.name + '__' + subfield.name), unicode(subfield.verbose_name))
                                        for subfield in subfields
                                    ],
                                   )
                                  )

        if custom_fields:
            choices.append((ugettext(u"Custom fields"),
                            [(url % (_CUSTOMFIELD_FORMAT % field.id), field.name)
                                for field in custom_fields
                            ]
                           )
                          )

        return choices + sub_choices

    def _bulk_custom_formfield(self, model_field, instance=None):
        if instance is not None:
            return model_field.get_formfield(instance.get_custom_value(model_field))

        return model_field.get_formfield(None)

    def _bulk_related_formfield(self, model_field, user, instance=None):
        form_field = model_field.formfield()
        related_to = model_field.rel.to
        q_filter = None

        if hasattr(model_field, 'limit_choices_to'):
            related_filter = model_field.limit_choices_to
            q_filter = related_filter() if callable(related_filter) else related_filter

        if issubclass(related_to, CremeEntity):
            if isinstance(q_filter, Q):
                raise ValueError('Q filter is not (yet) supported for bulk edition of a field related to a CremeEntity.')

            if isinstance(model_field, ForeignKey):
                form_field = CreatorEntityField(model=related_to, label=form_field.label,
                                                required=form_field.required,
                                                q_filter=q_filter,
                                               )
            elif isinstance(model_field, ManyToManyField):
                form_field = MultiCreatorEntityField(model=related_to,
                                                     label=form_field.label,
                                                     required=form_field.required,
                                                     q_filter=q_filter,
                                                    )
        else:
            if isinstance(q_filter, Q):
                choices = related_to.objects.filter(q_filter)
            elif q_filter:
                choices = related_to.objects.filter(**q_filter)
            else:
                choices = related_to.objects.all()

            if isinstance(model_field, ForeignKey):
                form_field = CreatorModelChoiceField(queryset=choices,
                                                     label=form_field.label,
                                                     required=form_field.required,
                                                    )
            elif isinstance(model_field, ManyToManyField):
                form_field = ModelMultipleChoiceField(label=form_field.label,
                                                      queryset=choices,
                                                      required=form_field.required,
                                                      widget=UnorderedMultipleChoiceWidget,
                                                     )

        return form_field

    def _bulk_updatable_formfield(self, model_field, user, instance=None):
        if isinstance(model_field, RelatedField):
            form_field = self._bulk_related_formfield(model_field, user, instance)
        else:
            form_field = model_field.formfield()
            # TODO : should remove this list and use some hooks in model fields in bulk registry to retrieve widgets
            form_field.widget = _BULK_FIELD_WIDGETS.get(model_field.__class__) or form_field.widget

        form_field.user = user

        if instance and self.is_subfield:
            instance = getattr(instance, self.model_parent_field.name)

        if instance:
            initial = getattr(instance, model_field.name)

            # HACK : special use case for manytomany fields to circumvent a strange django behaviour.
            if initial is not None and isinstance(model_field, ManyToManyField):
                initial = initial.get_queryset()

            form_field.initial = initial

        return form_field

    def _bulk_clean_entity(self, entity, values):
        for key, value in values.iteritems():
            setattr(entity, key, value)

        entity.full_clean()
        return entity

    def _bulk_clean_subfield(self, entity, values):
        instance = getattr(entity, self.model_parent_field.name)

        if instance is None:
            # TODO: code + _bulk_error_messages + params
            raise ValidationError(ugettext(u'The field %s is empty') % self.model_parent_field.verbose_name)

        return self._bulk_clean_entity(instance, values)

    def _bulk_clean_entities(self, entities, values):
        invalid_entities = []
        cleaned_entities = []
        clean = self._bulk_clean_subfield if self.is_subfield else self._bulk_clean_entity
        clean = partial(clean, values=values)

        for entity in entities:
            try:
                cleaned_entities.append(clean(entity))
            except ValidationError as e:
                invalid_entities.append((entity, e))

        return cleaned_entities, invalid_entities

    def _bulk_error_messages(self, entity, error):
        if not hasattr(error, 'message_dict'):
            return {NON_FIELD_ERRORS: error.messages}

        fields = {field.name: field
                    for field in (entity._meta.fields + entity._meta.many_to_many)
                 }
        messages = []

        for key, value in error.message_dict.iteritems():
            field = fields.get(key)
            message = ''.join(value) if isinstance(value, (list, tuple)) else value
            messages.append(u'%s : %s' % (ugettext(field.verbose_name), message)
                            if field is not None else
                            message
                           )

        return {NON_FIELD_ERRORS: messages}


class BulkDefaultEditForm(BulkForm):
    def __init__(self, model, field, user, entities, is_bulk=False, **kwargs):
        super(BulkDefaultEditForm, self).__init__(model, field, user, entities, is_bulk, **kwargs)

        instance = entities[0] if not is_bulk else None
        form_field = self._bulk_formfield(user, instance)

        self.fields['field_value'] = form_field

    def clean_field_value(self):
        field_value = self.cleaned_data.get('field_value')

        # TODO : CreatorEntityField doesn't check permission.
        if isinstance(field_value, CremeEntity) and not self.user.has_perm_to_view(field_value):
            raise ValidationError(ugettext(u"You can't view this value, so you can't set it."))

        return field_value

    def clean(self):
        if self.errors:
            return self.cleaned_data

        cleaned_data = super(BulkDefaultEditForm, self).clean()

        # In bulk mode get all entities, only the first one elsewhere
        entities = self.entities if self.is_bulk else self.entities[:1]

        # Skip model clean step for customfields
        if self.is_custom:
            self.bulk_cleaned_entities = entities
            self.bulk_invalid_entities = []
            return cleaned_data

        values = {self.field_name: cleaned_data.get('field_value')}

        # Update attribute <field_name> of each instance of entity and filter valid ones.
        self.bulk_cleaned_entities, self.bulk_invalid_entities = self._bulk_clean_entities(entities, values)

        if not self.is_bulk and self.bulk_invalid_entities:
            entity, error = self.bulk_invalid_entities[0]
            raise ValidationError(self._bulk_error_messages(entity, error))

        return cleaned_data

    def save(self):
        entities = self.bulk_cleaned_entities
        field_value = self.cleaned_data['field_value']

        if self.is_custom and entities:
            CustomFieldValue.save_values_for_entities(self.model_field, entities, field_value)
        else:
            for entity in entities:
                entity.save()
