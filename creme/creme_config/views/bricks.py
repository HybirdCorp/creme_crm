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

from django.db.transaction import atomic
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext_lazy

# from formtools.wizard.views import SessionWizardView

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui.bricks import brick_registry
from creme.creme_core.models import (UserRole,
        BrickDetailviewLocation, BrickHomeLocation, BrickMypageLocation,
        RelationBrickItem, InstanceBrickConfigItem, CustomBrickConfigItem)
from creme.creme_core.utils import get_from_POST_or_404, get_ct_or_404
from creme.creme_core.views.decorators import POST_only
from creme.creme_core.views.generic import BricksView
from creme.creme_core.views.generic.base import EntityCTypeRelatedMixin
# from creme.creme_core.views.generic.wizard import PopupWizardMixin

from ..forms import bricks as bricks_forms

from . import base


class Portal(BricksView):
    template_name = 'creme_config/bricks_portal.html'


class BrickDetailviewLocationsCreation(EntityCTypeRelatedMixin,
                                       # base.ConfigEdition,
                                       base.ConfigCreation,
                                      ):
    # model = BrickDetailviewLocation
    form_class = bricks_forms.BrickDetailviewLocationsAddForm
    # submit_label = _('Save the configuration')

    def check_related_ctype(self, ctype):
        super().check_related_ctype(ctype)

        if brick_registry.is_model_invalid(ctype.model_class()):
            raise ConflictError('This model cannot have a detail-view configuration.')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ctype'] = self.get_ctype()

        return kwargs

    def get_title(self):
        return ugettext('New block configuration for «{model}»').format(
            model=self.get_ctype(),
        )


class RelationTypeBrickCreation(base.ConfigModelCreation):
    model = RelationBrickItem
    form_class = bricks_forms.RTypeBrickAddForm


# class CustomBrickWizard(PopupWizardMixin, SessionWizardView):
class CustomBrickWizard(base.ConfigModelCreationWizard):
    class _ResourceStep(bricks_forms.CustomBrickConfigItemCreateForm):
        step_submit_label = pgettext_lazy('creme_config-verb', 'Select')

    class _ConfigStep(bricks_forms.CustomBrickConfigItemEditForm):
        class Meta(bricks_forms.CustomBrickConfigItemEditForm.Meta):
            exclude = ('name',)

        # step_prev_label = _('Previous step')
        # step_submit_label = _('Save the block')

    form_list = (
        _ResourceStep,
        _ConfigStep,
    )
    # wizard_title = _('New custom block')
    title = _('New custom block')
    submit_label = _('Save the block')
    # template_name = 'creme_core/generics/blockform/add_wizard_popup.html'
    # permission = 'creme_core.can_admin'

    # def done(self, form_list, **kwargs):
    #     resource_step, conf_step = form_list
    #
    #     with atomic():
    #         conf_step.instance = resource_step.save()
    #         conf_step.save()
    #
    #     return HttpResponse()
    def done_save(self, form_list):
        resource_step, conf_step = form_list

        # TODO: improve to do not save() twice
        conf_step.instance = resource_step.save()
        conf_step.save()

    def get_form_instance(self, step):
        if step == '1':
            cleaned_data = self.get_cleaned_data_for_step('0')
            return CustomBrickConfigItem(name=cleaned_data['name'],
                                         content_type=cleaned_data['ctype'],
                                        )


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
                                      base.ConfigEdition,
                                     ):
    # model = BrickDetailviewLocation
    form_class = bricks_forms.BrickDetailviewLocationsEditForm
    # template_name = 'creme_core/generics/blockform/edit-popup.html'
    submit_label = _('Save the configuration')
    ct_id_0_accepted = True

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.role_info = None

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
                title = ugettext('Edit configuration of super-users for «{model}»').format(model=ct)
            elif role is not None:
                title = ugettext('Edit configuration of «{role}» for «{model}»').format(
                    role=role,
                    model=ct,
                )
            else:
                title = ugettext('Edit default configuration for «{model}»').format(model=ct)
        else:
            title = _('Edit default configuration')

        return title


class HomeCreation(base.ConfigCreation):
    # model = BrickHomeLocation
    form_class = bricks_forms.BrickHomeLocationsAddingForm
    title = _('Create home configuration for a role')


class HomeEdition(RoleRelatedMixin, base.ConfigEdition):
    model = BrickHomeLocation  # TODO: useful ?
    # form_class = bricks_forms.BrickHomeLocationsForm
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
    permissions = None  # Every user can edit its own configuration
    title = _('Edit "My page"')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['owner'] = self.request.user

        return kwargs


