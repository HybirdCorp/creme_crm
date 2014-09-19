# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

import re

from functools import partial
from itertools import chain

from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.db.models.fields.related import ForeignKey, RelatedField
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.forms.fields import CharField, ChoiceField
from django.forms.models import model_to_dict
from django.forms.widgets import MultiWidget
from django.utils.translation import ugettext, ugettext_lazy as _

from ..models import fields, EntityCredentials, CremeEntity
from ..models.custom_field import CustomField, CustomFieldEnumValue, CustomFieldValue, CustomFieldMultiEnum, CustomFieldEnum
from ..gui.bulk_update import bulk_update_registry
from ..utils import entities2unicode, related2unicode
from ..utils.meta import FieldInfo #get_verbose_field_name
from ..forms.base import CremeModelForm
from .base import CremeForm
from .fields import DatePeriodField, CreatorEntityField
from .widgets import DateTimeWidget, CalendarWidget, UnorderedMultipleChoiceWidget, Label, AdaptiveWidget, DatePeriodWidget


_FIELDS_WIDGETS = {
        models.ManyToManyField:           UnorderedMultipleChoiceWidget(),
        models.DateField:                 CalendarWidget(),
        models.DateTimeField:             DateTimeWidget(),
        fields.CreationDateTimeField:     DateTimeWidget(),
        fields.ModificationDateTimeField: DateTimeWidget(),
        CustomFieldMultiEnum:             UnorderedMultipleChoiceWidget(),
        DatePeriodField:                  DatePeriodWidget(),
    }

_CUSTOMFIELD_PATTERN = re.compile('^customfield-(?P<id>[0-9]+)')
_CUSTOMFIELD_FORMAT = 'customfield-%d'

#TODO : staticmethod ??
#TODO: remove this when whe have a EntityForeignKey with the right model field that does the job.
def _get_choices(model_field, user):
    form_field = model_field.formfield()
    choices = ()
    if isinstance(model_field, (models.ForeignKey, models.ManyToManyField)) and issubclass(model_field.rel.to, CremeEntity):
        fk_entities = model_field.rel.to._default_manager \
                                        .filter(pk__in=[id_ for id_, text in form_field.choices if id_])
        choices = ((e.id, e) for e in EntityCredentials.filter(user, fk_entities))

        if model_field.null and isinstance(model_field, models.ForeignKey):
            choices = chain([(u"", ugettext(u"None"))], choices)
    elif hasattr(form_field, 'choices'):
        choices = form_field.choices
    return choices


