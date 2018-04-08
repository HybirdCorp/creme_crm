# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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
from django.db.models.fields import FieldDoesNotExist
from django.db.models.fields.related import ManyToManyField
from django.forms.fields import ChoiceField
from django.forms.forms import NON_FIELD_ERRORS
from django.forms.widgets import Select
from django.urls import reverse  # NoReverseMatch
from django.utils.translation import ugettext_lazy as _, ugettext

from ..gui.bulk_update import bulk_update_registry
from ..models import custom_field

from .base import CremeForm


_CUSTOMFIELD_PATTERN = re.compile('^customfield-(?P<id>[0-9]+)')
_CUSTOMFIELD_FORMAT = 'customfield-%d'


class BulkFieldSelectWidget(Select):
    # def build_attrs(self, extra_attrs=None, **kwargs):
    #     attrs = super(BulkFieldSelectWidget, self).build_attrs(extra_attrs, **kwargs)
    def build_attrs(self, base_attrs, extra_attrs=None):
        attrs = super(BulkFieldSelectWidget, self).build_attrs(base_attrs=base_attrs, extra_attrs=extra_attrs)
        attrs['onchange'] = 'creme.dialog.redirect($(this).val(), $(this));'
        return attrs


class BulkForm(CremeForm):
    def __init__(self, model, field, user, entities, is_bulk, parent_field=None, **kwargs):
        super(BulkForm, self).__init__(user, **kwargs)
        self.is_bulk = is_bulk
        self.is_subfield = parent_field is not None
        self.is_custom = is_custom = isinstance(field, custom_field.CustomField)

        self.field_name = field.name if not is_custom else _CUSTOMFIELD_FORMAT % field.pk
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
            fieldname = self.parent_field.name + '__' + self.field_name if self.is_subfield else self.field_name

            self.fields['_bulk_fieldname'] = ChoiceField(
                choices=self._bulk_model_choices(model, entities),
                label=_(u'Field to update'),
                initial=self._bulk_field_url(model, fieldname, entities),
                widget=BulkFieldSelectWidget,
                required=False,
            )

    def _bulk_field_url(self, model, fieldname, entities):
        kwargs = {'ct_id': ContentType.objects.get_for_model(model).id,
                  'field_name': fieldname,
                 }

        # try:
        #     return reverse(self._bulk_viewname, kwargs=kwargs)
        # except NoReverseMatch:
        #     # NB: ugly hack to support the old view bulk_edit_field().
        #     kwargs['id'] = ','.join(str(e.pk) for e in entities)
        #     return reverse(self._bulk_viewname, kwargs=kwargs)
        return reverse(self._bulk_viewname, kwargs=kwargs)

    def _bulk_formfield(self, user, instance=None):
        if self.is_custom:
            return self._bulk_custom_formfield(self.model_field, instance)

        return self._bulk_updatable_formfield(self.model_field, user, instance)

    def _bulk_model_choices(self, model, entities):
        regular_fields = bulk_update_registry.regular_fields(model, expand=True)
        custom_fields = bulk_update_registry.custom_fields(model)

        build_url = partial(self._bulk_field_url, model=model, entities=entities)

        choices = []
        sub_choices = []

        for field, subfields in regular_fields:
            if not subfields:
                choices.append((build_url(fieldname=field.name), unicode(field.verbose_name)))
            else:
                sub_choices.append((unicode(field.verbose_name),
                                    [(build_url(fieldname=field.name + '__' + subfield.name), unicode(subfield.verbose_name))
                                        for subfield in subfields
                                    ],
                                   )
                                  )

        if custom_fields:
            choices.append((ugettext(u'Custom fields'),
                            [(build_url(fieldname=_CUSTOMFIELD_FORMAT % field.id), field.name)
                                for field in custom_fields
                            ]
                           )
                          )

        return choices + sub_choices

    def _bulk_custom_formfield(self, model_field, instance=None):
        if instance is not None:
            return model_field.get_formfield(instance.get_custom_value(model_field))

        return model_field.get_formfield(None)

    def _bulk_updatable_formfield(self, model_field, user, instance=None):
        form_field = model_field.formfield()

        if hasattr(form_field, 'get_limit_choices_to'):
            q_filter = form_field.get_limit_choices_to()

            if q_filter is not None:
                form_field.queryset = form_field.queryset.complex_filter(q_filter)

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
            # setattr(entity, key, value)
            try:
                mfield = entity._meta.get_field(key)
            except FieldDoesNotExist:
                pass
            else:
                if not getattr(mfield, 'many_to_many', False):
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

    def _bulk_clean(self, values):
        # In bulk mode get all entities, only the first one elsewhere
        entities = self.entities if self.is_bulk else self.entities[:1]

        # Skip model clean step for custom-fields
        if self.is_custom:
            self.bulk_cleaned_entities = entities
            self.bulk_invalid_entities = []
            return

        # Update attribute <field_name> of each instance of entity and filter valid ones.
        self.bulk_cleaned_entities, self.bulk_invalid_entities = self._bulk_clean_entities(entities, values)

        if not self.is_bulk and self.bulk_invalid_entities:
            entity, error = self.bulk_invalid_entities[0]
            raise ValidationError(self._bulk_error_messages(entity, error))


class BulkDefaultEditForm(BulkForm):
    def __init__(self, model, field, user, entities, is_bulk=False, **kwargs):
        super(BulkDefaultEditForm, self).__init__(model, field, user, entities, is_bulk, **kwargs)

        instance = entities[0] if not is_bulk else None
        form_field = self._bulk_formfield(user, instance)

        self.fields['field_value'] = form_field

    def clean(self):
        cleaned_data = super(BulkDefaultEditForm, self).clean()

        if self.errors:
            return cleaned_data

        self._bulk_clean({self.field_name: cleaned_data.get('field_value')})

        return cleaned_data

    def save(self):
        entities = self.bulk_cleaned_entities
        field_value = self.cleaned_data['field_value']

        # if self.is_custom and entities:
        #     custom_field.CustomFieldValue.save_values_for_entities(self.model_field, entities, field_value)
        # else:
        #     for entity in entities:
        #         entity.save()
        if entities:
            if self.is_custom:
                custom_field.CustomFieldValue.save_values_for_entities(self.model_field, entities, field_value)
            elif getattr(self.model_field, 'many_to_many', False):
                name = self.model_field.name

                for entity in entities:
                    getattr(entity, name).set(field_value)
            else:
                for entity in entities:
                    entity.save()
