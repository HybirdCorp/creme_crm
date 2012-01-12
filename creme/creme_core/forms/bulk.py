# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from itertools import chain

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.forms.fields import CharField, ChoiceField
from django.utils.translation import ugettext, ugettext_lazy as _

from creme_core.models import fields, EntityCredentials, CremeEntity
from creme_core.models.custom_field import CustomField, CustomFieldEnumValue, CustomFieldValue, CustomFieldMultiEnum, CustomFieldEnum
from creme_core.forms import widgets
from creme_core.forms.base import CremeForm, _CUSTOM_NAME
from creme_core.forms.fields import AjaxMultipleChoiceField
from creme_core.utils import entities2unicode
from creme_core.utils.meta import get_flds_with_fk_flds_str, get_verbose_field_name
from creme_core.gui.bulk_update import bulk_update_registry


_datetime_widget = lambda name, choices, value=None: widgets.DateTimeWidget({'id': 'id_%s' % name}) \
                                                            .render(name=name, value=value, attrs=None)

_FIELDS_WIDGETS = {
    models.ManyToManyField: lambda name, choices, value=None: widgets.UnorderedMultipleChoiceWidget({'id': 'id_%s' % name}) \
                                                                     .render(name=name, value=value, attrs=None, choices=choices),
    models.DateField:       lambda name, choices, value=None: widgets.CalendarWidget({'id': 'id_%s' % name}) \
                                                                     .render(name=name, value=value, attrs=None),
    models.DateTimeField:             _datetime_widget,
    fields.CreationDateTimeField:     _datetime_widget,
    fields.ModificationDateTimeField: _datetime_widget,
    CustomFieldMultiEnum:   lambda name, choices, value=None: widgets.UnorderedMultipleChoiceWidget({'id': 'id_%s' % name}) \
                                                                     .render(name=name, value=value, attrs=None, choices=choices),
   }


def _get_choices(model_field, user):
    form_field = model_field.formfield()
    choices = ()
    if isinstance(model_field, (models.ForeignKey, models.ManyToManyField)) and issubclass(model_field.rel.to, CremeEntity):
        fk_entities = model_field.rel.to._default_manager \
                                        .filter(pk__in=[id_ for id_, text in form_field.choices if id_])
        choices = ((e.id, e) for e in EntityCredentials.filter(user, fk_entities))

        if model_field.null and isinstance(model_field, models.ForeignKey):
            choices = chain([(u"", _(u"None"))], choices)

    elif hasattr(form_field, 'choices'):
        choices = form_field.choices

    return choices


class EntitiesBulkUpdateForm(CremeForm):
    entities_lbl = CharField(label=_(u"Entities to update"), widget=widgets.Label)
    field_name = ChoiceField(label=_(u"Field to update"))
    field_value = AjaxMultipleChoiceField(label=_(u"Value"), required=False)

    def __init__(self, model, subjects, forbidden_subjects, user, *args, **kwargs):
        super(EntitiesBulkUpdateForm, self).__init__(user, *args, **kwargs)
        self.subjects = subjects
        self.user = user
        self.model = model
        self.ct = ContentType.objects.get_for_model(model)
        fields = self.fields

        fields['entities_lbl'].initial = entities2unicode(subjects, user) if subjects else ugettext(u'NONE !')
        fields['field_name'].widget = widgets.AdaptiveWidget(ct_id=self.ct.id, field_value_name='field_value')

        if forbidden_subjects:
            fields['bad_entities_lbl'] = CharField(label=ugettext(u"Unchangeable entities"),
                                                   widget=widgets.Label,
                                                   initial=entities2unicode(forbidden_subjects, user)
                                                  )

        excluded_fields = bulk_update_registry.get_excluded_fields(model)#Doesn't include cf
        model_fields = sorted(get_flds_with_fk_flds_str(model, deep=0, exclude_func=lambda f: f.name in excluded_fields),
                              key=lambda k: ugettext(k[1])
                             )
        cf_fields = sorted(((_CUSTOM_NAME % cf.id, cf.name) for cf in CustomField.objects.filter(content_type=self.ct)),
                           key=lambda k: ugettext(k[1])
                          )
        fields['field_name'].choices = ((_(u"Regular fields"), model_fields), (_(u"Custom fields"), cf_fields))

    def _get_field(self, field_name):
        if EntitiesBulkUpdateForm.is_custom_field(field_name):
            return CustomField.objects.get(pk=EntitiesBulkUpdateForm.get_custom_field_id(field_name)) #TODO: cache ??
        else:
            return self.model._meta.get_field(field_name)

    @staticmethod
    def is_custom_field(field_name):
        return field_name.startswith(_CUSTOM_NAME.partition('%s')[0])

    @staticmethod
    def get_custom_field_id(field_name):
        return field_name.replace(_CUSTOM_NAME.partition('%s')[0], '')

    def clean(self, *args, **kwargs):
        super(EntitiesBulkUpdateForm, self).clean(*args, **kwargs)
        cleaned_data = self.cleaned_data

        if self._errors:
            return cleaned_data

        field_value = cleaned_data['field_value']
        field_name  = cleaned_data['field_name']

        if EntitiesBulkUpdateForm.is_custom_field(field_name):
            try:
                field = self._get_field(field_name)
            except CustomField.DoesNotExist:
                raise ValidationError(_(u'Select a valid field.'))
            else:
                try:
                    field_klass = field.get_value_class()
                    if field_value and not issubclass(field_klass, CustomFieldMultiEnum):
                        field_value = field_value[0]

                    form_field = field.get_formfield(None)
                    form_field.initial = field_value
                    field_value = form_field.widget.value_from_datadict(self.data, self.files, 'field_value')
                    field_value = cleaned_data['field_value'] = form_field.clean(field_value)

                except ValidationError, ve:
                    raise ve#For displaying the field error on non-field error


                if field_value and issubclass(field_klass, CustomFieldEnum):
                    try:
