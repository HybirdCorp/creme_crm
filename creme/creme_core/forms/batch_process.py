# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.forms import ModelChoiceField
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from ..core.batch_process import batch_operator_manager, BatchAction
from ..models import CremeEntity, EntityFilter, EntityCredentials
from ..utils.chunktools import iter_as_slices
from ..utils.collections import LimitedList
from .base import CremeForm
from .fields import JSONField
from .widgets import DynamicInput, SelectorList, ChainedInput, PolymorphicInput


logger = logging.getLogger(__name__)


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

        pinput = PolymorphicInput(key='${operator}', attrs=attrs)
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

    value_type = list

    def __init__(self, model=None, *args, **kwargs):
        super(BatchActionsField, self).__init__(*args, **kwargs)
        self.model = model or CremeEntity

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
        value = clean_value(entry, 'value', unicode)

        return operator_name, value

    def _value_from_unjsonfied(self, data):
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

    _modified_objects_count = 0
    _read_objects_count = 0

    def __init__(self, *args, **kwargs):
        super(BatchProcessForm, self).__init__(*args, **kwargs)
        ct = self.initial['content_type']
        fields = self.fields
        fields['filter'].queryset = EntityFilter.objects.filter(entity_type=ct)
        fields['actions'].model = self._entity_type = ct.model_class()

        self.process_errors = LimitedList(50)

    def _humanize_validation_error(self, ve):
        meta = self._entity_type._meta

        try:
            #TODO: NON_FIELD_ERRORS need to be unit tested...
            humanized = [unicode(errors) if field == NON_FIELD_ERRORS else
                         u'%s => %s' % (meta.get_field(field).verbose_name, u', '.join(errors))
                             for field, errors in ve.message_dict.iteritems()
                        ]
        except Exception as e:
            logger.debug('BatchProcessForm._humanize_validation_error: %s', e)
            humanized = [unicode(ve)]

        return humanized

    @property
    def entity_type(self):
        return self._entity_type

    @property
    def modified_objects_count(self):
        return  self._modified_objects_count

    @property
    def read_objects_count(self):
        return  self._read_objects_count

    #TODO: move to a job when job engine is done
    def save(self, *args, **kwargs):
        cdata = self.cleaned_data
        entities = self._entity_type.objects.all()
        process_errors = self.process_errors
        efilter = cdata.get('filter')

        if efilter:
            entities = efilter.filter(entities)

        entities = EntityCredentials.filter(self.user, entities, EntityCredentials.CHANGE)
        actions = cdata['actions']
        mod_count = read_count = 0

        for entities_slice in iter_as_slices(entities, 1024):
            for entity in entities_slice:
                read_count += 1
                changed = False

                #we snapshot the unicode representation here, because the actions
                #could modify the field used to build it.
                entity_repr = unicode(entity)

                for action in actions:
                    if action(entity):
                        changed = True

                if changed:
                    try:
                        entity.full_clean()
                    except ValidationError as e:
                        process_errors.append((unicode(entity_repr), self._humanize_validation_error(e)))
                    else:
                        entity.save()
                        mod_count += 1

        self._read_objects_count = read_count
        self._modified_objects_count = mod_count
