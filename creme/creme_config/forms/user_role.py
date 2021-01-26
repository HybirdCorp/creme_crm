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

# import warnings
from collections import OrderedDict
from typing import Tuple

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext

from creme.creme_core.apps import (
    CremeAppConfig,
    creme_app_configs,
    extended_app_configs,
)
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core import deletion
from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    condition_handler,
    entity_filter_registries,
)
from creme.creme_core.creme_jobs import deletor_type
from creme.creme_core.forms import (  # CremeForm
    CremeModelForm,
    FieldBlockManager,
    MultiEntityCTypeChoiceField,
)
from creme.creme_core.forms import widgets as creme_widgets
from creme.creme_core.models import (
    CremeEntity,
    CremeUser,
    DeletionCommand,
    EntityFilter,
    Job,
    SetCredentials,
    UserRole,
)
from creme.creme_core.registry import creme_registry
from creme.creme_core.utils import update_model_instance
from creme.creme_core.utils.id_generator import generate_string_id_and_save
from creme.creme_core.utils.unicode_collation import collator


# TODO: move to creme_core.utils ?? (improve iter_entity_models() ?)
def filtered_entity_ctypes(app_labels):
    ext_app_labels = {app_config.label for app_config in extended_app_configs(app_labels)}
    get_ct = ContentType.objects.get_for_model

    for model in creme_registry.iter_entity_models():
        if model._meta.app_label in ext_app_labels:
            yield get_ct(model)