class _EntitiesEditForm(CremeForm):
    entities_lbl = CharField(label=_(u"Entities to update"), required=False, widget=Label)
    field_name   = ChoiceField(label=_(u"Field to update"))
    field_value  = CharField(label=_(u"Value"), required=False)

    def get_cfields_cache(self):
        return {cf.pk: cf for cf in CustomField.objects.filter(content_type=self.ct)}

    def __init__(self, model, subjects, forbidden_subjects, user, *args, **kwargs):
        super(_EntitiesEditForm, self).__init__(user, *args, **kwargs)

        self.subjects = subjects
        self.user = user
        self.model = model
        self.ct = ContentType.objects.get_for_model(model)
        self._cfields_cache = None

        fields = self.fields

        if subjects:
            fields['entities_lbl'].initial = related2unicode(subjects[0], user) \
                                             if hasattr(subjects[0], 'get_related_entity') \
                                             else entities2unicode(subjects, user)
        else:
            fields['entities_lbl'].initial = ugettext(u'NONE !')

        if forbidden_subjects:
            fields['bad_entities_lbl'] = CharField(label=ugettext(u"Uneditable entities"),
                                                   widget=Label,
                                                   initial=entities2unicode(forbidden_subjects, user)
                                                  )

    @staticmethod
    def get_field(model, field_name, cfields_cache=None, instance=None):
        field = None
        matches = _CUSTOMFIELD_PATTERN.match(field_name)

        if matches is not None:
            customfield_id = int(matches.group('id'))
            field = cfields_cache.get(customfield_id) if cfields_cache else None

            if field is None:
                field = CustomField.objects.get(pk=customfield_id)

                if cfields_cache:
                    cfields_cache[customfield_id] = field

            return field, True

        try:
            return model._meta.get_field(field_name), False
        except FieldDoesNotExist:
            return None, False

    @staticmethod
    def get_custom_formfield(model_field, instance=None):
        if instance is not None:
            return model_field.get_formfield(instance.get_custom_value(model_field))

        return model_field.get_formfield(None)

    @staticmethod
    def get_updatable_formfield(model_field, user, instance=None):
        form_field = model_field.formfield()

        if isinstance(model_field, RelatedField):
            if isinstance(model_field, ForeignKey) and issubclass(model_field.rel.to, CremeEntity):
                form_field = CreatorEntityField(model_field.rel.to, label=form_field.label, required=form_field.required)
            else:
                form_field.choices = _get_choices(model_field, user)

        form_field.widget = _FIELDS_WIDGETS.get(model_field.__class__) or form_field.widget
        form_field.user = user

        if instance:
            form_field.initial = model_to_dict(instance, [model_field.name])[model_field.name]

        return form_field

    def clean(self, *args, **kwargs):
        super(_EntitiesEditForm, self).clean(*args, **kwargs)
        cleaned_data = self.cleaned_data

        if self._errors:
            return cleaned_data

        field_name  = cleaned_data['field_name']

        model_field, is_custom = self.get_field(self.model, field_name, self._cfields_cache)

        if model_field is None:
            raise ValidationError(_(u'Select a valid field.'))

        if is_custom:
            self._custom_field = model_field

            field_klass = model_field.get_value_class()
            field_value = cleaned_data['field_value']

            if field_value and not issubclass(field_klass, CustomFieldMultiEnum):
                field_value = field_value[0]

            form_field = model_field.get_formfield(None)
            #form_field.initial = field_value #TODO: useful ??
            cleaned_value = form_field.clean(form_field.widget.value_from_datadict(self.data, self.files, 'field_value'))

            if cleaned_value and issubclass(field_klass, CustomFieldEnum):
                if not CustomFieldEnumValue.objects.filter(pk=cleaned_value).exists():
                    raise ValidationError(_(u'Select a valid choice.'))
        else:
            self._custom_field = None

            form_field = self.get_updatable_formfield(model_field, self.user)

            if isinstance(form_field.widget, MultiWidget):
                field_value = form_field.widget.value_from_datadict(self.data, self.files, self.add_prefix('field_value'))
            else:
                field_value = cleaned_data['field_value']

            cleaned_value = cleaned_data['field_value'] = form_field.clean(field_value)

            if isinstance(cleaned_value, CremeEntity) and not self.user.has_perm_to_view(cleaned_value):
                raise ValidationError(ugettext(u"You can't view this value, so you can't set it."))

            if cleaned_value is None and not model_field.null:
                raise ValidationError(ugettext(u'This field is required.'))

            if not (cleaned_value is not None or model_field.blank):
                raise ValidationError(ugettext(u'This field is required.'))

            #Checking valid choices & credentials
            if cleaned_value and isinstance(model_field, RelatedField) and issubclass(model_field.rel.to, CremeEntity):
                allowed_choices = [choice[0] for choice in _get_choices(model_field, self.user)]

                if isinstance(cleaned_value, list):
                    for field_val in cleaned_value:
                        if field_val.pk not in allowed_choices:
                            raise ValidationError(_(u'Select a valid choice.'))
                elif cleaned_value.pk not in allowed_choices:
                    raise ValidationError(_(u'Select a valid choice.'))

            for subject in self.subjects:
                setattr(subject, field_name, cleaned_value)
                subject.full_clean()

        cleaned_data['field_value'] = cleaned_value

        return cleaned_data

    def save(self):
        custom_field = self._custom_field

        if custom_field is not None:
            CustomFieldValue.save_values_for_entities(custom_field, self.subjects,
                                                      self.cleaned_data['field_value']
                                                     )
        else:
            for subject in self.subjects:
                subject.save()


class EntitiesBulkUpdateForm(_EntitiesEditForm):
    def __init__(self, model, subjects, forbidden_subjects, user, *args, **kwargs):
        super(EntitiesBulkUpdateForm, self).__init__(model, subjects, forbidden_subjects, user, *args, **kwargs)

        self._cfields_cache = self.get_cfields_cache()

        sort = partial(sorted, key=lambda k: ugettext(k[1]))

        bulk_status = bulk_update_registry.status(model)
        innerform_names = set(bulk_status.innerforms.keys())
        regular_fields = (f for f in bulk_status.updatables() if f.name not in innerform_names)

        f_field_name = self.fields['field_name']
        f_field_name.widget = AdaptiveWidget(ct_id=self.ct.id)
        f_field_name.choices = (
            (ugettext(u"Regular fields"), sort((unicode(field.name), unicode(field.verbose_name)) for field in regular_fields)),
            (ugettext(u"Custom fields"),  sort((_CUSTOMFIELD_FORMAT % cf.id, cf.name) for cf in self._cfields_cache.itervalues())),
          )


class EntityInnerEditForm(CremeModelForm):
    def __init__(self, model, field_name, user, instance, **kwargs):
        """@param field_id Name of a regular field, or pk (as int or string) for CustomFields."""
        super(EntityInnerEditForm, self).__init__(user, instance=instance, **kwargs)
        model_field, is_custom = _EntitiesEditForm.get_field(model, field_name)

        self.field_name = field_name
        self.model_field = model_field
        self.is_custom = is_custom
        self.verbose_fieldname = FieldInfo(model, field_name).verbose_name if not is_custom else model_field.name

        if is_custom:
            form_field = EntitiesBulkUpdateForm.get_custom_formfield(model_field, instance)
        else:
            form_field = EntitiesBulkUpdateForm.get_updatable_formfield(model_field, user, instance)

        fields = self.fields
        fields['field_value'] = form_field

    def save(self):
        instance = self.instance
        field_value = self.cleaned_data['field_value']

        if self.is_custom:
            CustomFieldValue.save_values_for_entities(self.model_field, [instance],
                                                      self.cleaned_data['field_value']
                                                     )
        else:
            setattr(instance, self.field_name, field_value)
            instance.save()

