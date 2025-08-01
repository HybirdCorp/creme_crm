################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import EntityFilter, SettingValue
from creme.creme_core.setting_keys import global_filters_edition_key
from creme.creme_core.utils.id_generator import generate_string_id_and_save

from ..base import CremeModelForm, FieldBlockManager
from ..widgets import CremeRadioSelect


class _EntityFilterForm(CremeModelForm):
    error_messages = {
        'no_condition':    _('The filter must have at least one condition.'),
        'foreign_private': _('A private filter must belong to you (or one of your teams).')
    }

    blocks = FieldBlockManager(
        {
            'id': 'general',
            'label': _('General information'),
            'fields': ('name', 'user', 'is_private', 'use_or'),
        }, {
            'id': 'conditions',
            'label': _('Conditions'),
            'fields': '*',
        },
    )

    class Meta(CremeModelForm.Meta):
        model = EntityFilter
        widgets = {
            'use_or': CremeRadioSelect,
        }

    def __init__(self, efilter_registry, *args, **kwargs):
        """Constructor.

        @param efilter_registry: Instance of <creme_core.core.entity_filter._EntityFilterRegistry>
        """
        super().__init__(*args, **kwargs)
        self.instance.filter_type = efilter_registry.id
        fields = self.fields

        user_f = fields['user']
        user_f.empty_label = _('No owner')
        user_f.help_text = _(
            'If you assign an owner, only the owner can edit or delete the filter; '
            'filters without owner can be edited/deleted by all users'
        ) if SettingValue.objects.get_4_key(global_filters_edition_key).value else _(
            'If you assign an owner, only the owner can edit or delete the filter; '
            'filters without owner can only be edited/deleted by superusers'
        )

        self.conditions_field_names = fnames = []
        f_kwargs = {
            'user': self.user,
            'required': False,
            'efilter_type': efilter_registry.id,
        }
        for handler_cls in efilter_registry.handler_classes:
            fname = self._handler_fieldname(handler_cls)
            fields[fname] = handler_cls.formfield(**f_kwargs)
            fnames.append(fname)

    def _handler_fieldname(self, handler_cls):
        return handler_cls.__name__.lower().replace('handler', '')

    def get_cleaned_conditions(self):
        cdata = self.cleaned_data
        conditions = []

        for fname in self.conditions_field_names:
            conditions.extend(cdata[fname])

        return conditions

    def clean(self):
        cdata = super().clean()

        if not self._errors:
            if not any(cdata[f] for f in self.conditions_field_names):
                raise ValidationError(
                    self.error_messages['no_condition'], code='no_condition',
                )

            is_private = cdata.get('is_private', False)
            owner      = cdata.get('user')
            req_user   = self.user

            if not req_user.is_staff and is_private and owner:
                if owner.is_team:
                    if req_user.id not in owner.teammates:
                        self.add_error('user', self.error_messages['foreign_private'])
                elif owner != req_user:
                    self.add_error('user', self.error_messages['foreign_private'])

            try:
                self.instance.check_privacy(self.get_cleaned_conditions(), is_private, owner)
            except EntityFilter.PrivacyError as e:
                raise ValidationError(e) from e

        return cdata


class EntityFilterCreationForm(_EntityFilterForm):
    pk_prefix = 'creme_core-userfilter_'

    def __init__(self, ctype, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._entity_type = self.instance.entity_type = ctype
        fields = self.fields

        for field_name in self.conditions_field_names:
            fields[field_name].initialize(ctype)

    def save(self, *args, **kwargs):
        instance = self.instance
        ct = self._entity_type

        super().save(commit=False, *args, **kwargs)
        generate_string_id_and_save(
            EntityFilter, [instance],
            f'{self.pk_prefix}{ct.app_label}-{ct.model}-',
        )

        instance.set_conditions(
            self.get_cleaned_conditions(),
            # There cannot be a cycle because we are creating the filter right now
            check_cycles=False,
            check_privacy=False,  # Already checked in clean()
        )

        return instance


# TODO: factorise
class EntityFilterCloningForm(_EntityFilterForm):
    pk_prefix = 'creme_core-userfilter_'

    def __init__(self, source: EntityFilter, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ctype = source.entity_type
        self._entity_type = self.instance.entity_type = ctype
        fields = self.fields

        fields['is_private'].initial = True
        # fields['name'].initial = _('Clone of ...') TODO?

        field_kwargs = {
            'ctype': ctype,
            'conditions': source.conditions.all(),
            'efilter': None,
        }

        for field_name in self.conditions_field_names:
            fields[field_name].initialize(**field_kwargs)

    def save(self, *args, **kwargs):
        instance = self.instance
        ct = self._entity_type

        super().save(commit=False, *args, **kwargs)
        generate_string_id_and_save(
            EntityFilter, [instance],
            f'{self.pk_prefix}{ct.app_label}-{ct.model}-',
        )

        instance.set_conditions(
            self.get_cleaned_conditions(),
            # There cannot be a cycle because we are creating the filter right now
            check_cycles=False,
            check_privacy=False,  # Already checked in clean()
        )

        return instance


class EntityFilterEditionForm(_EntityFilterForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        fields = self.fields
        instance = self.instance
        args = (instance.entity_type, instance.conditions.all(), instance)

        for field_name in self.conditions_field_names:
            fields[field_name].initialize(*args)

        if not instance.is_custom:
            del fields['name']
            del fields['is_private']

    def clean(self):
        cdata = super().clean()

        if not self.errors:
            conditions = self.get_cleaned_conditions()

            try:
                self.instance.check_cycle(conditions)
            except EntityFilter.CycleError as e:
                raise ValidationError(e) from e

            cdata['all_conditions'] = conditions

        return cdata

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        instance.set_conditions(
            self.cleaned_data['all_conditions'],
            check_cycles=False, check_privacy=False,  # Already checked in clean()
        )

        return instance
