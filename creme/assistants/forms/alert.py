################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2023  Hybird
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
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.forms import fields, widgets
from django.utils.timezone import localtime
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.entity_cell import CELLS_MAP, EntityCellRegularField
from creme.creme_core.forms import CremeModelForm
from creme.creme_core.forms import fields as core_fields
from creme.creme_core.forms.widgets import PrettySelect
from creme.creme_core.models import CremeEntity, FieldsConfig
from creme.creme_core.utils import date_period
from creme.creme_core.utils.meta import is_date_field

from ..models import Alert

logger = logging.getLogger(__name__)


# TODO: factorise with RelativeDatePeriodWidget?
class ModelRelativeDatePeriodWidget(widgets.MultiWidget):
    template_name = 'creme_core/forms/widgets/date-period.html'

    def __init__(self, period_choices=(), field_choices=(), relative_choices=(), attrs=None):
        super().__init__(
            widgets=(
                # widgets.Select(
                PrettySelect(
                    choices=field_choices,
                    attrs={'class': 'assistants-offset_dperiod-field'},
                ),
                # widgets.Select(
                PrettySelect(
                    choices=relative_choices,
                    attrs={'class': 'assistants-offset_dperiod-direction'},
                ),
                # widgets.Select(
                PrettySelect(
                    choices=period_choices,
                    attrs={'class': 'assistants-offset_dperiod-type'},
                ),
                widgets.NumberInput(
                    attrs={'class': 'assistants-offset_dperiod-value', 'min': 1},
                ),
            ),
            attrs=attrs,
        )

    @property
    def field_choices(self):
        return self.widgets[0].choices

    @field_choices.setter
    def field_choices(self, choices):
        self.widgets[0].choices = choices

    @property
    def period_choices(self):
        return self.widgets[2].choices

    @period_choices.setter
    def period_choices(self, choices):
        self.widgets[2].choices = choices

    @property
    def relative_choices(self):
        return self.widgets[1].choices

    @relative_choices.setter
    def relative_choices(self, choices):
        self.widgets[1].choices = choices

    def decompress(self, value):
        if value:
            # field_name, sign, period = value
            # d = period.as_dict()
            # return field_name, sign, d['type'], d['value']
            d = value.as_dict()
            return d['field'], d['sign'], d['type'], d['value']

        return None, None, None, None

    def get_context(self, name, value, attrs):
        # TODO: see value_from_datadict()
        if isinstance(value, list):
            value = [value[0], value[1][0], *value[1][1]]

        context = super().get_context(name=name, value=value, attrs=attrs)

        try:
            # Translators: this string is used to set the order of the inputs
            # in the widget to choose the relative trigger date of Alerts.
            # Just re-order the format argument, DO NOT ADD other characters (like space...)
            # dateperiod_value: the value of the period ("1" in "1 week)
            # dateperiod_type: the type of the period ("week" in "1 week)
            # dateperiod_direction: "after" or "before"
            # field: the date field of the related entity (creation date, last modification, ...)
            localized_order = _(
                '{dateperiod_value}{dateperiod_type}{dateperiod_direction}{field}'
            ).format(
                dateperiod_type='2',
                dateperiod_value='3',
                dateperiod_direction='1',
                field='0',
            )
            indices = [int(i) for i in localized_order]
        except Exception:  # TODO: better exception
            logger.exception('ModelRelativeDatePeriodWidget.get_context()')
            indices = (0, 1, 2, 3)

        context['widget']['indices'] = indices

        return context

    # TODO: remove this method when we use directly a sub RelativeDatePeriodWidget
    def value_from_datadict(self, data, files, name):
        values = super().value_from_datadict(data=data, files=files, name=name)
        return [values[0], [values[1], values[2:]]]


