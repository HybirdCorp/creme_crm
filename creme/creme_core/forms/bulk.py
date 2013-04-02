# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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
from itertools import chain

from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.forms.fields import CharField, ChoiceField
from django.utils.translation import ugettext, ugettext_lazy as _

from creme.creme_core.models import fields, EntityCredentials, CremeEntity
from creme.creme_core.models.custom_field import CustomField, CustomFieldEnumValue, CustomFieldValue, CustomFieldMultiEnum, CustomFieldEnum
from creme.creme_core.forms.widgets import DateTimeWidget, CalendarWidget, UnorderedMultipleChoiceWidget, Label, AdaptiveWidget
from creme.creme_core.forms.base import CremeForm, _CUSTOM_NAME
from creme.creme_core.forms.fields import AjaxMultipleChoiceField
from creme.creme_core.utils import entities2unicode, related2unicode
from creme.creme_core.utils.meta import get_verbose_field_name
from creme.creme_core.gui.bulk_update import bulk_update_registry


_FIELDS_WIDGETS = {
        models.ManyToManyField:           UnorderedMultipleChoiceWidget(),
        models.DateField:                 CalendarWidget(),
        models.DateTimeField:             DateTimeWidget(),
        fields.CreationDateTimeField:     DateTimeWidget(),
        fields.ModificationDateTimeField: DateTimeWidget(),
        CustomFieldMultiEnum:             UnorderedMultipleChoiceWidget(),
    }

_CUSTOM_PREFIX = _CUSTOM_NAME.partition('%s')[0]

#TODO : staticmethod ??
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
    field_value  = AjaxMultipleChoiceField(label=_(u"Value"), required=False)

    def get_cfields_cache(self):
        return dict((cf.pk, cf) for cf in CustomField.objects.filter(content_type=self.ct))

    def __init__(self, model, subjects, forbidden_subjects, user, *args, **kwargs):
        super(_EntitiesEditForm, self).__init__(user, *args, **kwargs)

        self.subjects = subjects
        self.user = user
        self.model = model
        self.ct = ContentType.objects.get_for_model(model)
        self._cfields_cache = None

        fields = self.fields

        if subjects:
            fields['entities_lbl'].initial = related2unicode(subjects[0], user) if hasattr(subjects[0], 'get_related_entity') else entities2unicode(subjects, user)
        else:
            fields['entities_lbl'].initial = ugettext(u'NONE !')

        if forbidden_subjects:
            fields['bad_entities_lbl'] = CharField(label=ugettext(u"Uneditable entities"),
                                                   widget=Label,
                                                   initial=entities2unicode(forbidden_subjects, user)
                                                  )

    @staticmethod
    def get_field(model, field_name, cfields_cache=None):
        field = None

        try:
            cf_id = int(field_name.replace(_CUSTOM_PREFIX, ''))
        except:
            is_custom = False

            try:
                field = model._meta.get_field(field_name)
            except FieldDoesNotExist:
                pass
        else: #custom_field
            is_custom = True

            try:
                field = cfields_cache[cf_id] if cfields_cache is not None else \
                        CustomField.objects.get(pk=cf_id)
            except (KeyError, CustomField.DoesNotExist):
                pass

        return (field, is_custom)

    def clean(self, *args, **kwargs):
        super(_EntitiesEditForm, self).clean(*args, **kwargs)
        cleaned_data = self.cleaned_data

        if self._errors:
            return cleaned_data

        field_value = cleaned_data['field_value']
        field_name  = cleaned_data['field_name']

        field, is_custom = self.get_field(self.model, field_name, self._cfields_cache)

        if field is None:
            raise ValidationError(_(u'Select a valid field.'))

        if is_custom:
            self._custom_field = field
            field_klass = field.get_value_class()
            if field_value and not issubclass(field_klass, CustomFieldMultiEnum):
                field_value = field_value[0]

            form_field = field.get_formfield(None)
            form_field.initial = field_value #TODO: useful ??
            cleaned_value = form_field.clean(form_field.widget.value_from_datadict(self.data, self.files, 'field_value'))

            if cleaned_value and issubclass(field_klass, CustomFieldEnum):
                if not CustomFieldEnumValue.objects.filter(pk=cleaned_value).exists():
                    raise ValidationError(_(u'Select a valid choice.'))
        else:
            self._custom_field = None
            m2m = True

            if field_value and not isinstance(field, models.ManyToManyField):
                field_value = field_value[0]
                m2m = False

            cleaned_value = field.formfield().clean(field_value)

            if isinstance(cleaned_value, CremeEntity) and not cleaned_value.can_view(self.user):
                raise ValidationError(ugettext(u"You can't view this value, so you can't set it."))

            if cleaned_value is None and not field.null:
                raise ValidationError(ugettext(u'This field is required.'))

            if not (cleaned_value is not None or field.blank):
                raise ValidationError(ugettext(u'This field is required.'))

            #Checking valid choices & credentials
            if isinstance(field, (models.ForeignKey, models.ManyToManyField)) and issubclass(field.rel.to, CremeEntity):
                valid_choices = [entity or None for id_, entity in _get_choices(field, self.user)]
                if m2m:
                    for field_val in cleaned_value:
                        if field_val not in valid_choices:
                            raise ValidationError(_(u'Select a valid choice.'))
                elif cleaned_value is not None and cleaned_value not in valid_choices:
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

        f_field_name = self.fields['field_name']
        f_field_name.widget = AdaptiveWidget(ct_id=self.ct.id, field_value_name='field_value')
        f_field_name.choices = (
            (ugettext(u"Regular fields"), sort((unicode(field.name), unicode(field.verbose_name)) for field in bulk_update_registry.get_fields(model))),
            (ugettext(u"Custom fields"),  sort((_CUSTOM_NAME % cf.id, cf.name) for cf in self._cfields_cache.itervalues())),
          )


class EntityInnerEditForm(_EntitiesEditForm):
    class InvalidField(Exception):
        pass

    def __init__(self, model, field_id, subject, user, *args, **kwargs):
        """@param field_id Name of a regular field, or pk (as int or string) for CustomFields."""
        super(EntityInnerEditForm, self).__init__(model, [subject], (), user, *args, **kwargs)

        self.field_name = field_name = _CUSTOM_NAME % field_id if field_id.isdigit() else \
                                       field_id #TODO: the reverse work is done in self.get_field()...
        field, is_custom = self.get_field(self.model, field_name)

        if is_custom:
            verbose_field_name = field.name
        else:
            if not bulk_update_registry.is_bulk_updatable(model, field_name, exclude_unique=False):
                raise self.InvalidField(u'The field %s.%s is not editable' % (model, field_name))

            verbose_field_name = get_verbose_field_name(model, field_name)

        fields = self.fields

        fields['entities_lbl'].label = ugettext(u'Entity')

        f_field_name = fields['field_name']
        f_field_name.widget = AdaptiveWidget(ct_id=self.ct.id, field_value_name='field_value', object_id=subject.id, attrs={'disabled': True})
        f_field_name.label = ugettext(u'Field')
        f_field_name.choices = [(field_name, "%s - %s" % (model._meta.verbose_name.title(), verbose_field_name))]
        f_field_name.required = False

    def clean(self, *args, **kwargs):
        self.cleaned_data['field_name'] = self.field_name
        return super(EntityInnerEditForm, self).clean(*args, **kwargs)
