################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2010-2025  Hybird
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

from collections import Counter
from functools import partial

from django import forms
from django.core.exceptions import ValidationError
from django.forms.widgets import Textarea
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

import creme.creme_core.forms.fields as core_fields
from creme.creme_core.core.deletion import FixedValueReplacer
from creme.creme_core.creme_jobs import deletor_type
from creme.creme_core.forms import CremeModelForm
from creme.creme_core.forms.widgets import DynamicSelect
from creme.creme_core.models import DeletionCommand, Job
from creme.creme_core.models.custom_field import (
    _TABLES,
    CustomField,
    CustomFieldEnumValue,
)

# TODO: User friendly order in choices fields


class CustomFieldBaseForm(CremeModelForm):
    field_type = forms.TypedChoiceField(
        label=_('Type of field'), coerce=int,
        choices=[(i, klass.verbose_name) for i, klass in _TABLES.items()],
    )
    enum_values = forms.CharField(
        widget=Textarea(),
        label=_('Available choices'),
        required=False,
        help_text=_(
            'Give the possible choices (one per line) '
            'if you choose the type "Choice list".'
        ),
    )

    error_messages = {
        'empty_list': _(
            'The choices list must not be empty '
            'if you choose the type "Choice list".'
        ),
        'duplicated_choice': _('The choice «{}» is duplicated.'),
    }

    class Meta(CremeModelForm.Meta):
        model = CustomField

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._choices = ()

    def clean(self):
        cdata = super().clean()

        if cdata.get('field_type') in (CustomField.ENUM, CustomField.MULTI_ENUM):
            str_choices = cdata['enum_values'].strip()

            if not str_choices:
                raise ValidationError(
                    self.error_messages['empty_list'], code='empty_list',
                )

            choices = str_choices.splitlines()

            max_choice, max_count = Counter(choices).most_common(1)[0]
            if max_count > 1:
                self.add_error(
                    'enum_values',
                    self.error_messages['duplicated_choice'].format(max_choice),
                )

            self._choices = choices

        return cdata

    def save(self):
        instance = super().save()
        choices = self._choices

        if choices:
            create_enum_value = partial(
                CustomFieldEnumValue.objects.create, custom_field=instance,
            )

            for enum_value in choices:
                create_enum_value(value=enum_value)

        return instance