class CredentialsGeneralStep(CremeModelForm):
    can_view   = forms.BooleanField(label=_('View'),   required=False)
    can_change = forms.BooleanField(label=_('Change'), required=False)
    can_delete = forms.BooleanField(label=_('Delete'), required=False)

    can_link = forms.BooleanField(
        label=_('Link'), required=False,
        help_text=_(
            "You must have the permission to link on 2 entities "
            "to create a relationship between them. "
            "Beware: if you use «Filtered entities», you won't "
            "be able to add relationships in the creation forms "
            "(you'll have to add them later).",
        ),
    )
    can_unlink = forms.BooleanField(
        label=_('Unlink'), required=False,
        help_text=_(
            'You must have the permission to unlink on '
            '2 entities to delete a relationship between them.'
        ),
    )

    # Field name => permission
    PERM_FIELDS = OrderedDict([
        ('can_view',    EntityCredentials.VIEW),
        ('can_change',  EntityCredentials.CHANGE),
        ('can_delete',  EntityCredentials.DELETE),
        ('can_link',    EntityCredentials.LINK),
        ('can_unlink',  EntityCredentials.UNLINK),
    ])

    blocks = FieldBlockManager(
        {
            'id': 'general',
            'label': _('General information'),
            'fields': '*',
        }, {
            'id': 'actions',
            'label': _('Actions'),
            'fields': [*PERM_FIELDS.keys()],
        },
    )

    class Meta:
        model = SetCredentials
        exclude = ('value', )  # fields ??
        widgets = {
            'set_type':  creme_widgets.CremeRadioSelect,
            # TODO: always this widget for CTypeForeignKey ??
            'ctype':     creme_widgets.DynamicSelect(attrs={'autocomplete': True}),
            'forbidden': creme_widgets.CremeRadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = self.fields

        ctype_f = fields['ctype']
        ctype_f.empty_label = pgettext('content_type', 'None')
        ctype_f.ctypes = filtered_entity_ctypes(self._get_allowed_apps())

        # TODO: SetCredentials.value default to 0
        value = self.instance.value or 0
        for fname, perm in self.PERM_FIELDS.items():
            fields[fname].initial = bool(value & perm)

    def clean(self, *args, **kwargs):
        cdata = super().clean(*args, **kwargs)

        if not self._errors:
            get = cdata.get

            if not any(get(fname) for fname in self.PERM_FIELDS.keys()):
                raise ValidationError(gettext('No action has been selected.'))

        return cdata

    def _get_allowed_apps(self):
        return self.instance.role.allowed_apps

    def save(self, *args, **kwargs):
        get_data = self.cleaned_data.get
        self.instance.set_value(
            **{fname: get_data(fname) for fname in self.PERM_FIELDS.keys()}
        )


class CredentialsFilterStep(CremeModelForm):
    name = EntityFilter._meta.get_field('name').formfield(label=_('Name of the filter'))
    use_or = EntityFilter._meta.get_field('use_or').formfield(
        widget=creme_widgets.CremeRadioSelect,
    )

    class Meta:
        model = SetCredentials
        fields = ()

    error_messages = {
        'no_condition': _('The filter must have at least one condition.'),
    }

    blocks = FieldBlockManager(
        {
            'id': 'general',
            'label': _('Filter'),
            'fields': ('name', 'use_or'),
        }, {
            'id': 'conditions',
            'label': _('Conditions'),
            'fields': '*',
        },
    )

    step_help_message = _(
        'Beware to performances with conditions on custom fields or relationships.'
    )

    # TODO: API for this in handlers ??
    no_entity_base_handlers = (
        condition_handler.CustomFieldConditionHandler,
        condition_handler.DateCustomFieldConditionHandler,
    )

    def __init__(self, efilter_type=EF_CREDENTIALS, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = self.fields
        self.efilter_type = efilter_type
        self.conditions_field_names = fnames = []
        instance = self.instance

        if instance.set_type == SetCredentials.ESET_FILTER:
            efilter_registry = entity_filter_registries[efilter_type]
            ctype = instance.ctype

            if ctype is None:
                ctype = ContentType.objects.get_for_model(CremeEntity)
                handler_classes = (
                    cls
                    for cls in efilter_registry.handler_classes
                    if not issubclass(cls, self.no_entity_base_handlers)
                )
            else:
                handler_classes = efilter_registry.handler_classes

            efilter = instance.efilter

            # NB: some explanations :
            #  - if the entity class related to the filter, we keep the current filter as initial.
            #  - if we pass from a Contact filter to an Organisation filter (for example),
            #     we do not use current filter as initial.
            #  - if we pass from a CremeEntity filter to an Organisation filter (for example),
            #    we keep the current filter as initial (the fields use are still valid).
            if efilter and issubclass(ctype.model_class(), efilter.entity_type.model_class()):
                fields['name'].initial = efilter.name
                fields['use_or'].initial = efilter.use_or

                f_init_args = (ctype, efilter.conditions.all(), efilter)
            else:
                f_init_args = (ctype,)

            f_kwargs = {
                'user': self.user,
                'required': False,
                'efilter_registry': efilter_registry,
                'efilter_type': efilter_type,
            }
            handler_fieldname = self._handler_fieldname
            for handler_cls in handler_classes:
                fname = handler_fieldname(handler_cls)

                field = handler_cls.formfield(**f_kwargs)
                field.initialize(*f_init_args)

                fields[fname] = field
                fnames.append(fname)
        else:
            fields.clear()
            fields['no_filter_label'] = forms.CharField(
                label=_('Conditions'),
                required=False, widget=creme_widgets.Label,
                initial=_('No filter, no condition.'),
            )

    def clean(self):
        cdata = super().clean()

        if not self._errors:
            fnames = self.conditions_field_names

            if fnames and not any(cdata[f] for f in fnames):
                raise ValidationError(
                    self.error_messages['no_condition'], code='no_condition',
                )

        return cdata

    def get_cleaned_conditions(self):
        cdata = self.cleaned_data
        conditions = []

        for fname in self.conditions_field_names:
            conditions.extend(cdata[fname])

        return conditions

    def _handler_fieldname(self, handler_cls):
        return handler_cls.__name__.lower().replace('handler', '')

    def save(self, *args, **kwargs):
        instance = self.instance
        conditions = self.get_cleaned_conditions()
        efilter = instance.efilter

        if conditions:
            role = instance.role
            cdata = self.cleaned_data
            name = cdata['name']
            use_or = cdata['use_or']
            ctype = instance.ctype or ContentType.objects.get_for_model(CremeEntity)

            if efilter is None:
                efilter = EntityFilter(
                    name=name,
                    entity_type=ctype,
                    filter_type=self.efilter_type,
                    use_or=use_or,
                )
                generate_string_id_and_save(
                    EntityFilter, [efilter],
                    f'creme_core-credentials_{role.id}-',
                )
                instance.efilter = efilter
            else:
                update_model_instance(
                    efilter,
                    entity_type=ctype,
                    name=name,
                    use_or=use_or,
                )

            efilter.set_conditions(
                conditions,
                check_cycles=False,   # There cannot be a cycle without sub-filter.
                check_privacy=False,  # No sense here.
            )
            super().save(*args, **kwargs)
        elif efilter:
            instance.efilter = None
            super().save(*args, **kwargs)
            efilter.delete()
        else:
            super().save(*args, **kwargs)

        return instance


# class UserRoleDeleteForm(CremeForm):
#     def __init__(self, user, instance, *args, **kwargs):
#         warnings.warn('UserRoleDeleteForm is deprecated ; '
#                       'use UserRoleDeletionForm instead.',
#                       DeprecationWarning
#                      )
#
#         super().__init__(user, *args, **kwargs)
#         self.role_to_delete = instance
#         self.using_users = users = CremeUser.objects.filter(role=instance)
#
#         if users:
#             self.fields['to_role'] = forms.ModelChoiceField(
#                 label=gettext('Choose a role to transfer to'),
#                 queryset=UserRole.objects.exclude(id=instance.id),
#             )
#         else:
#             self.fields['info'] = forms.CharField(
#                 label=gettext('Information'), required=False,
#                 widget=creme_widgets.Label,
#                 initial=gettext('This role is not used by any user,'
#                                 ' you can delete it safely.'
#                                ),
#             )
#
#     def save(self, *args, **kwargs):
#         to_role = self.cleaned_data.get('to_role')
#
#         if to_role is not None:
#             self.using_users.update(role=to_role)
#
#         self.role_to_delete.delete()


class UserRoleDeletionForm(CremeModelForm):
    class Meta:
        model = DeletionCommand
        fields = ()

    def __init__(self, role_to_delete, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role_to_delete = role_to_delete

        if CremeUser.objects.filter(role=role_to_delete).exists():
            self.fields['to_role'] = forms.ModelChoiceField(
                label=_('Choose a role to transfer to'),
                help_text=_(
                    'The chosen role will replace the deleted one in users which use it.'
                ),
                queryset=UserRole.objects.exclude(id=role_to_delete.id),
            )
        else:
            self.fields['info'] = forms.CharField(
                label=gettext('Information'), required=False,
                widget=creme_widgets.Label,
                initial=gettext(
                    'This role is not used by any user, you can delete it safely.'
                ),
            )

    def save(self, *args, **kwargs):
        instance = self.instance
        instance.instance_to_delete = self.role_to_delete

        # TODO: check other FK ?
        replacement = self.cleaned_data.get('to_role')
        if replacement:
            instance.replacers = [
                deletion.FixedValueReplacer(
                    model_field=CremeUser._meta.get_field('role'),
                    value=replacement,
                )
            ]
        instance.total_count = CremeUser.objects.filter(role=self.role_to_delete).count()
        instance.job = Job.objects.create(
            type_id=deletor_type.id,
            user=self.user,
        )

        return super().save(*args, **kwargs)


# Wizard steps -----------------------------------------------------------------

class _UserRoleWizardFormStep(CremeModelForm):
    class Meta:
        model = UserRole
        fields: Tuple[str, ...] = ()

    @staticmethod
    def app_choices(apps):
        sort_key = collator.sort_key

        return sorted(
            ((app.label, str(app.verbose_name)) for app in apps),
            key=lambda t: sort_key(t[1])
        )

    def save(self, commit=False, *args, **kwargs):
        return super().save(*args, **kwargs) if commit else self.instance


class UserRoleAppsStep(_UserRoleWizardFormStep):
    allowed_apps = forms.MultipleChoiceField(label=_('Allowed applications'), choices=())

    class Meta(_UserRoleWizardFormStep.Meta):
        fields = ('name', 'allowed_apps',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        CRED_REGULAR = CremeAppConfig.CRED_REGULAR
        allowed_apps_f = self.fields['allowed_apps']
        allowed_apps_f.choices = self.app_choices(
            app for app in creme_app_configs() if app.credentials & CRED_REGULAR
        )
        allowed_apps_f.initial = self.instance.allowed_apps

    def clean(self):
        cdata = super().clean()

        if not self._errors:
            self.instance.allowed_apps = self.cleaned_data['allowed_apps']

        return cdata


class UserRoleAdminAppsStep(_UserRoleWizardFormStep):
    admin_4_apps = forms.MultipleChoiceField(
        required=False, choices=(),
        label=_('Administrated applications'),
        help_text=_(
            'These applications can be configured. '
            'For example, the concerned users can create new choices '
            'available in forms (eg: position for contacts).'
        ),
    )

    class Meta(_UserRoleWizardFormStep.Meta):
        fields = ('admin_4_apps',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        CRED_ADMIN = CremeAppConfig.CRED_ADMIN
        labels = self.instance.allowed_apps
        admin_4_apps_f = self.fields['admin_4_apps']
        admin_4_apps_f.choices = self.app_choices(
            app
            for app in creme_app_configs()
            if app.label in labels and app.credentials & CRED_ADMIN
        )
        admin_4_apps_f.initial = self.instance.admin_4_apps

    def clean(self):
        cdata = super().clean()

        if not self._errors:
            self.instance.admin_4_apps = self.cleaned_data['admin_4_apps']

        return cdata

    def save(self, commit=True, *args, **kwargs):
        return super().save(commit=commit, *args, **kwargs)


class UserRoleCreatableCTypesStep(_UserRoleWizardFormStep):
    creatable_ctypes = MultiEntityCTypeChoiceField(
        label=_('Creatable resources'), required=False,
    )

    class Meta(_UserRoleWizardFormStep.Meta):
        fields = ('creatable_ctypes',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['creatable_ctypes'].ctypes = filtered_entity_ctypes(
            self.instance.allowed_apps,
        )

    def save(self, commit=True, *args, **kwargs):
        instance = self.instance

        if commit:
            # Optimisation: we only save the M2M
            instance.creatable_ctypes.set(self.cleaned_data['creatable_ctypes'])

        return instance


class UserRoleExportableCTypesStep(_UserRoleWizardFormStep):
    exportable_ctypes = MultiEntityCTypeChoiceField(
        label=_('Exportable resources'), required=False,
        help_text=_(
            'This types of entities can be downloaded as CSV/XLS '
            'files (in the corresponding list-views).'
        ),
    )

    class Meta(_UserRoleWizardFormStep.Meta):
        fields = ('exportable_ctypes',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['exportable_ctypes'].ctypes = filtered_entity_ctypes(
            self.instance.allowed_apps,
        )

    def save(self, commit=True, *args, **kwargs):
        instance = self.instance

        if commit:
            # Optimisation: we only save the M2M
            instance.exportable_ctypes.set(self.cleaned_data['exportable_ctypes'])

        return instance


class UserRoleCredentialsGeneralStep(CredentialsGeneralStep):
    blocks = FieldBlockManager(
        {
            'id': 'general',
            'label': _('First credentials: main information'),
            'fields': '*',
        }, {
            'id': 'actions',
            'label': _('First credentials: actions'),
            'fields': [
                'can_view', 'can_change', 'can_delete', 'can_link', 'can_unlink',
            ],
        },
    )

    def __init__(self, role, *args, **kwargs):
        self.role = role
        super().__init__(*args, **kwargs)
        fields = self.fields
        fields['can_view'] = forms.CharField(
            label=fields['can_view'].label,
            required=False,
            widget=creme_widgets.Label,
            initial=_('Yes'),
        )

    def clean_can_view(self):
        return True

    def _get_allowed_apps(self):
        return self.role.allowed_apps

    def save(self, commit=False, *args, **kwargs):
        self.instance.role = self.role
        return super().save(commit=commit, *args, **kwargs)


class UserRoleCredentialsFilterStep(CredentialsFilterStep):
    blocks = FieldBlockManager(
        {
            'id': 'general',
            'label': _('First credentials: filter'),
            'fields': ('name', 'use_or'),
        }, {
            'id': 'conditions',
            'label': _('First credentials: conditions'),
            'fields': '*',
        },
    )

    def __init__(self, role, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = role  # NB: not currently used, but facilitate extending
