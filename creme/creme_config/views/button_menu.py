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

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import ButtonMenuItem, UserRole
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from ..bricks import ButtonMenuBrick
from ..forms import button_menu as button_forms
from . import base


class Portal(base.ConfigPortal):
    template_name = 'creme_config/portals/button-menu.html'
    brick_classes = [ButtonMenuBrick]


class RoleRelatedMixin:
    role_id_kwarg = 'role_id'
    check_role_configuration = True
    _role = None

    def get_related_role(self):
        role = self._role

        if role is None:
            self._role = role = get_object_or_404(UserRole, id=self.kwargs[self.role_id_kwarg])

            if (
                self.check_role_configuration
                and not ButtonMenuItem.objects.filter(role=role).exists()
            ):
                raise ConflictError(gettext('This role has no button configuration.'))

        return role


class _ButtonMenuCreationWizard(generic.wizard.CremeWizardViewPopup):
    class _ResourceStep(button_forms.ButtonMenuCreationForm):
        step_submit_label = pgettext_lazy('creme_config-verb', 'Select')

        def save(self, commit=False):
            return super().save(commit=commit)

    class _ButtonsStep(button_forms.ButtonMenuEditionForm):
        @property
        def step_title(self):
            return gettext('New buttons configuration for «{model}»').format(model=self.ct)

    form_list = [
        _ResourceStep,
        _ButtonsStep,
    ]
    title = 'New buttons configuration'
    submit_label = _('Save the configuration')
    permissions = 'creme_core.can_admin'

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)

        if step == '1':
            cleaned_data = self.get_cleaned_data_for_step('0')
            kwargs['button_menu_items'] = ()
            kwargs['ct_id'] = cleaned_data['ctype'].id
            kwargs['role'] = self.get_role()
            kwargs['superuser'] = self.get_superuser()

        return kwargs

    def get_superuser(self):
        return False

    def get_role(self):
        return None


class ButtonMenuBaseCreationWizard(_ButtonMenuCreationWizard):
    title = _('New buttons base configuration')


class ButtonMenuRoleCreationWizard(RoleRelatedMixin, _ButtonMenuCreationWizard):
    title = _('New buttons configuration for role «{role}»')

    def get_role(self):
        return self.get_related_role()

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['role'] = self.get_related_role()

        return data


class ButtonMenuSuperuserCreationWizard(_ButtonMenuCreationWizard):
    title = _('New buttons configuration for superusers')

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        if not ButtonMenuItem.objects.filter(superuser=True).exists():
            raise ConflictError(gettext('Superusers have no button configuration.'))

    def get_superuser(self):
        return True


class _ButtonMenuEdition(generic.base.EntityCTypeRelatedMixin, base.ConfigEdition):
    model = ButtonMenuItem
    form_class = button_forms.ButtonMenuEditionForm
    ct_id_0_accepted = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items = None

    def get_role(self):
        return None

    def get_superuser(self):
        return False

    def get_items(self):
        items = self.items

        if items is None:
            items = ButtonMenuItem.objects.filter(
                content_type=self.get_ctype(),
                role=self.get_role(), superuser=self.get_superuser()
            )

            if not items:
                raise Http404('This configuration does not exist.')

            self.items = items

        return items

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['button_menu_items'] = self.get_items()
        kwargs['role'] = self.get_role()
        kwargs['superuser'] = self.get_superuser()

        ctype = self.get_ctype()
        kwargs['ct_id'] = None if ctype is None else ctype.id

        return kwargs


class ButtonMenuBaseEdition(_ButtonMenuEdition):
    def get_title(self):
        ctype = self.get_ctype()

        return (
            gettext('Edit base configuration for «{model}»').format(model=ctype)
            if ctype else
            gettext('Edit default base configuration')
        )


class ButtonMenuRoleEdition(RoleRelatedMixin, _ButtonMenuEdition):
    check_role_configuration = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = None

    def get_role(self):
        return self.get_related_role()

    def get_title(self):
        ctype = self.get_ctype()
        role = self.get_related_role()

        return (
            gettext('Edit configuration of role «{role}» for «{model}»').format(
                role=role, model=ctype,
            ) if ctype else
            gettext('Edit default configuration of role «{role}»').format(role=role)
        )


class ButtonMenuSuperuserEdition(_ButtonMenuEdition):
    def get_superuser(self):
        return True

    def get_title(self):
        ctype = self.get_ctype()

        return (
            gettext('Edit configuration of superusers for «{model}»').format(model=ctype)
            if ctype else
            gettext('Edit default configuration of superusers')
        )


class ButtonMenuDeletion(base.ConfigDeletion):
    ct_id_arg = 'ctype'
    role_arg = 'role'

    def perform_deletion(self, request):
        kwargs = {}
        ctype_id = get_from_POST_or_404(request.POST, self.ct_id_arg, cast=int, default=0)

        raw_role = request.POST.get(self.role_arg)
        if raw_role is None:
            if not ctype_id:
                raise Http404('Default configuration cannot be deleted')

            kwargs['content_type'] = ctype_id
            kwargs['role'] = None
            kwargs['superuser'] = False
        else:
            if ctype_id:
                kwargs['content_type'] = ctype_id

            if raw_role == 'superuser':
                kwargs['superuser'] = True
            else:
                try:
                    kwargs['role'] = int(raw_role)
                except ValueError as e:
                    raise Http404(
                        f'The argument "{self.role_arg}" must be "superuser" or an integer.'
                    ) from e

        ButtonMenuItem.objects.filter(**kwargs).delete()


# Cloning ----------------------------------------------------------------------
class _ButtonMenuCloning(base.ConfigCreation):
    title = 'Clone the configuration'
    form_class = button_forms.ButtonMenuCloningForm
    submit_label = _('Clone')


class ButtonMenuBaseCloning(_ButtonMenuCloning):
    title = _('Clone the base configuration')
    form_class = button_forms.ButtonMenuCloningForm


class ButtonMenuRoleCloning(RoleRelatedMixin, _ButtonMenuCloning):
    title = _('Clone the configuration of «{role}»')
    form_class = button_forms.ButtonMenuCloningForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['source_role'] = self.get_related_role()

        return kwargs

    def get_title_format_data(self):
        return {'role': self.get_related_role()}


class ButtonMenuSuperuserCloning(_ButtonMenuCloning):
    title = _('Clone the configuration of superusers')
    form_class = button_forms.ButtonMenuCloningForm

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        if not ButtonMenuItem.objects.filter(superuser=True).exists():
            raise ConflictError(gettext('Superusers have no button configuration.'))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['source_superuser'] = True

        return kwargs