#                        field_value = cleaned_data['field_value'] = CustomFieldEnumValue.objects.get(pk=field_value)
                        field_value = CustomFieldEnumValue.objects.get(pk=field_value)
                    except CustomFieldEnumValue.DoesNotExist:
                        raise ValidationError(_(u'Select a valid choice.'))

        else:
            field = self._get_field(field_name)
            m2m = True

            if field_value and not isinstance(field, models.ManyToManyField):
                field_value = field_value[0]
                m2m = False

            try:
                field_value = cleaned_data['field_value'] = field.formfield().clean(field_value)
            except ValidationError, ve:
                raise ve#For displaying the field error on non-field error

            if isinstance(field_value, CremeEntity) and not field_value.can_view(self.user):
                raise ValidationError(ugettext(u"You can't view this value, so you can't set it."))

            if field_value is None and not field.null:
                raise ValidationError(ugettext(u'This field is required.'))

            # TODO comment on 30/11/2011 : old condition does not allow 0 value
#           if not (field_value or field.blank):
            if not (field_value is not None or field.blank):
                raise ValidationError(ugettext(u'This field is required.'))

            valid_choices = [entity for id_, entity  in _get_choices(field, self.user)]

            #Checking valid choices & credentials
            if isinstance(field, (models.ForeignKey, models.ManyToManyField)) and issubclass(field.rel.to, CremeEntity):
                if m2m:
                    for field_val in field_value:
                        if field_val not in valid_choices:
                            raise ValidationError(_(u'Select a valid choice.'))
                else:
                    if field_value not in valid_choices:
                        raise ValidationError(_(u'Select a valid choice.'))

        return cleaned_data

    def save(self):
        cleaned_data = self.cleaned_data
        field_value = cleaned_data['field_value']
        field_name  = cleaned_data['field_name']

        ##post_save_function = self.model.post_save_bulk if hasattr(self.model, 'post_save_bulk') else lambda x, y, z: None
        #already_saved = False

        if EntitiesBulkUpdateForm.is_custom_field(field_name):
            field = self._get_field(field_name)
            CustomFieldValue.save_values_for_entities(field, self.subjects, field_value)
        else:
            ##.update doesn't either send any signal or call save, and when changing entity's user credentials have to be regenerated
            ## todo: Override the default manager ?
            #if field_name == "user":
                #for subject in self.subjects:
                    #subject.user = field_value
                    #subject.save()
                #already_saved = True
            #else:
                #model_field = self._get_field(field_name)#self.model._meta.get_field(field_name)
                #if not isinstance(model_field, models.ManyToManyField):
                    #self.model.objects.filter(pk__in=self.subjects)\
                                      #.update(**{field_name: field_value})#Doesn't work with m2m
                #else:
                    #for subject in self.subjects:
                        #setattr(subject, field_name, field_value)
                        #subject.save()
                    #already_saved = True

            # TODO: Override the default manager ?
            #NB: we do not use update() because it avoids signal, method overloading etc...
            for subject in self.subjects:
                setattr(subject, field_name, field_value)
                subject.save()

        ##post_save_function(self.subjects, field_name, already_saved)
        #post_save_function = getattr(self.model, 'post_save_bulk', None)
        #if post_save_function:
            #post_save_function(self.subjects, field_name, already_saved)


class EntityInnerEditForm(EntitiesBulkUpdateForm):
    #def __init__(self, model, field_name, subjects, forbidden_subjects, user, *args, **kwargs):
    def __init__(self, model, field_name, subject, user, *args, **kwargs):
        #super(EntityInnerEditForm, self).__init__(model, subjects, forbidden_subjects, user, *args, **kwargs)
        super(EntityInnerEditForm, self).__init__(model, [subject], (), user, *args, **kwargs)
        self.field_name = field_name

        verbose_field_name = self._get_field(field_name).name if self.is_custom_field(field_name) else get_verbose_field_name(model, field_name)
        verbose_model_name = model._meta.verbose_name.title()

        fields = self.fields

        f_entities_lbl = fields['entities_lbl']
        f_entities_lbl.label    = ugettext(u'Entity')
        f_entities_lbl.required = False

        f_field_name = fields['field_name']
        #f_field_name.widget = widgets.AdaptiveWidget(ct_id=self.ct.id, field_value_name='field_value', object_id=subjects[0].id)
        f_field_name.widget = widgets.AdaptiveWidget(ct_id=self.ct.id, field_value_name='field_value', object_id=subject.id)
        f_field_name.widget.attrs['disabled'] = True #TODO: in the previous line
        f_field_name.label = ugettext(u'Field')
        f_field_name.choices = [(field_name, "%s - %s" % (verbose_model_name, verbose_field_name))]
        f_field_name.required = False

    def clean(self, *args, **kwargs):
        self.cleaned_data['field_name'] = self.field_name
        return super(EntityInnerEditForm, self).clean(*args, **kwargs)
