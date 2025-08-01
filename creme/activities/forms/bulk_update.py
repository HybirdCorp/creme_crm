################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2022-2025  Hybird
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

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django import forms
from django.core.exceptions import ValidationError
from django.db.models.query_utils import Q
from django.utils.timezone import localtime, make_aware
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from creme.creme_core.gui.bulk_update import FieldOverrider

from .. import constants
from ..models import ActivityType
from ..utils import check_activity_collisions
from . import fields


class ActivityRangeWidget(forms.MultiWidget):
    template_name = 'activities/forms/widgets/activity-range.html'

    def __init__(self, attrs=None):
        super().__init__(
            widgets=(
                fields.DateWithOptionalTimeWidget,
                fields.DateWithOptionalTimeWidget,
                forms.CheckboxInput,
                forms.CheckboxInput,
            ),
            attrs=attrs,
        )

    def decompress(self, value):
        return value or ()


class ActivityRangeField(forms.MultiValueField):
    widget = ActivityRangeWidget

    @dataclass(frozen=True)
    class Range:
        start: fields.DateWithOptionalTimeField.DateWithOptionalTime | None
        end: fields.DateWithOptionalTimeField.DateWithOptionalTime | None
        all_day: bool
        busy: bool

    def __init__(self, *, required=True, **kwargs):
        super().__init__(
            (
                fields.DateWithOptionalTimeField(label='Start', required=required),
                fields.DateWithOptionalTimeField(label='End', required=required),
                forms.BooleanField(label='All day', required=False),
                forms.BooleanField(label='Busy', required=False),
            ),
            require_all_fields=False,
            required=required,
            **kwargs
        )

    def compress(self, data_list):
        return self.Range(
            start=data_list[0],
            end=data_list[1],
            all_day=data_list[2],
            busy=data_list[3],
        ) if data_list else None


class RangeOverrider(FieldOverrider):
    field_names = ['start', 'end', 'busy', 'is_all_day']

    error_messages = {
        'floating_cannot_busy': _(
            "A floating on the day activity can't busy its participants"
        ),
        'no_start': _(
            "You can't set the end of your activity without setting its start"
        ),
        'end_before_start': _('End is before start'),
    }

    def formfield(self, instances, user, **kwargs):
        field = ActivityRangeField(
            label=_('When'), required=False,
            help_text=_(
                'You can specify:\n'
                ' - The dates and the times (hour/minute).\n'
                ' - Only the dates; the activity is placed in the calendar anyway '
                '(at the corresponding days).\n'
                ' - Neither the date neither the time; the activity is available '
                'in the calendar view in the panel «Floating activities».'
            ),
            **kwargs
        )

        if len(instances) == 1:
            first = instances[0]

            # TODO: factorise (see <.activity._ActivityDateSubCell.formfield()>)
            def initial_date_tuple(dt):
                dt = localtime(dt)
                return (
                    dt.date(),
                    # None if first.floating_type == constants.FLOATING_TIME else dt.time(),
                    None if first.floating_type == first.FloatingType.FLOATING_TIME else dt.time(),
                )

            field.initial = (
                initial_date_tuple(first.start),
                initial_date_tuple(first.end),
                first.is_all_day,
                first.busy
            )

        return field

    # TODO: factorise with BaseCustomForm._clean_temporal_data() + error_messages
    def post_clean_instance(self, *, instance, value, form):
        start = end = None
        if value.start:
            start_date = value.start.date
            start_time = value.start.time
        else:
            start_date = start_time = None

        if value.end:
            end_date = value.end.date
            end_time = value.end.time
        else:
            end_date = end_time = None

        is_all_day = value.all_day
        busy       = value.busy

        if not start_date:
            if end_date:
                raise ValidationError(self.error_messages['no_start'], code='no_start')

            floating_type = instance.FloatingType.FLOATING
        else:
            floating_type = (
                instance.FloatingType.NARROW
                if start_time or is_all_day else
                instance.FloatingType.FLOATING_TIME
            )

            # TODO: not start_date, not end_date, start time, end time =>
            #       floating activity with time set but lost in the process

            if floating_type == instance.FloatingType.FLOATING_TIME and busy:
                raise ValidationError(
                    self.error_messages['floating_cannot_busy'],
                    code='floating_cannot_busy',
                )

            start = make_aware(datetime.combine(start_date, start_time or time()))

            if end_date:
                end = make_aware(datetime.combine(end_date, end_time or time()))
            elif end_time is not None:
                end = make_aware(datetime.combine(start_date, end_time))
            else:
                tdelta = instance.type.as_timedelta()

                if (
                    is_all_day or floating_type == instance.FloatingType.FLOATING_TIME
                ) and tdelta.days:
                    # In 'all day' mode, we round the number of day
                    # Activity already takes 1 day (we do not want it takes 2)
                    days = tdelta.days - 1

                    if tdelta.seconds:
                        days += 1

                    tdelta = timedelta(days=days)

                end = start + tdelta

            if is_all_day or floating_type == instance.FloatingType.FLOATING_TIME:
                start = make_aware(datetime.combine(start, time(hour=0, minute=0)))
                end   = make_aware(datetime.combine(end,   time(hour=23, minute=59)))

            if start > end:
                raise ValidationError(
                    self.error_messages['end_before_start'],
                    code='end_before_start',
                )

        instance.is_all_day = is_all_day
        instance.busy = busy
        instance.start = start
        instance.end = end
        instance.floating_type = floating_type

        if start:
            collisions = check_activity_collisions(
                activity_start=start,
                activity_end=end,
                participants=instance.get_related_entities(constants.REL_OBJ_PART_2_ACTIVITY),
                busy=busy,
                exclude_activity_id=instance.id,
            )
            if collisions:
                raise ValidationError(collisions)


class TypeOverrider(FieldOverrider):
    field_names = ['type', 'sub_type']

    error_messages = {
        'immutable': _('The type of an unavailability cannot be changed.'),
    }

    _mixed_unavailability = False

    def formfield(self, instances, user, **kwargs):
        unav_type = ActivityType.objects.get(uuid=constants.UUID_TYPE_UNAVAILABILITY)
        field = fields.ActivitySubTypeField(
            label=_('Type'), limit_choices_to=~Q(type=unav_type),
        )

        unavailability_count = sum(a.type_id == unav_type.id for a in instances)

        if unavailability_count:
            if unavailability_count == len(instances):
                # All entities are Unavailability, so we propose to change the subtype.
                field.limit_choices_to = Q(type=unav_type)
            else:
                self._mixed_unavailability = True

                field.help_text = ngettext(
                    'Beware! The type of {count} activity cannot be changed '
                    'because it is an unavailability.',
                    'Beware! The type of {count} activities cannot be changed '
                    'because they are unavailability.',
                    unavailability_count
                ).format(count=unavailability_count)

        if len(instances) == 1:
            first = instances[0]
            field.initial = first.sub_type_id

        return field

    def post_clean_instance(self, *, instance, value, form):
        if (
            self._mixed_unavailability
            and str(instance.type.uuid) == constants.UUID_TYPE_UNAVAILABILITY
        ):
            raise ValidationError(
                self.error_messages['immutable'],
                code='immutable',
            )

        if value:
            instance.type, instance.sub_type = value.type, value
