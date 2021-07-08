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

from django.db.models import Model, ProtectedError
from django.db.transaction import atomic
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui.bricks import brick_registry
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    BrickMypageLocation,
    CustomBrickConfigItem,
    InstanceBrickConfigItem,
    RelationBrickItem,
    UserRole,
)
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.utils.content_type import get_ctype_or_404
from creme.creme_core.views.generic import BricksView
from creme.creme_core.views.generic.base import EntityCTypeRelatedMixin

from ..forms import bricks as bricks_forms
from . import base


class Portal(BricksView):
    template_name = 'creme_config/portals/bricks.html'


class BrickDetailviewLocationsCreation(EntityCTypeRelatedMixin,
                                       base.ConfigCreation):
    # model = BrickDetailviewLocation
    form_class = bricks_forms.BrickDetailviewLocationsAddForm

    def check_related_ctype(self, ctype):
        super().check_related_ctype(ctype)

        if brick_registry.is_model_invalid(ctype.model_class()):
            raise ConflictError('This model cannot have a detail-view configuration.')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ctype'] = self.get_ctype()

        return kwargs

    def get_title(self):
        return gettext('New block configuration for «{model}»').format(
            model=self.get_ctype(),
        )


class RelationTypeBrickCreation(base.ConfigModelCreation):
    model = RelationBrickItem
    form_class = bricks_forms.RTypeBrickAddForm


class CustomBrickWizard(base.ConfigModelCreationWizard):
    class _ResourceStep(bricks_forms.CustomBrickConfigItemCreateForm):
        step_submit_label = pgettext_lazy('creme_config-verb', 'Select')

        def save(self, commit=False, *args, **kwargs):
            super().save(commit=commit, *args, **kwargs)

    class _ConfigStep(bricks_forms.CustomBrickConfigItemEditForm):
        class Meta(bricks_forms.CustomBrickConfigItemEditForm.Meta):
            exclude = ('name',)

        @property
        def step_title(self):
            return gettext('New custom block for «{model}»').format(
                model=self.instance.content_type,
            )

    form_list = [
        _ResourceStep,
        _ConfigStep,
    ]
    title = _('New custom block')
    submit_label = _('Save the block')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cbci = CustomBrickConfigItem()

    def get_form_instance(self, step):
        # We fill the instance with the previous step (so recursively all previous should be used)
        self.validate_previous_steps(step)

        return self.cbci


class RoleRelatedMixin:
    role_url_kwarg = 'role'

    def check_role_info(self, role, superuser):
        pass

    def get_role_info(self):
        try:
            role_info = getattr(self, 'role_info')
        except AttributeError:
            role = self.kwargs[self.role_url_kwarg]

            if role == 'default':
                role_obj = None
                superuser = False
            elif role == 'superuser':
                role_obj = None
                superuser = True
            else:
                try:
                    role_id = int(role)
                except ValueError:
                    raise Http404('Role must be "default", "superuser" or an integer')

                role_obj = get_object_or_404(UserRole, id=role_id)
                superuser = False

            self.check_role_info(role_obj, superuser)

            self.role_info = role_info = (role_obj, superuser)

        return role_info


class BrickDetailviewLocationsEdition(EntityCTypeRelatedMixin,
                                      RoleRelatedMixin,
                                      base.ConfigEdition):
    # model = BrickDetailviewLocation
    form_class = bricks_forms.BrickDetailviewLocationsEditForm
    submit_label = _('Save the configuration')
    ct_id_0_accepted = True

    # TODO: factorise + remove _get_configurable_ctype()
    def check_related_ctype(self, ctype):
        super().check_related_ctype(ctype)

        if brick_registry.is_model_invalid(ctype.model_class()):
            raise ConflictError('This model cannot have a detail-view configuration.')

    def check_role_info(self, role, superuser):
        if self.get_ctype() is None and (superuser or role):
            raise Http404('You can only edit "default" role with default config')

    # TODO: factorise ?
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ctype'] = self.get_ctype()
        kwargs['role'], kwargs['superuser'] = self.get_role_info()

        return kwargs

    def get_title(self):
        ct = self.get_ctype()
        role, superuser = self.get_role_info()

        if ct is not None:
            if superuser:
                title = gettext(
                    'Edit configuration of super-users for «{model}»'
                ).format(model=ct)
            elif role is not None:
                title = gettext(
                    'Edit configuration of «{role}» for «{model}»'
                ).format(role=role, model=ct)
            else:
                title = gettext(
                    'Edit default configuration for «{model}»'
                ).format(model=ct)
        else:
            title = _('Edit default configuration')

        return title


class HomeCreation(base.ConfigCreation):
    # model = BrickHomeLocation
    form_class = bricks_forms.BrickHomeLocationsAddingForm
    title = _('Create home configuration for a role')


class HomeEdition(RoleRelatedMixin, base.ConfigEdition):
    model = BrickHomeLocation  # TODO: useful ?
    form_class = bricks_forms.BrickHomeLocationsEditionForm
    title = _('Edit home configuration')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['role'], kwargs['superuser'] = self.get_role_info()

        return kwargs


class BaseMyPageEdition(base.ConfigEdition):
    model = BrickMypageLocation
    form_class = bricks_forms.BrickMypageLocationsForm


