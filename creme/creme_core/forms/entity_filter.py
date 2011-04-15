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

#from logging import debug

from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext

from creme_core.models import CremeEntity, EntityFilter, EntityFilterCondition
from creme_core.forms import CremeModelForm
from creme_core.forms.fields import JSONField
from creme_core.forms.widgets import DynamicInput, SelectorList, ChainedInput
from creme_core.utils.id_generator import generate_string_id_and_save
from creme_core.utils.meta import is_date_field


class EntityFilterConditionsWidget(SelectorList):
    def __init__(self, model, attrs=None):
        chained_input = ChainedInput(attrs)
        attrs = {'auto': False}

        excluded = model.header_filter_exclude_fields
        model_fields = [(f.name, f.verbose_name) for f in model._meta.fields
                            if f.name not in excluded and
                               not is_date_field(f) and
                               not f.get_internal_type() == 'ForeignKey'
                       ]

        chained_input.add_dselect('name', options=model_fields, attrs=attrs)
        chained_input.add_dselect('type', options=EntityFilterCondition._OPERATOR_MAP.iteritems(), attrs=attrs)
        chained_input.add_input('value', DynamicInput, attrs=attrs)

        super(EntityFilterConditionsWidget, self).__init__(chained_input)


class EntityFilterConditionsField(JSONField):
    default_error_messages = {
        'invalidfield': _(u"This field is invalid with this model."),
    }

    def __init__(self, model=None, *args, **kwargs):
        super(EntityFilterConditionsField, self).__init__(*args, **kwargs)
        self.model = model or CremeEntity

    def _set_model(self, model):
        self._model = model
        self._build_widget()

    model = property(lambda self: self._model, _set_model); del _set_model

    def _create_widget(self):
        return EntityFilterConditionsWidget(self.model)

    #TODO: remove this hack ??
    def from_python(self, value):
        if not value:
            return ''

        if isinstance(value, basestring):
            return value

        return self.format_json([{'type':  condition.type,
                                  'name':  condition.name,
                                  'value': condition.decoded_value,
                                 } for condition in value
                                ]
                               )

    def clean(self, value):
        data = self.clean_json(value)

        if not data:
            if self.required:
                raise ValidationError(self.error_messages['required'])

            return []

        #if not isinstance(data, list):
            #raise ValidationError(self.error_messages['invalidformat'])

        build_condition = EntityFilterCondition.build
        clean_value = self.clean_value

        try:
            conditions = [build_condition(model=self.model,
                                          type=clean_value(entry, 'type', int),
                                          name=clean_value(entry, 'name', str),
                                          value=clean_value(entry, 'value', unicode),
                                         )
                                for entry in data
                         ]
        except EntityFilterCondition.ValueError:
            raise ValidationError(self.error_messages['invalidfield'])

        return conditions


class _EntityFilterForm(CremeModelForm):
    conditions = EntityFilterConditionsField(label=_(u'Conditions'))

    class Meta:
        model = EntityFilter

    def __init__(self, *args, **kwargs):
        super(_EntityFilterForm, self).__init__(*args, **kwargs)
        fields = self.fields
        fields['user'].empty_label = ugettext(u'All users')
        fields['use_or'].help_text = ugettext(u'Use "OR" between the conditions (else "AND" is used).')


class EntityFilterCreateForm(_EntityFilterForm):
    def __init__(self, *args, **kwargs):
        super(EntityFilterCreateForm, self).__init__(*args, **kwargs)
        ct = self.initial['content_type']
        self._entity_type = ct
        self.fields['conditions'].model = ct.model_class()

    def save(self, *args, **kwargs):
        instance = self.instance
        ct = self._entity_type

        instance.is_custom = True
        instance.entity_type = ct

        super(EntityFilterCreateForm, self).save(commit=False, *args, **kwargs)
        generate_string_id_and_save(EntityFilter, [instance], 'creme_core-userfilter_%s-%s' % (ct.app_label, ct.model))

        instance.set_conditions(self.cleaned_data['conditions'])

        return instance


class EntityFilterEditForm(_EntityFilterForm):
    def __init__(self, *args, **kwargs):
        super(EntityFilterEditForm, self).__init__(*args, **kwargs)

        conditions_field = self.fields['conditions']
        instance = self.instance
        conditions_field.model   = instance.entity_type.model_class()
        conditions_field.initial = instance.conditions.all()

    def save(self, *args, **kwargs):
        instance = super(EntityFilterEditForm, self).save(*args, **kwargs)
        instance.set_conditions(self.cleaned_data['conditions'])

        return instance
