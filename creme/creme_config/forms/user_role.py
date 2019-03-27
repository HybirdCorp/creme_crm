# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.forms import CharField, ChoiceField, BooleanField, MultipleChoiceField, ModelChoiceField
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext

from creme.creme_core.apps import creme_app_configs, extended_app_configs, CremeAppConfig
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.forms import (CremeForm, CremeModelForm, FieldBlockManager,
        EntityCTypeChoiceField, MultiEntityCTypeChoiceField)
from creme.creme_core.forms.widgets import Label, DynamicSelect, CremeRadioSelect
from creme.creme_core.models import CremeUser, UserRole, SetCredentials  # Mutex
from creme.creme_core.registry import creme_registry
from creme.creme_core.utils.unicode_collation import collator


def filtered_entity_ctypes(app_labels):  # TODO: move to creme_core.utils ??
    ext_app_labels = {app_config.label for app_config in extended_app_configs(app_labels)}
    get_ct = ContentType.objects.get_for_model

    for model in creme_registry.iter_entity_models():
        if model._meta.app_label in ext_app_labels:
            yield get_ct(model)


# def EmptyMultipleChoiceField(required=False, *args, **kwargs):
#     return MultipleChoiceField(required=required, choices=(), *args, **kwargs)


class EditCredentialsForm(CremeModelForm):
    can_view   = BooleanField(label=_('Can view'),   required=False)
    can_change = BooleanField(label=_('Can change'), required=False)
    can_delete = BooleanField(label=_('Can delete'), required=False)
    can_link   = BooleanField(label=_('Can link'),   required=False,
                              help_text=_('You must have the permission to link on 2 entities'
                                          ' to create a relationship between them.'
                                         ),
                             )
    can_unlink = BooleanField(label=_('Can unlink'), required=False,
                              help_text=_('You must have the permission to unlink on 2 entities'
                                          ' to delete a relationship between them.'
                                         ),
                             )
    set_type   = ChoiceField(label=_('Type of entities set'),
                             choices=SetCredentials.ESETS_MAP.items(),
                             widget=CremeRadioSelect,
                            )
    ctype      = EntityCTypeChoiceField(label=_('Apply to a specific type'),
                                        widget=DynamicSelect(attrs={'autocomplete': True}),
                                        required=False,
                                        empty_label=pgettext('content_type', 'None'),
                                       )

    class Meta:
        model = SetCredentials
        exclude = ('role', 'value')  # fields ??

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = self.fields
        fields['ctype'].ctypes = filtered_entity_ctypes(self._get_allowed_apps())

        # TODO: SetCredentials.value default to 0
        value = self.instance.value or 0
        fields['can_view'].initial   = bool(value & EntityCredentials.VIEW)
        fields['can_change'].initial = bool(value & EntityCredentials.CHANGE)
        fields['can_delete'].initial = bool(value & EntityCredentials.DELETE)
        fields['can_link'].initial   = bool(value & EntityCredentials.LINK)
        fields['can_unlink'].initial = bool(value & EntityCredentials.UNLINK)

    def _get_allowed_apps(self):
        return self.instance.role.allowed_apps

    def save(self, *args, **kwargs):
        get_data = self.cleaned_data.get

        self.instance.set_value(get_data('can_view'), get_data('can_change'), get_data('can_delete'),
                                get_data('can_link'), get_data('can_unlink')
                               )

        return super().save(*args, **kwargs)


class AddCredentialsForm(EditCredentialsForm):
    def __init__(self, instance, *args, **kwargs):
        self.role = instance
        super().__init__(*args, **kwargs)
        self.fields['set_type'].initial = SetCredentials.ESET_ALL

    def _get_allowed_apps(self):
        return self.role.allowed_apps

    def save(self, *args, **kwargs):
        self.instance.role = self.role

        return super().save(*args, **kwargs)