class DefaultMyPageEdition(BaseMyPageEdition):
    title = _('Edit default "My page"')


class MyPageEdition(BaseMyPageEdition):
    # permissions = None  # Every user can edit its own configuration
    permissions = ''  # Every user can edit its own configuration
    title = _('Edit "My page"')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['owner'] = self.request.user

        return kwargs


class RelationCTypeBrickWizard(base.ConfigModelEditionWizard):
    model = RelationBrickItem
    pk_url_kwarg = 'rbi_id'

    class _ContentTypeStep(bricks_forms.RTypeBrickItemAddCtypeForm):
        step_submit_label = pgettext_lazy('creme_config-verb', 'Select')

    form_list = [
        _ContentTypeStep,
        bricks_forms.RTypeBrickItemEditCtypeForm,
    ]
    title = _('New customised type for «{object}»')
    submit_label = _('Save the configuration')

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step=step)

        if step == '1':
            kwargs['ctype'] = self.get_cleaned_data_for_step('0')['ctype']

        return kwargs


class RelationCTypeBrickEdition(EntityCTypeRelatedMixin, base.ConfigModelEdition):
    model = RelationBrickItem
    form_class = bricks_forms.RTypeBrickItemEditCtypeForm
    pk_url_kwarg = 'rbi_id'
    title = _('Edit «{model}» configuration')

    def check_instance_permissions(self, instance, user):
        super().check_instance_permissions(instance=instance, user=user)

        if instance.get_cells(self.get_ctype()) is None:
            raise Http404('This ContentType is not set in the RelationBrickItem.')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ctype'] = self.get_ctype()

        return kwargs

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['model'] = self.get_ctype()

        return data


class CellsOfRtypeBrickDeletion(base.ConfigDeletion):
    rbi_id_url_kwarg = 'rbi_id'
    ct_id_arg = 'id'

    @atomic
    def perform_deletion(self, request):
        ctype = get_ctype_or_404(get_from_POST_or_404(request.POST, self.ct_id_arg))
        rbi = get_object_or_404(
            RelationBrickItem.objects.select_for_update(),
            id=self.kwargs[self.rbi_id_url_kwarg],
        )

        try:
            rbi.delete_cells(ctype)
        except KeyError:
            raise Http404('This ContentType is not set in the RelationBrickItem.')

        rbi.save()


class CustomBrickEdition(base.ConfigModelEdition):
    model = CustomBrickConfigItem
    form_class = bricks_forms.CustomBrickConfigItemEditForm
    pk_url_kwarg = 'cbci_id'
    title = _('Edit the block «{object}»')


class BrickDetailviewLocationsDeletion(base.ConfigDeletion):
    ct_id_arg = 'id'
    role_arg = 'role'

    def perform_deletion(self, request):
        POST = request.POST
        ct_id = get_from_POST_or_404(POST, self.ct_id_arg, cast=int)

        if not ct_id:
            raise Http404('Default config can not be deleted')

        role_id = None
        superuser = False

        role_str = POST.get(self.role_arg)
        if role_str:
            if role_str == 'superuser':
                superuser = True
            else:
                try:
                    role_id = int(role_str)
                except ValueError:
                    raise Http404(
                        '"role" argument must be "superuser" or an integer'
                    )

        BrickDetailviewLocation.objects.filter(
            content_type=ct_id,
            role=role_id, superuser=superuser,
        ).delete()


class HomeDeletion(base.ConfigDeletion):
    role_arg = 'role'

    def perform_deletion(self, request):
        role_str = get_from_POST_or_404(request.POST, self.role_arg)

        role_id = None
        superuser = False

        if role_str == 'superuser':
            superuser = True
        else:
            try:
                role_id = int(role_str)
            except ValueError:
                raise Http404('"role" argument must be "superuser" or an integer')

        BrickHomeLocation.objects.filter(role=role_id, superuser=superuser).delete()


class DefaultMyPageDeletion(base.ConfigDeletion):
    id_arg = 'id'

    def perform_deletion(self, request):
        get_object_or_404(
            BrickMypageLocation,
            pk=get_from_POST_or_404(request.POST, self.id_arg),
            user=None,
        ).delete()


class MyPageDeletion(base.ConfigDeletion):
    permissions = ''
    id_arg = 'id'

    def perform_deletion(self, request):
        get_object_or_404(
            BrickMypageLocation,
            pk=get_from_POST_or_404(request.POST, self.id_arg),
            user=request.user,
        ).delete()


class BaseBrickTypeDeletion(base.ConfigDeletion):
    id_arg = 'id'
    model = Model

    def perform_deletion(self, request):
        try:
            get_object_or_404(
                self.model,
                pk=get_from_POST_or_404(request.POST, self.id_arg),
            ).delete()
        except ProtectedError as e:
            raise ConflictError(e.args[0])


class RelationTypeBrickDeletion(BaseBrickTypeDeletion):
    model = RelationBrickItem


class CustomBrickDeletion(BaseBrickTypeDeletion):
    model = CustomBrickConfigItem


class InstanceBrickDeletion(BaseBrickTypeDeletion):
    model = InstanceBrickConfigItem
