# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from creme_core.forms import widgets
from creme_core.forms.base import CremeForm
from creme_core.forms.fields import AjaxMultipleChoiceField
from creme_core.utils import entities2unicode
from creme_core.utils.meta import get_flds_with_fk_flds_str
from creme_core.gui.bulk_update import bulk_update_registry

_FIELDS_WIDGETS = {
    models.DateField: lambda name, choices:widgets.CalendarWidget({'id': 'id_%s' % name}).render(name=name, value=None, attrs=None),
    models.DateTimeField: lambda name, choices:widgets.DateTimeWidget({'id': 'id_%s' % name}).render(name=name, value=None, attrs=None),
    models.ManyToManyField: lambda name, choices: widgets.UnorderedMultipleChoiceWidget({'id': 'id_%s' % name}).render(name=name, value=None, attrs=None, choices=choices),
}

_FIELDS_WIDGETS[fields.CreationDateTimeField] = _FIELDS_WIDGETS[fields.ModificationDateTimeField] = _FIELDS_WIDGETS[models.DateTimeField]

def _get_choices(model_field, user):
    form_field = model_field.formfield()
    choices = ()
    if isinstance(model_field, (models.ForeignKey, models.ManyToManyField)) and issubclass(model_field.rel.to, CremeEntity):
        fk_entities = model_field.rel.to._default_manager.filter(pk__in=[id_ for id_, text in form_field.choices if id_])

        choices = ((e.id, e) for e in EntityCredentials.filter(user, fk_entities))

        if model_field.null and isinstance(model_field, models.ForeignKey):
            choices = chain([(u"", _(u"None"))], choices)

    elif hasattr(form_field, 'choices'):
        choices = form_field.choices

    return choices

class EntitiesBulkUpdateForm(CremeForm):
    entities_lbl = CharField(label=_(u"Entities to update"), widget=widgets.Label)
    field_name   = ChoiceField(label=_(u"Field to update"))
    field_value  = AjaxMultipleChoiceField(label=_(u"Value"), required=False)

    def __init__(self, model, subjects, forbidden_subjects, user, *args, **kwargs):
        super(EntitiesBulkUpdateForm, self).__init__(user, *args, **kwargs)
        self.subjects = subjects
        self.user = user
        self.model = model
        fields = self.fields

        fields['entities_lbl'].initial = entities2unicode(subjects, user) if subjects else ugettext(u'NONE !')

        fields['field_name'].widget = widgets.AdaptiveWidget(ct_id=ContentType.objects.get_for_model(model).id, field_value_name='field_value')

        if forbidden_subjects:
            fields['bad_entities_lbl'] = CharField(label=ugettext(u"Unchangeable entities"),
                                                        widget=widgets.Label,
                                                        initial=entities2unicode(forbidden_subjects, user)
                                                       )

        excluded_fields = bulk_update_registry.get_excluded_fields(model)
        #TODO: Add customs fields
        fields['field_name'].choices = sorted(get_flds_with_fk_flds_str(model, deep=0, exclude_func=lambda f: f.name in excluded_fields), key=lambda k: ugettext(k[1]))

    def clean(self, *args, **kwargs):
        super(EntitiesBulkUpdateForm, self).clean(*args, **kwargs)
        cleaned_data = self.cleaned_data

        if self._errors:
            return cleaned_data
        
        field_value = cleaned_data['field_value']
        field_name  = cleaned_data['field_name']

        field = self.model._meta.get_field(field_name)
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

        if not (field_value or field.blank):
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

        #.update doesn't either send any signal or call save, and when changing entity's user credentials have to be regenerated
        # TODO: Override the default manager ?
        if field_name == "user":
            for subject in self.subjects:
                subject.user = field_value
                subject.save()
        else:
            model_field = self.model._meta.get_field(field_name)
            if not isinstance(model_field, models.ManyToManyField):
                self.model.objects.filter(pk__in=self.subjects).update(**{field_name:field_value})#TODO: Doesn't work with m2m
            else:
                for subject in self.subjects:
                    setattr(subject, field_name, field_value)
                    subject.save()