# TODO: in creme_core ?
# TODO: manage CustomFields
class ModelRelativeDatePeriodField(fields.MultiValueField):
    """Field to choose a relative date period (e.g. "3 weeks before", "1 day after")
    & a (date) model field.
    Hint: see RelativeDatePeriodField too.
    """
    widget = ModelRelativeDatePeriodWidget

    @dataclass(frozen=True)
    class ModelRelativeDatePeriod:
        field_name: str
        relative_period: core_fields.RelativeDatePeriodField.RelativeDatePeriod

        # def __init__(self,
        #              field_name: str,
        #              relative_period: core_fields.RelativeDatePeriodField.RelativeDatePeriod,
        #              ):
        #     self.field_name = field_name
        #     self.relative_period = relative_period

        def __str__(self):
            # TODO: localize?
            return f'{self.relative_period} on field "{self.field_name}"'

        # def __eq__(self, other):
        #     return (
        #         isinstance(other, type(self))
        #         and (self.field_name == other.field_name)
        #         and (self.relative_period == other.relative_period)
        #     )

        def as_dict(self) -> dict:
            "As a jsonifiable dictionary."
            return {
                'field': self.field_name,
                **self.relative_period.as_dict(),
            }

    def __init__(self, *,
                 model=CremeEntity,
                 non_hiddable_cell=None,
                 period_registry=date_period.date_period_registry,
                 period_names=None,
                 **kwargs):
        super().__init__(
            (
                fields.ChoiceField(),
                core_fields.RelativeDatePeriodField(period_registry=period_registry),
            ),
            **kwargs
        )

        self.period_names = period_names
        self.relative_choices = [(-1, _('Before')), (1, _('After'))]
        self.model = model
        self.non_hiddable_cell = non_hiddable_cell

    def _get_field_options(self):
        model = self._model
        is_field_hidden = FieldsConfig.objects.get_for_model(model).is_field_hidden

        non_hiddable_cell = self._non_hiddable_cell
        non_hiddable_fname = (
            '' if non_hiddable_cell is None else non_hiddable_cell.field_info[0].name
        )

        for field in model._meta.fields:
            if is_date_field(field) and (
                not is_field_hidden(field) or field.name == non_hiddable_fname
            ):
                yield field.name, field.verbose_name

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, model):
        self._model = model

        date_fields_f = self.fields[0]
        date_fields_f.choices = self._get_field_options
        self.widget.field_choices = date_fields_f.choices

    @property
    def non_hiddable_cell(self):
        return self._non_hiddable_cell

    @non_hiddable_cell.setter
    def non_hiddable_cell(self, cell):
        if cell is not None:
            if not isinstance(cell, EntityCellRegularField):
                raise ValueError(
                    f'EntityCell must be an instance of EntityCellRegularField ({type(cell)})'
                )

            if cell.model != self._model:
                raise ValueError(
                    f"The model of the EntityCell must the same as the "
                    f"ModelRelativeDatePeriodField's one ({cell.model} != {self._model})."
                )

            field_info = cell.field_info
            if len(field_info) != 1:
                raise ValueError(
                    f"The field of the EntityCell must have only a depth of 1 :"
                    f"({cell.value} => {len(field_info)})."
                )

            if not is_date_field(field_info[0]):
                raise ValueError(
                    f"The field of the EntityCell must be a DateField :"
                    f"yours is a {type(field_info[0])}."
                )

        self._non_hiddable_cell = cell

    @property
    def period_names(self):
        return self.fields[1].period_names

    @period_names.setter
    def period_names(self, period_names):
        """Set the periods which are valid (they must be registered in the related registry too).
        @param period_names: Sequence of strings (see DatePeriod.name for valid values),
               or None (== all available periods in the registry are used).
        """
        period_f = self.fields[1]
        period_f.period_names = period_names
        self.widget.period_choices = period_f.period_choices

    @property
    def period_registry(self):
        return self.fields[1].period_registry

    @period_registry.setter
    def period_registry(self, period_registry):
        period_f = self.fields[1]
        period_f.period_registry = period_registry
        self.widget.period_choices = period_f.period_choices

    @property
    def relative_choices(self):
        return self.fields[1].relative_choices

    @relative_choices.setter
    def relative_choices(self, choices):
        self.fields[1].relative_choices = self.widget.relative_choices = choices

    def compress(self, data_list):
        # return (data_list[0], data_list[1]) if data_list else ()
        return self.ModelRelativeDatePeriod(
            field_name=data_list[0], relative_period=data_list[1],
        ) if data_list and all(data_list) else None

    def validate(self, value):
        # if self.required and not value[1]:
        if self.required and not value:
            raise ValidationError(self.error_messages['required'], code='required')

    # def clean(self, value):
    #     if isinstance(value, (list, tuple)) and len(value) == 4:
    #         value = [value[0], value[1:]]
    #
    #     cleaned = super().clean(value)
    #
    #     return cleaned if (cleaned and cleaned[1]) else ()


