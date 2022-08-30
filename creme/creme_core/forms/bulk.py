# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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
# import re
from functools import partial
from itertools import chain

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db.models import FileField, ManyToManyField
from django.forms.fields import ChoiceField
from django.forms.forms import NON_FIELD_ERRORS
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from ..gui import bulk_update
from ..models import CremeEntity, FieldsConfig, custom_field
from .base import CremeForm

logger = logging.getLogger(__name__)
# _CUSTOMFIELD_PATTERN = re.compile('^customfield-(?P<id>[0-9]+)')
_CUSTOMFIELD_FORMAT = 'customfield-{}'  # TODO: remove & use base._CUSTOM_NAME instead


class BulkForm(CremeForm):
    excluded_bulk_fields = (
        # TODO: fix that ?
        # NB1: bulk update of file field is broken on JS side any way(IDs are not posted ?)
        # NB2: it's probably a bad idea to set the same file to several entities
        #      (when one entity is deleted the file is attached to a FileRef then by a Job).
        FileField,
    )

    def __init__(self, model, field, user, entities, is_bulk,
                 parent_field=None, bulk_update_registry=None, **kwargs):
        super().__init__(user, **kwargs)
        self.bulk_update_registry = bulk_update_registry or bulk_update.bulk_update_registry

        self.is_bulk = is_bulk
        self.is_subfield = parent_field is not None
        self.is_custom = is_custom = isinstance(field, custom_field.CustomField)

        self.field_name = field.name if not is_custom else _CUSTOMFIELD_FORMAT.format(field.pk)
        self.model = model
        self.model_field = field
        self.model_parent_field = parent_field
        self.entities = entities
        self.bulk_viewname = 'creme_core__bulk_update'

    @property
    def bulk_viewname(self):
        return self._bulk_viewname

    @bulk_viewname.setter
    def bulk_viewname(self, viewname):
        self._bulk_viewname = viewname

        if self.is_bulk:
            model = self.model
            entities = self.entities
            # TODO: factorise
            field_name = (
                f'{self.model_parent_field.name}__{self.field_name}'
                if self.is_subfield else
                self.field_name
            )

            self.fields['_bulk_fieldname'] = ChoiceField(
                choices=self._bulk_model_choices(model, entities),
                label=_('Field to update'),
                initial=self._bulk_field_url(model, field_name, entities),
                required=False,
            )

    def _bulk_field_url(self, model, fieldname, entities):  # TODO: remove 'entities'
        return reverse(
            self._bulk_viewname,
            kwargs={
                'ct_id': ContentType.objects.get_for_model(model).id,
                'field_name': fieldname,
            },
        )

    def _bulk_formfield(self, user, instance=None):
        if self.is_custom:
            return self._bulk_custom_formfield(self.model_field, user=user, instance=instance)

        return self._bulk_updatable_formfield(self.model_field, user=user, instance=instance)

    def _bulk_model_choices(self, model, entities):
        registry = self.bulk_update_registry
        regular_fields = registry.regular_fields(model, expand=True)
        custom_fields = registry.custom_fields(model)

        build_url = partial(self._bulk_field_url, model=model, entities=entities)

        choices = []
        sub_choices = []
        excluded = self.excluded_bulk_fields

        for field, subfields in regular_fields:
            if not subfields:
                if not isinstance(field, excluded):
                    choices.append((build_url(fieldname=field.name), str(field.verbose_name)))
            else:
                field_sub_choices = [
                    (
                        build_url(fieldname=f'{field.name}__{subfield.name}'),
                        str(subfield.verbose_name),
                    )
                    for subfield in subfields
                    if not isinstance(subfield, excluded)
                ]
                if field_sub_choices:
                    sub_choices.append((str(field.verbose_name), field_sub_choices))

        if custom_fields:
            choices.append((
                gettext('Custom fields'),
                [
                    (build_url(fieldname=_CUSTOMFIELD_FORMAT.format(field.id)), field.name)
                    for field in custom_fields
                ]
            ))

        return choices + sub_choices

    # TODO: rename "model_field"
    def _bulk_custom_formfield(self, model_field, instance=None, user=None):
        if instance is not None:
            return model_field.get_formfield(
                instance.get_custom_value(model_field),
                user=user,
            )

        return model_field.get_formfield(None, user=user)

    def _bulk_updatable_formfield(self, model_field, user, instance=None):
        form_field = model_field.formfield()

        if form_field is None:
            # Should never happen
            logger.critical(
                'creme_core.forms.bulk.BulkForm._bulk_updatable_formfield(): '
                'the model-field <%s> cannot be edited, & should have been '
                'rejected by te view ; a bug report would be a nice thing to do.',
                model_field,
            )
            raise ValueError('This field cannot be edited.')

        if FieldsConfig.objects.get_for_model(model_field.model).is_field_required(model_field):
            form_field.required = True

        if hasattr(form_field, 'get_limit_choices_to'):
            q_filter = form_field.get_limit_choices_to()

            if q_filter is not None:
                form_field.queryset = form_field.queryset.complex_filter(q_filter)

        form_field.user = user

        if instance and self.is_subfield:
            instance = getattr(instance, self.model_parent_field.name)

        if instance:
            initial = getattr(instance, model_field.name)

            # HACK: special use case for manytomany fields to circumvent a
            #       strange django behaviour.
            if initial is not None and isinstance(model_field, ManyToManyField):
                initial = initial.get_queryset()

            form_field.initial = initial

        return form_field

    def _bulk_clean_entity(self, entity, values):
        file_field_info = []

        for key, value in values.items():
            try:
                mfield = entity._meta.get_field(key)
            except FieldDoesNotExist:
                pass
            else:
                # Copied from django/forms/models.py l.55 ( construct_instance() )
                #  "Defer saving file-type fields until after the other fields, so a
                #  callable upload_to can use the values from other fields."
                if isinstance(mfield, FileField):
                    file_field_info.append((mfield, value))
                else:
                    mfield.save_form_data(entity, value)

        for mfield, value in file_field_info:
            # TODO: what about cleaning useless files VS files history
            mfield.save_form_data(entity, value)

        entity.full_clean()

        return entity

    def _bulk_clean_subfield(self, entity, values):
        instance = getattr(entity, self.model_parent_field.name)

        if instance is None:
            # TODO: code + _bulk_error_messages + params
            raise ValidationError(
                gettext('The field «{}» is empty').format(
                    self.model_parent_field.verbose_name
                )
            )

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

        meta = entity._meta
        fields = {
            field.name: field
            # for field in (entity._meta.fields + entity._meta.many_to_many)
            for field in chain(meta.fields, meta.many_to_many)
        }
        messages = []

        for key, value in error.message_dict.items():
            field = fields.get(key)
            message = ''.join(value) if isinstance(value, (list, tuple)) else value
            messages.append(
                f'{field.verbose_name} : {message}'
                if field is not None else
                message
            )

        return {NON_FIELD_ERRORS: messages}

    def _bulk_clean(self, values):
        # In bulk mode get all entities, only the first one elsewhere
        entities = self.entities if self.is_bulk else self.entities[:1]

        # Skip model clean step for custom-fields
        if self.is_custom:
            self.bulk_cleaned_entities = entities
            self.bulk_invalid_entities = []
            return

        # Update attribute <field_name> of each instance of entity and filter valid ones.
        self.bulk_cleaned_entities, self.bulk_invalid_entities = \
            self._bulk_clean_entities(entities, values)

        if not self.is_bulk and self.bulk_invalid_entities:
            entity, error = self.bulk_invalid_entities[0]
            raise ValidationError(self._bulk_error_messages(entity, error))