# class RelationCTypeBrickWizard(PopupWizardMixin, SessionWizardView):
class RelationCTypeBrickWizard(base.ConfigModelCreationWizard):
    class _ContentTypeStep(bricks_forms.RTypeBrickItemAddCtypeForm):
        step_submit_label = pgettext_lazy('creme_config-verb', 'Select')

    # class _FieldsStep(bricks_forms.RTypeBrickItemEditCtypeForm):
    #     step_prev_label = _('Previous step')
    #     step_submit_label = _('Save the configuration')

    form_list = (
        _ContentTypeStep,
        # _FieldsStep,
        bricks_forms.RTypeBrickItemEditCtypeForm,
    )
    # wizard_title = 'New customised type'  # Overridden by get_context_data()
    title = _('New customised type for «{predicate}»')
    submit_label = _('Save the configuration')
    # template_name = 'creme_core/generics/blockform/add_wizard_popup.html'
    # permission = 'creme_core.can_admin'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.relation_brick_item = None

    # def done(self, form_list, **kwargs):
    #     _ct_form, fields_form = form_list
    #     fields_form.save()
    #
    #     return HttpResponse()

    # def get_context_data(self, form, **kwargs):
    #     context = super().get_context_data(form, **kwargs)
    #     context['title'] = ugettext('New customised type for «{predicate}»').format(
    #                             predicate=form.instance,
    #                         )
    #
    #     return context

    def get_relation_brick_item(self):
        rbi = self.relation_brick_item
        if rbi is None:
            rbi = self.relation_brick_item = \
                get_object_or_404(RelationBrickItem, id=self.kwargs['rbi_id'])

        return rbi

    def get_form_instance(self, step):
        # return get_object_or_404(RelationBrickItem, id=self.kwargs['rbi_id'])
        return self.get_relation_brick_item()

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step=step)

        if step == '1':
            kwargs['ctype'] = self.get_cleaned_data_for_step('0')['ctype']

        return kwargs

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['predicate'] = self.get_relation_brick_item()

        return data


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


@POST_only
@login_required
@permission_required('creme_core.can_admin')
@atomic
def delete_cells_of_rtype_brick(request, rbi_id):
    ctype = get_ct_or_404(get_from_POST_or_404(request.POST, 'id'))
    rbi = get_object_or_404(RelationBrickItem.objects.select_for_update(), id=rbi_id)

    try:
        rbi.delete_cells(ctype)
    except KeyError:
        raise Http404('This ContentType is not set in the RelationBrickItem.')

    rbi.save()

    return HttpResponse()


class CustomBrickEdition(base.ConfigModelEdition):
    model = CustomBrickConfigItem
    form_class = bricks_forms.CustomBrickConfigItemEditForm
    pk_url_kwarg = 'cbci_id'
    title = _('Edit the block «{object}»')


@login_required
@permission_required('creme_core.can_admin')
def delete_detailview(request):
    POST = request.POST
    ct_id = get_from_POST_or_404(POST, 'id', int)

    if not ct_id:
        raise Http404('Default config can not be deleted')

    role_id = None
    superuser = False

    role_str = POST.get('role')
    if role_str:
        if role_str == 'superuser':
            superuser = True
        else:
            try:
                role_id = int(role_str)
            except ValueError:
                raise Http404('"role" argument must be "superuser" or an integer')

    BrickDetailviewLocation.objects.filter(content_type=ct_id,
                                           role=role_id, superuser=superuser,
                                          ).delete()

    return HttpResponse()


@login_required
@permission_required('creme_core.can_admin')
def delete_home(request):
    # get_object_or_404(BrickHomeLocation,
    #                   pk=get_from_POST_or_404(request.POST, 'id'),
    #                  ).delete()

    role_str = get_from_POST_or_404(request.POST, 'role')

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

    return HttpResponse()


@login_required
@permission_required('creme_core.can_admin')
def delete_default_mypage(request):
    get_object_or_404(BrickMypageLocation,
                      pk=get_from_POST_or_404(request.POST, 'id'),
                      user=None,
                     ).delete()

    return HttpResponse()


@login_required
def delete_mypage(request):
    get_object_or_404(BrickMypageLocation,
                      pk=get_from_POST_or_404(request.POST, 'id'),
                      user=request.user,
                     ).delete()

    return HttpResponse()


@login_required
@permission_required('creme_core.can_admin')
def delete_rtype_brick(request):
    get_object_or_404(RelationBrickItem,
                      pk=get_from_POST_or_404(request.POST, 'id'),
                     ).delete()

    return HttpResponse()


@login_required
@permission_required('creme_core.can_admin')
def delete_instance_brick(request):
    get_object_or_404(InstanceBrickConfigItem,
                      pk=get_from_POST_or_404(request.POST, 'id'),
                     ).delete()

    return HttpResponse()


@login_required
@permission_required('creme_core.can_admin')
def delete_custom_brick(request):
    cbci_id = get_from_POST_or_404(request.POST, 'id')
    get_object_or_404(CustomBrickConfigItem, pk=cbci_id).delete()

    return HttpResponse()
