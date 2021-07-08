# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from collections import OrderedDict
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.forms import ModelChoiceField
from django.forms.fields import CallableChoiceIterator
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ..core.batch_process import BatchAction, batch_operator_manager
from ..creme_jobs.batch_process import batch_process_type
from ..gui import bulk_update
from ..models import CremeEntity, EntityFilter, Job
from ..utils.unicode_collation import collator
from ..utils.url import TemplateURLBuilder
from .base import CremeModelForm
from .fields import JSONField
from .widgets import ChainedInput, DynamicInput, PolymorphicInput, SelectorList


class BatchActionsWidget(SelectorList):
    def __init__(self, model=CremeEntity, fields=(), attrs=None):
        super().__init__(selector=None, attrs=attrs)
        self.model = model
        self.fields = fields

    def get_context(self, name, value, attrs):
        # TODO: "if self.selector is None" ??
        # TODO: creating the instance here is ugly (use a SelectorList instead of inherit it ?)
        self.selector = chained_input = ChainedInput()
        sub_attrs = {'auto': False}

        # TODO: improve SelectorList.add_* to avoid attribute 'auto'
        chained_input.add_dselect('name', attrs=sub_attrs, options=self.fields)
        chained_input.add_dselect(
            'operator', attrs=sub_attrs,
            # TODO: use a GET arg instead of using a TemplateURLBuilder ?
            options=TemplateURLBuilder(
                field=(TemplateURLBuilder.Word, '${name}'),
            ).resolve(
                'creme_core__batch_process_ops',
                kwargs={'ct_id': ContentType.objects.get_for_model(self.model).id},
            ),
        )

        pinput = PolymorphicInput(key='${operator}', attrs=sub_attrs)
        # TODO: count if the operators with need_arg=False are more ?
        pinput.set_default_input(widget=DynamicInput, attrs=sub_attrs)

        for op_id, operator in batch_operator_manager.operators():
            if not operator.need_arg:
                # TODO: DynamicHiddenInput
                pinput.add_input(op_id, widget=DynamicInput, attrs=sub_attrs, type='hidden')

        chained_input.add_input('value', pinput, attrs=sub_attrs)

        return super().get_context(name=name, value=value, attrs=attrs)


class BatchActionsField(JSONField):
    widget = BatchActionsWidget  # Should have 'model' & 'fields' attributes
    default_error_messages = {
        'invalidfield':    _('This field is invalid with this model.'),
        'reusedfield':     _('The field «%(field)s» can not be used twice.'),
        'invalidoperator': _('This operator is invalid.'),
        'invalidvalue':    _('Invalid value => %(error)s'),
    }

    value_type = list
    _fields = None

    def __init__(self, *, model=CremeEntity, bulk_update_registry=None, **kwargs):
        super().__init__(**kwargs)
        self.model = model
        self.bulk_update_registry = bulk_update_registry or bulk_update.bulk_update_registry

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, model):
        self._model = model

        widget = self.widget
        widget.model = model
        widget.fields = CallableChoiceIterator(
            lambda: [
                (fname, field.verbose_name)
                for fname, field in self._get_fields().items()
            ]
        )

    def _get_fields(self):
        if self._fields is None:
            fields = []
            model = self._model
            managed_fields = tuple(batch_operator_manager.managed_fields)
            registry = self.bulk_update_registry
            updatable = partial(
                registry.is_updatable, model=model, exclude_unique=False,
            )
            get_form = registry.status(model).get_form

            for field in model._meta.fields:
                if field.editable and isinstance(field, managed_fields):
                    fname = field.name

                    # Not a specific form (ie: specific business logic) TODO: test
                    if updatable(field_name=fname) and get_form(fname) is None:
                        fields.append((field.name, field))

            sort_key = collator.sort_key
            fields.sort(key=lambda c: sort_key(str(c[1].verbose_name)))

            self._fields = OrderedDict(fields)

        return self._fields

    def _clean_fieldname(self, entry, used_fields):
        fname = self.clean_value(entry, 'name', str)
        field = self._get_fields().get(fname)

        if not field:
            raise ValidationError(
                self.error_messages['invalidfield'], code='invalidfield',
            )

        if fname in used_fields:
            raise ValidationError(
                self.error_messages['reusedfield'],
                params={'field': field.verbose_name},
                code='reusedfield',
            )

        used_fields.add(fname)

        return fname

    def _clean_operator_name_n_value(self, entry):
        clean_value = self.clean_value
        operator_name = clean_value(entry, 'operator', str)
        value = clean_value(entry, 'value', str)

        return operator_name, value

    def _value_from_unjsonfied(self, data):
        actions = []
        model = self._model
        clean_fieldname = self._clean_fieldname
        clean_operator_n_value = self._clean_operator_name_n_value
        used_fields = set()

        for entry in data:
            try:
                action = BatchAction(
                    model, clean_fieldname(entry, used_fields),
                    *clean_operator_n_value(entry),
                )
            except BatchAction.InvalidOperator:
                raise ValidationError(
                    self.error_messages['invalidoperator'], code='invalidoperator',
                )
            except BatchAction.ValueError as e:
                raise ValidationError(
                    self.error_messages['invalidvalue'],
                    params={'error': e}, code='invalidvalue',
                )

            actions.append(action)

        return actions


class BatchProcessForm(CremeModelForm):
    filter = ModelChoiceField(
        label=pgettext_lazy('creme_core-noun', 'Filter'),
        queryset=EntityFilter.objects.none(),
        empty_label=pgettext_lazy('creme_core-filter', 'All'),
        required=False,
    )
    actions = BatchActionsField(label=_('Actions'))

    class Meta:
        model = Job
        exclude = ('reference_run', 'periodicity')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ct = ct = self.initial['content_type']

        fields = self.fields
        fields['filter'].queryset = EntityFilter.objects\
                                                .filter_by_user(self.user)\
                                                .filter(entity_type=ct)
        fields['actions'].model = self._entity_type = ct.model_class()

    def save(self, *args, **kwargs):
        instance = self.instance
        cdata = self.cleaned_data
        job_data = {
            'ctype': self.ct.id,
            'actions': [
                {
                    'field_name':    a._field_name,
                    'operator_name': a._operator.id,
                    'value':         a._value,
                } for a in cdata['actions']
            ],
        }

        efilter = cdata.get('filter')
        if efilter:
            job_data['efilter'] = efilter.id

        instance.type = batch_process_type
        instance.user = self.user
        instance.data = job_data

        return super().save(*args, **kwargs)
