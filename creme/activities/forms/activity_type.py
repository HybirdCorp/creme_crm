################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

from django.core.exceptions import ValidationError
# from django.utils.translation import ngettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

import creme.creme_core.forms.fields as core_fields
from creme.creme_core.forms import CremeModelForm
# from creme.creme_core.forms.bulk import BulkDefaultEditForm
from creme.creme_core.gui.bulk_update import FieldOverrider
from creme.creme_core.utils.id_generator import generate_string_id_and_save

from ..constants import ACTIVITYTYPE_INDISPO
from ..models import ActivitySubType, ActivityType
from .fields import ActivityTypeField


class ActivityTypeForm(CremeModelForm):
    default_hour_duration = core_fields.DurationField(label=_('Duration'))

    class Meta(CremeModelForm.Meta):
        model = ActivityType

    def save(self):  # TODO: *args, **kwargs
        instance = self.instance

        if not instance.id:
            super().save(commit=False)
            generate_string_id_and_save(
                ActivityType, [instance], 'creme_config-useractivitytype',
            )
        else:
            super().save()

        return instance


class ActivitySubTypeForm(CremeModelForm):
    class Meta(CremeModelForm.Meta):
        model = ActivitySubType

    def save(self, *args, **kwargs):
        instance = self.instance

        if not instance.id:
            super().save(commit=False, *args, **kwargs)
            generate_string_id_and_save(
                ActivitySubType, [instance],
                'creme_config-useractivitydetailesubtype',
            )
        else:
            super().save(*args, **kwargs)

        return instance


# class BulkEditTypeForm(BulkDefaultEditForm):
#     error_messages = {
#         'immutable_indispo': _('The type of an indisponibility cannot be changed.'),
#     }
#
#     def __init__(self, model, field, user, entities, is_bulk=False, **kwargs):
#         super().__init__(model, field, user, entities, is_bulk=is_bulk, **kwargs)
#         self.fields['field_value'] = type_selector = ActivityTypeField(
#             label=_('Type'),
#             types=ActivityType.objects.exclude(pk=ACTIVITYTYPE_INDISPO),
#         )
#         self._mixed_indispo = False
#         indispo_count = sum(a.type_id == ACTIVITYTYPE_INDISPO for a in entities)
#
#         if indispo_count:
#             if indispo_count == len(entities):
#                 # All entities are indisponibilities, so we propose to change the sub-type.
#                 type_selector.types = ActivityType.objects.filter(pk=ACTIVITYTYPE_INDISPO)
#             else:
#                 self._mixed_indispo = True
#                 self.fields['beware'] = core_fields.ReadonlyMessageField(
#                     label=_('Beware !'),
#                     initial=ngettext(
#                         'The type of {count} activity cannot be changed because'
#                         ' it is an indisponibility.',
#                         'The type of {count} activities cannot be changed because'
#                         ' they are indisponibilities.',
#                         indispo_count
#                     ).format(count=indispo_count),
#                 )
#
#         if not is_bulk:
#             first = entities[0]
#             type_selector.initial = (first.type_id, first.sub_type_id)
#
#     def _bulk_clean_entity(self, entity, values):
#         if self._mixed_indispo and entity.type_id == ACTIVITYTYPE_INDISPO:
#             raise ValidationError(
#                 self.error_messages['immutable_indispo'],
#                 code='immutable_indispo',
#             )
#
#         entity.type, entity.sub_type = values.get(self.field_name)
#
#         return entity
class TypeOverrider(FieldOverrider):
    field_names = ['type', 'sub_type']

    error_messages = {
        'immutable': _('The type of an unavailability cannot be changed.'),
    }

    _mixed_unavailability = False

    def formfield(self, instances, user, **kwargs):
        field = ActivityTypeField(
            label=_('Type'),
            types=ActivityType.objects.exclude(pk=ACTIVITYTYPE_INDISPO),
        )
        unavailability_count = sum(a.type_id == ACTIVITYTYPE_INDISPO for a in instances)

        if unavailability_count:
            if unavailability_count == len(instances):
                # All entities are Unavailability, so we propose to change the subtype.
                field.types = ActivityType.objects.filter(pk=ACTIVITYTYPE_INDISPO)
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
            field.initial = first.type_id, first.sub_type_id

        return field

    def post_clean_instance(self, *, instance, value, form):
        if self._mixed_unavailability and instance.type_id == ACTIVITYTYPE_INDISPO:
            raise ValidationError(
                self.error_messages['immutable'],
                code='immutable',
            )

        if value:
            instance.type, instance.sub_type = value
