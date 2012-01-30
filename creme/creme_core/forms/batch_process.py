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

from django.forms import ModelChoiceField, ValidationError
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, EntityFilter, EntityFilterCondition, EntityCredentials
from creme_core.forms import CremeForm
from creme_core.forms.fields import JSONField
from creme_core.forms.widgets import DynamicInput, SelectorList, ChainedInput, PolymorphicInput
from creme_core.core.batch_process import batch_operator_manager, BatchAction
from creme_core.utils.chunktools import iter_as_slices


class BatchActionsWidget(SelectorList):
    def __init__(self, model, fields, attrs=None):
        chained_input = ChainedInput(attrs)
        attrs = {'auto': False}

        #TODO: improve SelectorList.add_* to avoid attribute 'auto'
        chained_input.add_dselect('name', attrs=attrs,
                                  options=[(fname, field.verbose_name) for fname, field in fields.iteritems()]
                                 )
        chained_input.add_dselect('operator', attrs=attrs,
                                  options='/creme_core/list_view/batch_process/%s/get_ops/${name}' % ContentType.objects.get_for_model(model).id
                                 )

        pinput = PolymorphicInput(url='${operator}', attrs=attrs)
        pinput.set_default_input(widget=DynamicInput, attrs=attrs) #TODO: count if the operators with need_arg=False are more ?

        for op_id, operator in batch_operator_manager.operators():
            if not operator.need_arg:
                pinput.add_input(op_id, widget=DynamicInput, attrs=attrs, type='hidden') #TODO: DynamicHiddenInput

        chained_input.add_input('value', pinput, attrs=attrs)

        super(BatchActionsWidget, self).__init__(chained_input)


class BatchActionsField(JSONField):
    default_error_messages = {
        'invalidfield':    _(u"This field is invalid with this model."),
        'reusedfield':     _(u"The field '%s' can not be used twice."),
        'invalidoperator': _(u"This operator is invalid."),
        'invalidvalue':    _(u"Invalid value => %s"),
    }

    def __init__(self, model=None, *args, **kwargs):
        super(BatchActionsField, self).__init__(*args, **kwargs)
        self.model = model or CremeEntity

    def from_python(self, value):
        if not value:
            return ''

        if isinstance(value, basestring):
            return value

        #return self.format_json(self._actions_to_dicts(value)) #todo: inline

    def clean(self, value):
        data = self.clean_json(value)

        if not data:
            if self.required:
                raise ValidationError(self.error_messages['required'])

            return []

        return self._actions_from_dicts(data) #TODO: inline ??

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, model):
        self._model = model
        self._fields = fields = {}
        managed_fields = tuple(batch_operator_manager.managed_fields)

        #excluded = model.header_filter_exclude_fields

        for field in model._meta.fields:
            if field.editable and isinstance(field, managed_fields):
                fields[field.name] = field

        self._build_widget()

    def _create_widget(self):
        return BatchActionsWidget(self._model, self._fields)

    #def _actions_to_dicts(self, actions):
        #dicts = []

        #for action in actions:
            #dicts.append({'name':     action.name,
                          #'operator': operator,
                         #})

        #return dicts

    def _clean_fieldname(self, entry, used_fields):
        fname = self.clean_value(entry, 'name', str)
        field = self._fields.get(fname)

        if not field:
            raise ValidationError(self.error_messages['invalidfield'])

        if fname in used_fields:
            raise ValidationError(self.error_messages['reusedfield'] % field.verbose_name)

        used_fields.add(fname)

        return fname

    def _clean_operator_name_n_value(self, entry):
        clean_value =  self.clean_value
        operator_name = clean_value(entry, 'operator', str)
        value = clean_value(clean_value(entry, 'value', dict), 'value', unicode)

        return operator_name, value

    def _actions_from_dicts(self, data):
        model = self._model
        clean_fieldname = self._clean_fieldname
        clean_operator_n_value = self._clean_operator_name_n_value
        used_fields = set()
        actions = []

        for entry in data:
            try:
                action = BatchAction(model, clean_fieldname(entry, used_fields), *clean_operator_n_value(entry))
            except BatchAction.InvalidOperator as e:
                raise ValidationError(self.error_messages['invalidoperator'])
            except BatchAction.ValueError as e:
                raise ValidationError(self.error_messages['invalidvalue'] % e)

            actions.append(action)

        return actions


class BatchProcessForm(CremeForm):
    filter  = ModelChoiceField(label=_(u'Filter'), queryset=EntityFilter.objects.none(), empty_label=_(u'All'), required=False)
    actions = BatchActionsField(label=_(u'Actions'))

    def __init__(self, *args, **kwargs):
        super(BatchProcessForm, self).__init__(*args, **kwargs)
        ct = self.initial['content_type']
        fields = self.fields
        fields['filter'].queryset = EntityFilter.objects.filter(entity_type=ct)
        fields['actions'].model = self._entity_type = ct.model_class()

    def save(self, *args, **kwargs):
        cdata = self.cleaned_data
        entities = self._entity_type.objects.all()
        efilter = cdata.get('filter')

        if efilter:
            entities = efilter.filter(entities)

        entities = EntityCredentials.filter(self.user, entities, EntityCredentials.CHANGE)
        actions = cdata['actions']

        for entities_slice in iter_as_slices(entities, 1024):
            for entity in entities_slice:
                changed = False

                for action in actions:
                    if action(entity):
                        changed = True

                if changed:
                    entity.save()