# TODO: move to creme_core?
class AbsoluteOrRelativeDatetimeField(core_fields.UnionField):
    ABSOLUTE = 'absolute'
    RELATIVE = 'relative'

    def __init__(self, model=CremeEntity, **kwargs):
        kwargs['fields_choices'] = (
            (self.ABSOLUTE, fields.DateTimeField(label=_('Fixed date'))),
            (
                self.RELATIVE,
                ModelRelativeDatePeriodField(
                    label=_('Relative date'),
                    period_names=(
                        date_period.MinutesPeriod.name,
                        date_period.HoursPeriod.name,
                        date_period.DaysPeriod.name,
                        date_period.WeeksPeriod.name,
                    ),
                ),
            ),
        )

        super().__init__(**kwargs)
        self.model = model

    @property
    def model(self):
        return self._fields_choices[1][1].model

    @model.setter
    def model(self, model):
        self._fields_choices[1][1].model = model

    @property
    def non_hiddable_cell(self):
        return self._fields_choices[1][1].non_hiddable_cell

    @non_hiddable_cell.setter
    def non_hiddable_cell(self, cell):
        self._fields_choices[1][1].non_hiddable_cell = cell


class AlertForm(CremeModelForm):
    trigger = AbsoluteOrRelativeDatetimeField(
        label=_('Trigger date'),
        help_text=_(
            'An email is sent to the owner of the Alert when it is about to '
            'expire (the job «Reminders» must be enabled), if the Alert is not '
            'validated before.\n'
            'Hint #1: if the owner is a team, every teammate receives an email.\n'
            'Hint #2: when you use a relative date, the trigger date is '
            'automatically re-computed when the field of the related entity is '
            'modified.'
        ),
    )

    class Meta(CremeModelForm.Meta):
        model = Alert
        help_texts = {
            'user': _(
                'The owner is only used to send emails (a deadline is required).\n'
                'Hint: the choice «Same owner than the entity» allows to always '
                'send the email to the owner of the entity, even if it is changed.'
            ),
        }

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        instance.real_entity = entity

        fields = self.fields
        fields['user'].empty_label = gettext(
            'Same owner than the entity (currently «{user}»)'
        ).format(user=entity.user)

        trigger_f = fields['trigger']
        trigger_f.model = type(entity)

        if instance.pk is None:  # Creation
            trigger_f.initial = (AbsoluteOrRelativeDatetimeField.ABSOLUTE, {})
        else:  # Edition
            offset = instance.trigger_offset
            if offset:
                RELATIVE = AbsoluteOrRelativeDatetimeField.RELATIVE
                trigger_f.non_hiddable_cell = CELLS_MAP.build_cell_from_dict(
                    model=type(entity),
                    dict_cell=offset['cell'],
                )
                trigger_f.initial = (
                    RELATIVE,
                    {
                        # RELATIVE: (
                        #     offset['cell']['value'],
                        #     offset['sign'],
                        #     date_period.date_period_registry.deserialize(offset['period']),
                        # ),
                        RELATIVE: ModelRelativeDatePeriodField.ModelRelativeDatePeriod(
                            field_name=offset['cell']['value'],
                            relative_period=core_fields.RelativeDatePeriodField.RelativeDatePeriod(
                                sign=offset['sign'],
                                period=date_period.date_period_registry.deserialize(
                                    offset['period']
                                ),
                            )
                        ),
                    },
                )
            else:
                ABSOLUTE = AbsoluteOrRelativeDatetimeField.ABSOLUTE
                trigger_f.initial = (ABSOLUTE, {ABSOLUTE: localtime(instance.trigger_date)})

    def save(self, *args, **kwargs):
        instance = self.instance

        trigger_type, trigger_value = self.cleaned_data['trigger']
        if trigger_type == AbsoluteOrRelativeDatetimeField.ABSOLUTE:
            instance.trigger_date = trigger_value
            instance.trigger_offset = {}
        else:  # RELATIVE
            # field_name, (sign, period) = trigger_value
            cell = EntityCellRegularField.build(
                model=type(instance.real_entity),
                # name=field_name,
                name=trigger_value.field_name,
            )
            relative_period = trigger_value.relative_period
            sign = relative_period.sign
            period = relative_period.period
            instance.trigger_date = instance.trigger_date_from_offset(
                cell=cell, sign=sign, period=period,
                # cell=cell, sign=relative_period.sign, period=relative_period.period,
            )
            instance.trigger_offset = {
                'cell': cell.to_dict(),
                'sign': sign,
                'period': period.as_dict(),
            }

        return super().save(*args, **kwargs)