class FirstCustomFieldCreationForm(CustomFieldBaseForm):
    content_type = core_fields.EntityCTypeChoiceField(
        label=_('Related resource'),
        help_text=_(
            'The other custom fields for this type of resource will be chosen '
            'by editing the configuration'
        ),
        widget=DynamicSelect({'autocomplete': True}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        used_ct_ids = {
            *CustomField.objects
                        .exclude(is_deleted=True)
                        .values_list('content_type_id', flat=True)
        }
        ct_field = self.fields['content_type']
        ct_field.ctypes = (ct for ct in ct_field.ctypes if ct.id not in used_ct_ids)


class CustomFieldCreationForm(CustomFieldBaseForm):
    error_messages = {
        **CustomFieldBaseForm.error_messages,
        'duplicated_name': _('There is already a custom field with this name.'),
    }

    class Meta(CustomFieldBaseForm.Meta):
        exclude = ('content_type',)

    def __init__(self, ctype, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ct = ctype

    def clean_name(self):
        name = self.cleaned_data['name']

        if CustomField.objects.filter(content_type=self.ct, name=name).exists():
            raise ValidationError(
                self.error_messages['duplicated_name'], code='duplicated_name',
            )

        return name

    def save(self):
        self.instance.content_type = self.ct
        return super().save()


class CustomFieldEditionForm(CremeModelForm):
    # TODO: factorise
    error_messages = {
        'duplicated_name': _('There is already a custom field with this name.'),
    }

    class Meta:
        model = CustomField
        fields = ('name', 'is_required', 'description')

    def clean_name(self):
        name = self.cleaned_data['name']
        instance = self.instance

        if CustomField.objects.filter(content_type=instance.content_type, name=name)\
                              .exclude(id=instance.id)\
                              .exists():
            raise ValidationError(
                self.error_messages['duplicated_name'], code='duplicated_name',
            )

        return name


class BaseCustomEnumAddingForm(CremeModelForm):
    # TODO: factorise
    error_messages = {
        'duplicated_choice': _('The choice «{}» is duplicated.'),
    }

    class Meta:
        model = CustomField
        fields = ()

    def raise_duplicated_choice(self, choice):
        raise ValidationError(
            self.error_messages['duplicated_choice'].format(choice),
            code='duplicated_choice',
        )


class CustomEnumAddingForm(BaseCustomEnumAddingForm):
    choice = forms.CharField(label=gettext('New choice'))

    def clean_choice(self):
        choice = self.cleaned_data['choice']

        if CustomFieldEnumValue.objects.filter(
            custom_field=self.instance,
            value=choice,
        ).exists():
            self.raise_duplicated_choice(choice)

        return choice

    def save(self):
        # cfield = super().save()  NOPE
        enum_value = CustomFieldEnumValue.objects.create(
            custom_field=self.instance,
            value=self.cleaned_data['choice'],
        )

        return enum_value


class CustomEnumsAddingForm(BaseCustomEnumAddingForm):
    choices = forms.CharField(
        widget=Textarea(),
        label=gettext('New choices of the list'),
        help_text=gettext('Give the new possible choices (one per line).'),
    )

    def clean_choices(self):
        choices = self.cleaned_data['choices'].splitlines()

        # TODO: factorise ??
        max_choice, max_count = Counter(choices).most_common(1)[0]
        if max_count > 1:
            self.raise_duplicated_choice(max_choice)

        existing = CustomFieldEnumValue.objects.filter(
            custom_field=self.instance,
            value__in=choices,
        ).first()
        if existing:
            self.raise_duplicated_choice(existing)

        return choices

    def save(self):
        # cfield = super().save()  NOPE
        cfield = self.instance

        create_enum_value = partial(
            CustomFieldEnumValue.objects.create,
            custom_field=cfield,
        )

        for enum_value in self.cleaned_data['choices']:
            create_enum_value(value=enum_value)

        return cfield


class CustomEnumEditionForm(CremeModelForm):
    class Meta:
        model = CustomFieldEnumValue
        fields = ('value', )


class CustomEnumDeletionForm(CremeModelForm):
    class Meta:
        model = DeletionCommand
        fields = ()

    def __init__(self, choice_to_delete, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choice_to_delete = choice_to_delete

        if choice_to_delete.custom_field.value_class.objects.filter(
            value=choice_to_delete
        ).exists():
            self.fields['to_choice'] = forms.ModelChoiceField(
                label=_('Choose a choice to transfer to'),
                help_text=_(
                    'The selected choice will replace the deleted one '
                    'in entities which use it.'
                ),
                required=False,
                queryset=CustomFieldEnumValue.objects.filter(
                    custom_field=choice_to_delete.custom_field,
                ).exclude(id=choice_to_delete.id),
            )
        else:
            self.fields['info'] = core_fields.ReadonlyMessageField(
                label=_('Information'),
                initial=gettext(
                    'This choice is not used by any entity, you can delete it safely.'
                ),
            )

    def save(self, *args, **kwargs):
        instance = self.instance
        instance.instance_to_delete = choice_to_delete = self.choice_to_delete
        cf_value_model = choice_to_delete.custom_field.value_class

        replacement = self.cleaned_data.get('to_choice')
        if replacement:
            instance.replacers = [
                FixedValueReplacer(
                    model_field=cf_value_model._meta.get_field('value'),
                    value=replacement,
                )
            ]
        instance.total_count = cf_value_model.objects.filter(
            value=choice_to_delete,
        ).count()
        instance.job = Job.objects.create(
            type_id=deletor_type.id,
            user=self.user,
        )

        return super().save(*args, **kwargs)
