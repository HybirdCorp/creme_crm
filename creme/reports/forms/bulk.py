################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2024  Hybird
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
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext, pgettext_lazy

from creme.creme_config.forms.fields import CreatorModelChoiceField
from creme.creme_core.core.entity_filter import EF_REGULAR
from creme.creme_core.forms.fields import ReadonlyMessageField
from creme.creme_core.gui.bulk_update import FieldOverrider
from creme.creme_core.models import EntityFilter, FieldsConfig
from creme.reports.constants import EF_REPORTS


class ReportFilterOverrider(FieldOverrider):
    field_names = ['filter']

    error_messages = {
        'different_ctypes': _(
            'Filter field can only be updated when reports '
            'target the same type of entities (e.g: only contacts).'
        ),
        # TODO: factorise?
        'private_filter': _('The filter cannot be changed because it is private.'),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._uneditable_ids = set()
        self._has_same_report_ct = False

    def formfield(self, instances, user, **kwargs):
        assert instances

        first = instances[0]
        model = type(first)
        model_field = model._meta.get_field(self.field_names[0])

        # Use legacy form field because of filtering issues with the EnumeratorChoiceField
        # TODO: Fix it later
        # field = model_field.formfield()
        field = CreatorModelChoiceField(
            queryset=model_field.related_model.objects.all(),
            empty_label=pgettext_lazy('creme_core-filter', 'All'),
            user=user,
            limit_choices_to=model_field.get_limit_choices_to(),
            required=FieldsConfig.objects.get_for_model(model).is_field_required(model_field),
            label=model_field.verbose_name,
            help_text=model_field.help_text
        )

        # TODO: in constructor?
#         field.empty_label = pgettext_lazy('creme_core-filter', 'All')
#         field.required = FieldsConfig.objects.get_for_model(model).is_field_required(model_field)
#         field.user = user

        first_ct = first.ct
        self._has_same_report_ct = all(e.ct == first_ct for e in instances)

        if self._has_same_report_ct:
            field.queryset = EntityFilter.objects.filter_by_user(
                user, types=[EF_REGULAR, EF_REPORTS],
            ).filter(entity_type=first_ct)

            if len(instances) == 1:
                field.initial = first.filter_id

            self._uneditable_ids = uneditable_ids = {
                report.id
                for report in instances
                if report.filter and not report.filter.can_view(user)[0]
            }

            if uneditable_ids:
                length = len(uneditable_ids)

                if length == len(instances):
                    field = ReadonlyMessageField(
                        label=field.label,
                        initial=ngettext(
                            'The filter cannot be changed because it is private.',
                            'The filters cannot be changed because they are private.',
                            length,
                        ),
                    )
                else:
                    field.help_text = ngettext(
                        'Beware! The filter of {count} report cannot be changed '
                        'because it is private.',
                        'Beware! The filters of {count} reports cannot be changed '
                        'because they are private.',
                        length,
                    ).format(count=length)
        else:
            field = ReadonlyMessageField(
                label=field.label,
                initial=_(
                    'Filter field can only be updated when reports target '
                    'the same type of entities (e.g: only contacts).'
                ),
            )

        return field

    def post_clean_instance(self, *, instance, value, form):
        if not self._has_same_report_ct:
            raise ValidationError(
                self.error_messages['different_ctypes'],
                code='different_ctypes',
            )

        if instance.id in self._uneditable_ids:
            raise ValidationError(
                self.error_messages['private_filter'],
                code='private',
            )

        # TODO: default implementation of post_clean_instance()?
        setattr(instance, self.field_names[0], value)