class BulkDefaultEditForm(BulkForm):
    def __init__(self, model, field, user, entities, is_bulk=False, **kwargs):
        super().__init__(model, field, user, entities, is_bulk, **kwargs)

        instance = entities[0] if not is_bulk else None
        form_field = self._bulk_formfield(user, instance)

        self.fields['field_value'] = form_field

    def clean(self):
        cleaned_data = super().clean()

        if self.errors:
            return cleaned_data

        self._bulk_clean({self.field_name: cleaned_data.get('field_value')})

        return cleaned_data

    def save(self):
        entities = self.bulk_cleaned_entities
        field_value = self.cleaned_data['field_value']

        if entities:
            if self.is_custom:
                custom_field.CustomFieldValue.save_values_for_entities(
                    self.model_field, entities, field_value,
                )
                # We ensure the field "modified" is updated (CremeEntity.save() is not called).
                # TODO: smarter way? (to ensure "modified" is always updated
                #       when a custom value is saved (beware to extra queries...)
                # TODO: do not update if the values does not change?
                #       (notice that this is not done even for regular fields...)
                CremeEntity.objects.filter(
                    id__in=[e.id for e in entities],
                ).update(modified=now())
            elif getattr(self.model_field, 'many_to_many', False):
                name = self.model_field.name

                for entity in entities:
                    getattr(entity, name).set(field_value)
            else:
                for entity in entities:
                    entity.save()