class UserRoleDeleteForm(CremeForm):
    def __init__(self, user, instance, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.role_to_delete = instance
        self.using_users = users = CremeUser.objects.filter(role=instance)

        if users:
            self.fields['to_role'] = ModelChoiceField(label=ugettext('Choose a role to transfer to'),
                                                      queryset=UserRole.objects.exclude(id=instance.id),
                                                     )
        else:
            self.fields['info'] = CharField(label=ugettext('Information'), required=False, widget=Label,
                                            initial=ugettext('This role is not used by any user,'
                                                             ' you can delete it safely.'
                                                            ),
                                           )

    def save(self, *args, **kwargs):
        to_role = self.cleaned_data.get('to_role')

        if to_role is not None:
            self.using_users.update(role=to_role)

        self.role_to_delete.delete()


# Wizard steps -----------------------------------------------------------------

class _UserRoleWizardFormStep(CremeModelForm):
    class Meta:
        model = UserRole
        fields = ()

    @staticmethod
    def app_choices(apps):
        sort_key = collator.sort_key

        return sorted(((app.label, str(app.verbose_name)) for app in apps),
                          key=lambda t: sort_key(t[1])
                     )

    def partial_save(self):
        pass

    def save(self, *args, **kwargs):
        self.partial_save()

        return super().save(*args, **kwargs)


class UserRoleAppsStep(_UserRoleWizardFormStep):
    allowed_apps = MultipleChoiceField(label=_('Allowed applications'), choices=())

    class Meta(_UserRoleWizardFormStep.Meta):
        fields = ('name', 'allowed_apps',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        CRED_REGULAR = CremeAppConfig.CRED_REGULAR
        allowed_apps_f = self.fields['allowed_apps']
        allowed_apps_f.choices = self.app_choices(app for app in creme_app_configs()
                                                       if app.credentials & CRED_REGULAR
                                                 )
        allowed_apps_f.initial = self.instance.allowed_apps

    def partial_save(self):
        self.instance.allowed_apps = self.cleaned_data['allowed_apps']


class UserRoleAdminAppsStep(_UserRoleWizardFormStep):
    # admin_4_apps = EmptyMultipleChoiceField(label=_('Administrated applications'),
    #                                         help_text=_('These applications can be configured. '
    #                                                     'For example, the concerned users can create new choices '
    #                                                     'available in forms (eg: position for contacts).'
    #                                                    )
    #                                        )
    admin_4_apps = MultipleChoiceField(
                        required=False, choices=(),
                        label=_('Administrated applications'),
                        help_text=_('These applications can be configured. '
                                    'For example, the concerned users can create new choices '
                                    'available in forms (eg: position for contacts).'
                                   )
                   )

    class Meta(_UserRoleWizardFormStep.Meta):
        fields = ('admin_4_apps',)

    def __init__(self, allowed_app_names, *args, **kwargs):
        super().__init__(*args, **kwargs)

        CRED_ADMIN = CremeAppConfig.CRED_ADMIN
        labels = set(allowed_app_names)
        admin_4_apps_f = self.fields['admin_4_apps']
        admin_4_apps_f.choices = self.app_choices(app for app in creme_app_configs()
                                                        if app.label in labels and
                                                           app.credentials & CRED_ADMIN
                                                 )
        admin_4_apps_f.initial = self.instance.admin_4_apps

    def partial_save(self):
        self.instance.admin_4_apps = self.cleaned_data['admin_4_apps']


class UserRoleCreatableCTypesStep(_UserRoleWizardFormStep):
    creatable_ctypes = MultiEntityCTypeChoiceField(label=_('Creatable resources'), required=False)

    class Meta(_UserRoleWizardFormStep.Meta):
        fields = ('creatable_ctypes',)

    def __init__(self, allowed_app_names, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['creatable_ctypes'].ctypes = filtered_entity_ctypes(allowed_app_names)

    def save(self, *args, **kwargs):
        # Optimisation: we only save the M2M
        self.instance.creatable_ctypes.set(self.cleaned_data['creatable_ctypes'])


class UserRoleExportableCTypesStep(_UserRoleWizardFormStep):
    exportable_ctypes = MultiEntityCTypeChoiceField(label=_('Exportable resources'), required=False,
                                                    help_text=_('This types of entities can be downloaded as CSV/XLS '
                                                                'files (in the corresponding list-views).'
                                                               )
                                                   )

    class Meta(_UserRoleWizardFormStep.Meta):
        fields = ('exportable_ctypes',)

    def __init__(self, allowed_app_names, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['exportable_ctypes'].ctypes = filtered_entity_ctypes(allowed_app_names)

    def save(self, *args, **kwargs):
        # Optimisation: we only save the M2M
        self.instance.exportable_ctypes.set(self.cleaned_data['exportable_ctypes'])


class UserRoleCredentialsStep(AddCredentialsForm):
    blocks = FieldBlockManager(('general', _('First credentials'), '*'))

    def __init__(self, allowed_app_names, *args, **kwargs):
        self.allowed_app_names = allowed_app_names
        super().__init__(*args, **kwargs)
        self.fields['can_view'] = CharField(label=_('Can view'),
                                            required=False, widget=Label,
                                            initial=_('Yes'),
                                           )

    def _get_allowed_apps(self):
        return self.allowed_app_names

    def clean_can_view(self):
        return True
